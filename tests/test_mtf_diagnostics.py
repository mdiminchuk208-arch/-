from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport,
    MarketEvent,
    MarketEventKind,
    OrderBlockReadiness,
    TrendState,
)
from crypto_bot.strategy.mtf_diagnostics import build_candidate_bos_diagnostics, ltf_bos_inventory
from crypto_bot.strategy.mtf_sfp import MtfSfpCandidate, MtfSfpReport, MtfSfpStatus

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def event(kind, minute):
    return MarketEvent(kind, minute, BASE + timedelta(minutes=minute), 100.0, 1, 100.0, "x")


def market_report(*events):
    return MarketAnalysisReport(
        candle_count=0,
        final_trend=TrendState.BROKEN,
        levels=(),
        sweep_episodes=(),
        events=tuple(events),
        order_block_readiness=OrderBlockReadiness(False, "BLOCKED", ()),
        structure_policy="x",
        sfp_timeframe_preference="x",
        sfp_policy="x",
    )


class MtfDiagnosticsTests(unittest.TestCase):
    def test_inventory_counts_both_bos_sides(self):
        r = market_report(
            event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 10),
            event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 20),
            event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 30),
        )
        inv = ltf_bos_inventory(r)
        self.assertEqual(inv.bullish_structure_broken_bos, 1)
        self.assertEqual(inv.bearish_structure_broken_bos, 2)

    def test_later_expected_bos_after_invalidation_is_diagnostic_only(self):
        c = MtfSfpCandidate(
            candidate_id=1, htf_minutes=240, ltf_minutes=15,
            htf_sfp_kind=MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED,
            htf_sfp_event_time=BASE + timedelta(minutes=10), htf_sfp_candle_index=1,
            htf_episode_id=1, htf_level_id=1, htf_level_price=100,
            expected_direction=Direction.LONG,
            expected_ltf_bos_kind=MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
            status=MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS,
            sfp_invalidation_event_time=BASE + timedelta(minutes=20),
        )
        mtf = MtfSfpReport(240, 15, None, (c,), "s", "m", "e", "entry")
        ltf = market_report(event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 30))
        row = build_candidate_bos_diagnostics(mtf, ltf)[0]
        self.assertTrue(row.expected_bos_exists_after_sfp)
        self.assertFalse(row.expected_bos_before_invalidation)
