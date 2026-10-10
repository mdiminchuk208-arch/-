"""Read-only real native prefix, future mutation, physical union and cost QA."""
from __future__ import annotations

import argparse
import gzip
import heapq
import itertools
import json
import math
import sys
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_pdf_native import evidence_json, sign
from crypto_bot.strategy.source_permitted import (
    SourceEngine,
    SourceSeries,
    select_union,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_permitted_bybit import (
    case_stats,
    digest,
    instant,
    read_rows,
    verify_manifest,
    write_json,
)
from verify_source_pdf_native_evidence import timestamp_check
from verify_source_pdf_preservation import retained
from verify_source_pdf_preservation import verify as verify_preserved

REPO = Path(__file__).resolve().parents[1]


def build_prefix(policy, cutoff, symbol, mutate=False):
    series, total = {}, 0
    for tf in policy['native_timeframes']:
        all_candles = [r.to_strategy_candle(tf * 60000) for r in
                       read_klines_csv(REPO / f'data/history/bybit/{symbol}/{tf}.csv')]
        cs = [c for c in all_candles if c.close_time <= cutoff]
        total += len(cs)
        if mutate:
            cs += [replace(c, open=c.open * 2, high=c.high * 2, low=c.low * .5, close=c.close * 2)
                   for c in all_candles if c.close_time > cutoff][:8]
        market = analyze_market(cs, timeframe_minutes=tf)
        ranges = analyze_ranges(cs, market, params=RangeDetectionParams(
            midpoint_tolerance_fraction=policy['range_midpoint_tolerance'])) if tf != 5 else None
        series[tf] = SourceSeries(symbol, tf, cs, market, ranges)
    engine = SourceEngine(symbol, series, policy)
    clock = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(s.candles)
                          if c.close_time <= cutoff] for tf, s in series.items()])
    for now, group in itertools.groupby(clock, key=lambda r: r[0]):
        changed = set()
        for _, _, tf, index in group:
            engine.advance(tf, index)
            changed.add(tf)
        engine.evaluate(now, changed)
    return engine, total


def flow_rows(engine):
    return [{'tf': tf, **f} for tf, s in engine.series.items() for f in s.flow_history]


def observed_prefix(engine):
    return {'signals':[asdict(s) for s in engine.signals], 'cancellations':engine.cancellations,
            'exit_events':engine.exit_events, 'attempts':engine.attempts,
            'flow_history':flow_rows(engine),
            'range_audit':[{'tf':tf,**r} for tf,s in engine.series.items() for r in s.range_audit],
            'flow_bottleneck':[{'tf':tf,**r} for tf,s in engine.series.items() for r in s.flow_audit]}


def prefix_checks(folder, cutoff, symbol, cache=None, build_only=False):
    policy = json.loads((folder / 'run_lock.json').read_text())['policy']
    if cache is not None and cache.exists() and not build_only:
        with gzip.open(cache,'rt') as f: saved=json.load(f)
        assert saved['run_lock_sha256']==digest(folder/'run_lock.json')
        assert saved['symbol']==symbol and saved['cutoff']==cutoff.isoformat()
        for name,observed in saved['observations'].items():
            full=[r for r in read_rows(folder/'segments'/symbol/f'{name}.jsonl.gz')
                  if instant(r['known_at'])<=cutoff]
            if name=='flow_history':
                for r in full:
                    if r['invalidated_at'] and instant(r['invalidated_at'])>cutoff:
                        r['invalidated_at']=None;r.pop('invalidation_reason',None)
            assert evidence_json(full)==evidence_json(observed),('cached full/prefix mismatch',name)
        return {**saved['receipt'],'full_history_prefix_parity':'PASS','cache_sha256':digest(cache)}
    clean, total = build_prefix(policy, cutoff, symbol)
    altered, _ = build_prefix(policy, cutoff, symbol, True)
    segment = folder / 'segments' / symbol
    if not build_only:
        for name,observed in observed_prefix(clean).items():
            full=[r for r in read_rows(segment/f'{name}.jsonl.gz') if instant(r['known_at'])<=cutoff]
            if name=='flow_history':
                for r in full:
                    if r['invalidated_at'] and instant(r['invalidated_at'])>cutoff:
                        r['invalidated_at']=None;r.pop('invalidation_reason',None)
            assert evidence_json(full)==evidence_json(observed),('full/prefix mismatch',name)
    # Future metadata can exist in the precomputed reports; it cannot affect a
    # single prefix decision, state, quote, cancellation, zone, pool or ATR value.
    assert clean.signals, 'real prefix must be nonempty'
    assert evidence_json(observed_prefix(clean))==evidence_json(observed_prefix(altered))
    assert evidence_json(clean.finish())==evidence_json(altered.finish())
    for tf,a in clean.series.items():
        b=altered.series[tf]
        assert a.pools==b.pools and a.counts==b.counts and a.atr_values==b.atr_values
        assert evidence_json(a.structural_key_history)==evidence_json(b.structural_key_history)
        assert evidence_json([asdict(z) for z in a.zones])==evidence_json([asdict(z) for z in b.zones])
    receipt={'status':'PASS','symbol':symbol,'fixed_cutoff':cutoff.isoformat(),
             'native_prefix_candles':total,'exact_READY':len(clean.signals),
             'paths_nonempty':dict(Counter(s.evidence['path_id'] for s in clean.signals)),
             'exact_cancellations':len(clean.cancellations),'exact_global_flows':len(flow_rows(clean)),
             'native_TFs':policy['native_timeframes'],'future_mutation':'PASS',
             'full_history_prefix_parity':'PENDING_FULL_SEGMENT' if build_only else 'PASS',
             'cohort':'ALREADY_INSPECTED_DEVELOPMENT','trade_entry_allowed':False}
    if cache is not None:
        payload=evidence_json({'run_lock_sha256':digest(folder/'run_lock.json'),'symbol':symbol,
                              'cutoff':cutoff.isoformat(),'observations':observed_prefix(clean),'receipt':receipt})
        cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_bytes(gzip.compress(payload.encode(),mtime=0))
    return receipt


def ledger_checks(folder):
    verify_manifest(folder)
    lock = json.loads((folder / 'run_lock.json').read_text()); policy = lock['policy']
    assert policy['trade_entry_allowed'] is False
    for name, h in lock['implementation'].items():
        assert digest(REPO / name) == h, name
    for name, row in lock['inputs'].items():
        assert digest(REPO / name) == row['sha256'], name
    signals, by_symbol, cancels = {}, defaultdict(list), defaultdict(list)
    prices, opens, closes = {}, {}, {}
    for symbol in policy['symbol_priority']:
        prices[symbol] = [r.to_strategy_candle(300000) for r in
                          read_klines_csv(REPO / f'data/history/bybit/{symbol}/5.csv')]
        opens[symbol] = [c.open_time for c in prices[symbol]]
        closes[symbol] = [c.close_time for c in prices[symbol]]
        segment = folder / 'segments' / symbol
        for r in read_rows(segment / 'cancellations.jsonl.gz'):
            cancels[(r['signal_id'], r['cohort'])].append(r)
        for r in read_rows(segment / 'signals.jsonl.gz'):
            assert r['signal_id'] not in signals
            signals[r['signal_id']] = r; by_symbol[symbol].append(r)
            ready = instant(r['known_at']); e = r['evidence']; s = sign(r['direction'])
            timestamp_check(e, ready)
            assert r['trade_entry_allowed'] is False
            assert s * (r['entry'] - r['stop']) > 0 and s * (r['targets'][0] - r['entry']) > 0
            assert math.isclose(sum(r['fractions']), 1.)
            assert e['order_flow']['direction'] == r['direction']
            assert e['order_flow']['invalidated_at'] is None
            assert e['ltf_poi']['invalidated_at'] is None
            for target in (e['fta'], e['order_flow'].get('destination_poi', {})):
                if not target.get('zone_id'): continue
                assert target['first_test'] is None
                lo = bisect_left(opens[symbol], instant(target['known_at']))
                hi = bisect_right(closes[symbol], ready)
                assert not any(c.low <= target['high'] and c.high >= target['low']
                               for c in prices[symbol][lo:hi]), ('target tested before READY', r['signal_id'])
            path = e['path_id']
            if path in ('DEMAND_SUPPLY', 'STB_BTS_EDGE', 'STB_BTS_HALF'):
                assert e['premium_discount']['allowed'] is True
            if path.startswith('OB_DIRECT'):
                q = e['ltf_poi']; assert q['kind'] == 'ORDER_BLOCK'
                assert q['structural_proof']['kind'].endswith('STRUCTURE_BROKEN_BOS')
                assert q['raid']['candle_index'] == q['origin_index']
            if path == 'OB_ULTRA_CONSERVATIVE_CONF':
                p = e['confirmations']
                assert instant(p['bos']['known_at']) < instant(p['new_structure']['known_at']) <= instant(p['conf']['known_at']) <= ready
            if path.startswith('SFP'):
                assert e['thesis_tf'] == r['ltf']
                assert e['htf_poi']['kind'] == 'SFP'
            if path.startswith('RANGE'):
                assert r['fractions'] == [.8, .2]
            current_index = bisect_right(closes[symbol], ready) - 1
            assert closes[symbol][current_index] == ready
    selected = read_rows(folder / 'selections/SOURCE_PERMITTED_UNION.jsonl.gz')
    assert len({r['physical_opportunity_id'] for r in selected}) == len(selected)
    hydrated = [SourceSignal(**{**r, 'known_at': instant(r['known_at']), 'targets': tuple(r['targets']),
                                'fractions': tuple(r['fractions'])}) for r in signals.values()]
    fresh_selection, _ = select_union(hydrated, policy)
    assert [r['signal_id'] for r in selected] == [s.signal_id for s in fresh_selection]
    selection_receipt = json.loads((folder / 'pre_execution_selection_receipt.json').read_text())
    assert selection_receipt['selection_uses_future_outcomes'] is False
    for name, h in selection_receipt['selection_sha256'].items():assert digest(folder / name) == h
    counts, case_total = {}, 0
    for summary_file in sorted((folder / 'cohorts').glob('*/*/summary.json')):
        cohort = summary_file.parent
        summary = json.loads(summary_file.read_text())
        trades = read_rows(cohort / 'cases.jsonl.gz')
        closed = [t for t in trades if t['status'] == 'CLOSED']
        primary = read_rows(cohort / 'primary_cases.jsonl.gz')
        assert primary == closed[:50]
        assert len({t['physical_opportunity_id'] for t in trades}) == len(trades)
        assert summary['primary'] == case_stats(primary)
        assert summary['all_closed'] == case_stats(closed)
        prior = None
        for t in trades:
            case_total += 1
            s = sign(t['direction']); ready = instant(t['ready_time']); start = instant(t['entry_interval_start'])
            assert ready <= start and (prior is None or prior <= start)
            prior = start
            assert t['signal_id'] in signals and t['trade_entry_allowed'] is False
            assert not any(instant(r['known_at']) <= start for r in cancels[(t['signal_id'], t['cancellation_cohort'])])
            cs = prices[t['symbol']]; i = bisect_left(opens[t['symbol']], start); c = cs[i]
            assert c.low <= t['entry_reference'] if s == 1 else c.high >= t['entry_reference']
            assert t['entry_bar_ohlc'] == {k: getattr(c, k) for k in ('open', 'high', 'low', 'close')}
            assert math.isclose(t['risk_amount'], 23.4, abs_tol=1e-9)
            assert math.isclose(t['initial_equity'], 1170., abs_tol=1e-9)
            assert math.isclose(t['entry'], t['entry_reference'] * (1 + s * policy['slippage_fraction']))
            stop_fill = t['stop'] * (1 - s * policy['slippage_fraction'])
            unit_risk = s * (t['entry'] - stop_fill) + policy['fee_rate'] * (t['entry'] + stop_fill)
            assert math.isclose(unit_risk * t['quantity'], 23.4, abs_tol=1e-8)
            fees = t['quantity'] * t['entry'] * policy['fee_rate']
            slip = t['quantity'] * abs(t['entry'] - t['entry_reference']); gross = quote_gross = 0.
            for f in t['fills']:
                assert instant(f['known_at']) >= instant(t['entry_interval_end'])
                assert math.isclose(f['price'], f['reference'] * (1 - s * policy['slippage_fraction']))
                assert math.isclose(f['exit_fee'], f['quantity'] * f['price'] * policy['fee_rate'])
                fees += f['exit_fee']; slip += f['quantity'] * abs(f['price'] - f['reference'])
                gross += s * (f['price'] - t['entry']) * f['quantity']
                quote_gross += s * (f['reference'] - t['entry_reference']) * f['quantity']
            for actual, expected in ((t['fees'], fees), (t['slippage'], slip), (t['gross_pnl'], gross),
                                     (t['quote_gross_pnl'], quote_gross), (t['net_pnl'], gross - fees)):
                assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8)
            if t['status'] == 'CLOSED':
                assert math.isclose(t['result_R'], t['net_pnl'] / 23.4)
                assert t['result'] == ('WIN' if t['net_pnl'] > 1e-10 else 'LOSS' if t['net_pnl'] < -1e-10 else 'BE')
            if t['path_id'] == 'RANGE_AGGRESSIVE_EXTERNAL_POI':
                assert t['evidence']['actual_range_deviation_at_fill']['known_at'] == t['entry_interval_end']
        counts[str(cohort.relative_to(folder))] = {'FILLED': len(trades), 'CLOSED': len(closed)}
    return {'status': 'PASS', 'READY_raw_variants': len(signals), 'physical_union_READY': len(selected),
            'cohort_case_instances_audited': case_total, 'cohorts': counts,
            'native_identity_cost_risk_prefix_selection_cancellation': 'PASS', 'trade_entry_allowed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prefix-only', action='store_true'); p.add_argument('--ledger-only', action='store_true')
    p.add_argument('--symbol', default='SOLUSDT')
    p.add_argument('--cutoff', default='2026-03-01T00:00:00+00:00')
    p.add_argument('--prefix-cache',type=Path)
    p.add_argument('--build-prefix-only',action='store_true')
    a = p.parse_args(); result = {'trade_entry_allowed': False}
    if not a.ledger_only: result['real_prefix'] = prefix_checks(a.folder, instant(a.cutoff), a.symbol,
                                                              a.prefix_cache,a.build_prefix_only)
    if not a.prefix_only and not a.build_prefix_only:
        result['ledger'] = ledger_checks(a.folder)
        result['preservation'] = verify_preserved()
        result['retained_d46646f'] = retained('d46646f', ('src/', 'config/', 'tests/', 'scripts/', 'data/'))
    write_json(a.output, result); print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
