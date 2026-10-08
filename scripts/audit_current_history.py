"""Exhaustive first rejection on real emitted setups, without changing production.

Rebuilds the exact run under read-only observation hooks. Each saved gate trace
describes a single OB candidate at one observation; no candidate unions qualify
anything. Only states actually emitted into the execution journal count, including
the same warmup collapse. Every observed signal must match the retained run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import gzip
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy import historical_replay as index
from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.replay import opportunity_key
from ready_audit_support import GateInspector
from run_historical_portfolio import canonical, encode


STAGES = ('SETUP','STRUCTURE','BOS','ENTRY GEOMETRY','OB candidate','valid OB',
          'HTF POI','preexisting POI','fresh POI','supporting POI','OB first test',
          'SL','targets','R:R','Score','READY','virtual entry')
VALID_GATES = ('AGGRESSION','IMBALANCE','OB_OTE_AND_IMPULSE','RAW_SWEEP')


def first_rejection(signal, diag):
    """Index of first failed stage; a single candidate supplies every passed gate."""
    if signal.status=='READY_FOR_VIRTUAL_ENTRY':
        return (16,0,'READY_AWAITING_REAL_PRICE_TOUCH',None)
    if signal.status=='INVALIDATED':
        return (3,0,'ALL_HTF_CONTEXTS_INVALIDATED_BEFORE_FURTHER_PROGRESS',None)
    if diag is None or signal.entry_geometry_ready_time is None:
        return (3,0,'GEOMETRY_NOT_RESOLVED_BEFORE_CONTEXT_OR_DATA_END',None)
    best=(4,0,'NO_OB_CANDIDATE',None)
    for candidate in diag['candidates']:
        gates=candidate['gates'];depth=0
        rank,reason=5,candidate['first_failure']
        for gate in VALID_GATES:
            if not gates[gate]:
                break
            depth+=1
        else:
            rank,reason=6,'NO_OVERLAPPING_DIRECTIONAL_HTF_POI'
            pre=candidate['preexisting_supporting_poi_evidence']
            if pre or candidate['later_supporting_poi_evidence']:
                rank,reason=7,'HTF_POI_NOT_PREEXISTING_AT_OB_A_OPEN'
            if pre:
                rank,reason=8,'ALL_PREEXISTING_HTF_POIS_PREVIOUSLY_TOUCHED'
            if candidate['fresh_supporting_pois']:
                rank,reason=9,'SUPPORTING_TREND_ALIGNMENT_FAILED'
                if gates['TREND_ALIGNMENT']:
                    rank,reason=10,'OB_FIRST_TEST_ALREADY_CONSUMED'
                    if gates['OB_FRESH']:
                        rank,reason=11,'OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE'
                        if gates['STOP_GEOMETRY']:
                            rank,reason=12,'THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND'
                            if diag['independent_targets_available']:
                                raise AssertionError('all gates passed without production READY')
        row=(rank,depth,reason,candidate['a_open'])
        if row[:2]>best[:2]:best=row
    return best


def job(task):
    symbol,data_root,summary,expected,output=task
    root=Path(output);inspector=GateInspector();diagnostics={};best={};receipts={}
    htf_minutes,ltf_minutes=summary['htf_minutes'],summary['ltf_minutes']
    start=datetime.fromisoformat(summary['warmup_start']);end=datetime.fromisoformat(summary['execution_end'])
    first=datetime.fromisoformat(summary['execution_start'])+timedelta(minutes=ltf_minutes)
    histories={tf:[c for row in read_klines_csv(Path(data_root)/symbol/f'{tf}.csv')
                  if start<=(c:=row.to_strategy_candle(tf*60000)).open_time and c.close_time<=end]
               for tf in (htf_minutes,ltf_minutes)}
    expected_by_time={(r['signal_id'],r['event_time']):r for r in expected}
    ids={r['signal_id'] for r in expected};warmup={}
    original_detector,original_constructor=index.derive_automatic_levels,index.signals_from_opportunities
    trace_path=root/(symbol+'_candidate_traces.jsonl.gz')
    with trace_path.open('wb') as raw, gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as stream:
        def detector(htf,ltf,hr,lr,opp,*,as_of,policy,freshness_index=None):
            result=original_detector(htf,ltf,hr,lr,opp,as_of=as_of,policy=policy,freshness_index=freshness_index)
            diag=inspector.inspect(htf,ltf,hr,lr,opp,as_of=as_of,policy=policy,freshness_index=freshness_index)
            if tuple(diag['predicted_reasons'])!=result.blocked_reasons or diag['predicted_ready']!=(result.status=='READY'):
                raise AssertionError(('DIAGNOSTIC_MODEL_DIVERGED',symbol,as_of))
            key=opportunity_key(symbol,htf_minutes,ltf_minutes,opp)
            diagnostics[key]=diag
            if key in ids:
                stream.write((canonical(dict(signal_id=key,symbol=symbol,as_of=as_of,
                    direction=opp.expected_direction.name,opportunity=asdict(opp),
                    result=asdict(result),diagnostic=diag))+'\n').encode())
            return result

        def record(signal,diag,expected_row):
            actual=json.loads(canonical({**asdict(signal),'direction':signal.direction.name}))
            if actual!=expected_row:
                raise AssertionError(('SIGNAL_CHANGED_UNDER_OBSERVATION',symbol,signal.signal_id,signal.event_time))
            receipts[(signal.signal_id,signal.event_time.isoformat())]=True
            rank=first_rejection(signal,diag)
            if signal.signal_id not in best or rank[:2]>best[signal.signal_id]['rank'][:2]:
                best[signal.signal_id]=dict(rank=rank,signal=actual,proof_time=signal.event_time)

        def constructor(*args,**kwargs):
            signals=original_constructor(*args,**kwargs)
            for signal in signals:
                if signal.signal_id not in ids:continue
                diag=diagnostics.get(signal.signal_id)
                if signal.event_time<=first:
                    warmup[signal.signal_id]=(signal,diag)
                elif (row:=expected_by_time.get((signal.signal_id,signal.event_time.isoformat()))) is not None:
                    record(signal,diag,row)
            return signals

        index.derive_automatic_levels,index.signals_from_opportunities=detector,constructor
        try:
            index.indexed_signal_updates(histories,symbol=symbol,htf_minutes=htf_minutes,
                ltf_minutes=ltf_minutes,mode=summary['mode'],auto_level_policy=AutoLevelPolicy())
        finally:
            index.derive_automatic_levels,index.signals_from_opportunities=original_detector,original_constructor
        for key,(signal,diag) in warmup.items():
            row=expected_by_time.get((key,first.isoformat()))
            if row is not None:record(replace(signal,event_time=first),diag,row)
    if set(receipts)!=set(expected_by_time):
        raise AssertionError(('MISSING_OBSERVED_SIGNAL',symbol,len(receipts),len(expected_by_time)))
    assert set(best)==ids
    print(symbol,'all observed signals matched;',len(best),'setups explained',flush=True)
    return symbol,best


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    summary=json.loads((args.run/'summary.json').read_text())
    observed=[json.loads(line) for line in (args.run/'signals.jsonl').read_text().splitlines()]
    trades={r['signal_id']:r for line in (args.run/'trades.jsonl').read_text().splitlines() if (r:=json.loads(line))}
    execution={r['signal_id']:r for line in (args.run/'setup_outcomes.jsonl').read_text().splitlines() if (r:=json.loads(line))}
    tasks=[(s,str(args.data_root),summary,[r for r in observed if r['symbol']==s],str(args.output)) for s in summary['symbols']]
    all_best={}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for symbol,best in pool.map(job,tasks):all_best.update(best)
    rows=[];counts=Counter();reasons=Counter()
    for key,proof in sorted(all_best.items()):
        rank,_,reason,a_open=proof['rank'];trade=trades.get(key)
        if trade:
            rank,reason=17,'VIRTUAL_TRADE_'+trade['status']
        elif rank==16:
            reason=';'.join([execution[key]['execution_outcome'],*execution[key]['reasons']])
        counts[rank]+=1;reasons[reason]+=1
        rows.append(dict(signal_id=key,symbol=proof['signal']['symbol'],direction=proof['signal']['direction'],
            proof_time=proof['proof_time'],candidate_a_open=a_open,passed_stages=list(STAGES[:rank]),
            first_reject_stage=STAGES[rank] if rank<len(STAGES) else None,first_rejection=reason,
            final_execution=execution[key],trade_status=trade['status'] if trade else None))
    funnel=[]
    for i,stage in enumerate(STAGES):
        entered=sum(n for rank,n in counts.items() if rank>=i);passed=sum(n for rank,n in counts.items() if rank>i)
        funnel.append(dict(stage=stage,input=entered,passed=passed,reject=entered-passed,pass_rate=passed/entered if entered else None))
    assert len(rows)==summary['funnel']['unique_setups']
    assert sum(r['reject'] for r in funnel)+len(trades)==len(rows)
    assert funnel[-2]['passed']==summary['funnel']['ever_status_unique_setup_counts']['READY_FOR_VIRTUAL_ENTRY']
    for name,value in [('funnel.json',funnel),('setup_first_rejections.json',rows),('summary.json',
        dict(setups=len(rows),ready=funnel[-2]['passed'],entries=len(trades),rejections=dict(reasons),
             policy='ONE_FIRST_REJECTION_BEST_SINGLE_CANDIDATE_AT_EMITTED_ALIVE_OBSERVATION',
             observed_signals_verified=len(observed),trade_entry_allowed=False))]:
        (args.output/name).write_text(json.dumps(value,indent=2,sort_keys=True,default=encode)+'\n')


if __name__=='__main__':main()
