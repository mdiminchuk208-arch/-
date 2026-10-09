"""Read-only native prefix/future-mutation and independent-case ledger audit."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import heapq
import itertools
import json
from pathlib import Path
import sys

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_pdf_native import SourceEngine, SourceSeries, evidence_json, sign
from crypto_bot.strategy.source_pdf_cases import deduplicate_cases, opportunity_key, same_opportunity
from crypto_bot.strategy.source_engine import SourceSignal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_pdf_native_bybit import digest, read_rows, stats, write_json

REPO = Path(__file__).resolve().parents[1]


def timestamp_check(value, cutoff):
    if isinstance(value, dict):
        for key, child in value.items():
            if (key.endswith('_at') or key in ('first_test', 'last_test', 'deviation_open')) and isinstance(child, str):
                assert datetime.fromisoformat(child) <= cutoff, (key, child, cutoff)
            timestamp_check(child, cutoff)
    elif isinstance(value, list):
        for child in value:
            timestamp_check(child, cutoff)


def prefix_engine(policy, cutoff, mutate, symbol="BTCUSDT"):
    series, total = {}, 0
    for tf in (5, 15, 60, 240):
        all_cs = [r.to_strategy_candle(tf * 60000) for r in read_klines_csv(REPO / f'data/history/bybit/{symbol}/{tf}.csv')]
        cs = [c for c in all_cs if c.close_time <= cutoff]
        total += len(cs)
        if mutate:
            tail = [c for c in all_cs if c.close_time > cutoff][:8]
            cs += [replace(c, open=c.open * 2, high=c.high * 2, low=c.low * .5, close=c.close * 2) for c in tail]
        analysis = analyze_market(cs, timeframe_minutes=tf)
        ranges = analyze_ranges(cs, analysis, params=RangeDetectionParams(midpoint_tolerance_fraction=policy['range_midpoint_tolerance'])) if tf != 5 else None
        series[tf] = SourceSeries(symbol, tf, cs, analysis, ranges)
    mappings = tuple(tuple(v) for v in policy['mappings'] + policy['any_tf_mappings'])
    engine = SourceEngine(symbol, series, mappings=mappings)
    events = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(s.candles) if c.close_time <= cutoff]
                          for tf, s in series.items()])
    for _, group in itertools.groupby(events, key=lambda r: r[0]):
        for _, _, tf, index in group:
            engine.advance(tf, index)
    return engine, total


def flows(engine):
    return [{'tf': tf, **f} for tf, s in engine.series.items() for f in s.flow_history]


def verify_prefix(folder, cutoff=None, symbol="BTCUSDT"):
    cutoff = cutoff or datetime(2026, 3, 1, tzinfo=timezone.utc)
    policy = json.loads((folder / 'run_lock.json').read_text())['policy']
    clean, total = prefix_engine(policy, cutoff, False, symbol)
    mutated, _ = prefix_engine(policy, cutoff, True, symbol)
    saved = folder / 'segments' / symbol
    full_signals = [r for r in read_rows(saved / 'signals.jsonl.gz') if datetime.fromisoformat(r['known_at']) <= cutoff]
    full_cancels = [r for r in read_rows(saved / 'cancellations.jsonl.gz') if datetime.fromisoformat(r['known_at']) <= cutoff]
    assert evidence_json(full_signals) == evidence_json([asdict(s) for s in clean.signals])
    assert evidence_json(full_cancels) == evidence_json(clean.cancellations)
    full_flows = [r for r in read_rows(saved / 'flow_history.jsonl.gz') if datetime.fromisoformat(r['known_at']) <= cutoff]
    for r in full_flows:
        if r['invalidated_at'] and datetime.fromisoformat(r['invalidated_at']) > cutoff:
            r['invalidated_at'] = None
            r.pop('invalidation_reason', None)
    assert evidence_json(full_flows) == evidence_json(flows(clean)), 'global flow prefix mismatch'
    ranges = [r for r in read_rows(saved / 'range_audit.jsonl.gz') if datetime.fromisoformat(r['known_at']) <= cutoff]
    observed_ranges = [{'tf': tf, **r} for tf, s in clean.series.items() for r in s.range_audit]
    assert evidence_json(ranges) == evidence_json(observed_ranges), 'Range external evidence prefix mismatch'
    assert evidence_json([asdict(s) for s in clean.signals]) == evidence_json([asdict(s) for s in mutated.signals])
    assert evidence_json(clean.cancellations) == evidence_json(mutated.cancellations)
    assert evidence_json(flows(clean)) == evidence_json(flows(mutated))
    for signal in clean.signals:
        if signal.known_at != cutoff:
            continue
        owner = clean.series[signal.htf]
        destination_id = signal.evidence['order_flow']['destination_poi']['zone_id']
        assert owner.zone_registry[destination_id].fresh(cutoff), 'flow destination already tested at READY'
    for tf in clean.series:
        a, b = clean.series[tf], mutated.series[tf]
        assert evidence_json([asdict(z) for z in a.zones]) == evidence_json([asdict(z) for z in b.zones])
        assert evidence_json(a.range_audit) == evidence_json(b.range_audit)
        assert evidence_json(a.structural_key_history) == evidence_json(b.structural_key_history)
        assert a.pools == b.pools and a.counts == b.counts
    return {'status': 'PASS', 'symbol': symbol, 'fixed_cutoff': cutoff.isoformat(), 'native_prefix_candles': total,
            'exact_signals': len(full_signals), 'exact_cancellations': len(full_cancels),
            'exact_global_flows': len(full_flows), 'exact_range_external_audits': len(ranges),
            'future_mutation_4_native_TFs': 'PASS', 'cohort': 'ALREADY_INSPECTED_DEVELOPMENT'}


def verify_ledger(folder):
    lock = json.loads((folder / 'run_lock.json').read_text())
    policy = lock['policy']
    assert policy['trade_entry_allowed'] is False and policy['mode'] in ('BACKTEST', 'SHADOW')
    assert policy['mappings'] == [[15, 5], [60, 5], [60, 15], [240, 5], [240, 15]]
    assert len(lock['inputs']) == 40 and sum(r['candles'] for r in lock['inputs'].values()) == 993575
    signals, cancellations, native_prices = {}, {}, {}
    for segment in (folder / 'segments').iterdir():
        for r in read_rows(segment / 'cancellations.jsonl.gz'):
            cancellations[r['signal_id']] = datetime.fromisoformat(r['known_at'])
        for r in read_rows(segment / 'signals.jsonl.gz'):
            assert r['signal_id'] not in signals
            signals[r['signal_id']] = r
            cutoff = datetime.fromisoformat(r['known_at'])
            e, s = r['evidence'], sign(r['direction'])
            if r['symbol'] not in native_prices:
                native_prices[r['symbol']] = [c.to_strategy_candle(300000) for c in read_klines_csv(REPO / f"data/history/bybit/{r['symbol']}/5.csv")]
            timestamp_check(e, cutoff)
            raid, bos, new, conf = (datetime.fromisoformat(e[k]['known_at']) for k in ('liquidity_sweep', 'bos', 'new_structure', 'conf'))
            assert raid <= bos < new <= conf <= cutoff
            local = e['ltf_poi']
            htf = e['htf_poi']
            if htf['kind'] != 'RANGE_POI':
                assert htf['native_touch_clock'] is True
                assert datetime.fromisoformat(htf['known_at']) < datetime.fromisoformat(e['htf_interaction_at']) <= cutoff
            assert e['fta']['native_touch_clock'] is True
            assert e['fta']['first_test'] is None
            current = next(c for c in read_klines_csv(REPO / f"data/history/bybit/{r['symbol']}/{r['ltf']}.csv")
                           if c.to_strategy_candle(r['ltf'] * 60000).close_time == cutoff)
            assert s * (current.close - r['entry']) > 0 and s * (r['targets'][0] - current.close) > 0
            assert local['structural_proof']['direction'] == r['direction']
            assert bos <= datetime.fromisoformat(local['structural_proof']['known_at']) <= datetime.fromisoformat(local['known_at'])
            flow = e['order_flow']
            assert flow['direction'] == r['direction'] and flow['invalidated_at'] is None
            for target in (e['fta'], flow['destination_poi']):
                available = datetime.fromisoformat(target['known_at'])
                tested = [c for c in native_prices[r['symbol']] if available <= c.open_time and c.close_time <= cutoff
                          and c.low <= target['high'] and c.high >= target['low']]
                assert not tested, ('actual native target tested before READY', r['signal_id'], target['zone_id'])
            keys = flow['sequence']['structural_keys']
            for field in ('protected', 'extreme'):
                assert s * (keys[-1][field] - keys[-2][field]) > 0
            assert e['fta']['direction'] != r['direction']
            assert e['htf_interaction_at'] <= r['known_at']
            if local['kind'] == 'ORDER_BLOCK':
                assert local['low'] <= e['htf_poi']['high'] and local['high'] >= e['htf_poi']['low']
            assert datetime.fromisoformat(flow['liquidity_work']['known_at']) < datetime.fromisoformat(flow['body_break_at']) <= datetime.fromisoformat(flow['known_at']) <= cutoff
            assert flow['destination_poi']['first_test'] is None
            assert not e['meaningful_liquidity_against'] and not any(p['role'] == 'AGAINST_SETUP' for p in e['liquidity_roles'])
            assert e['ltf_poi']['first_test'] is None and e['ltf_poi']['invalidated_at'] is None
            for z in (e['htf_poi'], e['ltf_poi']):
                if z['kind'] == 'ORDER_BLOCK':
                    assert z['raid']['candle_index'] == z['origin_index']
                if z['kind'] in ('DEMAND', 'SUPPLY'):
                    assert z['origin_index'] <= z['raid']['candle_index'] <= z['move_end_index']
            z = e['htf_poi']
            if z['kind'] == 'RANGE_POI':
                assert z['external_poi'] is not None
                assert datetime.fromisoformat(z['external_poi']['known_at']) < datetime.fromisoformat(z['formed_at']) < datetime.fromisoformat(z['range_reclaim_at']) < datetime.fromisoformat(z['range_retest_at']) <= cutoff
            assert r['trade_entry_allowed'] is False
    selected = []
    for r in signals.values():
        if [r['htf'], r['ltf']] in policy['mappings']:
            selected.append(SourceSignal(**{**r, 'known_at': datetime.fromisoformat(r['known_at']),
                                            'targets': tuple(r['targets']), 'fractions': tuple(r['fractions'])}))
    unique, duplicate = deduplicate_cases(selected, policy['symbol_priority'])
    for i, a in enumerate(unique):
        assert all(not same_opportunity(opportunity_key(a), opportunity_key(b)) for b in unique[:i])
    accepted = {s.signal_id for s in unique}
    cases, primary = read_rows(folder / 'cases.jsonl.gz'), read_rows(folder / 'primary_cases.jsonl.gz')
    closed = [t for t in cases if t['status'] == 'CLOSED']
    assert primary == closed[:50]
    assert len({t['trade_id'] for t in cases}) == len(cases)
    previous_entry = None
    for t in cases:
        ready, entry = datetime.fromisoformat(t['ready_time']), datetime.fromisoformat(t['entry_interval_start'])
        assert ready <= entry and t['signal_id'] in accepted and t['ltf'] <= 15
        assert previous_entry is None or entry >= previous_entry
        previous_entry = entry
        assert t['signal_id'] not in cancellations or cancellations[t['signal_id']] > entry
        assert abs(t['risk_amount'] - 23.4) < 1e-9
        assert abs(t['initial_equity'] - 1170) < 1e-9 and t['trade_entry_allowed'] is False
        s = sign(t['direction'])
        stop_fill = t['stop'] * (1 - s * policy['slippage_fraction'])
        unit_risk = s * (t['entry'] - stop_fill) + policy['fee_rate'] * (t['entry'] + stop_fill)
        assert abs(unit_risk * t['quantity'] - t['risk_amount']) < 1e-8
        if t['status'] == 'CLOSED':
            scale = max(1, abs(t['net_pnl']))
            assert abs(t['quote_gross_pnl'] - t['slippage'] - t['fees'] - t['net_pnl']) < scale * 1e-9
            assert abs(t['result_R'] - t['net_pnl'] / t['risk_amount']) < 1e-12
            assert abs(sum(f['quantity'] for f in t['fills']) - t['quantity']) < max(1, t['quantity']) * 1e-10
    summary = json.loads((folder / 'case_summary.json').read_text())
    assert summary['primary'] == stats(primary)
    assert summary['all_closed'] == stats(closed)
    assert summary['CLOSED'] == len(closed) and summary['unique_opportunities'] == len(unique)
    assert summary['READY'] == len(selected) == len(unique) + len(duplicate)
    assert not any('BUSY' in r['reason'] or 'BUDGET' in r['reason'] for r in read_rows(folder / 'case_decisions.jsonl.gz'))
    audits = [r for symbol in policy['symbol_priority'] for r in json.loads((folder / 'segments' / symbol / 'intermediate_audit.json').read_text())]
    assert len(audits) == 13 and all(set(r['snapshots']) == {'ready_time', 'entry_interval_start'} for r in audits)
    ranges = [r for r in audits if r['old_trade']['poi_type'] == 'RANGE_POI' and r['old_trade']['net_pnl'] < 0]
    assert len(ranges) == 5
    return {'status': 'PASS', 'source_ready_timestamp_and_flow_evidence': len(signals),
            'unique_strict_opportunities': len(unique), 'unique_entries': len(cases),
            'full_strict_closed': len(closed), 'primary_closed': len(primary),
            'case_occupancy_independent': True, 'case_budget_independent': True,
            'scope_240_60_excluded': True, 'cost_and_risk_accounting': 'PASS',
            'actual_cost_and_risk_ledger_rows': len(cases),
            'nonempty_execution_cost_risk_validation': 'ACTUAL_NATIVE_CASE_LEDGER' if cases else 'CONSTRUCTED_UNIT_FIXTURES_NOT_HISTORY_PERFORMANCE',
            'intermediate13_exact_cutoff_audits': dict(Counter(r['classification'] for r in audits)),
            'five_old_range_losses_audited': len(ranges), 'trade_entry_allowed': False}


def verify_manifests(folder):
    lock = json.loads((folder / 'run_lock.json').read_text())
    checked = 0
    for path in [folder / 'manifest.json'] + sorted((folder / 'segments').glob('*/manifest.json')):
        manifest = json.loads(path.read_text())
        assert manifest['status'] == 'COMPLETE'
        for name, expected in manifest['artifacts'].items():
            assert digest(path.parent / name) == expected
            checked += 1
    for name, expected in lock['implementation'].items():
        assert digest(REPO / name) == expected
    for name, row in lock['inputs'].items():
        assert digest(REPO / name) == row['sha256']
    return {'status': 'PASS', 'hashed_artifacts': checked, 'native_inputs': len(lock['inputs']),
            'implementation_files': len(lock['implementation'])}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prefix-only', action='store_true')
    p.add_argument('--symbol', default='BTCUSDT')
    p.add_argument('--cutoff', type=datetime.fromisoformat,
                   help='optional event-time cutoff for additional nonempty READY prefix audit')
    args = p.parse_args()
    result = {'real_prefix_future_mutation': verify_prefix(args.input.resolve(), args.cutoff, args.symbol)}
    if not args.prefix_only:
        result.update(ledger=verify_ledger(args.input.resolve()), manifests=verify_manifests(args.input.resolve()))
    result['verification_script_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    write_json(args.output, result)
    print(json.dumps(result, indent=2))
