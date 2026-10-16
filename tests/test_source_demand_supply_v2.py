from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.strategy.source_demand_supply_v2 import (
    DemandSupplyKind,
    MovementDirection,
    OldLiquidityRaidReference,
    SourceMovementReference,
    assess_demand_supply_context,
    form_source_demand_supply,
)
from crypto_bot.strategy.source_imb_ote_pd_v2 import PremiumDiscountEvidence, PremiumDiscountLocation
from crypto_bot.strategy.source_ob_breaker_v2 import QualitativeEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


BASE = datetime(2026, 7, 1, tzinfo=timezone.utc)


def q(status: EvidenceStatus = EvidenceStatus.PASS, minute: int = 10) -> QualitativeEvidence:
    return QualitativeEvidence(
        status=status,
        evidence_id="last-movement-proof" if status == EvidenceStatus.PASS else None,
        known_at=BASE + timedelta(minutes=minute),
    )


def movement(direction: MovementDirection, *, quality: EvidenceStatus = EvidenceStatus.PASS) -> SourceMovementReference:
    return SourceMovementReference(
        direction=direction,
        zone_low=95.0,
        zone_high=105.0,
        start_at=BASE + timedelta(minutes=5),
        known_at=BASE + timedelta(minutes=10),
        parent_object_ids=("movement-parent",),
        evidence_id=f"movement-{direction.value}",
        provenance="blinded last-movement geometry fixture",
        last_movement_evidence=q(quality, 10),
    )


def raid(side: str, *, minute: int = 9) -> OldLiquidityRaidReference:
    return OldLiquidityRaidReference(
        parent_liquidity_id=f"old-liquidity-{side}",
        parent_known_at=BASE + timedelta(minutes=1),
        raid_known_at=BASE + timedelta(minutes=minute),
        swept_side=side,
        evidence_id=f"raid-{side}-{minute}",
        provenance="causal old-liquidity raid fixture",
    )


def pd(location: PremiumDiscountLocation, *, minute: int = 12) -> PremiumDiscountEvidence:
    return PremiumDiscountEvidence(
        location=location,
        price=100.0,
        equilibrium=100.0,
        dealing_range_evidence_id="dealing-range",
        known_at=BASE + timedelta(minutes=minute),
    )


class DemandSupplyFormationTests(unittest.TestCase):
    def test_falling_last_movement_plus_low_raid_forms_demand(self):
        result = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.FALLING),
            raid=raid("low"),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        e = result.evidence
        self.assertEqual(e.kind, DemandSupplyKind.DEMAND)
        self.assertEqual(e.direction, Direction.LONG)
        self.assertEqual((e.zone_low, e.zone_high), (95.0, 105.0))
        self.assertTrue(e.obj.formation_valid)
        self.assertFalse(e.obj.trade_eligible)
        self.assertIn("DS_LAST_MOVEMENT_001", e.obj.source_rule_ids)
        self.assertIn("DS_OLD_LIQUIDITY_RAID_001", e.obj.source_rule_ids)

    def test_rising_last_movement_plus_high_raid_forms_supply(self):
        result = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.RISING),
            raid=raid("high"),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.evidence is not None
        self.assertEqual(result.evidence.kind, DemandSupplyKind.SUPPLY)
        self.assertEqual(result.evidence.direction, Direction.SHORT)

    def test_wrong_raid_side_fails_directional_source_rule(self):
        result = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.FALLING),
            raid=raid("high"),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "RAID_SIDE_DOES_NOT_MATCH_DEMAND_SUPPLY_DIRECTION")

    def test_raid_after_forming_movement_cannot_retroactively_create_zone(self):
        result = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.FALLING),
            raid=raid("low", minute=11),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "LIQUIDITY_RAID_OCCURS_AFTER_ZONE_FORMING_MOVEMENT")

    def test_unknown_last_movement_geometry_stays_unknown(self):
        result = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.FALLING, quality=EvidenceStatus.UNKNOWN),
            raid=raid("low"),
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_LAST_MOVEMENT_QUALITATIVE_PROVENANCE")
        self.assertIsNone(result.evidence)

    def test_failed_last_movement_geometry_is_fail_not_candidate_promotion(self):
        result = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.FALLING, quality=EvidenceStatus.FAIL),
            raid=raid("low"),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "LAST_MOVEMENT_SOURCE_GEOMETRY_FAILED")


class DemandSupplyContextTests(unittest.TestCase):
    def demand(self):
        formed = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.FALLING),
            raid=raid("low"),
        )
        assert formed.evidence is not None
        return formed.evidence

    def supply(self):
        formed = form_source_demand_supply(
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            movement=movement(MovementDirection.RISING),
            raid=raid("high"),
        )
        assert formed.evidence is not None
        return formed.evidence

    def test_demand_requires_discount_for_context_eligibility(self):
        zone = self.demand()
        result = assess_demand_supply_context(
            zone,
            premium_discount=pd(PremiumDiscountLocation.DISCOUNT),
            decision_at=BASE + timedelta(minutes=12),
            first_test_at=None,
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        self.assertTrue(result.eligible_context)

    def test_supply_requires_premium_for_context_eligibility(self):
        zone = self.supply()
        result = assess_demand_supply_context(
            zone,
            premium_discount=pd(PremiumDiscountLocation.PREMIUM),
            decision_at=BASE + timedelta(minutes=12),
            first_test_at=None,
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)

    def test_wrong_premium_discount_side_rejects_context_not_object(self):
        zone = self.demand()
        original_id = zone.obj.object_id
        result = assess_demand_supply_context(
            zone,
            premium_discount=pd(PremiumDiscountLocation.PREMIUM),
            decision_at=BASE + timedelta(minutes=12),
            first_test_at=None,
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "DEMAND_SUPPLY_WRONG_PREMIUM_DISCOUNT_SIDE")
        self.assertEqual(zone.obj.object_id, original_id)
        self.assertTrue(zone.obj.formation_valid)

    def test_missing_pd_context_stays_unknown(self):
        zone = self.demand()
        result = assess_demand_supply_context(
            zone,
            premium_discount=None,
            decision_at=BASE + timedelta(minutes=12),
            first_test_at=None,
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_PREMIUM_DISCOUNT_CONTEXT")

    def test_future_pd_context_cannot_be_used_early(self):
        zone = self.demand()
        result = assess_demand_supply_context(
            zone,
            premium_discount=pd(PremiumDiscountLocation.DISCOUNT, minute=15),
            decision_at=BASE + timedelta(minutes=12),
            first_test_at=None,
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "PREMIUM_DISCOUNT_NOT_YET_KNOWN")

    def test_first_test_removes_fresh_context_but_not_historical_object(self):
        zone = self.demand()
        original_id = zone.obj.object_id
        result = assess_demand_supply_context(
            zone,
            premium_discount=pd(PremiumDiscountLocation.DISCOUNT),
            decision_at=BASE + timedelta(minutes=14),
            first_test_at=BASE + timedelta(minutes=13),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "ZONE_ALREADY_TESTED_NOT_FRESH")
        self.assertFalse(result.fresh)
        self.assertEqual(zone.obj.object_id, original_id)
        self.assertTrue(zone.obj.formation_valid)

    def test_equilibrium_is_not_supply_premium_or_demand_discount(self):
        zone = self.demand()
        result = assess_demand_supply_context(
            zone,
            premium_discount=pd(PremiumDiscountLocation.EQUILIBRIUM),
            decision_at=BASE + timedelta(minutes=12),
            first_test_at=None,
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "DEMAND_SUPPLY_WRONG_PREMIUM_DISCOUNT_SIDE")


if __name__ == "__main__":
    unittest.main()
