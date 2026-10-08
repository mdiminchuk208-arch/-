import unittest
from datetime import timedelta

from crypto_bot.strategy.market_analysis import MarketEventKind
from crypto_bot.strategy.range_engine import (
    RangeBoundaryClarityReview,
    RangeBoundaryState,
    RangeStatus,
    analyze_ranges,
    range_review_key,
)
from test_range_engine import BASE, base_report, bullish_range_events, c, ev


class Phase1419RangeLifecycleTests(unittest.TestCase):
    def _pass_report(self, candles, events):
        base = base_report(candles, events)
        initial = analyze_ranges(candles, base)
        reviews = {range_review_key(item): RangeBoundaryClarityReview.PASS for item in initial.ranges}
        return analyze_ranges(candles, base, boundary_clarity_reviews=reviews)

    def test_one_consumed_boundary_does_not_retire_range(self):
        candles = [c(i) for i in range(10)]
        candles[7] = c(7, 106, 112, 104, 111)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        item = report.ranges[0]
        self.assertEqual(item.status, RangeStatus.VALIDATED)
        self.assertEqual(item.upper_boundary_state, RangeBoundaryState.CONSUMED)
        self.assertEqual(item.lower_boundary_state, RangeBoundaryState.ACTIVE)

    def test_second_consumed_boundary_retires_range_at_exhaustion_time(self):
        candles = [c(i) for i in range(11)]
        candles[7] = c(7, 106, 112, 104, 111)
        candles[8] = c(8, 102, 108, 98, 101)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        item = report.ranges[0]
        self.assertEqual(item.status, RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED)
        self.assertEqual(item.status_time, BASE + timedelta(hours=9))
        self.assertEqual(item.upper_boundary_state, RangeBoundaryState.CONSUMED)
        self.assertEqual(item.lower_boundary_state, RangeBoundaryState.CONSUMED)

    def test_last_boundary_sweep_can_finish_sfp_after_retirement(self):
        candles = [c(i) for i in range(11)]
        candles[7] = c(7, 106, 112, 104, 111)
        candles[8] = c(8, 102, 108, 98, 101)
        report = self._pass_report(candles, bullish_range_events())
        self.assertEqual(report.ranges[0].status, RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED)
        sfps = [e for e in report.events if e.kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED]
        self.assertEqual(len(sfps), 1)
        self.assertEqual(sfps[0].event_time, BASE + timedelta(hours=9))

    def test_formed_sfp_invalidation_continues_after_range_retirement(self):
        candles = [c(i) for i in range(12)]
        candles[7] = c(7, 106, 112, 104, 111)
        candles[8] = c(8, 102, 108, 98, 101)
        candles[10] = c(10, 99, 100, 96, 97)
        report = self._pass_report(candles, bullish_range_events())
        invalid = [e for e in report.events if e.kind == MarketEventKind.BULLISH_SFP_INVALIDATED_CLOSE]
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0].price, 97)

    def test_prevalidation_liquidity_exhaustion_keeps_actual_raid_time(self):
        candles = [c(i) for i in range(10)]
        candles[5] = c(5, 105, 112, 98, 105)
        report = analyze_ranges(candles, base_report(candles, bullish_range_events()))
        item = report.ranges[0]
        self.assertTrue(item.ever_validated)
        self.assertEqual(item.status, RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED)
        self.assertEqual(item.status_time, BASE + timedelta(hours=6))

    def test_new_bos_creates_independent_range_without_reactivating_old(self):
        candles = [c(i) for i in range(15)]
        candles[7] = c(7, 106, 122, 104, 120)
        candles[8] = c(8, 102, 108, 98, 101)
        for i in (12, 13, 14):
            candles[i] = c(i, 125, 128, 122, 125)
        events = bullish_range_events() + [
            ev(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 7, 120, 30, 120),
            ev(MarketEventKind.SWING_HIGH_CONFIRMED, 9, 130, 31, 130),
            ev(MarketEventKind.SWING_LOW_CONFIRMED, 11, 120, 32, 120),
            ev(MarketEventKind.SWING_HIGH_CONFIRMED, 13, 125, 33, 125),
        ]
        report = analyze_ranges(candles, base_report(candles, events))
        self.assertEqual(len(report.ranges), 2)
        old, new = report.ranges
        self.assertEqual(old.status, RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED)
        self.assertEqual(old.upper_boundary_state, RangeBoundaryState.CONSUMED)
        self.assertEqual(old.lower_boundary_state, RangeBoundaryState.CONSUMED)
        self.assertEqual(new.range_id, 2)
        self.assertEqual((new.lower, new.upper), (120, 130))
        self.assertEqual(new.status, RangeStatus.VALIDATED)
        self.assertEqual(new.upper_boundary_state, RangeBoundaryState.ACTIVE)
        self.assertEqual(new.lower_boundary_state, RangeBoundaryState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
