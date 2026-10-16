from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType


OTE_SHALLOW = 0.705
OTE_DEEP = 0.79


class GeometryStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class PremiumDiscountLocation(str, Enum):
    DISCOUNT = "DISCOUNT"
    EQUILIBRIUM = "EQUILIBRIUM"
    PREMIUM = "PREMIUM"


@dataclass(frozen=True)
class SourceImbalanceEvidence:
    """SOURCE IMB/FVG object from exact three-candle wick-gap geometry."""

    obj: CausalSourceObject
    direction: Direction
    zone_low: float
    zone_high: float
    equilibrium: float
    first_open_time: datetime
    impulse_open_time: datetime
    third_close_time: datetime

    def __post_init__(self) -> None:
        if not 0 < self.zone_low < self.zone_high:
            raise ValueError("imbalance zone must have positive width")
        if self.equilibrium != (self.zone_low + self.zone_high) / 2:
            raise ValueError("equilibrium must be exact 0.5 midpoint")


@dataclass(frozen=True)
class ImbalanceAssessment:
    status: GeometryStatus
    reason: str
    evidence: SourceImbalanceEvidence | None = None

    @property
    def valid(self) -> bool:
        return self.status == GeometryStatus.PASS


@dataclass(frozen=True)
class ImbalanceInteraction:
    equilibrium_touched: bool
    full_fill: bool


@dataclass(frozen=True)
class SourceImpulseReference:
    """Already source-qualified impulse endpoints consumed by OTE geometry.

    Stage 5 intentionally does not choose impulse anchors from arbitrary highs/lows.
    Callers must provide causal parent object ids and provenance from a source-valid
    structure/setup object.
    """

    direction: Direction
    start_price: float
    end_price: float
    known_at: datetime
    parent_object_ids: tuple[str, ...]
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        _positive("start_price", self.start_price)
        _positive("end_price", self.end_price)
        _aware("known_at", self.known_at)
        if not self.parent_object_ids:
            raise ValueError("source impulse requires parent object ids")
        if not self.evidence_id or not self.provenance:
            raise ValueError("source impulse requires evidence provenance")
        if self.direction == Direction.LONG and self.end_price <= self.start_price:
            raise ValueError("LONG source impulse must move upward")
        if self.direction == Direction.SHORT and self.end_price >= self.start_price:
            raise ValueError("SHORT source impulse must move downward")


@dataclass(frozen=True)
class SourceOteEvidence:
    obj: CausalSourceObject
    direction: Direction
    zone_low: float
    zone_high: float
    ratio_shallow: float
    ratio_deep: float
    impulse_evidence_id: str


@dataclass(frozen=True)
class SourceDealingRangeReference:
    """Typed contract for an already source-valid dealing range.

    Stage 5 does not infer a dealing range from arbitrary extrema. Range/dealing-
    range construction remains a separate evidence problem; Premium/Discount is
    deterministic only after those endpoints are known.
    """

    low: float
    high: float
    known_at: datetime
    parent_object_ids: tuple[str, ...]
    evidence_id: str
    provenance: str

    def __post_init__(self) -> None:
        _positive("range.low", self.low)
        _positive("range.high", self.high)
        if self.low >= self.high:
            raise ValueError("dealing range low must be below high")
        _aware("range.known_at", self.known_at)
        if not self.parent_object_ids:
            raise ValueError("dealing range requires parent object ids")
        if not self.evidence_id or not self.provenance:
            raise ValueError("dealing range requires evidence provenance")

    @property
    def equilibrium(self) -> float:
        return (self.low + self.high) / 2


@dataclass(frozen=True)
class PremiumDiscountEvidence:
    location: PremiumDiscountLocation
    price: float
    equilibrium: float
    dealing_range_evidence_id: str
    known_at: datetime


def detect_source_imbalance(
    first: Candle,
    impulse: Candle,
    third: Candle,
    *,
    symbol: str,
    timeframe: str | int,
) -> ImbalanceAssessment:
    """Detect SOURCE IMB/FVG from exact wick-gap geometry.

    SW8 p1-3 and Методичка p11 define the inefficiency between the wick/extreme
    of the candle before the impulse and the wick/extreme of the candle after it.
    Stage 5 uses a strict positive gap; equality is no area and therefore no IMB.

    All three candles must be closed because the third-candle low/high is a zone
    endpoint and may still mutate intrabar.
    """
    if not symbol:
        raise ValueError("symbol is required")
    if not first.is_closed or not impulse.is_closed or not third.is_closed:
        return ImbalanceAssessment(GeometryStatus.FAIL, "IMB_REQUIRES_THREE_CLOSED_CANDLES")
    if first.close_time != impulse.open_time or impulse.close_time != third.open_time:
        return ImbalanceAssessment(GeometryStatus.FAIL, "IMB_CANDLES_NOT_CONTIGUOUS")

    bullish = third.low > first.high
    bearish = third.high < first.low
    if not bullish and not bearish:
        return ImbalanceAssessment(GeometryStatus.FAIL, "NO_POSITIVE_WICK_GAP")
    if bullish and bearish:
        raise ValueError("one three-candle sequence cannot be both bullish and bearish IMB")

    if bullish:
        direction = Direction.LONG
        zone_low, zone_high = first.high, third.low
    else:
        direction = Direction.SHORT
        zone_low, zone_high = third.high, first.low

    equilibrium = (zone_low + zone_high) / 2
    known_at = third.close_time
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.FVG,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction.value,
        formation_at=known_at,
        known_at=known_at,
        identity_parts={
            "direction": direction.value,
            "first_open_time": first.open_time,
            "impulse_open_time": impulse.open_time,
            "third_open_time": third.open_time,
            "zone_low": zone_low,
            "zone_high": zone_high,
        },
        source_rule_ids=(
            "IMB_THREE_CANDLE_WICK_GAP_001",
            "IMB_ZONE_BOUNDARIES_001",
            "IMB_EQUILIBRIUM_001",
        ),
        technical_normalization_ids=(
            "TN_IMB_STRICT_POSITIVE_GAP",
            "TN_IMB_KNOWN_AFTER_THIRD_CLOSE",
        ),
        provenance=(
            "SW8 p1-3 + Методичка p11: three-candle wick-gap price inefficiency; "
            "equilibrium is exact 0.5 of the zone"
        ),
    )
    return ImbalanceAssessment(
        GeometryStatus.PASS,
        "SOURCE_IMB_FORMED",
        SourceImbalanceEvidence(
            obj=obj,
            direction=direction,
            zone_low=zone_low,
            zone_high=zone_high,
            equilibrium=equilibrium,
            first_open_time=first.open_time,
            impulse_open_time=impulse.open_time,
            third_close_time=third.close_time,
        ),
    )


def assess_imbalance_interaction(
    imbalance: SourceImbalanceEvidence,
    candle: Candle,
) -> ImbalanceInteraction:
    """Observe later equilibrium/full-fill facts without mutating IMB history."""
    if not candle.is_closed:
        raise ValueError("IMB interaction requires a closed candle")
    if candle.close_time <= imbalance.obj.known_at:
        raise ValueError("interaction candle must be later than IMB known_at")

    equilibrium_touched = candle.low <= imbalance.equilibrium <= candle.high
    if imbalance.direction == Direction.LONG:
        # Bullish IMB lies below price after formation; complete fill reaches the
        # lower boundary originating from the first candle high.
        full_fill = candle.low <= imbalance.zone_low
    else:
        # Bearish IMB lies above price after formation; complete fill reaches the
        # upper boundary originating from the first candle low.
        full_fill = candle.high >= imbalance.zone_high
    return ImbalanceInteraction(equilibrium_touched, full_fill)


def build_source_ote(
    impulse: SourceImpulseReference,
    *,
    symbol: str,
    timeframe: str | int,
) -> SourceOteEvidence:
    """Build SOURCE OTE 0.705-0.79 only from a pre-qualified impulse."""
    if not symbol:
        raise ValueError("symbol is required")
    a = _retracement_price(impulse, OTE_SHALLOW)
    b = _retracement_price(impulse, OTE_DEEP)
    zone_low, zone_high = min(a, b), max(a, b)
    obj = CausalSourceObject.formed(
        object_type=SourceObjectType.POI,
        symbol=symbol,
        timeframe=timeframe,
        direction=impulse.direction.value,
        formation_at=impulse.known_at,
        known_at=impulse.known_at,
        identity_parts={
            "poi_kind": "OTE",
            "direction": impulse.direction.value,
            "start_price": impulse.start_price,
            "end_price": impulse.end_price,
            "impulse_evidence_id": impulse.evidence_id,
            "zone_low": zone_low,
            "zone_high": zone_high,
        },
        source_rule_ids=("OTE_ZONE_0705_079_001",),
        technical_normalization_ids=("TN_OTE_REQUIRES_SOURCE_IMPULSE_REFERENCE",),
        parent_object_ids=impulse.parent_object_ids,
        provenance=(
            "Методичка p16-18 OTE 0.705-0.79; anchor selection is not inferred here and "
            "must already be source-qualified by the supplied impulse reference"
        ),
    )
    return SourceOteEvidence(
        obj=obj,
        direction=impulse.direction,
        zone_low=zone_low,
        zone_high=zone_high,
        ratio_shallow=OTE_SHALLOW,
        ratio_deep=OTE_DEEP,
        impulse_evidence_id=impulse.evidence_id,
    )


def classify_premium_discount(
    dealing_range: SourceDealingRangeReference,
    *,
    price: float,
    decision_at: datetime,
) -> PremiumDiscountEvidence:
    """Classify price around source equilibrium 0.5 of a known dealing range.

    This function does not decide whether the dealing range itself is valid.
    It consumes a source-qualified range contract and performs only deterministic
    midpoint geometry.
    """
    _positive("price", price)
    _aware("decision_at", decision_at)
    if decision_at < dealing_range.known_at:
        raise ValueError("cannot classify Premium/Discount before dealing range is known")
    if price < dealing_range.low or price > dealing_range.high:
        raise ValueError("price must be inside the source dealing range")

    equilibrium = dealing_range.equilibrium
    if price < equilibrium:
        location = PremiumDiscountLocation.DISCOUNT
    elif price > equilibrium:
        location = PremiumDiscountLocation.PREMIUM
    else:
        location = PremiumDiscountLocation.EQUILIBRIUM
    return PremiumDiscountEvidence(
        location=location,
        price=price,
        equilibrium=equilibrium,
        dealing_range_evidence_id=dealing_range.evidence_id,
        known_at=decision_at,
    )


def _retracement_price(impulse: SourceImpulseReference, ratio: float) -> float:
    return impulse.end_price + ratio * (impulse.start_price - impulse.end_price)


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
