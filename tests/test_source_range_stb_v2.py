from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_imb_ote_pd_v2 import SourceImpulseReference
from crypto_bot.strategy.source_ob_breaker_v2 import BosReference, QualitativeEvidence
from crypto_bot.strategy.source_range_stb_v2 import (
    CorrectionEndpointReference,
    ManipulationReference,
    RangeDeviationSide,
    assess_source_range,
    assess_source_stb_bts,
    detect_range_deviations,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


BASE = datetime(2026, 6, 1, tzinfo=timezone.utc)


def q(name: str, minute: int, status: EvidenceStatus = EvidenceStatus.PASS) -> QualitativeEvidence:
    return QualitativeEvidence(
        status=status,
        evidence_id=f"qual:{name}" if status == EvidenceStatus.PASS else None,
        known_at=BASE + timedelta(minutes=minute),
    )


def c(minute: int, o: float, h: float, l: float, cl: float, *, closed: bool = True) -> Candle:
    start = BASE + timedelta(minutes=minute)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, closed)


def structure(direction: Direction, minute: int = 5) -> CausalSourceObject:
    t = BASE + timedelta(minutes=minute)
    return CausalSourceObject.formed(
        object_type=SourceObjectType.STRUCTURE,
        symbol="BTC-USDT-SWAP",
        timeframe="15m",
        direction=direction.value,
        formation_at=t,
        known_at=t,
        identity_parts={"direction": direction.value, "known_minute": minute},
        source_rule_ids=("TEST_STRUCTURE",),
        provenance="source structure fixture",
    )


def long_impulse() -> SourceImpulseReference:
    return SourceImpulseReference(
        direction=Direction.LONG,
        start_price=100.0,
        end_price=120.0,
        known_at=BASE + timedelta(minutes=10),
        parent_object_ids=("bull-structure-parent",),
        evidence_id="impulse-long",
        provenance="source-qualified bullish impulse fixture",
    )


def correction(price: float = 110.0, minute: int = 12) -> CorrectionEndpointReference:
    return CorrectionEndpointReference(
        price=price,
        known_at=BASE + timedelta(minutes=minute),
        parent_object_ids=("correction-pivot-parent",),
        evidence_id=f"correction-{price}-{minute}",
        provenance="source-qualified correction endpoint fixture",
    )


def valid_range():
    return assess_source_range(
        symbol="BTC-USDT-SWAP",
        timeframe="15m",
        impulse=long_impulse(),
        correction=correction(),
        strong_directional_impulse=q("strong-impulse", 10),
        midpoint_reaction=q("midpoint-reaction", 15),
        no_internal_structure=q("no-internal-structure", 15),
    )


class SourceRangeV2Tests(unittest.TestCase):
    def test_range_boundaries_follow_impulse_then_correction(self):
        result = valid_range()
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        e = result.evidence
        self.assertEqual((e.lower, e.upper, e.midpoint), (110.0, 120.0, 115.0))
        self.assertEqual(e.first_boundary_price, 120.0)
        self.assertEqual(e.second_boundary_price, 110.0)
        self.assertEqual(e.obj.formation_at, BASE + timedelta(minutes=12))
        self.assertEqual(e.obj.known_at, BASE + timedelta(minutes=15))
        self.assertEqual(e.obj.confirmed_at, BASE + timedelta(minutes=15))
        self.assertFalse(e.obj.trade_eligible)

    def test_strong_impulse_may_be_known_before_second_boundary(self):
        result = valid_range()
        self.assertEqual(result.status, EvidenceStatus.PASS)

    def test_midpoint_reaction_cannot_precede_second_boundary(self):
        result = assess_source_range(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            impulse=long_impulse(),
            correction=correction(),
            strong_directional_impulse=q("strong", 10),
            midpoint_reaction=q("mid", 11),
            no_internal_structure=q("no-structure", 15),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "MIDPOINT_REACTION_KNOWN_BEFORE_RANGE_BOUNDARIES")

    def test_unknown_midpoint_quality_stays_unknown_without_numeric_tolerance(self):
        result = assess_source_range(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            impulse=long_impulse(),
            correction=correction(),
            strong_directional_impulse=q("strong", 10),
            midpoint_reaction=q("mid", 15, EvidenceStatus.UNKNOWN),
            no_internal_structure=q("no-structure", 15),
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_MIDPOINT_REACTION_QUALITATIVE_PROVENANCE")

    def test_internal_structure_evidence_can_fail_range(self):
        result = assess_source_range(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            impulse=long_impulse(),
            correction=correction(),
            strong_directional_impulse=q("strong", 10),
            midpoint_reaction=q("mid", 15),
            no_internal_structure=q("no-structure", 15, EvidenceStatus.FAIL),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "NO_INTERNAL_STRUCTURE_SOURCE_EVIDENCE_FAILED")

    def test_bearish_range_is_directional_mirror(self):
        impulse = SourceImpulseReference(
            direction=Direction.SHORT,
            start_price=120.0,
            end_price=100.0,
            known_at=BASE + timedelta(minutes=10),
            parent_object_ids=("bear-structure-parent",),
            evidence_id="impulse-short",
            provenance="source-qualified bearish impulse fixture",
        )
        result = assess_source_range(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            impulse=impulse,
            correction=correction(price=110.0),
            strong_directional_impulse=q("strong", 10),
            midpoint_reaction=q("mid", 15),
            no_internal_structure=q("no-structure", 15),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        self.assertEqual((result.evidence.lower, result.evidence.upper), (100.0, 110.0))

    def test_deviation_is_boundary_sweep_not_reclaim_or_entry(self):
        result = valid_range()
        assert result.evidence is not None
        deviations = detect_range_deviations(result.evidence, c(16, 115.0, 122.0, 113.0, 119.0))
        self.assertEqual(len(deviations), 1)
        self.assertEqual(deviations[0].side, RangeDeviationSide.HIGH)
        self.assertEqual(deviations[0].boundary_price, 120.0)
        self.assertEqual(deviations[0].extreme_price, 122.0)

    def test_dual_side_deviation_same_candle_is_preserved_not_direction_selected(self):
        result = valid_range()
        assert result.evidence is not None
        deviations = detect_range_deviations(result.evidence, c(16, 115.0, 122.0, 108.0, 114.0))
        self.assertEqual({d.side for d in deviations}, {RangeDeviationSide.HIGH, RangeDeviationSide.LOW})

    def test_candle_before_range_known_cannot_become_retroactive_deviation(self):
        result = valid_range()
        assert result.evidence is not None
        self.assertEqual(
            detect_range_deviations(result.evidence, c(14, 115.0, 122.0, 108.0, 114.0)),
            (),
        )

    def test_future_deviation_does_not_change_range_identity(self):
        a = valid_range()
        b = valid_range()
        assert a.evidence is not None and b.evidence is not None
        detect_range_deviations(a.evidence, c(16, 115.0, 122.0, 113.0, 119.0))
        self.assertEqual(a.evidence.obj.object_id, b.evidence.obj.object_id)


class SourceStbBtsV2Tests(unittest.TestCase):
    def manipulation(self, direction: Direction = Direction.LONG) -> ManipulationReference:
        return ManipulationReference(
            direction=direction,
            swept_side="low" if direction == Direction.LONG else "high",
            zone_low=95.0,
            zone_high=105.0,
            known_at=BASE + timedelta(minutes=10),
            parent_liquidity_id=f"liq-{direction.value}",
            parent_liquidity_known_at=BASE + timedelta(minutes=5),
            evidence_id=f"manipulation-{direction.value}",
            provenance="source liquidity-sweep manipulation fixture",
        )

    def test_stb_long_object_requires_sweep_engulf_bos_and_main_trend(self):
        result = assess_source_stb_bts(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            manipulation=self.manipulation(Direction.LONG),
            main_structure=structure(Direction.LONG),
            full_engulf_of_manipulation=q("full-engulf", 12),
            bos_or_conf=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos-long", kind="BOS"),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        self.assertEqual(result.evidence.kind, "STB")
        self.assertEqual(result.evidence.direction, Direction.LONG)
        self.assertEqual(result.evidence.midpoint, 100.0)
        self.assertFalse(result.evidence.obj.trade_eligible)
        self.assertEqual(result.evidence.obj.formation_at, BASE + timedelta(minutes=10))
        self.assertEqual(result.evidence.obj.known_at, BASE + timedelta(minutes=13))

    def test_bts_short_is_directional_mirror(self):
        result = assess_source_stb_bts(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            manipulation=self.manipulation(Direction.SHORT),
            main_structure=structure(Direction.SHORT),
            full_engulf_of_manipulation=q("full-engulf", 12),
            bos_or_conf=BosReference(Direction.SHORT, BASE + timedelta(minutes=13), "conf-short", kind="CONF"),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        self.assertEqual(result.evidence.kind, "BTS")
        self.assertEqual(result.evidence.direction, Direction.SHORT)

    def test_stb_bts_must_align_with_main_trend(self):
        result = assess_source_stb_bts(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            manipulation=self.manipulation(Direction.LONG),
            main_structure=structure(Direction.SHORT),
            full_engulf_of_manipulation=q("full-engulf", 12),
            bos_or_conf=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos-long"),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "STB_BTS_NOT_ALIGNED_WITH_MAIN_TREND")

    def test_full_engulf_is_qualitative_not_hidden_numeric_filter(self):
        result = assess_source_stb_bts(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            manipulation=self.manipulation(Direction.LONG),
            main_structure=structure(Direction.LONG),
            full_engulf_of_manipulation=q("full-engulf", 12, EvidenceStatus.UNKNOWN),
            bos_or_conf=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos-long"),
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_FULL_MANIPULATION_ENGULF_PROVENANCE")

    def test_stb_bts_requires_bos_or_conf_not_arbitrary_event(self):
        result = assess_source_stb_bts(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            manipulation=self.manipulation(Direction.LONG),
            main_structure=structure(Direction.LONG),
            full_engulf_of_manipulation=q("full-engulf", 12),
            bos_or_conf=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "other", kind="OTHER"),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "STB_BTS_REQUIRES_BOS_OR_CONF")

    def test_manipulation_direction_must_match_swept_side(self):
        with self.assertRaises(ValueError):
            ManipulationReference(
                direction=Direction.LONG,
                swept_side="high",
                zone_low=95.0,
                zone_high=105.0,
                known_at=BASE + timedelta(minutes=10),
                parent_liquidity_id="liq",
                parent_liquidity_known_at=BASE + timedelta(minutes=5),
                evidence_id="bad",
                provenance="bad mirror",
            )

    def test_future_mitigation_is_not_part_of_stb_identity(self):
        kwargs = dict(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            manipulation=self.manipulation(Direction.LONG),
            main_structure=structure(Direction.LONG),
            full_engulf_of_manipulation=q("full-engulf", 12),
            bos_or_conf=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos-long"),
        )
        a = assess_source_stb_bts(**kwargs)
        b = assess_source_stb_bts(**kwargs)
        assert a.evidence is not None and b.evidence is not None
        self.assertEqual(a.evidence.obj.object_id, b.evidence.obj.object_id)


if __name__ == "__main__":
    unittest.main()
