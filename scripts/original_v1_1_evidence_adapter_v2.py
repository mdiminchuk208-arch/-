"""SOURCE_FAITHFUL_HISTORICAL_EVIDENCE_ADAPTER_v2: evidence only, never execution."""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from decimal import Decimal

from original_strategy_executable_profile_v1 import (
    ACTIVE,
    digest,
    encode,
    evaluate,
    stop_price,
)
from original_v1_1_objective_geometry_v2 import contextual_fta, source_known_at

VERSION = 'SOURCE_FAITHFUL_HISTORICAL_EVIDENCE_ADAPTER_v2'
FORBIDDEN = {'pnl','net_pnl','gross_pnl','winrate','win_rate','profit_factor','expectancy','avg_r',
    'holding_time','future_holding_time','outcome','win','loss','mfe','mae','future_return',
    'baseline_result','old_tree_prediction','old751','adverse_liquidity_label','owner_tf',
    'macro_context','fta_label','range_tolerance','significance','branch_owner','fitted_tree',
    'old_no_htf_context','no_htf_context','h1_h4_owner','old_fta','mfe_r','mae_r','win_loss'}
QUALITATIVE = {
    'market_context': ['S_STRUCTURE'], 'liquidity_context':['S_LIQUIDITY_CONTEXT'],
    'ob_formation':['S_OB_FORMATION'], 'higher_poi':['S_OB_FORMATION'], 'trend_aligned':['S_OB_TREND','S_STB_FORMATION'],
    'smooth_approach':['S_OB_APPROACH'], 'reaction_bos_new_poi':['S_OB_CONS_TRIGGER'],
    'breaker_formation':['S_BREAKER_FORMATION'], 'flow_context':['S_FLOW'], 'poi_reaction':['S_POI'],
    'stb_raid_absorption_structure':['S_STB_FORMATION'], 'pd_context':['S_PD'],
    'clear_range':['S_RANGE_FORMATION'], 'range_deviation':['S_RANGE_DEVIATION'],
    'outside_poi':['S_RANGE_AGGRESSIVE'], 'range_reclaim_retest':['S_RANGE_CONSERVATIVE'],
    'return_choch_zone':['S_RANGE_CONSERVATIVE'], 'ltf_bos_source_entry':['S_SFP_REFINE'],
    'breaker_confirmation':['S_BREAKER_FORMATION'], 'sl_off_liquidity':['S_SL_OFF_POOL'],
    'meaningful_liquidity':['S_LIQUIDITY_CONTEXT'], 'adverse_liquidity':['S_ADVERSE_BLOCK','S_ADVERSE_WAIT'],
    'whole_impulse':['S_BREAKER_FORMATION'], 'reasonable_tilt':['S_EQ_STRUCTURE'],
    'protected_endpoints':['S_STRUCTURE','S_BOS'], 'contextual_poi_relation':['S_POI','S_FTA'],
    'selected_impulse':['S_OTE','S_PD'], 'selected_range':['S_RANGE_FORMATION','S_PD'],
    'zone_first_test':['S_OB_FIRST_TEST'], 'inventory_completeness':['S_FTA','S_POOL_SCOPE'],
    'source_stop_anchor':['S_PLAN'], 'branch_confirmation':['S_BOS','S_CONF'],
}
BRANCH_CONCEPTS = {
    'SFP':['market_context','liquidity_context','meaningful_liquidity','protected_endpoints','ltf_bos_source_entry'],
    'OB_CONSERVATIVE':['market_context','ob_formation','higher_poi','trend_aligned','smooth_approach','reaction_bos_new_poi'],
    'BREAKER':['market_context','breaker_formation','whole_impulse','flow_context','poi_reaction','breaker_confirmation'],
    'STB_BTS':['market_context','trend_aligned','stb_raid_absorption_structure','flow_context','pd_context','selected_impulse'],
    'RANGE_CONSERVATIVE':['market_context','clear_range','protected_endpoints','range_deviation','outside_poi','range_reclaim_retest'],
    'RANGE_RETURN_CHOCH':['market_context','clear_range','protected_endpoints','range_deviation','return_choch_zone','range_reclaim_retest'],
}


def no_outcomes(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key.lower() in FORBIDDEN:
                raise ValueError('Outcome/legacy truth input forbidden: '+key)
            no_outcomes(item)
    elif isinstance(value,(list,tuple)):
        for item in value:
            no_outcomes(item)


def metadata_at(registry, symbol, at):
    matches=[]
    required={'tick_size','price_precision','qty_step','quantity_precision','minimum_qty',
              'contract_type','linear_perpetual','base_asset','quote_asset'}
    for r in registry['records']:
        if r['symbol']!=symbol or not r['effective_from']<=at<r['effective_to']:
            continue
        if r['verification_status']!='VERIFIED_HISTORICAL':
            continue
        p=r.get('provenance',{}); values=r.get('values',{})
        if (not required<=values.keys() or not p.get('source_sha256') or not p.get('authoritative')
            or type(p.get('historical_known_at')) is not int or p['historical_known_at']>at
            or p.get('effective_period_proof') is not True):
            continue
        if (values['linear_perpetual'] is not True or values['contract_type']!='LinearPerpetual'
            or Decimal(values['tick_size'])<=0 or Decimal(values['qty_step'])<=0 or Decimal(values['minimum_qty'])<=0):
            raise ValueError('Invalid verified instrument identity/filters')
        matches.append({**values,'known_at':p['historical_known_at'],'completed_at':p['historical_known_at'],
                        'evidence':'Historical effective-date proof '+p['source_sha256']})
    if len(matches)>1:
        raise ValueError('Overlapping verified instrument metadata periods')
    return matches[0] if matches else None


def validate_annotation(record, objects, decision_at):
    no_outcomes(record)
    required={'concept','state','object_ids','source_rule_ids','decision_at','known_at',
              'completed_at','allowed_window','annotator_id','rationale','provenance'}
    if not required<=record.keys() or record['concept'] not in QUALITATIVE or record['state'] not in ('PASS','FAIL','UNKNOWN'):
        raise ValueError('Invalid qualitative annotation schema')
    if (record['decision_at']!=decision_at or not 0<=record['completed_at']<=record['known_at']<=decision_at
        or len(record['allowed_window'])!=2 or record['allowed_window'][1]>record['known_at']
        or record['allowed_window'][0]>record['allowed_window'][1] or not record['annotator_id']
        or not record['rationale'] or not record['provenance'].get('blinded_pack_sha256')):
        raise ValueError('Noncausal/unproven annotation')
    if not set(record['source_rule_ids'])<=set(QUALITATIVE[record['concept']]) or not record['source_rule_ids']:
        raise ValueError('Annotation citation is not applicable SOURCE_RULE')
    if not record['object_ids'] or any(k not in objects or source_known_at(objects[k])>record['known_at'] for k in record['object_ids']):
        raise ValueError('Annotation references absent/future object')
    return record


def annotation_fact(records, concept, objects, at):
    selected=[validate_annotation(r,objects,at) for r in records if r['concept']==concept]
    if not selected or len({r['state'] for r in selected})!=1 or selected[0]['state']=='UNKNOWN':
        return None
    return {'value':selected[0]['state']=='PASS','known_at':max(r['known_at'] for r in selected),
        'completed_at':max(r['completed_at'] for r in selected),'source_validated':True,
        'evidence':'Blinded audited annotation '+digest(selected), 'annotation_ids':[digest(r) for r in selected]}


def attest_existing_object(source_object, annotations, concept, objects, at):
    """Preserve founding ID/payload; add explicit audited selection evidence only."""
    records=[r for r in annotations if r['concept']==concept and source_object['id'] in r['object_ids']]
    fact=annotation_fact(records,concept,objects,at)
    if not fact or not fact['value']:
        return None
    if source_known_at(source_object)>at:
        return None
    import copy
    result=copy.deepcopy(source_object)
    result['source_validated']=True
    result['source_attestation']=fact
    if concept=='protected_endpoints':
        result['protected_endpoint']=True
    if concept in ('selected_impulse','selected_range'):
        result['selected_source_endpoint']=True
    return result


def causal_record(record, at):
    if not isinstance(record,dict):
        return False
    return (type(record.get('known_at')) is int and type(record.get('completed_at')) is int
            and 0<=record['completed_at']<=record['known_at']<=at and bool(record.get('evidence')))


def identity_records(symbol, context, formation, confirmation, poi):
    if not all(o and o.get('source_validated') for o in (context,formation,confirmation,poi)):
        return {}
    records={k:{'id':o['id'],'known_at':source_known_at(o),'completed_at':o['completed_at'],'evidence':o['evidence']}
             for k,o in [('context',context),('formation',formation),('confirmation',confirmation),('poi',poi)]}
    physical=digest([symbol,context['id'],poi['id']])
    setup=digest([physical,formation['payload']['direction'],formation['id'],confirmation['id']])
    return {'records':records,'physical_idea_id':physical,'setup_id':setup}


def source_entry_poi(branch, direction, at, original, candidates, *, reaction=None, bos=None, confirmation=None):
    """Unique validated source POI only, never nearest/highest-return retrospective pick."""
    eligible=[o for o in candidates if o.get('source_validated') and source_known_at(o)<=at
              and o['payload'].get('direction')==direction and o['payload'].get('parent_poi_id')==original['id']]
    if branch in ('SFP','OB_CONSERVATIVE'):
        if not causal_record(reaction,at) or not causal_record(bos,at) or bos.get('tf')!=15 or reaction['known_at']>bos['known_at']:
            return None
        eligible=[o for o in eligible if o['payload'].get('formation_known_at',-1)>=bos['known_at']]
    else:
        if not causal_record(confirmation,at):
            return None
        eligible=[o for o in eligible if o['payload'].get('confirmation_id')==confirmation.get('id')]
    if len(eligible)!=1:
        return None
    o=eligible[0]; p=o['payload']
    if not 0<Decimal(p['low'])<Decimal(p['high']):
        return None
    return {'id':o['id'],'low':p['low'],'high':p['high'],'parent_poi_id':original['id'],
            'formation_known_at':p.get('formation_known_at',o['known_at']),'known_at':o['known_at'],
            'completed_at':o['completed_at'],'source_validated':True,'evidence':o['evidence']}


def source_stop(branch, direction, source_object, at):
    if not source_object or not source_object.get('source_validated') or source_known_at(source_object)>at:
        return None
    p=source_object['payload']; long=direction=='LONG'
    key=('low' if long else 'high')
    if branch=='BREAKER':
        key='raid_impulse_low' if long else 'raid_impulse_high'
    if not (source_object.get('unique_anchor') or p.get('unique_anchor')) or key not in p:
        return None
    kind={'SFP':'SFP_PATTERN_EXTREME','OB_CONSERVATIVE':'SOURCE_OB_EXTREME','BREAKER':'RAID_IMPULSE_EXTREME',
          'STB_BTS':'MANIPULATION_RAID_EXTREME','RANGE_CONSERVATIVE':'DEVIATION_INVALIDATION_EXTREME',
          'RANGE_RETURN_CHOCH':'DEVIATION_INVALIDATION_EXTREME'}[branch]
    return {'kind':kind,'price':p[key],'unique':True,'source_validated':True,
        'known_at':source_known_at(source_object),'completed_at':source_object['completed_at'],'evidence':source_object['evidence']}


def liquidity_role(pool, annotation, direction, entry, at):
    """No role inference from price alone or automatic pass after sweep."""
    no_outcomes(annotation)
    fields={'pool_id','tf','entry_relation','setup_direction','structure_relation','source_rule_ids','role','known_at','evidence'}
    if (not fields<=annotation.keys() or annotation['pool_id']!=pool['id'] or annotation['tf']!=pool['tf']
        or annotation['setup_direction']!=direction or not pool['known_at']<=annotation['known_at']<=at
        or annotation['role'] not in ('ADVERSE','TARGET_OR_FUEL','NEUTRAL','UNKNOWN')
        or not annotation['structure_relation'] or not annotation['evidence']
        or not set(annotation['source_rule_ids'])<=set(QUALITATIVE['adverse_liquidity']+QUALITATIVE['meaningful_liquidity'])):
        raise ValueError('Incomplete liquidity role proof')
    price=Decimal(pool['payload']['price']); quote=Decimal(entry)
    relation='ABOVE' if price>quote else 'BELOW' if price<quote else 'AT_ENTRY'
    if annotation['entry_relation']!=relation:
        raise ValueError('Incorrect entry/pool relation')
    return {**annotation,'id':pool['id'],'completed_at':pool['completed_at'],
            'source_validated':annotation['role']!='UNKNOWN'}


def build_case(raw,index,metadata,*,mode='BACKTEST',annotations=(),selection=None,source_registry=None):
    no_outcomes(raw)
    if mode not in ('BACKTEST','SHADOW'):
        raise ValueError('Offline modes only')
    at=raw['decision_at']; branch=raw['branch']; direction=raw['direction']
    objects=source_registry if source_registry is not None else index.by_id
    instrument=metadata_at(metadata,raw['symbol'],at)
    case={k:raw[k] for k in ('branch','symbol','direction','setup_tf','decision_at','event')}
    case.update(mode=mode,trigger_tf=15,instrument_metadata=instrument,
                tick_size=instrument['tick_size'] if instrument else None,facts={},liquidity=[],
                entry_poi=None,stop_anchor=None,identity_evidence={},trade_entry_allowed=False)
    if branch not in ACTIVE:
        return case
    for name in BRANCH_CONCEPTS[branch]+['sl_off_liquidity']:
        fact=annotation_fact(annotations,name,objects,at)
        if fact:
            case['facts'][name]=fact
    formation_at=raw.get('formation_at',at)
    if branch=='SFP':
        sfps=[o for o in index.event_objects(formation_at,'SFP') if o['payload']['direction']==direction]
        if len(sfps)==1:
            sfp=sfps[0]; level=index.by_id[sfp['payload']['level_id']]
            _,bar=index.bar_at(formation_at)
            case['sfp']={'raid':bar.observed(index.tf),'old_level':{**level,'price':level['payload']['price']},
                         'next_open':index.next_open(formation_at,at)}
            case['atr_bars']=index.atr_bars(formation_at)
            # SFP pattern extreme is objective, unlike externality/context.
            case['stop_anchor']={**bar.observed(index.tf),'kind':'SFP_PATTERN_EXTREME',
                'price':str(bar.low if direction=='LONG' else bar.high),'unique':True,'source_validated':True}
    if not selection:
        case.update(contextual_poi_inventory=None,liquidity_inventory=None)
        return case
    # Explicit source-selected geometry; every selected object is checked and cited.
    no_outcomes(selection)
    objs={k:objects[v] for k,v in selection.get('objects',{}).items()}
    for o in objs.values():
        if source_known_at(o)>at or not o.get('source_validated'):
            raise ValueError('Selected object lacks causal SOURCE validation')
    original=objs.get('poi')
    if original:
        candidates=[objects[k] for k in selection.get('entry_candidates',[])]
        case['entry_poi']=source_entry_poi(branch,direction,at,original,candidates,
            reaction=selection.get('reaction'),bos=selection.get('bos'),confirmation=objs.get('confirmation'))
        case['idea_poi_id']=original['id']
    case['stop_anchor']=source_stop(branch,direction,objs.get('stop'),at) or case['stop_anchor']
    if objs.get('stop') and branch!='SFP':
        s=objs['stop']; p=s['payload']; low=p.get('raid_impulse_low',p.get('low')); high=p.get('raid_impulse_high',p.get('high'))
        case['source_defining_zone']={'id':s['id'],'low':low,'high':high,'known_at':source_known_at(s),
            'completed_at':s['completed_at'],'evidence':s['evidence'],'source_validated':True}
    ids=identity_records(raw['symbol'],objs.get('context'),objs.get('formation'),objs.get('confirmation'),original)
    case['identity_evidence']=ids.get('records',{})
    for k in ('reaction','bos','range_exit','liquidity_inventory','liquidity','post_sweep_revalidation','zone_first_test'):
        if k in selection:
            value=selection[k]
            records=value if isinstance(value,list) else [value]
            if any(not causal_record(r,at) for r in records):
                raise ValueError('Future/unproven selected evidence '+k)
            case[k]=value
    inventory=annotation_fact(annotations,'inventory_completeness',objects,at)
    case.update(contextual_fta([objects[k] for k in selection.get('contextual_objects',[])],direction,at,
        annotated_complete=bool(inventory and inventory['value'] and selection.get('inventory_complete') is True),
        consumed=set(selection.get('consumed_ids',[]))))
    if inventory:
        case['contextual_poi_inventory'].update({k:inventory[k] for k in ('known_at','completed_at','evidence')})
    if instrument and case['stop_anchor']:
        stop=stop_price(case)
        if stop is not None and 'sl_off_liquidity' in case['facts']:
            # The annotation must explicitly attest the exact selected stop, no auto-clearance.
            clear=[r for r in annotations if r['concept']=='sl_off_liquidity']
            if clear and all(r.get('checked_price')==encode(stop) for r in clear):
                case['facts']['sl_off_liquidity']['checked_price']=encode(stop)
    return case


def inspect(raw,index,metadata,tree,*,mode='BACKTEST'):
    case=build_case(raw,index,metadata,mode=mode)
    at=raw['decision_at']; branch=raw['branch']; direction=raw['direction']
    rules=[]; fail=[]; unknown=[]
    # Only exact necessary geometry can PASS, never source context/branch admission.
    if branch=='SFP':
        sfp=case.get('sfp')
        if not sfp:
            unknown.append('SFP_STRUCTURAL_REFERENCE')
        else:
            from original_strategy_executable_profile_v1 import sfp_valid
            value=sfp_valid(case)
            rules.append({'rule_id':'S_SFP_FORMATION','component':'raid_reclaim_close','value':value})
            if value is False:
                fail.append('SFP_RAID_RECLAIM')
            nxt=sfp['next_open']
            value=sfp_valid(case,next_open=True) if nxt else None
            rules.append({'rule_id':'S_SFP_FORMATION','component':'next_open','value':value})
            if value is False:
                fail.append('SFP_NEXT_OPEN_NOT_RECLAIMED')
            elif value is None:
                unknown.append('SFP_NEXT_OPEN_UNOBSERVED')
    elif branch in ('OB_CONSERVATIVE','STB_BTS'):
        kind='OB' if branch=='OB_CONSERVATIVE' else 'STB'
        objs=[o for o in index.event_objects(raw.get('formation_at',at),kind) if o['payload']['direction']==direction]
        if not objs:
            unknown.append(kind+'_FORMATION_PRIMITIVE_UNPROVEN')
        else:
            rules.append({'rule_id':'S_OB_FORMATION' if kind=='OB' else 'S_STB_FORMATION',
                          'component':'raid_full_range_engulf','value':True})
    elif branch=='BREAKER':
        # Prior raw OB/body-cross supplies only geometry; cannot certify source OB or impulse.
        if raw.get('anchor') in index.ob_alias:
            rules.append({'rule_id':'S_BREAKER_FORMATION','component':'prior_candidate_only','value':True})
        else:
            unknown.append('PRIOR_SOURCE_OB_UNPROVEN')
    elif branch.startswith('RANGE'):
        if raw.get('primitive')=='PROVISIONAL_SWING_BRACKET_DEVIATION_RECLAIM':
            rules.append({'rule_id':'S_RANGE_DEVIATION','component':'provisional_bracket_only','value':True})
        else:
            unknown.append('SELECTED_RANGE_ENDPOINTS')
    if branch in ('SFP','OB_CONSERVATIVE') and raw['setup_tf']==15:
        unknown.append('WAIT_NO_AVAILABLE_LOWER_TF')
    gaps=['HISTORICAL_INSTRUMENT_METADATA'] if case['instrument_metadata'] is None else []
    concepts=BRANCH_CONCEPTS.get(branch,[])
    gaps += concepts+['adverse_liquidity','contextual_poi_relation','inventory_completeness','zone_first_test']
    if not case['stop_anchor']:
        gaps.append('source_stop_anchor')
    gaps += unknown+['SOURCE_ENTRY_POI','SOURCE_CONFIRMATION','CANONICAL_SOURCE_CONTEXT']
    result=evaluate(case,tree)
    geometry_pass=bool(rules) and not fail and not any('UNPROVEN' in k for k in unknown)
    # Coverage/primitive unknown precedes annotation workload; other gaps remain parallel.
    category='OBJECTIVE_FAIL' if fail else 'UNKNOWN' if unknown else 'QUALITATIVE_REQUIRED' if concepts else 'UNKNOWN'
    if result['SOURCE_STRATEGY_DECISION']=='ALLOW':
        category='EVIDENCE_COMPLETE'
    return {'candidate_id':raw['candidate_id'],'symbol':raw['symbol'],'direction':direction,'setup_tf':raw['setup_tf'],
        'branch':branch,'formation_at':raw.get('formation_at',at),'decision_at':at,'event':raw['event'],
        'category':category,'objective_geometry_pass':geometry_pass,'objective_fail_reasons':fail,
        'qualitative_concepts':concepts,'remaining_unknown':unknown,'missing_evidence':sorted(set(gaps)),
        'evidence_complete':category=='EVIDENCE_COMPLETE','SOURCE_STRATEGY_DECISION':result['SOURCE_STRATEGY_DECISION'],
        'frozen_status':result['status'],'objective_rule_trace':rules,'trade_entry_allowed':False}


def blinded_reference(raw,result,indices):
    at=raw['decision_at']; views={}
    for tf,index in indices.items():
        # All available completed prefix is accessible, no fitted lookback horizon.
        count=bisect_right(index.ends,at)
        views[str(tf)]={'completed_bar_count':count,'last_completed_at':index.ends[count-1] if count else None,
                        'candles_file':f'candles/{raw["symbol"]}_{tf}.jsonl.gz','cutoff':at}
    row={k:result[k] for k in ('candidate_id','symbol','direction','setup_tf','branch','formation_at','decision_at')}
    row.update(views=views,object_cutoff=at,objects_file=f'objects/{raw["symbol"]}_{raw["setup_tf"]}.jsonl.gz',
        required_concepts=result['qualitative_concepts'],source_rule_ids=sorted({r for c in result['qualitative_concepts'] for r in QUALITATIVE[c]}),
        trade_entry_allowed=False)
    no_outcomes(row)
    return row


def summarize(rows):
    counts=Counter(r['category'] for r in rows)
    return {'RAW_PROPOSALS':len(rows),'OBJECTIVE_GEOMETRY_PASS':sum(r['objective_geometry_pass'] for r in rows),
        'OBJECTIVE_SOURCE_FAIL':counts['OBJECTIVE_FAIL'],'QUALITATIVE_REQUIRED':counts['QUALITATIVE_REQUIRED'],
        'EVIDENCE_COMPLETE':counts['EVIDENCE_COMPLETE'],'SOURCE_DECISION_READY':sum(r['SOURCE_STRATEGY_DECISION']=='ALLOW' for r in rows),
        'REMAINING_UNKNOWN':counts['UNKNOWN'],'partition_sum':sum(counts.values()),
        'gap_counts':dict(Counter(g for r in rows for g in r['missing_evidence']).most_common()),
        'geometry_pass_semantics':'Necessary observed primitive only; NOT complete SOURCE validation',
        'status_partition':'OBJECTIVE_FAIL > missing primitive/coverage UNKNOWN > QUALITATIVE_REQUIRED > EVIDENCE_COMPLETE',
        'metadata_gaps_are_parallel':'Qualitative-required can also lack metadata; not added twice to partition',
        'READY_FOR_SECOND_FINANCIAL_BACKTEST':counts['EVIDENCE_COMPLETE']>0,'trade_entry_allowed':False}
