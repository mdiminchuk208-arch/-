"""Opt-in, causal experimental OB/POI references for offline virtual execution.

The archive has no source-approved geometric HTF POI detector. Three-candle
imbalance seeds, numeric displacement filters and the three-target allocation
below are BACKTEST_PARAMETER policies. An eligible result is not a claim of
source certification and never grants permission for exchange execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Sequence

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.market_analysis import (
    MarketAnalysisReport, MarketEventKind, StructureAnalysisMode, TrendState,
)
from crypto_bot.strategy.mtf_sfp import MtfOpportunity
from crypto_bot.strategy.order_block import OrderBlockEvidence, assess_order_block
from crypto_bot.strategy.trade_plan import PriceZone, derive_structural_impulse_context


POI_POLICY = "HTF_THREE_CANDLE_GAP_POI_BACKTEST_PARAMETER"
TARGET_POLICY = "THREE_DISTINCT_OPPOSING_POI_NEAR_EDGES_BACKTEST_PARAMETER"
STOP_POLICY = "SOURCE_OB_EXTREME"
AGGRESSION_POLICY = "BODY_FRACTION_AND_ENGULF_RATIO_BACKTEST_PARAMETER"


@dataclass(frozen=True)
class AutoLevelPolicy:
    min_body_fraction: float = 0.6
    min_engulf_body_ratio: float = 1.0

    def __post_init__(self) -> None:
        if not isfinite(self.min_body_fraction) or not 0 < self.min_body_fraction <= 1:
            raise ValueError("min_body_fraction must be finite in (0, 1]")
        if not isfinite(self.min_engulf_body_ratio) or self.min_engulf_body_ratio < 1:
            raise ValueError("min_engulf_body_ratio must be finite and >= 1")


@dataclass(frozen=True)
class LevelEvidence:
    kind: str
    timeframe_minutes: int
    known_at: datetime
    source_times: tuple[datetime, ...]
    prices: tuple[float, ...]
    policy: str
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.timeframe_minutes <= 0 or self.known_at.utcoffset() is None:
            raise ValueError("evidence requires a timeframe and timezone-aware availability")
        if any(t.utcoffset() is None or t > self.known_at for t in self.source_times):
            raise ValueError("evidence source times must be causal and timezone-aware")
        if not all(isfinite(price) and price > 0 for price in self.prices):
            raise ValueError("evidence prices must be finite and positive")


@dataclass(frozen=True)
class AutomaticLevelResult:
    status: str
    known_at: datetime | None = None
    stop_loss: float | None = None
    targets: tuple[float, ...] = ()
    stop_policy: str = STOP_POLICY
    target_policy: str = TARGET_POLICY
    evidence: tuple[LevelEvidence, ...] = ()
    blocked_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PoiSeed:
    direction: Direction
    zone: PriceZone
    known_at: datetime
    source_times: tuple[datetime, ...]


def _prefix(candles: Sequence[Candle], as_of: datetime) -> tuple[tuple[Candle, ...], int]:
    prefix = tuple(c for c in candles if c.close_time <= as_of)
    if not prefix:
        return prefix, 0
    duration = prefix[0].close_time - prefix[0].open_time
    minutes = duration.total_seconds() / 60
    if not minutes.is_integer() or minutes <= 0:
        raise ValueError("automatic levels require whole-minute candle durations")
    for index, candle in enumerate(prefix):
        if not candle.is_closed or candle.low <= 0 or candle.close_time - candle.open_time != duration:
            raise ValueError("automatic levels require positive closed candles of one duration")
        if index and prefix[index - 1].close_time != candle.open_time:
            raise ValueError("automatic level histories must be chronological and contiguous")
    return prefix, int(minutes)


def _validate_report(report: MarketAnalysisReport, candles: Sequence[Candle], as_of: datetime) -> None:
    if report.analysis_mode != StructureAnalysisMode.SOURCE_CONSERVATIVE:
        raise ValueError("automatic levels require SOURCE_CONSERVATIVE reports")
    if report.candle_count != len(candles):
        raise ValueError("analysis report must match the available candle prefix")
    level_ids = {level.level_id for level in report.levels}
    if len(level_ids) != len(report.levels):
        raise ValueError("duplicate structural level identity")
    for level in report.levels:
        if not 0 <= level.swing_index < level.confirmed_index < len(candles):
            raise ValueError("structural level indexes do not match candle history")
        if (level.confirmed_time != candles[level.confirmed_index].close_time
                or level.swing_time != candles[level.swing_index].open_time
                or level.confirmed_time > as_of):
            raise ValueError("structural level times do not match candle history")
        if level.side not in ("high", "low") or not isfinite(level.price) or level.price <= 0:
            raise ValueError("invalid structural level reference")
        expected_price = candles[level.swing_index].high if level.side == "high" else candles[level.swing_index].low
        if level.price != expected_price:
            raise ValueError("structural level price does not match its swing candle")
    for event in report.events:
        if not 0 <= event.candle_index < len(candles):
            raise ValueError("analysis event index does not match candle history")
        candle = candles[event.candle_index]
        if event.event_time.utcoffset() is None or not candle.open_time <= event.event_time <= candle.close_time:
            raise ValueError("analysis event time does not match its candle")
        if event.event_time > as_of:
            raise ValueError("future analysis event")
    for transition in report.structure_transition_diagnostics:
        if not 0 <= transition.bos_index < len(candles) or transition.bos_time != candles[transition.bos_index].close_time:
            raise ValueError("structure transition BOS identity does not match history")
        if transition.resolved_index is not None:
            if (not transition.bos_index <= transition.resolved_index < len(candles)
                    or transition.resolved_time != candles[transition.resolved_index].close_time):
                raise ValueError("structure transition resolution does not match history")
    if len({t.transition_id for t in report.structure_transition_diagnostics}) != len(report.structure_transition_diagnostics):
        raise ValueError("duplicate structural transition identity")


def _seeds(candles: Sequence[Candle]) -> tuple[_PoiSeed, ...]:
    seeds = []
    for index in range(2, len(candles)):
        first, middle, third = candles[index - 2:index + 1]
        times = (first.close_time, middle.close_time, third.close_time)
        if third.low > first.high:
            seeds.append(_PoiSeed(Direction.LONG, PriceZone(first.high, third.low), third.close_time, times))
        elif third.high < first.low:
            seeds.append(_PoiSeed(Direction.SHORT, PriceZone(third.high, first.low), third.close_time, times))
    return tuple(seeds)


def _overlap(low: float, high: float, zone: PriceZone) -> bool:
    return low <= zone.high and high >= zone.low


def ob_impulse_window(report: MarketAnalysisReport, opportunity: MtfOpportunity,
                      candle_count: int) -> range | None:
    """B-candle indexes in the actual source structural impulse, inclusive of its end.

    BOS confirms a displacement; it does not require the engulfed candle to open
    after that confirmation. The old BOS+2 lower bound discarded the very OB
    causing the break. The previous structural extreme fixes the causal origin;
    the selected anchor fixes the end. C may confirm an IMB just after that end.
    No arbitrary lookback, future extreme or price-distance tolerance is used.
    """
    adverse = "low" if opportunity.expected_direction == Direction.LONG else "high"
    origins = [level for level in report.levels
               if level.side == adverse and level.price == opportunity.impulse_start_price
               and level.swing_index <= opportunity.ltf_bos_candle_index
               and level.confirmed_time <= opportunity.ltf_bos_event_time]
    anchor = next((level for level in report.levels
                   if level.level_id == opportunity.entry_anchor_level_id), None)
    if not origins or anchor is None:
        return None
    origin = max(origins, key=lambda level:(level.swing_index, level.confirmed_index, level.level_id))
    return range(origin.swing_index + 1, min(anchor.swing_index + 1, candle_count - 1))


def _fresh(seed: _PoiSeed, histories: tuple[Sequence[Candle], ...], cutoff: datetime) -> bool:
    # Strictly after formation: the seed's own third candle touches its near edge.
    # A bar straddling availability is treated conservatively as a potential touch.
    return not any(
        seed.known_at < candle.close_time <= cutoff and _overlap(candle.low, candle.high, seed.zone)
        for history in histories for candle in history
    )


def _seed_evidence(seed: _PoiSeed, minutes: int, kind: str) -> LevelEvidence:
    return LevelEvidence(kind, minutes, seed.known_at, seed.source_times,
                         (seed.zone.low, seed.zone.high), POI_POLICY,
                         (("direction", seed.direction.value.upper()),))


def _blocked(*reasons: str, evidence: tuple[LevelEvidence, ...] = ()) -> AutomaticLevelResult:
    return AutomaticLevelResult("BLOCKED", evidence=evidence, blocked_reasons=tuple(sorted(set(reasons))))


def derive_automatic_levels(
    htf_candles: Sequence[Candle], ltf_candles: Sequence[Candle],
    htf_report: MarketAnalysisReport, ltf_report: MarketAnalysisReport,
    opportunity: MtfOpportunity, *, as_of: datetime, policy: AutoLevelPolicy,
) -> AutomaticLevelResult:
    """Return experimental causal virtual references or explicit blocking causes.

    Supporting POI freshness is checked before the initiating OB candle. The
    initiating first reaction may complete A/B/C formation; subsequent OB touches
    consume its first-test eligibility. Opposing target POIs must be fresh now.
    No ATR, fixed-RR targets, private endpoints or actual entry flags exist here.
    """
    if as_of.utcoffset() is None or not isinstance(policy, AutoLevelPolicy):
        raise ValueError("timezone-aware as_of and AutoLevelPolicy are required")
    if opportunity.expected_direction not in (Direction.LONG, Direction.SHORT):
        raise ValueError("opportunity direction must be LONG or SHORT")
    htf, htf_minutes = _prefix(htf_candles, as_of)
    ltf, ltf_minutes = _prefix(ltf_candles, as_of)
    _validate_report(htf_report, htf, as_of)
    _validate_report(ltf_report, ltf, as_of)
    if not htf or not ltf:
        return _blocked("HISTORY_UNAVAILABLE")
    if htf_minutes <= ltf_minutes:
        raise ValueError("HTF must exceed LTF")
    if not opportunity.entry_search_allowed:
        return _blocked("SOURCE_CONTEXT_NOT_ENTRY_ELIGIBLE")
    ready = opportunity.entry_geometry_ready_time
    if ready is None:
        return _blocked("ENTRY_GEOMETRY_NOT_READY")
    if ready.utcoffset() is None:
        raise ValueError("entry geometry availability must be timezone-aware")
    if opportunity.ltf_bos_event_time.utcoffset() is None:
        raise ValueError("BOS event time must be timezone-aware")
    if ready > as_of:
        return _blocked("ENTRY_GEOMETRY_NOT_READY")
    direction = opportunity.expected_direction
    expected_bos = (MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS if direction == Direction.LONG
                    else MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS)
    matching_bos = [event for event in ltf_report.events
                    if event.kind == expected_bos and event.candle_index == opportunity.ltf_bos_candle_index
                    and event.event_time == opportunity.ltf_bos_event_time
                    and event.level_id == opportunity.ltf_bos_level_id
                    and event.level_price == opportunity.ltf_bos_level_price]
    if opportunity.ltf_bos_kind != expected_bos or len(matching_bos) != 1:
        return _blocked("EXACT_SOURCE_BOS_NOT_FOUND")
    if matching_bos[0].recovery_transition_ids or opportunity.ltf_recovery_transition_ids or opportunity.htf_recovery_transition_ids:
        return _blocked("TECHNICAL_RECOVERY_LINEAGE_NOT_ENTRY_ELIGIBLE")
    protected = next((level for level in ltf_report.levels if level.level_id == matching_bos[0].level_id), None)
    bos_candle = ltf[opportunity.ltf_bos_candle_index]
    if (protected is None or protected.price != opportunity.ltf_bos_level_price
            or protected.side != ("high" if direction == Direction.LONG else "low")
            or protected.confirmed_time > bos_candle.open_time
            or matching_bos[0].price != bos_candle.close
            or not (bos_candle.close > protected.price if direction == Direction.LONG else bos_candle.close < protected.price)):
        return _blocked("BOS_CANDLE_DOES_NOT_ACCEPT_BEYOND_STRUCTURAL_LEVEL")
    context = derive_structural_impulse_context(
        direction=direction, ltf_report=ltf_report, bos_kind=expected_bos,
        bos_index=opportunity.ltf_bos_candle_index, bos_time=opportunity.ltf_bos_event_time,
    )
    if context is None:
        return _blocked("EXPECTED_OPPOSITE_STRUCTURAL_IMPULSE_NOT_FOUND")
    transition = next(t for t in ltf_report.structure_transition_diagnostics if t.transition_id == context.transition_id)
    expected_trend = TrendState.BULLISH if direction == Direction.LONG else TrendState.BEARISH
    if transition.expected_trend != expected_trend or transition.from_trend != (TrendState.BEARISH if direction == Direction.LONG else TrendState.BULLISH):
        return _blocked("EXPECTED_OPPOSITE_STRUCTURAL_IMPULSE_NOT_FOUND")
    if (context.transition_id != opportunity.entry_geometry_transition_id
            or context.ready_time != ready or context.anchor_level_id != opportunity.entry_anchor_level_id
            or context.correction_level_id != opportunity.entry_correction_level_id
            or context.entry_zone.low != opportunity.entry_zone_low
            or context.entry_zone.high != opportunity.entry_zone_high):
        raise ValueError("opportunity geometry does not match the source structural transition")
    zone = context.entry_zone
    levels_by_id = {level.level_id: level for level in ltf_report.levels}
    anchor = levels_by_id[context.anchor_level_id]
    correction = levels_by_id[context.correction_level_id]
    if anchor.confirmed_time > ready or correction.confirmed_time > ready:
        raise ValueError("entry geometry cannot precede its confirming structural levels")
    impulse_low, impulse_high = sorted((context.impulse_start_price, context.impulse_end_price))
    seeds = _seeds(htf)
    histories = (htf, ltf)
    expected_sweep = MarketEventKind.LOW_LIQUIDITY_TAKEN if direction == Direction.LONG else MarketEventKind.HIGH_LIQUIDITY_TAKEN
    failures: set[str] = set()
    valid = []
    window = ob_impulse_window(ltf_report, opportunity, len(ltf))
    if window is None:
        return _blocked("IMPULSE_ORIGIN_REFERENCE_NOT_FOUND")
    for index in window:
        first, engulfing, third = ltf[index - 1:index + 2]
        first_body = abs(first.close - first.open)
        body = abs(engulfing.close - engulfing.open)
        colors_match = (first.close < first.open and engulfing.close > engulfing.open) if direction == Direction.LONG else (first.close > first.open and engulfing.close < engulfing.open)
        if not colors_match:
            continue
        if not (min(engulfing.open, engulfing.close) <= min(first.open, first.close)
                and max(engulfing.open, engulfing.close) >= max(first.open, first.close)
                and body > first_body):
            continue
        failures.add("NO_ELIGIBLE_IMPULSE_OB")
        if body / (engulfing.high - engulfing.low) < policy.min_body_fraction or body < policy.min_engulf_body_ratio * first_body:
            failures.add("AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET")
            continue
        imbalance = third.low > first.high if direction == Direction.LONG else third.high < first.low
        if not imbalance:
            failures.add("DIRECTIONAL_IMBALANCE_NOT_CONFIRMED")
            continue
        ob_zone = PriceZone(first.low, first.high)
        if not _overlap(first.low, first.high, zone) or any(c.low < impulse_low or c.high > impulse_high for c in (first, engulfing, third)):
            failures.add("OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE")
            continue
        sweeps = [event for event in ltf_report.events
                  if event.kind == expected_sweep and event.candle_index == index - 1
                  and event.event_time == first.close_time
                  and event.level_id in levels_by_id
                  and levels_by_id[event.level_id].confirmed_time <= first.open_time
                  and levels_by_id[event.level_id].side == ("low" if direction == Direction.LONG else "high")
                  and event.level_price == levels_by_id[event.level_id].price]
        sweeps = [event for event in sweeps if (first.low < event.level_price if direction == Direction.LONG else first.high > event.level_price)]
        if not sweeps:
            failures.add("RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND")
            continue
        supporting = [seed for seed in seeds if seed.direction == direction
                      and seed.known_at <= first.open_time and _overlap(first.low, first.high, seed.zone)
                      and _fresh(seed, histories, first.open_time)]
        if not supporting:
            failures.add("FRESH_PREEXISTING_HTF_POI_NOT_FOUND")
            continue
        # The exact expected-opposite resolution is proof of structural/trend alignment;
        # the final report trend alone could belong to a later unrelated transition.
        assessment = assess_order_block(OrderBlockEvidence(
            liquidity_swept=True, aggressive_impulse=True, engulfs_previous_candle=True,
            bos_confirmed=True, in_htf_poi=True, in_structural_impulse=True,
            aligned_with_trend=(transition.resolved_trend == expected_trend),
            imbalance_present=True,
        ))
        if not assessment.trade_eligible:
            failures.add("ORDER_BLOCK_ASSESSMENT_BLOCKED")
            continue
        if any(c.close_time > third.close_time and _overlap(c.low, c.high, ob_zone) for c in ltf):
            failures.add("OB_FIRST_TEST_ALREADY_CONSUMED")
            continue
        stop = first.low if direction == Direction.LONG else first.high
        stop_protects_ote = stop < zone.low if direction == Direction.LONG else stop > zone.high
        if not stop_protects_ote:
            failures.add("OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE")
            continue
        supporting.sort(key=lambda seed: (seed.known_at, seed.zone.low, seed.zone.high))
        seed = supporting[-1]
        sweep = min(sweeps, key=lambda event: (event.level_price, event.level_id))
        known_at = max(ready, third.close_time, seed.known_at)
        evidence = (
            _seed_evidence(seed, htf_minutes, "SUPPORTING_HTF_POI"),
            LevelEvidence("LTF_OB", ltf_minutes, max(third.close_time, opportunity.ltf_bos_event_time),
                          (first.close_time, engulfing.close_time, third.close_time),
                          (first.low, first.high, stop), "OB_BODY_ENGULF_IMBALANCE_IN_SOURCE_STRUCTURAL_IMPULSE",
                          (("bos_relation", "BEFORE_OR_AT_BOS" if engulfing.close_time <= opportunity.ltf_bos_event_time
                            else "AFTER_BOS_IN_SAME_IMPULSE"),
                           ("window_start_b_index", str(window.start)),
                           ("window_end_b_index_exclusive", str(window.stop)))),
            LevelEvidence("AGGRESSIVE_IMPULSE", ltf_minutes, engulfing.close_time,
                          (first.close_time, engulfing.close_time), (), AGGRESSION_POLICY,
                          (("body_fraction", format(body / (engulfing.high - engulfing.low), ".17g")),
                           ("body_ratio", format(body / first_body, ".17g")),
                           ("min_body_fraction", str(policy.min_body_fraction)),
                           ("min_engulf_body_ratio", str(policy.min_engulf_body_ratio)))),
            LevelEvidence("RAW_STRUCTURAL_LIQUIDITY_SWEEP", ltf_minutes, first.close_time,
                          (levels_by_id[sweep.level_id].confirmed_time, first.close_time),
                          (sweep.level_price,), "STRICT_STRUCTURAL_LIQUIDITY_TAKE_NORMALIZATION",
                          (("level_id", str(sweep.level_id)),)),
            LevelEvidence("EXPECTED_OPPOSITE_STRUCTURE", ltf_minutes, ready,
                          (opportunity.ltf_bos_event_time, ready),
                          (context.impulse_start_price, context.impulse_end_price),
                          "SOURCE_CONSERVATIVE_EXPECTED_OPPOSITE_STRUCTURE_NORMALIZATION",
                          (("transition_id", str(context.transition_id)),)),
            LevelEvidence("STOP", ltf_minutes, known_at, (first.close_time,), (stop,), STOP_POLICY),
        )
        valid.append((known_at, first.open_time, stop, evidence))
    if not valid:
        return _blocked(*(failures or {"NO_OB_PATTERN_IN_STRUCTURAL_IMPULSE"}))
    known_at, _, stop, evidence = min(valid, key=lambda candidate: (candidate[0], candidate[1], candidate[2]))
    opposing = [seed for seed in seeds if seed.direction != direction and _fresh(seed, histories, as_of)
                and (seed.zone.low > zone.high if direction == Direction.LONG else seed.zone.high < zone.low)]
    opposing.sort(key=lambda seed: (seed.zone.low, seed.zone.high, seed.known_at) if direction == Direction.LONG
                  else (-seed.zone.high, -seed.zone.low, seed.known_at))
    selected: list[_PoiSeed] = []
    for seed in opposing:
        if any(_overlap(seed.zone.low, seed.zone.high, existing.zone) for existing in selected):
            continue
        selected.append(seed)
        if len(selected) == 3:
            break
    if len(selected) < 3:
        return _blocked("THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND", evidence=evidence)
    targets = tuple(seed.zone.low if direction == Direction.LONG else seed.zone.high for seed in selected)
    target_evidence = tuple(_seed_evidence(seed, htf_minutes, f"TARGET_POI_{index}")
                            for index, seed in enumerate(selected, 1))
    known_at = max(known_at, *(seed.known_at for seed in selected))
    allocation = LevelEvidence("TARGET_SELECTION", htf_minutes, known_at,
                               tuple(seed.known_at for seed in selected), targets, TARGET_POLICY)
    return AutomaticLevelResult("READY", known_at, stop, targets, STOP_POLICY, TARGET_POLICY,
                                (*evidence, *target_evidence, allocation))
