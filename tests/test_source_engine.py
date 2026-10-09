from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import random
import unittest

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.source_engine import (Pool, Raid, SourceEngine, SourceSeries, SourceSignal, Zone,
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
