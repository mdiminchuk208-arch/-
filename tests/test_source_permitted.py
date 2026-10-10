"""Constructed rule/execution fixtures, never historical performance evidence."""
import json
import random
import unittest
from dataclasses import asdict, replace
from datetime import timedelta
from pathlib import Path

from crypto_bot.strategy.market_analysis import MarketEvent, TrendState, analyze_market
from crypto_bot.strategy.market_analysis import MarketEventKind as K
from crypto_bot.strategy.source_pdf_native import Pool, Raid, Zone, evidence_json
from crypto_bot.strategy.source_permitted import (
    Context,
    PhysicalRegistry,
    SourceContextZone,
    SourceEngine,
    SourceSeries,
    select_union,
)
from crypto_bot.strategy.source_permitted_cases import replay_case
from tests.test_source_engine import START, candle, signal


def policy():
    return json.loads((Path(__file__).parents[1]/'config/source_permitted_policy.json').read_text())


def zone(kind='ORDER_BLOCK',direction='LONG',low=95.,high=100.,name='local'):
    return Zone(name,kind,direction,low,high,START,START,0,
                Raid(direction,START,96 if direction=='LONG' else 124,low if direction=='LONG' else high,0,('SWING:old',)),
                90,130,structural_proof={'direction':direction,'known_at':START,'protected':90,'extreme':130},
                confluence={'engulfing_candle':{'low':96.,'high':124.,'known_at':START}})


def fixture():
    cs=[candle(0,104,106,103,105)]
    series={tf:SourceSeries('BTCUSDT',tf,cs,replace(analyze_market(cs),events=())) for tf in (5,60)}
    l,h=series[5],series[60]
    proof={'kind':K.BULLISH_STRUCTURE_CONFIRMED.value,'direction':'LONG','known_at':START,'protected':90.,'extreme':130.}
    for s in series.values():s.index=0;s.structure=dict(proof);s.trend=TrendState.BULLISH
    parent=zone('ORDER_BLOCK',low=90,high=110,name='parent')
    dest=zone('SUPPLY','SHORT',120,125,'destination')
    h.zones=[parent,dest];h.zone_registry={z.zone_id:z for z in h.zones}
    h.flow={'flow_id':'flow','direction':'LONG','known_at':START,'structure':dict(proof),
            'liquidity_work':asdict(parent.raid),'destination_poi':asdict(dest),'invalidated_at':None}
    l.bos['LONG']={'kind':K.BEARISH_STRUCTURE_BROKEN_BOS.value,'known_at':START,'direction':'LONG','protected':90,'extreme':130}
    local=zone();l.zones=[local];l.zone_registry[local.zone_id]=local
    e=SourceEngine('BTCUSDT',series,policy())
    return e,parent,local,cs[0].close_time


class PermittedPathTests(unittest.TestCase):
    def emit(self,path,kind='ORDER_BLOCK'):
        e,parent,local,now=fixture();local.kind=kind
        e._emit(path,60,5,parent,local,now,'physical',1,START,local.raid)
        self.assertEqual(len(e.signals),1)
        return e.signals[0]

    def test_ob_direct_edge_no_extra_ltf_bos_or_conf(self):
        e,_,local,now=fixture();e.series[5].bos={};e.series[5].conf={}
        e._direct(60,5,local,now)
        self.assertEqual({s.evidence['path_id'] for s in e.signals},{'OB_DIRECT_FIRST_TEST','OB_DIRECT_INSIDE','OB_DIRECT_ENGULFING_STOP','OB_DIRECT_INSIDE_ENGULFING_STOP'})
        self.assertEqual(e.signals[0].entry,100)

    def test_ob_inside_is_distinct_fixed_quote(self):
        self.assertEqual(self.emit('OB_DIRECT_INSIDE').entry,97.5)

    def test_ob_engulfing_stop_is_separate_from_ob_stop(self):
        s=self.emit('OB_DIRECT_ENGULFING_STOP')
        self.assertLess(s.stop,96);self.assertGreater(s.stop,95)

    def test_ob_inside_engulfing_combination(self):
        s=self.emit('OB_DIRECT_INSIDE_ENGULFING_STOP')
        self.assertEqual(s.entry,97.5);self.assertGreater(s.stop,95)

    def test_ob_bos_poi_does_not_require_conf(self):
        e,parent,_local,now=fixture()
        ctx=Context(60,5,parent,START,1,'physical')
        e._conservative(ctx,now)
        self.assertEqual([s.evidence['path_id'] for s in e.signals],['OB_CONSERVATIVE_BOS_POI'])
        self.assertNotIn('conf',e.signals[0].evidence['confirmations'])

    def test_conf_path_requires_distinct_later_structure(self):
        e,parent,_local,now=fixture();l=e.series[5]
        l.conf['LONG']={'known_at':now,'new_structure':{'known_at':START,'protected':90,'extreme':130}}
        ctx=Context(60,5,parent,START,1,'physical');e._conservative(ctx,now)
        self.assertNotIn('OB_ULTRA_CONSERVATIVE_CONF',[s.evidence['path_id'] for s in e.signals])
        e,parent,_local,now=fixture();l=e.series[5]
        l.conf['LONG']={'known_at':now,'new_structure':{'known_at':START+timedelta(minutes=1),'protected':90,'extreme':130}}
        e._conservative(Context(60,5,parent,START,1,'physical'),now)
        self.assertIn('OB_ULTRA_CONSERVATIVE_CONF',[s.evidence['path_id'] for s in e.signals])

    def test_stb_edge(self):
        self.assertEqual(self.emit('STB_BTS_EDGE','STB').entry,100)

    def test_stb_half(self):
        self.assertEqual(self.emit('STB_BTS_HALF','STB').entry,97.5)

    def test_breaker_conservative_outside_sweep(self):
        e,p,q,n=fixture();q.kind='BREAKER';q.stop_extreme=92
        e._emit('BREAKER_CONSERVATIVE_STOP',60,5,p,q,n,'physical',1,START,q.raid)
        self.assertLess(e.signals[0].stop,92)

    def test_breaker_aggressive_outside_block(self):
        self.assertLess(self.emit('BREAKER_AGGRESSIVE_STOP','BREAKER').stop,95)

    def test_ds_independent_multi_candle_move_without_fvg(self):
        cs=[candle(0,104,105,100,101),candle(1,101,102,95,98),candle(2,98,107,97,106)]
        s=SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=()))
        s.index=2;s.last_opposite['LONG']=1
        s.raids=[Raid('LONG',cs[1].close_time,96,95,1,('SWING:old',))]
        s._demand_supply(cs[2])
        self.assertEqual((s.pending[0].low,s.pending[0].high,s.pending[0].origin_index,s.pending[0].move_end_index),(95,105,0,1))
        self.assertEqual(self.emit('DEMAND_SUPPLY','DEMAND').entry,97.5)

    def test_range_conservative_boundary_limit_without_universal_conf(self):
        e,_,_q,now=fixture();r=zone('RANGE_POI',low=95,high=115,name='range');r.range_id='range';r.range_retest_at=now
        e._range_signal(r,60,5,r,now,'RANGE_CONSERVATIVE_RETEST')
        self.assertEqual(len(e.signals),1);s=e.signals[0]
        self.assertEqual(s.entry,95);self.assertEqual(s.fractions,(.8,.2));self.assertLess(s.targets[0],115)

    def test_range_aggressive_fixed_external_quote_implies_deviation_at_fill(self):
        s=self.emit('OB_DIRECT_FIRST_TEST');s=replace(s,setup_type='RANGE_AGGRESSIVE_EXTERNAL_POI',
            evidence={**s.evidence,'path_id':'RANGE_AGGRESSIVE_EXTERNAL_POI','htf_poi':{'low':101,'high':115}})
        a=replay_case(s,[candle(1,104,105,99,101)],[])
        self.assertEqual(len(a.trades),1)
        self.assertIn('actual_range_deviation_at_fill',a.trades[0]['evidence'])
        self.assertNotIn('actual_range_deviation_at_fill',s.evidence)

    def test_sfp_bos_path_no_conf(self):
        e,_p,_q,now=fixture();sfp=SourceContextZone('sfp','SFP','LONG',94,106,START,START,0,
            Raid('LONG',START,96,94,0,('SWING:old',),True),90,130)
        e.series[60].atr_values=[2.]
        e._conservative(Context(60,5,sfp,START,1,'physical'),now)
        self.assertEqual({s.evidence['path_id'] for s in e.signals},{'SFP_BOS_POI','SFP_ATR_STOP'})

    def test_sfp_atr_stop_frozen_at_pattern(self):
        e,p,q,now=fixture();e.series[60].atr_values=[2.]
        raid=Raid('LONG',START,96,94,0,('SWING:old',),True)
        e._emit('SFP_ATR_STOP',60,5,p,q,now,'physical',1,START,raid)
        self.assertEqual(e.signals[0].stop,92.)


class CausalityAndUnionTests(unittest.TestCase):
    def test_native_5m_target_test_prevents_same_close_ready(self):
        e,_p,q,now=fixture()
        c=candle(0,104,125,103,105)
        e.series[5].candles=[c]
        e.series[5].index=-1
        e.advance(5,0)
        self.assertEqual(e.series[60].zone_registry['destination'].first_test,now)
        self.assertIsNone(e._active_flow(e.series[60],'LONG'))
        e._direct(60,5,q,now)
        self.assertEqual(e.signals,[])

    def test_atr_wilder_seed_and_current_closed_bar_only(self):
        cs=[candle(i,100,102+i,98,100) for i in range(16)]
        s=SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=()))
        for i in range(15):s.advance(i)
        self.assertEqual(s.atr_values[:13],[None]*13)
        self.assertAlmostEqual(s.atr_values[13],sum(4+i for i in range(14))/14)
        self.assertAlmostEqual(s.atr_values[14],(s.atr_values[13]*13+18)/14)
        self.assertEqual(len(s.atr_values),15)

    def test_fta_touch_other_than_global_destination_is_not_universal_cancel(self):
        e,p,q,now=fixture()
        e._emit('OB_DIRECT_FIRST_TEST',60,5,p,q,now,'physical',1,START,q.raid)
        e.signals[0].evidence['fta'].update(zone_id='different_non_global_FTA',low=108,high=109)
        e._lifecycle(5,candle(1,105,110,103,105))
        self.assertEqual([r['cohort'] for r in e.cancellations],['CANCEL_STRICT_STRUCTURE'])

    def test_sfp_local_flow_is_confluence_and_thesis_keeps_local_tf(self):
        e,_,_,now=fixture()
        e.series[5].flow=dict(e.series[60].flow)
        sfp=SourceContextZone('sfp','SFP','LONG',94,106,START,START,0,
            Raid('LONG',START,96,94,0,('SWING:old',),True),90,130)
        e._conservative(Context(60,5,sfp,START,1,'physical'),now)
        self.assertEqual(e.signals[0].evidence['thesis_tf'],5)
        self.assertNotIn('destination_poi',e.signals[0].evidence['order_flow'])
        self.assertIsNotNone(e.signals[0].evidence['order_flow']['local_flow_confluence'])

    def test_ob_formation_uses_real_bos_without_future_conf(self):
        cs=[candle(0,100,105,95,99),candle(1,99,104,98,102)]
        event=MarketEvent(K.BEARISH_STRUCTURE_BROKEN_BOS,1,cs[1].close_time,103,1,101,'constructed source BOS fixture')
        s=SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=(event,)))
        s.pools['old']=Pool('SWING:old','low',96,START-timedelta(minutes=1),'SSL','EXTERNAL')
        s.advance(0);s.advance(1)
        obs=[q for q in s.zones if q.kind=='ORDER_BLOCK']
        self.assertEqual(len(obs),1)
        self.assertEqual(obs[0].structural_proof['kind'],K.BEARISH_STRUCTURE_BROKEN_BOS.value)
        self.assertEqual(s.conf,{})

    def test_ob_body_absorption_is_not_universal_full_wick_close(self):
        cs=[candle(0,100,105,95,99),candle(1,99,104,98,102)]
        s=SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=()))
        s.index=1;s.raids=[Raid('LONG',cs[0].close_time,96,95,0,('SWING:old',))]
        s._order_blocks(cs[1]);self.assertEqual(len(s.pending),1)
        self.assertFalse(s.pending[0].confluence['full_wick_close_strict_subset'])
        s._qualify(s.pending[0],{'direction':'LONG','known_at':cs[1].close_time})
        self.assertEqual(s.zones,[]) # No actual formation BOS yet.

    def test_of_liquidity_work_does_not_need_second_later_key_body_break(self):
        e,_p,_q,now=fixture();h=e.series[60];h.flow=None
        h.structural_key_history['LONG']=[{'protected':80,'extreme':120,'known_at':START},
            {'protected':90,'extreme':130,'known_at':now}]
        h.raids=[Raid('LONG',now,99,98,0,('SWING:old',))]
        h._update_flow(h.candles[0],[])
        self.assertIsNotNone(h.flow)
        self.assertFalse(h.flow['extra_post_raid_body_break_required'])

    def test_unrelated_ltf_break_only_cancels_strict_cohort(self):
        e,p,q,now=fixture();e._emit('OB_DIRECT_FIRST_TEST',60,5,p,q,now,'physical',1,START,q.raid)
        e.series[5].trend=TrendState.BROKEN
        e._lifecycle(5,candle(1,105,106,102,104))
        self.assertEqual([r['cohort'] for r in e.cancellations],['CANCEL_STRICT_STRUCTURE'])

    def test_source_poi_invalidation_cancels_both_at_known_close(self):
        e,p,q,now=fixture();e._emit('OB_DIRECT_FIRST_TEST',60,5,p,q,now,'physical',1,START,q.raid)
        q.invalidated_at=START+timedelta(minutes=10)
        e._lifecycle(5,candle(1,103,104,94,94.5))
        self.assertEqual({r['cohort'] for r in e.cancellations},set(policy()['cancellation_cohorts']))
        self.assertTrue(all(r['known_at']>now for r in e.cancellations))

    def test_physical_identity_across_aliases_and_native_tf_variants(self):
        r=PhysicalRegistry();a=zone();b=replace(a,zone_id='alias',kind='DEMAND')
        self.assertEqual(r.assign('BTCUSDT',15,a,1,START),r.assign('BTCUSDT',60,b,1,START))
        self.assertNotEqual(r.assign('BTCUSDT',15,a,1,START),r.assign('BTCUSDT',15,a,2,START+timedelta(days=1)))

    def test_union_has_one_physical_case_and_no_later_outcome_substitution(self):
        e,p,q,now=fixture()
        for path in ('OB_DIRECT_INSIDE','OB_DIRECT_FIRST_TEST'):
            e._emit(path,60,5,p,q,now,'physical',1,START,q.raid)
        selected,dups=select_union(e.signals,policy())
        self.assertEqual(selected[0].evidence['path_id'],'OB_DIRECT_FIRST_TEST')
        self.assertEqual(len(dups),1)
        early=replace(e.signals[0],known_at=START)
        selected,_=select_union([early,e.signals[1]],policy())
        self.assertEqual(selected[0].signal_id,early.signal_id)

    def test_gap_through_stop_is_real_paper_loss_not_retroactive_cancel(self):
        s=signal();s=replace(s,evidence={**s.evidence,'path_id':'OB_DIRECT_FIRST_TEST','physical_opportunity_id':'physical'})
        cs=[candle(0,90,92,88,91)]
        a=replay_case(s,cs,[]);strict=replay_case(s,cs,[],cancellation_cohort='CANCEL_STRICT_STRUCTURE')
        self.assertEqual(len(a.trades),1);self.assertEqual(a.trades[0]['result'],'LOSS')
        self.assertLess(a.trades[0]['net_pnl'],-23.4);self.assertEqual(strict.trades,[])

    def test_same_bar_close_cancellation_cannot_prevent_prior_touch(self):
        s=signal();s=replace(s,evidence={**s.evidence,'path_id':'OB_DIRECT_FIRST_TEST','physical_opportunity_id':'physical'})
        c=candle(0,103,104,99,102)
        r={'known_at':c.close_time,'reason':'POI_BODY_INVALID','cohort':'CANCEL_SOURCE_POI_INVALIDATION'}
        self.assertEqual(len(replay_case(s,[c],[r]).trades),1)
        r['known_at']=c.open_time
        self.assertEqual(replay_case(s,[c],[r]).trades,[])

    def test_atr_pattern_close_exits_executed_case_not_cancels_trade(self):
        s=signal();s=replace(s,stop=85,evidence={**s.evidence,'path_id':'SFP_ATR_STOP','physical_opportunity_id':'physical'})
        cs=[candle(0,103,104,99,101),candle(1,101,102,90,91)]
        exits=[{'known_at':cs[1].close_time,'reason':'SFP_PATTERN_BODY_CLOSE_INVALIDATION','price':91}]
        a=replay_case(s,cs,[],exits)
        self.assertEqual(a.trades[0]['exit_reason'],'SFP_PATTERN_BODY_CLOSE_INVALIDATION')
        self.assertEqual(a.trades[0]['result'],'LOSS')

    def test_registry_all_paths_have_sources_and_distinct_ids(self):
        rows=policy()['paths'];self.assertEqual(len(rows),15)
        self.assertEqual(len({p['path_id'] for p in rows}),15)
        self.assertTrue(all(p['source_citations'] and p['trade_entry_allowed'] is False for p in rows))

    def test_full_analysis_future_mutation_keeps_all_prefix_source_state(self):
        rng=random.Random(21010);cs=[];p=100.
        for i in range(110):
            q=p+rng.uniform(-3,3);cs.append(candle(i,p,max(p,q)+.4,min(p,q)-.4,q));p=q
        def build(bars,n):
            series={tf:SourceSeries('BTCUSDT',tf,bars,analyze_market(bars)) for tf in (5,60)}
            e=SourceEngine('BTCUSDT',series,policy())
            for i in range(n):
                e.advance(60,i);e.advance(5,i);e.evaluate(bars[i].close_time,{5,60})
            return e
        a,b=build(cs,80),build(cs[:80],80)
        mutated=cs[:80]+[replace(c,open=c.open*2,high=c.high*3,low=c.low*.5,close=c.close*2) for c in cs[80:]]
        d=build(mutated,80)
        for other in (b,d):
            self.assertEqual(evidence_json(a.finish()),evidence_json(other.finish()))
            self.assertEqual(evidence_json([asdict(s) for s in a.signals]),evidence_json([asdict(s) for s in other.signals]))
            self.assertEqual(evidence_json(a.cancellations),evidence_json(other.cancellations))
            self.assertEqual(evidence_json(a.attempts),evidence_json(other.attempts))


if __name__=='__main__':unittest.main()
