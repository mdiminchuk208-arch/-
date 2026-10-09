from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import random
import unittest

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import analyze_market, MarketEvent, MarketEventKind, TrendState
from crypto_bot.strategy.source_engine import (Pool, Raid, Setup, SourceEngine, SourceSeries, SourceSignal, Zone,
                                               evidence_json, opposing_liquidity, pd_location)
from crypto_bot.strategy.source_portfolio import SourcePortfolio, SourceRiskPolicy

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def candle(i, o, h, l, c):
    t = START + timedelta(minutes=5 * i)
    return Candle(t, t + timedelta(minutes=5), o, h, l, c)


def signal(direction='LONG', *, fractions=(1.0,), targets=(110.0,)):
    short = direction == 'SHORT'
    return SourceSignal('signal', 'setup', 'BTCUSDT', START, direction, 60, 5,
                        'CONSTRUCTED_UNIT_FIXTURE', 'ORDER_BLOCK', 100, 105 if short else 95,
                        tuple(200 - t for t in targets) if short else targets, fractions,
                        {'exit_policy': 'SOURCE_TEST'})


class SourceGeometryTests(unittest.TestCase):
    def test_pd_ote_is_confluence_not_a_required_gate(self):
        self.assertEqual(pd_location('LONG', 23, 20, 30)[:2], (True, False))
        self.assertEqual(pd_location('LONG', 22.5, 20, 30)[:2], (True, True))
        self.assertEqual(pd_location('SHORT', 27.5, 20, 30)[:2], (True, True))
        self.assertFalse(pd_location('LONG', 25, 20, 30)[0])

    def test_meaningful_adverse_liquidity_has_price_and_side_context(self):
        pools = [Pool('against', 'low', 98, START, 'SSL', 'INTERNAL'),
                 Pool('remote', 'low', 90, START, 'SSL', 'EXTERNAL'),
                 Pool('goal', 'high', 110, START, 'BSL', 'EXTERNAL')]
        self.assertEqual([p['pool_id'] for p in opposing_liquidity(pools, 'LONG', 100, 95)], ['against'])
        self.assertEqual([p['pool_id'] for p in opposing_liquidity(pools, 'SHORT', 100, 115)], ['goal'])

    def test_demand_supply_freshness_never_inherits_repeat_ob_exception(self):
        t1, t2, t3 = (START + timedelta(minutes=i) for i in (5, 10, 15))
        for kind in ('DEMAND', 'SUPPLY', 'ORDER_BLOCK'):
            z = Zone(kind, kind, 'LONG', 95, 100, START, START, 0, None, 90, 110,
                     first_test=t1, last_test=t2, test_count=2)
            self.assertFalse(z.test_allowed(t3))
            self.assertEqual(z.test_allowed(t3, reaction_confirmed_at=t3), kind == 'ORDER_BLOCK')
            self.assertFalse(z.test_allowed(t3, reaction_confirmed_at=t1))
            z.invalidated_at = t2
            self.assertFalse(z.test_allowed(t3, reaction_confirmed_at=t3))

    def test_fta_selects_nearest_qualified_zone_not_three_gaps(self):
        cs = [candle(0, 100, 101, 99, 100)]
        s = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        far = Zone('far', 'SUPPLY', 'SHORT', 120, 125, START, START, 0, None, 90, 125)
        near = Zone('near', 'BREAKER', 'SHORT', 110, 115, START, START, 0, None, 90, 115)
        s.zones = [far, near]
        self.assertEqual(s.target('LONG', 100, START).zone_id, 'near')
        near.first_test = START
        self.assertEqual(s.target('LONG', 100, START).zone_id, 'far')

    def test_no_live_signal_or_mode(self):
        with self.assertRaises(ValueError):
            SourceSignal('x', 'y', 'BTCUSDT', START, 'LONG', 60, 5, 'x', 'x', 100, 90,
                         (110,), (1.0,), {}, trade_entry_allowed=True)
        with self.assertRaises(ValueError):
            SourcePortfolio(mode='LIVE')


class SourceCausalityTests(unittest.TestCase):
    def test_ob_and_stb_aliases_do_not_create_duplicate_mapped_setups(self):
        cs = [candle(0, 100, 102, 99, 101)]
        series = {tf: SourceSeries('BTCUSDT', tf, cs, analyze_market(cs)) for tf in (5, 15, 60, 240)}
        h = series[60]
        raid = Raid('LONG', START, 99, 98, 0, ('SSL',))
        for kind in ('ORDER_BLOCK', 'STB'):
            z = Zone(kind, kind, 'LONG', 98, 100, START, START, 0, raid, 98, 110)
            h.zones.append(z)
            h.zone_registry[z.zone_id] = z
        engine = SourceEngine('BTCUSDT', series)
        engine.advance(60, 0)
        self.assertEqual(len(engine.setups), 2)  # 60/5 and60/15; one physical zone.
        self.assertEqual(engine.funnel['source_contexts'], 1)
        self.assertTrue(all(s.poi.kind == 'ORDER_BLOCK' and 'STB' in s.poi.aliases for s in engine.setups))

    def test_tested_demand_context_still_observes_retest_and_body_invalidation(self):
        cs = [candle(0, 100, 101, 98, 100), candle(1, 105, 106, 104, 105),
              candle(2, 104, 105, 99, 100), candle(3, 99, 100, 94, 95)]
        series = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        raid = Raid('LONG', START, 96, 94, 0, ('SSL',))
        z = Zone('demand', 'DEMAND', 'LONG', 96, 101, START, START, 0, raid, 94, 110)
        series.zones = [z]
        series.zone_registry[z.zone_id] = z
        series.advance(0)
        self.assertEqual(z.test_count, 1)
        self.assertNotIn(z, series.zones)
        series.context_watches[z.zone_id] = z
        series.advance(1)
        series.advance(2)
        self.assertEqual(z.test_count, 2)
        series.advance(3)
        self.assertEqual(z.invalidated_at, cs[3].close_time)

    def test_ob_requires_origin_candle_raid_not_only_later_impulse_raid(self):
        for origin_raids, expected in ((True, 'ORDER_BLOCK'), (False, 'DEMAND')):
            cs = [candle(0, 105, 106, 102, 104),
                  candle(1, 104, 104.5, 99 if origin_raids else 101, 100 if origin_raids else 102),
                  candle(2, 100 if origin_raids else 102, 109, 99.5 if origin_raids else 100, 108),
                  candle(3, 108, 111, 107, 110)]
            # Constructed event tests the zone classifier, not market conformance.
            event = MarketEvent(MarketEventKind.BULLISH_STRUCTURE_CONFIRMED, 3, cs[3].close_time,
                                110, 1, 99, 'CONSTRUCTED_UNIT_STRUCTURE')
            report = replace(analyze_market(cs), events=(event,))
            series = SourceSeries('BTCUSDT', 5, cs, report)
            series.pools['prior'] = Pool('prior', 'low', 100.5, START, 'SSL', 'EXTERNAL')
            for i in range(4):
                series.advance(i)
            candidates = [z for z in series.zones if z.kind in ('ORDER_BLOCK', 'DEMAND')]
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].kind, expected)
            self.assertEqual(candidates[0].raid.candle_index, 1 if origin_raids else 2)

    def test_complete_causal_chain_is_ready_with_one_fta_without_ote(self):
        now = START + timedelta(minutes=30)
        cs = [candle(5, 104, 106, 103, 105)]
        series = {tf: SourceSeries('BTCUSDT', tf, cs, analyze_market(cs)) for tf in (5, 15, 60, 240)}
        l, h = series[5], series[60]
        l.index = h.index = 0
        t = lambda minutes: START + timedelta(minutes=minutes)
        raid = Raid('LONG', t(10), 96, 95, 0, ('oldSSL',))
        structural = {'direction': 'LONG', 'known_at': t(20), 'protected': 95, 'extreme': 108, 'kind': 'NEW_STRUCTURE'}
        l.raids = [raid]
        l.bos['LONG'] = {'known_at': t(15), 'direction': 'LONG'}
        l.conf['LONG'] = {'known_at': t(25), 'new_structure': structural}
        l.structure = structural
        h.structure = dict(structural)
        l.trend = h.trend = TrendState.BULLISH
        zone = Zone('htf', 'DEMAND', 'LONG', 94, 101, START, START, 0, raid, 90, 120,
                    structural_proof=structural, first_test=t(10), last_test=t(10))
        local = Zone('local', 'ORDER_BLOCK', 'LONG', 98, 100, t(20), t(25), 0, raid, 95, 108,
                     structural_proof=structural)
        target = Zone('target', 'SUPPLY', 'SHORT', 110, 112, START, START, 0, None, 90, 120)
        l.zones = [local]
        h.zones = [target]
        engine = SourceEngine('BTCUSDT', series)
        setup = Setup('setup', 60, 5, zone, t(10))
        l.pools['against'] = Pool('against', 'low', 97, t(5), 'SSL', 'INTERNAL')
        engine._evaluate(setup, now)
        self.assertEqual(engine.signals, [])
        self.assertEqual(setup.reason, 'WAIT_MEANINGFUL_LIQUIDITY_AGAINST_SETUP')
        l.pools.clear()  # Explicitly represents the subsequent raid, not a caller flag.
        engine._evaluate(setup, now)
        self.assertEqual(len(engine.signals), 1)
        signal = engine.signals[0]
        self.assertEqual(signal.targets, (110,))
        self.assertFalse(signal.evidence['premium_discount']['ote_confluence'])
        self.assertEqual(signal.evidence['bos']['known_at'], t(15))
        self.assertEqual(signal.evidence['conf']['known_at'], t(25))
        self.assertFalse(signal.trade_entry_allowed)

    def test_full_history_event_index_matches_each_observed_prefix(self):
        rng = random.Random(413)
        cs = []
        price = 100.0
        for i in range(160):
            close = price + rng.uniform(-2, 2)
            cs.append(candle(i, price, max(price, close) + rng.random(), min(price, close) - rng.random(), close))
            price = close
        full = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs, timeframe_minutes=5))
        for i in range(len(cs)):
            full.advance(i)
            if i < 8 or i % 13:
                continue
            prefix_cs = cs[:i + 1]
            prefix = SourceSeries('BTCUSDT', 5, prefix_cs, analyze_market(prefix_cs, timeframe_minutes=5))
            for n in range(i + 1):
                prefix.advance(n)
            self.assertEqual(full.trend, prefix.trend)
            self.assertEqual(evidence_json(full.structure), evidence_json(prefix.structure))
            self.assertEqual(evidence_json([asdict(p) for p in full.pools.values()]), evidence_json([asdict(p) for p in prefix.pools.values()]))
            self.assertEqual(evidence_json([asdict(z) for z in full.zones]), evidence_json([asdict(z) for z in prefix.zones]))
            self.assertEqual(full.counts, prefix.counts)

    def test_future_ohlc_mutation_cannot_change_prior_zones_or_pools(self):
        cs = [candle(i, 100, 101 + i % 5, 99 - i % 3, 100) for i in range(25)]
        future = [candle(i, 100, 120 + i, 50 - i, 100) for i in range(25, 30)]
        a = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        b = SourceSeries('BTCUSDT', 5, cs + future, analyze_market(cs + future))
        for i in range(len(cs)):
            a.advance(i); b.advance(i)
        self.assertEqual(evidence_json([asdict(z) for z in a.zones]), evidence_json([asdict(z) for z in b.zones]))
        self.assertEqual(a.pools, b.pools)

    def test_known_structure_cannot_substitute_for_missing_reaction_bos_conf(self):
        cs = [candle(i, 100, 101, 99, 100) for i in range(3)]
        series = {tf: SourceSeries('BTCUSDT', tf, cs, analyze_market(cs)) for tf in (5, 15, 60, 240)}
        e = SourceEngine('BTCUSDT', series)
        for i in range(3):
            e.advance(5, i)
        self.assertEqual(e.signals, [])

    def test_raid_metadata_is_real_known_event_not_boolean(self):
        cs = [candle(0, 100, 101, 99, 100), candle(1, 100, 102, 98, 100)]
        s = SourceSeries('BTCUSDT', 5, cs, analyze_market(cs))
        s.advance(0)
        s.pools['old'] = Pool('old', 'low', 99, START, 'SSL', 'EXTERNAL')
        s.advance(1)
        self.assertEqual(s.raids[-1], Raid('LONG', cs[1].close_time, 99, 98, 1, ('old',)))
        self.assertNotIn('old', s.pools)


class SourcePortfolioTests(unittest.TestCase):
    def test_risk_max_and_full_stop_cost_accounting(self):
        with self.assertRaises(ValueError):
            SourceRiskPolicy(risk_fraction=0.0201)
        p = SourcePortfolio()
        p.offer(signal())
        p.on_bar('BTCUSDT', candle(0, 101, 102, 99, 100))
        self.assertIsNotNone(p.position)
        p.on_bar('BTCUSDT', candle(1, 100, 101, 94, 95))
        t = p.trades[0]
        self.assertAlmostEqual(t['net_pnl'], -1170 * 0.02)
        self.assertAlmostEqual(t['result_R'], -1)
        self.assertAlmostEqual(t['quote_gross_pnl'] - t['slippage'] - t['fees'], t['net_pnl'])

    def test_entry_bar_favourable_high_before_fill_is_not_profit(self):
        p = SourcePortfolio()
        p.offer(signal())
        p.on_bar('BTCUSDT', candle(0, 101, 120, 99, 100))
        self.assertEqual(p.trades[0]['status'], 'OPEN')
        p.on_bar('BTCUSDT', candle(1, 100, 111, 99, 110))
        self.assertEqual(p.trades[0]['status'], 'CLOSED')

    def test_stop_dominates_same_bar_targets_and_gap_worsens_risk(self):
        p = SourcePortfolio()
        p.offer(signal())
        p.on_bar('BTCUSDT', candle(0, 101, 120, 94, 110))
        self.assertEqual(p.trades[0]['exit_reason'], 'ORIGINAL_SL_STOP_FIRST')
        q = SourcePortfolio()
        q.offer(signal())
        q.on_bar('BTCUSDT', candle(0, 101, 102, 99, 100))
        q.on_bar('BTCUSDT', candle(1, 90, 94, 88, 91))
        self.assertLess(q.trades[0]['result_R'], -1)

    def test_range_80_20_keeps_original_stop_no_be(self):
        p = SourcePortfolio()
        p.offer(signal(fractions=(0.8, 0.2), targets=(110, 120)))
        p.on_bar('BTCUSDT', candle(0, 101, 102, 99, 100))
        p.on_bar('BTCUSDT', candle(1, 100, 111, 99, 110))
        self.assertAlmostEqual(p.position['remaining'] / p.position['quantity'], 0.2)
        self.assertEqual(p.position['stop'], 95)
        p.on_bar('BTCUSDT', candle(2, 110, 111, 94, 96))
        self.assertEqual(len(p.trades[0]['fills']), 2)
        self.assertEqual(p.trades[0]['fills'][-1]['reason'], 'ORIGINAL_SL_STOP_FIRST')

    def test_short_symmetry_and_backtest_shadow_equivalence(self):
        portfolios = [SourcePortfolio(mode=mode) for mode in ('BACKTEST', 'SHADOW')]
        for p in portfolios:
            p.offer(signal('SHORT'))
            p.on_bar('BTCUSDT', candle(0, 99, 101, 98, 100))
            p.on_bar('BTCUSDT', candle(1, 100, 101, 89, 90))
        self.assertEqual(portfolios[0].trades, portfolios[1].trades)
        self.assertGreater(portfolios[0].trades[0]['net_pnl'], 0)

    def test_one_sequential_account_and_censored_endpoint(self):
        p = SourcePortfolio()
        self.assertTrue(p.offer(signal()))
        self.assertFalse(p.offer(signal('SHORT')))
        p.on_bar('BTCUSDT', candle(0, 101, 102, 99, 100))
        self.assertFalse(p.offer(signal('SHORT')))
        p.mark(START + timedelta(minutes=5))
        self.assertEqual(p.trades[0]['status'], 'OPEN')
        self.assertIsNotNone(p.position)

    def test_signal_close_cannot_fill_retroactively_and_cancel_is_causal(self):
        s = signal()
        p = SourcePortfolio()
        p.offer(s)
        before = Candle(START - timedelta(minutes=5), START, 101, 111, 99, 110)
        p.on_bar('BTCUSDT', before)
        self.assertEqual(p.trades, [])
        p.cancel(s.signal_id, START, 'FLOW_DESTINATION_TESTED')
        p.on_bar('BTCUSDT', candle(0, 101, 102, 99, 100))
        self.assertEqual(p.trades, [])


if __name__ == '__main__':
    unittest.main()
