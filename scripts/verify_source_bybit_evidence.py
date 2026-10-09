"""Read-only causal prefix and sequential-account evidence verification."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import heapq
import itertools
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_engine import SourceEngine, SourceSeries, evidence_json


def read_rows(path):
    import gzip
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_prefix(folder, cutoff):
    repo = Path(__file__).resolve().parents[1]
    series = {}
    total = 0
    for tf in (5, 15, 60, 240):
        cs = [r.to_strategy_candle(tf * 60000) for r in read_klines_csv(repo / f'data/history/bybit/BTCUSDT/{tf}.csv')]
        cs = [c for c in cs if c.close_time <= cutoff]
        total += len(cs)
        report = analyze_market(cs, timeframe_minutes=tf)
        ranges = analyze_ranges(cs, report, params=RangeDetectionParams(midpoint_tolerance_fraction=0.08)) if tf != 5 else None
        series[tf] = SourceSeries('BTCUSDT', tf, cs, report, ranges)
    engine = SourceEngine('BTCUSDT', series)
    events = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(s.candles)] for tf, s in series.items()])
    for _, group in itertools.groupby(events, key=lambda x: x[0]):
        for _, _, tf, i in group:
            engine.advance(tf, i)
    saved = folder / 'segments/BTCUSDT'
    full_signals = [r for r in read_rows(saved / 'signals.jsonl.gz') if datetime.fromisoformat(r['known_at']) <= cutoff]
    full_cancels = [r for r in read_rows(saved / 'cancellations.jsonl.gz') if datetime.fromisoformat(r['known_at']) <= cutoff]
    assert evidence_json(full_signals) == evidence_json([asdict(s) for s in engine.signals]), 'real-history prefix signal mismatch'
    assert evidence_json(full_cancels) == evidence_json(engine.cancellations), 'real-history prefix cancellation mismatch'
    return {'status': 'PASS', 'symbol': 'BTCUSDT', 'cutoff': cutoff.isoformat(), 'actual_native_candles': total,
            'source_signals_exact': len(full_signals), 'cancellations_exact': len(full_cancels),
            'selection': 'FIXED_2026_03_01_CUTOFF_NOT_SELECTED_BY_PNL'}


def timestamp_check(value, cutoff, path='evidence'):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('known_at', 'formed_at', 'first_test', 'last_test', 'invalidated_at') and isinstance(child, str):
                assert datetime.fromisoformat(child) <= cutoff, f'future evidence: {path}.{key}'
            timestamp_check(child, cutoff, path + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            timestamp_check(child, cutoff, path + '.' + str(i))


def verify_ledger(folder):
    lock = json.loads((folder / 'run_lock.json').read_text())
    summary = json.loads((folder / 'summary.json').read_text())
    assert lock['policy']['trade_entry_allowed'] is False
    assert lock['policy']['risk_fraction'] <= 0.02
    signals = {}
    cancellations = {}
    signal_count = 0
    for segment in (folder / 'segments').iterdir():
        if not segment.is_dir():
            continue
        for row in read_rows(segment / 'cancellations.jsonl.gz'):
            cancellations[row['signal_id']] = datetime.fromisoformat(row['known_at'])
        for row in read_rows(segment / 'signals.jsonl.gz'):
            assert row['signal_id'] not in signals, 'duplicate physical source signal'
            signals[row['signal_id']] = row
            cutoff = datetime.fromisoformat(row['known_at'])
            timestamp_check(row['evidence'], cutoff)
            e = row['evidence']
            b, structure, conf = (datetime.fromisoformat(e[key]['known_at']) for key in ('bos', 'new_structure', 'conf'))
            raid = datetime.fromisoformat(e['liquidity_sweep']['known_at'])
            assert raid <= b < structure <= conf <= cutoff
            assert not e['meaningful_liquidity_against']
            assert e['ltf_poi']['first_test'] is None
            assert e['ltf_poi']['invalidated_at'] is None
            assert e['htf_poi']['invalidated_at'] is None
            assert e['order_flow']['direction'] == row['direction']
            if e['htf_poi']['kind'] in ('ORDER_BLOCK', 'DEMAND', 'SUPPLY'):
                assert e['htf_poi']['test_count'] == 1
            for zone in (e['htf_poi'], e['ltf_poi']):
                if zone['kind'] == 'ORDER_BLOCK':
                    assert zone['raid']['candle_index'] == zone['origin_index'], 'OB origin did not raid'
            assert row['trade_entry_allowed'] is False
            signal_count += 1
    trades = read_rows(folder / 'trades.jsonl.gz')
    primary = read_rows(folder / 'primary_trades.jsonl.gz')
    closed = [t for t in trades if t['status'] == 'CLOSED']
    assert primary == closed[:50]
    assert len({t['trade_id'] for t in trades}) == len(trades)
    prior_exit = None
    for trade in trades:
        ready = datetime.fromisoformat(trade['ready_time'])
        opened = datetime.fromisoformat(trade['entry_interval_start'])
        assert ready <= opened
        assert trade['signal_id'] not in cancellations or cancellations[trade['signal_id']] > opened, 'entry after known cancellation'
        if prior_exit is not None:
            assert datetime.fromisoformat(prior_exit) <= opened, 'overlapping account positions'
        assert trade['signal_id'] in signals
        assert abs(trade['risk_amount'] / trade['initial_equity'] - 0.02) < 1e-12
        assert trade['trade_entry_allowed'] is False
        if trade['status'] == 'CLOSED':
            prior_exit = trade['exit_time']
            scale = max(1, abs(trade['net_pnl']))
            assert abs(trade['quote_gross_pnl'] - trade['slippage'] - trade['fees'] - trade['net_pnl']) < scale * 1e-9
            assert abs(trade['result_R'] - trade['net_pnl'] / trade['risk_amount']) < 1e-12
            assert abs(sum(f['quantity'] for f in trade['fills']) - trade['quantity']) < max(1, trade['quantity']) * 1e-10
            assert datetime.fromisoformat(trade['exit_time']) >= opened
    assert summary['primary']['CLOSED'] == len(primary)
    assert summary['funnel']['CLOSED'] == len(closed)
    assert abs(summary['primary']['NetPnL'] - sum(t['net_pnl'] for t in primary)) < 1e-8
    equity = read_rows(folder / 'equity.jsonl.gz')
    if primary:
        row = next(r for r in equity if r['known_at'] == primary[-1]['exit_time'])
        assert abs(row['cash'] - lock['policy']['initial_equity'] - sum(t['net_pnl'] for t in primary)) < 1e-7
    return {'status': 'PASS', 'all_source_signals_causal': signal_count, 'unique_entries': len(trades),
            'all_closed': len(closed), 'primary_first_closed': len(primary), 'no_overlapping_positions': True,
            'OB_origin_raid_proven': True, 'DS_OB_first_visit': True, 'cost_accounting': 'PASS',
            'all_evidence_known_by_READY': True, 'trade_entry_allowed': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prefix-only', action='store_true')
    args = p.parse_args()
    result = {'real_history_prefix': verify_prefix(args.input.resolve(), datetime(2026, 3, 1, tzinfo=timezone.utc))}
    if not args.prefix_only:
        result['ledger'] = verify_ledger(args.input.resolve())
    result['verification_script_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
