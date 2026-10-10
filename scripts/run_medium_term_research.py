"""Hash-locked causal medium-term detection and paired source backtests."""
from __future__ import annotations

import argparse
import gzip
import heapq
import itertools
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from crypto_bot.common.models import Candle
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_medium_term import (
    MediumTermEngine,
    MediumTermPortfolio,
    portfolio_signal,
)
from crypto_bot.strategy.source_pdf_native import evidence_json
from crypto_bot.strategy.source_permitted import SourceSeries
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_support import read_compressed

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'data/reports/medium_term_2026_10_10'
POLICY_PATH = REPO / 'config/source_medium_term_policy.json'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(evidence_json(obj) + '\n')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
        for row in rows:
            compressed.write((evidence_json(row) + '\n').encode())


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(row) for row in stream]


def seal(folder, fingerprint, metadata):
    files = {str(p.relative_to(folder)): digest(p) for p in sorted(folder.rglob('*'))
             if p.is_file() and p.name != 'manifest.json'}
    write_json(folder / 'manifest.json', dict(status='COMPLETE', fingerprint=fingerprint,
                                             artifacts=files, trade_entry_allowed=False, **metadata))


def resume(folder, fingerprint, allowed):
    if not folder.exists():
        return False
    if not allowed:
        raise ValueError(f'Existing artifacts require --resume-existing: {folder}')
    manifest_path = folder / 'manifest.json'
    if not manifest_path.exists():
        raise ValueError(f'Incomplete segment preserved; select a new output root: {folder}')
    m = json.loads(manifest_path.read_text())
    if m['fingerprint'] != fingerprint or m['status'] != 'COMPLETE':
        raise ValueError('Dependency fingerprint changed: ' + str(folder))
    actual = {str(p.relative_to(folder)): digest(p) for p in folder.rglob('*')
              if p.is_file() and p.name != 'manifest.json'}
    if actual != m['artifacts']:
        raise ValueError('Artifact checksum/membership mismatch: ' + str(folder))
    print('VERIFIED_RESUME', folder.relative_to(REPO), flush=True)
    return True


def complete_aggregate(candles, minutes):
    """No partial buckets, gaps, duplicated timestamps or interpolated candles."""
    width = timedelta(minutes=minutes)
    buckets = defaultdict(list)
    for c in candles:
        stamp = int(c.open_time.timestamp()) // (minutes * 60) * minutes * 60
        buckets[stamp].append(c)
    result, excluded = [], 0
    for stamp, rows in sorted(buckets.items()):
        start = datetime.fromtimestamp(stamp, candles[0].open_time.tzinfo)
        if (rows[0].open_time != start or rows[-1].close_time != start + width
                or any(b.open_time != a.close_time for a, b in itertools.pairwise(rows))):
            excluded += 1
            continue
        result.append(Candle(start, start + width, rows[0].open,
                             max(c.high for c in rows), min(c.low for c in rows), rows[-1].close))
    return result, excluded


def inputs_for(cohort, symbol):
    if cohort == 'bybit_2023_2025':
        return {tf: f'data/history/public_research/bybit_mirror/{symbol}/{tf}.csv.gz' for tf in (15, 60, 240)}
    return {tf: f'data/history/bybit/{symbol}/{tf}.csv' for tf in (5, 15, 60, 240)}


def load_data(cohort, symbol, policy):
    result, audits = {}, []
    begin = datetime.fromisoformat(policy['warmup_start']) if cohort == 'bybit_2023_2025' else None
    end = datetime.fromisoformat(policy['requested_end']) if cohort == 'bybit_2023_2025' else None
    for tf, name in inputs_for(cohort, symbol).items():
        path = REPO / name
        if path.suffix == '.gz':
            candles = read_compressed(path, tf, begin=begin, end=end)
        else:
            candles = [r.to_strategy_candle(tf * 60000) for r in read_klines_csv(path)]
        if not candles or any(b.open_time != a.close_time for a, b in itertools.pairwise(candles)):
            raise ValueError(f'Empty or discontinuous data: {path}')
        if any(int(c.open_time.timestamp()) % (tf * 60) or not c.is_closed for c in candles):
            raise ValueError('Unaligned or unfinished real bars')
        result[tf] = candles
        audits.append({'tf': tf, 'path': name, 'sha256': digest(path), 'candles': len(candles),
                           'start': candles[0].open_time, 'end': candles[-1].close_time, 'gaps': 0})
    clock = min(result)
    result[1440], excluded = complete_aggregate(result[clock], 1440)
    audits.append({'tf': 1440, 'source_tf': clock, 'derivation': 'COMPLETE_REAL_UTC_DAYS_ONLY',
                       'candles': len(result[1440]), 'excluded_partial_buckets': excluded,
                       'candle_content_sha256': sha256(evidence_json([asdict(c) for c in result[1440]]).encode()).hexdigest()})
    return result, audits


def fingerprint(cohort, symbols, policy):
    paths = list((REPO / 'src').rglob('*.py'))
    paths += [POLICY_PATH, Path(__file__), REPO / 'scripts/research_support.py', REPO / 'MEDIUM_TERM_RESEARCH_PROTOCOL.md']
    paths += list((REPO / 'data/source_materials/primary_pdf_2026_10_09').glob('SW*.*'))
    paths += [REPO / name for s in symbols for name in inputs_for(cohort, s).values()]
    return {'code_and_data_hashes': {str(p.relative_to(REPO)): digest(p) for p in sorted(set(paths))},
            'cohort': cohort, 'symbols': symbols, 'policy': policy, 'trade_entry_allowed': False}


def detect(cohort, symbol, policy, lock, use_resume):
    folder = ROOT / cohort / 'detection' / symbol
    fp = sha256(evidence_json({'lock': lock, 'symbol': symbol}).encode()).hexdigest()
    if resume(folder, fp, use_resume):
        return
    data, audits = load_data(cohort, symbol, policy)
    engines = {}
    # Analyze once; state owners remain separate in the two paired arms.
    owners = {'enabled': {}, 'disabled_cost_gate': {}}
    for tf, candles in data.items():
        print(cohort, symbol, 'analyze', tf, len(candles), flush=True)
        analysis = SimpleNamespace(events=[]) if tf == 5 else analyze_market(candles, timeframe_minutes=tf)
        ranges = None if tf == 5 else analyze_ranges(candles, analysis, params=RangeDetectionParams(
            midpoint_tolerance_fraction=policy['range_midpoint_tolerance']))
        for arm_series in owners.values():
            arm_series[tf] = SourceSeries(symbol, tf, candles, analysis, ranges)
    for arm, arm_series in owners.items():
        engines[arm] = MediumTermEngine(symbol, arm_series, policy,
                                         anti_scalp_enabled=arm == 'enabled')
    start = datetime.fromisoformat(policy['requested_start']) if cohort == 'bybit_2023_2025' else data[policy['execution_clock']][0].open_time
    merged = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(cs)] for tf, cs in data.items()])
    last_log = time.monotonic()
    for now, rows in itertools.groupby(merged, key=lambda x: x[0]):
        rows = list(rows)
        changed = [r[2] for r in rows]
        for engine in engines.values():
            for _, _, tf, i in rows:
                engine.advance(tf, i)
            if policy['execution_clock'] in changed and now >= start:
                engine.evaluate(now, changed)
        if time.monotonic() - last_log > 40:
            print(cohort, symbol, now.isoformat(), 'READY', {a: len(e.signals) for a, e in engines.items()}, flush=True)
            last_log = time.monotonic()
    folder.mkdir(parents=True)
    write_json(folder / 'dataset_audit.json', audits)
    write_rows(folder / 'derived_D1.jsonl.gz', (asdict(c) for c in data[1440]))
    for arm, e in engines.items():
        write_rows(folder / arm / 'signals.jsonl.gz', (asdict(s) for s in e.signals))
        write_rows(folder / arm / 'cancellations.jsonl.gz', e.cancellations)
        write_rows(folder / arm / 'exit_events.jsonl.gz', e.exit_events)
        write_rows(folder / arm / 'attempts.jsonl.gz', e.attempts)
        write_rows(folder / arm / 'anti_scalp_rejections.jsonl.gz', e.rejections)
        write_rows(folder / arm / 'setup_lifecycle.jsonl.gz', e.lifecycle)
        write_json(folder / arm / 'funnel.json', e.finish())
    seal(folder, fp, {'symbol': symbol, 'arms': list(engines), 'coverage_start': start,
                          'coverage_end': data[policy['execution_clock']][-1].close_time})


def deserialize_signal(row):
    row = dict(row)
    row['known_at'] = datetime.fromisoformat(row['known_at'])
    row['targets'], row['fractions'] = tuple(row['targets']), tuple(row['fractions'])
    return SourceSignal(**row)


def indexed(rows):
    result = defaultdict(list)
    for r in rows:
        at = r.known_at if isinstance(r, SourceSignal) else datetime.fromisoformat(r['known_at'])
        if isinstance(r, dict):
            r = {**r, 'known_at': at}
        result[at].append(r)
    return result


def create_portfolio(policy, arm):
    return MediumTermPortfolio(equity=policy['case_reference_equity'],
                               anti_scalp_enabled=arm == 'enabled',
                               policy=SimulationPolicy(risk_fraction=policy['risk_fraction'],
                                                       fee_fraction=policy['fee_rate'],
                                                       slippage_fraction=policy['slippage_fraction']))


def simulate(cohort, symbols, policy, lock, arm, use_resume):
    folder = ROOT / cohort / 'simulation' / arm
    detector_hashes = {s: digest(ROOT / cohort / 'detection' / s / 'manifest.json') for s in symbols}
    fp = sha256(evidence_json({'lock': lock, 'detection': detector_hashes, 'arm': arm}).encode()).hexdigest()
    if resume(folder, fp, use_resume):
        return
    clock = policy['execution_clock']
    clocks, all_signals, cancels, exits = {}, [], [], []
    for s in symbols:
        data, _ = load_data(cohort, s, policy)
        clocks[s] = data[clock]
        base = ROOT / cohort / 'detection' / s / arm
        all_signals.extend(deserialize_signal(r) for r in read_rows(base / 'signals.jsonl.gz'))
        cancels.extend(read_rows(base / 'cancellations.jsonl.gz'))
        exits.extend(read_rows(base / 'exit_events.jsonl.gz'))
    all_signals.sort(key=lambda s: (s.known_at, policy['entry_tie_precedence'].index(s.setup_type), -s.htf, s.symbol, s.signal_id))
    start = max(cs[0].open_time for cs in clocks.values())
    if cohort == 'bybit_2023_2025':
        start = max(start, datetime.fromisoformat(policy['requested_start']))
    end = min(cs[-1].close_time for cs in clocks.values())
    per_time = {s: {c.close_time: c for c in cs if c.open_time >= start and c.close_time <= end}
                for s, cs in clocks.items()}
    signal_updates, cancel_updates, exit_updates = indexed(all_signals), indexed(cancels), indexed(exits)
    portfolio = create_portfolio(policy, arm)
    for now in sorted(next(iter(per_time.values()))):
        bars = {s: cs[now] for s, cs in per_time.items()}
        portfolio.source_step(bars, signal_updates[now], cancel_updates[now], exit_updates[now])
    folder.mkdir(parents=True)
    for t in portfolio.trades.values():
        t['source_setup'] = portfolio.source_signals[t['signal_id']].setup_type
    write_rows(folder / 'shared_trades.jsonl.gz', portfolio.trades.values())
    write_rows(folder / 'shared_journal.jsonl.gz', (asdict(d) for d in portfolio.journal))
    write_rows(folder / 'shared_equity_curve.jsonl.gz', portfolio.equity_curve)
    write_rows(folder / 'admission_anti_scalp_rejections.jsonl.gz', portfolio.anti_scalp_admission_rejections)
    from research_support import performance
    summary = performance(portfolio, [portfolio_signal(s, clock) for s in all_signals if start < s.known_at <= end], start, end)
    write_json(folder / 'shared_summary.json', summary)
    # Independent cases cover each symbol's full available entry interval.
    cases, case_lifecycle, case_admission_blocks = [], [], []
    by_symbol_index = {s: {c.close_time: i for i, c in enumerate(cs)} for s, cs in clocks.items()}
    cancel_by_id = defaultdict(list)
    exit_by_id = defaultdict(list)
    for r in cancels:
        cancel_by_id[r['signal_id']].append(r)
    for r in exits:
        exit_by_id[r['signal_id']].append(r)
    for i, signal in enumerate(all_signals):
        p = create_portfolio(policy, arm)
        si = by_symbol_index[signal.symbol][signal.known_at]
        cc = indexed(cancel_by_id[signal.signal_id])
        ee = indexed(exit_by_id[signal.signal_id])
        for j, c in enumerate(clocks[signal.symbol][si:]):
            p.source_step({signal.symbol: c}, [signal] if j == 0 else (), cc[c.close_time], ee[c.close_time])
            # A case has no NAV inference; retain bounded current bookkeeping.
            if len(p.equity_curve) > 2:
                p.equity_curve = p.equity_curve[-2:]
            if p.trades and next(iter(p.trades.values()))['status'] == 'CLOSED':
                break
            if signal.signal_id in p.consumed_ids and not p.trades or signal.signal_id in p.terminal_ids and not p.trades:
                break
        if p.trades:
            t = dict(next(iter(p.trades.values())))
            t['source_setup'] = signal.setup_type
            t['physical_opportunity_id'] = signal.evidence['physical_opportunity_id']
            t['anti_scalp'] = signal.evidence['anti_scalp']
            cases.append(t)
            case_lifecycle.extend([{'idea_id': t['physical_opportunity_id'], 'signal_id': signal.signal_id,
                                       'status': 'ENTERED', 'known_at': t['entry_time'], 'trade_entry_allowed': False},
                                   {'idea_id': t['physical_opportunity_id'], 'signal_id': signal.signal_id,
                                       'status': t['status'] if t['status'] == 'CLOSED' else 'CENSORED_OPEN',
                                       'known_at': t.get('exit_time', clocks[signal.symbol][-1].close_time), 'trade_entry_allowed': False}])
        elif signal.signal_id in p.terminal_ids:
            case_lifecycle.append({'idea_id': signal.evidence['physical_opportunity_id'], 'signal_id': signal.signal_id,
                                       'status': 'INVALIDATED', 'known_at': p.last_close, 'trade_entry_allowed': False})
        else:
            case_lifecycle.append({'idea_id': signal.evidence['physical_opportunity_id'], 'signal_id': signal.signal_id,
                                       'status': 'CENSORED_UNFILLED', 'known_at': p.last_close, 'trade_entry_allowed': False})
        case_admission_blocks.extend(asdict(d) for d in p.journal if d.action == 'VIRTUAL_ENTRY_BLOCKED')
        if i % 50 == 0:
            print(cohort, arm, 'independent cases', i + 1, '/', len(all_signals), flush=True)
    write_rows(folder / 'independent_cases.jsonl.gz', cases)
    write_rows(folder / 'execution_lifecycle.jsonl.gz', case_lifecycle)
    write_rows(folder / 'case_admission_blocks.jsonl.gz', case_admission_blocks)
    write_json(folder / 'coverage.json', {'shared_start': start, 'shared_end': end,
                                              'per_symbol': {s: {'start': cs[0].open_time, 'end': cs[-1].close_time}
                                                          for s, cs in clocks.items()},
                                              'requested_start': policy['requested_start'], 'requested_end': policy['requested_end'],
                                              'forced_close': False, 'trade_entry_allowed': False})
    seal(folder, fp, {'arm': arm, 'READY': len(all_signals), 'FILLED': len(cases),
                          'CLOSED': sum(t['status'] == 'CLOSED' for t in cases),
                          'shared_FILLED': len(portfolio.trades), 'shared_CLOSED': summary['completed_trades']})


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=('bybit_2023_2025', 'native_bybit_2026'), required=True)
    parser.add_argument('--stage', choices=('register', 'detect', 'simulate', 'all'), default='all')
    parser.add_argument('--symbols', nargs='+')
    parser.add_argument('--resume-existing', action='store_true')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    args = parser.parse_args()
    ROOT = args.output_root.resolve()
    if not ROOT.is_relative_to(REPO / 'data/reports'):
        raise ValueError('Research output must remain inside repository reports')
    policy = json.loads(POLICY_PATH.read_text())
    if args.cohort == 'native_bybit_2026':
        policy['execution_clock'] = 5
    symbols = args.symbols or (['BTCUSDT', 'ETHUSDT'] if args.cohort == 'bybit_2023_2025' else policy['symbol_priority'])
    lock = fingerprint(args.cohort, symbols, policy)
    lock_path = ROOT / args.cohort / 'run_lock.json'
    if lock_path.exists():
        if json.loads(lock_path.read_text()) != lock:
            raise ValueError('Registered code/data/policy changed; preserve this run and create a new root')
    else:
        write_json(lock_path, lock)
    if args.stage == 'register':
        print('REGISTERED_BEFORE_OUTCOMES', args.cohort, sha256(evidence_json(lock).encode()).hexdigest())
        return
    if args.stage in ('detect', 'all'):
        for s in symbols:
            detect(args.cohort, s, policy, lock, args.resume_existing)
    if args.stage in ('simulate', 'all'):
        for arm in ('enabled', 'disabled_cost_gate'):
            simulate(args.cohort, symbols, policy, lock, arm, args.resume_existing)


if __name__ == '__main__':
    main()
