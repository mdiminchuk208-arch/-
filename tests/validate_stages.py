"""Reproduce full closed-OHLC structure and unreviewed Range diagnostics.

Default scope is the retained original 60m/5m baseline, including warmup.
"""
from pathlib import Path
from datetime import datetime
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
import argparse
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import analyze_ranges

def job(args):
 symbol,tf,start,end,data_root=args
 candles=[row.to_strategy_candle(tf*60000) for row in read_klines_csv(Path(data_root)/symbol/f'{tf}.csv')]
 candles=[c for c in candles if c.open_time>=start and c.close_time<=end]
 market=analyze_market(candles,timeframe_minutes=tf)
 ranges=analyze_ranges(candles,market)
 return f'{symbol}/{tf}',dict(candles=len(candles),structural_levels=len(market.levels),market_events=dict(Counter(e.kind.value for e in market.events)),structure_transitions=len(market.structure_transition_diagnostics),range_candidates=len(ranges.ranges),range_statuses=dict(Counter(r.status.value for r in ranges.ranges)),range_episodes=len(ranges.sweep_episodes),range_episode_statuses=dict(Counter(e.status for e in ranges.sweep_episodes)),range_events=len(ranges.events))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--summary',type=Path,default=Path('data/reports/continuation_validation/baseline/baseline_60_5/summary.json'))
 parser.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
 parser.add_argument('--output',type=Path,default=Path('data/reports/continuation_validation/baseline_stages.json'))
 parser.add_argument('--workers',type=int,default=4)
 config=parser.parse_args()
 if not 1<=config.workers<=4:parser.error('workers must be 1-4')
 summary=json.loads(config.summary.read_text())
 start,end=[datetime.fromisoformat(summary[k]) for k in ('warmup_start','execution_end')]
 results={}
 with ProcessPoolExecutor(max_workers=config.workers) as pool:
  for k,v in pool.map(job,[(symbol,tf,start,end,config.data_root) for symbol in summary['symbols'] for tf in (summary['ltf_minutes'],summary['htf_minutes'])]):
   results[k]=v;print(k,'bars',v['candles'],'ranges',v['range_candidates'],flush=True)
 config.output.parent.mkdir(parents=True,exist_ok=True)
 config.output.write_text(json.dumps({'scope':'FULL_ANALYSIS_INCLUDING_WARMUP_RANGE_REVIEW_UNREVIEWED','series':results},indent=2,sort_keys=True)+'\n')
