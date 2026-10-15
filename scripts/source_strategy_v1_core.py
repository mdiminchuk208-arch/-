from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
import json
from typing import Iterable, Literal, Sequence


VERSION = "SOURCE_STRATEGY_REBUILD_v1"
TRADE_ENTRY_ALLOWED = False
ACTIVE_TIMEFRAMES = (15, 60, 240, 1440)


class SourceSemanticError(ValueError):
    pass


def _d(value: Decimal | str | int) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def canonical_decimal(value: Decimal | str | int) -> str:
    number = _d(value)
    if not number.is_finite():
        raise SourceSemanticError("NON_FINITE_DECIMAL")
    if number == 0:
        return "0"
    text = format(number.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def stable_id(kind: str, **fields: object) -> str:
    payload = json.dumps(
        {"kind": kind, **fields},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return f"{kind.lower()}_{sha256(payload.encode()).hexdigest()[:24]}"


@dataclass(frozen=True, slots=True)
class Bar:
    start: int
    end: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    timeframe_minutes: int

    def __post_init__(self) -> None:
        values = tuple(map(_d, (self.open, self.high, self.low, self.close)))
        object.__setattr__(self, "open", values[0])
        object.__setattr__(self, "high", values[1])
        object.__setattr__(self, "low", values[2])
        object.__setattr__(self, "close", values[3])
        if self.start >= self.end:
            raise SourceSemanticError("BAR_TIME_ORDER")
        if self.timeframe_minutes <= 0:
            raise SourceSemanticError("INVALID_TIMEFRAME")
        if self.low > self.high:
            raise SourceSemanticError("BAR_LOW_ABOVE_HIGH")
        if not self.low <= self.open <= self.high:
            raise SourceSemanticError("OPEN_OUTSIDE_BAR")
        if not self.low <= self.close <= self.high:
            raise SourceSemanticError("CLOSE_OUTSIDE_BAR")


PivotSide = Literal["HIGH", "LOW"]
StructureLabel = Literal["HH", "LH", "HL", "LL", "EQUAL_HIGH", "EQUAL_LOW"]


@dataclass(frozen=True, slots=True)
class Pivot:
    id: str
    side: PivotSide
    price: Decimal
    source_bar_start: int
    source_bar_end: int
    known_at: int
    timeframe_minutes: int
    label: StructureLabel | None = None


@dataclass(frozen=True, slots=True)
class StructureState:
    known_at: int
    timeframe_minutes: int
    trend: Literal["BULLISH", "BEARISH", "UNKNOWN"]
    latest_high_id: str | None
    latest_high_label: StructureLabel | None
    latest_low_id: str | None
    latest_low_label: StructureLabel | None


@dataclass(frozen=True, slots=True)
class BreakEvent:
    id: str
    direction: Literal["BULLISH", "BEARISH"]
    broken_pivot_id: str
    broken_price: Decimal
    event_bar_start: int
    known_at: int
    timeframe_minutes: int
    normalization: str = "TN_BOS_001"


@dataclass(frozen=True, slots=True)
class Imbalance:
    id: str
    direction: Literal["BULLISH", "BEARISH"]
    zone_low: Decimal
    zone_high: Decimal
    first_bar_start: int
    third_bar_start: int
    known_at: int
    timeframe_minutes: int
    unresolved: tuple[str, ...] = ("UNKNOWN_IMPULSE_STRENGTH",)


@dataclass(frozen=True, slots=True)
class LiquidityLevel:
    id: str
    kind: Literal["EXACT_EQH", "EXACT_EQL", "SWING_HIGH", "SWING_LOW", "RANGE_HIGH", "RANGE_LOW"]
    price: Decimal
    known_at: int
    timeframe_minutes: int
    source_ids: tuple[str, ...]
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RawSfpCandidate:
    id: str
    direction: Literal["LONG", "SHORT"]
    level_id: str
    level_price: Decimal
    sweep_bar_start: int
    known_at: int
    timeframe_minutes: int
    state: Literal["UNKNOWN_SOURCE_SEMANTICS"] = "UNKNOWN_SOURCE_SEMANTICS"
    unresolved: tuple[str, ...] = (
        "UNKNOWN_SFP_EXACT_THREE_CANDLE_GEOMETRY",
        "UNKNOWN_SFP_OPTIONAL_FOURTH_CONFIRMATION",
        "UNKNOWN_SFP_CONTEXT_PRIORITY",
    )


@dataclass(frozen=True, slots=True)
class RangeBoundary:
    id: str
    low: Decimal
    high: Decimal
    known_at: int
    timeframe_minutes: int
    source_ids: tuple[str, ...]
    state: Literal["UNKNOWN_SOURCE_SEMANTICS"] = "UNKNOWN_SOURCE_SEMANTICS"
    unresolved: tuple[str, ...] = (
        "UNKNOWN_RANGE_CLARITY",
        "UNKNOWN_NO_STRUCTURE_NUMERIC_DEFINITION",
    )


@dataclass(frozen=True, slots=True)
class RangeDeviation:
    id: str
    direction: Literal["ABOVE", "BELOW"]
    range_id: str
    event_bar_start: int
    known_at: int
    timeframe_minutes: int


def completed_bars(bars: Sequence[Bar], cutoff: int) -> list[Bar]:
    result: list[Bar] = []
    previous_end: int | None = None
    for bar in bars:
        if previous_end is not None and bar.start < previous_end:
            raise SourceSemanticError("OVERLAPPING_OR_UNSORTED_BARS")
        previous_end = bar.end
        if bar.end <= cutoff:
            result.append(bar)
    return result


def strict_three_bar_pivots(bars: Sequence[Bar], cutoff: int) -> list[Pivot]:
    completed = completed_bars(bars, cutoff)
    raw: list[Pivot] = []
    for index in range(1, len(completed) - 1):
        left, center, right = completed[index - 1], completed[index], completed[index + 1]
        if len({left.timeframe_minutes, center.timeframe_minutes, right.timeframe_minutes}) != 1:
            raise SourceSemanticError("MIXED_TIMEFRAME_PIVOT")
        if center.high > left.high and center.high > right.high:
            raw.append(
                Pivot(
                    id=stable_id(
                        "PIVOT_HIGH",
                        tf=center.timeframe_minutes,
                        source_bar_start=center.start,
                        price=canonical_decimal(center.high),
                    ),
                    side="HIGH",
                    price=center.high,
                    source_bar_start=center.start,
                    source_bar_end=center.end,
                    known_at=right.end,
                    timeframe_minutes=center.timeframe_minutes,
                )
            )
        if center.low < left.low and center.low < right.low:
            raw.append(
                Pivot(
                    id=stable_id(
                        "PIVOT_LOW",
                        tf=center.timeframe_minutes,
                        source_bar_start=center.start,
                        price=canonical_decimal(center.low),
                    ),
                    side="LOW",
                    price=center.low,
                    source_bar_start=center.start,
                    source_bar_end=center.end,
                    known_at=right.end,
                    timeframe_minutes=center.timeframe_minutes,
                )
            )
    return label_pivots(raw)


def label_pivots(pivots: Sequence[Pivot]) -> list[Pivot]:
    previous: dict[PivotSide, Pivot] = {}
    labeled: list[Pivot] = []
    for pivot in sorted(pivots, key=lambda item: (item.known_at, item.source_bar_start, item.side)):
        prior = previous.get(pivot.side)
        label: StructureLabel | None = None
        if prior is not None:
            if pivot.side == "HIGH":
                label = "HH" if pivot.price > prior.price else "LH" if pivot.price < prior.price else "EQUAL_HIGH"
            else:
                label = "HL" if pivot.price > prior.price else "LL" if pivot.price < prior.price else "EQUAL_LOW"
        current = Pivot(
            id=pivot.id,
            side=pivot.side,
            price=pivot.price,
            source_bar_start=pivot.source_bar_start,
            source_bar_end=pivot.source_bar_end,
            known_at=pivot.known_at,
            timeframe_minutes=pivot.timeframe_minutes,
            label=label,
        )
        labeled.append(current)
        previous[pivot.side] = current
    return labeled


def structure_state(pivots: Sequence[Pivot], cutoff: int) -> StructureState:
    known = [pivot for pivot in pivots if pivot.known_at <= cutoff]
    highs = [pivot for pivot in known if pivot.side == "HIGH"]
    lows = [pivot for pivot in known if pivot.side == "LOW"]
    high = highs[-1] if highs else None
    low = lows[-1] if lows else None
    trend: Literal["BULLISH", "BEARISH", "UNKNOWN"] = "UNKNOWN"
    if high and low and high.label == "HH" and low.label == "HL":
        trend = "BULLISH"
    elif high and low and high.label == "LH" and low.label == "LL":
        trend = "BEARISH"
    timeframe = high.timeframe_minutes if high else low.timeframe_minutes if low else 0
    return StructureState(
        known_at=cutoff,
        timeframe_minutes=timeframe,
        trend=trend,
        latest_high_id=high.id if high else None,
        latest_high_label=high.label if high else None,
        latest_low_id=low.id if low else None,
        latest_low_label=low.label if low else None,
    )


def detect_bos(bars: Sequence[Bar], pivots: Sequence[Pivot], cutoff: int) -> list[BreakEvent]:
    completed = completed_bars(bars, cutoff)
    events: list[BreakEvent] = []
    used: set[tuple[str, str]] = set()
    for bar in completed:
        known = [pivot for pivot in pivots if pivot.known_at < bar.end]
        if not known:
            continue
        state = structure_state(known, bar.start)
        highs = [pivot for pivot in known if pivot.side == "HIGH"]
        lows = [pivot for pivot in known if pivot.side == "LOW"]
        if state.trend == "BULLISH":
            protected = next((pivot for pivot in reversed(lows) if pivot.label == "HL"), None)
            if protected and bar.close < protected.price and (protected.id, "BEARISH") not in used:
                events.append(_break_event("BEARISH", protected, bar))
                used.add((protected.id, "BEARISH"))
        elif state.trend == "BEARISH":
            protected = next((pivot for pivot in reversed(highs) if pivot.label == "LH"), None)
            if protected and bar.close > protected.price and (protected.id, "BULLISH") not in used:
                events.append(_break_event("BULLISH", protected, bar))
                used.add((protected.id, "BULLISH"))
    return events


def _break_event(direction: Literal["BULLISH", "BEARISH"], pivot: Pivot, bar: Bar) -> BreakEvent:
    return BreakEvent(
        id=stable_id(
            "BOS",
            direction=direction,
            broken_pivot_id=pivot.id,
            event_bar_start=bar.start,
        ),
        direction=direction,
        broken_pivot_id=pivot.id,
        broken_price=pivot.price,
        event_bar_start=bar.start,
        known_at=bar.end,
        timeframe_minutes=bar.timeframe_minutes,
    )


def detect_imbalances(bars: Sequence[Bar], cutoff: int) -> list[Imbalance]:
    completed = completed_bars(bars, cutoff)
    result: list[Imbalance] = []
    for index in range(2, len(completed)):
        first, third = completed[index - 2], completed[index]
        if first.timeframe_minutes != third.timeframe_minutes:
            raise SourceSemanticError("MIXED_TIMEFRAME_IMBALANCE")
        if third.low > first.high:
            result.append(_imbalance("BULLISH", first.high, third.low, first, third))
        if third.high < first.low:
            result.append(_imbalance("BEARISH", third.high, first.low, first, third))
    return result


def _imbalance(
    direction: Literal["BULLISH", "BEARISH"],
    low: Decimal,
    high: Decimal,
    first: Bar,
    third: Bar,
) -> Imbalance:
    return Imbalance(
        id=stable_id(
            "IMBALANCE",
            direction=direction,
            tf=third.timeframe_minutes,
            first_bar_start=first.start,
            third_bar_start=third.start,
            low=canonical_decimal(low),
            high=canonical_decimal(high),
        ),
        direction=direction,
        zone_low=low,
        zone_high=high,
        first_bar_start=first.start,
        third_bar_start=third.start,
        known_at=third.end,
        timeframe_minutes=third.timeframe_minutes,
    )


def exact_equal_liquidity(pivots: Sequence[Pivot]) -> list[LiquidityLevel]:
    by_side: dict[PivotSide, list[Pivot]] = {"HIGH": [], "LOW": []}
    for pivot in pivots:
        by_side[pivot.side].append(pivot)
    levels: list[LiquidityLevel] = []
    for side, items in by_side.items():
        previous: Pivot | None = None
        for pivot in items:
            if previous is not None and pivot.price == previous.price:
                kind: Literal["EXACT_EQH", "EXACT_EQL"] = "EXACT_EQH" if side == "HIGH" else "EXACT_EQL"
                levels.append(
                    LiquidityLevel(
                        id=stable_id(kind, first=previous.id, second=pivot.id),
                        kind=kind,
                        price=pivot.price,
                        known_at=max(previous.known_at, pivot.known_at),
                        timeframe_minutes=pivot.timeframe_minutes,
                        source_ids=(previous.id, pivot.id),
                        unresolved=("UNKNOWN_EQH_EQL_TOLERANCE",),
                    )
                )
            previous = pivot
    return levels


def swing_liquidity(pivots: Sequence[Pivot]) -> list[LiquidityLevel]:
    return [
        LiquidityLevel(
            id=stable_id("LIQUIDITY_SWING", pivot_id=pivot.id),
            kind="SWING_HIGH" if pivot.side == "HIGH" else "SWING_LOW",
            price=pivot.price,
            known_at=pivot.known_at,
            timeframe_minutes=pivot.timeframe_minutes,
            source_ids=(pivot.id,),
        )
        for pivot in pivots
    ]


def ote_levels(anchor_zero: Decimal | str | int, anchor_one: Decimal | str | int) -> dict[str, str]:
    zero, one = _d(anchor_zero), _d(anchor_one)
    span = one - zero
    return {
        "0": canonical_decimal(zero),
        "0.5": canonical_decimal(zero + span * Decimal("0.5")),
        "0.62": canonical_decimal(zero + span * Decimal("0.62")),
        "0.705": canonical_decimal(zero + span * Decimal("0.705")),
        "0.79": canonical_decimal(zero + span * Decimal("0.79")),
        "1": canonical_decimal(one),
    }


def raw_sfp_candidates(
    bars: Sequence[Bar],
    levels: Iterable[LiquidityLevel],
    cutoff: int,
) -> list[RawSfpCandidate]:
    completed = completed_bars(bars, cutoff)
    level_list = list(levels)
    result: list[RawSfpCandidate] = []
    for bar in completed:
        for level in level_list:
            if level.known_at > bar.start or level.timeframe_minutes != bar.timeframe_minutes:
                continue
            if bar.high > level.price and bar.close <= level.price:
                result.append(_raw_sfp("SHORT", bar, level))
            if bar.low < level.price and bar.close >= level.price:
                result.append(_raw_sfp("LONG", bar, level))
    return result


def _raw_sfp(direction: Literal["LONG", "SHORT"], bar: Bar, level: LiquidityLevel) -> RawSfpCandidate:
    return RawSfpCandidate(
        id=stable_id(
            "RAW_SFP",
            direction=direction,
            level_id=level.id,
            sweep_bar_start=bar.start,
        ),
        direction=direction,
        level_id=level.id,
        level_price=level.price,
        sweep_bar_start=bar.start,
        known_at=bar.end,
        timeframe_minutes=bar.timeframe_minutes,
    )


def range_boundary(
    first_low: Pivot,
    first_high: Pivot,
    known_at: int | None = None,
) -> RangeBoundary:
    if first_low.side != "LOW" or first_high.side != "HIGH":
        raise SourceSemanticError("RANGE_BOUNDARY_REQUIRES_LOW_AND_HIGH")
    if first_low.timeframe_minutes != first_high.timeframe_minutes:
        raise SourceSemanticError("MIXED_TIMEFRAME_RANGE")
    when = max(first_low.known_at, first_high.known_at) if known_at is None else known_at
    if when < max(first_low.known_at, first_high.known_at):
        raise SourceSemanticError("RANGE_KNOWN_BEFORE_INPUTS")
    return RangeBoundary(
        id=stable_id("RANGE", low_id=first_low.id, high_id=first_high.id),
        low=first_low.price,
        high=first_high.price,
        known_at=when,
        timeframe_minutes=first_low.timeframe_minutes,
        source_ids=(first_low.id, first_high.id),
    )


def detect_range_deviations(
    bars: Sequence[Bar],
    range_object: RangeBoundary,
    cutoff: int,
) -> list[RangeDeviation]:
    result: list[RangeDeviation] = []
    for bar in completed_bars(bars, cutoff):
        if bar.timeframe_minutes != range_object.timeframe_minutes or bar.start < range_object.known_at:
            continue
        if bar.high > range_object.high:
            result.append(_range_deviation("ABOVE", bar, range_object))
        if bar.low < range_object.low:
            result.append(_range_deviation("BELOW", bar, range_object))
    return result


def _range_deviation(
    direction: Literal["ABOVE", "BELOW"],
    bar: Bar,
    range_object: RangeBoundary,
) -> RangeDeviation:
    return RangeDeviation(
        id=stable_id(
            "RANGE_DEVIATION",
            direction=direction,
            range_id=range_object.id,
            event_bar_start=bar.start,
        ),
        direction=direction,
        range_id=range_object.id,
        event_bar_start=bar.start,
        known_at=bar.end,
        timeframe_minutes=bar.timeframe_minutes,
    )


_FORBIDDEN_FINANCIAL_FIELDS = {
    "win",
    "loss",
    "pnl",
    "profit",
    "mfe",
    "mae",
    "fees",
    "funding",
    "slippage",
    "tp",
    "stop_outcome",
}


def assert_nonfinancial_record(record: object) -> None:
    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key).lower() in _FORBIDDEN_FINANCIAL_FIELDS:
                    raise SourceSemanticError("FINANCIAL_FIELD_FORBIDDEN_IN_STAGE_2")
                walk(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                walk(nested)

    if hasattr(record, "__dataclass_fields__"):
        walk(asdict(record))
    else:
        walk(record)
