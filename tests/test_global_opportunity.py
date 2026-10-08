from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.strategy.global_opportunity import GlobalOpportunity, GlobalOpportunityError, cluster_cross_pair_opportunities
from crypto_bot.strategy.market_analysis import MarketEventKind
from crypto_bot.strategy.mtf_sfp import MtfOpportunity, MtfOpportunityStatus, MtfSfpReport

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def report(htf, ltf, direction, minute, opp_id=1):
    bos_kind = (
        MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS
        if direction == Direction.LONG
        else MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS
    )
    opp = MtfOpportunity(
        opportunity_id=opp_id,
        status=MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE,
        expected_direction=direction,
        ltf_bos_kind=bos_kind,
        ltf_bos_event_time=BASE + timedelta(minutes=minute),
        ltf_bos_candle_index=10,
        ltf_bos_level_id=2,
        ltf_bos_level_price=100.0,
        candidate_ids=(1,),
        htf_episode_ids=(1,),
        htf_level_ids=(1,),
        earliest_sfp_time=BASE,
        latest_sfp_time=BASE,
        representative_candidate_id=1,
    )
    return MtfSfpReport(htf, ltf, None, (), "s", "m", "e", "entry", opportunities=(opp,))


class GlobalOpportunityTests(unittest.TestCase):
    def test_v0411_positional_global_opportunity_values_are_preserved(self):
        legacy = GlobalOpportunity(
            1, "BTCUSDT", Direction.LONG, BASE, BASE, BASE,
            ("pair",), ("pair#1",), 1, 1, 0, False, "legacy note",
        )
        self.assertFalse(legacy.entry_search_allowed)
        self.assertFalse(legacy.trade_entry_allowed)
        self.assertEqual(legacy.note, "legacy note")
        self.assertEqual(legacy.recovery_context_refs, ())
        self.assertEqual(legacy.analysis_mode.value, "SOURCE_CONSERVATIVE")

    def test_exact_timestamp_merges_cross_pair_same_direction(self):
        a = report(60, 5, Direction.LONG, 100)
        b = report(240, 15, Direction.LONG, 100)
        result = cluster_cross_pair_opportunities("BTCUSDT", [("60_to_5", a), ("240_to_15", b)])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].local_opportunity_count, 2)
        self.assertEqual(set(result[0].pair_labels), {"60_to_5", "240_to_15"})

    def test_near_time_only_merges_with_positive_backtest_window(self):
        a = report(60, 5, Direction.LONG, 100)
        b = report(240, 15, Direction.LONG, 110)
        exact = cluster_cross_pair_opportunities("BTCUSDT", [("a", a), ("b", b)], cluster_window_minutes=0)
        wide = cluster_cross_pair_opportunities("BTCUSDT", [("a", a), ("b", b)], cluster_window_minutes=15)
        self.assertEqual(len(exact), 2)
        self.assertEqual(len(wide), 1)

    def test_opposite_directions_never_merge(self):
        a = report(60, 5, Direction.LONG, 100)
        b = report(240, 15, Direction.SHORT, 100)
        result = cluster_cross_pair_opportunities("BTCUSDT", [("a", a), ("b", b)], cluster_window_minutes=60)
        self.assertEqual(len(result), 2)


    def test_same_pair_distinct_opportunities_are_never_collapsed(self):
        # One report can contain two local opportunities. A global time window must not
        # merge them merely because they are close; global de-dup is cross-pair only.
        a1 = report(60, 5, Direction.LONG, 100, opp_id=1)
        # Rebuild with two opportunities in the same report.
        o1 = a1.opportunities[0]
        a2single = report(60, 5, Direction.LONG, 105, opp_id=2)
        combined = MtfSfpReport(60, 5, None, (), "s", "m", "e", "entry", opportunities=(o1, a2single.opportunities[0]))
        result = cluster_cross_pair_opportunities("BTCUSDT", [("60_to_5", combined)], cluster_window_minutes=60)
        self.assertEqual(len(result), 2)

    def test_duplicate_pair_label_is_rejected(self):
        a = report(60, 5, Direction.LONG, 100)
        with self.assertRaises(GlobalOpportunityError):
            cluster_cross_pair_opportunities("BTCUSDT", [("a", a), ("a", a)])

    def test_mixed_analysis_modes_are_rejected(self):
        from crypto_bot.strategy.market_analysis import StructureAnalysisMode
        a = MtfSfpReport(
            60, 5, None, (), "s", "m", "e", "entry",
            opportunities=report(60, 5, Direction.LONG, 100).opportunities,
            analysis_mode=StructureAnalysisMode.TECHNICAL_RECOVERY,
        )
        b = MtfSfpReport(
            240, 15, None, (), "s", "m", "e", "entry",
            opportunities=report(240, 15, Direction.LONG, 100).opportunities,
            analysis_mode=StructureAnalysisMode.SOURCE_CONSERVATIVE,
        )
        with self.assertRaises(GlobalOpportunityError):
            cluster_cross_pair_opportunities("BTCUSDT", [("a", a), ("b", b)])

    def test_local_entry_gate_propagates_to_global_opportunity(self):
        a = report(60, 5, Direction.LONG, 100)
        gated = replace(a.opportunities[0], entry_search_allowed=False)
        a = MtfSfpReport(60, 5, None, (), "s", "m", "e", "entry", opportunities=(gated,))
        result = cluster_cross_pair_opportunities("BTCUSDT", [("a", a)])
        self.assertFalse(result[0].entry_search_allowed)

    def test_global_opportunity_preserves_report_analysis_mode(self):
        from crypto_bot.strategy.market_analysis import StructureAnalysisMode
        a = MtfSfpReport(
            60, 5, None, (), "s", "m", "e", "entry",
            opportunities=report(60, 5, Direction.LONG, 100).opportunities,
            analysis_mode=StructureAnalysisMode.SOURCE_CONSERVATIVE,
        )
        result = cluster_cross_pair_opportunities("BTCUSDT", [("a", a)])
        self.assertEqual(result[0].analysis_mode, StructureAnalysisMode.SOURCE_CONSERVATIVE)
