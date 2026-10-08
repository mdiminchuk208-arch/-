from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisError,
    MarketEventKind,
    TrendState,
    StructureAnalysisMode,
    analyze_market,
)


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def c(i: int, o: float, h: float, l: float, cl: float, *, closed: bool = True) -> Candle:
    return Candle(
        open_time=BASE + timedelta(minutes=i),
        close_time=BASE + timedelta(minutes=i + 1),
        open=o,
        high=h,
        low=l,
        close=cl,
        is_closed=closed,
    )


def bullish_structure_sequence(*, bos_close: float = 8.8) -> list[Candle]:
    # Swing lows: 8 -> 9 (HL), swing highs: 12 -> 13 (HH).
    # The second HH confirms bullish structure and protects the 9 HL.
    return [
        c(0, 10.0, 11.0, 9.5, 10.2),
        c(1, 10.2, 10.5, 8.0, 9.0),       # first swing low
        c(2, 9.0, 11.0, 8.5, 10.4),       # confirms first swing low
        c(3, 10.4, 12.0, 9.0, 11.3),      # first swing high
        c(4, 11.3, 11.5, 9.5, 10.2),      # confirms first swing high
        c(5, 10.2, 11.0, 9.0, 9.6),       # HL
        c(6, 9.6, 12.0, 9.3, 11.2),       # confirms HL
        c(7, 11.2, 13.0, 10.0, 12.6),     # HH
        c(8, 12.6, 12.7, 10.5, 11.6),     # confirms HH -> bullish structure, protected HL=9
        c(9, 11.6, 11.9, 8.5, bos_close), # wick below protected HL; body may/may not break
    ]


def bearish_structure_sequence(*, bos_close: float = 13.2) -> list[Candle]:
    # Swing highs: 14 -> 13 (LH), swing lows: 10 -> 9 (LL).
    # The second LL confirms bearish structure and protects the 13 LH.
    return [
        c(0, 12.0, 13.5, 11.0, 12.3),
        c(1, 12.3, 14.0, 11.5, 13.2),      # first swing high
        c(2, 13.2, 13.5, 10.8, 11.6),      # confirms first swing high
        c(3, 11.6, 12.6, 10.0, 10.5),      # first swing low
        c(4, 10.5, 12.0, 10.4, 11.5),      # confirms first swing low
        c(5, 11.5, 13.0, 10.6, 12.5),      # LH
        c(6, 12.5, 12.7, 9.8, 10.4),       # confirms LH
        c(7, 10.4, 11.5, 9.0, 9.4),        # LL
        c(8, 9.4, 12.0, 9.2, 11.2),        # confirms LL -> bearish structure, protected LH=13
        c(9, 11.2, 13.5, 10.8, bos_close), # wick above protected LH; body may/may not break
    ]


class MarketAnalysisTests(unittest.TestCase):
    def test_bullish_structure_uses_hh_hl_and_bos_breaks_protected_hl(self):
        report = analyze_market(bullish_structure_sequence())
        bullish = report.events_of(MarketEventKind.BULLISH_STRUCTURE_CONFIRMED)
        bos = report.events_of(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)
        self.assertTrue(bullish)
        self.assertEqual(bullish[-1].level_price, 9.0)
        self.assertEqual(len(bos), 1)
        self.assertEqual(bos[0].level_price, 9.0)
        self.assertEqual(report.final_trend, TrendState.BROKEN)

    def test_wick_below_bullish_key_hl_is_not_bos_without_body_close(self):
        report = analyze_market(bullish_structure_sequence(bos_close=9.2))
        self.assertEqual(len(report.events_of(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)), 0)
        self.assertEqual(report.final_trend, TrendState.BULLISH)
        self.assertTrue(report.events_of(MarketEventKind.LOW_LIQUIDITY_TAKEN))

    def test_bearish_structure_uses_ll_lh_and_bos_breaks_protected_lh(self):
        report = analyze_market(bearish_structure_sequence())
        bearish = report.events_of(MarketEventKind.BEARISH_STRUCTURE_CONFIRMED)
        bos = report.events_of(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS)
        self.assertTrue(bearish)
        self.assertEqual(bearish[-1].level_price, 13.0)
        self.assertEqual(len(bos), 1)
        self.assertEqual(bos[0].level_price, 13.0)
        self.assertEqual(report.final_trend, TrendState.BROKEN)

    def test_wick_above_bearish_key_lh_is_not_bos_without_body_close(self):
        report = analyze_market(bearish_structure_sequence(bos_close=12.8))
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS)), 0)
        self.assertEqual(report.final_trend, TrendState.BEARISH)
        self.assertTrue(report.events_of(MarketEventKind.HIGH_LIQUIDITY_TAKEN))

    def test_structural_liquidity_is_only_taken_after_level_is_confirmed(self):
        candles = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),  # center high
            c(2, 12, 12.5, 10, 11), # confirms swing high at 13
            c(3, 11, 13.2, 10.5, 12.8),
        ]
        report = analyze_market(candles)
        swing = report.events_of(MarketEventKind.SWING_HIGH_CONFIRMED)
        takes = report.events_of(MarketEventKind.HIGH_LIQUIDITY_TAKEN)
        self.assertEqual(len(swing), 1)
        self.assertEqual(swing[0].candle_index, 2)
        self.assertEqual(len(takes), 1)
        self.assertEqual(takes[0].candle_index, 3)

    def test_sfp_is_confirmed_only_on_following_candle(self):
        candles = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),
            c(2, 12, 12.5, 10, 11), # level 13 confirmed
            c(3, 11, 13.5, 10.5, 12.8), # sweeps and closes back below 13
            c(4, 12.7, 12.9, 11.5, 12.0), # opens back below 13 -> SFP confirmed
        ]
        report = analyze_market(candles)
        sfp = report.events_of(MarketEventKind.BEARISH_SFP_CONFIRMED)
        self.assertEqual(len(sfp), 1)
        self.assertEqual(sfp[0].candle_index, 4)

    def test_sfp_confirmation_time_uses_next_open_without_next_hlc_dependency(self):
        prefix = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),
            c(2, 12, 12.5, 10, 11),
            c(3, 11, 13.5, 10.5, 12.8),
        ]
        next_a = c(4, 12.7, 12.9, 11.5, 12.0)
        next_b = c(4, 12.7, 20.0, 8.0, 19.0)
        sfp_a = analyze_market(prefix + [next_a]).events_of(MarketEventKind.BEARISH_SFP_CONFIRMED)
        sfp_b = analyze_market(prefix + [next_b]).events_of(MarketEventKind.BEARISH_SFP_CONFIRMED)
        self.assertEqual(len(sfp_a), 1)
        self.assertEqual(len(sfp_b), 1)
        self.assertEqual(sfp_a[0].event_time, next_a.open_time)
        self.assertEqual(sfp_b[0].event_time, next_b.open_time)
        self.assertEqual(sfp_a[0].level_price, sfp_b[0].level_price)

    def test_opposite_swing_pattern_cannot_flip_live_trend_without_bos_close(self):
        candles = bullish_structure_sequence(bos_close=9.2)
        candles.extend(
            [
                c(10, 9.2, 11.0, 8.8, 10.5),
                c(11, 10.5, 12.0, 9.5, 11.5),  # lower high vs 13
                c(12, 11.5, 11.5, 8.7, 9.5),  # confirms LH
                c(13, 9.5, 10.5, 8.0, 9.1),   # lower low wick, but close still above protected HL=9
                c(14, 9.1, 10.0, 8.4, 9.2),   # confirms LL
            ]
        )
        report = analyze_market(candles)
        self.assertEqual(len(report.events_of(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)), 0)
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_STRUCTURE_CONFIRMED)), 0)
        self.assertEqual(report.final_trend, TrendState.BULLISH)


    def test_bearish_conf_uses_only_post_bos_low_lh_and_later_close(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 9.3, 7.5, 8.0),   # post-BOS move to new low
                c(11, 8.0, 9.0, 7.8, 8.5),   # confirms post-BOS swing low 7.5
                c(12, 8.5, 10.5, 8.0, 10.0), # post-BOS correction high
                c(13, 10.0, 10.0, 8.2, 8.8), # confirms LH 10.5
                c(14, 8.8, 9.0, 7.0, 7.2),   # later body close below key low -> CONF
            ]
        )
        report = analyze_market(candles)
        conf = report.events_of(MarketEventKind.BEARISH_CONF_CONFIRMED)
        self.assertEqual(len(conf), 1)
        self.assertEqual(conf[0].candle_index, 14)
        self.assertEqual(conf[0].level_price, 10.5)
        self.assertEqual(report.final_trend, TrendState.BEARISH)

    def test_bullish_conf_uses_only_post_bos_high_hl_and_later_close(self):
        candles = bearish_structure_sequence()
        candles.extend(
            [
                c(10, 13.2, 14.5, 13.0, 14.0),
                c(11, 14.0, 14.0, 13.2, 13.5), # confirms post-BOS swing high 14.5
                c(12, 13.5, 13.8, 12.0, 12.5), # post-BOS correction low
                c(13, 12.5, 14.0, 12.5, 13.8), # confirms HL 12.0
                c(14, 13.8, 15.0, 13.5, 14.7), # later body close above key high -> CONF
            ]
        )
        report = analyze_market(candles)
        conf = report.events_of(MarketEventKind.BULLISH_CONF_CONFIRMED)
        self.assertEqual(len(conf), 1)
        self.assertEqual(conf[0].candle_index, 14)
        self.assertEqual(conf[0].level_price, 12.0)
        self.assertEqual(report.final_trend, TrendState.BULLISH)

    def test_post_bos_single_new_extreme_is_not_enough_for_conf(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 9.3, 7.5, 8.0),
                c(11, 8.0, 9.0, 7.8, 8.5),  # only a post-BOS low exists
            ]
        )
        report = analyze_market(candles)
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_CONF_CONFIRMED)), 0)
        self.assertEqual(report.final_trend, TrendState.BROKEN)


    def test_post_bos_opposite_structure_forms_before_conf(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 9.3, 7.5, 8.0),
                c(11, 8.0, 9.0, 7.8, 8.5),   # confirms post-BOS LL 7.5
                c(12, 8.5, 10.5, 8.0, 10.0),
                c(13, 10.0, 10.0, 8.2, 8.8), # confirms post-BOS LH 10.5
            ]
        )
        report = analyze_market(candles)
        bearish = report.events_of(MarketEventKind.BEARISH_STRUCTURE_CONFIRMED)
        conf = report.events_of(MarketEventKind.BEARISH_CONF_CONFIRMED)
        self.assertTrue(any("Post-BOS bearish structure formed" in e.note for e in bearish))
        self.assertEqual(len(conf), 0)
        self.assertEqual(report.final_trend, TrendState.BEARISH)

    def test_post_bos_new_structure_can_break_before_conf_without_sticking(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 9.3, 7.5, 8.0),
                c(11, 8.0, 9.0, 7.8, 8.5),
                c(12, 8.5, 10.5, 8.0, 10.0),
                c(13, 10.0, 10.0, 8.2, 8.8), # bearish LL+LH established
                c(14, 8.8, 11.0, 8.7, 10.8), # body close above protected LH before bearish CONF
            ]
        )
        report = analyze_market(candles)
        self.assertEqual(len(report.events_of(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)), 1)
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS)), 1)
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_CONF_CONFIRMED)), 0)
        self.assertEqual(report.final_trend, TrendState.BROKEN)

    def test_structure_lifecycle_recovers_across_multiple_bos_without_conf(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 9.3, 7.5, 8.0),
                c(11, 8.0, 9.0, 7.8, 8.5),
                c(12, 8.5, 10.5, 8.0, 10.0),
                c(13, 10.0, 10.0, 8.2, 8.8), # bearish structure, no CONF
                c(14, 8.8, 11.0, 8.7, 10.8), # bullish BOS of bearish structure
                c(15, 10.8, 12.0, 10.0, 11.8),
                c(16, 11.8, 11.9, 10.5, 11.0), # confirms post-BOS HH 12
                c(17, 11.0, 11.2, 9.0, 9.5),
                c(18, 9.5, 10.8, 9.3, 10.4),  # confirms post-BOS HL 9 -> bullish structure
            ]
        )
        report = analyze_market(candles)
        self.assertEqual(len(report.events_of(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)), 1)
        self.assertEqual(len(report.events_of(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS)), 1)
        self.assertEqual(report.final_trend, TrendState.BULLISH)
        self.assertLessEqual(report.longest_state_run(TrendState.BROKEN), 4)
        self.assertGreaterEqual(report.state_candle_counts()[TrendState.BULLISH.value], 2)
        self.assertGreaterEqual(report.state_candle_counts()[TrendState.BEARISH.value], 1)

    def test_older_history_does_not_suppress_recent_second_bos_cycle(self):
        # Warm-up history ends bullish. The common recent segment contains a bullish BOS,
        # post-BOS bearish structure, and a second BOS before CONF. The second BOS must
        # still exist when older history is prepended; this targets the v0.4.7 BROKEN lock.
        warm = [
            Candle(
                open_time=x.open_time, close_time=x.close_time,
                open=x.open * 0.5, high=x.high * 0.5, low=x.low * 0.5, close=x.close * 0.5,
                is_closed=x.is_closed,
            )
            for x in bullish_structure_sequence(bos_close=9.2)
        ]
        recent = bullish_structure_sequence() + [
            c(10, 8.8, 9.3, 7.5, 8.0),
            c(11, 8.0, 9.0, 7.8, 8.5),
            c(12, 8.5, 10.5, 8.0, 10.0),
            c(13, 10.0, 10.0, 8.2, 8.8),
            c(14, 8.8, 11.0, 8.7, 10.8),
        ]
        shift = timedelta(minutes=len(warm))
        shifted_recent = [
            Candle(
                open_time=x.open_time + shift, close_time=x.close_time + shift,
                open=x.open, high=x.high, low=x.low, close=x.close, is_closed=x.is_closed,
            )
            for x in recent
        ]
        short_report = analyze_market(recent)
        long_report = analyze_market(warm + shifted_recent)
        short_kinds = [
            e.kind for e in short_report.events
            if e.kind in {MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS}
        ]
        cutoff = shifted_recent[0].open_time
        long_recent_kinds = [
            e.kind for e in long_report.events
            if e.event_time >= cutoff and e.kind in {MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS}
        ]
        self.assertEqual(short_kinds, [
            MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
            MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
        ])
        self.assertEqual(long_recent_kinds[-2:], short_kinds)

    def test_bos_candle_low_can_be_first_bearish_anchor_when_confirmed_after_bos(self):
        # The BOS candle itself is the new LL extreme. It becomes a valid three-candle
        # swing only on the following candle, so using it after confirmation is causal.
        candles = bullish_structure_sequence()
        candles[-1] = c(9, 11.6, 11.9, 7.5, 8.0)  # bullish BOS + eventual LL center
        candles.extend([
            c(10, 8.0, 9.0, 7.8, 8.5),           # confirms BOS-candle LL=7.5
            c(11, 8.5, 10.5, 8.0, 10.0),         # later LH center
            c(12, 10.0, 10.0, 8.2, 8.8),         # confirms LH=10.5
        ])
        report = analyze_market(candles)
        bearish = report.events_of(MarketEventKind.BEARISH_STRUCTURE_CONFIRMED)
        self.assertTrue(any("BOS-leg-or-later LL" in e.note for e in bearish))
        self.assertEqual(report.final_trend, TrendState.BEARISH)

    def test_bos_candle_high_can_be_first_bullish_anchor_when_confirmed_after_bos(self):
        # Symmetric case: the bearish-structure BOS candle is the new HH extreme and
        # is only confirmed as a swing on the next candle.
        candles = bearish_structure_sequence()
        candles[-1] = c(9, 11.2, 14.5, 10.8, 13.5)  # bearish BOS + eventual HH center
        candles.extend([
            c(10, 13.5, 14.0, 10.5, 11.0),          # confirms BOS-candle HH=14.5
            c(11, 11.0, 12.0, 10.0, 10.5),          # later HL center
            c(12, 10.5, 13.0, 10.2, 12.5),          # confirms HL=10.0
        ])
        report = analyze_market(candles)
        bullish = report.events_of(MarketEventKind.BULLISH_STRUCTURE_CONFIRMED)
        self.assertTrue(any("BOS-leg-or-later HH" in e.note for e in bullish))
        self.assertEqual(report.final_trend, TrendState.BULLISH)


    def test_post_bos_same_direction_recovery_uses_only_post_bos_structure(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 12.0, 8.0, 11.5),
                c(11, 11.5, 13.8, 10.5, 13.4),  # confirms post-BOS low 8.0
                c(12, 13.4, 14.0, 11.0, 11.5),
                c(13, 11.5, 12.0, 10.0, 10.5),  # confirms post-BOS high 14.0
                c(14, 10.5, 13.0, 10.2, 12.5),  # confirms post-BOS HL 10.0
                c(15, 12.5, 14.5, 12.0, 14.0),
                c(16, 14.0, 14.2, 12.8, 13.2),  # confirms HH 14.5 -> bullish recovery
            ]
        )
        report = analyze_market(candles, analysis_mode=StructureAnalysisMode.TECHNICAL_RECOVERY)
        self.assertEqual(report.final_trend, TrendState.BULLISH)
        self.assertLessEqual(report.longest_state_run(TrendState.BROKEN), 7)
        diagnostics = report.structure_transition_diagnostics
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].resolution_mode, "SAME_DIRECTION_POST_BOS_RECOVERY")
        self.assertEqual(diagnostics[0].resolved_trend, TrendState.BULLISH)
        self.assertIn("BEARISH_CORRECTION_NOT_LH_VS_BROKEN_HH", diagnostics[0].rejection_reasons)

    def test_unresolved_transition_is_diagnostic_not_silently_hidden(self):
        candles = bullish_structure_sequence()
        candles.extend(
            [
                c(10, 8.8, 9.3, 7.5, 8.0),
                c(11, 8.0, 9.0, 7.8, 8.5),
            ]
        )
        report = analyze_market(candles)
        self.assertEqual(report.final_trend, TrendState.BROKEN)
        self.assertEqual(len(report.structure_transition_diagnostics), 1)
        diag = report.structure_transition_diagnostics[0]
        self.assertEqual(diag.resolution_mode, "UNRESOLVED_END_OF_DATA")
        self.assertIsNone(diag.resolved_trend)
        self.assertGreaterEqual(diag.broken_candles, 1)
        self.assertTrue(diag.post_bos_low_level_ids)
        self.assertIn("END_OF_DATA_BEFORE_POST_BOS_STRUCTURE_RESOLUTION", diag.rejection_reasons)

    def test_post_bos_local_recovery_cannot_reuse_pre_bos_swings(self):
        candles = bullish_structure_sequence()
        # Only one new post-BOS low/high pair is not enough for generic HH+HL recovery;
        # pre-BOS highs/lows must not fill the missing pair.
        candles.extend(
            [
                c(10, 8.8, 13.5, 8.0, 13.0),
                c(11, 13.0, 13.2, 10.0, 10.5),
                c(12, 10.5, 12.5, 9.5, 12.0),
            ]
        )
        report = analyze_market(candles)
        recovery = [
            item for item in report.structure_transition_diagnostics
            if item.resolution_mode == "SAME_DIRECTION_POST_BOS_RECOVERY"
        ]
        self.assertEqual(recovery, [])

    def test_order_block_real_market_autovalidation_is_deliberately_blocked(self):
        report = analyze_market(bullish_structure_sequence())
        self.assertFalse(report.order_block_readiness.enabled)
        self.assertEqual(report.order_block_readiness.status, "BLOCKED_PENDING_CONTEXT")
        self.assertGreaterEqual(len(report.order_block_readiness.blocking_reasons), 3)

    def test_unfinished_candle_is_rejected(self):
        candles = [c(0, 10, 11, 9, 10), c(1, 10, 11, 9, 10, closed=False)]
        with self.assertRaises(MarketAnalysisError):
            analyze_market(candles)

    def test_analysis_is_deterministic(self):
        candles = bullish_structure_sequence()
        self.assertEqual(analyze_market(candles), analyze_market(candles))

    def test_prefix_analysis_does_not_change_past_events(self):
        candles = bullish_structure_sequence() + [
            c(10, 8.8, 9.3, 7.5, 8.0),
            c(11, 8.0, 9.0, 7.8, 8.5),
            c(12, 8.5, 10.5, 8.0, 10.0),
            c(13, 10.0, 10.0, 8.2, 8.8),
            c(14, 8.8, 9.0, 7.0, 7.2),
        ]
        full = analyze_market(candles)
        for size in range(3, len(candles) + 1):
            prefix = analyze_market(candles[:size])
            past_from_full = tuple(e for e in full.events if e.candle_index < size)
            self.assertEqual(prefix.events, past_from_full)

    def test_sfp_event_records_completed_sweep_candle_extreme_for_invalidation(self):
        candles = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),
            c(2, 12, 12.5, 10, 11),
            c(3, 11, 13.5, 10.5, 12.8),
            c(4, 12.7, 13.4, 11.5, 12.0),
        ]
        report = analyze_market(candles)
        sfp = report.events_of(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED)
        self.assertEqual(len(sfp), 1)
        self.assertEqual(sfp[0].sfp_pattern_extreme_price, 13.5)

    def test_bearish_sfp_is_invalidated_only_by_body_close_above_pattern_max(self):
        candles = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),
            c(2, 12, 12.5, 10, 11),
            c(3, 11, 13.5, 10.5, 12.8),
            c(4, 12.7, 14.0, 11.5, 13.2),  # wick above 13.5, close below -> still relevant
            c(5, 13.2, 14.2, 12.8, 13.8),  # close above 13.5 -> invalidated
        ]
        report = analyze_market(candles)
        invalid = report.events_of(MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE)
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0].candle_index, 5)
        self.assertEqual(invalid[0].level_price, 13.5)
        self.assertEqual(invalid[0].price, 13.8)

    def test_bearish_sfp_can_invalidate_on_same_confirmation_candle_close(self):
        candles = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),
            c(2, 12, 12.5, 10, 11),
            c(3, 11, 13.5, 10.5, 12.8),
            c(4, 12.7, 14.0, 11.5, 13.8),  # SFP known at open, invalidated at this candle close
        ]
        report = analyze_market(candles)
        sfp = report.events_of(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED)
        invalid = report.events_of(MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE)
        self.assertEqual(len(sfp), 1)
        self.assertEqual(len(invalid), 1)
        self.assertEqual(sfp[0].event_time, candles[4].open_time)
        self.assertEqual(invalid[0].event_time, candles[4].close_time)


if __name__ == "__main__":
    unittest.main()
