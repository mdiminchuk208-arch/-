"""Full retained native Bybit replay, verified segment resume, independent cases and separate paper portfolio.

No network access. Source policy is registered before outcomes. Output must be
fresh or each existing segment must pass exact code/input/artifact verification.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
import gzip
from hashlib import sha256
import heapq
import itertools
import json
from pathlib import Path
import statistics
import time

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_corrected import (SourceEngine, SourceSeries, SourceSignal, evidence_json,
                                               opposing_liquidity, pd_location, sign)
from crypto_bot.strategy.source_portfolio import SourcePortfolio, SourceRiskPolicy
from crypto_bot.strategy.source_cases import deduplicate_cases, replay_case

REPO = Path(__file__).resolve().parents[1]
POLICY = REPO / 'config/source_case_policy.json'
DATA_RECEIPT = REPO / 'data/reports/source_validation_qa_2026_10_09/dataset_integrity.json'
IMPLEMENTATION = ['scripts/run_source_cases_bybit.py', 'config/source_case_policy.json',
                  'SOURCE_CORRECTION_PROTOCOL.md', 'src/crypto_bot/strategy/source_cases.py',
                  'SOURCE_RECONSTRUCTION_2026_10_09.md', 'src/crypto_bot/strategy/source_corrected.py', 'src/crypto_bot/strategy/source_engine.py',
                  'src/crypto_bot/strategy/source_portfolio.py', 'src/crypto_bot/strategy/market_analysis.py',
                  'src/crypto_bot/strategy/range_engine.py', 'src/crypto_bot/strategy/structure.py',
                  'src/crypto_bot/strategy/sfp.py', 'src/crypto_bot/common/models.py',
                  'src/crypto_bot/data/storage.py', 'src/crypto_bot/data/models.py']


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, default=lambda x: x.isoformat() if isinstance(x, datetime) else x.value,
                                    ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def write_rows(path, rows):
    with Path(path).open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as output:
        for row in rows:
            output.write((evidence_json(row) + '\n').encode())


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def verify_segment(folder, fingerprint):
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest.get('status') != 'COMPLETE' or manifest.get('fingerprint') != fingerprint:
        raise ValueError(f'resume fingerprint mismatch: {folder}')
    expected = {'signals.jsonl.gz', 'cancellations.jsonl.gz', 'setup_outcomes.jsonl.gz', 'summary.json', 'old_loss_audit.json', 'intermediate_audit.json', 'flow_history.jsonl.gz', 'range_audit.jsonl.gz'}
    if set(manifest['artifacts']) != expected:
        raise ValueError('incomplete segment artifact manifest')
    for name, checksum in manifest['artifacts'].items():
        if digest(folder / name) != checksum:
            raise ValueError(f'resume artifact corruption: {folder / name}')
    return manifest


def old_losses():
    out = []
    for folder in ('limit_60_5', 'final_60_15', 'final_240_5', 'final_240_15', 'final_240_60'):
        root = REPO / 'data/reports/historical_blocker_investigation/stage3' / folder
        for line in (root / 'trades.jsonl').read_text().splitlines():
            t = json.loads(line)
            if t.get('status') != 'CLOSED' or t['net_pnl'] >= 0:
                continue
            signals = [r for r in read_rows(root / 'signals.jsonl.gz') if r['signal_id'] == t['signal_id']
                       and datetime.fromisoformat(r['event_time']) <= datetime.fromisoformat(t['entry_interval_start'])]
            signal = max(signals, key=lambda r: r['event_time'])
            out.append({'old_trade': t, 'old_signal': signal, 'source_folder': str(root.relative_to(REPO)),
                        'snapshots': {}})
    if len(out) != 5:
        raise ValueError('expected exactly five original unique losses')
    return out


def load_intermediate(symbol):
    root = REPO / 'data/reports/source_bybit_2026_10_09_final'
    return [{'old_trade': t, 'snapshots': {}} for t in read_rows(root / 'primary_trades.jsonl.gz') if t['symbol'] == symbol]


def intermediate_snapshot(engine, trade, now):
    h, l = engine.series[trade['htf']], engine.series[trade['ltf']]
    old = trade['evidence']
    z = old['htf_poi']
    external = None
    if z['kind'] == 'RANGE_POI':
        # Reconstruct the actually known external candidates at the old deviation.
        raid_open = datetime.fromisoformat(z['formed_at'])
        from datetime import timedelta
        raid_open -= timedelta(minutes=trade['htf'] * 2)
        raid_end = raid_open + timedelta(minutes=trade['htf'])
        candidates = []
        for p in h.zone_registry.values():
            if p.kind in ('RANGE_POI', 'FVG') or p.direction != trade['direction'] or p.known_at > raid_open:
                continue
            if p.invalidated_at is not None and p.invalidated_at <= raid_end:
                continue
            if p.first_test is not None and p.first_test < raid_open:
                continue
            outside = p.high <= z['low'] if trade['direction'] == 'LONG' else p.low >= z['high']
            observed = [c for c in h.candles[:h.index + 1] if c.open_time == raid_open]
            if outside and observed and observed[0].low <= p.high and observed[0].high >= p.low:
                candidates.append(asdict(p))
        external = candidates
    return {'known_at': now, 'flow': json.loads(evidence_json(h.flow)),
            'range_external_poi_candidates': external,
            'htf_trend': h.trend.value, 'ltf_trend': l.trend.value,
            'matching_corrected_ready': [s.signal_id for s in engine.signals if s.htf == trade['htf'] and s.ltf == trade['ltf']
                                         and s.known_at <= now and s.direction == trade['direction']
                                         and abs(s.entry - trade['entry_reference']) < 1e-10]}


def audit_intermediate(engine, records):
    for row in records:
        t, reasons = row['old_trade'], []
        ready = row['snapshots'].get('ready_time')
        z, local = t['evidence']['htf_poi'], t['evidence']['ltf_poi']
        if t['ltf'] > 15:
            reasons.append('240_60_OUTSIDE_STRICT_CONSERVATIVE_SCOPE')
        if z['kind'] == 'RANGE_POI' and ready is not None and not ready['range_external_poi_candidates']:
            reasons.append('RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI')
        if ready is not None and (ready['flow'] is None or ready['flow']['invalidated_at'] is not None
                                   or ready['flow']['direction'] != t['direction']):
            reasons.append('NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY')
        from crypto_bot.strategy.source_corrected import poi_entry_policy, Zone, Raid
        copied = dict(local)
        copied['raid'] = Raid(**{**copied['raid'], 'known_at': datetime.fromisoformat(copied['raid']['known_at'])}) if copied['raid'] else None
        for name in ('formed_at', 'known_at', 'first_test', 'last_test', 'invalidated_at'):
            if copied[name]:
                copied[name] = datetime.fromisoformat(copied[name])
        copied_zone = Zone(**copied)
        raid_row = t['evidence']['liquidity_sweep']
        raid = Raid(**{**raid_row, 'known_at': datetime.fromisoformat(raid_row['known_at'])})
        quote, stop, _, _ = poi_entry_policy(copied_zone, raid)
        if abs(quote - t['entry_reference']) > 1e-10:
            reasons.append('OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY')
        if abs(stop - t['stop']) > 1e-10:
            reasons.append('OLD_UNIVERSAL_STOP_DIFFERS_FROM_REGISTERED_POI_POLICY')
        if z['kind'] in ('DEMAND', 'SUPPLY'):
            reasons.append('OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK')
        row['classification'] = 'FALSE_POSITIVE_IMPLEMENTATION' if reasons else 'SOURCE_VALID' if ready and ready['matching_corrected_ready'] else 'UNCERTAIN'
        row['reasons'] = reasons or ['EXACT_CORRECTED_CHAIN_NOT_PROVEN_WITH_MISSING_PRIMARY_MODULES']
        row['remaining_in_corrected_sample'] = bool(ready and ready['matching_corrected_ready'] and not reasons)
        row['trade_entry_allowed'] = False


def snapshot_old(engine, record, now):
    t, old_signal = record['old_trade'], record['old_signal']
    h, l = engine.series[t['htf']], engine.series[t['ltf']]
    direction, entry, stop = t['direction'], t['theoretical_entry'], t['stop']
    adverse = opposing_liquidity(list(h.pools.values()) + list(l.pools.values()), direction, entry, stop)
    h_zones = [z for z in h.zone_registry.values() if z.direction == direction and z.known_at <= now
               and z.invalidated_at is None and z.kind != 'FVG']
    supporting = next((e for e in old_signal['level_evidence'] if e['kind'] == 'SUPPORTING_HTF_POI'), None)
    if supporting is not None:
        a, b = supporting['prices'][:2]
        h_zones = [z for z in h_zones if z.low <= b and z.high >= a]
    local = [z for z in l.zone_registry.values() if z.direction == direction and z.known_at <= now and z.low <= entry <= z.high]
    h_zone = max(h_zones, key=lambda z: z.known_at, default=None)
    local_zone = max(local, key=lambda z: z.known_at, default=None)
    expected = 'BULLISH' if direction == 'LONG' else 'BEARISH'
    fta = [z for s in (h, l) if (z := s.target(direction, entry, now)) is not None]
    pd = pd_location(direction, entry, h_zone.leg_low, h_zone.leg_high) if h_zone else None
    blockers = []
    if h.trend.value != expected:
        blockers.append('HTF_ORDER_FLOW_DIRECTION_' + h.trend.value)
    if l.trend.value != expected:
        blockers.append('LTF_CURRENT_STRUCTURE_' + l.trend.value)
    if adverse:
        blockers.append('MEANINGFUL_UNSWEPT_LIQUIDITY_BETWEEN_ENTRY_AND_SL')
    if h_zone is None:
        blockers.append('NO_TYPED_QUALIFIED_HTF_POI_SUPPORTING_OLD_GAP')
    if local_zone is None:
        blockers.append('NO_TYPED_LOCAL_POI_AT_OLD_QUOTE')
    elif not local_zone.fresh(now):
        blockers.append('OLD_LOCAL_POI_ALREADY_TESTED_OR_INVALIDATED')
    conf = l.conf.get(direction)
    if conf is None or datetime.fromisoformat(old_signal['bos_time']) >= conf['known_at']:
        blockers.append('NO_ACTIVE_CONF_AFTER_OLD_BOS')
    if pd is not None and not pd[0]:
        blockers.append('OUTSIDE_REQUIRED_DISCOUNT_PREMIUM')
    if not fta:
        blockers.append('NO_FIRST_OPPOSING_POI_FTA')
    hard = any(b.startswith(('HTF_ORDER_FLOW_DIRECTION_BEARISH', 'HTF_ORDER_FLOW_DIRECTION_BULLISH',
                             'LTF_CURRENT_STRUCTURE_BEARISH', 'LTF_CURRENT_STRUCTURE_BULLISH', 'OUTSIDE_REQUIRED')) for b in blockers)
    # Absence of blockers alone cannot prove the exact new entry chain. ALLOW
    # requires a genuinely emitted matching source signal at this cutoff.
    matches = [s for s in engine.signals if s.htf == t['htf'] and s.ltf == t['ltf'] and s.direction == direction
               and s.known_at <= now and abs(s.entry - entry) < 1e-10 and s.signal_id not in engine._cancelled]
    verdict = 'ALLOW' if matches and not blockers else 'REJECT' if hard else 'WAIT'
    return {'known_at': now, 'source_strategy_would': verdict, 'reasons': blockers or ['EXACT_SOURCE_CHAIN_NOT_PROVEN'],
            'htf_trend': h.trend.value, 'ltf_trend': l.trend.value,
            'order_flow_structure': h.structure, 'liquidity_against': adverse,
            'htf_poi': asdict(h_zone) if h_zone else None, 'ltf_poi': asdict(local_zone) if local_zone else None,
            'bos': l.bos.get(direction), 'new_structure': l.structure, 'conf': conf,
            'pd_ote': {'passed': pd[0], 'ote': pd[1], 'retracement': pd[2]} if pd else 'UNKNOWN_WITHOUT_TYPED_HTF_LEG',
            'fta': [asdict(z) for z in fta], 'old_entry': entry, 'old_stop': stop,
            'stop_behind_local_zone': (sign(direction) * (entry - stop) > 0 and
                                       (stop <= local_zone.low if direction == 'LONG' else stop >= local_zone.high)) if local_zone else 'UNKNOWN',
            'timeframe_scope': 'SECONDARY_CONSERVATIVE_1_TO_15' if t['ltf'] <= 15 else 'ANY_TF_INTERPRETATION',
            'trade_entry_allowed': False}


def detect_symbol(symbol, folder, inputs, code_hash, policy, losses):
    fingerprint = sha256(evidence_json({'code': code_hash, 'inputs': inputs, 'symbol': symbol}).encode()).hexdigest()
    if folder.exists():
        return verify_segment(folder, fingerprint)
    folder.mkdir(parents=True)
    series = {}
    loaded = []
    for tf in (5, 15, 60, 240):
        path = REPO / f'data/history/bybit/{symbol}/{tf}.csv'
        print(f'{symbol} analyze native {tf}m', flush=True)
        raw = read_klines_csv(path)
        if any(r.exchange != 'BYBIT' or r.symbol != symbol or r.interval != str(tf) for r in raw):
            raise ValueError('input identity mismatch')
        cs = [r.to_strategy_candle(tf * 60000) for r in raw]
        if len(cs) != inputs[str(tf)]['candles']:
            raise ValueError('saved input count mismatch')
        if any(int(c.open_time.timestamp()) % (tf * 60) for c in cs):
            raise ValueError('unaligned native candle')
        report = analyze_market(cs, timeframe_minutes=tf)
        ranges = analyze_ranges(cs, report, params=RangeDetectionParams(midpoint_tolerance_fraction=policy['range_midpoint_tolerance'])) if tf != 5 else None
        series[tf] = SourceSeries(symbol, tf, cs, report, ranges)
        loaded.append({'tf': tf, 'candles': len(cs), 'start': cs[0].open_time, 'end': cs[-1].close_time})
    engine = SourceEngine(symbol, series, mappings=tuple(tuple(v) for v in policy['mappings'] + policy['any_tf_mappings']))
    merged = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(s.candles)] for tf, s in series.items()])
    records = [r for r in losses if r['old_trade']['symbol'] == symbol]
    intermediate = load_intermediate(symbol)
    last_log = time.monotonic()
    for now, group in itertools.groupby(merged, key=lambda row: row[0]):
        for _, _, tf, index in group:
            engine.advance(tf, index)
        for record in records:
            for field in ('ready_time', 'entry_interval_start'):
                cutoff = datetime.fromisoformat(record['old_trade'][field])
                if now == cutoff:
                    record['snapshots'][field] = snapshot_old(engine, record, now)
        for row in intermediate:
            for name in ('ready_time', 'entry_interval_start'):
                if now == datetime.fromisoformat(row['old_trade'][name]):
                    row['snapshots'][name] = intermediate_snapshot(engine, row['old_trade'], now)
        if time.monotonic() - last_log > 30:
            print(f'{symbol} observed through {now.isoformat()}; setups={len(engine.setups)} READY={len(engine.signals)}', flush=True)
            last_log = time.monotonic()
    audit_intermediate(engine, intermediate)
    summary = engine.finish()
    summary['loaded'] = loaded
    write_rows(folder / 'signals.jsonl.gz', (asdict(s) for s in engine.signals))
    write_rows(folder / 'cancellations.jsonl.gz', engine.cancellations)
    write_rows(folder / 'setup_outcomes.jsonl.gz', ({'setup_id': s.setup_id, 'htf': s.htf, 'ltf': s.ltf,
               'poi_type': s.poi.kind, 'interaction_at': s.interaction_at, 'stages': sorted(s.stages),
               'latest_reason': s.reason, 'invalidated_at': s.invalidated_at, 'ready_id': s.ready_id} for s in engine.setups))
    write_json(folder / 'summary.json', summary)
    write_json(folder / 'old_loss_audit.json', records)
    write_json(folder / 'intermediate_audit.json', intermediate)
    write_rows(folder / 'flow_history.jsonl.gz', ({'tf': tf, **f} for tf, s in series.items() for f in s.flow_history))
    write_rows(folder / 'range_audit.jsonl.gz', ({'tf': tf, **f} for tf, s in series.items() for f in s.range_audit))
    files = ('intermediate_audit.json', 'flow_history.jsonl.gz', 'range_audit.jsonl.gz', 'signals.jsonl.gz', 'cancellations.jsonl.gz', 'setup_outcomes.jsonl.gz', 'summary.json', 'old_loss_audit.json')
    manifest = {'status': 'COMPLETE', 'fingerprint': fingerprint, 'code_hash': code_hash, 'inputs': inputs,
                'artifacts': {f: digest(folder / f) for f in files}, 'trade_entry_allowed': False}
    write_json(folder / 'manifest.json', manifest)
    print(f'{symbol} COMPLETE: {dict(engine.funnel)}', flush=True)
    return manifest


def stats(trades, equity=()):
    n = len(trades)
    pnl = [t['net_pnl'] for t in trades]
    wins = [v for v in pnl if v > 1e-10]
    losses = [-v for v in pnl if v < -1e-10]
    avg_win = statistics.mean(wins) if wins else None
    avg_loss = statistics.mean(losses) if losses else None
    r = [t['result_R'] for t in trades]
    max_win = max_loss = run_win = run_loss = 0
    for v in pnl:
        run_win = run_win + 1 if v > 1e-10 else 0
        run_loss = run_loss + 1 if v < -1e-10 else 0
        max_win, max_loss = max(max_win, run_win), max(max_loss, run_loss)
    dd = peak = 0.0
    dd_fraction = 0.0
    for row in equity:
        peak = max(peak, row['equity'])
        dd = max(dd, peak - row['equity'])
        dd_fraction = max(dd_fraction, (peak - row['equity']) / peak if peak else 0)
    return {'CLOSED': n, 'Wins': len(wins), 'Losses': len(losses), 'BE': n - len(wins) - len(losses),
            'WinRate': len(wins) / n if n else None, 'ProfitFactor': sum(wins) / sum(losses) if losses else None,
            'Expectancy': statistics.mean(pnl) if n else None, 'AvgR': statistics.mean(r) if r else None,
            'MedianR': statistics.median(r) if r else None, 'AvgWin': avg_win, 'AvgLoss': avg_loss,
            'PayoffRatio': avg_win / avg_loss if avg_win is not None and avg_loss else None,
            'NetPnL': sum(pnl), 'GrossPnL': sum(t['quote_gross_pnl'] for t in trades),
            'GrossAfterSlippageBeforeFees': sum(t['gross_pnl'] for t in trades),
            'MaxDrawdown': dd if equity else None, 'MaxDrawdownFraction': dd_fraction if equity else None,
            'MaxLosingStreak': max_loss, 'MaxWinningStreak': max_win,
            'Fees': sum(t['fees'] for t in trades), 'Slippage': sum(t['slippage'] for t in trades),
            'AvgHoldingSeconds': statistics.mean(t['holding_seconds'] for t in trades) if n else None}


def execute_cases(output, policy):
    signals, cancellation_map = [], defaultdict(list)
    for symbol in policy['symbol_priority']:
        folder = output / 'segments' / symbol
        for row in read_rows(folder / 'signals.jsonl.gz'):
            row['known_at'] = datetime.fromisoformat(row['known_at'])
            row['targets'], row['fractions'] = tuple(row['targets']), tuple(row['fractions'])
            signals.append(SourceSignal(**row))
        for row in read_rows(folder / 'cancellations.jsonl.gz'):
            cancellation_map[row['signal_id']].append(row)
    risk = SourceRiskPolicy(initial_equity=policy['case_reference_equity'], risk_fraction=policy['risk_fraction'],
                            fee_rate=policy['fee_rate'], slippage_fraction=policy['slippage_fraction'])
    results = {}
    candles = {symbol: [r.to_strategy_candle(300000) for r in read_klines_csv(REPO / f'data/history/bybit/{symbol}/5.csv')]
               for symbol in policy['symbol_priority']}
    for label, mappings in [('strict', policy['mappings']), ('any_tf', policy['any_tf_mappings'])]:
        selected = [s for s in signals if [s.htf, s.ltf] in mappings]
        unique, duplicates = deduplicate_cases(selected, policy['symbol_priority'])
        trades, decisions = [], []
        for s in unique:
            case = replay_case(s, candles[s.symbol], cancellation_map[s.signal_id], risk)
            trades.extend(case.trades)
            decisions.extend(case.decisions)
        trades.sort(key=lambda t: (t['entry_interval_start'], t['ready_time'], -t['htf'], t['ltf'],
                                   policy['symbol_priority'].index(t['symbol']), t['signal_id']))
        closed = [t for t in trades if t['status'] == 'CLOSED']
        primary = closed[:policy['primary_closed_count']]
        breakdown = {}
        for dimension in ('direction', 'symbol', 'setup_type', 'poi_type', 'mapping', 'local_poi_type'):
            groups = defaultdict(list)
            for t in primary:
                key = f"{t['htf']}/{t['ltf']}" if dimension == 'mapping' else t['evidence']['ltf_poi']['kind'] if dimension == 'local_poi_type' else t[dimension]
                groups[key].append(t)
            breakdown[dimension] = {key: stats(rows) for key, rows in groups.items()}
        summary = {'status': 'COMPLETE_FULL_NATIVE_DATASET', 'validation_mode': 'SOURCE_TRADE_CASE_VALIDATION',
                   'scope': label, 'READY': len(selected), 'unique_opportunities': len(unique),
                   'duplicates': len(duplicates), 'FILLED': len(trades), 'CLOSED': len(closed),
                   'OPEN_CENSORED': len(trades) - len(closed),
                   'PENDING_CENSORED': sum(r['reason'] == 'PENDING_RIGHT_CENSORED' for r in decisions),
                   'primary_selection': 'FIRST_50_FILLED_CLOSED_BY_ENTRY_CHRONOLOGY',
                   'primary': stats(primary), 'all_closed': stats(closed), 'primary_breakdown': breakdown,
                   'max_post_entry_bar_MAE_R': max((t['max_adverse_excursion_R'] for t in primary), default=None),
                   'admission_decisions': dict(Counter(r['reason'] for r in decisions)),
                   'shared_capital': False, 'trade_entry_allowed': False,
                   'source_certification': 'DECLARED_MACHINE_POLICY_MISSING_ORIGINAL_ADVANCED_PRO_PDFS',
                   'cohort': policy['cohort']}
        if label == 'strict':
            write_rows(output / 'cases.jsonl.gz', trades)
            write_rows(output / 'primary_cases.jsonl.gz', primary)
            write_rows(output / 'case_decisions.jsonl.gz', decisions)
            results = summary
        else:
            write_rows(output / 'any_tf_cases.jsonl.gz', trades)
            write_json(output / 'any_tf_summary.json', summary)
    return results


def execute(output, policy):
    symbols = policy['symbol_priority']
    signals = []
    cancels = []
    funnel = Counter()
    for symbol in symbols:
        folder = output / 'segments' / symbol
        for row in read_rows(folder / 'signals.jsonl.gz'):
            row['known_at'] = datetime.fromisoformat(row['known_at'])
            row['targets'], row['fractions'] = tuple(row['targets']), tuple(row['fractions'])
            signals.append(SourceSignal(**row))
        cancels.extend(read_rows(folder / 'cancellations.jsonl.gz'))
        funnel.update(json.loads((folder / 'summary.json').read_text())['funnel'])
    signals = [s for s in signals if [s.htf, s.ltf] in policy['mappings']]
    signals, duplicates = deduplicate_cases(signals, symbols)
    write_rows(output / 'duplicate_opportunities.jsonl.gz', duplicates)
    signals.sort(key=lambda s: (s.known_at, -s.htf, s.ltf, symbols.index(s.symbol), s.signal_id))
    cancels.sort(key=lambda c: (c['known_at'], c['signal_id']))
    portfolio = SourcePortfolio(SourceRiskPolicy(initial_equity=policy['initial_equity'], risk_fraction=policy['risk_fraction'],
                                                  fee_rate=policy['fee_rate'], slippage_fraction=policy['slippage_fraction']))
    streams = []
    for rank, symbol in enumerate(symbols):
        cs = [r.to_strategy_candle(300000) for r in read_klines_csv(REPO / f'data/history/bybit/{symbol}/5.csv')]
        streams.append([(c.open_time, rank, symbol, c) for c in cs])
    events = heapq.merge(*streams)
    i = j = 0
    last_mark_time = None
    for opened, group in itertools.groupby(events, key=lambda row: row[0]):
        while j < len(cancels) and datetime.fromisoformat(cancels[j]['known_at']) <= opened:
            c = cancels[j]
            portfolio.cancel(c['signal_id'], datetime.fromisoformat(c['known_at']), c['reason'])
            j += 1
        while i < len(signals) and signals[i].known_at <= opened:
            # If the signal was already cancelled by this OPEN, it is unavailable.
            cancelled = any(c['signal_id'] == signals[i].signal_id for c in cancels[:j])
            if not cancelled:
                portfolio.offer(signals[i])
            i += 1
        for _, _, symbol, candle in group:
            portfolio.on_bar(symbol, candle)
            last_mark_time = candle.close_time
        portfolio.mark(last_mark_time)
    closed = [t for t in portfolio.trades if t['status'] == 'CLOSED']
    primary = closed[:policy['primary_closed_count']]
    primary_end = primary[-1]['exit_time'] if primary else None
    primary_equity = [{'equity': policy['initial_equity'], 'known_at': streams[0][0][0]}] + [r for r in portfolio.equity if primary_end is None or r['known_at'] <= primary_end]
    breakdown = {}
    for dimension in ('direction', 'symbol', 'setup_type', 'poi_type', 'mapping'):
        groups = defaultdict(list)
        for t in primary:
            key = f"{t['htf']}/{t['ltf']}" if dimension == 'mapping' else t[dimension]
            groups[key].append(t)
        breakdown[dimension] = {key: stats(rows) for key, rows in groups.items()}
    funnel['entries'] = len(portfolio.trades)
    funnel['CLOSED'] = len(closed)
    funnel['open_censored'] = len(portfolio.trades) - len(closed)
    funnel['pending_censored'] = int(portfolio.pending is not None)
    summary = {'status': 'COMPLETE_FULL_NATIVE_DATASET', 'funnel': dict(funnel), 'primary': stats(primary, primary_equity),
               'all_closed': stats(closed, [{'equity': policy['initial_equity']}] + portfolio.equity),
               'primary_breakdown': breakdown, 'admission_decisions': dict(Counter(r['reason'] for r in portfolio.decisions)),
               'primary_selection': 'PORTFOLIO_SIMULATION_SEPARATE_FROM_PRIMARY_CASES',
               'mode': 'BACKTEST', 'trade_entry_allowed': False, 'one_position': True,
               'initial_equity': policy['initial_equity'], 'final_cash': portfolio.cash,
               'final_equity': portfolio.equity[-1]['equity'] if portfolio.equity else policy['initial_equity'],
               'funding': 'UNAVAILABLE_NOT_MODELLED', 'cohort': policy['cohort']}
    write_rows(output / 'trades.jsonl.gz', portfolio.trades)
    write_rows(output / 'primary_trades.jsonl.gz', primary)
    write_rows(output / 'decisions.jsonl.gz', portfolio.decisions)
    write_rows(output / 'equity.jsonl.gz', portfolio.equity)
    write_json(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume-existing', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not args.resume_existing:
        raise ValueError('existing output requires verified --resume-existing')
    policy = json.loads(POLICY.read_text())
    if policy['trade_entry_allowed'] is not False or policy['mode'] not in ('BACKTEST', 'SHADOW'):
        raise ValueError('unsafe replay policy')
    if policy['mappings'] != [[15, 5], [60, 5], [60, 15], [240, 5], [240, 15]] or policy['any_tf_mappings'] != [[240, 60]]:
        raise ValueError('registered mappings differ')
    receipt = json.loads(DATA_RECEIPT.read_text())
    inputs = {}
    for row in receipt['native_bybit_series']:
        if digest(REPO / row['path']) != row['sha256']:
            raise ValueError('stored Bybit input SHA mismatch')
        inputs[row['path']] = row
    expected = {f'data/history/bybit/{symbol}/{tf}.csv' for symbol in policy['symbol_priority'] for tf in (5, 15, 60, 240)}
    if set(inputs) != expected or len(inputs) != 40 or sum(v['candles'] for v in inputs.values()) != 993575:
        raise ValueError('the entire registered40-series dataset is required')
    code = {name: digest(REPO / name) for name in IMPLEMENTATION}
    code_hash = sha256(evidence_json(code).encode()).hexdigest()
    request = {'implementation': code, 'inputs': inputs, 'policy': policy, 'trade_entry_allowed': False}
    request_path = output / 'run_lock.json'
    if request_path.exists() and json.loads(request_path.read_text()) != request:
        raise ValueError('run lock differs; retain old run and use fresh output')
    final_manifest = output / 'manifest.json'
    if final_manifest.exists():
        final = json.loads(final_manifest.read_text())
        names = {'case_summary.json', 'cases.jsonl.gz', 'primary_cases.jsonl.gz', 'case_decisions.jsonl.gz', 'any_tf_cases.jsonl.gz', 'any_tf_summary.json', 'duplicate_opportunities.jsonl.gz', 'run_lock.json', 'summary.json', 'trades.jsonl.gz', 'primary_trades.jsonl.gz', 'decisions.jsonl.gz', 'equity.jsonl.gz'}
        if final.get('status') != 'COMPLETE' or final.get('code_hash') != code_hash or set(final['artifacts']) != names:
            raise ValueError('completed run manifest mismatch')
        for name, checksum in final['artifacts'].items():
            if digest(output / name) != checksum:
                raise ValueError('completed run artifact corruption: ' + name)
        for symbol in policy['symbol_priority']:
            symbol_inputs = {str(tf): inputs[f'data/history/bybit/{symbol}/{tf}.csv'] for tf in (5, 15, 60, 240)}
            fingerprint = sha256(evidence_json({'code': code_hash, 'inputs': symbol_inputs, 'symbol': symbol}).encode()).hexdigest()
            verify_segment(output / 'segments' / symbol, fingerprint)
        print(json.dumps({'resume': 'VERIFIED_COMPLETE_NO_MUTATION', 'segments': len(policy['symbol_priority']),
                          'summary': json.loads((output / 'summary.json').read_text()), 'trade_entry_allowed': False}, indent=2))
        return
    output.mkdir(parents=True, exist_ok=True)
    write_json(request_path, request)
    losses = old_losses()
    for symbol in policy['symbol_priority']:
        symbol_inputs = {str(tf): inputs[f'data/history/bybit/{symbol}/{tf}.csv'] for tf in (5, 15, 60, 240)}
        detect_symbol(symbol, output / 'segments' / symbol, symbol_inputs, code_hash, policy, losses)
    case_summary = execute_cases(output, policy)
    summary = execute(output, policy)
    write_json(output / 'case_summary.json', case_summary)
    files = ['case_summary.json', 'cases.jsonl.gz', 'primary_cases.jsonl.gz', 'case_decisions.jsonl.gz', 'any_tf_cases.jsonl.gz', 'any_tf_summary.json', 'duplicate_opportunities.jsonl.gz', 'run_lock.json', 'summary.json', 'trades.jsonl.gz', 'primary_trades.jsonl.gz', 'decisions.jsonl.gz', 'equity.jsonl.gz']
    write_json(output / 'manifest.json', {'status': 'COMPLETE', 'code_hash': code_hash,
                                        'artifacts': {f: digest(output / f) for f in files}, 'trade_entry_allowed': False})
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
