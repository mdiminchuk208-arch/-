import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport,
    MarketEvent,
    MarketEventKind,
    OrderBlockReadiness,
    TrendState,
)
from crypto_bot.strategy.mtf_sfp import (
    MtfOpportunity,
    MtfOpportunityStatus,
    MtfSfpCandidate,
    MtfSfpReport,
    MtfSfpStatus,
    link_sfp_formations_to_ltf_bos,
)
from crypto_bot.strategy.range_engine import RangeDetectionParams
from range_test_support import analyze_ranges, augment_market_report_with_range_sfps
from crypto_bot.strategy.range_validation import (
    build_origin_mtf_funnel,
    build_range_audit_rows,
    build_range_stage_funnel,
    build_range_validation_matrix_row,
    unique_sorted_tolerances,
)

BASE = datetime(2026, 3, 1, tzinfo=timezone.utc)


def candle(i, o=105, h=108, l=102, cl=105):
    start = BASE + timedelta(hours=i)
    return Candle(start, start + timedelta(hours=1), o, h, l, cl, True)


def event(kind, i, price, lid):
    return MarketEvent(kind, i, BASE + timedelta(hours=i + 1), price, lid, price, "fixture")


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


def range_fixture():
    candles = [candle(i) for i in range(10)]
    candles[7] = candle(7, 106, 112, 104, 109)
    candles[8] = candle(8, 108, 109, 103, 106)
    events = [
        event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 0, 103, 1),
        event(MarketEventKind.SWING_HIGH_CONFIRMED, 2, 110, 2),
        event(MarketEventKind.SWING_LOW_CONFIRMED, 4, 100, 3),
        event(MarketEventKind.SWING_HIGH_CONFIRMED, 6, 105.5, 4),
    ]
    report = analyze_ranges(
        candles,
        base_report(candles, events),
        params=RangeDetectionParams(midpoint_tolerance_fraction=0.08),
    )
    return candles, base_report(candles, events), report


class RangeValidationTests(unittest.TestCase):
    def test_tolerance_grid_is_sorted_deduplicated_and_guarded(self):
        self.assertEqual(unique_sorted_tolerances([0.10, 0.04, 0.10, 0.08]), (0.04, 0.08, 0.10))
        with self.assertRaises(ValueError):
            unique_sorted_tolerances([0.08, 0.51])
        with self.assertRaises(ValueError):
            unique_sorted_tolerances([])

    def test_stage_funnel_uses_unique_range_counts_not_fake_trade_counts(self):
        _, _, report = range_fixture()
        funnel = build_range_stage_funnel(report)
        self.assertEqual(funnel.range_candidate_count, 1)
        self.assertEqual(funnel.ever_validated_range_count, 1)
        self.assertEqual(funnel.ranges_with_boundary_sweep, 1)
        self.assertEqual(funnel.boundary_sweep_episode_count, 1)
        self.assertEqual(funnel.ranges_with_sfp, 1)
        self.assertEqual(funnel.range_sfp_formation_count, 1)

    def test_range_audit_exposes_midpoint_distance_and_manual_clarity_gate(self):
        _, _, report = range_fixture()
        rows = build_range_audit_rows(
            report,
            evaluation_start=BASE,
            htf_minutes=60,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertAlmostEqual(row.midpoint_distance_fraction, 0.05)
        self.assertTrue(row.evaluation_context)
        self.assertEqual(row.manual_boundary_clarity_review, "PASS")
        self.assertTrue(row.boundary_clarity_review_key)
        self.assertLess(row.audit_window_start, row.impulse_bos_time)
        self.assertGreater(row.audit_window_end, row.status_time)

    def test_origin_funnel_counts_contexts_and_origin_opportunities(self):
        c1 = MtfSfpCandidate(
            candidate_id=1, htf_minutes=60, ltf_minutes=5,
            htf_sfp_kind=MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
            htf_sfp_event_time=BASE, htf_sfp_candle_index=0, htf_episode_id=1,
            htf_level_id=1, htf_level_price=110, expected_direction=Direction.SHORT,
            expected_ltf_bos_kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            status=MtfSfpStatus.LTF_BOS_CONFIRMED, htf_liquidity_origin="RANGE_BOUNDARY",
            ltf_bos_event_time=BASE + timedelta(minutes=30), ltf_bos_candle_index=6,
            ltf_bos_level_id=5, ltf_bos_level_price=108, opportunity_id=1,
        )
        c2 = MtfSfpCandidate(
            candidate_id=2, htf_minutes=60, ltf_minutes=5,
            htf_sfp_kind=MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED,
            htf_sfp_event_time=BASE, htf_sfp_candle_index=0, htf_episode_id=2,
            htf_level_id=2, htf_level_price=100, expected_direction=Direction.LONG,
            expected_ltf_bos_kind=MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
            status=MtfSfpStatus.EXPIRED_BY_BACKTEST_PARAMETER, htf_liquidity_origin="RANGE_BOUNDARY",
        )
        opp = MtfOpportunity(
            opportunity_id=1, status=MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE,
            expected_direction=Direction.SHORT,
            ltf_bos_kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            ltf_bos_event_time=BASE + timedelta(minutes=30), ltf_bos_candle_index=6,
            ltf_bos_level_id=5, ltf_bos_level_price=108,
            candidate_ids=(1,), htf_episode_ids=(1,), htf_level_ids=(1,),
            earliest_sfp_time=BASE, latest_sfp_time=BASE, representative_candidate_id=1,
        )
        report = MtfSfpReport(
            htf_minutes=60, ltf_minutes=5, max_wait_ltf_bars=None,
            candidates=(c1, c2), source_policy="fixture", mapping_policy="fixture",
            expiry_policy="fixture", entry_policy="fixture", opportunities=(opp,),
        )
        funnel = build_origin_mtf_funnel(report, "RANGE_BOUNDARY")
        self.assertEqual(funnel.sfp_context_count, 2)
        self.assertEqual(funnel.bos_confirmed_contexts, 1)
        self.assertEqual(funnel.expired, 1)
        self.assertEqual(funnel.opportunities_with_origin_context, 1)

    def test_matrix_row_keeps_range_stage_and_mtf_outcome_separate(self):
        candles, base, range_report = range_fixture()
        htf, _ = augment_market_report_with_range_sfps(
            candles, base, params=RangeDetectionParams(midpoint_tolerance_fraction=0.08)
        )
        bos = MarketEvent(
            kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            candle_index=9,
            event_time=BASE + timedelta(hours=9, minutes=30),
            price=107,
            level_id=90,
            level_price=106,
            note="ltf bos",
        )
        ltf = base_report(candles, [bos])
        mtf = link_sfp_formations_to_ltf_bos(
            htf, ltf, htf_minutes=60, ltf_minutes=5,
            ltf_observation_start=BASE, ltf_observation_end=BASE + timedelta(hours=10),
        )
        row = build_range_validation_matrix_row(
            midpoint_tolerance_fraction=0.08,
            wait_mode="minutes",
            wait_value=120,
            effective_wait_minutes=120,
            range_report=range_report,
            mtf_report=mtf,
        )
        self.assertEqual(row.range_candidate_count_loaded, 1)
        self.assertEqual(row.range_sfp_formation_count_loaded, 1)
        self.assertEqual(row.range_sfp_context_count_evaluation, 1)
        self.assertEqual(row.range_bos_confirmed_contexts, 1)

    def test_entry_blockers_expose_remaining_range_validation_gaps(self):
        candles, base, _ = range_fixture()
        htf, _ = augment_market_report_with_range_sfps(candles, base)
        bos = MarketEvent(
            kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            candle_index=9, event_time=BASE + timedelta(hours=9, minutes=30),
            price=107, level_id=99, level_price=106, note="ltf"
        )
        mtf = link_sfp_formations_to_ltf_bos(
            htf, base_report(candles, [bos]), htf_minutes=60, ltf_minutes=5,
            ltf_observation_start=BASE, ltf_observation_end=BASE + timedelta(hours=10),
        )
        self.assertNotIn("STRUCTURE_LIFECYCLE_REAL_DATA_NOT_REVALIDATED", mtf.entry_engine_blocking_reasons)
        self.assertNotIn("STRUCTURE_RECOVERY_ABLATION_NOT_VALIDATED", mtf.entry_engine_blocking_reasons)
        self.assertNotIn("RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED", mtf.entry_engine_blocking_reasons)
        self.assertNotIn("RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED", mtf.entry_engine_blocking_reasons)
        self.assertNotIn("RANGE_RETIREMENT_REDRAW_LIFECYCLE_NOT_FORMALIZED", mtf.entry_engine_blocking_reasons)
        self.assertIn("SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED", mtf.entry_engine_blocking_reasons)
        self.assertNotIn("CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED", mtf.entry_engine_blocking_reasons)
        self.assertIn("SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED", mtf.entry_engine_blocking_reasons)


if __name__ == "__main__":
    unittest.main()
