from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EqualLiquidityKind,
    EvidenceStatus,
    LiquidityLocation,
    assess_equal_liquidity,
    bos_breaks_active_leg,
    confirmed_source_swings,
    latest_structure_leg,
    strict_liquidity_take,
    structural_liquidity,
)


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def c(i: int, o: float, h: float, l: float, cl: float, *, closed: bool = True) -> Candle:
    start = BASE + timedelta(minutes=i)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, closed)


def bullish_sequence() -> list[Candle]:
    # Confirmed swings: L=8, H=12, HL=9, HH=13.
    return [
        c(0, 10, 11, 9.5, 10.2),
        c(1, 10.2, 10.5, 8, 9),
        c(2, 9, 11, 8.5, 10.4),
        c(3, 10.4, 12, 9, 11.3),
        c(4, 11.3, 11.5, 9.5, 10.2),
        c(5, 10.2, 11, 9, 9.6),
        c(6, 9.6, 12, 9.3, 11.2),
        c(7, 11.2, 13, 10, 12.6),
        c(8, 12.6, 12.7, 10.5, 11.6),
    ]


def bearish_sequence() -> list[Candle]:
    # Confirmed swings: H=14, L=10, LH=13, LL=9.
    return [
        c(0, 12, 13.5, 11, 12.3),
        c(1, 12.3, 14, 11.5, 13.2),
        c(2, 13.2, 13.5, 10.8, 11.6),
        c(3, 11.6, 12.6, 10, 10.5),
        c(4, 10.5, 12, 10.4, 11.5),
        c(5, 11.5, 13, 10.6, 12.5),
        c(6, 12.5, 12.7, 9.8, 10.4),
        c(7, 10.4, 11.5, 9, 9.4),
        c(8, 9.4, 12, 9.2, 11.2),
    ]


class SourceStructureLiquidityV2Tests(unittest.TestCase):
    def test_swing_is_known_only_after_right_candle_closes(self):
        candles = [c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11)]
        swings = confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m")
        high = next(s for s in swings if s.side == "high")
        self.assertEqual(high.center_index, 1)
        self.assertEqual(high.confirmed_index, 2)
        self.assertEqual(high.obj.known_at, candles[2].close_time)
        self.assertEqual(high.obj.formation_at, candles[2].close_time)
        self.assertIn("MS_SWING_HIGH_001", high.obj.source_rule_ids)
        self.assertIn("SWING_CONFIRM_001", high.obj.technical_normalization_ids)

    def test_unfinished_right_candle_is_rejected(self):
        candles = [c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11, closed=False)]
        with self.assertRaises(ValueError):
            confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m")

    def test_bullish_structure_leg_is_interleaved_hh_hl(self):
        swings = confirmed_source_swings(bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m")
        leg = latest_structure_leg(swings)
        self.assertIsNotNone(leg)
        assert leg is not None
        self.assertEqual(leg.direction, "BULLISH")
        self.assertEqual(leg.protected_price, 9)
        self.assertEqual(leg.extreme_price, 13)

    def test_bearish_structure_leg_is_interleaved_ll_lh(self):
        swings = confirmed_source_swings(bearish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m")
        leg = latest_structure_leg(swings)
        self.assertIsNotNone(leg)
        assert leg is not None
        self.assertEqual(leg.direction, "BEARISH")
        self.assertEqual(leg.protected_price, 13)
        self.assertEqual(leg.extreme_price, 9)

    def test_bos_requires_body_close_beyond_protected_point(self):
        leg = latest_structure_leg(
            confirmed_source_swings(bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m")
        )
        assert leg is not None
        wick_only = c(20, 10, 10.5, 8.5, 9.2)
        close_break = c(21, 9.2, 9.4, 8.5, 8.8)
        self.assertFalse(bos_breaks_active_leg(wick_only, leg))
        self.assertTrue(bos_breaks_active_leg(close_break, leg))

    def test_structural_liquidity_external_without_active_leg(self):
        swings = confirmed_source_swings(bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m")
        pool = structural_liquidity(
            swings[0], symbol="BTC-USDT-SWAP", timeframe="1m", active_leg=None
        )
        self.assertEqual(pool.location, LiquidityLocation.EXTERNAL)
        self.assertEqual(pool.obj.parent_object_ids, (swings[0].obj.object_id,))
        self.assertIn("LIQ_STRUCTURAL_001", pool.obj.source_rule_ids)

    def test_structural_liquidity_inside_known_leg_is_internal(self):
        swings = confirmed_source_swings(bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m")
        leg = latest_structure_leg(swings)
        assert leg is not None
        internal_swing = next(s for s in swings if s.side == "high" and s.price == 12)
        pool = structural_liquidity(
            internal_swing, symbol="BTC-USDT-SWAP", timeframe="1m", active_leg=leg
        )
        self.assertEqual(pool.location, LiquidityLocation.INTERNAL)

    def test_exact_eqh_does_not_pass_without_substructure_evidence(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11),
            c(3, 11, 12, 9, 10), c(4, 10, 13, 9.5, 12), c(5, 12, 12, 10, 11),
        ]
        highs = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "high"]
        self.assertEqual(len(highs), 2)
        evidence = assess_equal_liquidity(
            highs[0], highs[1], kind=EqualLiquidityKind.EQH,
            substructure_pair_confirmed=None, reasonable_tilt_confirmed=None,
        )
        self.assertEqual(evidence.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(evidence.reason, "WAIT_SUBSTRUCTURE_EVIDENCE")

    def test_exact_eqh_passes_when_pair_is_confirmed_substructure(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11),
            c(3, 11, 12, 9, 10), c(4, 10, 13, 9.5, 12), c(5, 12, 12, 10, 11),
        ]
        highs = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "high"]
        evidence = assess_equal_liquidity(
            highs[0], highs[1], kind=EqualLiquidityKind.EQH,
            substructure_pair_confirmed=True, reasonable_tilt_confirmed=None,
        )
        self.assertEqual(evidence.status, EvidenceStatus.PASS)
        self.assertTrue(evidence.exact_price)

    def test_tilted_eqh_is_unknown_without_reasonable_tilt_evidence(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11),
            c(3, 11, 12, 9, 10), c(4, 10, 12.8, 9.5, 12), c(5, 12, 12, 10, 11),
        ]
        highs = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "high"]
        evidence = assess_equal_liquidity(
            highs[0], highs[1], kind=EqualLiquidityKind.EQH,
            substructure_pair_confirmed=True, reasonable_tilt_confirmed=None,
        )
        self.assertEqual(evidence.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(evidence.reason, "WAIT_QUALITATIVE_REASONABLE_TILT")
        self.assertFalse(evidence.exact_price)
        self.assertTrue(evidence.directional_tilt_valid)

    def test_tilted_eqh_true_without_provenance_stays_unknown(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11),
            c(3, 11, 12, 9, 10), c(4, 10, 12.8, 9.5, 12), c(5, 12, 12, 10, 11),
        ]
        highs = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "high"]
        evidence = assess_equal_liquidity(
            highs[0], highs[1], kind=EqualLiquidityKind.EQH,
            substructure_pair_confirmed=True, reasonable_tilt_confirmed=True,
        )
        self.assertEqual(evidence.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(evidence.reason, "WAIT_QUALITATIVE_EVIDENCE_PROVENANCE")

    def test_tilted_eqh_passes_only_after_qualitative_confirmation_with_provenance(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 13, 9.5, 12), c(2, 12, 12, 10, 11),
            c(3, 11, 12, 9, 10), c(4, 10, 12.8, 9.5, 12), c(5, 12, 12, 10, 11),
        ]
        highs = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "high"]
        evidence = assess_equal_liquidity(
            highs[0], highs[1], kind=EqualLiquidityKind.EQH,
            substructure_pair_confirmed=True, reasonable_tilt_confirmed=True,
            qualitative_evidence_id="annotation:eqh:001",
        )
        self.assertEqual(evidence.status, EvidenceStatus.PASS)
        self.assertEqual(evidence.qualitative_evidence_id, "annotation:eqh:001")
        self.assertEqual(evidence.reason, "QUALITATIVE_REASONABLE_TILT_CONFIRMED")

    def test_wrong_eqh_tilt_direction_fails(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 12.8, 9.5, 12), c(2, 12, 12, 10, 11),
            c(3, 11, 12, 9, 10), c(4, 10, 13, 9.5, 12), c(5, 12, 12, 10, 11),
        ]
        highs = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "high"]
        evidence = assess_equal_liquidity(
            highs[0], highs[1], kind=EqualLiquidityKind.EQH,
            substructure_pair_confirmed=True, reasonable_tilt_confirmed=True,
            qualitative_evidence_id="annotation:eqh:bad-direction",
        )
        self.assertEqual(evidence.status, EvidenceStatus.FAIL)
        self.assertEqual(evidence.reason, "SOURCE_TILT_DIRECTION_VIOLATION")

    def test_eql_mirror_uses_left_low_below_right_low(self):
        candles = [
            c(0, 10, 11, 9, 10), c(1, 10, 11, 8, 9), c(2, 9, 11, 8.5, 10),
            c(3, 10, 11, 9, 10), c(4, 10, 11, 8.2, 9), c(5, 9, 11, 8.5, 10),
        ]
        lows = [s for s in confirmed_source_swings(candles, symbol="BTC-USDT-SWAP", timeframe="1m") if s.side == "low"]
        evidence = assess_equal_liquidity(
            lows[0], lows[1], kind=EqualLiquidityKind.EQL,
            substructure_pair_confirmed=True, reasonable_tilt_confirmed=True,
            qualitative_evidence_id="annotation:eql:001",
        )
        self.assertEqual(evidence.status, EvidenceStatus.PASS)

    def test_strict_raid_is_a_named_normalization_not_eq_tolerance(self):
        swings = confirmed_source_swings(bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m")
        high_swing = next(s for s in swings if s.side == "high" and s.price == 12)
        pool = structural_liquidity(high_swing, symbol="BTC-USDT-SWAP", timeframe="1m", active_leg=None)
        equal_touch = c(30, 10, pool.price, 9, 10)
        penetration = c(31, 10, pool.price + 0.1, 9, 10)
        self.assertFalse(strict_liquidity_take(equal_touch, pool))
        self.assertTrue(strict_liquidity_take(penetration, pool))

    def test_future_extension_does_not_change_existing_swing_ids(self):
        prefix = bullish_sequence()
        future = [c(9, 11.6, 14, 10, 13), c(10, 13, 13.5, 11, 12)]
        a = confirmed_source_swings(prefix, symbol="BTC-USDT-SWAP", timeframe="1m")
        b = confirmed_source_swings(prefix + future, symbol="BTC-USDT-SWAP", timeframe="1m")
        self.assertEqual([s.obj.object_id for s in a], [s.obj.object_id for s in b[: len(a)]])
        self.assertEqual([s.obj.known_at for s in a], [s.obj.known_at for s in b[: len(a)]])


if __name__ == "__main__":
    unittest.main()
