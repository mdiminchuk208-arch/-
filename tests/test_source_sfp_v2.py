from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, ObjectStatus, SourceObjectType
from crypto_bot.strategy.source_sfp_v2 import (
    SfpFormationStatus,
    SfpLiquidityReference,
    SfpOrigin,
    apply_sfp_invalidation,
    detect_source_sfp,
    directions_are_ambiguous_for_same_formation,
    sfp_invalidated_by_body_close,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    LiquidityLocation,
    StructuralLiquidityEvidence,
)


BASE = datetime(2026, 3, 1, tzinfo=timezone.utc)


def c(
    minute: int,
    o: float,
    h: float,
    l: float,
    cl: float,
    *,
    closed: bool = True,
) -> Candle:
    start = BASE + timedelta(minutes=minute)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, closed)


def structural_pool(
    *,
    side: str,
    price: float,
    known_minute: int = 0,
    location: LiquidityLocation = LiquidityLocation.EXTERNAL,
) -> StructuralLiquidityEvidence:
    known = BASE + timedelta(minutes=known_minute)
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.LIQUIDITY_POOL,
        symbol="BTC-USDT-SWAP",
        timeframe="5m",
        direction=None,
        formation_at=known,
        known_at=known,
        identity_parts={"level_price": price, "side": side, "origin": "test-structural"},
        source_rule_ids=("LIQ_STRUCTURAL_001",),
        provenance="test structural liquidity",
    )
    return StructuralLiquidityEvidence(
        obj=obj,
        swing_object_id="test-parent-pivot",
        side=side,
        price=price,
        location=location,
    )


def valid_bearish() -> tuple[Candle, Candle, SfpLiquidityReference]:
    pool = structural_pool(side="high", price=103.0)
    ref = SfpLiquidityReference.from_structural_liquidity(pool)
    sweep = c(10, 101.0, 105.0, 100.0, 102.0)
    next_candle = c(11, 102.0, 103.0, 101.0, 102.5, closed=False)
    return sweep, next_candle, ref


def valid_bullish() -> tuple[Candle, Candle, SfpLiquidityReference]:
    pool = structural_pool(side="low", price=97.0)
    ref = SfpLiquidityReference.from_structural_liquidity(pool)
    sweep = c(10, 99.0, 100.0, 95.0, 98.0)
    next_candle = c(11, 98.0, 99.0, 97.5, 98.5, closed=False)
    return sweep, next_candle, ref


class SourceSfpV2Tests(unittest.TestCase):
    def test_bearish_source_sfp_forms_on_immediate_next_open(self):
        sweep, next_candle, ref = valid_bearish()
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertEqual(result.status, SfpFormationStatus.PASS)
        assert result.evidence is not None
        evidence = result.evidence
        self.assertEqual(evidence.direction, Direction.SHORT)
        self.assertEqual(evidence.obj.formation_at, next_candle.open_time)
        self.assertEqual(evidence.obj.known_at, next_candle.open_time)
        self.assertFalse(evidence.obj.trade_eligible)
        self.assertTrue(evidence.obj.formation_valid)
        self.assertTrue(evidence.requires_ltf_bos)
        self.assertEqual(evidence.pattern_extreme, sweep.high)
        self.assertEqual(evidence.origin, SfpOrigin.STRUCTURAL_LIQUIDITY)

    def test_bullish_source_sfp_is_mirrored(self):
        sweep, next_candle, ref = valid_bullish()
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertTrue(result.valid)
        assert result.evidence is not None
        self.assertEqual(result.evidence.direction, Direction.LONG)
        self.assertEqual(result.evidence.pattern_extreme, sweep.low)

    def test_next_candle_may_be_unfinished_because_only_open_is_used(self):
        sweep, next_candle, ref = valid_bearish()
        self.assertFalse(next_candle.is_closed)
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertTrue(result.valid)

    def test_future_next_candle_hlc_mutation_cannot_change_sfp_id(self):
        sweep, next_candle, ref = valid_bearish()
        a = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        mutated = replace(next_candle, high=110.0, low=90.0, close=109.0)
        b = detect_source_sfp(
            sweep,
            mutated,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        assert a.evidence is not None and b.evidence is not None
        self.assertEqual(a.evidence.obj.object_id, b.evidence.obj.object_id)
        self.assertEqual(a.evidence.obj.known_at, b.evidence.obj.known_at)

    def test_unclosed_sweep_candle_fails(self):
        sweep, next_candle, ref = valid_bearish()
        result = detect_source_sfp(
            replace(sweep, is_closed=False),
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "SWEEP_CANDLE_NOT_CLOSED")

    def test_liquidity_must_be_known_before_sweep_begins(self):
        late_pool = structural_pool(side="high", price=103.0, known_minute=10)
        late_ref = SfpLiquidityReference.from_structural_liquidity(late_pool)
        sweep = c(10, 101.0, 105.0, 100.0, 102.0)
        next_candle = c(11, 102.0, 103.0, 101.0, 102.5, closed=False)
        # Same timestamp as sweep open is causally available; one second later is not.
        self.assertTrue(
            detect_source_sfp(
                sweep,
                next_candle,
                late_ref,
                symbol="BTC-USDT-SWAP",
                timeframe="5m",
            ).valid
        )
        too_late_obj = replace(late_pool.obj, known_at=sweep.open_time + timedelta(seconds=1))
        too_late = StructuralLiquidityEvidence(
            obj=too_late_obj,
            swing_object_id=late_pool.swing_object_id,
            side=late_pool.side,
            price=late_pool.price,
            location=late_pool.location,
        )
        too_late_ref = SfpLiquidityReference.from_structural_liquidity(too_late)
        result = detect_source_sfp(
            sweep,
            next_candle,
            too_late_ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "LIQUIDITY_NOT_KNOWN_BEFORE_SWEEP")

    def test_internal_liquidity_cannot_anchor_clean_sfp(self):
        pool = structural_pool(
            side="high",
            price=103.0,
            location=LiquidityLocation.INTERNAL,
        )
        with self.assertRaises(ValueError):
            SfpLiquidityReference.from_structural_liquidity(pool)

    def test_sweep_without_strict_penetration_fails(self):
        sweep, next_candle, ref = valid_bearish()
        sweep = replace(sweep, high=ref.price)
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "EXTERNAL_LIQUIDITY_NOT_SWEPT")

    def test_sweep_candle_body_must_close_back_inside(self):
        sweep, next_candle, ref = valid_bearish()
        sweep = replace(sweep, close=104.0)
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "SWEEP_BODY_DID_NOT_CLOSE_BACK_INSIDE")

    def test_next_open_must_be_back_inside(self):
        sweep, next_candle, ref = valid_bearish()
        next_candle = replace(next_candle, open=104.0, high=105.0)
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "NEXT_CANDLE_DID_NOT_OPEN_INSIDE")

    def test_missing_immediate_next_open_fails(self):
        sweep, next_candle, ref = valid_bearish()
        delayed = replace(
            next_candle,
            open_time=next_candle.open_time + timedelta(minutes=1),
            close_time=next_candle.close_time + timedelta(minutes=1),
        )
        result = detect_source_sfp(
            sweep,
            delayed,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "IMMEDIATE_NEXT_CANDLE_OPEN_UNAVAILABLE")

    def test_sfp_is_source_valid_below_h1_preference(self):
        sweep, next_candle, ref = valid_bearish()
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="1m",
        )
        self.assertTrue(result.valid)
        assert result.evidence is not None
        self.assertEqual(result.evidence.obj.timeframe, "1m")

    def test_range_boundary_is_supported_as_external_sfp_origin(self):
        known = BASE
        range_obj = CausalSourceObject.formed(
            object_type=SourceObjectType.RANGE,
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            direction=None,
            formation_at=known,
            known_at=known,
            identity_parts={"range_origin": "test", "boundary_a": 103.0, "boundary_b": 97.0},
            source_rule_ids=("RANGE_SOURCE_PLACEHOLDER",),
            provenance="test range object",
        )
        ref = SfpLiquidityReference.from_range_boundary(range_obj, side="high", price=103.0)
        sweep = c(10, 101.0, 105.0, 100.0, 102.0)
        next_candle = c(11, 102.0, 103.0, 101.0, 102.5, closed=False)
        result = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
        )
        self.assertTrue(result.valid)
        assert result.evidence is not None
        self.assertEqual(result.evidence.origin, SfpOrigin.RANGE_BOUNDARY)
        self.assertEqual(result.evidence.obj.parent_object_ids, (range_obj.object_id,))

    def test_wick_beyond_pattern_extreme_does_not_invalidate_without_body_close(self):
        sweep, next_candle, ref = valid_bullish()
        formed = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        assert formed.evidence is not None
        later = c(20, 99.0, 100.0, 94.0, 98.5)
        self.assertFalse(sfp_invalidated_by_body_close(formed.evidence, later))
        unchanged = apply_sfp_invalidation(formed.evidence, later)
        self.assertIsNone(unchanged.obj.invalidated_at)

    def test_body_close_beyond_pattern_extreme_invalidates_append_only(self):
        sweep, next_candle, ref = valid_bullish()
        formed = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        assert formed.evidence is not None
        before = formed.evidence.obj.state_at(formed.evidence.obj.known_at)
        later = c(20, 99.0, 100.0, 97.0, 97.5)
        invalidated = apply_sfp_invalidation(formed.evidence, later)
        after = invalidated.obj.state_at(later.close_time)
        self.assertTrue(before.formation_valid)
        self.assertEqual(before.status, ObjectStatus.KNOWN)
        self.assertTrue(after.formation_valid)
        self.assertEqual(after.status, ObjectStatus.INVALIDATED)
        self.assertEqual(invalidated.obj.invalidated_at, later.close_time)
        self.assertEqual(invalidated.obj.object_id, formed.evidence.obj.object_id)

    def test_no_finite_expiry_is_applied(self):
        sweep, next_candle, ref = valid_bearish()
        formed = detect_source_sfp(
            sweep,
            next_candle,
            ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        assert formed.evidence is not None
        far_later = c(10_000, 102.0, 104.0, 100.0, 102.0)
        unchanged = apply_sfp_invalidation(formed.evidence, far_later)
        self.assertIsNone(unchanged.obj.invalidated_at)
        self.assertTrue(unchanged.obj.formation_valid)
        self.assertFalse(unchanged.obj.trade_eligible)

    def test_dual_side_same_time_is_ambiguous_for_chain_not_object_validity(self):
        high_ref = SfpLiquidityReference.from_structural_liquidity(
            structural_pool(side="high", price=103.0)
        )
        low_ref = SfpLiquidityReference.from_structural_liquidity(
            structural_pool(side="low", price=97.0)
        )
        sweep = c(10, 100.0, 105.0, 95.0, 100.0)
        next_candle = c(11, 100.0, 101.0, 99.0, 100.0, closed=False)
        short = detect_source_sfp(
            sweep,
            next_candle,
            high_ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        long = detect_source_sfp(
            sweep,
            next_candle,
            low_ref,
            symbol="BTC-USDT-SWAP",
            timeframe="5m",
        )
        assert short.evidence is not None and long.evidence is not None
        self.assertTrue(short.evidence.obj.formation_valid)
        self.assertTrue(long.evidence.obj.formation_valid)
        self.assertTrue(directions_are_ambiguous_for_same_formation((short.evidence, long.evidence)))


if __name__ == "__main__":
    unittest.main()
