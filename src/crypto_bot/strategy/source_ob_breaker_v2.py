from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus, StructuralLiquidityEvidence


class FormationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class QualitativeEvidence:
    """Blinded/source-geometry evidence for a qualitative SOURCE term.

    The SOURCE uses words such as aggressive, fast, whole and small/large
    without a numeric threshold. Stage 4 therefore requires auditable evidence
    rather than silently inventing ATR/percent/body-ratio constants.
    """

    status: EvidenceStatus
    evidence_id: str | None
    known_at: datetime | None

    def __post_init__(self) -> None:
        if self.known_at is not None and (self.known_at.tzinfo is None or self.known_at.utcoffset() is None):
            raise ValueError("qualitative evidence known_at must be timezone-aware")

    @property
    def provenance_ready(self) -> bool:
        return self.status == EvidenceStatus.PASS and bool(self.evidence_id) and self.known_at is not None


@dataclass(frozen=True)
class BosReference:
    direction: Direction
    known_at: datetime
    evidence_id: str
    kind: str = "BOS"

    def __post_init__(self) -> None:
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ValueError("BOS known_at must be timezone-aware")
        if not self.evidence_id:
            raise ValueError("BOS evidence_id is required")


@dataclass(frozen=True)
class ObRaidReference:
    parent_liquidity_id: str
    side: str
    level_price: float
    parent_known_at: datetime
    sweep_open_time: datetime
    sweep_close_time: datetime
    extreme_price: float

    def __post_init__(self) -> None:
        if self.side not in ("high", "low"):
            raise ValueError("raid side must be high or low")
        if not isfinite(self.level_price) or self.level_price <= 0:
            raise ValueError("level price must be finite and positive")
        if not self.parent_liquidity_id:
            raise ValueError("parent liquidity id is required")


@dataclass(frozen=True)
class SourceOrderBlockEvidence:
    obj: CausalSourceObject
    direction: Direction
    zone_low: float
    zone_high: float
    candidate_open_time: datetime
    candidate_close_time: datetime
    impulse_close_time: datetime
    raid_parent_id: str
    htf_poi_parent_id: str
    structure_parent_id: str
    bos_evidence_id: str
    imbalance_present: bool


@dataclass(frozen=True)
class OrderBlockAssessment:
    status: FormationStatus
    reason: str
    evidence: SourceOrderBlockEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == FormationStatus.PASS


@dataclass(frozen=True)
class SourceBreakerEvidence:
    obj: CausalSourceObject
    direction: Direction
    zone_low: float
    zone_high: float
    parent_ob_id: str
    break_close_time: datetime
    structure_shift_evidence_id: str


@dataclass(frozen=True)
class BreakerAssessment:
    status: FormationStatus
    reason: str
    evidence: SourceBreakerEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == FormationStatus.PASS


def raid_from_structural_liquidity(
    pool: StructuralLiquidityEvidence,
    sweep_candle: Candle,
) -> ObRaidReference | None:
    """Build the OB-candle liquidity raid reference causally.

    SW9 p2 says the OB candle itself swept liquidity. The machine uses strict
    wick penetration as the inherited Stage-2 TECHNICAL_NORMALIZATION.
    """
    if not sweep_candle.is_closed:
        raise ValueError("OB raid requires a closed sweep candle")
    if pool.obj.known_at > sweep_candle.open_time:
        return None
    swept = sweep_candle.high > pool.price if pool.side == "high" else sweep_candle.low < pool.price
    if not swept:
        return None
    return ObRaidReference(
        parent_liquidity_id=pool.obj.object_id,
        side=pool.side,
        level_price=pool.price,
        parent_known_at=pool.obj.known_at,
        sweep_open_time=sweep_candle.open_time,
        sweep_close_time=sweep_candle.close_time,
        extreme_price=sweep_candle.high if pool.side == "high" else sweep_candle.low,
    )


def body_engulfs_candidate(candidate: Candle, impulse: Candle, direction: Direction) -> bool:
    """Deterministic representation of SW9 p2 'impulse overlaps prior candle'.

    Exact body-engulf geometry is TECHNICAL_NORMALIZATION; SOURCE does not give
    a numeric displacement threshold.
    """
    if not candidate.is_closed or not impulse.is_closed:
        raise ValueError("engulf geometry requires closed candles")
    if candidate.close_time != impulse.open_time:
        return False
    impulse_direction_ok = impulse.close > impulse.open if direction == Direction.LONG else impulse.close < impulse.open
    candidate_body_low = min(candidate.open, candidate.close)
    candidate_body_high = max(candidate.open, candidate.close)
    impulse_body_low = min(impulse.open, impulse.close)
    impulse_body_high = max(impulse.open, impulse.close)
    return (
        impulse_direction_ok
        and impulse_body_low <= candidate_body_low
        and impulse_body_high >= candidate_body_high
    )


def assess_source_order_block(
    *,
    symbol: str,
    timeframe: str | int,
    candidate: Candle,
    impulse: Candle,
    raid: ObRaidReference | None,
    bos: BosReference,
    htf_poi: CausalSourceObject,
    structure: CausalSourceObject,
    aggressive_impulse: QualitativeEvidence,
    large_body_small_wicks: QualitativeEvidence,
    imbalance_present: bool | None,
) -> OrderBlockAssessment:
    """Assess clean SOURCE OB object formation, never trade admission.

    Intersection that is unambiguous across Методичка and SW9:
    - the OB candidate candle swept already-known liquidity;
    - the following directional impulse engulfs/overlaps the candidate;
    - the move receives BOS confirmation;
    - the formation is in an already-known HTF POI and structural impulse/trend;
    - zone geometry is the whole candidate candle including wicks.

    The IMB hard-vs-soft conflict is not invented away. Методичка describes OB
    as the last candle before imbalance, while SW9 p2 says IMB gives the most
    accurate signal. If IMB is absent/unknown Stage 4 returns UNKNOWN rather
    than promoting or deleting the candidate.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if not candidate.is_closed or not impulse.is_closed:
        return OrderBlockAssessment(FormationStatus.FAIL, "CANDIDATE_OR_IMPULSE_NOT_CLOSED")
    if candidate.close_time != impulse.open_time:
        return OrderBlockAssessment(FormationStatus.FAIL, "IMPULSE_NOT_IMMEDIATE_AFTER_CANDIDATE")
    if raid is None:
        return OrderBlockAssessment(FormationStatus.FAIL, "OB_CANDLE_DID_NOT_CAUSALLY_SWEEP_LIQUIDITY")
    if raid.sweep_open_time != candidate.open_time or raid.sweep_close_time != candidate.close_time:
        return OrderBlockAssessment(FormationStatus.FAIL, "RAID_NOT_PERFORMED_BY_OB_CANDIDATE_CANDLE")

    direction = Direction.LONG if raid.side == "low" else Direction.SHORT
    if not body_engulfs_candidate(candidate, impulse, direction):
        return OrderBlockAssessment(FormationStatus.FAIL, "IMPULSE_DOES_NOT_ENGULF_CANDIDATE")

    qualitative = (
        ("AGGRESSIVE_IMPULSE", aggressive_impulse),
        ("LARGE_BODY_SMALL_WICKS", large_body_small_wicks),
    )
    for name, evidence in qualitative:
        if evidence.status == EvidenceStatus.FAIL:
            return OrderBlockAssessment(FormationStatus.FAIL, f"{name}_SOURCE_GEOMETRY_FAILED")
        if not evidence.provenance_ready:
            return OrderBlockAssessment(FormationStatus.UNKNOWN, f"WAIT_{name}_QUALITATIVE_PROVENANCE")

    if bos.direction != direction:
        return OrderBlockAssessment(FormationStatus.FAIL, "BOS_DIRECTION_MISMATCH")
    if bos.known_at < impulse.close_time:
        return OrderBlockAssessment(FormationStatus.FAIL, "BOS_KNOWN_BEFORE_IMPULSE_COMPLETED")

    if htf_poi.object_type not in {
        SourceObjectType.POI,
        SourceObjectType.ORDER_BLOCK,
        SourceObjectType.BREAKER,
        SourceObjectType.FVG,
        SourceObjectType.RANGE,
    }:
        return OrderBlockAssessment(FormationStatus.FAIL, "INVALID_HTF_POI_PARENT_TYPE")
    if not htf_poi.formation_valid:
        return OrderBlockAssessment(FormationStatus.FAIL, "HTF_POI_SOURCE_INVALID")
    if htf_poi.known_at > candidate.open_time:
        return OrderBlockAssessment(FormationStatus.FAIL, "HTF_POI_NOT_KNOWN_BEFORE_OB_FORMATION")

    if structure.object_type != SourceObjectType.STRUCTURE or not structure.formation_valid:
        return OrderBlockAssessment(FormationStatus.FAIL, "STRUCTURE_PARENT_INVALID")
    if structure.known_at > candidate.open_time:
        return OrderBlockAssessment(FormationStatus.FAIL, "STRUCTURE_NOT_KNOWN_BEFORE_OB_FORMATION")
    expected_structure_direction = Direction.LONG.value if direction == Direction.LONG else Direction.SHORT.value
    if structure.direction != expected_structure_direction:
        return OrderBlockAssessment(FormationStatus.FAIL, "OB_NOT_ALIGNED_WITH_SOURCE_STRUCTURE")

    latest_qualitative_time = max(
        aggressive_impulse.known_at,  # type: ignore[arg-type]
        large_body_small_wicks.known_at,  # type: ignore[arg-type]
    )
    known_at = max(bos.known_at, latest_qualitative_time)

    if imbalance_present is not True:
        return OrderBlockAssessment(
            FormationStatus.UNKNOWN,
            "SOURCE_CONFLICT_OB_IMB_HARD_VS_QUALITY_UNRESOLVED",
        )

    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.ORDER_BLOCK,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction.value,
        formation_at=impulse.close_time,
        known_at=known_at,
        identity_parts={
            "direction": direction.value,
            "candidate_open_time": candidate.open_time,
            "candidate_close_time": candidate.close_time,
            "zone_low": candidate.low,
            "zone_high": candidate.high,
            "raid_parent_id": raid.parent_liquidity_id,
            "bos_evidence_id": bos.evidence_id,
        },
        source_rule_ids=(
            "OB_RAID_CANDLE_001",
            "OB_ENGULF_IMPULSE_001",
            "OB_BOS_CONFIRMATION_001",
            "OB_HTF_POI_CONTEXT_001",
            "OB_STRUCTURAL_IMPULSE_TREND_001",
            "OB_WHOLE_CANDLE_ZONE_001",
        ),
        technical_normalization_ids=(
            "LIQ_STRICT_WICK_TAKE_V2",
            "TN_OB_DIRECTION_FROM_RAID_SIDE",
            "TN_OB_BODY_ENGULF_GEOMETRY",
            "TN_OB_QUALITATIVE_EVIDENCE_PROVENANCE",
        ),
        parent_object_ids=(
            raid.parent_liquidity_id,
            htf_poi.object_id,
            structure.object_id,
        ),
        provenance=(
            "Методичка p9-10 + SW9 p2-3; whole candidate candle including wicks; "
            "qualitative geometry supplied by auditable evidence; trade admission/test policy deferred"
        ),
    )
    evidence = SourceOrderBlockEvidence(
        obj=obj,
        direction=direction,
        zone_low=candidate.low,
        zone_high=candidate.high,
        candidate_open_time=candidate.open_time,
        candidate_close_time=candidate.close_time,
        impulse_close_time=impulse.close_time,
        raid_parent_id=raid.parent_liquidity_id,
        htf_poi_parent_id=htf_poi.object_id,
        structure_parent_id=structure.object_id,
        bos_evidence_id=bos.evidence_id,
        imbalance_present=True,
    )
    return OrderBlockAssessment(FormationStatus.PASS, "SOURCE_OB_FORMED", evidence)


def assess_source_breaker(
    *,
    symbol: str,
    timeframe: str | int,
    parent_ob: SourceOrderBlockEvidence,
    break_candle: Candle,
    structure_shift: BosReference,
    fast_impulse: QualitativeEvidence,
    continuous_no_ob_trading: QualitativeEvidence,
    imbalance_present: bool,
) -> BreakerAssessment:
    """Assess a clean Breaker as a descendant of an already-valid OB.

    SW9 p7: Breaker is an OB broken by a fast, whole impulsive move without
    trading in the OB area and associated with structural update/BOS.
    Методичка p12 additionally says the break must be through imbalance and be
    followed by CHOCH. Because Методичка has higher SOURCE priority, Stage 4
    requires imbalance plus a later structure-shift reference, while keeping the
    qualitative impulse terms provenance-based rather than numeric.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if not parent_ob.obj.formation_valid:
        return BreakerAssessment(FormationStatus.FAIL, "PARENT_OB_SOURCE_INVALID")
    if not break_candle.is_closed:
        return BreakerAssessment(FormationStatus.FAIL, "BREAKER_IMPULSE_CANDLE_NOT_CLOSED")
    if break_candle.open_time < parent_ob.obj.known_at:
        return BreakerAssessment(FormationStatus.FAIL, "BREAKER_BREAK_PRECEDES_KNOWN_PARENT_OB")

    direction = Direction.SHORT if parent_ob.direction == Direction.LONG else Direction.LONG
    close_breaks_zone = (
        break_candle.close < parent_ob.zone_low
        if direction == Direction.SHORT
        else break_candle.close > parent_ob.zone_high
    )
    if not close_breaks_zone:
        return BreakerAssessment(FormationStatus.FAIL, "OB_NOT_BROKEN_BEYOND_ZONE")

    for name, evidence in (
        ("FAST_IMPULSE", fast_impulse),
        ("CONTINUOUS_NO_OB_TRADING", continuous_no_ob_trading),
    ):
        if evidence.status == EvidenceStatus.FAIL:
            return BreakerAssessment(FormationStatus.FAIL, f"{name}_SOURCE_GEOMETRY_FAILED")
        if not evidence.provenance_ready:
            return BreakerAssessment(FormationStatus.UNKNOWN, f"WAIT_{name}_QUALITATIVE_PROVENANCE")

    if not imbalance_present:
        return BreakerAssessment(FormationStatus.FAIL, "METHOD_BREAKER_REQUIRES_IMBALANCE")
    if structure_shift.direction != direction:
        return BreakerAssessment(FormationStatus.FAIL, "BREAKER_STRUCTURE_SHIFT_DIRECTION_MISMATCH")
    if structure_shift.known_at < break_candle.close_time:
        return BreakerAssessment(FormationStatus.FAIL, "STRUCTURE_SHIFT_PRECEDES_BREAK_COMPLETION")

    known_at = max(
        structure_shift.known_at,
        fast_impulse.known_at,  # type: ignore[arg-type]
        continuous_no_ob_trading.known_at,  # type: ignore[arg-type]
    )
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.BREAKER,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction.value,
        formation_at=break_candle.close_time,
        known_at=known_at,
        identity_parts={
            "direction": direction.value,
            "parent_ob_id": parent_ob.obj.object_id,
            "break_open_time": break_candle.open_time,
            "break_close_time": break_candle.close_time,
            "zone_low": parent_ob.zone_low,
            "zone_high": parent_ob.zone_high,
            "structure_evidence_id": structure_shift.evidence_id,
        },
        source_rule_ids=(
            "BREAKER_PARENT_OB_001",
            "BREAKER_FAST_WHOLE_IMPULSE_001",
            "BREAKER_STRUCTURE_UPDATE_001",
            "BREAKER_METHOD_IMB_SHIFT_001",
        ),
        technical_normalization_ids=(
            "TN_BREAKER_CLOSE_BEYOND_OB_ZONE",
            "TN_BREAKER_QUALITATIVE_EVIDENCE_PROVENANCE",
        ),
        parent_object_ids=(parent_ob.obj.object_id,),
        provenance=(
            "SW9 p7-9 + higher-priority Методичка p12; valid parent OB preserved; "
            "Breaker is a later descendant object, never a retroactive mutation of the OB"
        ),
    )
    evidence = SourceBreakerEvidence(
        obj=obj,
        direction=direction,
        zone_low=parent_ob.zone_low,
        zone_high=parent_ob.zone_high,
        parent_ob_id=parent_ob.obj.object_id,
        break_close_time=break_candle.close_time,
        structure_shift_evidence_id=structure_shift.evidence_id,
    )
    return BreakerAssessment(FormationStatus.PASS, "SOURCE_BREAKER_FORMED", evidence)
