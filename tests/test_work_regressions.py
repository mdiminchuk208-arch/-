import unittest
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

from crypto_bot.strategy.market_analysis import MarketAnalysisError, analyze_market
from crypto_bot.strategy.mtf_sfp import link_sfp_formations_to_ltf_bos
from crypto_bot.strategy.range_engine import RangeAnalysisError, analyze_ranges
from crypto_bot.strategy.sfp import detect_sfp
from test_mtf_sfp import event, report, MarketEventKind as K
from test_range_engine import base_report, bullish_range_events, c
from test_sfp import c as minute_c


class WorkRegressions(unittest.TestCase):
    def test_unknown_direction_is_not_silently_treated_as_short(self):
        from crypto_bot.strategy.trade_plan import ote_entry_zone, rr_ratio, select_first_opposing_poi_fta, PriceZone
        operations = (
            lambda: ote_entry_zone(direction='UNKNOWN', impulse_start_price=100, impulse_end_price=120),
            lambda: rr_ratio(direction='UNKNOWN', entry_price=100, stop_loss_price=110, target_price=90),
            lambda: select_first_opposing_poi_fta(direction='UNKNOWN', entry_zone=PriceZone(99, 101), opposing_poi_zones=(PriceZone(90, 95),)),
        )
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                operation()

    def test_order_block_geometry_rejects_unclosed_or_nonadjacent_candles(self):
        from crypto_bot.common.models import Direction
        from crypto_bot.strategy.order_block import OrderBlockAssessment, derive_qualified_order_block_geometry
        assessment = OrderBlockAssessment(True, True, 'A', ())
        engulfed, engulfing = minute_c(0, 100, 108, 99, 105), minute_c(1, 105, 110, 98, 109)
        for previous, current in ((replace(engulfed, is_closed=False), engulfing),
                                  (engulfed, replace(engulfing, is_closed=False)),
                                  (engulfed, replace(engulfing, open_time=engulfing.open_time + timedelta(seconds=5)))):
            with self.subTest(previous=previous, current=current), self.assertRaises(ValueError):
                derive_qualified_order_block_geometry(direction=Direction.LONG, engulfed_candle=previous,
                                                     engulfing_candle=current, assessment=assessment)

    def test_invalid_post_bos_impulse_rejects_geometry_without_crashing_mtf(self):
        from test_trade_plan import Phase1420PlanStatusTests
        from crypto_bot.strategy.market_analysis import TrendState
        from crypto_bot.strategy.mtf_sfp import _attach_entry_geometry
        opp = Phase1420PlanStatusTests()._opp()
        diagnostic = SimpleNamespace(
            transition_id=1, bos_kind=opp.ltf_bos_kind.value,
            bos_index=opp.ltf_bos_candle_index, bos_time=opp.ltf_bos_event_time,
            resolved_time=opp.ltf_bos_event_time + timedelta(minutes=15),
            resolved_trend=TrendState.BULLISH, resolution_mode='EXPECTED_OPPOSITE_FAST_PATH',
            broken_extreme_price=110, selected_anchor_level_id=1, selected_correction_level_id=2,
        )
        r = SimpleNamespace(structure_transition_diagnostics=(diagnostic,),
                            levels=(SimpleNamespace(level_id=1, price=100), SimpleNamespace(level_id=2, price=95)))
        rejected = _attach_entry_geometry((opp,), r)[0]
        self.assertEqual(rejected.entry_plan_status, 'REJECTED_ENTRY_GEOMETRY')
        self.assertIn('upward impulse', rejected.entry_geometry_policy)
        self.assertFalse(rejected.entry_search_allowed)
        self.assertFalse(rejected.trade_entry_allowed)
        self.assertEqual(rejected.ltf_bos_event_time, opp.ltf_bos_event_time)

    def test_sfp_requires_immediate_next_candle(self):
        sweep = minute_c(0, 99, 102, 98, 99)
        self.assertFalse(detect_sfp(sweep, minute_c(4, 99, 100, 98, 99), 100, 'high').valid)

    def test_nonfinite_sfp_levels_are_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                detect_sfp(minute_c(0, 99, 102, 98, 99), minute_c(1, 99, 100, 98, 99), value, 'high')

    def test_overlapping_history_is_rejected_by_both_engines(self):
        candles = [c(0), replace(c(1), open_time=c(0).open_time + timedelta(minutes=30))]
        with self.assertRaises(MarketAnalysisError):
            analyze_market(candles)
        with self.assertRaises(RangeAnalysisError):
            analyze_ranges(candles, base_report(candles, []))

    def test_range_rejects_future_events_in_external_base_report(self):
        candles = [c(i) for i in range(6)]
        with self.assertRaises(RangeAnalysisError):
            analyze_ranges(candles, base_report(candles, bullish_range_events()))

    def test_ambiguous_range_episodes_are_resolved_without_reuse(self):
        candles = [c(i) for i in range(11)]
        candles[7] = c(7, 105, 112, 98, 105)
        candles[9] = c(9, 105, 114, 96, 105)
        r = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        self.assertEqual(len(r.sweep_episodes), 2)
        self.assertTrue(all(ep.status == 'AMBIGUOUS_DUAL_SIDE_SWEEP' for ep in r.sweep_episodes))
        self.assertTrue(all(ep.resolved_index == 7 for ep in r.sweep_episodes))
        self.assertEqual(r.events, ())

    def test_later_opposite_opportunity_does_not_renumber_previous(self):
        sfp_short = event(K.BEARISH_SFP_FORMATION_CONFIRMED, 60)
        bos_short = event(K.BULLISH_STRUCTURE_BROKEN_BOS, 70, episode=None)
        before = link_sfp_formations_to_ltf_bos(report(sfp_short), report(bos_short), htf_minutes=60, ltf_minutes=5)
        after = link_sfp_formations_to_ltf_bos(
            report(sfp_short, event(K.BULLISH_SFP_FORMATION_CONFIRMED, 80, episode=2)),
            report(bos_short, event(K.BEARISH_STRUCTURE_BROKEN_BOS, 90, level_id=2, episode=None)),
            htf_minutes=60, ltf_minutes=5,
        )
        self.assertEqual(before.opportunities[0], after.opportunities[0])
