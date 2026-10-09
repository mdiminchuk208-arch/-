import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.replay import StrategySignal
from crypto_bot.strategy.trade_plan import PriceZone
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy, VirtualPortfolio


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def bar(i, o=100, h=101, low=99, close=100):
    t = BASE + timedelta(minutes=5 * i)
    return Candle(t, t + timedelta(minutes=5), o, h, low, close)


def signal(i=0, symbol='TEST', ident='one', direction=Direction.LONG, score=100, mode='BACKTEST'):
    t = bar(i).close_time
    return StrategySignal(ident, symbol, 60, 5, direction, t, BASE - timedelta(minutes=10),
                          BASE - timedelta(minutes=5), 'READY_FOR_VIRTUAL_ENTRY', score, ('TEST_QUALIFIED',),
                          entry_zone=PriceZone(99, 101), optimal_entry=100,
                          stop_loss=95 if direction == Direction.LONG else 105,
                          targets=(110, 120, 130) if direction == Direction.LONG else (90, 80, 70), mode=mode,
                          entry_geometry_ready_time=BASE, levels_known_at=t,
                          source_qualification_known_at=BASE,
                          source_poi_kind='ORDER_BLOCK', source_entry_path='DIRECT_OB',
                          source_qualification_evidence=('TEST_SOURCE_CONTEXT',))


class VirtualPortfolioTests(unittest.TestCase):
    def portfolio(self, **kwargs):
        return VirtualPortfolio(policy=SimulationPolicy(fee_fraction=0, slippage_fraction=0, **kwargs))

    def open_position(self, p, direction=Direction.LONG):
        p.step({'TEST': bar(0)}, [signal(direction=direction)])
        self.assertEqual(p.positions, {})
        p.step({'TEST': bar(1)})
        return p.positions['TEST']

    def test_entry_only_on_next_open_no_signal_candle_fill(self):
        p = self.portfolio()
        pos = self.open_position(p)
        self.assertEqual(pos.entry_time, bar(1).open_time)
        self.assertEqual(pos.quantity, 40)
        self.assertFalse(p.trade_entry_allowed)

    def test_tp_fractions_and_breakeven_long(self):
        p = self.portfolio()
        self.open_position(p)
        p.step({'TEST': bar(2, 108, 111, 107, 110)})
        self.assertAlmostEqual(p.positions['TEST'].remaining_fraction, .6)
        self.assertEqual(p.positions['TEST'].stop_loss, 100)
        p.step({'TEST': bar(3, 115, 121, 114, 120)})
        self.assertAlmostEqual(p.positions['TEST'].remaining_fraction, .3)
        p.step({'TEST': bar(4, 125, 131, 124, 130)})
        self.assertEqual(p.positions, {})
        exits = [d for d in p.journal if d.action == 'VIRTUAL_EXIT']
        self.assertEqual([d.reason for d in exits], ['TP1', 'TP2', 'TP3'])
        self.assertEqual([d.quantity for d in exits], [16, 12, 12])
        self.assertAlmostEqual(p.equity, 10760)

    def test_tp_fractions_short(self):
        p = self.portfolio()
        self.open_position(p, Direction.SHORT)
        p.step({'TEST': bar(2, 92, 93, 89, 90)})
        p.step({'TEST': bar(3, 85, 86, 79, 80)})
        p.step({'TEST': bar(4, 75, 76, 69, 70)})
        self.assertEqual(p.positions, {})
        self.assertAlmostEqual(p.equity, 10760)

    def test_old_stop_wins_same_bar_stop_and_target(self):
        p = self.portfolio()
        self.open_position(p)
        p.step({'TEST': bar(2, 100, 131, 94, 110)})
        self.assertEqual(p.positions, {})
        self.assertAlmostEqual(p.equity, 9800)
        self.assertEqual(p.journal[-1].reason, 'STOP_FIRST_CONSERVATIVE')

    def test_new_breakeven_wins_over_higher_tps_in_ambiguous_bar(self):
        p = self.portfolio()
        self.open_position(p)
        p.step({'TEST': bar(2, 105, 131, 99, 110)})
        self.assertEqual(p.positions, {})
        self.assertEqual([d.reason for d in p.journal if d.action == 'VIRTUAL_EXIT'], ['TP1', 'BREAKEVEN_SAME_BAR_CONSERVATIVE'])
        self.assertAlmostEqual(p.equity, 10160)

    def test_breakeven_covers_fees_and_slippage_both_directions(self):
        for direction in Direction:
            p = VirtualPortfolio()
            pos = self.open_position(p, direction)
            be = p._breakeven(pos)
            exit_price = p._exit_price(be, direction)
            sign = 1 if direction == Direction.LONG else -1
            net = sign * (exit_price - pos.entry_price) - p.policy.fee_fraction * (pos.entry_price + exit_price)
            self.assertAlmostEqual(net, 0, places=10)

    def test_actual_breakeven_exit_has_zero_net_remaining_pnl(self):
        for direction in Direction:
            p = VirtualPortfolio()
            self.open_position(p, direction)
            tp = bar(2, 108, 111, 107, 110) if direction == Direction.LONG else bar(2, 92, 93, 89, 90)
            p.step({'TEST': tp})
            p.step({'TEST': bar(3, 101, 102, 99, 101) if direction == Direction.LONG else bar(3, 99, 100, 98, 99)})
            self.assertEqual(p.positions, {})
            self.assertAlmostEqual(p.journal[-1].net_pnl, 0, places=9)

    def test_isolated_margin_guard_blocks_too_large_quantity(self):
        p = self.portfolio()
        p.step({'TEST': bar(0)}, [replace(signal(), stop_loss=99.99, entry_zone=PriceZone(100, 100))])
        p.step({'TEST': bar(1)})
        self.assertEqual(p.positions, {})
        self.assertEqual(p.journal[-1].reason, 'ISOLATED_MARGIN_BUDGET')

    def test_gap_stop_uses_adverse_open(self):
        p = self.portfolio()
        self.open_position(p)
        p.step({'TEST': bar(2, 90, 92, 89, 91)})
        self.assertAlmostEqual(p.equity, 9600)
        self.assertEqual(p.journal[-1].price, 90)

    def test_tp1_below_cost_breakeven_cannot_create_unreachable_be_fill(self):
        for direction in Direction:
            with self.subTest(direction=direction):
                p = VirtualPortfolio()
                targets = (100.05, 110, 120) if direction == Direction.LONG else (99.95, 90, 80)
                ready = replace(signal(direction=direction), entry_zone=PriceZone(100, 100), targets=targets)
                p.step({'TEST': bar(0)}, [ready])
                p.step({'TEST': bar(1, 100, 100.06, 99.94, 100)})
                self.assertEqual(p.positions, {})
                self.assertEqual(p.journal[-1].reason, 'TP1_NOT_POSITIVE_AFTER_COSTS')
                self.assertFalse(any(d.action in ('VIRTUAL_ENTRY', 'VIRTUAL_EXIT') for d in p.journal))

    def test_aggregate_risk_cap_and_deterministic_batch_allocation(self):
        p = self.portfolio()
        names = ('A', 'B', 'C', 'D')
        p.step({s: bar(0) for s in reversed(names)}, [signal(symbol=s, ident=s) for s in reversed(names)])
        p.step({s: bar(1) for s in names})
        self.assertEqual(tuple(p.positions), ('A', 'B', 'C'))
        self.assertEqual(p.journal[-1].reason, 'TOTAL_RISK_CAP_6_PERCENT')

    def test_previous_position_and_reentry_score_guards(self):
        p = self.portfolio()
        self.open_position(p)
        p.step({'TEST': bar(2)}, [signal(2, ident='second')])
        p.step({'TEST': bar(3, 100, 101, 94, 95)}, [signal(3, ident='third', score=74)])
        p.step({'TEST': bar(4)})
        self.assertTrue(any(d.reason == 'PREVIOUS_POSITION_STILL_OPEN' for d in p.journal))
        self.assertEqual(p.journal[-1].reason, 'REENTRY_SCORE_BELOW_75')
        p.step({'TEST': bar(5)}, [signal(5, ident='fourth', score=75)])
        p.step({'TEST': bar(6)})
        self.assertIn('TEST', p.positions)

    def test_daily_limit_blocks_new_entries_but_manages_open_positions(self):
        p = self.portfolio(risk_fraction=.03, daily_loss_limit=.025)
        p.step({'A': bar(0), 'B': bar(0)}, [signal(symbol='A', ident='a'), signal(symbol='B', ident='b')])
        p.step({'A': bar(1), 'B': bar(1)})
        p.step({'A': bar(2, 100, 101, 94, 95), 'B': bar(2)}, [signal(2, symbol='A', ident='a2')])
        p.step({'A': bar(3), 'B': bar(3, 100, 101, 94, 95)})
        self.assertEqual(p.positions, {})
        self.assertTrue(any(d.reason == 'DAILY_LOSS_LIMIT_LATCHED' for d in p.journal))
        self.assertEqual(len([d for d in p.journal if d.action == 'VIRTUAL_EXIT']), 2)

    def test_invalidated_setup_is_terminal_and_cannot_be_reused(self):
        p = self.portfolio()
        p.step({'TEST': bar(0)}, [replace(signal(), status='INVALIDATED', invalidation_reasons=('HTF_INVALIDATED',))])
        p.step({'TEST': bar(1)}, [signal(1)])
        p.step({'TEST': bar(2)})
        self.assertEqual(p.positions, {})

    def test_rejected_geometry_is_terminal(self):
        p = self.portfolio()
        p.step({'TEST': bar(0)}, [replace(signal(), status='REJECTED_ENTRY_GEOMETRY')])
        p.step({'TEST': bar(1)}, [signal(1)])
        p.step({'TEST': bar(2)})
        self.assertEqual(p.positions, {})

    def test_daily_limit_stays_latched_after_profit_until_next_utc_day(self):
        p = self.portfolio(risk_fraction=.03, daily_loss_limit=.025)
        p.step({'A': bar(0), 'B': bar(0)}, [signal(symbol='A', ident='a'), signal(symbol='B', ident='b')])
        p.step({'A': bar(1), 'B': bar(1)})
        p.step({'A': bar(2, 100, 101, 94, 95), 'B': bar(2, 108, 131, 107, 130)})
        self.assertGreater(p.equity, p._day_start_equity)
        p.step({'A': bar(3), 'B': bar(3)}, [signal(3, symbol='A', ident='a2')])
        p.step({'A': bar(4), 'B': bar(4)})
        self.assertTrue(any(d.reason == 'DAILY_LOSS_LIMIT_LATCHED' for d in p.journal))
        for i in range(5, 288):
            p.step({'A': bar(i), 'B': bar(i)})
        p.step({'A': bar(288), 'B': bar(288)}, [signal(288, symbol='A', ident='a3')])
        p.step({'A': bar(289), 'B': bar(289)})
        self.assertIn('A', p.positions)

    def test_same_open_entries_do_not_use_other_symbols_future_close_profit(self):
        p = self.portfolio(risk_fraction=.03)
        p.step({'A': bar(0), 'B': bar(0), 'C': bar(0)}, [signal(symbol='A', ident='a'), signal(symbol='B', ident='b')])
        p.step({'A': bar(1), 'B': bar(1), 'C': bar(1)}, [signal(1, symbol='C', ident='c')])
        p.step({'A': bar(2, 108, 131, 107, 130), 'B': bar(2), 'C': bar(2)})
        self.assertTrue(any(d.symbol == 'C' and d.reason == 'TOTAL_RISK_CAP_6_PERCENT' for d in p.journal))

    def test_timeframe_change_is_rejected(self):
        p = self.portfolio()
        p.step({'TEST': bar(0)})
        changed = replace(bar(1), close_time=bar(1).close_time + timedelta(minutes=5))
        with self.assertRaises(ValueError):
            p.step({'TEST': changed})

    def test_ready_signal_requires_causal_reference_availability(self):
        for change in ({'levels_known_at': bar(1).close_time}, {'entry_geometry_ready_time': None},
                       {'entry_geometry_ready_time': BASE - timedelta(minutes=20)}):
            p = self.portfolio()
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.step({'TEST': bar(0)}, [replace(signal(), **change)])
            self.assertEqual(p.journal, ())

    def test_future_signal_or_missing_position_bar_does_not_mutate_state(self):
        p = self.portfolio()
        with self.assertRaises(ValueError):
            p.step({'TEST': bar(0)}, [signal(1)])
        self.assertEqual(p.journal, ())
        self.open_position(p)
        journal = p.journal
        with self.assertRaises(ValueError):
            p.step({'OTHER': bar(2)})
        self.assertEqual(p.journal, journal)

    def test_duplicate_and_gap_batches_are_rejected(self):
        p = self.portfolio()
        p.step({'TEST': bar(0)})
        for i in (0, 2):
            with self.subTest(i=i), self.assertRaises(ValueError):
                p.step({'TEST': bar(i)})

    def test_policy_and_live_safety(self):
        for changes in ({'risk_fraction': .01}, {'max_total_risk': .07}, {'leverage': 6},
                        {'margin_mode': 'Cross'}, {'fee_fraction': float('nan')}, {'reentry_min_score': 74}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                SimulationPolicy(**changes)
        with self.assertRaises(ValueError):
            VirtualPortfolio(mode='LIVE')
        with self.assertRaises(TypeError):
            StrategySignal('x', 'X', 60, 5, Direction.LONG, BASE, BASE, BASE, 'WAITING', 0, (), trade_entry_allowed=True)

    def test_repeat_run_and_shadow_are_equivalent(self):
        results = []
        for mode in ('BACKTEST', 'BACKTEST', 'SHADOW'):
            p = VirtualPortfolio(mode=mode, policy=SimulationPolicy(fee_fraction=0, slippage_fraction=0))
            p.step({'TEST': bar(0)}, [signal(mode=mode)])
            p.step({'TEST': bar(1)})
            p.step({'TEST': bar(2, 100, 131, 94, 110)})
            results.append((p.equity, p.journal))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertTrue(all(not d.trade_entry_allowed for d in results[2][1]))
