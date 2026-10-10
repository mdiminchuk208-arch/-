"""Locked full native Bybit source paths, physical union and independent variants."""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_pdf_native import SourceEngine as StrictEngine
from crypto_bot.strategy.source_pdf_native import SourceSeries as StrictSeries
from crypto_bot.strategy.source_pdf_native import evidence_json, sign
from crypto_bot.strategy.source_permitted import (
    SourceEngine,
    SourceSeries,
    select_union,
)
from crypto_bot.strategy.source_permitted_cases import replay_case
from crypto_bot.strategy.source_portfolio import SourceRiskPolicy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_source_pdf_native_bybit import (
    digest,
    intermediate_snapshot,
    load_intermediate,
    read_rows,
    stats,
    write_json,
    write_rows,
)

REPO=Path(__file__).resolve().parents[1]
POLICY=REPO/'config/source_permitted_policy.json'
STRICT=REPO/'data/reports/source_pdf_native_bybit_2026_10_09'
SEGMENT_FILES=('signals.jsonl.gz','cancellations.jsonl.gz','exit_events.jsonl.gz','attempts.jsonl.gz',
               'flow_history.jsonl.gz','flow_bottleneck.jsonl.gz','range_audit.jsonl.gz',
               'strict_bottleneck.jsonl.gz','old13_audit.json','old9_cancel_audit.json',
               'range_admissibility.json','physical_anchors.json','dataset_audit.json','summary.json')
IMPLEMENTATION=['SOURCE_PERMITTED_PROTOCOL.md','SOURCE_PERMITTED_RECONSTRUCTION.md','config/source_permitted_policy.json',
    'scripts/run_source_permitted_bybit.py','scripts/run_source_pdf_native_bybit.py',
    'src/crypto_bot/strategy/source_permitted.py','src/crypto_bot/strategy/source_permitted_cases.py',
    'src/crypto_bot/strategy/source_pdf_native.py','src/crypto_bot/strategy/source_pdf_cases.py',
    'src/crypto_bot/strategy/source_engine.py','src/crypto_bot/strategy/source_portfolio.py',
    'src/crypto_bot/strategy/market_analysis.py','src/crypto_bot/strategy/range_engine.py',
    'src/crypto_bot/strategy/sfp.py','src/crypto_bot/strategy/structure.py',
    'src/crypto_bot/common/models.py','src/crypto_bot/data/storage.py','src/crypto_bot/data/models.py',
    'data/source_materials/primary_pdf_2026_10_09/manifest.json',
    'data/source_materials/cryptology_2026_10_09/manifest.json',
    'data/source_materials/cryptology_2026_10_09/cryptology.zip']
IMPLEMENTATION += [f'data/source_materials/primary_pdf_2026_10_09/SW{n}.{suffix}'
                   for n in (5,9,11,12,22) for suffix in ('pdf','txt')]
IMPLEMENTATION += [f'data/source_materials/cryptology_2026_10_09/{n:02d}.clean.txt'
                   for n in (3,6,11,14,16,18,19,20)]


class StrictBottleneckAudit(StrictEngine):
    """Read-only instrumentation, exact original strict engine decisions."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.audit=[]
        self._last_reason={}

    def _evaluate(self,setup,now):
        super()._evaluate(setup,now)
        if 'liquidity_passed' not in setup.stages:
            return
        h=self.series[setup.htf]
        f=h.flow
        reason=setup.reason
        if self._last_reason.get(setup.setup_id)==reason:
            return
        self._last_reason[setup.setup_id]=reason
        self.audit.append({'setup_id':setup.setup_id,'known_at':now,'htf':setup.htf,'ltf':setup.ltf,
                          'direction':setup.poi.direction,'reason':reason,'stages':sorted(setup.stages),
                          'htf_flow':json.loads(evidence_json(f)),
                          'key_pairs':h.structural_key_history[setup.poi.direction][-2:],
                          'classification':'STRICT_CONSERVATIVE_SOURCE_INTERPRETATION'})


def verify_manifest(folder, fingerprint=None):
    m=json.loads((folder/'manifest.json').read_text())
    if m['status']!='COMPLETE' or fingerprint and m['fingerprint']!=fingerprint:
        raise ValueError('incomplete or different segment lock: '+str(folder))
    if fingerprint and set(m['artifacts'])!=set(SEGMENT_FILES):
        raise ValueError('segment artifact set differs')
    for name,expected in m['artifacts'].items():
        if digest(folder/name)!=expected:raise ValueError('artifact corruption: '+str(folder/name))
    return m


def old9(symbol):
    signals=read_rows(STRICT/'segments'/symbol/'signals.jsonl.gz')
    cancels={r['signal_id']:r for r in read_rows(STRICT/'segments'/symbol/'cancellations.jsonl.gz')}
    return [{'old_signal':r,'strict_cancel':cancels[r['signal_id']],
             'source_cancel':None,'strict_cancel_snapshot':None} for r in signals]


def audit_old9(rows,series,now,c):
    for row in rows:
        signal=row['old_signal'];ready=datetime.fromisoformat(signal['known_at'])
        if ready>=now:continue
        s=sign(signal['direction']);e=signal['evidence'];h=series[signal['htf']];l=series[signal['ltf']]
        hclose=h.candles[h.index] if h.index>=0 else None
        lclose=l.candles[l.index] if l.index>=0 else None
        local=e['ltf_poi'];parent=e['htf_poi'];flow=e['order_flow']
        local_bad=lclose is not None and lclose.close_time==now and s*(lclose.close-(local['low'] if s==1 else local['high']))<0
        parent_bad=hclose is not None and hclose.close_time==now and s*(hclose.close-(parent['low'] if s==1 else parent['high']))<0
        protected_bad=hclose is not None and hclose.close_time==now and s*(hclose.close-flow['structure']['protected'])<=0
        dest=flow['destination_poi'];dest_known=datetime.fromisoformat(dest['known_at'])
        global_test=dest_known<=c.open_time and c.low<=dest['high'] and c.high>=dest['low']
        flags={'entry_poi_native_body_invalid':local_bad,'parent_poi_native_body_invalid':parent_bad,
               'frozen_htf_thesis_body_invalid':protected_bad,'fixed_global_destination_tested':global_test,
               'generic_ltf_state':l.trend.value,'hta_flow_snapshot':json.loads(evidence_json(h.flow)),
               'old_FTA_is_fixed_global_destination':e['fta']['zone_id']==dest['zone_id']}
        if row['source_cancel'] is None and any((local_bad,parent_bad,protected_bad,global_test)):
            reason='FIXED_GLOBAL_DESTINATION_TESTED' if global_test else 'SOURCE_POI_OR_FROZEN_HTF_THESIS_INVALIDATED'
            row['source_cancel']={'signal_id':signal['signal_id'],'cohort':'CANCEL_SOURCE_POI_INVALIDATION',
                                  'known_at':now,'reason':reason,'classification':'SOURCE_RULE_WITH_DECLARED_BODY_TOUCH_INTERPRETATION',
                                  'source':'SW9 p2–10; SW5 p3–5; SW22 p6'}
        if now==datetime.fromisoformat(row['strict_cancel']['known_at']):
            row['strict_cancel_snapshot']={'known_at':now,'flags':flags,
                'classification':'SOURCE_RULE_SUPPORTED' if any((local_bad,parent_bad,protected_bad,global_test)) else 'SOURCE_INTERPRETATION_GENERIC_LTF_OR_NON_GLOBAL_FTA',
                'source':'SW22 p6 global destination; SW5 protected thesis; SW9 POI; generic later LTF state is not universal'}


def path_assessment(engine,trade,now):
    """Only old quote/SL/READY evidence, never old future result, selects proof."""
    h,l=engine.series[trade['htf']],engine.series[trade['ltf']]
    direction=trade['direction'];s=sign(direction);entry=trade['entry_reference'];stop=trade['stop']
    candidates=[q for q in l.zone_registry.values() if q.direction==direction and q.known_at<=now
                and q.low<=entry<=q.high and q.fresh(now)]
    rows=[]
    for q in candidates:
        bos=l.bos.get(direction)
        trend_flow=engine._active_flow(h,direction)
        fixed_stop=s*((q.low if s==1 else q.high)-stop)>0
        quote_exact=abs(entry-(q.high if s==1 else q.low))<1e-10 or abs(entry-(q.low+q.high)/2)<1e-10
        rows.append({'poi':asdict(q),'entry_inside_real_source_zone':True,'fixed_stop_outside_whole_zone':fixed_stop,
                     'deterministic_edge_or_half_quote':quote_exact,'htf_flow':json.loads(evidence_json(trend_flow)),
                     'ltf_bos':dict(bos) if bos else None,'source_path_family':'OB_DIRECT' if q.kind=='ORDER_BLOCK' else 'BOS_NEW_POI',
                     'formation_stop_candidate_only_not_complete_source_proof':bool(fixed_stop and trend_flow and bos),
                     'exact_registered_primary_quote':quote_exact})
    matching=[{'signal_id':r.signal_id,'path_id':r.evidence['path_id'],
               'physical_opportunity_id':r.evidence['physical_opportunity_id'],'quote':r.entry,'stop':r.stop,
               'known_at':r.known_at} for r in engine.signals if r.htf==trade['htf'] and r.ltf==trade['ltf']
               and r.direction==direction and r.known_at<=now and abs(r.entry-entry)<1e-10
               and not any(c['signal_id']==r.signal_id and c['cohort']==engine.policy['primary_cancellation']
                           and instant(c['known_at'])<=now for c in engine.cancellations)]
    return {'known_at':now,'all_source_local_candidates_at_old_quote':rows,
            'registered_paths_at_exact_old_quote':matching,
            'assessment':'ACTUAL_REGISTERED_SOURCE_READY_AT_EXACT_OLD_QUOTE' if matching
                         else 'EXACT_OLD_CASE_NOT_PROVEN_BY_ALL_REGISTERED_SOURCE_PATHS',
            'candidate_zone_does_not_prove_missing_parent_reaction_PD_OR_confirmation':True,
            'old_outcome_not_used_for_classification':True,'trade_entry_allowed':False}


def detect_symbol(symbol,folder,inputs,code_hash,policy):
    fingerprint=sha256(evidence_json({'code':code_hash,'inputs':inputs,'symbol':symbol}).encode()).hexdigest()
    if folder.exists():return verify_manifest(folder,fingerprint)
    folder.mkdir(parents=True)
    series,strict_series={},{}
    data_audit=[];admissibility=[]
    for tf in policy['native_timeframes']:
        print(f'{symbol} analyze native {tf}m',flush=True)
        path=REPO/inputs[str(tf)]['path'];raw=read_klines_csv(path)
        if len(raw)!=inputs[str(tf)]['candles'] or any(r.exchange!='BYBIT' or r.symbol!=symbol or r.interval!=str(tf) for r in raw):
            raise ValueError('native Bybit identity/count mismatch')
        cs=[r.to_strategy_candle(tf*60000) for r in raw]
        gaps=sum(b.open_time!=a.close_time for a,b in itertools.pairwise(cs))
        if gaps or any(int(c.open_time.timestamp())%(tf*60) or not c.is_closed for c in cs):
            raise ValueError('native gaps/alignment/closed mismatch')
        report=analyze_market(cs,timeframe_minutes=tf)
        ranges=None
        if tf!=5:
            for tolerance in policy['range_admissibility_sensitivity']:
                r=analyze_ranges(cs,report,params=RangeDetectionParams(midpoint_tolerance_fraction=tolerance))
                admissibility.append({'tf':tf,'midpoint_tolerance':tolerance,'classification':'RESEARCH_PARAMETER',
                                      'ever_validated':sum(x.midpoint_reaction_time is not None for x in r.ranges),
                                      'SFP_events':len(r.events),'PnL_used':False})
                if tolerance==policy['range_midpoint_tolerance']:ranges=r
        series[tf]=SourceSeries(symbol,tf,cs,report,ranges)
        strict_series[tf]=StrictSeries(symbol,tf,cs,report,ranges)
        data_audit.append({'symbol':symbol,'interval':tf,'exchange':'BYBIT','instrument':'USDT_LINEAR_PERPETUAL',
                           'count':len(cs),'start':cs[0].open_time,'end':cs[-1].close_time,
                           'gaps':gaps,'OHLC':'PASS_BY_VALIDATED_NATIVE_MODEL','alignment':'PASS',
                           'sha256':digest(path),'source_receipt':inputs[str(tf)]})
    engine=SourceEngine(symbol,series,policy)
    strict=StrictBottleneckAudit(symbol,strict_series,mappings=((15,5),(60,5),(60,15),(240,5),(240,15),(240,60)))
    original=load_intermediate(symbol)
    old_orders=old9(symbol)
    merged=heapq.merge(*[[(c.close_time,-tf,tf,i) for i,c in enumerate(s.candles)] for tf,s in series.items()])
    last_log=time.monotonic()
    for now,group in itertools.groupby(merged,key=lambda row:row[0]):
        group=list(group);changed={r[2] for r in group}
        for _,_,tf,index in group:
            strict.advance(tf,index)
            engine.advance(tf,index)
        engine.evaluate(now,changed)
        native=series[5].candles[series[5].index]
        audit_old9(old_orders,series,now,native)
        for row in original:
            for field in ('ready_time','entry_interval_start'):
                if now==datetime.fromisoformat(row['old_trade'][field]):
                    row['snapshots'][field]={**intermediate_snapshot(engine,row['old_trade'],now),
                                             'permitted_path_assessment':path_assessment(engine,row['old_trade'],now)}
        if time.monotonic()-last_log>30:
            print(f'{symbol} observed through {now.isoformat()}; source contexts={len(engine.registry.assignments)} path READY={len(engine.signals)}',flush=True)
            last_log=time.monotonic()
    # A read-only bottleneck replay must reproduce the archived strict detector exactly.
    saved=read_rows(STRICT/'segments'/symbol/'signals.jsonl.gz')
    assert evidence_json(saved)==evidence_json([asdict(s) for s in strict.signals]),'strict audit changed signals'
    assert evidence_json(read_rows(STRICT/'segments'/symbol/'cancellations.jsonl.gz'))==evidence_json(strict.cancellations),'strict audit changed cancellations'
    write_rows(folder/'signals.jsonl.gz',(asdict(s) for s in engine.signals))
    write_rows(folder/'cancellations.jsonl.gz',engine.cancellations)
    write_rows(folder/'exit_events.jsonl.gz',engine.exit_events)
    write_rows(folder/'attempts.jsonl.gz',engine.attempts)
    write_rows(folder/'flow_history.jsonl.gz',({'tf':tf,**r} for tf,s in series.items() for r in s.flow_history))
    write_rows(folder/'flow_bottleneck.jsonl.gz',({'tf':tf,**r} for tf,s in series.items() for r in s.flow_audit))
    write_rows(folder/'range_audit.jsonl.gz',({'tf':tf,**r} for tf,s in series.items() for r in s.range_audit))
    write_rows(folder/'strict_bottleneck.jsonl.gz',strict.audit)
    write_json(folder/'old13_audit.json',original)
    write_json(folder/'old9_cancel_audit.json',old_orders)
    write_json(folder/'range_admissibility.json',admissibility)
    write_json(folder/'physical_anchors.json',[a for rows in engine.registry.anchors.values() for a in rows])
    write_json(folder/'dataset_audit.json',data_audit)
    summary=engine.finish();summary['strict_readonly_detector_parity']='PASS';summary['strict_liquidity_POI_contexts']=sum('liquidity_passed' in s.stages for s in strict.setups if [s.htf,s.ltf] in policy['mappings'])
    write_json(folder/'summary.json',summary)
    manifest={'status':'COMPLETE','fingerprint':fingerprint,'code_hash':code_hash,'inputs':inputs,
              'artifacts':{name:digest(folder/name) for name in SEGMENT_FILES},'trade_entry_allowed':False}
    write_json(folder/'manifest.json',manifest)
    print(f'{symbol} COMPLETE source paths={summary["paths"]}',flush=True)
    return manifest


def case_stats(rows):
    result=stats(rows)
    pnl=peak=dd=0.0
    for t in sorted(rows,key=lambda t:(instant(t['exit_time']),t['physical_opportunity_id'])):
        pnl+=t['net_pnl'];peak=max(peak,pnl);dd=max(dd,peak-pnl)
    result['MaxDrawdown']=dd if rows else None
    result['MaxDrawdownFraction']=None
    result['drawdown_scope']='CUMULATIVE_INDEPENDENT_CASE_NET_PNL_BY_EXIT_TIME; NOT_SHARED_NAV'
    return result


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value,str) else value


def execute(output,policy):
    signals=[];cancels=defaultdict(list);exits=defaultdict(list)
    old_orders=[]
    for symbol in policy['symbol_priority']:
        folder=output/'segments'/symbol
        for r in read_rows(folder/'signals.jsonl.gz'):
            signals.append(SourceSignal(**{**r,'known_at':instant(r['known_at']),
                                            'targets':tuple(r['targets']),'fractions':tuple(r['fractions'])}))
        for r in read_rows(folder/'cancellations.jsonl.gz'):cancels[r['signal_id']].append(r)
        for r in read_rows(folder/'exit_events.jsonl.gz'):exits[r['signal_id']].append(r)
        old_orders+=json.loads((folder/'old9_cancel_audit.json').read_text())
    definitions={'SOURCE_PERMITTED_UNION':None}
    definitions.update({name:set(paths) for name,paths in policy['family_cohorts'].items()})
    definitions.update({p['path_id']:{p['path_id']} for p in policy['paths']})
    selected_by_cohort={}
    for name,paths in definitions.items():
        allowed=signals if paths is None else [s for s in signals if s.evidence['path_id'] in paths]
        selected,duplicates=select_union(allowed,policy)
        selected_by_cohort[name]=selected
        write_rows(output/'selections'/f'{name}.jsonl.gz',({'signal_id':s.signal_id,
                  'physical_opportunity_id':s.evidence['physical_opportunity_id'],'known_at':s.known_at,
                  'path_id':s.evidence['path_id']} for s in selected))
        write_rows(output/'selections'/f'{name}_duplicates.jsonl.gz',duplicates)
    write_json(output/'pre_execution_selection_receipt.json',{'selection_uses_future_outcomes':False,
        'selection_rule':policy['selection'],'path_precedence':policy['entry_tie_precedence'],
        'selection_sha256':{p.relative_to(output).as_posix():digest(p) for p in (output/'selections').glob('*')},
        'primary_cancellation':policy['primary_cancellation'],'trade_entry_allowed':False})
    candles={symbol:[c.to_strategy_candle(300000) for c in read_klines_csv(REPO/f'data/history/bybit/{symbol}/5.csv')]
             for symbol in policy['symbol_priority']}
    risk=SourceRiskPolicy(initial_equity=policy['case_reference_equity'],risk_fraction=policy['risk_fraction'],
                          fee_rate=policy['fee_rate'],slippage_fraction=policy['slippage_fraction'])
    cache={};summaries={}
    for name,selected in selected_by_cohort.items():
        for cancellation in policy['cancellation_cohorts']:
            trades=[];decisions=[]
            for s in selected:
                key=(s.signal_id,cancellation)
                if key not in cache:
                    account=replay_case(s,candles[s.symbol],cancels[s.signal_id],exits[s.signal_id],risk,cancellation)
                    cache[key]=(account.trades,account.decisions)
                ts,ds=cache[key];trades+=ts;decisions+=ds
            trades.sort(key=lambda t:(instant(t['entry_interval_start']),instant(t['ready_time']),
                                      -t['htf'],t['ltf'],policy['symbol_priority'].index(t['symbol']),t['signal_id']))
            closed=[t for t in trades if t['status']=='CLOSED'];primary=closed[:50]
            folder=output/'cohorts'/name/cancellation;folder.mkdir(parents=True,exist_ok=True)
            write_rows(folder/'cases.jsonl.gz',trades);write_rows(folder/'primary_cases.jsonl.gz',primary)
            write_rows(folder/'case_decisions.jsonl.gz',decisions)
            breakdown={}
            for dimension in ('path','setup','POI','direction','symbol','mapping'):
                groups=defaultdict(list)
                for t in primary:
                    key=t['path_id'] if dimension=='path' else next(p['setup_family'] for p in policy['paths'] if p['path_id']==t['path_id']) if dimension=='setup' else t['poi_type'] if dimension=='POI' else f'{t["htf"]}/{t["ltf"]}' if dimension=='mapping' else t[dimension]
                    groups[key].append(t)
                breakdown[dimension]={key:case_stats(rows) for key,rows in groups.items()}
            summary={'cohort':name,'cancellation_cohort':cancellation,'READY':len(selected),
                     'raw_variant_READY':len(signals) if definitions[name] is None else sum(s.evidence['path_id'] in definitions[name] for s in signals),
                     'FILLED':len(trades),'CLOSED':len(closed),'OPEN':len(trades)-len(closed),
                     'PENDING':sum(d['reason']=='PENDING_RIGHT_CENSORED' for d in decisions),
                     'primary_closed_count':len(primary),'primary':case_stats(primary),'all_closed':case_stats(closed),
                     'breakdowns':breakdown,'decisions':dict(Counter(d['reason'] for d in decisions)),
                     'shared_capital':False,'trade_entry_allowed':False}
            write_json(folder/'summary.json',summary)
            summaries[f'{name}/{cancellation}']=summary
    controlled=[]
    for r in old_orders:
        original=r['old_signal'];e=original['evidence']
        signal=SourceSignal(**{**original,'known_at':instant(original['known_at']),
            'targets':tuple(original['targets']),'fractions':tuple(original['fractions']),
            'evidence':{**e,'path_id':'OB_ULTRA_CONSERVATIVE_CONF','physical_opportunity_id':'OLD9:'+original['signal_id']}})
        strict={**r['strict_cancel'],'cohort':'CANCEL_STRICT_STRUCTURE'}
        source=[r['source_cancel']] if r['source_cancel'] else []
        for cohort in policy['cancellation_cohorts']:
            case=replay_case(signal,candles[signal.symbol],[strict]+source,(),risk,cohort)
            controlled.append({'old_signal_id':signal.signal_id,'cancellation_cohort':cohort,
                               'cases':case.trades,'decisions':case.decisions})
    write_json(output/'controlled_old9_execution.json',controlled)
    write_json(output/'summary.json',{'status':'COMPLETE_FULL_NATIVE_SOURCE_PERMITTED_REPLAY',
        'native_series':40,'candles':993575,'paths':len(policy['paths']),'cohorts':summaries,
        'primary':summaries['SOURCE_PERMITTED_UNION/'+policy['primary_cancellation']],
        'trade_entry_allowed':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--resume-existing',action='store_true')
    p.add_argument('--workers',type=int,default=4,choices=range(1,5))
    a=p.parse_args();output=a.output.resolve();policy=json.loads(POLICY.read_text())
    if policy['trade_entry_allowed'] is not False or policy['mode'] not in ('BACKTEST','SHADOW'):raise ValueError('unsafe policy')
    if output.exists() and not a.resume_existing:raise ValueError('existing output requires exact --resume-existing')
    inputs=json.loads((STRICT/'run_lock.json').read_text())['inputs']
    if len(inputs)!=40 or sum(r['candles'] for r in inputs.values())!=993575:raise ValueError('full40 native series required')
    for path,row in inputs.items():
        if digest(REPO/path)!=row['sha256']:raise ValueError('native input SHA differs')
    implementation={path:digest(REPO/path) for path in IMPLEMENTATION}
    request={'implementation':implementation,'inputs':inputs,'policy':policy,'trade_entry_allowed':False}
    code_hash=sha256(evidence_json(implementation).encode()).hexdigest()
    if (output/'run_lock.json').exists() and json.loads((output/'run_lock.json').read_text())!=request:
        raise ValueError('lock differs; retain old output and use fresh root')
    if (output/'manifest.json').exists():
        verify_manifest(output)
        for symbol in policy['symbol_priority']:
            native={str(tf):inputs[f'data/history/bybit/{symbol}/{tf}.csv'] for tf in policy['native_timeframes']}
            fingerprint=sha256(evidence_json({'code':code_hash,'inputs':native,'symbol':symbol}).encode()).hexdigest()
            verify_manifest(output/'segments'/symbol,fingerprint)
        print(json.dumps({'resume':'VERIFIED_COMPLETE_NO_MUTATION','segments':10,'trade_entry_allowed':False},indent=2))
        return
    output.mkdir(parents=True,exist_ok=True);write_json(output/'run_lock.json',request)
    jobs=[(symbol,output/'segments'/symbol,
           {str(tf):inputs[f'data/history/bybit/{symbol}/{tf}.csv'] for tf in policy['native_timeframes']},
           code_hash,policy) for symbol in policy['symbol_priority']]
    if a.workers==1:
        for job in jobs:detect_symbol(*job)
    else:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            futures=[pool.submit(detect_symbol,*job) for job in jobs]
            for future in futures:future.result()
    (output/'selections').mkdir(parents=True,exist_ok=True)
    execute(output,policy)
    artifacts={p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*'))
               if p.is_file() and p!=output/'manifest.json'}
    write_json(output/'manifest.json',{'status':'COMPLETE','code_hash':code_hash,'artifacts':artifacts,'trade_entry_allowed':False})
    result=json.loads((output/'summary.json').read_text())['primary']
    print(json.dumps({'cohort':result['cohort'],'READY':result['READY'],'FILLED':result['FILLED'],
                      'CLOSED':result['CLOSED'],'first50':result['primary'],'trade_entry_allowed':False},indent=2),flush=True)


if __name__=='__main__':main()
