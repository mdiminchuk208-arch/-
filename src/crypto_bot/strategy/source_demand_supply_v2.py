from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_imb_ote_pd_v2 import PremiumDiscountEvidence, PremiumDiscountLocation
from crypto_bot.strategy.source_ob_breaker_v2 import QualitativeEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


class MovementDirection(str, Enum):
    RISING = "RISING"
    FALLING = "FALLING"


class DemandSupplyKind(str, Enum):
    DEMAND = "DEMAND"
    SUPPLY = "SUPPLY"


@dataclass(frozen=True)
class OldLiquidityRaidReference:
    parent_liquidity_id: str
    parent_known_at: datetime
    raid_known_at: datetime
    swept_side: str
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        if self.swept_side not in ("high", "low"):
            raise ValueError("swept_side must be high or low")
        _aware("parent_known_at", self.parent_known_at)
        _aware("raid_known_at", self.raid_known_at)
        if self.parent_known_at > self.raid_known_at:
            raise ValueError("old liquidity must be known before its raid")
        if not self.parent_liquidity_id or not self.evidence_id or not self.provenance:
            raise ValueError("raid reference requires parent id and provenance")


@dataclass(frozen=True)
class SourceMovementReference:
    """Causal, pre-qualified 'last movement' geometry for Demand/Supply.

    The secondary SOURCE allows one candle or several consecutive candles and
    does not provide a deterministic segmentation algorithm. Stage 6.5 therefore
    consumes auditable movement geometry instead of inventing a candle count,
    ATR threshold, or displacement rule.
    """

    direction: MovementDirection
    zone_low: float
    zone_high: float
    start_at: datetime
    known_at: datetime
    parent_object_ids: tuple[str, ...]
    evidence_id: str
    provenance: str
    last_movement_evidence: QualitativeEvidence

    def __post_init__(self) -> None:
        _positive("movement zone low", self.zone_low)
        _positive("movement zone high", self.zone_high)
        if self.zone_low >= self.zone_high:
            raise ValueError("movement zone must have positive width")
        _aware("movement start_at", self.start_at)
        _aware("movement known_at", self.known_at)
        if self.known_at < self.start_at:
            raise ValueError("movement cannot be known before it starts")
        if not self.parent_object_ids or not self.evidence_id or not self.provenance:
            raise ValueError("movement reference requires parent ids and provenance")
        if self.last_movement_evidence.status == EvidenceStatus.FAIL:
            raise ValueError("movement is explicitly not the SOURCE last movement")
        if not self.last_movement_evidence.provenance_ready:
            raise ValueError("last-movement geometry requires auditable qualitative provenance")
        if self.last_movement_evidence.known_at is not None and self.last_movement_evidence.known_at < self.start_at:
            raise ValueError("last-movement evidence cannot predate movement start")


@dataclass(frozen=True)
class SourceDemandSupplyEvidence:
    obj: CausalSourceObject
    kind: DemandSupplyKind
    direction: Direction
    zone_low: float
    zone_high: float
    movement_evidence_id: str
    raid_evidence_id: str


@dataclass(frozen=True)
class DemandSupplyFormationAssessment:
    status: EvidenceStatus
    reason: str
    evidence: SourceDemandSupplyEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == EvidenceStatus.PASS


@dataclass(frozen=True)
class DemandSupplyContextAssessment:
    status: EvidenceStatus
    reason: str
    direction: Direction
    premium_discount_location: PremiumDiscountLocation | None
    fresh: bool | None

    @property
    def eligible_context(self) -> bool:
        return self.status == EvidenceStatus.PASS


def form_source_demand_supply(
    *,
    symbol: str,
    timeframe: str | int,
    movement: SourceMovementReference,
    raid: OldLiquidityRaidReference,
) -> DemandSupplyFormationAssessment:
    """Form Demand/Supply object from the verified secondary SOURCE material.

    SOURCE:
    - Supply = last rising movement, one or several consecutive candles;
    - Demand = last falling movement, one or several consecutive candles;
    - the movement forming the zone must raid old liquidity.

    Premium/Discount and untested/fresh status are evaluated separately as
    context/admission facts so later testing cannot erase the historical object.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if raid.raid_known_at > movement.known_at:
        return DemandSupplyFormationAssessment(
            EvidenceStatus.FAIL,
            "LIQUIDITY_RAID_OCCURS_AFTER_ZONE_FORMING_MOVEMENT",
        )

    if movement.direction == MovementDirection.FALLING:
        kind = DemandSupplyKind.DEMAND
        direction = Direction.LONG
        expected_side = "low"
    else:
        kind = DemandSupplyKind.SUPPLY
        direction = Direction.SHORT
        expected_side = "high"

    if raid.swept_side != expected_side:
        return DemandSupplyFormationAssessment(
            EvidenceStatus.FAIL,
            "RAID_SIDE_DOES_NOT_MATCH_DEMAND_SUPPLY_DIRECTION",
        )

    known_at = max(
        movement.known_at,
        raid.raid_known_at,
        movement.last_movement_evidence.known_at,  # type: ignore[arg-type]
    )
    parent_ids = tuple(dict.fromkeys(movement.parent_object_ids + (raid.parent_liquidity_id,)))
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.POI,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction.value,
        formation_at=movement.known_at,
        known_at=known_at,
        identity_parts={
            "poi_kind": kind.value,
            "direction": direction.value,
            "movement_evidence_id": movement.evidence_id,
            "raid_evidence_id": raid.evidence_id,
            "zone_low": movement.zone_low,
            "zone_high": movement.zone_high,
            "movement_start_at": movement.start_at,
        },
        source_rule_ids=(
            "DS_LAST_MOVEMENT_001",
            "DS_OLD_LIQUIDITY_RAID_001",
        ),
        technical_normalization_ids=("TN_DS_QUALITATIVE_MOVEMENT_PROVENANCE",),
        parent_object_ids=parent_ids,
        provenance=(
            "Verified secondary source material 'Зоны спроса и предложения Demand and Supply': "
            "last rising/falling movement plus mandatory old-liquidity raid; exact one-vs-multi-candle "
            "segmentation is supplied as qualitative evidence, not invented"
        ),
    )
    evidence = SourceDemandSupplyEvidence(
        obj=obj,
        kind=kind,
        direction=direction,
        zone_low=movement.zone_low,
        zone_high=movement.zone_high,
        movement_evidence_id=movement.evidence_id,
        raid_evidence_id=raid.evidence_id,
    )
    return DemandSupplyFormationAssessment(EvidenceStatus.PASS, "SOURCE_DEMAND_SUPPLY_FORMED", evidence)


def assess_demand_supply_context(
    zone: SourceDemandSupplyEvidence,
    *,
    premium_discount: PremiumDiscountEvidence | None,
    decision_at: datetime,
    first_test_at: datetime | None,
) -> DemandSupplyContextAssessment:
    """Evaluate D/S freshness + Premium/Discount without rewriting object history.

    SOURCE says Supply is valid for sales in Premium, Demand for buys in
    Discount, and D/S zones are untested. These are contextual eligibility facts;
    the already-formed market object remains historically valid after a later test.
    """
    _aware("decision_at", decision_at)
    if decision_at < zone.obj.known_at:
        raise ValueError("cannot assess Demand/Supply before object known_at")
    if first_test_at is not None:
        _aware("first_test_at", first_test_at)
        if first_test_at < zone.obj.known_at:
            raise ValueError("first_test_at cannot precede zone known_at")
        if first_test_at <= decision_at:
            return DemandSupplyContextAssessment(
                EvidenceStatus.FAIL,
                "ZONE_ALREADY_TESTED_NOT_FRESH",
                zone.direction,
                premium_discount.location if premium_discount else None,
                False,
            )

    if premium_discount is None:
        return DemandSupplyContextAssessment(
            EvidenceStatus.UNKNOWN,
            "WAIT_PREMIUM_DISCOUNT_CONTEXT",
            zone.direction,
            None,
            True,
        )
    if premium_discount.known_at > decision_at:
        return DemandSupplyContextAssessment(
            EvidenceStatus.UNKNOWN,
            "PREMIUM_DISCOUNT_NOT_YET_KNOWN",
            zone.direction,
            premium_discount.location,
            True,
        )

    expected = (
        PremiumDiscountLocation.DISCOUNT
        if zone.kind == DemandSupplyKind.DEMAND
        else PremiumDiscountLocation.PREMIUM
    )
    if premium_discount.location != expected:
        return DemandSupplyContextAssessment(
            EvidenceStatus.FAIL,
            "DEMAND_SUPPLY_WRONG_PREMIUM_DISCOUNT_SIDE",
            zone.direction,
            premium_discount.location,
            True,
        )
    return DemandSupplyContextAssessment(
        EvidenceStatus.PASS,
        "SOURCE_DEMAND_SUPPLY_CONTEXT_ELIGIBLE",
        zone.direction,
        premium_discount.location,
        True,
    )


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
