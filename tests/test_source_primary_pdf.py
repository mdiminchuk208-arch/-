from dataclasses import asdict, replace
from datetime import timedelta
import random
import unittest

from crypto_bot.strategy.market_analysis import analyze_market, MarketEvent, MarketEventKind as K, TrendState
from crypto_bot.strategy.source_pdf import SourceSeries, SourceEngine, Zone, Raid, Pool, Setup, evidence_json, poi_entry_policy, liquidity_roles
from crypto_bot.strategy.source_pdf_cases import deduplicate_cases, replay_case
from tests.test_source_engine import START, candle, signal


def zone(kind='ORDER_BLOCK', direction='LONG', low=95, high=100, name='poi'):
    return Zone(name, kind, direction, low, high, START, START, 0,
                Raid(direction, START, 96, low, 0, ('SWING:0',)), low, high+20)


class PrimaryPDFTests(unittest.TestCase):
    def test_full_manipulation_absorption_is_not_single_sweep_bar(self):
        cs = [candle(0, 110, 112, 108, 109), candle(1, 109, 110, 104, 105),
              candle(2, 105, 106, 94, 99), candle(3, 99, 108, 98, 107),
              candle(4, 107, 114, 106, 113)]
        series = SourceSeries('BTCUSDT', 5, cs, replace(analyze_market(cs), events=()))
        series.swing_history['high'] = [{'price':112, 'known_at':cs[1].close_time, 'origin_index':0, 'level_id':0}]
        series.latest_raid['LONG'] = Raid('LONG', cs[2].close_time, 95, 94, 2, ('SWING:old',))
        series.index = 3
        series._manipulations(cs[3])
        self.assertEqual(series.pending, [])  # raid candle absorbed, entire move not.
        series.index = 4
        series._manipulations(cs[4])
        z = series.pending[0]
        self.assertEqual((z.kind, z.low, z.high, z.origin_index, z.move_end_index), ('STB',94,112,0,2))
        self.assertEqual(poi_entry_policy(z, z.raid)[0], 103)

    def test_raid_ob_can_form_without_mandatory_imb_or_body_dominance(self):
        cs = [candle(0, 100, 102, 95, 99), candle(1, 99, 104, 98, 103)]
        event = MarketEvent(K.BULLISH_STRUCTURE_CONFIRMED, 1, cs[1].close_time, 103, 1, 95, 'fixture')
        s = SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=(event,)))
        s.pools['old']=Pool('SWING:old','low',96,START-timedelta(minutes=1),'SSL','EXTERNAL')
        for i in range(2): s.advance(i)
        obs=[z for z in s.zones if z.kind=='ORDER_BLOCK']
        self.assertEqual(len(obs),1)
        self.assertEqual(obs[0].confluence,{})
        self.assertLess(poi_entry_policy(obs[0],obs[0].raid)[1],95)

    def test_repeat_ob_requires_distinct_visit_and_new_context(self):
        cs=[candle(0,101,102,98,101),candle(1,101,102,98,101),
            candle(2,102,104,101,103),candle(3,103,104,98,102)]
        s=SourceSeries('BTCUSDT',60,cs,replace(analyze_market(cs),events=()))
        z=zone();s.zones=[z];s.zone_registry[z.zone_id]=z
        engine=SourceEngine('BTCUSDT',{60:s},mappings=((60,5),))
        # No active LTF event evaluation is needed to observe visit contracts.
        for i in range(4): engine.advance(60,i)
        self.assertEqual(z.test_count,2)
        self.assertEqual(len(engine.setups),2)
        self.assertEqual(engine.setups[0].reason,'OB_NEW_VISIT_REQUIRES_NEW_LTF_REACTION')
        self.assertEqual(engine.setups[1].interaction_at,cs[3].close_time)
        self.assertEqual(engine.signals,[])

    def test_remote_equal_pool_is_not_universal_blocker_below_active_leg(self):
        cs=[candle(0,100,101,99,100)]
        h=SourceSeries('BTCUSDT',60,cs,analyze_market(cs));l=SourceSeries('BTCUSDT',5,cs,analyze_market(cs))
        z=zone();z.leg_low=85
        h.pools={'in':Pool('in','low',90,START,'EQL','INTERNAL'),
                 'out':Pool('out','low',70,START,'EQL','EXTERNAL')}
        roles={r['pool_id']:r['role'] for r in liquidity_roles(h,l,z,'LONG',100,START)}
        self.assertEqual(roles,{'in':'AGAINST_SETUP','out':'UNRELATED_WITHOUT_CONTEXT'})

    def test_flow_preserves_global_destination_through_new_confirmations(self):
        cs=[candle(0,100,110,99,108)]
        s=SourceSeries('BTCUSDT',60,cs,analyze_market(cs));s.index=0;s.trend=TrendState.BULLISH
        destination=zone('SUPPLY','SHORT',115,120,'global');near=zone('SUPPLY','SHORT',112,113,'near')
        s.zones=[destination,near];s.zone_registry={z.zone_id:z for z in s.zones}
        s.flow={'direction':'LONG','known_at':START,'destination_poi':asdict(destination),
                'liquidity_work':{'extreme':95},'invalidated_at':None}
        old=s.flow
        proof={'kind':K.BULLISH_STRUCTURE_CONFIRMED.value,'direction':'LONG','protected':101,'extreme':111,
               'known_at':cs[0].close_time,'level_id':1}
        s._update_flow(cs[0],[proof])
        self.assertIs(s.flow,old)
        self.assertEqual(s.flow['destination_poi']['zone_id'],'global')
        destination.first_test=cs[0].close_time
        s._update_flow(cs[0],[])
        self.assertEqual(s.flow['invalidation_reason'],'GLOBAL_DESTINATION_TESTED_OR_INVALIDATED')

    def test_repeat_visit_dedup_uses_actual_reaction_not_original_first_test(self):
        a=signal();h=asdict(zone());h['first_test']=START
        ev={**a.evidence,'htf_poi':h,'ltf_poi':h,'htf_interaction_at':START}
        a=replace(a,evidence=ev)
        b=replace(a,signal_id='repeat',known_at=START+timedelta(days=1),evidence={**ev,'htf_interaction_at':START+timedelta(days=1)})
        accepted,dups=deduplicate_cases([a,b],['BTCUSDT'])
        self.assertEqual(len(accepted),2);self.assertEqual(dups,[])

    def test_causal_full_report_and_prefix_match_all_new_state(self):
        rng=random.Random(381);price=100.;cs=[]
        for i in range(170):
            close=price+rng.uniform(-3,3);cs.append(candle(i,price,max(price,close)+.8,min(price,close)-.8,close));price=close
        full=SourceSeries('BTCUSDT',5,cs,analyze_market(cs))
        for i in range(140):
            full.advance(i)
            if i%23:continue
            prefix=SourceSeries('BTCUSDT',5,cs[:i+1],analyze_market(cs[:i+1]))
            for j in range(i+1):prefix.advance(j)
            for name in ('zone_registry','structural_key_history','flow','flow_history','range_audit','counts'):
                a,b=getattr(full,name),getattr(prefix,name)
                if name=='zone_registry':a,b={k:asdict(v) for k,v in a.items()},{k:asdict(v) for k,v in b.items()}
                self.assertEqual(evidence_json(a),evidence_json(b))

    def test_independent_filled_closed_cost_case(self):
        s=signal(targets=(105.,));cs=[candle(0,101,102,99,101),candle(1,101,106,100,105)]
        a=replay_case(s,cs,[])
        self.assertEqual(a.trades[0]['status'],'CLOSED')
        self.assertGreater(a.trades[0]['fees'],0)
        self.assertAlmostEqual(a.trades[0]['net_pnl'],a.trades[0]['gross_pnl']-a.trades[0]['fees'])
        self.assertFalse(a.trades[0]['trade_entry_allowed'])

    def test_flow_can_start_on_key_continuation_with_reclaimed_liquidity(self):
        cs=[candle(0,100,104,99,103),candle(1,103,104,94,101),candle(2,101,112,100,111)]
        s=SourceSeries('BTCUSDT',60,cs,analyze_market(cs));s.index=2;s.trend=TrendState.BULLISH
        old={'kind':K.BULLISH_STRUCTURE_CONFIRMED.value,'direction':'LONG','protected':95,'extreme':104,'known_at':START,'level_id':1}
        proof={**old,'protected':100,'extreme':110,'known_at':cs[2].close_time,'level_id':2}
        s.structure=proof;s.structural_key_history['LONG']=[old]
        s.raids=[Raid('LONG',cs[1].close_time,95,94,1,('SWING:old',))]
        target=zone('SUPPLY','SHORT',115,120,'global');s.zones=[target];s.zone_registry[target.zone_id]=target
        s._update_flow(cs[2],[proof])
        self.assertIsNotNone(s.flow)
        self.assertEqual(s.flow['destination_poi']['zone_id'],'global')
        self.assertEqual(s.flow['sequence']['structural_keys'],[old,proof])
        self.assertLess(s.flow['liquidity_work']['known_at'],s.flow['body_break_at'])

    def test_ready_fta_is_htf_not_nearer_ltf_gap(self):
        t=lambda n:START+timedelta(minutes=n)
        cs=[candle(0,104,106,103,105)]
        series={tf:SourceSeries('BTCUSDT',tf,cs,analyze_market(cs)) for tf in (5,60)}
        l,h=series[5],series[60];l.index=h.index=0
        proof={'direction':'LONG','known_at':t(20),'protected':95,'extreme':108}
        l.raids=[Raid('LONG',t(10),96,95,0,('SWING:0',))]
        l.bos['LONG']={'known_at':t(15),'direction':'LONG'}
        l.conf['LONG']={'known_at':t(25),'new_structure':proof}
        l.structure=h.structure=proof;l.trend=h.trend=TrendState.BULLISH
        h.flow={'direction':'LONG','known_at':t(20),'invalidated_at':None,'structure':proof}
        local=zone(low=98,high=100,name='local');local.formed_at=t(20);local.known_at=t(25);local.structural_proof=proof
        near=zone('FVG','SHORT',107,108,'near');target=zone('SUPPLY','SHORT',110,112,'htf-target')
        l.zones=[local,near];h.zones=[target]
        context=zone('STB',low=95,high=101);context.leg_low=90;context.leg_high=120;context.first_test=t(10)
        engine=SourceEngine('BTCUSDT',series);setup=Setup('test',60,5,context,t(10))
        engine._evaluate(setup,t(30))
        self.assertEqual(engine.signals[0].targets,(110,))
        self.assertEqual(engine.signals[0].evidence['fta']['zone_id'],'htf-target')


if __name__=='__main__':unittest.main()
