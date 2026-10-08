import unittest

from crypto_bot.strategy.range_engine import (
    RangeBoundaryClarityReview,
    RangeDetectionParams,
    analyze_ranges,
    range_review_key,
)
from test_range_engine import base_report, bullish_range_events, c


class Phase1418BoundaryClarityTests(unittest.TestCase):
    def _fixture(self):
        candles = [c(i) for i in range(10)]
        base = base_report(candles, bullish_range_events())
        return candles, base

    def test_legacy_manual_audit_review_is_unreviewed(self):
        candles, base = self._fixture()
        report = analyze_ranges(candles, base, params=RangeDetectionParams(automatic_boundary_clarity=False))
        self.assertEqual(len(report.ranges), 1)
        self.assertEqual(
            report.ranges[0].boundary_clarity_review,
            RangeBoundaryClarityReview.UNREVIEWED,
        )

    def test_pass_review_is_attached_by_structural_key(self):
        candles, base = self._fixture()
        initial = analyze_ranges(candles, base)
        key = range_review_key(initial.ranges[0])
        report = analyze_ranges(
            candles,
            base,
            boundary_clarity_reviews={key: RangeBoundaryClarityReview.PASS},
        )
        self.assertEqual(
            report.ranges[0].boundary_clarity_review,
            RangeBoundaryClarityReview.PASS,
        )

    def test_fail_review_is_attached_by_structural_key(self):
        candles, base = self._fixture()
        initial = analyze_ranges(candles, base)
        key = range_review_key(initial.ranges[0])
        report = analyze_ranges(
            candles,
            base,
            boundary_clarity_reviews={key: RangeBoundaryClarityReview.FAIL},
        )
        self.assertEqual(
            report.ranges[0].boundary_clarity_review,
            RangeBoundaryClarityReview.FAIL,
        )

    def test_unreviewed_range_cannot_emit_boundary_sfp(self):
        candles, base = self._fixture()
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        report = analyze_ranges(candles, base, params=RangeDetectionParams(automatic_boundary_clarity=False))
        self.assertEqual(
            report.ranges[0].boundary_clarity_review,
            RangeBoundaryClarityReview.UNREVIEWED,
        )
        self.assertEqual(report.sfp_formation_count, 0)

    def test_failed_clarity_review_cannot_emit_boundary_sfp(self):
        candles, base = self._fixture()
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        initial = analyze_ranges(candles, base)
        key = range_review_key(initial.ranges[0])
        report = analyze_ranges(
            candles,
            base,
            boundary_clarity_reviews={key: RangeBoundaryClarityReview.FAIL},
        )
        self.assertEqual(report.sfp_formation_count, 0)

    def test_passed_clarity_review_can_emit_boundary_sfp(self):
        candles, base = self._fixture()
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        initial = analyze_ranges(candles, base)
        key = range_review_key(initial.ranges[0])
        report = analyze_ranges(
            candles,
            base,
            boundary_clarity_reviews={key: RangeBoundaryClarityReview.PASS},
        )
        self.assertEqual(report.sfp_formation_count, 1)


if __name__ == "__main__":
    unittest.main()
