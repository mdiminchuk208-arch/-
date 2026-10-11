"""Independent causal geometry, evidence boundary and blinded-view regression tests."""
from __future__ import annotations

import copy
import csv
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from materialize_original_v1_1_annotation_pack import materialize, read_prefix
from original_strategy_executable_profile_v1 import atr14, digest, load_tree, sfp_valid
from original_v1_1_evidence_adapter_v2 import (
    annotation_fact,
    blinded_reference,
    build_case,
    identity_records,
    inspect,
    liquidity_role,
    metadata_at,
    no_outcomes,
    source_entry_poi,
    source_stop,
    summarize,
    validate_annotation,
)
from original_v1_1_financial_data import ROOT, Bar, write_rows
from original_v1_1_objective_geometry_v2 import (
    ConsumedRegistry,
    GeometryIndex,
    breaker_geometry,
    contextual_fta,
    dealing_geometry,
    object_record,
    pool_scope,
    previous_levels,
    source_structure,
    structure_break,
)

D=ROOT/'docs/original_v1_1_evidence_adapter_v2'


def bars(values,tf=60,start=0):
    return [Bar(start+i*tf*60,start+(i+1)*tf*60,*(Decimal(str(x)) for x in v)) for i,v in enumerate(values)]


def obj(kind='POI',at=7200,tf=60,**payload):
    return object_record(kind,'BTCUSDT',tf,at,payload,['S_POI'],validated=True)


def metadata(lo=0,hi=100000):
    return {'records':[{'symbol':'BTCUSDT','effective_from':lo,'effective_to':hi,'verification_status':'VERIFIED_HISTORICAL',
        'values':{'tick_size':'.1','price_precision':1,'qty_step':'.001','quantity_precision':3,'minimum_qty':'.001',
                  'contract_type':'LinearPerpetual','linear_perpetual':True,'base_asset':'BTC','quote_asset':'USDT'},
        'provenance':{'authoritative':True,'source_sha256':'a'*64,'historical_known_at':lo,'effective_period_proof':True}}]}


def annotation(o,concept='market_context',state='PASS',at=10000):
    from original_v1_1_evidence_adapter_v2 import QUALITATIVE
    return {'concept':concept,'state':state,'object_ids':[o['id']],'source_rule_ids':QUALITATIVE[concept],
        'decision_at':at,'known_at':at,'completed_at':o['completed_at'],'allowed_window':[0,at],
        'annotator_id':'TEST_ONLY_SYNTHETIC','rationale':'Explicit synthetic source relationship for independent QA',
        'provenance':{'blinded_pack_sha256':'b'*64}}


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.bars=bars([(10,11,8,10),(10,12,7,10),(10,11,8,10),(10,13,9,12),(12,12.5,9,11)])
        self.index=GeometryIndex('BTCUSDT',60,self.bars)

    def test_strict_swing_known_only_right_close(self):
        swings=self.index.event_objects(10800,'swing')
        self.assertEqual(len(swings),2)
        self.assertEqual({s['payload']['side'] for s in swings},{'HIGH','LOW'})
        self.assertFalse(self.index.event_objects(7200,'swing'))

    def test_equal_extreme_is_not_strict_swing(self):
        i=GeometryIndex('BTCUSDT',60,bars([(10,12,8,10)]*3))
        self.assertFalse(i.event_objects(10800,'swing'))

    def test_prefix_consistency(self):
        i=GeometryIndex('BTCUSDT',60,self.bars[:3])
        self.assertEqual(i.prefix_objects(10800),self.index.prefix_objects(10800))

    def test_future_mutation_preserves_known_ids(self):
        changed=self.bars[:3]+bars([(500,900,400,800),(800,850,500,700)],start=10800)
        i=GeometryIndex('BTCUSDT',60,changed)
        self.assertEqual(i.prefix_objects(10800),self.index.prefix_objects(10800))

    def test_replay_same_bytes(self):
        self.assertEqual(self.index.prefix_objects(18000),GeometryIndex('BTCUSDT',60,self.bars).prefix_objects(18000))

    def test_incomplete_bar_absent(self):
        self.assertTrue(all(o['known_at']<=10799 for o in self.index.prefix_objects(10799)))
        self.assertFalse(self.index.prefix_objects(10799))

    def test_discontinuous_bars_rejected(self):
        with self.assertRaises(ValueError):
            GeometryIndex('BTCUSDT',60,[self.bars[0],self.bars[2]])

    def test_fvg_three_bar_gap_midpoint(self):
        i=GeometryIndex('BTCUSDT',60,bars([(9,10,8,9),(11,13,10,12),(13,15,12,14)]))
        f=i.event_objects(10800,'FVG')[0]
        self.assertEqual((f['payload']['low'],f['payload']['high'],f['payload']['midpoint']),('10','12','11'))
        self.assertTrue(f['source_validated'])

    def test_equal_gap_edges_no_fvg(self):
        i=GeometryIndex('BTCUSDT',60,bars([(9,10,8,9),(11,13,10,12),(11,14,10,13)]))
        self.assertFalse(i.event_objects(10800,'FVG'))

    def test_pair_classification_is_not_protection(self):
        s=self.index.event_objects(18000,'swing')[0]
        self.assertEqual(s['payload']['pair_classification'],'HH')
        self.assertEqual(s['payload']['protected_endpoint'],'UNKNOWN')

    def test_pools_do_not_become_adverse(self):
        pools=self.index.event_objects(10800,'liquidity_pool')
        self.assertTrue(all(p['payload']['role']=='UNKNOWN' for p in pools))

    def test_sweep_known_at_cross_bar_close(self):
        sweeps=self.index.event_objects(14400,'sweep')
        self.assertEqual(len(sweeps),1)
        self.assertEqual(sweeps[0]['known_at'],14400)

    def test_provisional_ob_never_source_valid(self):
        i=GeometryIndex('BTCUSDT',60,bars([(10,11,8,10),(10,12,7,10),(10,11,8,10),(10,11,6,7),(7,13,5,12)]))
        o=i.event_objects(18000,'OB')[0]
        self.assertFalse(o['source_validated'])
        self.assertEqual(o['payload']['low'],'6')
        self.assertFalse(breaker_geometry(o,self.bars[-1],None,None))

    def test_no_automatic_structure_from_minor_swings(self):
        s=[obj('swing',at=i*1000,side=side,price=str(price)) for i,(side,price) in enumerate([('LOW',7),('HIGH',10),('LOW',8),('HIGH',11)],1)]
        self.assertIsNone(source_structure('BTCUSDT',60,s,5000))
        for o in s:
            o['protected_endpoint']=True
        self.assertEqual(source_structure('BTCUSDT',60,s,5000)['payload']['direction'],'LONG')

    def test_bos_body_not_wick(self):
        s=[obj('swing',at=i*1000,side=side,price=str(price)) for i,(side,price) in enumerate([('LOW',7),('HIGH',10),('LOW',8),('HIGH',11)],1)]
        for o in s: o['protected_endpoint']=True
        st=source_structure('BTCUSDT',60,s,5000)
        b=bars([(9,10,6,9)],start=7200)[0]
        self.assertIsNone(structure_break(st,s[2],b))
        b=bars([(9,10,6,7)],start=7200)[0]
        self.assertEqual(structure_break(st,s[2],b)['payload']['direction'],'SHORT')

    def test_conf_requires_new_structure_attestation(self):
        s=[obj('swing',at=i*1000,side=side,price=str(price)) for i,(side,price) in enumerate([('LOW',7),('HIGH',10),('LOW',8),('HIGH',11)],1)]
        for o in s: o['protected_endpoint']=True
        st=source_structure('BTCUSDT',60,s,5000)
        b=bars([(10,13,9,12)],start=7200)[0]
        self.assertIsNone(structure_break(st,s[-1],b,confirmation=True))
        st['new_structure_after_BOS']=True
        self.assertIsNotNone(structure_break(st,s[-1],b,confirmation=True))

    def test_ote_pd_require_explicit_endpoints(self):
        a,b=obj('swing',at=1000,price='100'),obj('swing',at=2000,price='200')
        self.assertIsNone(dealing_geometry(a,b))
        a['selected_source_endpoint']=b['selected_source_endpoint']=True
        g=dealing_geometry(a,b)
        self.assertEqual(g['payload']['midpoint'],'150')
        self.assertEqual((g['payload']['OTE_low'],g['payload']['OTE_high']),('121','129.5'))

    def test_pool_scope_unknown_without_range(self):
        p=obj('liquidity_pool',price='160')
        self.assertEqual(pool_scope(p,None),'UNKNOWN')
        g=obj('range',at=10000,low='100',high='200')
        self.assertEqual(pool_scope(p,g),'INTERNAL')

    def test_previous_levels_full_day_week_month(self):
        daily=bars([(10,12,8,10)]*40,tf=1440,start=1672531200)
        levels=previous_levels(daily,1675900800)
        self.assertEqual({r['period'] for r in levels},{'DAY','WEEK','MONTH'})
        self.assertTrue(all(r['known_at']<=1675900800 for r in levels))

    def test_partial_first_month_not_previous_month(self):
        daily=bars([(10,12,8,10)]*20,tf=1440,start=1673740800)
        self.assertNotIn('MONTH',{r['period'] for r in previous_levels(daily,1675382400)})

    def test_source_valid_breaker_uses_full_selected_impulse(self):
        ob=obj('OB',at=7200,low='10',high='12',body_low='10.5',body_high='11.5',direction='SHORT')
        st=obj('structure',at=14400,direction='LONG')
        bar=bars([(11,14,10,13)],start=10800)[0]
        whole={'source_validated':True,'value':True,'new_structure_extreme_proven':True,
               'known_at':14400,'completed_at':14400,'interval_start':7200,'interval_end':14400,
               'low':'9','high':'14','evidence':'Synthetic selected whole source impulse'}
        br=breaker_geometry(ob,bar,st,whole)
        self.assertEqual(br['payload']['raid_impulse_low'],'9')
        self.assertEqual(br['payload']['low'],'10.5')
        ob['source_validated']=False
        self.assertIsNone(breaker_geometry(ob,bar,st,whole))

    def test_range_deviation_and_later_retest_components(self):
        from original_v1_1_objective_geometry_v2 import (
            range_deviation_geometry,
            range_retest_geometry,
        )
        r=obj('range',at=7200,low='8',high='12')
        raid=bars([(10,11,7,9)],start=10800)[0]
        dev=range_deviation_geometry(r,raid,'LONG')
        self.assertIsNotNone(dev)
        retest=bars([(9,10,8,9)],start=14400)[0]
        self.assertIsNotNone(range_retest_geometry(r,dev,retest,'LONG'))
        self.assertIsNone(range_retest_geometry(r,dev,raid,'LONG'))

    def test_range_unknown_never_becomes_valid_boundary(self):
        from original_v1_1_objective_geometry_v2 import range_deviation_geometry
        r=obj('range',at=7200,low='8',high='12'); r['source_validated']=False
        self.assertIsNone(range_deviation_geometry(r,bars([(10,11,7,9)],start=10800)[0],'LONG'))

    def test_refined_poi_preserves_original_parent_and_bos_order(self):
        from original_v1_1_objective_geometry_v2 import refined_poi_geometry
        parent=obj('OB',at=7200,low='8',high='12',direction='LONG')
        bos=obj('BOS',at=10000,tf=15,direction='LONG')
        new=obj('POI',at=11000,tf=15,low='9',high='10',direction='LONG')
        refined=refined_poi_geometry(parent,new,bos)
        self.assertEqual(refined['payload']['parent_poi_id'],parent['id'])
        early=obj('POI',at=9000,tf=15,low='9',high='10',direction='LONG')
        self.assertIsNone(refined_poi_geometry(parent,early,bos))



class EvidenceBoundaryTests(unittest.TestCase):
    def test_metadata_half_open_interval(self):
        self.assertIsNotNone(metadata_at(metadata(1000,2000),'BTCUSDT',1000))
        self.assertIsNone(metadata_at(metadata(1000,2000),'BTCUSDT',2000))
        self.assertIsNone(metadata_at(metadata(1000,2000),'BTCUSDT',999))

    def test_current_metadata_not_backdated(self):
        m=metadata(); m['records'][0]['provenance']['historical_known_at']=200000
        self.assertIsNone(metadata_at(m,'BTCUSDT',10000))

    def test_unchanged_period_not_inferred(self):
        m=metadata(); m['records'][0]['provenance']['effective_period_proof']=False
        self.assertIsNone(metadata_at(m,'BTCUSDT',10000))

    def test_unknown_historical_period_preserved(self):
        m=metadata(); m['records'][0]['verification_status']='UNKNOWN'
        self.assertIsNone(metadata_at(m,'BTCUSDT',10000))

    def test_overlapping_verified_metadata_rejected(self):
        m=metadata(); m['records'].append(copy.deepcopy(m['records'][0]))
        with self.assertRaises(ValueError): metadata_at(m,'BTCUSDT',10000)

    def test_metadata_identity_must_be_linear(self):
        m=metadata(); m['records'][0]['values']['linear_perpetual']=False
        with self.assertRaises(ValueError): metadata_at(m,'BTCUSDT',10000)

    def test_historical_registry_honest_unknown(self):
        m=json.loads((D/'HISTORICAL_INSTRUMENT_METADATA_v1.json').read_text())
        for s in ('BTCUSDT','ETHUSDT'):
            self.assertIsNone(metadata_at(m,s,1700000000))

    def test_annotation_cited_causal_pass(self):
        o=obj(); r=annotation(o)
        f=annotation_fact([r],'market_context',{o['id']:o},10000)
        self.assertTrue(f['value'])

    def test_annotation_disagreement_unknown(self):
        o=obj(); records=[annotation(o),annotation(o,state='FAIL')]
        self.assertIsNone(annotation_fact(records,'market_context',{o['id']:o},10000))

    def test_annotation_missing_unknown(self):
        self.assertIsNone(annotation_fact([],'market_context',{},10000))

    def test_future_annotation_rejected(self):
        o=obj(); r=annotation(o); r['known_at']=10001
        with self.assertRaises(ValueError): validate_annotation(r,{o['id']:o},10000)

    def test_future_object_annotation_rejected(self):
        o=obj(at=11000); r=annotation(o)
        with self.assertRaises(ValueError): validate_annotation(r,{o['id']:o},10000)

    def test_project_policy_citation_rejected(self):
        o=obj(); r=annotation(o); r['source_rule_ids']=['P_CANONICAL_EXIT']
        with self.assertRaises(ValueError): validate_annotation(r,{o['id']:o},10000)

    def test_outcome_fields_recursive_rejected(self):
        for forbidden in ('pnl','winrate','loss','mfe','holding_time','owner_tf','old751'):
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                no_outcomes({'nested':[{'future':{forbidden:1}}]})

    def test_consumed_first_test_then_reuse_block(self):
        state=ConsumedRegistry()
        self.assertEqual(state.test('p','t1',100,eligible=True,ordered=True)['state'],'FIRST_TEST')
        self.assertEqual(state.test('p','t2',200,eligible=True,ordered=True)['state'],'CONSUMED')
        self.assertEqual(state.test('new_p','t3',300,eligible=True,ordered=True)['state'],'FIRST_TEST')

    def test_unordered_touch_unknown_not_consumed(self):
        state=ConsumedRegistry()
        self.assertEqual(state.test('p','t1',100,eligible=True,ordered=False)['state'],'UNKNOWN')
        self.assertEqual(state.test('p','t2',200,eligible=True,ordered=True)['state'],'FIRST_TEST')

    def test_consumption_cannot_run_backward(self):
        state=ConsumedRegistry(); state.test('p','t1',100,eligible=True,ordered=True)
        with self.assertRaises(ValueError): state.test('p','t2',99,eligible=True,ordered=True)

    def test_identity_branch_independent(self):
        c,f,conf,p=obj('contextual_origin'),obj('formation',direction='LONG'),obj('confirmation'),obj('POI')
        a=identity_records('BTCUSDT',c,f,conf,p); b=identity_records('BTCUSDT',c,f,conf,p)
        self.assertEqual(a,b)
        self.assertEqual(a['physical_idea_id'],digest(['BTCUSDT',c['id'],p['id']]))
        self.assertEqual(a['setup_id'],digest([a['physical_idea_id'],'LONG',f['id'],conf['id']]))

    def test_refinement_nonunique_wait(self):
        p=obj(); c1=obj('refined_POI',at=8000,low='10',high='11',direction='LONG',parent_poi_id=p['id'],formation_known_at=8000)
        c2=obj('refined_POI',at=8100,low='10',high='12',direction='LONG',parent_poi_id=p['id'],formation_known_at=8100)
        r={'known_at':7300,'completed_at':7300,'evidence':'reaction'}
        b={'known_at':7400,'completed_at':7400,'evidence':'protected BOS','tf':15}
        self.assertIsNone(source_entry_poi('SFP','LONG',10000,p,[c1,c2],reaction=r,bos=b))
        self.assertEqual(source_entry_poi('SFP','LONG',10000,p,[c1],reaction=r,bos=b)['id'],c1['id'])

    def test_stop_unknown_nonunique(self):
        p=obj(low='7',high='12')
        self.assertIsNone(source_stop('OB_CONSERVATIVE','LONG',p,10000))
        p['unique_anchor']=True
        self.assertEqual(source_stop('OB_CONSERVATIVE','LONG',p,10000)['price'],'7')

    def test_fta_all_timeframes_known_only(self):
        objects=[obj(at=7200,tf=tf,low='20',high='21',direction='SHORT',contextual=True) for tf in (15,60,240,1440)]
        objects.append(obj(at=11000,low='11',high='12',direction='SHORT',contextual=True))
        result=contextual_fta(objects,'LONG',10000,annotated_complete=True)
        self.assertEqual({p['tf'] for p in result['contextual_pois']},{15,60,240,1440})
        self.assertEqual(len(result['contextual_pois']),4)

    def test_fta_empty_does_not_imply_complete(self):
        self.assertFalse(contextual_fta([],'LONG',10000)['contextual_poi_inventory']['complete_for_known_prefix'])

    def test_adverse_requires_exact_relation(self):
        pool=obj('liquidity_pool',price='9')
        a={'pool_id':pool['id'],'tf':60,'entry_relation':'BELOW','setup_direction':'LONG',
           'structure_relation':'explicit source substructure relation','source_rule_ids':['S_ADVERSE_WAIT'],
           'role':'ADVERSE','known_at':8000,'evidence':'Blinded source annotation'}
        self.assertEqual(liquidity_role(pool,a,'LONG','10',10000)['role'],'ADVERSE')
        a['entry_relation']='ABOVE'
        with self.assertRaises(ValueError): liquidity_role(pool,a,'LONG','10',10000)

    def test_attestation_preserves_object_id_and_prefix_payload(self):
        from original_v1_1_evidence_adapter_v2 import attest_existing_object
        o=obj('swing',side='LOW',price='9'); o['source_validated']=False
        before=copy.deepcopy(o)
        a=annotation(o,concept='protected_endpoints')
        selected=attest_existing_object(o,[a],'protected_endpoints',{o['id']:o},10000)
        self.assertEqual(selected['id'],before['id'])
        self.assertEqual(selected['payload'],before['payload'])
        self.assertTrue(selected['protected_endpoint'])
        self.assertEqual(o,before)

    def test_annotation_cannot_backdate_visible_window(self):
        o=obj(); a=annotation(o); a['known_at']=o['known_at']
        with self.assertRaises(ValueError):
            validate_annotation(a,{o['id']:o},10000)

    def test_late_source_attestation_cannot_enable_early_structure(self):
        from original_v1_1_evidence_adapter_v2 import attest_existing_object
        s=[obj('swing',at=i*1000,side=side,price=str(price)) for i,(side,price) in enumerate([('LOW',7),('HIGH',10),('LOW',8),('HIGH',11)],1)]
        records=[annotation(o,concept='protected_endpoints',at=10000) for o in s]
        objects={o['id']:o for o in s}
        selected=[attest_existing_object(o,records,'protected_endpoints',objects,10000) for o in s]
        self.assertIsNone(source_structure('BTCUSDT',60,selected,5000))
        self.assertEqual(source_structure('BTCUSDT',60,selected,10000)['known_at'],10000)


    def test_consumption_same_event_replay_idempotent(self):
        state=ConsumedRegistry()
        first=state.test('p','t1',100,eligible=True,ordered=True)
        self.assertEqual(first,state.test('p','t1',100,eligible=True,ordered=True))

    def test_consumed_fta_not_reused_as_fresh_context(self):
        o=obj(low='20',high='22',direction='SHORT',contextual=True)
        p=contextual_fta([o],'LONG',10000,annotated_complete=True,consumed={o['id']})['contextual_pois'][0]
        self.assertTrue(p['consumed'])
        self.assertFalse(p['contextual'])

    def test_pool_scope_native_tf_must_match(self):
        p=obj('liquidity_pool',price='160',tf=15)
        g=obj('range',at=10000,low='100',high='200',tf=60)
        self.assertEqual(pool_scope(p,g),'UNKNOWN')

    def test_all_active_branch_annotated_schema_assembly(self):
        # Synthetic evidence contract only: no history inference, no execution.
        from original_strategy_executable_profile_v1 import (
            ACTIVE,
            encode,
            evaluate,
            stop_price,
        )
        from original_v1_1_evidence_adapter_v2 import BRANCH_CONCEPTS
        data=bars([(10,11,8,10)]*12+[(10,12,7,10),(10,11,8,10),(10,11,6,9),(9,11,8,10)])
        index=GeometryIndex('BTCUSDT',60,data)
        for branch in ACTIVE:
            with self.subTest(branch=branch):
                raw={'candidate_id':'synthetic','symbol':'BTCUSDT','branch':branch,'direction':'LONG',
                     'setup_tf':60,'decision_at':60000,'formation_at':54000,'event':'CLOSE'}
                context=obj('contextual_origin',at=40000)
                formation=obj('formation',at=54000,direction='LONG')
                confirmation=obj('confirmation',at=58000,direction='LONG')
                original=obj('POI',at=50000,low='95',high='105',direction='LONG')
                entry=obj('refined_POI',at=59000,low='99',high='101',direction='LONG',
                    parent_poi_id=original['id'],formation_known_at=59000,confirmation_id=confirmation['id'])
                stop=obj('POI',at=54000,low='6' if branch=='SFP' else '95',high='105',
                    unique_anchor=True,raid_impulse_low='95',raid_impulse_high='105')
                fta=obj('FVG',at=50000,tf=15,low='108',high='110',direction='SHORT',contextual=True)
                objects={o['id']:o for o in (context,formation,confirmation,original,entry,stop,fta)}
                records=[]
                for concept in set(BRANCH_CONCEPTS[branch]+['sl_off_liquidity','inventory_completeness']):
                    a=annotation(entry,concept=concept,at=60000)
                    records.append(a)
                record={'known_at':59000,'completed_at':59000,'evidence':'Synthetic cited eligible source observation','source_validated':True}
                selection={'objects':{'context':context['id'],'formation':formation['id'],'confirmation':confirmation['id'],
                                     'poi':original['id'],'stop':stop['id']},
                    'entry_candidates':[entry['id']],'contextual_objects':[fta['id']],'inventory_complete':True,
                    'reaction':{**record,'known_at':57800,'completed_at':57800},
                    'bos':{**record,'id':confirmation['id'],'tf':15,'known_at':58000,'completed_at':58000},
                    'liquidity_inventory':{**record,'complete_for_known_prefix':True},'liquidity':[],
                    'zone_first_test':{**record,'value':True},
                    'range_exit':{**record,'id':'synthetic-range','low':'85','high':'115','unique':True}}
                preliminary=build_case(raw,index,metadata(),annotations=records,selection=selection,source_registry=objects)
                expected=encode(stop_price(preliminary))
                for a in records:
                    if a['concept']=='sl_off_liquidity': a['checked_price']=expected
                case=build_case(raw,index,metadata(),annotations=records,selection=selection,source_registry=objects)
                result=evaluate(case)
                self.assertEqual(result['SOURCE_STRATEGY_DECISION'],'ALLOW',result)
                self.assertFalse(result['trade_entry_allowed'])
                other=build_case(raw,index,metadata(),annotations=records,selection=selection,source_registry=objects,mode='SHADOW')
                self.assertEqual(result,evaluate(other))



class SfpAndBlindingTests(unittest.TestCase):
    def setUp(self):
        # old low 7 is known by 10800; raid/reclaim at 14400, next OPEN at 18000.
        self.bars=bars([(10,11,8,10),(10,12,7,10),(10,11,8,10),(10,11,6,9),(9,11,8,10)])
        self.index=GeometryIndex('BTCUSDT',60,self.bars)
        self.raw={'candidate_id':'raw','symbol':'BTCUSDT','branch':'SFP','direction':'LONG',
                  'setup_tf':60,'decision_at':14400,'event':'CLOSE','formation_at':14400}

    def test_sfp_raid_close_precedes_next_open(self):
        case=build_case(self.raw,self.index,metadata())
        self.assertTrue(sfp_valid(case))
        self.assertIsNone(sfp_valid(case,next_open=True))

    def test_next_open_has_no_later_ohlc(self):
        n=self.index.next_open(14400,18000)
        self.assertFalse({'high','low','close','completed_at'}&n.keys())
        self.assertEqual(n['actual_open_time'],14400)
        self.assertEqual(n['known_at'],18000)

    def test_next_open_not_read_early(self):
        self.assertIsNone(self.index.next_open(14400,17999))

    def test_known_next_open_geometry(self):
        case=build_case({**self.raw,'decision_at':18000},self.index,metadata())
        self.assertTrue(sfp_valid(case,next_open=True))

    def test_next_open_wrong_side_objective_fail(self):
        bad=self.bars[:-1]+bars([(6,11,5,10)],start=14400)
        i=GeometryIndex('BTCUSDT',60,bad)
        result=inspect({**self.raw,'decision_at':18000},i,metadata(),load_tree())
        self.assertEqual(result['category'],'OBJECTIVE_FAIL')
        self.assertIn('SFP_NEXT_OPEN_NOT_RECLAIMED',result['objective_fail_reasons'])

    def test_missing_context_not_fail(self):
        r=inspect({**self.raw,'decision_at':18000},self.index,metadata(),load_tree())
        self.assertEqual(r['category'],'QUALITATIVE_REQUIRED')
        self.assertFalse(r['evidence_complete'])

    def test_modes_evidence_parity(self):
        a=inspect(self.raw,self.index,metadata(),load_tree(),mode='BACKTEST')
        b=inspect(self.raw,self.index,metadata(),load_tree(),mode='SHADOW')
        self.assertEqual(a,b)
        self.assertFalse(a['trade_entry_allowed'])

    def test_live_mode_forbidden(self):
        with self.assertRaises(ValueError): build_case(self.raw,self.index,metadata(),mode='LIVE')

    def test_atr_native_pattern_frozen(self):
        b=bars([(10,12,8,10)]*15+[(100,200,50,150)])
        i=GeometryIndex('BTCUSDT',60,b)
        case={'setup_tf':60,'decision_at':57600,'event':'CLOSE','sfp':{'raid':b[14].observed(60)},'atr_bars':i.atr_bars(54000)}
        self.assertEqual(atr14(case),Decimal(4))
        self.assertEqual(len(case['atr_bars']),15)
        self.assertEqual(case['atr_bars'][-1]['completed_at'],54000)

    def test_blinded_prefix_materialization(self):
        r=inspect(self.raw,self.index,metadata(),load_tree())
        ref=blinded_reference(self.raw,r,{60:self.index})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            write_rows(root/'candles/BTCUSDT_60.jsonl.gz',[b.observed(60) for b in self.bars])
            write_rows(root/'objects/BTCUSDT_60.jsonl.gz',self.index.prefix_objects(18000))
            result=materialize(ref,root)
            self.assertEqual(len(result['completed_candles']['60']),4)
            self.assertTrue(all(o['known_at']<=14400 for o in result['structural_objects']['60']))
            no_outcomes(result)

    def test_blinded_archive_ignores_future_suffix(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rows.gz'
            write_rows(path,[self.bars[0].observed(60),self.bars[-1].observed(60)])
            self.assertEqual(len(list(read_prefix(path,3600))),1)

    def test_funnel_exclusive_categories(self):
        rows=[inspect(self.raw,self.index,metadata(),load_tree()),inspect({**self.raw,'decision_at':18000},self.index,metadata(),load_tree())]
        s=summarize(rows)
        self.assertEqual(s['partition_sum'],2)
        self.assertEqual(s['REMAINING_UNKNOWN'],1)
        self.assertEqual(s['QUALITATIVE_REQUIRED'],1)
        self.assertFalse(s['READY_FOR_SECOND_FINANCIAL_BACKTEST'])

    def test_frozen_csv_hash_verification_without_materializing_or_parsing(self):
        import gzip
        from hashlib import sha256

        from run_original_v1_1_evidence_adapter_v2 import parent_checksum
        content=b'opaque,archived,bytes\n1,2,3\n'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'frozen.csv'
            with gzip.open(path.with_suffix('.csv.gz'),'wb') as f: f.write(content)
            self.assertEqual(parent_checksum(path),sha256(content).hexdigest())
            self.assertFalse(path.exists())


    def test_matrix_covers_all_source_predicates(self):
        with (D/'EVIDENCE_CAPABILITY_MATRIX.csv').open() as f:
            fields={r['evidence_field'] for r in csv.DictReader(f)}
        for node in load_tree()['source_nodes']:
            self.assertTrue('facts.'+node['predicate'] in fields or 'geometry.'+node['predicate'] in fields)

    def test_matrix_source_registry_consistency(self):
        registry=json.loads((ROOT/'docs/original_strategy_spec_v1_1/original_strategy_rule_registry_v1_1.json').read_text())
        source={r['rule_id'] for r in registry['rules'] if r['category']=='SOURCE_RULE'}
        with (D/'EVIDENCE_CAPABILITY_MATRIX.csv').open() as f:
            for row in csv.DictReader(f):
                self.assertTrue(set(filter(None,row['source_rule_ids'].split('|')))<=source)

    def test_new_modules_have_no_financial_or_private_imports(self):
        import ast
        modules=['original_v1_1_evidence_adapter_v2','original_v1_1_objective_geometry_v2',
                 'run_original_v1_1_evidence_adapter_v2','materialize_original_v1_1_annotation_pack']
        for m in modules:
            tree=ast.parse((ROOT/'scripts'/f'{m}.py').read_text())
            imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            self.assertFalse(any('accounting' in x or 'bybit' in x or 'simulation' in x for x in imports))


if __name__=='__main__':
    unittest.main()
