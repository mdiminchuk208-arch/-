from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Sequence

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEvent, MarketEventKind
from crypto_bot.strategy.sfp import detect_sfp


class RangeImpulseDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class RangeStatus(str, Enum):
    WAITING_MIDPOINT_REACTION = "WAITING_MIDPOINT_REACTION"
    VALIDATED = "VALIDATED"
    REJECTED_INTERNAL_STRUCTURE = "REJECTED_INTERNAL_STRUCTURE"
    INVALIDATED_INTERNAL_STRUCTURE = "INVALIDATED_INTERNAL_STRUCTURE"
    RETIRED_LIQUIDITY_EXHAUSTED = "RETIRED_LIQUIDITY_EXHAUSTED"


class RangeBoundaryState(str, Enum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"


class RangeBoundaryClarityReview(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class RangeDetectionParams:
    """Explicit Phase-1.4.6 machine parameters for the qualitative range source rules.

    SOURCE RULES:
      * range follows a strong directional impulse;
      * impulse end is boundary #1 and correction end is boundary #2;
      * up impulse -> first high then later low; down impulse -> first low then later high;
      * a good reaction from 0.5 confirms the boundaries;
      * structure should be absent inside a range;
      * range boundaries contain external liquidity and are eligible SFP levels.

    TECHNICAL NORMALIZATIONS / BACKTEST PARAMETERS:
      * source does not give a numeric definition of "strong impulse". This build uses a
        source-defined structural BOS as a conservative impulse proxy rather than inventing
        an ATR/percent threshold. It can under-detect ranges and must be chart-audited.
      * source does not numerically define a "good" 0.5 reaction. This build requires a
        confirmed three-candle swing within midpoint_tolerance_fraction * range_width of 0.5.
        The tolerance is a BACKTEST_PARAMETER and is not a source rule.
      * internal structure is machine-proxied by a BOS whose close remains inside the range.
    """

    midpoint_tolerance_fraction: float = 0.08
    require_clean_internal_structure: bool = True

    def __post_init__(self) -> None:
        if not (0.0 <= self.midpoint_tolerance_fraction <= 0.5):
            raise ValueError("midpoint_tolerance_fraction must be within [0, 0.5]")


@dataclass(frozen=True)
class RangeInstance:
    range_id: int
    impulse_direction: RangeImpulseDirection
    impulse_bos_kind: MarketEventKind
    impulse_bos_time: datetime
    impulse_bos_candle_index: int
    first_boundary_kind: str
    first_boundary_price: float
    first_boundary_time: datetime
    first_boundary_candle_index: int
    second_boundary_kind: str
    second_boundary_price: float
    second_boundary_time: datetime
    second_boundary_candle_index: int
    lower: float
    upper: float
    midpoint: float
    status: RangeStatus
    status_time: datetime
    boundary_clarity_review: RangeBoundaryClarityReview = RangeBoundaryClarityReview.UNREVIEWED
    midpoint_reaction_time: datetime | None = None
    midpoint_reaction_price: float | None = None
    midpoint_reaction_kind: str | None = None
    internal_bos_count: int = 0
    upper_boundary_state: RangeBoundaryState = RangeBoundaryState.ACTIVE
    lower_boundary_state: RangeBoundaryState = RangeBoundaryState.ACTIVE
    recovery_transition_ids: tuple[int, ...] = ()
    invalidating_recovery_transition_ids: tuple[int, ...] = ()

    @property
    def ever_validated(self) -> bool:
        return self.midpoint_reaction_time is not None


def range_review_key(item: RangeInstance) -> tuple[str, datetime, float, datetime, float]:
    """Stable structural identity for manual boundary-clarity review."""
    return (
        item.impulse_direction.value,
        item.first_boundary_time,
        item.first_boundary_price,
        item.second_boundary_time,
        item.second_boundary_price,
    )


@dataclass(frozen=True)
class RangeSweepEpisode:
    episode_id: int
    range_id: int
    side: str
    boundary_price: float
    sweep_candle_index: int
    sweep_time: datetime
    status: str
    resolved_index: int | None = None
    sfp_event_time: datetime | None = None


@dataclass(frozen=True)
class RangeAnalysisReport:
    ranges: tuple[RangeInstance, ...]
    sweep_episodes: tuple[RangeSweepEpisode, ...]
    events: tuple[MarketEvent, ...]
    source_policy: str
    impulse_proxy_policy: str
    midpoint_policy: str
    internal_structure_policy: str
    liquidity_policy: str
    boundary_clarity_policy: str

    @property
    def validated_count(self) -> int:
        return sum(r.ever_validated for r in self.ranges)

    @property
    def sfp_formation_count(self) -> int:
        kinds = {
            MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
            MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED,
        }
        return sum(e.kind in kinds for e in self.events)


class RangeAnalysisError(ValueError):
    pass


def range_review_key_text(item: RangeInstance) -> str:
    direction, first_time, first_price, second_time, second_price = range_review_key(item)
    return chr(124).join((direction, first_time.isoformat(), format(first_price, ".17g"), second_time.isoformat(), format(second_price, ".17g")))


def _event_sort_key(event: MarketEvent) -> tuple:
    return (event.event_time, event.candle_index, event.kind.value, event.level_id)


def _swings(report: MarketAnalysisReport) -> list[MarketEvent]:
    kinds = {MarketEventKind.SWING_HIGH_CONFIRMED, MarketEventKind.SWING_LOW_CONFIRMED}
    return sorted((e for e in report.events if e.kind in kinds), key=_event_sort_key)


def _bos_events(report: MarketAnalysisReport) -> list[MarketEvent]:
    kinds = {MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS}
    return sorted((e for e in report.events if e.kind in kinds), key=_event_sort_key)


def _make_range_candidates(report: MarketAnalysisReport) -> list[RangeInstance]:
    swings = _swings(report)
    candidates: list[RangeInstance] = []
    seen: set[tuple] = set()

    for bos in _bos_events(report):
        if bos.kind == MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS:
            direction = RangeImpulseDirection.UP
            first_event_kind = MarketEventKind.SWING_HIGH_CONFIRMED
            second_event_kind = MarketEventKind.SWING_LOW_CONFIRMED
            first_kind, second_kind = "high", "low"
        else:
            direction = RangeImpulseDirection.DOWN
            first_event_kind = MarketEventKind.SWING_LOW_CONFIRMED
            second_event_kind = MarketEventKind.SWING_HIGH_CONFIRMED
            first_kind, second_kind = "low", "high"

        # Exact-timestamp swing confirmation is not used: event ordering within the same
        # timestamp is not provable from OHLC, so the conservative rule is strictly later.
        first = next(
            (
                e
                for e in swings
                if e.kind == first_event_kind
                and e.event_time > bos.event_time
                and e.candle_index > bos.candle_index
            ),
            None,
        )
        if first is None:
            continue
        second = next(
            (
                e
                for e in swings
                if e.kind == second_event_kind
                and e.event_time > first.event_time
                and e.candle_index > first.candle_index
            ),
            None,
        )
        if second is None:
            continue

        # Directional boundary geometry is part of the qualitative source semantics,
        # not a tunable trading threshold. For an UP impulse, boundary #1 is the
        # impulse-end high and boundary #2 is the later correction low, so the latter
        # must be strictly below the former. DOWN is the mirror case. Using min/max
        # without this guard can silently turn an inverted boundary pair into an
        # apparently valid range. Reject such pairs conservatively.
        if direction == RangeImpulseDirection.UP:
            if not first.price > second.price:
                continue
        else:
            if not first.price < second.price:
                continue

        lower = min(first.price, second.price)
        upper = max(first.price, second.price)
        key = (first.event_time, first.price, second.event_time, second.price)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            RangeInstance(
                range_id=len(candidates) + 1,
                impulse_direction=direction,
                recovery_transition_ids=bos.recovery_transition_ids,
                impulse_bos_kind=bos.kind,
                impulse_bos_time=bos.event_time,
                impulse_bos_candle_index=bos.candle_index,
                first_boundary_kind=first_kind,
                first_boundary_price=first.price,
                first_boundary_time=first.event_time,
                first_boundary_candle_index=first.candle_index,
                second_boundary_kind=second_kind,
                second_boundary_price=second.price,
                second_boundary_time=second.event_time,
                second_boundary_candle_index=second.candle_index,
                lower=lower,
                upper=upper,
                midpoint=(lower + upper) / 2.0,
                status=RangeStatus.WAITING_MIDPOINT_REACTION,
                status_time=second.event_time,
            )
        )
    return candidates


def _swing_near_midpoint(event: MarketEvent, item: RangeInstance, params: RangeDetectionParams) -> bool:
    width = item.upper - item.lower
    tolerance = width * params.midpoint_tolerance_fraction
    return abs(event.price - item.midpoint) <= tolerance



def _validate_candidates(
    candles: Sequence[Candle],
    report: MarketAnalysisReport,
    candidates: list[RangeInstance],
    params: RangeDetectionParams,
) -> list[RangeInstance]:
    swings = _swings(report)
    bos = _bos_events(report)
    out: list[RangeInstance] = []

    for item in candidates:
        # Before the qualitative 0.5 validation is known, boundary raids are not used
        # retroactively as SFPs. They do consume that original boundary liquidity for the
        # later range-boundary SFP layer. This preserves causality and the source concept
        # that deviations can move beyond a range boundary without declaring the whole
        # range invalid solely because of an outside close.
        timeline: dict[datetime, dict[str, list]] = {}
        for i, candle in enumerate(candles):
            if candle.close_time <= item.second_boundary_time:
                continue
            high_sweep = candle.high > item.upper
            low_sweep = candle.low < item.lower
            if high_sweep or low_sweep:
                timeline.setdefault(candle.close_time, {}).setdefault("presweep", []).append(
                    (i, high_sweep, low_sweep)
                )

        for event in bos:
            if event.event_time <= item.second_boundary_time:
                continue
            if item.lower < event.price < item.upper:
                timeline.setdefault(event.event_time, {}).setdefault("internal", []).append(event)

        for event in swings:
            if event.event_time <= item.second_boundary_time:
                continue
            if _swing_near_midpoint(event, item, params):
                timeline.setdefault(event.event_time, {}).setdefault("midpoint", []).append(event)

        internal_seen = 0
        # Boundary liquidity becomes established when boundary #2 is known. Track any
        # first raid after that point even if the qualitative midpoint validation comes later.
        upper_state = RangeBoundaryState.ACTIVE
        lower_state = RangeBoundaryState.ACTIVE
        liquidity_exhausted_time: datetime | None = None
        terminal: RangeInstance | None = None
        for when in sorted(timeline):
            bucket = timeline[when]
            internal_events = bucket.get("internal", [])
            if internal_events:
                internal_seen += len(internal_events)
                if params.require_clean_internal_structure:
                    terminal = replace(
                        item,
                        status=RangeStatus.REJECTED_INTERNAL_STRUCTURE,
                        invalidating_recovery_transition_ids=tuple(sorted({rid for e in internal_events for rid in e.recovery_transition_ids})), 
                        status_time=when,
                        internal_bos_count=internal_seen,
                        upper_boundary_state=upper_state,
                        lower_boundary_state=lower_state,
                    )
                    break

            # Same-timestamp boundary sweep is consumed before midpoint validation.
            # We intentionally do not retroactively create a pending SFP from that candle.
            for _, high_sweep, low_sweep in bucket.get("presweep", []):
                if high_sweep:
                    upper_state = RangeBoundaryState.CONSUMED
                if low_sweep:
                    lower_state = RangeBoundaryState.CONSUMED
            if liquidity_exhausted_time is None and upper_state == RangeBoundaryState.CONSUMED and lower_state == RangeBoundaryState.CONSUMED:
                liquidity_exhausted_time = when

            midpoint_events = bucket.get("midpoint", [])
            if midpoint_events:
                event = midpoint_events[0]
                terminal = replace(
                    item,
                    status=RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED if liquidity_exhausted_time is not None else RangeStatus.VALIDATED,
                    status_time=liquidity_exhausted_time or when,
                    midpoint_reaction_time=when,
                    midpoint_reaction_price=event.price,
                    midpoint_reaction_kind=(
                        "high" if event.kind == MarketEventKind.SWING_HIGH_CONFIRMED else "low"
                    ),
                    internal_bos_count=internal_seen,
                    upper_boundary_state=upper_state,
                    lower_boundary_state=lower_state,
                )
                break

        out.append(
            terminal
            if terminal is not None
            else replace(
                item,
                internal_bos_count=internal_seen,
                upper_boundary_state=upper_state,
                lower_boundary_state=lower_state,
            )
        )
    return out


def _range_level_id(range_id: int, side: str) -> int:
    # Structural levels are positive. Negative IDs keep provenance collision-free.
    return -(range_id * 10 + (1 if side == "high" else 2))


def _range_episode_id(range_id: int, side: str) -> int:
    return -(range_id * 10 + (3 if side == "high" else 4))


def _internal_bos_by_close_time(report: MarketAnalysisReport, item: RangeInstance) -> dict[datetime, list[MarketEvent]]:
    out: dict[datetime, list[MarketEvent]] = {}
    for event in _bos_events(report):
        if item.midpoint_reaction_time is None or event.event_time <= item.midpoint_reaction_time:
            continue
        if item.lower < event.price < item.upper:
            out.setdefault(event.event_time, []).append(event)
    return out


def _scan_range_boundary_sfps(
    candles: Sequence[Candle],
    report: MarketAnalysisReport,
    ranges: list[RangeInstance],
    params: RangeDetectionParams,
) -> tuple[list[RangeInstance], list[RangeSweepEpisode], list[MarketEvent]]:
    updated_ranges: list[RangeInstance] = []
    episodes: list[RangeSweepEpisode] = []
    events: list[MarketEvent] = []

    for original in ranges:
        if original.status != RangeStatus.VALIDATED or original.midpoint_reaction_time is None:
            updated_ranges.append(original)
            continue

        item = original
        # Pre-validation boundary raids were already observed causally by _validate_candidates.
        # Do not resurrect consumed external liquidity when the range becomes validated.
        upper_state = item.upper_boundary_state
        lower_state = item.lower_boundary_state
        pending: tuple[str, int, float] | None = None
        active_sfps: dict[int, MarketEvent] = {}
        range_active = True
        internal_by_time = _internal_bos_by_close_time(report, item)
        internal_count = item.internal_bos_count

        for i, candle in enumerate(candles):
            # Validation is only known at its event timestamp. Candles that opened before that
            # timestamp cannot be retroactively used as post-validation boundary sweeps.
            if candle.open_time < item.midpoint_reaction_time:
                continue

            # At the new candle OPEN, resolve only the prior sweep using this candle's open.
            if pending is not None and i == pending[1] + 1:
                side, sweep_index, boundary = pending
                pending = None
                sweep_candle = candles[sweep_index]
                result = detect_sfp(sweep_candle, candle, boundary, side)
                episode_id = _range_episode_id(item.range_id, side)
                ep_idx = next(j for j, ep in enumerate(episodes) if ep.episode_id == episode_id)
                episodes[ep_idx] = replace(
                    episodes[ep_idx],
                    status=(
                        "SFP_FORMED"
                        if result.valid and item.boundary_clarity_review == RangeBoundaryClarityReview.PASS
                        else "CLARITY_REVIEW_BLOCKED"
                        if result.valid
                        else "CONSUMED_NO_SFP"
                    ),
                    resolved_index=i,
                    sfp_event_time=(
                        candle.open_time
                        if result.valid and item.boundary_clarity_review == RangeBoundaryClarityReview.PASS
                        else None
                    ),
                )
                if result.valid and item.boundary_clarity_review == RangeBoundaryClarityReview.PASS:
                    kind = (
                        MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED
                        if side == "high"
                        else MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED
                    )
                    sfp = MarketEvent(
                        kind=kind,
                        candle_index=i,
                        event_time=candle.open_time,
                        price=candle.open,
                        level_id=_range_level_id(item.range_id, side),
                        level_price=boundary,
                        note=(
                            "Range-boundary SFP formation from a previously validated range boundary; "
                            "range boundary is source-defined external liquidity."
                        ),
                        episode_id=episode_id,
                        member_level_ids=(_range_level_id(item.range_id, side),),
                        sfp_pattern_extreme_price=(
                            sweep_candle.high if side == "high" else sweep_candle.low
                        ),
                        liquidity_origin="RANGE_BOUNDARY",
                        range_id=item.range_id,
                        recovery_transition_ids=item.recovery_transition_ids,
                    )
                    events.append(sfp)
                    active_sfps[episode_id] = sfp

            # At candle CLOSE, apply the source-defined SFP invalidation rule. Existing
            # formed SFP context has its own lifecycle independent of later range deviations.
            invalidated: list[int] = []
            for episode_id, sfp in active_sfps.items():
                extreme = sfp.sfp_pattern_extreme_price
                if extreme is None or candle.close_time <= sfp.event_time:
                    continue
                if sfp.kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED and candle.close < extreme:
                    events.append(
                        MarketEvent(
                            kind=MarketEventKind.BULLISH_SFP_INVALIDATED_CLOSE,
                            candle_index=i,
                            event_time=candle.close_time,
                            price=candle.close,
                            level_id=sfp.level_id,
                            level_price=extreme,
                            note="Range-boundary bullish SFP invalidated by body close below pattern minimum.",
                            episode_id=episode_id,
                            member_level_ids=sfp.member_level_ids,
                            sfp_pattern_extreme_price=extreme,
                            liquidity_origin="RANGE_BOUNDARY",
                            range_id=item.range_id,
                            recovery_transition_ids=item.recovery_transition_ids,
                        )
                    )
                    invalidated.append(episode_id)
                elif sfp.kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED and candle.close > extreme:
                    events.append(
                        MarketEvent(
                            kind=MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE,
                            candle_index=i,
                            event_time=candle.close_time,
                            price=candle.close,
                            level_id=sfp.level_id,
                            level_price=extreme,
                            note="Range-boundary bearish SFP invalidated by body close above pattern maximum.",
                            episode_id=episode_id,
                            member_level_ids=sfp.member_level_ids,
                            sfp_pattern_extreme_price=extreme,
                            liquidity_origin="RANGE_BOUNDARY",
                            range_id=item.range_id,
                            recovery_transition_ids=item.recovery_transition_ids,
                        )
                    )
                    invalidated.append(episode_id)
            for episode_id in invalidated:
                active_sfps.pop(episode_id, None)

            if not range_active:
                continue

            # Conservative source-consistency: after validation, internal BOS also stops
            # NEW range-boundary sweeps if clean internal structure is required.
            internal_now = internal_by_time.get(candle.close_time, [])
            if internal_now:
                internal_count += len(internal_now)
                if params.require_clean_internal_structure:
                    range_active = False
                    pending = None
                    item = replace(
                        item,
                        status=RangeStatus.INVALIDATED_INTERNAL_STRUCTURE,
                        invalidating_recovery_transition_ids=tuple(sorted({rid for e in internal_now for rid in e.recovery_transition_ids})), 
                        status_time=candle.close_time,
                        internal_bos_count=internal_count,
                    )
                    continue

            high_sweep = upper_state == RangeBoundaryState.ACTIVE and candle.high > item.upper
            low_sweep = lower_state == RangeBoundaryState.ACTIVE and candle.low < item.lower

            if high_sweep and low_sweep:
                # Unspecified source edge case: do not manufacture two opposite SFPs.
                upper_state = RangeBoundaryState.CONSUMED
                lower_state = RangeBoundaryState.CONSUMED
                item = replace(item, status=RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED, status_time=candle.close_time)
                range_active = False
                episodes.extend(
                    [
                        RangeSweepEpisode(
                            _range_episode_id(item.range_id, "high"), item.range_id, "high", item.upper,
                            i, candle.close_time, "AMBIGUOUS_DUAL_SIDE_SWEEP", resolved_index=i
                        ),
                        RangeSweepEpisode(
                            _range_episode_id(item.range_id, "low"), item.range_id, "low", item.lower,
                            i, candle.close_time, "AMBIGUOUS_DUAL_SIDE_SWEEP", resolved_index=i
                        ),
                    ]
                )
                continue

            if high_sweep:
                upper_state = RangeBoundaryState.CONSUMED
                if lower_state == RangeBoundaryState.CONSUMED:
                    item = replace(item, status=RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED, status_time=candle.close_time)
                    range_active = False
                episode_id = _range_episode_id(item.range_id, "high")
                episodes.append(
                    RangeSweepEpisode(
                        episode_id, item.range_id, "high", item.upper, i, candle.close_time,
                        "PENDING_NEXT_CANDLE"
                    )
                )
                if i + 1 < len(candles):
                    pending = ("high", i, item.upper)

            if low_sweep:
                lower_state = RangeBoundaryState.CONSUMED
                if upper_state == RangeBoundaryState.CONSUMED:
                    item = replace(item, status=RangeStatus.RETIRED_LIQUIDITY_EXHAUSTED, status_time=candle.close_time)
                    range_active = False
                episode_id = _range_episode_id(item.range_id, "low")
                episodes.append(
                    RangeSweepEpisode(
                        episode_id, item.range_id, "low", item.lower, i, candle.close_time,
                        "PENDING_NEXT_CANDLE"
                    )
                )
                if i + 1 < len(candles):
                    pending = ("low", i, item.lower)

        updated_ranges.append(
            replace(
                item,
                internal_bos_count=internal_count,
                upper_boundary_state=upper_state,
                lower_boundary_state=lower_state,
            )
        )

    return updated_ranges, episodes, sorted(events, key=_event_sort_key)


def analyze_ranges(
    candles: Sequence[Candle],
    base_report: MarketAnalysisReport,
    *,
    params: RangeDetectionParams | None = None,
    boundary_clarity_reviews: dict[tuple[str, datetime, float, datetime, float], RangeBoundaryClarityReview] | None = None,
) -> RangeAnalysisReport:
    params = params or RangeDetectionParams()
    if len(candles) != base_report.candle_count:
        raise RangeAnalysisError("candles/base_report candle count mismatch")
    previous: datetime | None = None
    previous_close: datetime | None = None
    for i, candle in enumerate(candles):
        if not candle.is_closed:
            raise RangeAnalysisError(f"unfinished candle at index {i}")
        if previous is not None and candle.open_time <= previous:
            raise RangeAnalysisError("candles must be strictly chronological")
        if previous_close is not None and candle.open_time < previous_close:
            raise RangeAnalysisError("candles must not overlap")
        previous = candle.open_time
        previous_close = candle.close_time
    if candles and any(event.event_time > candles[-1].close_time for event in base_report.events):
        raise RangeAnalysisError("base_report contains events beyond available history")

    candidates = _make_range_candidates(base_report)
    candidates = _validate_candidates(candles, base_report, candidates, params)
    reviews = boundary_clarity_reviews or {}
    candidates = [
        replace(item, boundary_clarity_review=reviews.get(range_review_key(item), RangeBoundaryClarityReview.UNREVIEWED))
        for item in candidates
    ]
    ranges, episodes, events = _scan_range_boundary_sfps(candles, base_report, candidates, params)

    return RangeAnalysisReport(
        ranges=tuple(ranges),
        sweep_episodes=tuple(episodes),
        events=tuple(events),
        source_policy=(
            "SOURCE: range follows a strong directional impulse; impulse end is boundary #1 and correction end "
            "is boundary #2; a good reaction from 0.5 confirms the range; internal structure should be absent; "
            "validated range boundaries are external liquidity eligible for SFP."
        ),
        impulse_proxy_policy=(
            "TECHNICAL_NORMALIZATION: a structural BOS is the conservative strong-impulse proxy because the "
            "source gives no numeric impulse-strength threshold. This may under-detect ranges."
        ),
        midpoint_policy=(
            "BACKTEST_PARAMETER: a confirmed three-candle swing within midpoint_tolerance_fraction * range_width "
            "of 0.5 is the machine proxy for the qualitative 'good reaction from 0.5'."
        ),
        internal_structure_policy=(
            "SOURCE + TECHNICAL_NORMALIZATION: source says structure should be absent inside range; machine proxy "
            "is an in-range BOS. With require_clean_internal_structure=True it rejects/invalidates the range."
        ),
        liquidity_policy=(
            "SOURCE: range boundary is external liquidity; completed SFP requires boundary sweep, sweep-candle "
            "close back inside, and next candle open inside. TECHNICAL_NORMALIZATION: the first strict raid consumes "
            "that boundary liquidity even if SFP does not complete; the range itself is not invalidated merely by an "
            "outside close because the source explicitly allows deviations beyond range boundaries. Phase 1.4.19 "
            "lifecycle normalization: one consumed boundary leaves the validated range active; after both original "
            "boundaries are consumed the range retires as RETIRED_LIQUIDITY_EXHAUSTED. Consumed boundaries never "
            "reactivate; redraw requires a new independent BOS -> boundary #1 -> boundary #2 -> midpoint candidate."
        ),
        boundary_clarity_policy=(
            "SOURCE NUANCE: the general methodology says a range may lack perfectly crisp boundaries as long as "
            "price trades in a defined area, while the dedicated range module recommends skipping examples whose "
            "boundaries are smeared enough that future price movement becomes difficult to determine. No objective "
            "machine threshold is given, so Phase 1.4.18 uses explicit manual UNREVIEWED/PASS/FAIL boundary-clarity review; only PASS may emit a usable range-boundary SFP, while lifecycle diagnostics continue for all review states."
        ),
    )


def augment_market_report_with_range_sfps(
    candles: Sequence[Candle],
    base_report: MarketAnalysisReport,
    *,
    params: RangeDetectionParams | None = None,
    boundary_clarity_reviews: dict[tuple[str, datetime, float, datetime, float], RangeBoundaryClarityReview] | None = None,
) -> tuple[MarketAnalysisReport, RangeAnalysisReport]:
    range_report = analyze_ranges(
        candles,
        base_report,
        params=params,
        boundary_clarity_reviews=boundary_clarity_reviews,
    )
    merged_events = tuple(sorted((*base_report.events, *range_report.events), key=_event_sort_key))
    merged = replace(
        base_report,
        events=merged_events,
        sfp_liquidity_scope="STRUCTURAL_SWING_AND_RANGE_BOUNDARY_CONSERVATIVE_BOS_PROXY",
    )
    return merged, range_report
