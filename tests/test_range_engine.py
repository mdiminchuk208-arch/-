import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport,
    MarketEvent,
    MarketEventKind,
    OrderBlockReadiness,
    TrendState,
)
from crypto_bot.strategy.range_engine import (
    RangeBoundaryState,
    RangeDetectionParams,
    RangeStatus,
)
from range_test_support import analyze_ranges, augment_market_report_with_range_sfps
from crypto_bot.strategy.mtf_sfp import MtfSfpStatus, link_sfp_formations_to_ltf_bos


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def c(i, o=105, h=108, l=102, cl=105):
    start = BASE + timedelta(hours=i)
    return Candle(start, start + timedelta(hours=1), o, h, l, cl, True)


def ev(kind, idx, price, level_id=1, level_price=None):
    return MarketEvent(
        kind=kind,
        candle_index=idx,
        event_time=BASE + timedelta(hours=idx + 1),
        price=price,
        level_id=level_id,
        level_price=price if level_price is None else level_price,
        note="fixture",
    )


def base_report(candles, events):
    return MarketAnalysisReport(
        candle_count=len(candles),
        final_trend=TrendState.UNKNOWN,
        levels=(),
        sweep_episodes=(),
        events=tuple(events),
        order_block_readiness=OrderBlockReadiness(False, "BLOCKED", ("fixture",)),
        structure_policy="fixture",
        sfp_timeframe_preference="fixture",
        sfp_policy="fixture",
    )


def bullish_range_events(midpoint_price=105.0, include_midpoint=True):
    events = [
        ev(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 0, 103, 10, 102),
        ev(MarketEventKind.SWING_HIGH_CONFIRMED, 2, 110, 11, 110),
        ev(MarketEventKind.SWING_LOW_CONFIRMED, 4, 100, 12, 100),
    ]
    if include_midpoint:
        events.append(ev(MarketEventKind.SWING_HIGH_CONFIRMED, 6, midpoint_price, 13, midpoint_price))
    return events


class RangeEngineTests(unittest.TestCase):
    def test_source_boundary_order_and_midpoint_reaction_validate_range(self):
        candles = [c(i) for i in range(9)]
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        self.assertEqual(len(report.ranges), 1)
        r = report.ranges[0]
        self.assertEqual(r.first_boundary_kind, "high")
        self.assertEqual(r.first_boundary_price, 110)
        self.assertEqual(r.second_boundary_kind, "low")
        self.assertEqual(r.second_boundary_price, 100)
        self.assertEqual(r.midpoint, 105)
        self.assertTrue(r.ever_validated)
        self.assertEqual(r.status, RangeStatus.VALIDATED)

    def test_up_impulse_rejects_inverted_boundary_geometry(self):
        candles = [c(i) for i in range(8)]
        events = [
            ev(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 0, 103, 10, 102),
            ev(MarketEventKind.SWING_HIGH_CONFIRMED, 2, 110, 11, 110),
            ev(MarketEventKind.SWING_LOW_CONFIRMED, 4, 112, 12, 112),
        ]
        report = analyze_ranges(candles, base_report(candles, events))
        self.assertEqual(report.ranges, ())

    def test_down_impulse_rejects_inverted_boundary_geometry(self):
        candles = [c(i) for i in range(8)]
        events = [
            ev(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 0, 107, 10, 108),
            ev(MarketEventKind.SWING_LOW_CONFIRMED, 2, 100, 11, 100),
            ev(MarketEventKind.SWING_HIGH_CONFIRMED, 4, 98, 12, 98),
        ]
        report = analyze_ranges(candles, base_report(candles, events))
        self.assertEqual(report.ranges, ())

    def test_midpoint_tolerance_is_explicit_backtest_parameter(self):
        candles = [c(i) for i in range(9)]
        source = base_report(candles, bullish_range_events(midpoint_price=105.9))
        tight = analyze_ranges(candles, source, params=RangeDetectionParams(midpoint_tolerance_fraction=0.08))
        wide = analyze_ranges(candles, source, params=RangeDetectionParams(midpoint_tolerance_fraction=0.10))
        self.assertFalse(tight.ranges[0].ever_validated)
        self.assertTrue(wide.ranges[0].ever_validated)

    def test_prevalidation_boundary_raid_consumes_liquidity_but_does_not_kill_range(self):
        candles = [c(i) for i in range(10)]
        # Boundary #2 is already confirmed. This later candle raids the upper boundary and
        # even closes outside before the midpoint validation event becomes known. The range
        # source allows deviations outside boundaries, so the whole range is not hard-broken.
        # The original upper-boundary liquidity is nevertheless consumed causally.
        candles[5] = c(5, 105, 112, 104, 111)
        # A later would-be SFP cannot reuse that already-consumed upper boundary.
        candles[7] = c(7, 106, 113, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        self.assertTrue(report.ranges[0].ever_validated)
        self.assertEqual(report.ranges[0].status, RangeStatus.VALIDATED)
        self.assertEqual(report.ranges[0].upper_boundary_state, RangeBoundaryState.CONSUMED)
        self.assertEqual(report.sfp_formation_count, 0)

    def test_consumed_boundary_does_not_reactivate_after_price_returns_inside(self):
        candles = [c(i) for i in range(12)]
        candles[7] = c(7, 106, 112, 104, 111)  # first strict upper raid consumes original liquidity
        candles[8] = c(8, 108, 109, 103, 106)  # price returns inside
        candles[9] = c(9, 106, 113, 104, 109)  # second upper raid must not reuse/reactivate it
        candles[10] = c(10, 108, 109, 103, 106)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        self.assertEqual(report.ranges[0].upper_boundary_state, RangeBoundaryState.CONSUMED)
        upper_episodes = [ep for ep in report.sweep_episodes if ep.side == "high"]
        self.assertEqual(len(upper_episodes), 1)
        self.assertEqual(report.sfp_formation_count, 0)

    def test_postvalidation_outside_close_consumes_boundary_without_hard_range_break(self):
        candles = [c(i) for i in range(10)]
        candles[7] = c(7, 106, 112, 104, 111)  # strict raid, but close does not return inside
        candles[8] = c(8, 108, 109, 103, 106)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        self.assertTrue(report.ranges[0].ever_validated)
        self.assertEqual(report.ranges[0].status, RangeStatus.VALIDATED)
        self.assertEqual(report.ranges[0].upper_boundary_state, RangeBoundaryState.CONSUMED)
        self.assertEqual(report.sfp_formation_count, 0)
        self.assertEqual(len(report.sweep_episodes), 1)
        self.assertEqual(report.sweep_episodes[0].status, "CONSUMED_NO_SFP")

    def test_internal_bos_inside_range_rejects_before_midpoint(self):
        candles = [c(i) for i in range(9)]
        events = bullish_range_events()
        events.append(ev(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 5, 104, 20, 103))
        report = analyze_ranges(candles, base_report(candles, events))
        self.assertEqual(report.ranges[0].status, RangeStatus.REJECTED_INTERNAL_STRUCTURE)
        self.assertFalse(report.ranges[0].ever_validated)

    def test_upper_range_boundary_can_form_bearish_sfp(self):
        candles = [c(i) for i in range(10)]
        candles[7] = c(7, 106, 112, 104, 109)  # sweep above 110, close back inside
        candles[8] = c(8, 108, 109, 103, 106)  # open inside -> SFP formed at open
        merged, ranges = augment_market_report_with_range_sfps(
            candles, base_report(candles, bullish_range_events())
        )
        sfps = [
            e for e in ranges.events
            if e.kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED
        ]
        self.assertEqual(len(sfps), 1)
        self.assertEqual(sfps[0].level_price, 110)
        self.assertEqual(sfps[0].sfp_pattern_extreme_price, 112)
        self.assertEqual(sfps[0].liquidity_origin, "RANGE_BOUNDARY")
        self.assertEqual(sfps[0].range_id, 1)
        self.assertIn(sfps[0], merged.events)
        self.assertTrue(merged.sfp_liquidity_scope.startswith("STRUCTURAL_SWING_AND_RANGE_BOUNDARY"))

    def test_lower_range_boundary_mirror_can_form_bullish_sfp(self):
        candles = [c(i) for i in range(10)]
        candles[7] = c(7, 104, 106, 98, 101)
        candles[8] = c(8, 102, 108, 101, 106)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        sfps = [e for e in report.events if e.kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED]
        self.assertEqual(len(sfps), 1)
        self.assertEqual(sfps[0].level_price, 100)
        self.assertEqual(sfps[0].sfp_pattern_extreme_price, 98)

    def test_range_boundary_sfp_invalidation_uses_body_close_beyond_pattern_extreme(self):
        candles = [c(i) for i in range(11)]
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        candles[9] = c(9, 106, 114, 105, 113)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        invalid = [e for e in report.events if e.kind == MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE]
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0].price, 113)
        self.assertEqual(invalid[0].liquidity_origin, "RANGE_BOUNDARY")

    def test_next_candle_hlc_does_not_change_sfp_formation_if_open_is_same(self):
        a = [c(i) for i in range(10)]
        b = [c(i) for i in range(10)]
        a[7] = b[7] = c(7, 106, 112, 104, 109)
        a[8] = c(8, 108, 109, 103, 106)
        b[8] = c(8, 108, 109.5, 104, 108.5)
        ra = analyze_ranges(a, base_report(a, bullish_range_events()))
        rb = analyze_ranges(b, base_report(b, bullish_range_events()))
        ea = [e for e in ra.events if e.kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED]
        eb = [e for e in rb.events if e.kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED]
        self.assertEqual([(e.event_time, e.level_price) for e in ea], [(e.event_time, e.level_price) for e in eb])

    def test_dual_side_boundary_sweep_is_ambiguous_and_emits_no_sfp(self):
        candles = [c(i) for i in range(10)]
        candles[7] = c(7, 105, 112, 98, 105)
        candles[8] = c(8, 105, 108, 102, 106)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        self.assertEqual(report.sfp_formation_count, 0)
        self.assertEqual(sum(ep.status == "AMBIGUOUS_DUAL_SIDE_SWEEP" for ep in report.sweep_episodes), 2)


    def test_range_sfp_invalidation_propagates_into_mtf_gate(self):
        candles = [c(i) for i in range(12)]
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        candles[9] = c(9, 106, 114, 105, 113)  # invalidates bearish SFP at +10h close
        htf, _ = augment_market_report_with_range_sfps(
            candles, base_report(candles, bullish_range_events())
        )
        later_bos = MarketEvent(
            kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            candle_index=10,
            event_time=BASE + timedelta(hours=10, minutes=30),
            price=107,
            level_id=88,
            level_price=106,
            note="LTF later than invalidation",
        )
        ltf = base_report(candles, [later_bos])
        mtf = link_sfp_formations_to_ltf_bos(
            htf, ltf, htf_minutes=60, ltf_minutes=5,
            ltf_observation_start=BASE, ltf_observation_end=BASE + timedelta(hours=12),
        )
        range_candidates = [x for x in mtf.candidates if x.htf_liquidity_origin == "RANGE_BOUNDARY"]
        self.assertEqual(len(range_candidates), 1)
        self.assertEqual(range_candidates[0].status, MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS)
        self.assertEqual(range_candidates[0].sfp_invalidation_event_time, BASE + timedelta(hours=10))

    def test_range_origin_flows_into_mtf_and_replaces_not_implemented_blocker(self):
        candles = [c(i) for i in range(10)]
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        htf, _ = augment_market_report_with_range_sfps(
            candles, base_report(candles, bullish_range_events())
        )
        bos = MarketEvent(
            kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            candle_index=9,
            event_time=BASE + timedelta(hours=9, minutes=30),
            price=107,
            level_id=77,
            level_price=106,
            note="LTF fixture",
        )
        ltf = base_report(candles, [bos])
        mtf = link_sfp_formations_to_ltf_bos(
            htf, ltf, htf_minutes=60, ltf_minutes=5,
            ltf_observation_start=BASE, ltf_observation_end=BASE + timedelta(hours=10),
        )
        range_candidates = [x for x in mtf.candidates if x.htf_liquidity_origin == "RANGE_BOUNDARY"]
        self.assertEqual(len(range_candidates), 1)
        self.assertEqual(range_candidates[0].status, MtfSfpStatus.LTF_BOS_CONFIRMED)
        self.assertNotIn("RANGE_BOUNDARY_SFP_NOT_IMPLEMENTED", mtf.entry_engine_blocking_reasons)
        self.assertNotIn("RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED", mtf.entry_engine_blocking_reasons)


if __name__ == "__main__":
    unittest.main()
