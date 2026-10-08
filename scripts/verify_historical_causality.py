"""Positive real-signal prefix/reference/future-mutation and restart evidence.

Selects actual filled LONG/SHORT signals from completed reports, never fabricated
signals. Original OHLC is retained; only an explicitly labelled future-mutation
experiment changes prices after the tested cutoff. It cannot qualify a past entry.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.replay import evaluate_snapshot
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio
from run_historical_portfolio import canonical, encode, simulate


def check(task,data_root):
    summary,trade,signal=task;symbol=trade['symbol'];htf,ltf=summary['htf_minutes'],summary['ltf_minutes']
    start=datetime.fromisoformat(summary['warmup_start']);cutoff=datetime.fromisoformat(signal['event_time'])
    end=min(datetime.fromisoformat(summary['execution_end']),
            datetime.fromisoformat(trade.get('exit_time',trade['entry_time']))+timedelta(days=1))
    data={tf:[c for row in read_klines_csv(data_root/symbol/f'{tf}.csv')
              if start<=(c:=row.to_strategy_candle(tf*60000)).open_time and c.close_time<=end]
          for tf in (htf,ltf)}
    prefix={tf:[c for c in cs if c.close_time<=cutoff] for tf,cs in data.items()}
    future={tf:[replace(c,open=c.open*1.7,high=c.high*1.7,low=c.low*1.7,close=c.close*1.7)
                if c.close_time>cutoff else c for c in cs] for tf,cs in data.items()}
    past=[];full_updates=()
    for name,sample in [('actual',data),('prefix',prefix),('future_mutation',future)]:
        updates,_=indexed_signal_updates(sample,symbol=symbol,htf_minutes=htf,ltf_minutes=ltf,
                                         mode=summary['mode'],auto_level_policy=AutoLevelPolicy())
        if name=='actual':full_updates=updates
        rows=tuple(s for s in updates if s.event_time<=cutoff);past.append(rows)
        print(symbol,trade['direction'],name,'observed',len(rows),'past states',flush=True)
    assert past[0]==past[1]==past[2]
    ready=next(s for s in past[0] if s.signal_id==trade['signal_id'] and s.event_time==cutoff)
    assert ready.status=='READY_FOR_VIRTUAL_ENTRY'
    assert json.loads(canonical({**asdict(ready),'direction':ready.direction.name}))==signal
    snap=evaluate_snapshot(data,symbol=symbol,as_of=cutoff,htf_minutes=htf,ltf_minutes=ltf,
                           mode=summary['mode'],auto_level_policy=AutoLevelPolicy())
    assert next(s for s in snap.signals if s.signal_id==ready.signal_id)==ready
    execution={symbol:[c for c in data[ltf] if c.open_time>=datetime.fromisoformat(summary['execution_start'])]}
    complete,_=simulate(execution,full_updates,initial_capital=summary['initial_capital'],mode=summary['mode'])
    entry_open=datetime.fromisoformat(trade['entry_interval_start'])
    before=next(i for i,c in enumerate(execution[symbol]) if c.open_time==entry_open)
    with tempfile.TemporaryDirectory() as directory:
        for cut in (before,before+1):
            path=Path(directory)/'state.json'
            partial,_=simulate(execution,full_updates,initial_capital=summary['initial_capital'],
                mode=summary['mode'],checkpoint_path=path,stop_after_bars=cut)
            if cut==before:assert ready.signal_id in partial.pending
            restored=VirtualPortfolio.load_checkpoint(path)
            resumed,_=simulate(execution,full_updates,initial_capital=summary['initial_capital'],
                mode=summary['mode'],portfolio=restored)
            assert complete.snapshot()==resumed.snapshot()
    assert complete.trades[ready.signal_id]['status']=='CLOSED'
    return dict(symbol=symbol,direction=trade['direction'],htf=htf,ltf=ltf,signal_id=ready.signal_id,
                cutoff=cutoff,past_states=len(past[0]),prefix='PASS',future_mutation='PASS',
                independent_snapshot='PASS',actual_ready_signal_match='PASS',
                real_pending_and_filled_checkpoint_resume='PASS',trade_entry_allowed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',type=Path,nargs='+',required=True)
    p.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();selected={}
    for root in args.runs:
        summary=json.loads((root/'summary.json').read_text())
        signals=[json.loads(line) for line in (root/'signals.jsonl').read_text().splitlines()]
        for line in (root/'trades.jsonl').read_text().splitlines():
            trade=json.loads(line)
            if trade['status']!='CLOSED':continue
            signal=max((s for s in signals if s['signal_id']==trade['signal_id']
                        and s['status']=='READY_FOR_VIRTUAL_ENTRY' and s['event_time']<=trade['entry_interval_start']),
                       key=lambda s:s['event_time'])
            side=trade['direction']
            if side not in selected or signal['event_time']<selected[side][2]['event_time']:
                selected[side]=(summary,trade,signal)
    assert set(selected)=={'LONG','SHORT'},'real closed LONG and SHORT are required'
    results=[check(selected[side],args.data_root) for side in ('LONG','SHORT')]
    args.output.write_text(json.dumps(results,default=encode,sort_keys=True,indent=2)+'\n')


if __name__=='__main__':main()
