from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from math import isfinite

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_imb_ote_pd_v2 import SourceImpulseReference
from crypto_bot.strategy.source_ob_breaker_v2 import BosReference, QualitativeEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


class RangeDeviationSide(str, Enum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True)
class CorrectionEndpointReference:
    price: float
    known_at: datetime
    parent_object_ids: tuple[str, ...]
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        _positive("correction price", self.price)
        _aware("correction known_at", self.known_at)
        if not self.parent_object_ids or not self.evidence_id or not self.provenance:
            raise ValueError("correction endpoint requires parent ids and provenance")


@dataclass(frozen=True)
class SourceRangeEvidence:
    obj: CausalSourceObject
    impulse_direction: Direction
    lower: float
    upper: float
    midpoint: float
    first_boundary_price: float
    second_boundary_price: float
    impulse_evidence_id: str
    correction_evidence_id: str


@dataclass(frozen=True)
class RangeAssessment:
    status: EvidenceStatus
    reason: str
    evidence: SourceRangeEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == EvidenceStatus.PASS


@dataclass(frozen=True)
class RangeDeviationEvidence:
    evidence_id: str
    range_object_id: str
    side: RangeDeviationSide
    boundary_price: float
    extreme_price: float
    known_at: datetime


@dataclass(frozen=True)
class ManipulationReference:
    """Already-causal liquidity sweep/manipulation geometry for STB/BTS."""

    direction: Direction
    swept_side: str
    zone_low: float
    zone_high: float
    known_at: datetime
    parent_liquidity_id: str
    parent_liquidity_known_at: datetime
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        if self.swept_side not in ("high", "low"):
            raise ValueError("swept side must be high or low")
        _positive("manipulation zone low", self.zone_low)
        _positive("manipulation zone high", self.zone_high)
        if self.zone_low >= self.zone_high:
            raise ValueError("manipulation zone must have positive width")
        _aware("manipulation known_at", self.known_at)
        _aware("liquidity known_at", self.parent_liquidity_known_at)
        if self.parent_liquidity_known_at > self.known_at:
            raise ValueError("liquidity cannot become known after the manipulation")
        if not self.parent_liquidity_id or not self.evidence_id or not self.provenance:
            raise ValueError("manipulation reference requires provenance")
        expected_side = "low" if self.direction == Direction.LONG else "high"
        if self.swept_side != expected_side:
            raise ValueError("STB/BTS direction must mirror the swept liquidity side")

    @property
    def midpoint(self) -> float:
        return (self.zone_low + self.zone_high) / 2

    @property
    def kind(self) -> str:
        return "STB" if self.direction == Direction.LONG else "BTS"


@dataclass(frozen=True)
class SourceStbBtsEvidence:
    obj: CausalSourceObject
    kind: str
    direction: Direction
    zone_low: float
    zone_high: float
    midpoint: float
    manipulation_evidence_id: str
    structure_evidence_id: str


@dataclass(frozen=True)
class StbBtsAssessment:
    status: EvidenceStatus
    reason: str
    evidence: SourceStbBtsEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == EvidenceStatus.PASS


def assess_source_range(
    *,
    symbol: str,
    timeframe: str | int,
    impulse: SourceImpulseReference,
    correction: CorrectionEndpointReference,
    strong_directional_impulse: QualitativeEvidence,
    midpoint_reaction: QualitativeEvidence,
    no_internal_structure: QualitativeEvidence,
) -> RangeAssessment:
    """Assess SOURCE Range formation without invented clarity/tolerance numbers.

    SW10: Range follows a strong directional impulse. The impulse end is boundary
    one and the later correction end is boundary two. 0.5 reaction validates the
    construction. Higher-priority Методичка also says internal structure should be
    absent. The qualitative words strong/good/clear therefore require provenance.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if correction.known_at < impulse.known_at:
        return RangeAssessment(EvidenceStatus.FAIL, "CORRECTION_ENDPOINT_PRECEDES_IMPULSE")

    if impulse.direction == Direction.LONG:
        first_boundary = impulse.end_price
        second_boundary = correction.price
        if second_boundary >= first_boundary:
            return RangeAssessment(EvidenceStatus.FAIL, "BULLISH_RANGE_CORRECTION_DID_NOT_FORM_LOWER_BOUNDARY")
    else:
        first_boundary = impulse.end_price
        second_boundary = correction.price
        if second_boundary <= first_boundary:
            return RangeAssessment(EvidenceStatus.FAIL, "BEARISH_RANGE_CORRECTION_DID_NOT_FORM_UPPER_BOUNDARY")

    for name, evidence in (
        ("STRONG_DIRECTIONAL_IMPULSE", strong_directional_impulse),
        ("MIDPOINT_REACTION", midpoint_reaction),
        ("NO_INTERNAL_STRUCTURE", no_internal_structure),
    ):
        if evidence.status == EvidenceStatus.FAIL:
            return RangeAssessment(EvidenceStatus.FAIL, f"{name}_SOURCE_EVIDENCE_FAILED")
        if not evidence.provenance_ready:
            return RangeAssessment(EvidenceStatus.UNKNOWN, f"WAIT_{name}_QUALITATIVE_PROVENANCE")

    # The impulse-strength fact can be known when the impulse completes. By contrast,
    # midpoint reaction and absence of internal structure are confirmations of the range
    # after both boundaries exist, so they cannot causally precede the correction endpoint.
    if midpoint_reaction.known_at < correction.known_at:  # type: ignore[operator]
        return RangeAssessment(EvidenceStatus.FAIL, "MIDPOINT_REACTION_KNOWN_BEFORE_RANGE_BOUNDARIES")
    if no_internal_structure.known_at < correction.known_at:  # type: ignore[operator]
        return RangeAssessment(EvidenceStatus.FAIL, "NO_INTERNAL_STRUCTURE_KNOWN_BEFORE_RANGE_BOUNDARIES")

    lower, upper = sorted((first_boundary, second_boundary))
    midpoint = (lower + upper) / 2
    known_at = max(
        correction.known_at,
        strong_directional_impulse.known_at,  # type: ignore[arg-type]
        midpoint_reaction.known_at,  # type: ignore[arg-type]
        no_internal_structure.known_at,  # type: ignore[arg-type]
    )
    parent_ids = tuple(dict.fromkeys(impulse.parent_object_ids + correction.parent_object_ids))
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.RANGE,
        symbol=symbol,
        timeframe=timeframe,
        direction=impulse.direction.value,
        formation_at=correction.known_at,
        known_at=known_at,
        confirmed_at=known_at,
        identity_parts={
            "direction": impulse.direction.value,
            "impulse_evidence_id": impulse.evidence_id,
            "correction_evidence_id": correction.evidence_id,
            "first_boundary_price": first_boundary,
            "second_boundary_price": second_boundary,
            "lower": lower,
            "upper": upper,
        },
        source_rule_ids=(
            "RANGE_AFTER_STRONG_IMPULSE_001",
            "RANGE_BOUNDARY_SEQUENCE_001",
            "RANGE_MIDPOINT_REACTION_001",
            "RANGE_NO_INTERNAL_STRUCTURE_001",
        ),
        technical_normalization_ids=("TN_RANGE_QUALITATIVE_EVIDENCE_PROVENANCE",),
        parent_object_ids=parent_ids,
        provenance=(
            "SW10 range construction + higher-priority Методичка range validity; "
            "no fixed clarity/tolerance/ATR threshold"
        ),
    )
    return RangeAssessment(
        EvidenceStatus.PASS,
        "SOURCE_RANGE_CONFIRMED",
        SourceRangeEvidence(
            obj=obj,
            impulse_direction=impulse.direction,
            lower=lower,
            upper=upper,
            midpoint=midpoint,
            first_boundary_price=first_boundary,
            second_boundary_price=second_boundary,
            impulse_evidence_id=impulse.evidence_id,
            correction_evidence_id=correction.evidence_id,
        ),
    )


def detect_range_deviations(
    range_evidence: SourceRangeEvidence,
    candle: Candle,
) -> tuple[RangeDeviationEvidence, ...]:
    """Record strict boundary sweeps as deviation events, without entry logic.

    SW10 defines deviation as movement beyond range boundaries to take external
    liquidity. A reclaim/return is a later setup-chain fact and is not required
    for the deviation event itself.
    """
    if not candle.is_closed:
        raise ValueError("range deviation requires a closed candle")
    if range_evidence.obj.known_at > candle.open_time:
        return ()
    out: list[RangeDeviationEvidence] = []
    if candle.high > range_evidence.upper:
        out.append(
            _deviation(
                range_evidence,
                candle,
                RangeDeviationSide.HIGH,
                range_evidence.upper,
                candle.high,
            )
        )
    if candle.low < range_evidence.lower:
        out.append(
            _deviation(
                range_evidence,
                candle,
                RangeDeviationSide.LOW,
                range_evidence.lower,
                candle.low,
            )
        )
    return tuple(out)


def assess_source_stb_bts(
    *,
    symbol: str,
    timeframe: str | int,
    manipulation: ManipulationReference,
    main_structure: CausalSourceObject,
    full_engulf_of_manipulation: QualitativeEvidence,
    bos_or_conf: BosReference,
) -> StbBtsAssessment:
    """Assess STB/BTS object formation; entry/mitigation stays deferred.

    SW22 requires liquidity sweep/manipulation, full engulf of the manipulation on
    reversal, BOS or CONF, and alignment with the main trend. The exact multi-bar
    'full engulf' geometry is qualitative in SOURCE and therefore provenance-based.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if main_structure.object_type != SourceObjectType.STRUCTURE or not main_structure.formation_valid:
        return StbBtsAssessment(EvidenceStatus.FAIL, "MAIN_STRUCTURE_PARENT_INVALID")
    if main_structure.known_at > manipulation.known_at:
        return StbBtsAssessment(EvidenceStatus.FAIL, "MAIN_STRUCTURE_NOT_KNOWN_BEFORE_MANIPULATION")
    if main_structure.direction != manipulation.direction.value:
        return StbBtsAssessment(EvidenceStatus.FAIL, "STB_BTS_NOT_ALIGNED_WITH_MAIN_TREND")

    if full_engulf_of_manipulation.status == EvidenceStatus.FAIL:
        return StbBtsAssessment(EvidenceStatus.FAIL, "FULL_MANIPULATION_ENGULF_FAILED")
    if not full_engulf_of_manipulation.provenance_ready:
        return StbBtsAssessment(EvidenceStatus.UNKNOWN, "WAIT_FULL_MANIPULATION_ENGULF_PROVENANCE")
    if full_engulf_of_manipulation.known_at < manipulation.known_at:  # type: ignore[operator]
        return StbBtsAssessment(EvidenceStatus.FAIL, "ENGULF_EVIDENCE_PRECEDES_MANIPULATION")

    if bos_or_conf.kind not in ("BOS", "CONF"):
        return StbBtsAssessment(EvidenceStatus.FAIL, "STB_BTS_REQUIRES_BOS_OR_CONF")
    if bos_or_conf.direction != manipulation.direction:
        return StbBtsAssessment(EvidenceStatus.FAIL, "STB_BTS_STRUCTURE_CONFIRMATION_DIRECTION_MISMATCH")
    if bos_or_conf.known_at < manipulation.known_at:
        return StbBtsAssessment(EvidenceStatus.FAIL, "STRUCTURE_CONFIRMATION_PRECEDES_MANIPULATION")

    known_at = max(
        manipulation.known_at,
        full_engulf_of_manipulation.known_at,  # type: ignore[arg-type]
        bos_or_conf.known_at,
    )
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.STB_BTS,
        symbol=symbol,
        timeframe=timeframe,
        direction=manipulation.direction.value,
        formation_at=manipulation.known_at,
        known_at=known_at,
        confirmed_at=known_at,
        identity_parts={
            "kind": manipulation.kind,
            "direction": manipulation.direction.value,
            "manipulation_evidence_id": manipulation.evidence_id,
            "zone_low": manipulation.zone_low,
            "zone_high": manipulation.zone_high,
            "structure_evidence_id": bos_or_conf.evidence_id,
        },
        source_rule_ids=(
            "STB_BTS_LIQUIDITY_MANIPULATION_001",
            "STB_BTS_FULL_ENGULF_001",
            "STB_BTS_BOS_CONF_001",
            "STB_BTS_MAIN_TREND_001",
        ),
        technical_normalization_ids=("TN_STB_BTS_QUALITATIVE_ENGULF_PROVENANCE",),
        parent_object_ids=(manipulation.parent_liquidity_id, main_structure.object_id),
        provenance=(
            "SW22 p1-3 STB/BTS manipulation object; 0.5 mitigation/entry and execution remain later chain logic"
        ),
    )
    evidence = SourceStbBtsEvidence(
        obj=obj,
        kind=manipulation.kind,
        direction=manipulation.direction,
        zone_low=manipulation.zone_low,
        zone_high=manipulation.zone_high,
        midpoint=manipulation.midpoint,
        manipulation_evidence_id=manipulation.evidence_id,
        structure_evidence_id=bos_or_conf.evidence_id,
    )
    return StbBtsAssessment(EvidenceStatus.PASS, "SOURCE_STB_BTS_CONFIRMED", evidence)


def _deviation(
    range_evidence: SourceRangeEvidence,
    candle: Candle,
    side: RangeDeviationSide,
    boundary: float,
    extreme: float,
) -> RangeDeviationEvidence:
    payload = (
        f"{range_evidence.obj.object_id}|{side.value}|{boundary}|"
        f"{candle.open_time.isoformat()}|{candle.close_time.isoformat()}|{extreme}"
    )
    return RangeDeviationEvidence(
        evidence_id=sha256(payload.encode("utf-8")).hexdigest()[:32],
        range_object_id=range_evidence.obj.object_id,
        side=side,
        boundary_price=boundary,
        extreme_price=extreme,
        known_at=candle.close_time,
    )


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
