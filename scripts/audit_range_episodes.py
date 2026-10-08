"""Causal OHLC traces for every retained range sweep, with stratified samples.

This audit runs the existing detector; it does not inject review PASS or events.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import analyze_ranges
from crypto_bot.strategy.sfp import detect_sfp


def encode(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def job(args):
    symbol, tf, data_root, output, start, end = args
    path = Path(data_root) / symbol / f'{tf}.csv'
    candles = [c for row in read_klines_csv(path)
               if start <= (c := row.to_strategy_candle(tf*60000)).open_time and c.close_time <= end]
    market = analyze_market(candles, timeframe_minutes=tf)
    report = analyze_ranges(candles, market)
    ranges = {r.range_id:r for r in report.ranges}
    counts = Counter()
    samples = []
    traced = Counter()
    with (Path(output) / f'{symbol}_{tf}_episodes.jsonl').open('w') as stream:
        for episode in report.sweep_episodes:
            r = ranges[episode.range_id]
            sweep = candles[episode.sweep_candle_index]
            next_candle = candles[episode.sweep_candle_index+1] if episode.sweep_candle_index+1 < len(candles) else None
            upper = episode.side == 'high'
            reclaimed = sweep.close < episode.boundary_price if upper else sweep.close > episode.boundary_price
            opened_inside = None if next_candle is None else (
                next_candle.open < episode.boundary_price if upper else next_candle.open > episode.boundary_price)
            result = detect_sfp(sweep, next_candle, episode.boundary_price, episode.side) if next_candle else None
            cause = ('DUAL_SIDE_ORDER_UNOBSERVABLE' if episode.status == 'AMBIGUOUS_DUAL_SIDE_SWEEP' else
                     'SWEEP_CLOSE_NOT_INSIDE' if not reclaimed else
                     'RIGHT_CENSORED_NO_NEXT_CANDLE' if next_candle is None else
                     'NEXT_OPEN_NOT_INSIDE' if not opened_inside else
                     'BOUNDARY_CLARITY_'+r.boundary_clarity_review.value
                     if episode.status == 'CLARITY_REVIEW_BLOCKED' else 'SFP_CONFIRMED')
            counts[episode.status] += 1
            record = dict(symbol=symbol, timeframe_minutes=tf, episode=asdict(episode),
                boundary_1_time=r.first_boundary_time, boundary_2_time=r.second_boundary_time,
                boundaries=dict(low=r.lower,high=r.upper), midpoint_reaction_time=r.midpoint_reaction_time,
                clarity=r.boundary_clarity_review.value, final_range_status=r.status.value,
                final_range_status_time=r.status_time,
                trace=dict(BREAKOUT=True,BOUNDARY_INTERACTION=True,RECLAIM=reclaimed,
                           CANDIDATE=bool(result and result.valid),SFP_CONFIRMATION=episode.status=='SFP_FORMED'),
                first_rejection=cause, source_pattern_valid=bool(result and result.valid),
                before=asdict(candles[episode.sweep_candle_index-1]) if episode.sweep_candle_index else None,
                sweep=asdict(sweep), next_candle=asdict(next_candle) if next_candle else None,
                note='Formation resolves at next OPEN; later close/invalidation cannot change its formation result.')
            stream.write(json.dumps(record,default=encode,sort_keys=True)+'\n')
            # Each symbol/TF contributes up to five examples per outcome, rather than
            # selecting only conveniently successful episodes.
            if traced[episode.status] < 5:
                samples.append(record)
                traced[episode.status] += 1
    print(symbol,tf,len(candles),'candles;',len(report.sweep_episodes),'episodes;',dict(counts),flush=True)
    return dict(series=f'{symbol}/{tf}',candles=len(candles),source=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
                start=candles[0].open_time if candles else None,end=candles[-1].close_time if candles else None,
                candidates=len(report.ranges),ranges=dict(Counter(r.status.value for r in report.ranges)),
                episodes=len(report.sweep_episodes),episode_statuses=dict(counts),
                sfp_events=report.sfp_formation_count,samples=samples)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,default=Path('data/reports/continuation_validation/baseline/baseline_60_5/summary.json'))
    parser.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error('workers must be 1-4')
    args.output.mkdir(parents=True,exist_ok=False)
    summary=json.loads(args.summary.read_text())
    start,end=(datetime.fromisoformat(summary[k]) for k in ('warmup_start','execution_end'))
    jobs=[(s,tf,str(args.data_root),str(args.output),start,end) for s in summary['symbols']
          for tf in (summary['ltf_minutes'],summary['htf_minutes'])]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(job,jobs))
    # Preserve every stratified example (at least 200 if the data contain enough).
    samples=[row for result in results for row in result.pop('samples')]
    counts=Counter()
    for result in results:
        counts.update(result['episode_statuses'])
    output=dict(series=results,episodes=sum(r['episodes'] for r in results),episode_statuses=dict(counts),
                sfp_events=sum(r['sfp_events'] for r in results),sample_count=len(samples))
    for name,data in [('summary.json',output),('stratified_trace_samples.json',samples)]:
        (args.output/name).write_text(json.dumps(data,default=encode,indent=2,sort_keys=True)+'\n')
    print('All episodes accounted for:',output['episodes'],'samples:',len(samples),flush=True)


if __name__=='__main__':
    main()
