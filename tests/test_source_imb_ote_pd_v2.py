from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.source_imb_ote_pd_v2 import (
    GeometryStatus,
    PremiumDiscountLocation,
    SourceDealingRangeReference,
    SourceImpulseReference,
    assess_imbalance_interaction,
    build_source_ote,
    classify_premium_discount,
    detect_source_imbalance,
)


BASE = datetime(2026, 5, 1, tzinfo=timezone.utc)


def c(minute: int, o: float, h: float, l: float, cl: float, *, closed: bool = True) -> Candle:
    start = BASE + timedelta(minutes=minute)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, closed)


class SourceImbalanceV2Tests(unittest.TestCase):
    def test_bullish_wick_gap_forms_source_imbalance(self):
        first = c(0, 100.0, 101.0, 99.0, 100.5)
        impulse = c(1, 100.5, 108.0, 100.0, 107.0)
        third = c(2, 106.0, 109.0, 105.0, 108.0)
        result = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        self.assertEqual(result.status, GeometryStatus.PASS)
        assert result.evidence is not None
        e = result.evidence
        self.assertEqual(e.direction, Direction.LONG)
        self.assertEqual((e.zone_low, e.zone_high), (101.0, 105.0))
        self.assertEqual(e.equilibrium, 103.0)
        self.assertEqual(e.obj.formation_at, third.close_time)
        self.assertEqual(e.obj.known_at, third.close_time)
        self.assertTrue(e.obj.formation_valid)
        self.assertFalse(e.obj.trade_eligible)

    def test_bearish_wick_gap_forms_source_imbalance(self):
        first = c(0, 100.0, 101.0, 99.0, 99.5)
        impulse = c(1, 99.5, 100.0, 92.0, 93.0)
        third = c(2, 94.0, 95.0, 91.0, 92.0)
        result = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        self.assertTrue(result.valid)
        assert result.evidence is not None
        self.assertEqual(result.evidence.direction, Direction.SHORT)
        self.assertEqual((result.evidence.zone_low, result.evidence.zone_high), (95.0, 99.0))
        self.assertEqual(result.evidence.equilibrium, 97.0)

    def test_exact_wick_touch_has_no_positive_imbalance_zone(self):
        first = c(0, 100.0, 101.0, 99.0, 100.5)
        impulse = c(1, 100.5, 106.0, 100.0, 105.0)
        third = c(2, 103.0, 107.0, 101.0, 106.0)
        result = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        self.assertEqual(result.status, GeometryStatus.FAIL)
        self.assertEqual(result.reason, "NO_POSITIVE_WICK_GAP")

    def test_third_candle_must_be_closed_before_stable_zone_exists(self):
        first = c(0, 100.0, 101.0, 99.0, 100.5)
        impulse = c(1, 100.5, 108.0, 100.0, 107.0)
        third = c(2, 106.0, 109.0, 105.0, 108.0, closed=False)
        result = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        self.assertEqual(result.status, GeometryStatus.FAIL)
        self.assertEqual(result.reason, "IMB_REQUIRES_THREE_CLOSED_CANDLES")

    def test_non_contiguous_three_candle_sequence_is_rejected(self):
        first = c(0, 100.0, 101.0, 99.0, 100.5)
        impulse = c(2, 100.5, 108.0, 100.0, 107.0)
        third = c(3, 106.0, 109.0, 105.0, 108.0)
        result = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        self.assertEqual(result.status, GeometryStatus.FAIL)
        self.assertEqual(result.reason, "IMB_CANDLES_NOT_CONTIGUOUS")

    def test_equilibrium_and_full_fill_are_later_facts_not_object_identity(self):
        first = c(0, 100.0, 101.0, 99.0, 100.5)
        impulse = c(1, 100.5, 108.0, 100.0, 107.0)
        third = c(2, 106.0, 109.0, 105.0, 108.0)
        formed = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        assert formed.evidence is not None
        original_id = formed.evidence.obj.object_id
        eq_only = assess_imbalance_interaction(formed.evidence, c(4, 106.0, 107.0, 102.5, 104.0))
        self.assertTrue(eq_only.equilibrium_touched)
        self.assertFalse(eq_only.full_fill)
        full = assess_imbalance_interaction(formed.evidence, c(5, 104.0, 105.0, 100.5, 102.0))
        self.assertTrue(full.full_fill)
        self.assertEqual(formed.evidence.obj.object_id, original_id)
        self.assertTrue(formed.evidence.obj.formation_valid)

    def test_future_fill_does_not_change_recomputed_imbalance_id(self):
        first = c(0, 100.0, 101.0, 99.0, 100.5)
        impulse = c(1, 100.5, 108.0, 100.0, 107.0)
        third = c(2, 106.0, 109.0, 105.0, 108.0)
        a = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        b = detect_source_imbalance(first, impulse, third, symbol="BTC-USDT-SWAP", timeframe="5m")
        assert a.evidence is not None and b.evidence is not None
        self.assertEqual(a.evidence.obj.object_id, b.evidence.obj.object_id)


class SourceOteV2Tests(unittest.TestCase):
    def test_long_ote_is_exact_0705_to_079_retracement(self):
        impulse = SourceImpulseReference(
            direction=Direction.LONG,
            start_price=100.0,
            end_price=120.0,
            known_at=BASE + timedelta(minutes=10),
            parent_object_ids=("structure-parent",),
            evidence_id="impulse-long-1",
            provenance="source-valid structural impulse fixture",
        )
        ote = build_source_ote(impulse, symbol="BTC-USDT-SWAP", timeframe="15m")
        self.assertAlmostEqual(ote.zone_low, 104.2)
        self.assertAlmostEqual(ote.zone_high, 105.9)
        self.assertEqual(ote.ratio_shallow, 0.705)
        self.assertEqual(ote.ratio_deep, 0.79)
        self.assertFalse(ote.obj.trade_eligible)
        self.assertEqual(ote.obj.parent_object_ids, ("structure-parent",))

    def test_short_ote_is_directional_mirror(self):
        impulse = SourceImpulseReference(
            direction=Direction.SHORT,
            start_price=120.0,
            end_price=100.0,
            known_at=BASE + timedelta(minutes=10),
            parent_object_ids=("structure-parent",),
            evidence_id="impulse-short-1",
            provenance="source-valid structural impulse fixture",
        )
        ote = build_source_ote(impulse, symbol="BTC-USDT-SWAP", timeframe="15m")
        self.assertAlmostEqual(ote.zone_low, 114.1)
        self.assertAlmostEqual(ote.zone_high, 115.8)

    def test_ote_refuses_arbitrary_unproven_anchor_pair(self):
        with self.assertRaises(ValueError):
            SourceImpulseReference(
                direction=Direction.LONG,
                start_price=100.0,
                end_price=120.0,
                known_at=BASE + timedelta(minutes=10),
                parent_object_ids=(),
                evidence_id="",
                provenance="",
            )

    def test_impulse_direction_must_match_endpoint_order(self):
        with self.assertRaises(ValueError):
            SourceImpulseReference(
                direction=Direction.LONG,
                start_price=120.0,
                end_price=100.0,
                known_at=BASE,
                parent_object_ids=("p",),
                evidence_id="bad-long",
                provenance="test",
            )


class PremiumDiscountV2Tests(unittest.TestCase):
    def dealing_range(self) -> SourceDealingRangeReference:
        return SourceDealingRangeReference(
            low=100.0,
            high=120.0,
            known_at=BASE + timedelta(minutes=20),
            parent_object_ids=("range-parent",),
            evidence_id="dealing-range-1",
            provenance="source-qualified dealing range fixture",
        )

    def test_midpoint_is_equilibrium(self):
        r = self.dealing_range()
        result = classify_premium_discount(r, price=110.0, decision_at=r.known_at)
        self.assertEqual(result.location, PremiumDiscountLocation.EQUILIBRIUM)
        self.assertEqual(result.equilibrium, 110.0)

    def test_lower_half_discount_upper_half_premium(self):
        r = self.dealing_range()
        discount = classify_premium_discount(r, price=105.0, decision_at=r.known_at)
        premium = classify_premium_discount(r, price=115.0, decision_at=r.known_at)
        self.assertEqual(discount.location, PremiumDiscountLocation.DISCOUNT)
        self.assertEqual(premium.location, PremiumDiscountLocation.PREMIUM)

    def test_cannot_use_dealing_range_before_it_is_known(self):
        r = self.dealing_range()
        with self.assertRaises(ValueError):
            classify_premium_discount(r, price=105.0, decision_at=r.known_at - timedelta(seconds=1))

    def test_pd_does_not_invent_range_from_outside_price(self):
        r = self.dealing_range()
        with self.assertRaises(ValueError):
            classify_premium_discount(r, price=125.0, decision_at=r.known_at)

    def test_dealing_range_requires_provenance_and_parent(self):
        with self.assertRaises(ValueError):
            SourceDealingRangeReference(
                low=100.0,
                high=120.0,
                known_at=BASE,
                parent_object_ids=(),
                evidence_id="",
                provenance="",
            )


if __name__ == "__main__":
    unittest.main()
