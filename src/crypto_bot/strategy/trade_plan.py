from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEventKind

from crypto_bot.common.models import Direction


OTE_SHALLOW = 0.705
OTE_DEEP = 0.79


class TradePlanGeometryError(ValueError):
    pass


def _validate_price(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise TradePlanGeometryError(f"{name} must be finite and positive")


def _validate_direction(direction: Direction) -> None:
    if direction not in (Direction.LONG, Direction.SHORT):
        raise TradePlanGeometryError("direction must be LONG or SHORT")


@dataclass(frozen=True)
class PriceZone:
    low: float
    high: float

    def __post_init__(self) -> None:
        _validate_price("zone.low", self.low)
        _validate_price("zone.high", self.high)
        if self.low > self.high:
            raise TradePlanGeometryError("zone.low cannot exceed zone.high")

    @property
    def width(self) -> float:
        return self.high - self.low


@dataclass(frozen=True)
class SourceStopReference:
    price: float
    policy: str

    def __post_init__(self) -> None:
        _validate_price("stop_reference.price", self.price)
        allowed={"SOURCE_OB_EXTREME","SOURCE_ENGULFING_WICK"}
        if self.policy not in allowed:
            raise TradePlanGeometryError("unsupported source stop policy")


@dataclass(frozen=True)
class SourceTargetZone:
    zone: PriceZone
    policy: str = "SOURCE_FIRST_OPPOSING_POI_FTA"

    def __post_init__(self) -> None:
        if self.policy != "SOURCE_FIRST_OPPOSING_POI_FTA":
            raise TradePlanGeometryError("unsupported source target policy")


@dataclass(frozen=True)
class RrRange:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if not all(isfinite(v) and v > 0 for v in (self.minimum, self.maximum)):
            raise TradePlanGeometryError("RR values must be finite and positive")
        if self.minimum > self.maximum:
            raise TradePlanGeometryError("RR minimum cannot exceed maximum")


@dataclass(frozen=True)
class TradePlanGeometry:
    direction: Direction
    impulse_start_price: float
    impulse_end_price: float
    entry_zone: PriceZone
    stop_loss_price: float
    target_price: float
    rr: RrRange
    optimal_entry_price: float | None = None
    entry_policy: str = "SOURCE_OTE_0.705_0.79_ZONE"
    optimal_entry_policy: str = "SOURCE_DEFINES_OPTIMAL_ZONE_NOT_SINGLE_PRICE"


def ote_entry_zone(
    *,
    direction: Direction,
    impulse_start_price: float,
    impulse_end_price: float,
) -> PriceZone:
    """Return the source OTE 0.705-0.79 retracement zone of a completed impulse.

    `impulse_start_price` and `impulse_end_price` must be supplied in chronological
    impulse order. LONG therefore requires an upward impulse and SHORT a downward
    impulse. This function formalizes only OTE geometry; it does not decide which
    market-structure points are valid impulse anchors.
    """
    _validate_direction(direction)
    _validate_price("impulse_start_price", impulse_start_price)
    _validate_price("impulse_end_price", impulse_end_price)

    if direction == Direction.LONG and impulse_end_price <= impulse_start_price:
        raise TradePlanGeometryError("LONG OTE requires an upward impulse")
    if direction == Direction.SHORT and impulse_end_price >= impulse_start_price:
        raise TradePlanGeometryError("SHORT OTE requires a downward impulse")

    def retracement_price(ratio: float) -> float:
        return impulse_end_price + ratio * (impulse_start_price - impulse_end_price)

    a = retracement_price(OTE_SHALLOW)
    b = retracement_price(OTE_DEEP)
    return PriceZone(low=min(a, b), high=max(a, b))


def rr_ratio(
    *,
    direction: Direction,
    entry_price: float,
    stop_loss_price: float,
    target_price: float,
) -> float:
    """Reward/risk for one explicit entry price.

    No minimum acceptable RR is imposed here because Phase 1.4.20 has no
    source-backed fixed threshold.
    """
    _validate_direction(direction)
    for name, value in (
        ("entry_price", entry_price),
        ("stop_loss_price", stop_loss_price),
        ("target_price", target_price),
    ):
        _validate_price(name, value)

    if direction == Direction.LONG:
        if not stop_loss_price < entry_price < target_price:
            raise TradePlanGeometryError("LONG requires stop < entry < target")
        risk = entry_price - stop_loss_price
        reward = target_price - entry_price
    else:
        if not target_price < entry_price < stop_loss_price:
            raise TradePlanGeometryError("SHORT requires target < entry < stop")
        risk = stop_loss_price - entry_price
        reward = entry_price - target_price

    return reward / risk


def rr_range_for_entry_zone(
    *,
    direction: Direction,
    entry_zone: PriceZone,
    stop_loss_price: float,
    target_price: float,
) -> RrRange:
    """RR interval across both OTE-zone edges without inventing a single entry price."""
    values = (
        rr_ratio(
            direction=direction,
            entry_price=entry_zone.low,
            stop_loss_price=stop_loss_price,
            target_price=target_price,
        ),
        rr_ratio(
            direction=direction,
            entry_price=entry_zone.high,
            stop_loss_price=stop_loss_price,
            target_price=target_price,
        ),
    )
    return RrRange(minimum=min(values), maximum=max(values))


def build_trade_plan_geometry(
    *,
    direction: Direction,
    impulse_start_price: float,
    impulse_end_price: float,
    stop_loss_price: float,
    target_price: float,
) -> TradePlanGeometry:
    """Build source-aligned OTE + explicit SL/target + RR geometry.

    Stop and target selection are intentionally caller-supplied in this first
    Phase 1.4.20 slice. Their market-selection policies are separate concerns.
    """
    zone = ote_entry_zone(
        direction=direction,
        impulse_start_price=impulse_start_price,
        impulse_end_price=impulse_end_price,
    )
    rr = rr_range_for_entry_zone(
        direction=direction,
        entry_zone=zone,
        stop_loss_price=stop_loss_price,
        target_price=target_price,
    )
    return TradePlanGeometry(
        direction=direction,
        impulse_start_price=impulse_start_price,
        impulse_end_price=impulse_end_price,
        entry_zone=zone,
        stop_loss_price=stop_loss_price,
        target_price=target_price,
        rr=rr,
    )

@dataclass(frozen=True)
class StructuralImpulseContext:
    direction: Direction
    bos_time: datetime
    ready_time: datetime
    transition_id: int
    impulse_start_price: float
    impulse_end_price: float
    anchor_level_id: int
    correction_level_id: int
    correction_price: float
    entry_zone: PriceZone
    resolution_mode: str


def derive_structural_impulse_context(
    *,
    direction: Direction,
    ltf_report: "MarketAnalysisReport",
    bos_kind: "MarketEventKind",
    bos_index: int,
    bos_time: datetime,
) -> StructuralImpulseContext | None:
    """Derive causal post-BOS impulse geometry from an expected-opposite structure transition.

    TECHNICAL NORMALIZATION:
    - exact BOS identity is matched by kind/index/time;
    - same-direction recovery is never promoted into source entry geometry;
    - broken_extreme_price is the pre-BOS structural extreme and the selected post-BOS
      anchor is the new impulse extreme;
    - the selected correction is required only as proof that the expected opposite structure
      actually formed; OTE itself is measured over broken-extreme -> selected-anchor.
    """
    from crypto_bot.strategy.market_analysis import TrendState

    _validate_direction(direction)
    expected_trend = TrendState.BULLISH if direction == Direction.LONG else TrendState.BEARISH
    allowed_modes = {"EXPECTED_OPPOSITE_FAST_PATH", "EXPECTED_OPPOSITE_LOCAL_STRUCTURE"}
    matches = [
        t
        for t in ltf_report.structure_transition_diagnostics
        if t.bos_kind == bos_kind.value
        and t.bos_index == bos_index
        and t.bos_time == bos_time
        and t.resolution_mode in allowed_modes
        and t.resolved_trend == expected_trend
        and t.resolved_time is not None
        and t.broken_extreme_price is not None
        and t.selected_anchor_level_id is not None
        and t.selected_correction_level_id is not None
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise TradePlanGeometryError("exact BOS identity matched multiple structure transitions")

    transition = matches[0]
    levels_by_id = {level.level_id: level for level in ltf_report.levels}
    anchor = levels_by_id.get(transition.selected_anchor_level_id)
    correction = levels_by_id.get(transition.selected_correction_level_id)
    if anchor is None or correction is None:
        return None

    start = float(transition.broken_extreme_price)
    end = float(anchor.price)
    zone = ote_entry_zone(
        direction=direction,
        impulse_start_price=start,
        impulse_end_price=end,
    )
    return StructuralImpulseContext(
        direction=direction,
        bos_time=bos_time,
        ready_time=transition.resolved_time,
        transition_id=transition.transition_id,
        impulse_start_price=start,
        impulse_end_price=end,
        anchor_level_id=anchor.level_id,
        correction_level_id=correction.level_id,
        correction_price=correction.price,
        entry_zone=zone,
        resolution_mode=transition.resolution_mode,
    )


def validate_source_reference_geometry(*, direction: Direction, entry_zone: PriceZone, stop_reference: SourceStopReference, target_zone: SourceTargetZone) -> None:
    """Technical geometry guard for source-qualified references; does not choose SL or TP."""
    _validate_direction(direction)
    if direction == Direction.LONG:
        if stop_reference.price >= entry_zone.low:
            raise TradePlanGeometryError("LONG stop reference must be below the entry zone")
        if target_zone.zone.low <= entry_zone.high:
            raise TradePlanGeometryError("LONG target zone must be above the entry zone")
    else:
        if stop_reference.price <= entry_zone.high:
            raise TradePlanGeometryError("SHORT stop reference must be above the entry zone")
        if target_zone.zone.high >= entry_zone.low:
            raise TradePlanGeometryError("SHORT target zone must be below the entry zone")


def select_first_opposing_poi_fta(*, direction: Direction, entry_zone: PriceZone, opposing_poi_zones: tuple[PriceZone, ...]) -> SourceTargetZone:
    """Select the first price-reachable zone from caller-supplied source-qualified opposing POIs."""
    _validate_direction(direction)
    if direction == Direction.LONG:
        valid=[z for z in opposing_poi_zones if z.low > entry_zone.high]
        if not valid:
            raise TradePlanGeometryError("no opposing FTA/POI zone above LONG entry zone")
        zone=min(valid,key=lambda z:(z.low,z.high))
    else:
        valid=[z for z in opposing_poi_zones if z.high < entry_zone.low]
        if not valid:
            raise TradePlanGeometryError("no opposing FTA/POI zone below SHORT entry zone")
        zone=max(valid,key=lambda z:(z.high,z.low))
    return SourceTargetZone(zone=zone)
