from dataclasses import replace
from datetime import timedelta
import random
import unittest

from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.source_pdf_native import SourceEngine, SourceSeries, Zone, Raid, evidence_json
from tests.test_source_engine import START, candle


class NativeTimingTests(unittest.TestCase):
    def test_known_htf_zone_starts_context_on_native_touch_before_htf_close(self):
        cs=[candle(0,101,102,98,101),candle(1,101,102,98,101)]
        h=SourceSeries('BTCUSDT',60,cs,replace(analyze_market(cs),events=()))
        l=SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=()))
        z=Zone('known','DEMAND','LONG',95,100,START,START,0,Raid('LONG',START,96,95,0,('SWING:old',)),90,110,
               native_touch_clock=True)
        h.zones=[z];h.zone_registry[z.zone_id]=z
        e=SourceEngine('BTCUSDT',{60:h,5:l},mappings=((60,5),))
        e.advance(5,0)
        self.assertEqual(len(e.setups),1)
        self.assertEqual(e.setups[0].interaction_at,cs[0].close_time)
        self.assertEqual(h.index,-1)  # no forming/closed HTF candle consumed.
        e.advance(5,1)
        self.assertEqual(z.test_count,1)

    def test_poi_unknown_at_native_open_cannot_take_retroactive_touch(self):
        cs=[candle(0,101,102,98,101)]
        h=SourceSeries('BTCUSDT',60,cs,analyze_market(cs));l=SourceSeries('BTCUSDT',5,cs,replace(analyze_market(cs),events=()))
        z=Zone('new','DEMAND','LONG',95,100,cs[0].close_time,cs[0].close_time,0,
               Raid('LONG',START,96,95,0,('SWING:old',)),90,110,native_touch_clock=True)
        h.zones=[z];h.zone_registry[z.zone_id]=z
        e=SourceEngine('BTCUSDT',{60:h,5:l},mappings=((60,5),));e.advance(5,0)
        self.assertEqual(e.setups,[]);self.assertIsNone(z.first_test)

    def test_htf_close_does_not_recount_native_visit(self):
        cs=[candle(0,101,102,98,101),candle(1,101,102,98,101)]
        s=SourceSeries('BTCUSDT',60,cs,replace(analyze_market(cs),events=()))
        z=Zone('known','ORDER_BLOCK','LONG',95,100,START,START,0,Raid('LONG',START,96,95,0,('SWING:old',)),90,110,
               native_touch_clock=True,first_test=START+timedelta(minutes=5),last_test=START+timedelta(minutes=5),
               last_native_test_at=START+timedelta(minutes=5),test_count=1)
        s.zones=[z];s.zone_registry[z.zone_id]=z;s.advance(0)
        self.assertEqual(z.test_count,1)

    def test_future_native_bars_do_not_change_prefix_state(self):
        rng=random.Random(215);cs=[];p=100.
        for i in range(90):
            q=p+rng.uniform(-2,2);cs.append(candle(i,p,max(p,q)+.7,min(p,q)-.7,q));p=q
        def build(bars,n):
            series={tf:SourceSeries('BTCUSDT',tf,bars,analyze_market(bars)) for tf in (5,15)}
            engine=SourceEngine('BTCUSDT',series,mappings=((15,5),))
            for i in range(n):
                engine.advance(15,i);engine.advance(5,i)
            return engine
        full=build(cs,70);prefix=build(cs[:70],70)
        self.assertEqual(evidence_json(full.finish()),evidence_json(prefix.finish()))
        self.assertEqual(evidence_json(full.decisions),evidence_json(prefix.decisions))

    def test_fta_already_behind_ready_close_blocks_signal(self):
        # Reuse the source fixture with a target passed by current close (105).
        import crypto_bot.strategy.source_pdf_native as module
        from tests.test_source_primary_pdf import zone
        from crypto_bot.strategy.market_analysis import TrendState
        t=lambda n:START+timedelta(minutes=n);cs=[candle(0,104,106,103,105)]
        series={tf:SourceSeries('BTCUSDT',tf,cs,analyze_market(cs)) for tf in (5,60)}
        l,h=series[5],series[60];l.index=h.index=0
        proof={'direction':'LONG','known_at':t(20),'protected':95,'extreme':108}
        l.raids=[Raid('LONG',t(10),96,95,0,('SWING:0',))];l.bos['LONG']={'known_at':t(15),'direction':'LONG'}
        l.conf['LONG']={'known_at':t(25),'new_structure':proof};l.structure=h.structure=proof;l.trend=h.trend=TrendState.BULLISH
        h.flow={'direction':'LONG','known_at':t(20),'invalidated_at':None,'structure':proof}
        local=zone(low=98,high=100,name='local');local.formed_at=t(20);local.known_at=t(25);local.structural_proof=proof
        l.zones=[local];h.zones=[zone('SUPPLY','SHORT',104,104.5,'passed')]
        context=zone('STB',low=95,high=101);context.leg_low=90;context.leg_high=120;context.first_test=t(10)
        engine=SourceEngine('BTCUSDT',series);setup=module.Setup('test',60,5,context,t(10))
        engine._evaluate(setup,t(30))
        self.assertEqual(engine.signals,[]);self.assertEqual(setup.reason,'WAIT_FTA_ALREADY_PASSED_AT_READY')


if __name__=='__main__':unittest.main()
