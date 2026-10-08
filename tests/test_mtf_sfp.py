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
from crypto_bot.strategy.mtf_sfp import (
    MtfSfpError,
    MtfSfpStatus,
    link_sfp_formations_to_ltf_bos,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def event(
    kind: MarketEventKind,
    minute: int,
    *,
    level_id: int = 1,
    price: float = 100.0,
    episode: int | None = 1,
    sfp_extreme: float | None = None,
) -> MarketEvent:
    t = BASE + timedelta(minutes=minute)
    if sfp_extreme is None:
        if kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED:
            sfp_extreme = price + 1.0
        elif kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED:
            sfp_extreme = price - 1.0
    return MarketEvent(
        kind=kind,
        candle_index=minute,
        event_time=t,
        price=price,
        level_id=level_id,
        level_price=price,
        note="test",
        episode_id=episode,
        sfp_pattern_extreme_price=sfp_extreme,
    )


def report(*events: MarketEvent) -> MarketAnalysisReport:
    return MarketAnalysisReport(
        candle_count=1000,
        final_trend=TrendState.UNKNOWN,
        levels=(),
        sweep_episodes=(),
        events=tuple(events),
        order_block_readiness=OrderBlockReadiness(False, "BLOCKED_PENDING_CONTEXT", ("test",)),
        structure_policy="test",
        sfp_timeframe_preference="SOURCE_PREFERRED_H1_PLUS",
        sfp_policy="test",
    )


class MtfSfpTests(unittest.TestCase):
    def test_bearish_sfp_links_to_bullish_structure_break_bos_for_short(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, price=110.0))
        ltf = report(event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, price=105.0, episode=None))
        result = link_sfp_formations_to_ltf_bos(htf, ltf, htf_minutes=60, ltf_minutes=5)
        self.assertEqual(len(result.candidates), 1)
        c = result.candidates[0]
        self.assertEqual(c.expected_direction, Direction.SHORT)
        self.assertEqual(c.status, MtfSfpStatus.LTF_BOS_CONFIRMED)
        self.assertEqual(c.expected_ltf_bos_kind, MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)
        self.assertTrue(c.entry_search_allowed)
        self.assertFalse(c.trade_entry_allowed)
        self.assertEqual(c.elapsed_ltf_bars, 3)

    def test_bullish_sfp_links_to_bearish_structure_break_bos_for_long(self):
        htf = report(event(MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED, 120, price=90.0))
        ltf = report(event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 135, level_id=10, price=95.0, episode=None))
        result = link_sfp_formations_to_ltf_bos(htf, ltf, htf_minutes=240, ltf_minutes=15)
        c = result.candidates[0]
        self.assertEqual(c.expected_direction, Direction.LONG)
        self.assertEqual(c.status, MtfSfpStatus.LTF_BOS_CONFIRMED)
        self.assertTrue(c.entry_search_allowed)
        self.assertFalse(c.trade_entry_allowed)

    def test_bos_at_exact_sfp_confirmation_timestamp_is_not_post_sfp(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report(event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 60, episode=None))
        result = link_sfp_formations_to_ltf_bos(htf, ltf, htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.NO_LTF_BOS_IN_AVAILABLE_DATA)

    def test_bos_before_sfp_is_never_used(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report(event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 55, episode=None))
        result = link_sfp_formations_to_ltf_bos(htf, ltf, htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.NO_LTF_BOS_IN_AVAILABLE_DATA)
        self.assertFalse(result.candidates[0].entry_search_allowed)

    def test_wrong_direction_bos_is_not_used(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report(event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 65, episode=None))
        result = link_sfp_formations_to_ltf_bos(htf, ltf, htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.NO_LTF_BOS_IN_AVAILABLE_DATA)

    def test_positive_wait_window_is_backtest_parameter_and_can_expire(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report(event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 90, episode=None))
        result = link_sfp_formations_to_ltf_bos(
            htf, ltf, htf_minutes=60, ltf_minutes=5, max_wait_ltf_bars=3
        )
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.EXPIRED_BY_BACKTEST_PARAMETER)
        self.assertFalse(result.candidates[0].entry_search_allowed)

    def test_bos_at_deadline_is_allowed(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report(event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, episode=None))
        result = link_sfp_formations_to_ltf_bos(
            htf, ltf, htf_minutes=60, ltf_minutes=5, max_wait_ltf_bars=3
        )
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.LTF_BOS_CONFIRMED)

    def test_ltf_must_be_lower_than_htf(self):
        with self.assertRaises(MtfSfpError):
            link_sfp_formations_to_ltf_bos(report(), report(), htf_minutes=60, ltf_minutes=60)

    def test_wait_window_must_be_positive_when_present(self):
        with self.assertRaises(MtfSfpError):
            link_sfp_formations_to_ltf_bos(report(), report(), htf_minutes=60, ltf_minutes=5, max_wait_ltf_bars=0)

    def test_prefix_causality_no_bos_until_event_exists(self):
        sfp = event(MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED, 60)
        bos = event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 80, episode=None)
        before = link_sfp_formations_to_ltf_bos(report(sfp), report(), htf_minutes=60, ltf_minutes=5)
        after = link_sfp_formations_to_ltf_bos(report(sfp), report(bos), htf_minutes=60, ltf_minutes=5)
        self.assertEqual(before.candidates[0].status, MtfSfpStatus.NO_LTF_BOS_IN_AVAILABLE_DATA)
        self.assertEqual(after.candidates[0].status, MtfSfpStatus.LTF_BOS_CONFIRMED)
        self.assertEqual(after.candidates[0].ltf_bos_event_time, bos.event_time)

    def test_first_matching_bos_is_used_deterministically(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60)
        bos2 = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 80, level_id=2, episode=None)
        bos1 = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 70, level_id=1, episode=None)
        result = link_sfp_formations_to_ltf_bos(report(sfp), report(bos2, bos1), htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.candidates[0].ltf_bos_event_time, bos1.event_time)

    def test_positive_wait_is_right_censored_when_ltf_history_ends_before_deadline(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report()
        result = link_sfp_formations_to_ltf_bos(
            htf,
            ltf,
            htf_minutes=60,
            ltf_minutes=5,
            max_wait_ltf_bars=6,
            ltf_observation_start=BASE,
            ltf_observation_end=BASE + timedelta(minutes=80),
        )
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.RIGHT_CENSORED_BEFORE_DEADLINE)

    def test_candidate_outside_ltf_coverage_is_not_linked(self):
        htf = report(event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60))
        ltf = report(event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 90, episode=None))
        result = link_sfp_formations_to_ltf_bos(
            htf,
            ltf,
            htf_minutes=60,
            ltf_minutes=5,
            ltf_observation_start=BASE + timedelta(minutes=70),
            ltf_observation_end=BASE + timedelta(minutes=120),
        )
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.LTF_COVERAGE_MISSING_AT_SFP)
        self.assertFalse(result.candidates[0].entry_search_allowed)

    def test_candidate_not_before_keeps_earlier_history_as_warmup_only(self):
        early = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 30, level_id=1)
        in_window = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, level_id=2)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(
            report(early, in_window),
            report(bos),
            htf_minutes=60,
            ltf_minutes=5,
            candidate_not_before=BASE + timedelta(minutes=45),
        )
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].htf_level_id, 2)

    def test_shared_ltf_bos_links_are_reported_not_hidden(self):
        sfp1 = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, level_id=1)
        sfp2 = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 65, level_id=2)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(
            report(sfp1, sfp2), report(bos), htf_minutes=60, ltf_minutes=5
        )
        self.assertEqual(result.confirmed_count, 2)
        self.assertEqual(result.unique_ltf_bos_count, 1)
        self.assertEqual(result.shared_bos_link_count, 1)

    def test_observation_bounds_must_be_paired(self):
        with self.assertRaises(MtfSfpError):
            link_sfp_formations_to_ltf_bos(
                report(),
                report(),
                htf_minutes=60,
                ltf_minutes=5,
                ltf_observation_start=BASE,
            )

    def test_source_close_invalidation_blocks_bearish_sfp_before_bos(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, price=100.0, episode=7, sfp_extreme=105.0)
        invalid = event(
            MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE, 70, price=106.0, episode=7, sfp_extreme=105.0
        )
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(report(sfp, invalid), report(bos), htf_minutes=60, ltf_minutes=5)
        c = result.candidates[0]
        self.assertEqual(c.status, MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS)
        self.assertFalse(c.entry_search_allowed)
        self.assertEqual(c.sfp_invalidation_event_time, invalid.event_time)
        self.assertEqual(result.opportunity_count, 0)

    def test_source_close_invalidation_blocks_bullish_sfp_before_bos(self):
        sfp = event(MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED, 60, price=100.0, episode=8, sfp_extreme=95.0)
        invalid = event(
            MarketEventKind.BULLISH_SFP_INVALIDATED_CLOSE, 70, price=94.0, episode=8, sfp_extreme=95.0
        )
        bos = event(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(report(sfp, invalid), report(bos), htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS)

    def test_bos_before_later_invalidation_still_unlocks_entry_search(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, episode=7, sfp_extreme=105.0)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 70, level_id=9, episode=None)
        invalid = event(MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE, 80, price=106.0, episode=7, sfp_extreme=105.0)
        result = link_sfp_formations_to_ltf_bos(report(sfp, invalid), report(bos), htf_minutes=60, ltf_minutes=5)
        c = result.candidates[0]
        self.assertEqual(c.status, MtfSfpStatus.LTF_BOS_CONFIRMED)
        self.assertTrue(c.entry_search_allowed)
        self.assertEqual(c.sfp_invalidation_event_time, invalid.event_time)
        self.assertEqual(result.opportunity_count, 1)

    def test_invalidation_wins_when_same_timestamp_as_bos(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, episode=7, sfp_extreme=105.0)
        invalid = event(MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE, 75, price=106.0, episode=7, sfp_extreme=105.0)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(report(sfp, invalid), report(bos), htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS)

    def test_expiry_before_later_invalidation_remains_expiry(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, episode=7, sfp_extreme=105.0)
        invalid = event(MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE, 90, price=106.0, episode=7, sfp_extreme=105.0)
        result = link_sfp_formations_to_ltf_bos(
            report(sfp, invalid), report(), htf_minutes=60, ltf_minutes=5, max_wait_ltf_bars=3
        )
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.EXPIRED_BY_BACKTEST_PARAMETER)

    def test_shared_bos_contexts_cluster_into_one_opportunity(self):
        sfp1 = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, level_id=1, episode=1)
        sfp2 = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 65, level_id=2, episode=2)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 75, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(report(sfp1, sfp2), report(bos), htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.confirmed_count, 2)
        self.assertEqual(result.opportunity_count, 1)
        self.assertEqual(result.opportunities[0].context_count, 2)
        self.assertEqual(result.opportunities[0].candidate_ids, (1, 2))
        self.assertEqual(result.opportunities[0].representative_candidate_id, 2)
        self.assertTrue(all(c.opportunity_id == 1 for c in result.candidates))

    def test_distinct_bos_events_create_distinct_opportunities(self):
        sfp1 = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, level_id=1, episode=1)
        sfp2 = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 80, level_id=2, episode=2)
        bos1 = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 70, level_id=9, episode=None)
        bos2 = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 90, level_id=10, episode=None)
        result = link_sfp_formations_to_ltf_bos(report(sfp1, sfp2), report(bos1, bos2), htf_minutes=60, ltf_minutes=5)
        self.assertEqual(result.opportunity_count, 2)
        self.assertEqual(tuple(c.opportunity_id for c in result.candidates), (1, 2))

    def test_missing_sfp_extreme_is_rejected_in_phase_142(self):
        sfp = MarketEvent(
            kind=MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
            candle_index=60,
            event_time=BASE + timedelta(minutes=60),
            price=100.0,
            level_id=1,
            level_price=100.0,
            note="missing extreme",
            episode_id=1,
        )
        with self.assertRaises(MtfSfpError):
            link_sfp_formations_to_ltf_bos(report(sfp), report(), htf_minutes=60, ltf_minutes=5)


if __name__ == "__main__":
    unittest.main()

class MtfWaitMinutesTests(unittest.TestCase):
    def test_real_time_wait_minutes_confirms_at_deadline(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, episode=7, sfp_extreme=105.0)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 120, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(
            report(sfp), report(bos), htf_minutes=240, ltf_minutes=15, max_wait_minutes=60
        )
        c = result.candidates[0]
        self.assertEqual(c.status, MtfSfpStatus.LTF_BOS_CONFIRMED)
        self.assertEqual(c.elapsed_minutes, 60)
        self.assertEqual(result.max_wait_minutes, 60)

    def test_real_time_wait_minutes_can_expire(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, episode=7, sfp_extreme=105.0)
        bos = event(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, 121, level_id=9, episode=None)
        result = link_sfp_formations_to_ltf_bos(
            report(sfp), report(bos), htf_minutes=240, ltf_minutes=15, max_wait_minutes=60
        )
        self.assertEqual(result.candidates[0].status, MtfSfpStatus.EXPIRED_BY_BACKTEST_PARAMETER)

    def test_bars_and_minutes_are_mutually_exclusive(self):
        sfp = event(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED, 60, episode=7, sfp_extreme=105.0)
        with self.assertRaises(MtfSfpError):
            link_sfp_formations_to_ltf_bos(
                report(sfp), report(), htf_minutes=60, ltf_minutes=5,
                max_wait_ltf_bars=12, max_wait_minutes=60,
            )
