"""Frozen-rule external replay; independent windows/segments, no fitting or orders."""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
import csv
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from concurrent.futures import ProcessPoolExecutor
import gzip
from hashlib import sha256
import json
import pickle
from pathlib import Path

from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy, VirtualPortfolio
from import_public_research_data import aggregate
from crypto_bot.data.models import MarketCandle
from research_support import check_baseline, performance, read_compressed, regime
from run_historical_portfolio import canonical, simulate
from research_variants import STRUCTURAL_VARIANTS, isolated_variant
from research_structure_cache import structure_cache, validated_prefix_reuse


def index_job(job):
    sample,s,htf,ltf,mode,variant,source_hashes,baseline=job
    audit=[]
    cache=Path(__file__).resolve().parents[1]/'.research_cache'
    print('Indexing asset',s,htf,ltf,variant,len(sample[ltf]),'LTF candles',flush=True)
    with structure_cache(cache,source_hashes,baseline), validated_prefix_reuse(sample), isolated_variant(variant,audit) as policy:
        signals,metadata=indexed_signal_updates(sample,symbol=s,htf_minutes=htf,ltf_minutes=ltf,
                                               mode=mode,auto_level_policy=policy)
    return signals,metadata,[dict(symbol=s,**row) for row in audit]


def common_segments(base):
    begin = max(rows[0].open_time for rows in base.values())
    end = min(rows[-1].close_time for rows in base.values())
    gaps = []
    for rows in base.values():
        for a, b in zip(rows, rows[1:]):
            if a.close_time != b.open_time:
                gaps.append((max(begin,a.close_time), min(end,b.open_time)))
    gaps = sorted((a,b) for a,b in gaps if a < b)
    merged = []
    for a,b in gaps:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0],max(b,merged[-1][1]))
        else:
            merged.append((a,b))
    segments = []
    cursor = begin
    for a,b in merged:
        if cursor < a:
            segments.append((cursor,a))
        cursor = b
    if cursor < end:
        segments.append((cursor,end))
    return segments, merged


def slice_bars(rows, begin, end):
    opens = [c.open_time for c in rows]
    a, b = bisect_left(opens,begin), bisect_left(opens,end)
    return [c for c in rows[a:b] if c.close_time <= end]


def write_rows(path, rows):
    if path.suffix == '.gz':
        with path.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as writer:
            for row in rows:
                writer.write((canonical(row)+'\n').encode())
    else:
        path.write_text(''.join(canonical(row)+'\n' for row in rows))


def ready_audit(observed, portfolio, daily):
    ready = {}
    for signal in observed:
        if signal.status=='READY_FOR_VIRTUAL_ENTRY':
            ready.setdefault(signal.signal_id,signal)
    pending = set()
    terminal = {}
    for decision in portfolio.journal:
        key = decision.signal_id
        if key not in ready:
            continue
        if decision.action=='SETUP_READY':
            pending.add(key)
        elif key in pending and decision.action in ('SETUP_WAITING','SETUP_INVALIDATED','SETUP_REJECTED','VIRTUAL_ENTRY_BLOCKED'):
            terminal.setdefault(key,dict(time=decision.time,action=decision.action,reason=decision.reason))
            pending.discard(key)
        elif decision.action=='VIRTUAL_ENTRY':
            pending.discard(key)
    rows = []
    groups = defaultdict(lambda:Counter(ready=0,filled=0))
    for key,signal in ready.items():
        market,vol = regime(daily[signal.symbol],signal.event_time)
        filled = key in portfolio.trades
        first = terminal.get(key)
        reason = ('VIRTUAL_TRADE_'+portfolio.trades[key]['status'] if filled else
                  'LIMIT_NOT_FILLED_BEFORE_OB_FIRST_TEST_CONSUMED' if first and 'OB_FIRST_TEST_ALREADY_CONSUMED' in first['reason'] else
                  'TARGET_EVIDENCE_WITHDRAWN' if first and 'THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND' in first['reason'] else
                  first['reason'] if first else 'PRICE_NOT_FILLED_BEFORE_OBSERVATION_END')
        row = dict(signal_id=key,symbol=signal.symbol,direction=signal.direction.name,
                   first_ready_time=signal.event_time,ready_regime=market,ready_volatility_bucket=vol,
                   limit_price=signal.optimal_entry,filled=filled,entry_outcome=reason,
                   first_withdrawal_or_admission_block=first)
        rows.append(row)
        for label in ('symbol','direction','ready_regime','ready_volatility_bucket'):
            group = groups[(label,row[label])]
            group['ready'] += 1
            group['filled'] += filled
    return rows,[dict(dimension=k[0],value=k[1],**v,fill_rate=v['filled']/v['ready']) for k,v in sorted(groups.items())]


def study(cohort,root,split,htf,ltf,output,mode='BACKTEST',cost_factor=1.0,risk=.02,workers=2,windows=None,
          variant='BASE',score=75):
    repo = Path(__file__).resolve().parents[1]
    lock = check_baseline(repo)
    symbols = split['symbols']
    base_tf = 15 if cohort=='bybit' else 5
    input_hashes={str(p.relative_to(repo)):sha256(p.read_bytes()).hexdigest()
                  for s in symbols for tf in sorted({base_tf,htf,ltf})
                  for p in [root/s/f'{tf}.csv.gz']}
    first_opens=[]
    for s in symbols:
        with gzip.open(root/s/f'{base_tf}.csv.gz','rt',newline='') as handle:
            row=next(csv.DictReader(handle))
            first_opens.append(datetime.fromtimestamp(int(row['open_time_ms'])/1000,tz=timezone.utc))
    # Earlier solitary-symbol years remain stored but cannot enter a fixed
    # basket before its latest member exists. Retain its EXACT common coverage.
    read_begin=min(max(first_opens),datetime.fromisoformat(split['periods'][0]['start'])-timedelta(days=90))
    data = {symbol:{tf:read_compressed(root/symbol/f'{tf}.csv.gz',tf,begin=read_begin) for tf in sorted({base_tf,htf,ltf})} for symbol in symbols}
    segments,gaps = common_segments({s:data[s][base_tf] for s in symbols})
    daily = {}
    for s in symbols:
        candles = [MarketCandle(cohort.upper(),s,str(base_tf),int(c.open_time.timestamp()*1000),c.open,c.high,c.low,c.close) for c in data[s][base_tf]]
        rows,_ = aggregate(candles,base_tf,1440)
        daily[s] = [c.to_strategy_candle(86400000) for c in rows]
    periods = split['periods']
    begin = datetime.fromisoformat(periods[0]['start'])
    final = datetime.fromisoformat(periods[-1]['end'])
    walk = []
    anchor = begin + timedelta(days=90)
    while anchor < final:
        walk.append(dict(name=f'WALK_{len(walk):02}',start=anchor.isoformat(),end=min(final,anchor+timedelta(days=90)).isoformat(),
                         reference_start=(anchor-timedelta(days=90)).isoformat(),partial=anchor+timedelta(days=90)>final))
        anchor += timedelta(days=90)
    output.mkdir(parents=True,exist_ok=True)
    (output/'coverage_segments.json').write_text(canonical(dict(segments=segments,gaps=gaps,
        gaps_never_interpolated=True,all_independent_portfolios=True))+'\n')
    results=[]
    policy = SimulationPolicy(risk_fraction=risk,fee_fraction=.0006*cost_factor,slippage_fraction=.0002*cost_factor,
                              reentry_min_score=score)
    for window in [*periods,*walk]:
        if windows and window['name'] not in windows:
            continue
        requested_start=datetime.fromisoformat(window['start'])
        requested_end=datetime.fromisoformat(window['end'])
        for number,(segment_start,segment_end) in enumerate(segments):
            begin=max(requested_start,segment_start+timedelta(minutes=576*ltf))
            end=min(requested_end,segment_end)
            if max(requested_start,segment_start)>=min(requested_end,segment_end):
                continue
            label=window['name']+f'_SEGMENT_{number:02}'
            if begin>=end:
                results.append(dict(window=window['name'],segment=number,status='INSUFFICIENT_CONTIGUOUS_WARMUP',
                    available_start=max(requested_start,segment_start),available_end=end,never_omitted_due_to_pnl=True))
                continue
            prefix=max(segment_start,begin-timedelta(days=90))
            sample={s:{tf:slice_bars(data[s][tf],prefix,end) for tf in (htf,ltf)} for s in symbols}
            # Execution starts on a complete LTF boundary shared by all assets.
            execution={s:[c for c in sample[s][ltf] if c.open_time>=begin] for s in symbols}
            if not all(execution.values()):
                results.append(dict(window=window['name'],segment=number,status='NO_COMPLETE_EXECUTION_BAR'))
                continue
            actual_start=max(cs[0].open_time for cs in execution.values())
            actual_end=min(cs[-1].close_time for cs in execution.values())
            execution={s:[c for c in cs if actual_start<=c.open_time and c.close_time<=actual_end] for s,cs in execution.items()}
            updates=[]
            print(cohort,htf,ltf,label,actual_start.isoformat(),actual_end.isoformat(),'indexing',flush=True)
            cache_key=sha256(canonical(dict(input_hashes=input_hashes,prefix=prefix,end=end,htf=htf,ltf=ltf,
                            baseline=lock['code_hashes'],mode=mode,variant=variant,index_adapter_version=2)).encode()).hexdigest()
            cache=repo/'.research_cache'/(cache_key+'.pickle.gz')
            # Only this adapter's own trusted local, hash-bound objects are read;
            # no pickle is downloaded from a mirror or published as source data.
            if cache.exists():
                with gzip.open(cache,'rb') as handle:
                    indexed=pickle.load(handle)
            else:
                jobs=[(sample[s],s,htf,ltf,mode,variant,
                       {tf:input_hashes[str((root/s/f'{tf}.csv.gz').relative_to(repo))] for tf in (htf,ltf)},
                       lock['baseline_commit']) for s in symbols]
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    indexed=list(pool.map(index_job,jobs))
                cache.parent.mkdir(exist_ok=True)
                with gzip.open(cache,'wb') as handle:
                    pickle.dump(indexed,handle,pickle.HIGHEST_PROTOCOL)
            targets=[]
            for s,(signal_updates,metadata,audit) in zip(symbols,indexed):
                print(s,len(signal_updates),'signal updates',metadata['automatic_evaluations'],'evaluations',flush=True)
                updates.extend(signal_updates)
                targets.extend(audit)
            portfolio=VirtualPortfolio(equity=1170,policy=policy,mode=mode)
            p,observed=simulate(execution,updates,portfolio=portfolio,initial_capital=1170,mode=mode)
            measurements=performance(p,observed,actual_start,actual_end)
            ready,groups=ready_audit(observed,p,daily)
            folder=output/label;folder.mkdir(exist_ok=True)
            receipt=dict(cohort=cohort,htf=htf,ltf=ltf,window=window,segment=number,start=actual_start,end=actual_end,
                analysis_start=prefix,baseline_commit=lock['baseline_commit'],baseline_hash_guard='PASS',
                input_hashes=input_hashes,
                mode=mode,policy=asdict(policy),variant=variant,
                canonical_parameters=cost_factor==1 and risk==.02 and variant=='BASE' and score==75,
                performance=measurements,frequency_groups=groups,
                gap_or_window_boundary_open_trades_right_censored=True,trade_entry_allowed=False)
            (folder/'summary.json').write_text(canonical(receipt)+'\n')
            write_rows(folder/'signals.jsonl.gz',(asdict(s) for s in observed))
            write_rows(folder/'decisions.jsonl.gz',(asdict(d) for d in p.journal))
            write_rows(folder/'trades.jsonl',p.trades.values())
            write_rows(folder/'equity_curve.jsonl.gz',p.equity_curve)
            write_rows(folder/'ready_outcomes.jsonl',ready)
            write_rows(folder/'target_availability_qualification_only.jsonl.gz',targets)
            hashes={f.name:sha256(f.read_bytes()).hexdigest() for f in folder.iterdir() if f.name not in ('artifact_hashes.json','fingerprint.sha256')}
            (folder/'artifact_hashes.json').write_text(canonical(hashes)+'\n')
            (folder/'fingerprint.sha256').write_text(sha256(canonical(hashes).encode()).hexdigest()+'\n')
            results.append(dict(window=window['name'],segment=number,status='REPLAY_COMPLETE',path=str(folder),
                                start=actual_start,end=actual_end,performance=measurements))
            (output/'results.json').write_text(canonical(results)+'\n')
            print(label,measurements['setups'],'setups',measurements['ready'],'READY',measurements['entries'],'entries',flush=True)
    (output/'results.json').write_text(canonical(results)+'\n')
    check_baseline(repo)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',choices=['bybit','binance'],required=True)
    parser.add_argument('--htf',type=int,required=True)
    parser.add_argument('--ltf',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',choices=['BACKTEST','SHADOW'],default='BACKTEST')
    parser.add_argument('--cost-factor',type=float,choices=[1,1.5,2],default=1)
    parser.add_argument('--risk',type=float,choices=[.02,.021,.025],default=.02)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--windows',nargs='+',help='Explicit registered windows; omitted means every window')
    parser.add_argument('--variant',choices=list(STRUCTURAL_VARIANTS),default='BASE')
    parser.add_argument('--reentry-score',type=int,choices=[75,80],default=75)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    split=json.loads((repo/f'data/reports/robustness_research/{args.cohort}_temporal_split.json').read_text())
    if [args.htf,args.ltf] not in split['mappings']:
        parser.error('Mapping unavailable in the pre-registered source cohort')
    if args.variant!='BASE' and (args.cohort!='binance' or (args.htf,args.ltf)!=(60,5) or args.windows!=['VALIDATION']):
        parser.error('Structural variants are registered only for Binance 60/5 VALIDATION')
    study(args.cohort,repo/f'data/history/public_research/{args.cohort}_mirror',split,
          args.htf,args.ltf,args.output,args.mode,args.cost_factor,args.risk,args.workers,args.windows,args.variant,args.reentry_score)


if __name__=='__main__':
    main()
