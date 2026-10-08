"""Source-linked conformance fixtures.

These are representative numeric fixtures derived from the written rules in the uploaded
materials. They are intentionally separate from generic boundary tests so provenance is
visible. They are not claimed to reproduce exact chart prices from the PDFs.
"""

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.order_block import OrderBlockEvidence, assess_order_block
from crypto_bot.strategy.sfp import detect_sfp
from crypto_bot.strategy.structure import confirmed_swings
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport,
    MarketEvent,
    MarketEventKind,
    OrderBlockReadiness,
    TrendState,
    analyze_market,
)
from range_test_support import analyze_ranges


def c(i, o, h, l, cl):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i)
    return Candle(start, start + timedelta(hours=1), o, h, l, cl, True)


class SourceFixtureTests(unittest.TestCase):
    def test_market_structure_advanced_three_candle_swing_fixture(self):
        # Source: [SW.BAND]5. Рыночная структура (Advanced), p.2.
        swings = confirmed_swings([c(0, 10, 11, 9, 10), c(1, 11, 13, 10, 12), c(2, 12, 12.5, 11, 12)])
        self.assertEqual([(s.index, s.kind, s.price) for s in swings], [(1, "high", 13)])


    def test_market_structure_bos_breaks_last_higher_low_fixture(self):
        # Sources: [SW.BAND]4 Base, p.3 (HH/HL bullish structure) and
        # [SW.BAND]5 Advanced, pp.4-5 (bullish structure breaks through key minimum/HL).
        candles = [
            c(0, 10.0, 11.0, 9.5, 10.2),
            c(1, 10.2, 10.5, 8.0, 9.0),
            c(2, 9.0, 11.0, 8.5, 10.4),
            c(3, 10.4, 12.0, 9.0, 11.3),
            c(4, 11.3, 11.5, 9.5, 10.2),
            c(5, 10.2, 11.0, 9.0, 9.6),
            c(6, 9.6, 12.0, 9.3, 11.2),
            c(7, 11.2, 13.0, 10.0, 12.6),
            c(8, 12.6, 12.7, 10.5, 11.6),
            c(9, 11.6, 11.9, 8.5, 8.8),
        ]
        report = analyze_market(candles)
        bos = report.events_of(MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)
        self.assertEqual(len(bos), 1)
        self.assertEqual(bos[0].level_price, 9.0)

    def test_trading_tools_base_upper_side_sfp_fixture(self):
        # Source: [SW.BAND]8. Торговые инструменты (Base), p.5.
        result = detect_sfp(c(0, 99, 102, 98, 99.5), c(1, 99.4, 100, 97, 98), 100, "high")
        self.assertTrue(result.valid)
        self.assertEqual(result.direction, Direction.SHORT)

    def test_trading_tools_advanced_repeat_ob_requires_ltf_reaction_for_reentry(self):
        # Source: SW_BAND9 Торговые инструменты Advanced, p.3: first test preferred;
        # repeat entry can be considered after LTF reaction.
        e = OrderBlockEvidence(
            liquidity_swept=True,
            aggressive_impulse=True,
            engulfs_previous_candle=True,
            bos_confirmed=True,
            in_htf_poi=True,
            in_structural_impulse=True,
            aligned_with_trend=True,
            imbalance_present=True,
            test_number=2,
            ltf_reaction_confirmed=False,
        )
        a = assess_order_block(e)
        self.assertTrue(a.formation_valid)
        self.assertFalse(a.trade_eligible)

    def test_range_source_boundary_midpoint_and_boundary_sfp_fixture(self):
        # Sources: [SW.BAND]10. Боковое движение, pp.1-3 (impulse -> two boundaries -> 0.5 reaction)
        # and [SW.BAND]8. Торговые инструменты Base, p.5 (range boundary may be SFP liquidity).
        candles = [c(i, 105, 108, 102, 105) for i in range(10)]
        candles[7] = c(7, 106, 112, 104, 109)
        candles[8] = c(8, 108, 109, 103, 106)
        events = (
            MarketEvent(MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS, 0, candles[0].close_time, 103, 1, 102, "fixture"),
            MarketEvent(MarketEventKind.SWING_HIGH_CONFIRMED, 2, candles[2].close_time, 110, 2, 110, "fixture"),
            MarketEvent(MarketEventKind.SWING_LOW_CONFIRMED, 4, candles[4].close_time, 100, 3, 100, "fixture"),
            MarketEvent(MarketEventKind.SWING_HIGH_CONFIRMED, 6, candles[6].close_time, 105, 4, 105, "fixture"),
        )
        base = MarketAnalysisReport(
            candle_count=len(candles),
            final_trend=TrendState.UNKNOWN,
            levels=(), sweep_episodes=(), events=events,
            order_block_readiness=OrderBlockReadiness(False, "BLOCKED", ("fixture",)),
            structure_policy="fixture", sfp_timeframe_preference="fixture", sfp_policy="fixture",
        )
        report = analyze_ranges(candles, base)
        self.assertEqual(report.validated_count, 1)
        sfp = [e for e in report.events if e.kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED]
        self.assertEqual(len(sfp), 1)
        self.assertEqual(sfp[0].level_price, 110)
        self.assertEqual(sfp[0].liquidity_origin, "RANGE_BOUNDARY")

    def test_indicators_source_sfp_close_invalidation_fixture(self):
        # Source: [SW.BAND]12. Индикаторы, p.13: the SFP becomes irrelevant if a candle
        # closes beyond the pattern minimum/maximum. This upper-side fixture uses a
        # bearish SFP and a later body close above the SFP maximum.
        candles = [
            c(0, 10, 11, 9, 10),
            c(1, 10, 13, 9.5, 12),
            c(2, 12, 12.5, 10, 11),
            c(3, 11, 13.5, 10.5, 12.8),
            c(4, 12.7, 13.4, 11.5, 12.0),
            c(5, 12.0, 14.0, 11.8, 13.8),
        ]
        report = analyze_market(candles)
        sfp = report.events_of(MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED)
        invalid = report.events_of(MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE)
        self.assertEqual(len(sfp), 1)
        self.assertEqual(sfp[0].sfp_pattern_extreme_price, 13.5)
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0].price, 13.8)


if __name__ == "__main__":
    unittest.main()
