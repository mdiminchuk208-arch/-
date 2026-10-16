from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    LiquidityLocation,
    StructuralLiquidityEvidence,
)


class SfpOrigin(str, Enum):
    STRUCTURAL_LIQUIDITY = "STRUCTURAL_LIQUIDITY"
    RANGE_BOUNDARY = "RANGE_BOUNDARY"


class SfpFormationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class SfpLiquidityReference:
    """Already-known external liquidity that an SFP is allowed to sweep."""

    parent_object_id: str
    parent_object_type: SourceObjectType
    side: str
    price: float
    known_at: datetime
    origin: SfpOrigin

    def __post_init__(self) -> None:
        if self.side not in ("high", "low"):
            raise ValueError("liquidity side must be high or low")
        if not isfinite(self.price) or self.price <= 0:
            raise ValueError("liquidity price must be finite and positive")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ValueError("liquidity known_at must be timezone-aware")
        if not self.parent_object_id:
            raise ValueError("parent_object_id is required")

    @classmethod
    def from_structural_liquidity(cls, pool: StructuralLiquidityEvidence) -> "SfpLiquidityReference":
        if pool.location != LiquidityLocation.EXTERNAL:
            raise ValueError("SFP requires external liquidity; internal pool is not valid here")
        if not pool.obj.formation_valid:
            raise ValueError("source-invalid liquidity cannot anchor SFP")
        return cls(
            parent_object_id=pool.obj.object_id,
            parent_object_type=pool.obj.object_type,
            side=pool.side,
            price=pool.price,
            known_at=pool.obj.known_at,
            origin=SfpOrigin.STRUCTURAL_LIQUIDITY,
        )

    @classmethod
    def from_range_boundary(
        cls,
        range_obj: CausalSourceObject,
        *,
        side: str,
        price: float,
    ) -> "SfpLiquidityReference":
        if range_obj.object_type != SourceObjectType.RANGE:
            raise ValueError("range boundary reference requires a RANGE parent object")
        if not range_obj.formation_valid:
            raise ValueError("source-invalid range cannot anchor SFP")
        return cls(
            parent_object_id=range_obj.object_id,
            parent_object_type=range_obj.object_type,
            side=side,
            price=price,
            known_at=range_obj.known_at,
            origin=SfpOrigin.RANGE_BOUNDARY,
        )


@dataclass(frozen=True)
class SourceSfpEvidence:
    obj: CausalSourceObject
    direction: Direction
    origin: SfpOrigin
    parent_liquidity_id: str
    swept_side: str
    liquidity_price: float
    sweep_open_time: datetime
    sweep_close_time: datetime
    confirmation_open_time: datetime
    pattern_extreme: float

    @property
    def requires_ltf_bos(self) -> bool:
        """SOURCE chain requirement after SFP formation; not object-validity logic."""
        return True


@dataclass(frozen=True)
class SfpFormationAssessment:
    status: SfpFormationStatus
    reason: str
    evidence: SourceSfpEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == SfpFormationStatus.PASS


def detect_source_sfp(
    sweep: Candle,
    next_candle: Candle,
    liquidity: SfpLiquidityReference,
    *,
    symbol: str,
    timeframe: str | int,
) -> SfpFormationAssessment:
    """Detect a clean SOURCE SFP formation without entry-chain contamination.

    SOURCE formation sequence (SW8 p5):
    1. already-known external liquidity at a structural swing or range boundary;
    2. sweep/false break of that level;
    3. sweep candle body closes back inside;
    4. the immediate next candle opens back inside;
    5. only after formation may a lower-TF BOS be sought.

    The next candle does not need to be closed because only its opening fact is
    used. Its future H/L/C values are deliberately ignored.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if not sweep.is_closed:
        return SfpFormationAssessment(SfpFormationStatus.FAIL, "SWEEP_CANDLE_NOT_CLOSED")
    if liquidity.known_at > sweep.open_time:
        return SfpFormationAssessment(
            SfpFormationStatus.FAIL,
            "LIQUIDITY_NOT_KNOWN_BEFORE_SWEEP",
        )
    if next_candle.open_time != sweep.close_time:
        return SfpFormationAssessment(
            SfpFormationStatus.FAIL,
            "IMMEDIATE_NEXT_CANDLE_OPEN_UNAVAILABLE",
        )

    if liquidity.side == "high":
        swept = sweep.high > liquidity.price
        closed_inside = sweep.close < liquidity.price
        next_open_inside = next_candle.open < liquidity.price
        direction = Direction.SHORT
        pattern_extreme = sweep.high
    else:
        swept = sweep.low < liquidity.price
        closed_inside = sweep.close > liquidity.price
        next_open_inside = next_candle.open > liquidity.price
        direction = Direction.LONG
        pattern_extreme = sweep.low

    if not swept:
        return SfpFormationAssessment(SfpFormationStatus.FAIL, "EXTERNAL_LIQUIDITY_NOT_SWEPT")
    if not closed_inside:
        return SfpFormationAssessment(SfpFormationStatus.FAIL, "SWEEP_BODY_DID_NOT_CLOSE_BACK_INSIDE")
    if not next_open_inside:
        return SfpFormationAssessment(SfpFormationStatus.FAIL, "NEXT_CANDLE_DID_NOT_OPEN_INSIDE")

    formation_at = next_candle.open_time
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.SFP,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction.value,
        formation_at=formation_at,
        known_at=formation_at,
        identity_parts={
            "parent_liquidity_id": liquidity.parent_object_id,
            "level_price": liquidity.price,
            "swept_side": liquidity.side,
            "sweep_open_time": sweep.open_time,
        },
        source_rule_ids=(
            "SFP_EXTERNAL_LIQUIDITY_001",
            "SFP_RECLAIM_CLOSE_001",
            "SFP_NEXT_OPEN_001",
        ),
        technical_normalization_ids=(
            "LIQ_STRICT_WICK_TAKE_V2",
            "TN_SFP_PARENT_KNOWN_BEFORE_SWEEP",
            "TN_SFP_PATTERN_EXTREME_SWEEP_CANDLE",
        ),
        parent_object_ids=(liquidity.parent_object_id,),
        provenance=(
            "SW8 p5 SFP formation from already-known external liquidity; "
            "strict penetration and parent-known timing are explicit causal normalizations; "
            "sweep-candle extreme is retained only as the invalidation-anchor normalization"
        ),
    )
    evidence = SourceSfpEvidence(
        obj=obj,
        direction=direction,
        origin=liquidity.origin,
        parent_liquidity_id=liquidity.parent_object_id,
        swept_side=liquidity.side,
        liquidity_price=liquidity.price,
        sweep_open_time=sweep.open_time,
        sweep_close_time=sweep.close_time,
        confirmation_open_time=next_candle.open_time,
        pattern_extreme=pattern_extreme,
    )
    return SfpFormationAssessment(SfpFormationStatus.PASS, "SOURCE_SFP_FORMED", evidence)


def sfp_invalidated_by_body_close(evidence: SourceSfpEvidence, candle: Candle) -> bool:
    """Return SOURCE invalidation fact using only a completed later candle.

    SOURCE (SW12 p13): body close beyond the SFP pattern minimum/maximum makes
    the pattern irrelevant. The machine maps that min/max to the completed
    sweep-candle extreme as TECHNICAL_NORMALIZATION.
    """
    if not candle.is_closed:
        raise ValueError("SFP invalidation requires a closed candle")
    if candle.close_time <= evidence.obj.known_at:
        raise ValueError("invalidation candle must close after SFP became known")
    if evidence.direction == Direction.LONG:
        return candle.close < evidence.pattern_extreme
    return candle.close > evidence.pattern_extreme


def apply_sfp_invalidation(evidence: SourceSfpEvidence, candle: Candle) -> SourceSfpEvidence:
    """Append invalidation without rewriting the historical SFP formation fact."""
    if evidence.obj.invalidated_at is not None:
        return evidence
    if not sfp_invalidated_by_body_close(evidence, candle):
        return evidence
    obj = evidence.obj.invalidate(
        candle.close_time,
        "SOURCE_SFP_BODY_CLOSE_BEYOND_PATTERN_EXTREME",
    )
    return SourceSfpEvidence(
        obj=obj,
        direction=evidence.direction,
        origin=evidence.origin,
        parent_liquidity_id=evidence.parent_liquidity_id,
        swept_side=evidence.swept_side,
        liquidity_price=evidence.liquidity_price,
        sweep_open_time=evidence.sweep_open_time,
        sweep_close_time=evidence.sweep_close_time,
        confirmation_open_time=evidence.confirmation_open_time,
        pattern_extreme=evidence.pattern_extreme,
    )


def directions_are_ambiguous_for_same_formation(formations: tuple[SourceSfpEvidence, ...]) -> bool:
    """Flag dual-sided same-time SFPs without deleting either valid object.

    SOURCE does not define how to choose between simultaneous opposite SFP
    directions. Object formation is preserved; later setup admission must WAIT.
    """
    by_time: dict[datetime, set[Direction]] = {}
    for formation in formations:
        by_time.setdefault(formation.obj.known_at, set()).add(formation.direction)
    return any(len(directions) > 1 for directions in by_time.values())
