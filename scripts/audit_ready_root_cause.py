"""Exhaustive read-only READY audit of a frozen offline historical baseline.

Replays the existing engine with scoped observation hooks. No signal, detector
parameter, range review or portfolio decision is changed. Output roots must be
new; the frozen baseline is checked byte for byte before and after the audit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from hashlib import sha256
import csv
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy import historical_replay as index
from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.replay import opportunity_key
from ready_audit_support import GateInspector, CANDIDATE_GATES
from run_historical_portfolio import encode, canonical


STAGES = ['SETUP','SFP','POST-SFP BOS','ENTRY GEOMETRY','OTE','SOURCE CONTEXT',
          'AUTO LEVELS','OB','POI','3 TARGETS','RANGE REVIEW','SCORE','READY']


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2,default=encode,allow_nan=False)+'\n',encoding='utf-8')


def write_csv(path, rows):
    rows=list(rows)
    if not rows:
        path.write_text('',encoding='utf-8')
        return
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def job(args):
    symbol, data_root, summary, report_root, ids = args
    start=datetime.fromisoformat(summary['warmup_start'])
    end=datetime.fromisoformat(summary['execution_end'])
    execution_start=datetime.fromisoformat(summary['execution_start'])
    histories={tf:[c for row in read_klines_csv(Path(data_root)/symbol/f'{tf}.csv')
                      if start <= (c:=row.to_strategy_candle(tf*60000)).open_time and c.close_time<=end]
               for tf in (summary['ltf_minutes'],summary['htf_minutes'])}
    inspector=GateInspector()
    diagnostics={}
    original_detector=index.derive_automatic_levels
    original_constructor=index.signals_from_opportunities
    traces, state_changes, experiments=[], [], []
    previous={}
    first_experiment=set()
    training_end=execution_start+timedelta(days=60)

    def detector(htf, ltf, hr, lr, opp, *, as_of, policy):
        result=original_detector(htf,ltf,hr,lr,opp,as_of=as_of,policy=policy)
        diag=inspector.inspect(htf,ltf,hr,lr,opp,as_of=as_of,policy=policy)
        if tuple(diag['predicted_reasons']) != result.blocked_reasons or diag['predicted_ready'] != (result.status=='READY'):
            raise AssertionError(('DIAGNOSTIC_MODEL_DIVERGED',symbol,opp.ltf_bos_event_time,result,diag))
        ident=opportunity_key(symbol,summary['htf_minutes'],summary['ltf_minutes'],opp)
        diag['evaluated_at']=as_of
        diagnostics[ident]=diag
        # Predeclared first 60 execution days only. One parameter per experiment,
        # no performance fitting, no final-period sensitivity or threshold choice.
        if ident in ids and ident not in first_experiment and execution_start<=as_of<training_end:
            first_experiment.add(ident)
            for field,value in [('min_body_fraction',.5),('min_body_fraction',.7),
                                ('min_engulf_body_ratio',1.25),('min_engulf_body_ratio',1.5)]:
                experiment=original_detector(htf,ltf,hr,lr,opp,as_of=as_of,policy=replace(policy,**{field:value}))
                experiments.append(dict(signal_id=ident,symbol=symbol,timestamp=as_of,
                                        parameter=field,value=value,baseline_ready=result.status=='READY',
                                        experiment_ready=experiment.status=='READY',
                                        baseline_blockers=result.blocked_reasons,
                                        experiment_blockers=experiment.blocked_reasons))
        return result

    def constructor(opps, by_id, hr, lr, htf, ltf, **kwargs):
        signals=original_constructor(opps,by_id,hr,lr,htf,ltf,**kwargs)
        opp_by_id={opportunity_key(symbol,summary['htf_minutes'],summary['ltf_minutes'],o):o for o in opps}
        for signal in signals:
            if signal.signal_id not in ids:
                continue
            o=opp_by_id[signal.signal_id]
            contexts=[by_id[i] for i in o.candidate_ids]
            geometry=o.entry_geometry_ready_time is not None and o.entry_geometry_ready_time<=kwargs['as_of']
            rejected=o.entry_plan_status=='REJECTED_ENTRY_GEOMETRY'
            diag=diagnostics.get(signal.signal_id)
            candidates=diag['candidates'] if diag else []
            # OB qualification excluding supporting POI, then joint POI, then
            # OB freshness/stop. Each conjunction is on a single candidate.
            ob_gates=['AGGRESSION','IMBALANCE','OB_OTE_AND_IMPULSE','RAW_SWEEP']
            ob=any(all(c['gates'][g] for g in ob_gates) for c in candidates)
            poi=any(all(c['gates'][g] for g in ob_gates+['SUPPORTING_POI']) for c in candidates)
            complete=bool(diag and diag['qualified_ob_count'])
            def flag(value): return 'TRUE' if value else 'FALSE'
            gates={'SETUP':'TRUE','SFP':'TRUE','POST-SFP BOS':'TRUE',
                   'ENTRY GEOMETRY':'FALSE' if rejected else 'TRUE' if geometry else 'UNKNOWN',
                   'OTE':'TRUE' if geometry else 'UNKNOWN',
                   'SOURCE CONTEXT':flag(not(o.htf_recovery_transition_ids or o.ltf_recovery_transition_ids)),
                   'AUTO LEVELS':'TRUE' if diag else 'UNKNOWN',
                   'OB':flag(ob) if diag else 'UNKNOWN',
                   'POI':flag(poi) if diag and ob else 'UNKNOWN',
                   '3 TARGETS':flag(diag['independent_targets_available']) if complete else 'UNKNOWN',
                   'RANGE REVIEW':'NOT_APPLICABLE_STRUCTURAL_SFP',
                   'SCORE':'NOT_A_READY_GATE','READY':flag(signal.status=='READY_FOR_VIRTUAL_ENTRY'),
                   'SFP_ALIVE':flag(signal.status!='INVALIDATED'),
                   'LEVELS_KNOWN_AT':'TRUE' if signal.levels_known_at and signal.levels_known_at<=signal.event_time else 'UNKNOWN',
                   'EXPERIMENTAL_SOURCE_CERTIFICATION':'UNREVIEWED_NOT_ENFORCED_FOR_OFFLINE_READY',
                   'TP1_COST_RULE':'NOT_A_READY_GATE_UNREACHED_ADMISSION',
                   'REENTRY_SCORE_75':'NOT_A_READY_GATE_UNREACHED_ADMISSION'}
            prev=previous.get(signal.signal_id)
            row=dict(signal_id=signal.signal_id,symbol=symbol,direction=signal.direction.name,
                     timestamp=signal.event_time,scope='EXECUTION' if signal.event_time>=execution_start else 'WARMUP',
                     previous_state=prev.status if prev else 'ABSENT',next_state=signal.status,
                     score=signal.score,gates=gates,signal=asdict(signal),opportunity=asdict(o),
                     sfp_contexts=[asdict(c) for c in contexts],automatic_diagnostic=diag,
                     reasons=signal.reasons,invalidation_reasons=signal.invalidation_reasons)
            traces.append(row)
            if prev is None or replace(prev,event_time=signal.event_time)!=signal:
                state_changes.append(asdict(signal))
                previous[signal.signal_id]=signal
        return signals

    index.derive_automatic_levels, index.signals_from_opportunities=detector,constructor
    try:
        updates,meta=index.indexed_signal_updates(histories,symbol=symbol,
              htf_minutes=summary['htf_minutes'],ltf_minutes=summary['ltf_minutes'],
              mode=summary['mode'],auto_level_policy=AutoLevelPolicy(**summary['automatic_level_policy']))
    finally:
        index.derive_automatic_levels,index.signals_from_opportunities=original_detector,original_constructor
    path=Path(report_root)/symbol
    path.mkdir()
    with (path/'evaluations.jsonl').open('w',encoding='utf-8') as stream:
        for row in traces:
            stream.write(canonical(row)+'\n')
    # Apply the exact existing portfolio observation/warmup convention.
    first_close=execution_start+timedelta(minutes=summary['ltf_minutes'])
    warmup={}
    observed=[]
    for s in updates:
        if s.event_time<=first_close:
            warmup[s.signal_id]=replace(s,event_time=first_close)
        else:
            observed.append(s)
    observed=[*warmup.values(),*observed]
    observed.sort(key=lambda s:(s.event_time,s.symbol,s.bos_time,s.direction.value,s.signal_id))
    encoded=[{**asdict(s),'direction':s.direction.name} for s in observed]
    (path/'observed_signals.jsonl').write_text(''.join(canonical(s)+'\n' for s in encoded),encoding='utf-8')
    write_json(path/'sensitivity.json',experiments)
    write_json(path/'metadata.json',meta)
    print(f'{symbol}: {len(traces)} evaluations; {len(encoded)} observed changes; detector equivalence PASS',flush=True)
    return symbol,len(traces)


def category(reason):
    if reason in ('AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET','DIRECTIONAL_IMBALANCE_NOT_CONFIRMED',
                  'FRESH_PREEXISTING_HTF_POI_NOT_FOUND','OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE',
                  'NO_POST_BOS_OB_PATTERN','NO_ELIGIBLE_POST_BOS_OB','THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND',
                  'RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND','OB_FIRST_TEST_ALREADY_CONSUMED'):
        return 'C. EXPERIMENTAL BACKTEST PARAMETER'
    if reason in ('WAITING_FOR_SOURCE_LEVELS','RANGE_UNREVIEWED','SOURCE_CERTIFICATION_UNREVIEWED'):
        return 'D. MANUAL / SOURCE REVIEW GATE'
    if reason in ('REJECTED_ENTRY_GEOMETRY','SOURCE_CONTEXT_BLOCKED','OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE',
                  'TECHNICAL_RECOVERY_LINEAGE_NOT_ENTRY_ELIGIBLE','EXACT_SOURCE_BOS_NOT_FOUND','KNOWN_AT_IN_FUTURE'):
        return 'B. SAFETY / CAUSALITY RULE'
    if reason in ('WAITING_FOR_ENTRY_GEOMETRY','ALL_HTF_SFP_CONTEXTS_INVALIDATED','ORDER_BLOCK_ASSESSMENT_BLOCKED'):
        return 'A. REAL STRATEGY RULE'
    raise ValueError(f'Unclassified blocker requires evidence review: {reason}')


def aggregate(root,baseline,summary):
    by_setup=defaultdict(list)
    observed=[]
    experiments=[]
    for symbol in summary['symbols']:
        observed.extend(json.loads(line) for line in (root/symbol/'observed_signals.jsonl').read_text().splitlines())
        experiments.extend(json.loads((root/symbol/'sensitivity.json').read_text()))
        with (root/symbol/'evaluations.jsonl').open() as stream:
            for line in stream:
                row=json.loads(line)
                by_setup[row['signal_id']].append(row)
    observed.sort(key=lambda s:(s['event_time'],s['symbol'],s['bos_time'],0 if s['direction']=='LONG' else 1,s['signal_id']))
    # Baseline ordering is checked separately: compare sorted canonical objects.
    original=[json.loads(line) for line in (baseline/'signals.jsonl').read_text().splitlines()]
    assert sorted(map(canonical,observed))==sorted(map(canonical,original)), 'OBSERVED_SIGNALS_DIFFER_FROM_FROZEN_BASELINE'
    assert set(by_setup)=={s['signal_id'] for s in original}
    n=len(by_setup)
    aggregates=defaultdict(lambda:dict(count=0,ids=set(),LONG=set(),SHORT=set()))
    dimensions=defaultdict(lambda:dict(count=0,ids=set()))
    first_blockers=[]
    near=[]
    conditions={g:Counter() for g in STAGES+['SFP_ALIVE','LEVELS_KNOWN_AT','EXPERIMENTAL_SOURCE_CERTIFICATION','TP1_COST_RULE','REENTRY_SCORE_75']}
    ever={stage:set() for stage in STAGES}
    failure={stage:set() for stage in STAGES}
    entered={stage:set() for stage in STAGES}
    terminal_invalid=set()
    timeline=root/'gate_timeline.jsonl'
    with timeline.open('w',encoding='utf-8') as stream:
        for ident,rows in sorted(by_setup.items()):
            rows.sort(key=lambda r:r['timestamp'])
            final=rows[-1]
            if final['next_state']=='INVALIDATED': terminal_invalid.add(ident)
            for row in rows:
                for g,v in row['gates'].items():
                    conditions[g][v]+=1
                stage_ok=True
                for stage in STAGES:
                    if stage_ok: entered[stage].add(ident)
                    # Geometry may still be displayed after invalidation, but it
                    # cannot pass the actionable entry funnel. Invalidation wins
                    # at a shared close exactly as in signal construction.
                    if stage=='ENTRY GEOMETRY' and row['gates']['SFP_ALIVE']=='FALSE':
                        stage_ok=False
                    result=row['gates'][stage]
                    if stage_ok and result in ('TRUE','NOT_APPLICABLE_STRUCTURAL_SFP','NOT_A_READY_GATE'):
                        ever[stage].add(ident)
                    else:
                        if stage_ok and result=='FALSE': failure[stage].add(ident)
                        stage_ok=False
                    stream.write(canonical(dict(signal_id=ident,symbol=row['symbol'],direction=row['direction'],
                        timestamp=row['timestamp'],scope=row['scope'],previous_state=row['previous_state'],
                        evaluated_gate=stage,result=result,next_state=row['next_state'],
                        reason=list(row['reasons']) if stage in ('AUTO LEVELS','OB','POI') else
                        list(row['invalidation_reasons']) if stage=='READY' else result,
                        diagnostic_evaluated_at=(row.get('automatic_diagnostic') or {}).get('evaluated_at')))+'\n')
                # A reason occurrence = one reason per actual queue evaluation.
                reasons=set(row['signal']['level_blocking_reasons'])|set(row['invalidation_reasons'])
                if row['next_state'] in ('WAITING_FOR_ENTRY_GEOMETRY','REJECTED_ENTRY_GEOMETRY','SOURCE_CONTEXT_BLOCKED','WAITING_FOR_SOURCE_LEVELS'):
                    reasons.add(row['next_state'])
                for reason in reasons:
                    item=aggregates[reason]
                    item['count']+=1; item['ids'].add(ident); item[row['direction']].add(ident)
                    for dimension,value in [('symbol',row['symbol']),('timeframe','60/5'),
                                            ('month',row['timestamp'][:7]),('score_bucket','85-99' if row['score']>=85 else '65-84')]:
                        d=dimensions[(reason,dimension,value)]
                        d['count']+=1; d['ids'].add(ident)
            # Earliest never-passed gate, using the ENTIRE available lifecycle.
            # Later invalidation doesn't replace an already persistent OB failure.
            first_gate=next(stage for stage in STAGES if ident in entered[stage] and ident not in ever[stage])
            def reached(row):
                prior=STAGES[:STAGES.index(first_gate)]
                return all(row['gates'][g] in ('TRUE','NOT_APPLICABLE_STRUCTURAL_SFP','NOT_A_READY_GATE') for g in prior) and (
                    first_gate=='ENTRY GEOMETRY' or row['gates']['SFP_ALIVE']=='TRUE')
            first_row=next(r for r in rows if reached(r) and (
                           r['gates'][first_gate] not in ('TRUE','NOT_APPLICABLE_STRUCTURAL_SFP','NOT_A_READY_GATE')
                           or (first_gate=='ENTRY GEOMETRY' and r['gates']['SFP_ALIVE']=='FALSE')))
            diag=first_row.get('automatic_diagnostic') or {}
            if first_gate=='ENTRY GEOMETRY':
                rejection=next((r for r in rows if r['gates'][first_gate]=='FALSE' and r['gates']['SFP_ALIVE']=='TRUE'),None)
                invalidation=next((r for r in rows if r['gates']['SFP_ALIVE']=='FALSE'),None)
                if rejection:
                    reason='REJECTED_ENTRY_GEOMETRY';first_row=rejection
                    proof='directional geometry rejected while the SFP context was still alive'
                elif invalidation:
                    reason='ALL_HTF_SFP_CONTEXTS_INVALIDATED';first_row=invalidation
                    proof='first terminal invalidation before actionable geometry; earlier waiting was not a proven permanent failure'
                else:
                    reason='WAITING_FOR_ENTRY_GEOMETRY'
                    proof='never resolved by dataset end; right-censored, not proved impossible beyond the available history'
            elif first_gate=='AUTO LEVELS':
                reason='ALL_HTF_SFP_CONTEXTS_INVALIDATED'
                proof='SFP invalidated before automatic levels could be evaluated'
            else:
                if first_gate=='POI':
                    reason='FRESH_PREEXISTING_HTF_POI_NOT_FOUND'
                elif diag.get('candidates'):
                    def progress(candidate):
                        total=0
                        for gate,_ in CANDIDATE_GATES[:4]:
                            if not candidate['gates'][gate]:break
                            total+=1
                        return total
                    best_candidate=max(diag['candidates'],key=progress)
                    reason=best_candidate['first_failure']
                else:
                    reason='NO_POST_BOS_OB_PATTERN'
                proof='fixed post-BOS/pre-anchor candidate formation predicates never simultaneously pass; later retests cannot restore freshness'
            first_blockers.append(dict(signal_id=ident,symbol=final['symbol'],direction=final['direction'],
                                       first_gate=first_gate,reason=reason,timestamp=first_row['timestamp'],
                                       terminal_timestamp=final['timestamp'] if final['next_state']=='INVALIDATED' else None,
                                       final_state=final['next_state'],proof=proof,
                                       category=category(reason.split(' | ')[0])))
            # Rank by actual sequentially passed candidate predicates, not score
            # (the numerical score is identical for all geometry-ready candidates).
            best=None
            for row in rows:
                diag=row.get('automatic_diagnostic')
                if not diag or diag['evaluated_at']!=row['timestamp']:
                    continue
                for candidate in diag['candidates']:
                    sequential=0
                    for gate,_ in CANDIDATE_GATES:
                        if not candidate['gates'][gate]: break
                        sequential+=1
                    rank=(sequential,sum(candidate['gates'].values()),int(row['next_state']!='INVALIDATED'))
                    if best is None or rank>best[0]: best=(rank,row,candidate)
            if best:
                rank,row,c=best
                near.append(dict(signal_id=ident,symbol=row['symbol'],direction=row['direction'],timestamp=row['timestamp'],
                    score=row['score'],rank=list(rank),passed_gates=[g for g,v in c['gates'].items() if v],
                    failed_gates=[g for g,v in c['gates'].items() if not v],exact_blocker=c['first_failure'],
                    entry_zone=row['signal']['entry_zone'],ote=row['signal']['entry_zone'],ob_evidence=c,
                    poi_evidence=c['fresh_supporting_pois'],supporting_poi_candidates=c['supporting_poi_candidates'],
                    targets=row['automatic_diagnostic']['selected_targets'],
                    targets_are_independent_diagnostic=True,range_status='NOT_APPLICABLE_STRUCTURAL_SFP',
                    source_certification='UNREVIEWED_NOT_ENFORCED_FOR_OFFLINE',sfp=row['sfp_contexts'],
                    bos={k:v for k,v in row['opportunity'].items() if k.startswith('ltf_bos')},
                    opportunity=row['opportunity'],production_state=row['next_state']))
    funnel=[]
    for stage in STAGES:
        en,pa=entered[stage],ever[stage]
        failed=(en-pa)&failure[stage]
        invalid=(en-pa-failed)&terminal_invalid
        waiting=en-pa-failed-invalid
        assert len(en)==len(pa)+len(failed)+len(invalid)+len(waiting)
        funnel.append(dict(stage=stage,entered_count=len(en),passed_count=len(pa),failed_count=len(failed),
                           waiting_count=len(waiting),invalidated_count=len(invalid),
                           percentage_of_all_setups=100*len(pa)/n,
                           percentage_of_previous_stage=100*len(pa)/len(en) if en else None))
    blocker_rows=[dict(blocker_reason=reason,count=x['count'],unique_setups=len(x['ids']),
                       percentage_setups=100*len(x['ids'])/n,LONG=len(x['LONG']),SHORT=len(x['SHORT']),category=category(reason))
                  for reason,x in aggregates.items()]
    blocker_rows.sort(key=lambda r:(-r['unique_setups'],r['blocker_reason']))
    near.sort(key=lambda r:(tuple(-v for v in r['rank']),r['timestamp'],r['signal_id']))
    write_json(root/'funnel.json',funnel); write_csv(root/'funnel.csv',funnel)
    write_json(root/'blockers.json',blocker_rows);write_csv(root/'blockers.csv',blocker_rows)
    write_json(root/'first_blockers.json',first_blockers);write_csv(root/'first_blockers.csv',first_blockers)
    counts=Counter((r['first_gate'],r['reason'],r['category']) for r in first_blockers)
    top=[dict(gate=k[0],reason=k[1],category=k[2],setups=v,percentage=100*v/n)
         for k,v in sorted(counts.items(),key=lambda item:(-item[1],item[0]))[:20]]
    write_json(root/'top20_first_blockers.json',top)
    write_csv(root/'blocker_dimensions.csv',[dict(reason=k[0],dimension=k[1],value=k[2],count=v['count'],unique_setups=len(v['ids']))
               for k,v in sorted(dimensions.items())])
    write_json(root/'near_ready_top50.json',near[:50])
    write_csv(root/'near_ready_top50.csv',[dict(rank=i+1,signal_id=r['signal_id'],symbol=r['symbol'],direction=r['direction'],
                timestamp=r['timestamp'],score=r['score'],passed_gates=' | '.join(r['passed_gates']),
                failed_gates=' | '.join(r['failed_gates']),exact_blocker=r['exact_blocker'],
                entry_zone=canonical(r['entry_zone']),ob_zone=canonical(r['ob_evidence']['ob_zone']),
                poi_count=r['supporting_poi_candidates'],range_status=r['range_status']) for i,r in enumerate(near[:50])])
    write_json(root/'conditions.json',{g:dict(c) for g,c in conditions.items()})
    sensitivity=[]
    for parameter,value in sorted({(r['parameter'],r['value']) for r in experiments}):
        group=[r for r in experiments if (r['parameter'],r['value'])==(parameter,value)]
        sensitivity.append(dict(parameter=parameter,value=value,setups=len(group),
                                baseline_ready=sum(r['baseline_ready'] for r in group),
                                experimental_ready=sum(r['experiment_ready'] for r in group),
                                changed_blocker_sets=sum(r['baseline_blockers']!=r['experiment_blockers'] for r in group),
                                blocker_counts=dict(Counter(reason for r in group for reason in r['experiment_blockers']))))
    write_json(root/'sensitivity_summary.json',dict(period='FIRST_60_EXECUTION_DAYS_ONLY',
                status='PREDECLARED_DIAGNOSTIC_EXPERIMENTS_NO_OPTIMIZATION_NO_HOLDOUT_CLAIM',results=sensitivity))
    result=dict(unique_setups=n,observed_signal_state_changes=len(original),
                diagnostic_evaluations=sum(len(v) for v in by_setup.values()),baseline_signal_equivalence='PASS',
                funnel=funnel,top_blockers=blocker_rows,first_blocker_gate_counts=dict(Counter(r['first_gate'] for r in first_blockers)),
                near_ready_candidates=len(near),all_ready_conditions_simultaneously_true=len(ever['READY']),
                manual_gate_only_blocked_setups=0,source_certification_enforced_for_offline_ready=False,
                range_eligible_provenance_setups=0,trade_entry_allowed=False,
                verdict='ZERO READY IS EXPECTED UNDER CURRENT RULES',
                limitations=['CONDITIONS_COUNTS_ARE_ACTUAL_SCHEDULED_EVALUATIONS_NOT_EVERY_UNCHANGED_BAR',
                             'LATER_SHORT_CIRCUITED_PRODUCTION_GATES_ARE_UNKNOWN',
                             'INDEPENDENT_TARGET_AND_CANDIDATE_DIAGNOSTICS_DO_NOT_QUALIFY_SIGNALS',
                             'FIRST_PERSISTENT_BLOCKER_IS_RETROSPECTIVE_NOT_A_TRADING_RULE',
                             'GEOMETRY_AND_RANGE_MACHINE_NORMALIZATION_NOT_SOURCE_CERTIFIED'])
    write_json(root/'summary.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=Path('data/reports/historical_portfolio_audit/backtest_max'))
    parser.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    parser.add_argument('--report-root',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args(argv)
    if args.report_root.exists(): parser.error('report-root must be new; existing reports are never overwritten')
    if not 1<=args.workers<=4: parser.error('workers must be 1..4')
    summary=json.loads((args.baseline/'summary.json').read_text())
    before={p.name:digest(p) for p in args.baseline.iterdir() if p.is_file()}
    args.report_root.mkdir(parents=True)
    write_json(args.report_root/'baseline_manifest.json',before)
    write_json(args.report_root/'baseline_summary.json',summary)
    ids={s['signal_id'] for line in (args.baseline/'signals.jsonl').read_text().splitlines() if (s:=json.loads(line))}
    jobs=[(s,str(args.data_root),summary,str(args.report_root),ids) for s in summary['symbols']]
    if args.workers==1:
        for task in jobs: job(task)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            list(executor.map(job,jobs))
    result=aggregate(args.report_root,args.baseline,summary)
    assert before=={p.name:digest(p) for p in args.baseline.iterdir() if p.is_file()}
    write_json(args.report_root/'artifact_hashes.json',{p.relative_to(args.report_root).as_posix():digest(p)
                                                      for p in sorted(args.report_root.rglob('*')) if p.is_file()})
    print(canonical({k:result[k] for k in ('unique_setups','observed_signal_state_changes','baseline_signal_equivalence','verdict')}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
