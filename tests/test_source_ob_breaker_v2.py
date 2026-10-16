from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import (
    CausalSourceObject,
    RejectionCategory,
    SourceObjectType,
)
from crypto_bot.strategy.source_ob_breaker_v2 import (
    BosReference,
    FormationStatus,
    QualitativeEvidence,
    assess_source_breaker,
    assess_source_order_block,
    raid_from_structural_liquidity,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EvidenceStatus,
    LiquidityLocation,
    StructuralLiquidityEvidence,
)


BASE = datetime(2026, 4, 1, tzinfo=timezone.utc)


def c(minute: int, o: float, h: float, l: float, cl: float, *, closed: bool = True) -> Candle:
    start = BASE + timedelta(minutes=minute)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, closed)


def source_obj(
    object_type: SourceObjectType,
    *,
    name: str,
    known_minute: int,
    direction: str | None = None,
) -> CausalSourceObject:
    known = BASE + timedelta(minutes=known_minute)
    return CausalSourceObject.formed(
        object_type=object_type,
        symbol="BTC-USDT-SWAP",
        timeframe="15m",
        direction=direction,
        formation_at=known,
        known_at=known,
        identity_parts={"name": name, "known_minute": known_minute},
        source_rule_ids=("TEST_SOURCE_PARENT",),
        provenance=f"test {name}",
    )


def pool(*, known_minute: int = 0, side: str = "low", price: float = 97.0) -> StructuralLiquidityEvidence:
    obj = source_obj(SourceObjectType.LIQUIDITY_POOL, name=f"liq-{side}-{price}", known_minute=known_minute)
    return StructuralLiquidityEvidence(
        obj=obj,
        swing_object_id="test-pivot-parent",
        side=side,
        price=price,
        location=LiquidityLocation.EXTERNAL,
    )


def q(name: str, *, status: EvidenceStatus = EvidenceStatus.PASS, minute: int = 12) -> QualitativeEvidence:
    return QualitativeEvidence(
        status=status,
        evidence_id=f"qual:{name}" if status == EvidenceStatus.PASS else None,
        known_at=BASE + timedelta(minutes=minute),
    )


def valid_long_ob(*, imbalance_present: bool | None = True):
    candidate = c(10, 100.0, 101.0, 95.0, 98.0)
    impulse = c(11, 98.0, 105.0, 97.5, 104.0)
    liquidity = pool(side="low", price=97.0)
    raid = raid_from_structural_liquidity(liquidity, candidate)
    structure = source_obj(
        SourceObjectType.STRUCTURE,
        name="bull-structure",
        known_minute=5,
        direction=Direction.LONG.value,
    )
    poi = source_obj(SourceObjectType.POI, name="htf-poi", known_minute=5, direction=Direction.LONG.value)
    bos = BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos-long-13")
    assessment = assess_source_order_block(
        symbol="BTC-USDT-SWAP",
        timeframe="15m",
        candidate=candidate,
        impulse=impulse,
        raid=raid,
        bos=bos,
        htf_poi=poi,
        structure=structure,
        aggressive_impulse=q("aggressive", minute=12),
        large_body_small_wicks=q("body-wicks", minute=12),
        imbalance_present=imbalance_present,
    )
    return assessment, candidate, impulse, liquidity, structure, poi


class SourceOrderBlockV2Tests(unittest.TestCase):
    def test_valid_ob_is_object_not_trade_admission(self):
        assessment, candidate, impulse, liquidity, structure, poi = valid_long_ob()
        self.assertEqual(assessment.status, FormationStatus.PASS)
        assert assessment.evidence is not None
        evidence = assessment.evidence
        self.assertTrue(evidence.obj.formation_valid)
        self.assertFalse(evidence.obj.trade_eligible)
        self.assertEqual(evidence.direction, Direction.LONG)
        self.assertEqual((evidence.zone_low, evidence.zone_high), (candidate.low, candidate.high))
        self.assertEqual(evidence.obj.formation_at, impulse.close_time)
        self.assertEqual(evidence.obj.known_at, BASE + timedelta(minutes=13))
        self.assertIn(liquidity.obj.object_id, evidence.obj.parent_object_ids)
        self.assertIn(structure.object_id, evidence.obj.parent_object_ids)
        self.assertIn(poi.object_id, evidence.obj.parent_object_ids)

    def test_ob_candle_itself_must_be_the_liquidity_raid(self):
        assessment, candidate, impulse, _, structure, poi = valid_long_ob()
        assert assessment.evidence is not None
        later_pool = pool(known_minute=0, side="low", price=94.0)
        no_raid = raid_from_structural_liquidity(later_pool, candidate)
        self.assertIsNone(no_raid)
        result = assess_source_order_block(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            candidate=candidate,
            impulse=impulse,
            raid=no_raid,
            bos=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos"),
            htf_poi=poi,
            structure=structure,
            aggressive_impulse=q("aggressive"),
            large_body_small_wicks=q("body-wicks"),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "OB_CANDLE_DID_NOT_CAUSALLY_SWEEP_LIQUIDITY")

    def test_liquidity_discovered_after_candidate_open_cannot_anchor_ob(self):
        candidate = c(10, 100.0, 101.0, 95.0, 98.0)
        late = pool(known_minute=11, side="low", price=97.0)
        self.assertIsNone(raid_from_structural_liquidity(late, candidate))

    def test_qualitative_aggressive_impulse_needs_provenance_not_numeric_threshold(self):
        assessment, candidate, impulse, liquidity, structure, poi = valid_long_ob()
        assert assessment.evidence is not None
        raid = raid_from_structural_liquidity(liquidity, candidate)
        result = assess_source_order_block(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            candidate=candidate,
            impulse=impulse,
            raid=raid,
            bos=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos"),
            htf_poi=poi,
            structure=structure,
            aggressive_impulse=QualitativeEvidence(EvidenceStatus.UNKNOWN, None, BASE + timedelta(minutes=12)),
            large_body_small_wicks=q("body-wicks"),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_AGGRESSIVE_IMPULSE_QUALITATIVE_PROVENANCE")

    def test_absent_or_unknown_imbalance_does_not_get_silently_resolved(self):
        for value in (False, None):
            assessment, *_ = valid_long_ob(imbalance_present=value)
            self.assertEqual(assessment.status, FormationStatus.UNKNOWN)
            self.assertEqual(assessment.reason, "SOURCE_CONFLICT_OB_IMB_HARD_VS_QUALITY_UNRESOLVED")
            self.assertIsNone(assessment.evidence)

    def test_htf_poi_must_be_known_before_ob_candidate(self):
        assessment, candidate, impulse, liquidity, structure, _ = valid_long_ob()
        assert assessment.evidence is not None
        raid = raid_from_structural_liquidity(liquidity, candidate)
        late_poi = source_obj(SourceObjectType.POI, name="late-poi", known_minute=11, direction=Direction.LONG.value)
        result = assess_source_order_block(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            candidate=candidate,
            impulse=impulse,
            raid=raid,
            bos=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos"),
            htf_poi=late_poi,
            structure=structure,
            aggressive_impulse=q("aggressive"),
            large_body_small_wicks=q("body-wicks"),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "HTF_POI_NOT_KNOWN_BEFORE_OB_FORMATION")

    def test_structure_direction_must_match_ob_direction(self):
        assessment, candidate, impulse, liquidity, _, poi = valid_long_ob()
        assert assessment.evidence is not None
        raid = raid_from_structural_liquidity(liquidity, candidate)
        bearish = source_obj(
            SourceObjectType.STRUCTURE,
            name="bearish",
            known_minute=5,
            direction=Direction.SHORT.value,
        )
        result = assess_source_order_block(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            candidate=candidate,
            impulse=impulse,
            raid=raid,
            bos=BosReference(Direction.LONG, BASE + timedelta(minutes=13), "bos"),
            htf_poi=poi,
            structure=bearish,
            aggressive_impulse=q("aggressive"),
            large_body_small_wicks=q("body-wicks"),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "OB_NOT_ALIGNED_WITH_SOURCE_STRUCTURE")

    def test_future_touch_is_not_part_of_ob_identity_or_existence(self):
        a, *_ = valid_long_ob()
        b, *_ = valid_long_ob()
        assert a.evidence is not None and b.evidence is not None
        self.assertEqual(a.evidence.obj.object_id, b.evidence.obj.object_id)
        self.assertTrue(a.evidence.obj.formation_valid)
        self.assertFalse(a.evidence.obj.trade_eligible)


class SourceBreakerV2Tests(unittest.TestCase):
    def test_valid_breaker_descends_from_valid_ob_without_mutating_parent(self):
        ob_assessment, *_ = valid_long_ob()
        assert ob_assessment.evidence is not None
        parent = ob_assessment.evidence
        before_id = parent.obj.object_id
        breaker = assess_source_breaker(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            parent_ob=parent,
            break_candle=c(14, 98.0, 99.0, 93.0, 94.0),
            structure_shift=BosReference(Direction.SHORT, BASE + timedelta(minutes=16), "shift-short"),
            fast_impulse=q("fast", minute=15),
            continuous_no_ob_trading=q("continuous", minute=15),
            imbalance_present=True,
        )
        self.assertEqual(breaker.status, FormationStatus.PASS)
        assert breaker.evidence is not None
        self.assertEqual(breaker.evidence.direction, Direction.SHORT)
        self.assertEqual(breaker.evidence.parent_ob_id, before_id)
        self.assertEqual(breaker.evidence.obj.parent_object_ids, (before_id,))
        self.assertFalse(breaker.evidence.obj.trade_eligible)
        self.assertTrue(parent.obj.formation_valid)
        self.assertEqual(parent.obj.object_id, before_id)

    def test_wick_through_ob_without_close_beyond_zone_is_not_auto_breaker(self):
        ob_assessment, *_ = valid_long_ob()
        assert ob_assessment.evidence is not None
        result = assess_source_breaker(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            parent_ob=ob_assessment.evidence,
            break_candle=c(14, 98.0, 99.0, 94.0, 96.0),
            structure_shift=BosReference(Direction.SHORT, BASE + timedelta(minutes=16), "shift-short"),
            fast_impulse=q("fast", minute=15),
            continuous_no_ob_trading=q("continuous", minute=15),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "OB_NOT_BROKEN_BEYOND_ZONE")

    def test_breaker_fast_and_continuous_terms_are_qualitative_evidence(self):
        ob_assessment, *_ = valid_long_ob()
        assert ob_assessment.evidence is not None
        result = assess_source_breaker(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            parent_ob=ob_assessment.evidence,
            break_candle=c(14, 98.0, 99.0, 93.0, 94.0),
            structure_shift=BosReference(Direction.SHORT, BASE + timedelta(minutes=16), "shift-short"),
            fast_impulse=QualitativeEvidence(EvidenceStatus.UNKNOWN, None, BASE + timedelta(minutes=15)),
            continuous_no_ob_trading=q("continuous", minute=15),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_FAST_IMPULSE_QUALITATIVE_PROVENANCE")

    def test_higher_priority_method_requires_breaker_imbalance(self):
        ob_assessment, *_ = valid_long_ob()
        assert ob_assessment.evidence is not None
        result = assess_source_breaker(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            parent_ob=ob_assessment.evidence,
            break_candle=c(14, 98.0, 99.0, 93.0, 94.0),
            structure_shift=BosReference(Direction.SHORT, BASE + timedelta(minutes=16), "shift-short"),
            fast_impulse=q("fast", minute=15),
            continuous_no_ob_trading=q("continuous", minute=15),
            imbalance_present=False,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "METHOD_BREAKER_REQUIRES_IMBALANCE")

    def test_breaker_requires_structure_shift_in_break_direction(self):
        ob_assessment, *_ = valid_long_ob()
        assert ob_assessment.evidence is not None
        result = assess_source_breaker(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            parent_ob=ob_assessment.evidence,
            break_candle=c(14, 98.0, 99.0, 93.0, 94.0),
            structure_shift=BosReference(Direction.LONG, BASE + timedelta(minutes=16), "wrong-shift"),
            fast_impulse=q("fast", minute=15),
            continuous_no_ob_trading=q("continuous", minute=15),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "BREAKER_STRUCTURE_SHIFT_DIRECTION_MISMATCH")

    def test_source_invalid_parent_ob_cannot_form_breaker(self):
        ob_assessment, *_ = valid_long_ob()
        assert ob_assessment.evidence is not None
        invalid_obj = ob_assessment.evidence.obj.reject(
            RejectionCategory.OBJECT_INVALID_SOURCE,
            ob_assessment.evidence.obj.known_at,
            "test-invalid-parent",
        )
        invalid_parent = replace(ob_assessment.evidence, obj=invalid_obj)
        result = assess_source_breaker(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            parent_ob=invalid_parent,
            break_candle=c(14, 98.0, 99.0, 93.0, 94.0),
            structure_shift=BosReference(Direction.SHORT, BASE + timedelta(minutes=16), "shift-short"),
            fast_impulse=q("fast", minute=15),
            continuous_no_ob_trading=q("continuous", minute=15),
            imbalance_present=True,
        )
        self.assertEqual(result.status, FormationStatus.FAIL)
        self.assertEqual(result.reason, "PARENT_OB_SOURCE_INVALID")


if __name__ == "__main__":
    unittest.main()
