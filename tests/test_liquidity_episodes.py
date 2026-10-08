from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import (
    LiquidityState,
    MarketEventKind,
    SweepEpisodeStatus,
    analyze_market,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def c(i: int, o: float, h: float, l: float, cl: float) -> Candle:
    return Candle(
        open_time=BASE + timedelta(minutes=i),
        close_time=BASE + timedelta(minutes=i + 1),
        open=o,
        high=h,
        low=l,
        close=cl,
        is_closed=True,
    )


def two_highs_one_sweep(*, include_next: bool = True) -> list[Candle]:
    candles = [
        c(0, 10.0, 11.0, 9.0, 10.4),
        c(1, 10.4, 13.0, 10.0, 12.0),  # swing high #1 = 13.0
        c(2, 12.0, 12.0, 10.5, 11.0), # confirms #1
        c(3, 11.0, 12.5, 10.3, 11.8),
        c(4, 11.8, 12.8, 10.8, 12.2), # swing high #2 = 12.8
        c(5, 12.2, 12.4, 10.9, 11.5), # confirms #2
        c(6, 11.5, 13.5, 10.5, 12.6), # first sweep takes both highs; closes below both
    ]
    if include_next:
        candles.append(c(7, 12.5, 12.7, 11.0, 11.8)) # opens below both -> SFP formation
    return candles


class LiquidityEpisodeTests(unittest.TestCase):
    def test_same_candle_same_side_levels_are_one_sweep_episode_and_one_sfp(self):
        report = analyze_market(two_highs_one_sweep(), timeframe_minutes=1)

        raw_takes = report.events_of(MarketEventKind.HIGH_LIQUIDITY_TAKEN)
        episodes = report.events_of(MarketEventKind.HIGH_LIQUIDITY_SWEEP_EPISODE)
        sfps = report.events_of(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED)

        self.assertEqual(len(raw_takes), 2)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(len(report.sweep_episodes), 1)
        self.assertEqual(len(sfps), 1)

        episode = report.sweep_episodes[0]
        self.assertEqual(episode.status, SweepEpisodeStatus.SFP_FORMED)
        self.assertEqual(len(episode.member_level_ids), 2)
        self.assertEqual(episode.representative_level_price, 13.0)
        self.assertEqual(sfps[0].episode_id, episode.episode_id)
        self.assertEqual(sfps[0].level_price, 13.0)

    def test_swept_levels_become_consumed_after_next_candle_resolves_episode(self):
        report = analyze_market(two_highs_one_sweep(), timeframe_minutes=1)
        swept_members = set(report.sweep_episodes[0].member_level_ids)
        members = [level for level in report.levels if level.level_id in swept_members]
        self.assertEqual(len(members), 2)
        self.assertTrue(all(level.liquidity_state == LiquidityState.CONSUMED for level in members))
        self.assertTrue(all(level.liquidity_resolved_index == 7 for level in members))

    def test_last_candle_sweep_stays_pending_without_future_candle(self):
        report = analyze_market(two_highs_one_sweep(include_next=False), timeframe_minutes=1)
        self.assertEqual(len(report.sweep_episodes), 1)
        episode = report.sweep_episodes[0]
        self.assertEqual(episode.status, SweepEpisodeStatus.PENDING_NEXT_CANDLE)
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED)), 0)
        swept_members = set(episode.member_level_ids)
        members = [level for level in report.levels if level.level_id in swept_members]
        self.assertTrue(all(level.liquidity_state == LiquidityState.SWEPT for level in members))

    def test_m1_sfp_is_source_valid_but_below_preferred_search_timeframe(self):
        report = analyze_market(two_highs_one_sweep(), timeframe_minutes=1)
        self.assertEqual(report.sfp_timeframe_preference, "SOURCE_VALID_BELOW_PREFERRED_H1")

    def test_h1_sfp_is_in_source_preferred_search_timeframe(self):
        report = analyze_market(two_highs_one_sweep(), timeframe_minutes=60)
        self.assertEqual(report.sfp_timeframe_preference, "SOURCE_PREFERRED_H1_PLUS")


if __name__ == "__main__":
    unittest.main()

class DualSideLiquidityEpisodeTests(unittest.TestCase):
    def test_dual_side_first_sweep_is_ambiguous_and_emits_no_sfp(self):
        candles = [
            c(0, 10.0, 11.0, 9.0, 10.5),
            c(1, 10.5, 13.0, 10.0, 12.0),  # confirmed swing high 13
            c(2, 12.0, 12.0, 9.5, 10.5),
            c(3, 10.5, 11.0, 8.0, 9.0),    # swing low 8
            c(4, 9.0, 12.0, 9.0, 11.0),    # confirms swing low
            c(5, 11.0, 14.0, 7.0, 10.5),   # first-sweeps both sides
            c(6, 10.5, 11.5, 9.0, 10.0),
        ]
        report = analyze_market(candles, timeframe_minutes=60)
        self.assertEqual(len(report.sweep_episodes), 2)
        self.assertTrue(
            all(ep.status == SweepEpisodeStatus.AMBIGUOUS_DUAL_SIDE_SWEEP for ep in report.sweep_episodes)
        )
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED)), 0)
        self.assertEqual(len(report.events_of(MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED)), 0)
        self.assertIn("RANGE_BOUNDARY_PENDING", report.sfp_liquidity_scope)
