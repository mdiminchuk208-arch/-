"""Automatic clarity uses available source confirmations, never future labels."""
from dataclasses import replace
import unittest

from crypto_bot.strategy.range_engine import (RangeBoundaryClarityReview, RangeDetectionParams,
    RangeStatus, analyze_ranges, automatic_boundary_clarity, range_review_key)
from crypto_bot.strategy.market_analysis import MarketEventKind
from test_range_engine import base_report, bullish_range_events, c, ev


class RangeAutomaticClarityTests(unittest.TestCase):
    def fixture(self):
        candles=[c(i) for i in range(12)]
        candles[7]=c(7,106,112,104,109)
        candles[8]=c(8,108,109,103,106)
        return candles,bullish_range_events()

    def test_valid_source_area_automatically_emits_real_pattern(self):
        candles,events=self.fixture()
        report=analyze_ranges(candles,base_report(candles,events))
        self.assertEqual(report.ranges[0].boundary_clarity_review,RangeBoundaryClarityReview.AUTO_PASS)
        self.assertEqual(report.ranges[0].boundary_clarity_known_at,events[-1].event_time)
        self.assertEqual(report.sfp_formation_count,1)
        self.assertEqual(report.sweep_episodes[0].status,'SFP_FORMED')

    def test_midpoint_not_yet_known_cannot_pass(self):
        candles,events=self.fixture()
        report=analyze_ranges(candles[:6],base_report(candles[:6],events[:-1]))
        self.assertEqual(report.ranges[0].boundary_clarity_review,RangeBoundaryClarityReview.AUTO_PENDING)
        self.assertEqual(report.sfp_formation_count,0)

    def test_internal_structure_remains_rejected(self):
        candles,events=self.fixture()
        events=events+[ev(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,5,104,99,103)]
        report=analyze_ranges(candles,base_report(candles,events))
        self.assertEqual(report.ranges[0].status,RangeStatus.REJECTED_INTERNAL_STRUCTURE)
        self.assertEqual(report.ranges[0].boundary_clarity_review,RangeBoundaryClarityReview.AUTO_FAIL)
        self.assertEqual(report.sfp_formation_count,0)

    def test_manual_fail_and_explicit_unreviewed_still_block(self):
        candles,events=self.fixture()
        base=base_report(candles,events)
        key=range_review_key(analyze_ranges(candles,base).ranges[0])
        for value in (RangeBoundaryClarityReview.FAIL,RangeBoundaryClarityReview.UNREVIEWED):
            with self.subTest(value=value):
                result=analyze_ranges(candles,base,boundary_clarity_reviews={key:value})
                self.assertEqual(result.sfp_formation_count,0)

    def test_later_internal_bos_cannot_revoke_prior_clarity_or_sfp(self):
        candles,events=self.fixture()
        events=events+[ev(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,10,104,99,103)]
        full=analyze_ranges(candles,base_report(candles,events))
        early=analyze_ranges(candles[:10],base_report(candles[:10],events[:-1]))
        self.assertEqual(full.ranges[0].status,RangeStatus.INVALIDATED_INTERNAL_STRUCTURE)
        self.assertEqual(full.ranges[0].boundary_clarity_known_at,early.ranges[0].boundary_clarity_known_at)
        self.assertEqual(full.ranges[0].boundary_clarity_review,early.ranges[0].boundary_clarity_review)
        self.assertEqual(full.events,early.events)
        self.assertEqual(automatic_boundary_clarity(full.ranges[0])[0],RangeBoundaryClarityReview.AUTO_PASS)

    def test_future_price_mutation_keeps_earlier_formation(self):
        candles,events=self.fixture()
        early=analyze_ranges(candles[:10],base_report(candles[:10],events))
        future=candles[:10]+[replace(c,open=500,high=600,low=400,close=550) for c in candles[10:]]
        full=analyze_ranges(future,base_report(future,events))
        self.assertEqual(tuple(e for e in full.events if e.event_time<=candles[9].close_time),early.events)

    def test_disabling_clean_structure_does_not_auto_certify_dirty_range(self):
        candles,events=self.fixture()
        events=events+[ev(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,5,104,99,103)]
        report=analyze_ranges(candles,base_report(candles,events),params=RangeDetectionParams(require_clean_internal_structure=False))
        self.assertEqual(report.ranges[0].boundary_clarity_review,RangeBoundaryClarityReview.AUTO_FAIL)
        self.assertEqual(report.sfp_formation_count,0)


if __name__=='__main__':
    unittest.main()
