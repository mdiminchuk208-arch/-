"""Offline causal snapshots shared by BACKTEST and closed-candle SHADOW observers.

There is no execution adapter. Level inputs can be explicit caller assertions or
an opt-in experimental detector; automatic selection is not source certification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from math import isfinite
from typing import Mapping, Sequence

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.auto_levels import AutoLevelPolicy, LevelEvidence, derive_automatic_levels
from crypto_bot.strategy.market_analysis import StructureAnalysisMode, analyze_market
from crypto_bot.strategy.mtf_sfp import MtfSfpReport, attach_source_qualified_trade_levels, link_sfp_formations_to_ltf_bos
from crypto_bot.strategy.range_engine import RangeAnalysisReport, augment_market_report_with_range_sfps
from crypto_bot.strategy.trade_plan import PriceZone, rr_ratio


STRATEGY_VERSION = "0.4.22-source-gate.3"

SOURCE_POI_KINDS = {
    "ORDER_BLOCK",
    "BREAKER_BLOCK",
    "DEMAND",
    "SUPPLY",
    "MANIPULATION",
    "RANGE_POI",
    "OTHER_SOURCE_QUALIFIED",
}
SOURCE_ENTRY_PATHS = {
    "DIRECT_OB",
    "CONSERVATIVE_HTF_LTF",
    "BREAKER",
    "STB_BTS",
    "RANGE_DEVIATION",
    "OTHER_SOURCE_QUALIFIED",
}


class EngineMode(str, Enum):
    BACKTEST = "BACKTEST"
    SHADOW = "SHADOW"


@dataclass(frozen=True)
class SourceQualification:
    """Auditable caller assertion for methodology context not yet fully automated.

    This is deliberately stricter than a free-form "qualified" label. It does not
    invent detectors for qualitative source concepts; instead, a caller supplying
    manual/source-derived levels must state which source POI/path was used and must
    explicitly attest the context gates that the supplied material requires.
    """
    known_at: datetime
    poi_kind: str
    entry_path: str
    poi_source: str
    structure_path_confirmed: bool
    order_flow_aligned: bool
    opposing_liquidity_cleared: bool
    premium_discount_valid: bool
    fresh_untested: bool
    evidence: tuple[str, ...]
    repeat_test_ltf_reaction_confirmed: bool = False
    repeat_test_ltf_reaction_known_at: datetime | None = None
    repeat_test_ltf_reaction_evidence: tuple[str, ...] = ()

    def __post_init__(self):
        if self.known_at.utcoffset() is None:
            raise ValueError("source qualification known_at must be timezone-aware")
        if self.poi_kind not in SOURCE_POI_KINDS:
            raise ValueError("unsupported source POI kind")
        if self.entry_path not in SOURCE_ENTRY_PATHS:
            raise ValueError("unsupported source entry path")
        if not self.poi_source.strip():
            raise ValueError("source qualification requires POI provenance")
        if not self.evidence or any(not item.strip() for item in self.evidence):
            raise ValueError("source qualification requires nonempty evidence")
        repeat_proof_supplied = (
            self.repeat_test_ltf_reaction_confirmed
            or self.repeat_test_ltf_reaction_known_at is not None
            or bool(self.repeat_test_ltf_reaction_evidence)
        )
        if repeat_proof_supplied:
            if self.poi_kind != "ORDER_BLOCK":
                raise ValueError("repeat-test LTF reaction qualification is only valid for ORDER_BLOCK")
            if self.fresh_untested:
                raise ValueError("repeat-test LTF reaction qualification requires a previously tested ORDER_BLOCK")
            if not self.repeat_test_ltf_reaction_confirmed:
                raise ValueError("repeat-test LTF reaction proof must be explicitly confirmed")
            if self.repeat_test_ltf_reaction_known_at is None:
                raise ValueError("repeat-test LTF reaction proof requires known_at")
            if self.repeat_test_ltf_reaction_known_at.utcoffset() is None:
                raise ValueError("repeat-test LTF reaction known_at must be timezone-aware")
            if self.repeat_test_ltf_reaction_known_at > self.known_at:
                raise ValueError("source qualification cannot precede repeat-test LTF reaction proof")
            if (not self.repeat_test_ltf_reaction_evidence
                    or any(not item.strip() for item in self.repeat_test_ltf_reaction_evidence)):
                raise ValueError("repeat-test LTF reaction proof requires nonempty evidence")

    @property
    def poi_freshness_valid(self) -> bool:
        return self.fresh_untested or (
            self.poi_kind == "ORDER_BLOCK"
            and self.repeat_test_ltf_reaction_confirmed
            and self.repeat_test_ltf_reaction_known_at is not None
            and bool(self.repeat_test_ltf_reaction_evidence)
        )

    @property
    def canonical_ready(self) -> bool:
        return all((
            self.structure_path_confirmed,
            self.order_flow_aligned,
            self.opposing_liquidity_cleared,
            self.premium_discount_valid,
            self.poi_freshness_valid,
        ))


@dataclass(frozen=True)
class QualifiedLevels:
    """Caller-supplied source levels plus their auditable source context."""
    known_at: datetime
    stop_loss: float
    targets: tuple[float, float, float]
    stop_policy: str
    target_policy: str
    qualification: SourceQualification | None = None

    def __post_init__(self):
        if self.known_at.utcoffset() is None:
            raise ValueError("known_at must be timezone-aware")
        if len(self.targets) != 3 or not all(isfinite(p) and p > 0 for p in (self.stop_loss, *self.targets)):
            raise ValueError("one positive finite stop and three targets are required")
        if not self.stop_policy.strip() or not self.target_policy.strip():
            raise ValueError("source qualification policies are required")
        if self.qualification is not None and self.qualification.known_at > self.known_at:
            raise ValueError("level availability cannot precede source qualification")


@dataclass(frozen=True)
class StrategySignal:
    signal_id: str
    symbol: str
    htf_minutes: int
    ltf_minutes: int
    direction: Direction
    event_time: datetime
    sfp_time: datetime
    bos_time: datetime
    status: str
    score: int
    reasons: tuple[str, ...]
    invalidation_reasons: tuple[str, ...] = ()
    entry_zone: PriceZone | None = None
    optimal_entry: float | None = None
    stop_loss: float | None = None
    targets: tuple[float, ...] = ()
    mode: EngineMode = EngineMode.BACKTEST
    analysis_mode: StructureAnalysisMode = StructureAnalysisMode.SOURCE_CONSERVATIVE
    strategy_version: str = STRATEGY_VERSION
    entry_policy: str = "MIDPOINT_OF_OTE_BACKTEST_PARAMETER"
    score_policy: str = "EVIDENCE_35_SFP_30_BOS_20_OTE_15_LEVELS_BACKTEST_PARAMETER"
    entry_geometry_ready_time: datetime | None = None
    levels_known_at: datetime | None = None
    level_policy: str = "EXPLICIT_QUALIFIED_LEVELS_ONLY"
    level_evidence: tuple[LevelEvidence, ...] = ()
    level_blocking_reasons: tuple[str, ...] = ()
    rr_minimum: float | None = None
    rr_maximum: float | None = None
    rr_at_optimal_entry: float | None = None
    source_qualification_known_at: datetime | None = None
    source_poi_kind: str = ""
    source_entry_path: str = ""
    source_qualification_evidence: tuple[str, ...] = ()
    trade_entry_allowed: bool = field(default=False, init=False)

    def __post_init__(self):
        if (self.status == "READY_FOR_VIRTUAL_ENTRY"
                and self.level_policy != "EXPLICIT_QUALIFIED_LEVELS_ONLY"):
            raise ValueError(
                "canonical READY requires explicitly source-qualified levels; "
                "research proxies cannot be promoted to virtual entry"
            )
        if self.status == "READY_FOR_VIRTUAL_ENTRY":
            if self.source_qualification_known_at is None or not self.source_poi_kind or not self.source_entry_path:
                raise ValueError("canonical READY requires auditable source qualification")
            if not self.source_qualification_evidence:
                raise ValueError("canonical READY requires source qualification evidence")


@dataclass(frozen=True)
class StrategySnapshot:
    symbol: str
    as_of: datetime
    mode: EngineMode
    candle_counts: tuple[tuple[int, int], ...]
    mtf: MtfSfpReport
    ranges: tuple[tuple[int, RangeAnalysisReport], ...]
    signals: tuple[StrategySignal, ...]
    trade_entry_allowed: bool = field(default=False, init=False)


def opportunity_key(symbol: str, htf: int, ltf: int, opportunity) -> str:
    """Stable identity independent of run-local sequential IDs and future candles."""
    parts = (symbol, str(htf), str(ltf), opportunity.expected_direction.value,
             opportunity.ltf_bos_kind.value, opportunity.ltf_bos_event_time.isoformat(),
             format(opportunity.ltf_bos_level_price, '.17g'))
    return sha256('|'.join(parts).encode('utf-8')).hexdigest()[:24]


def _source_qualification_blocker(
    qualification: SourceQualification | None,
    *,
    direction: Direction,
    htf_minutes: int,
    ltf_minutes: int,
) -> str | None:
    if qualification is None:
        return "SOURCE_QUALIFICATION_MISSING"
    if not qualification.structure_path_confirmed:
        return "SOURCE_STRUCTURE_PATH_NOT_CONFIRMED"
    if not qualification.order_flow_aligned:
        return "SOURCE_ORDER_FLOW_NOT_ALIGNED"
    if not qualification.opposing_liquidity_cleared:
        return "LIQUIDITY_AGAINST_SETUP"
    if not qualification.premium_discount_valid:
        return "SOURCE_PREMIUM_DISCOUNT_NOT_VALID"
    if not qualification.poi_freshness_valid:
        return "SOURCE_POI_NOT_FRESH"
    if qualification.poi_kind == "DEMAND" and direction != Direction.LONG:
        return "DEMAND_REQUIRES_LONG"
    if qualification.poi_kind == "SUPPLY" and direction != Direction.SHORT:
        return "SUPPLY_REQUIRES_SHORT"
    if qualification.entry_path == "CONSERVATIVE_HTF_LTF":
        if not (1 <= ltf_minutes <= 15 and 15 <= htf_minutes <= 1440):
            return "CONSERVATIVE_HTF_LTF_TIMEFRAME_OUT_OF_SOURCE_RANGE"
    return None


def evaluate_snapshot(
    histories: Mapping[int, Sequence[Candle]], *, symbol: str, as_of: datetime,
    htf_minutes: int = 60, ltf_minutes: int = 5, mode: EngineMode | str = EngineMode.BACKTEST,
    qualified_levels: Mapping[str, QualifiedLevels] | None = None,
    auto_level_policy: AutoLevelPolicy | None = None,
) -> StrategySnapshot:
    """Read only history with close_time <= as_of; never backdate a decision.

    Both timeframes must be internally contiguous. Missing bars fail closed rather
    than interpreting separated candles as adjacent confirmations. Range clarity
    uses causal automatic boundary proof; this interface accepts no manual reviews.
    """
    mode = EngineMode(mode)
    if auto_level_policy is not None and not isinstance(auto_level_policy, AutoLevelPolicy):
        raise ValueError("automatic levels require an AutoLevelPolicy")
    if auto_level_policy is not None and qualified_levels:
        raise ValueError("automatic and caller-qualified levels cannot be combined")
    symbol = symbol.strip().upper()
    if not symbol or as_of.utcoffset() is None:
        raise ValueError("symbol and timezone-aware as_of are required")
    if not isinstance(htf_minutes, int) or not isinstance(ltf_minutes, int) or not 0 < ltf_minutes < htf_minutes:
        raise ValueError("integer timeframes must satisfy 0 < LTF < HTF")
    reports, ranges, counts, prefixes = {}, [], [], {}
    for minutes in (ltf_minutes, htf_minutes):
        if minutes not in histories:
            raise ValueError(f"missing timeframe {minutes}")
        candles = [c for c in histories[minutes] if c.close_time <= as_of]
        previous = None
        for candle in candles:
            if not candle.is_closed or candle.close_time - candle.open_time != timedelta(minutes=minutes):
                raise ValueError("snapshot requires closed candles of the declared duration")
            if candle.low <= 0:
                raise ValueError("market prices must be positive")
            if previous is not None and candle.open_time != previous:
                raise ValueError("snapshot history must be chronological and contiguous")
            previous = candle.close_time
        base = analyze_market(candles, timeframe_minutes=minutes)
        merged, range_report = augment_market_report_with_range_sfps(candles, base)
        reports[minutes] = merged
        ranges.append((minutes, range_report))
        counts.append((minutes, len(candles)))
        prefixes[minutes] = candles
    ltf = prefixes[ltf_minutes]
    mtf = link_sfp_formations_to_ltf_bos(reports[htf_minutes], reports[ltf_minutes],
        htf_minutes=htf_minutes, ltf_minutes=ltf_minutes,
        ltf_observation_start=ltf[0].open_time if ltf else None,
        ltf_observation_end=ltf[-1].close_time if ltf else None)
    by_id = {c.candidate_id: c for c in mtf.candidates}
    signals = signals_from_opportunities(
        mtf.opportunities, by_id, reports[htf_minutes], reports[ltf_minutes],
        prefixes[htf_minutes], ltf, symbol=symbol, as_of=as_of, htf_minutes=htf_minutes,
        ltf_minutes=ltf_minutes, mode=mode, qualified_levels=qualified_levels,
        auto_level_policy=auto_level_policy,
    )
    return StrategySnapshot(symbol, as_of, mode, tuple(counts), mtf, tuple(ranges), signals)


def signals_from_opportunities(opportunities, by_id, htf_report, ltf_report,
                               htf_candles, ltf_candles, *, symbol, as_of, htf_minutes,
                               ltf_minutes, mode, qualified_levels=None, auto_level_policy=None,
                               automatic_results=None):
    """Shared signal construction; availability gates also apply to indexed replay."""
    signals = []
    for opp in sorted(opportunities, key=lambda o: (o.ltf_bos_event_time, o.expected_direction.value, o.ltf_bos_level_price)):
        key = opportunity_key(symbol, htf_minutes, ltf_minutes, opp)
        contexts = [by_id[cid] for cid in opp.candidate_ids]
        invalid = all(c.sfp_invalidation_event_time is not None and c.sfp_invalidation_event_time <= as_of for c in contexts)
        reasons = ["HTF_SFP_FORMED", "LTF_BOS_STRICTLY_AFTER_SFP"]
        score, zone, entry, stop, targets, levels_time = 65, None, None, None, (), None
        rr_minimum = rr_maximum = rr_optimal = None
        source_qualification_known_at = None
        source_poi_kind = ""
        source_entry_path = ""
        source_qualification_evidence = ()
        entry_policy = "MIDPOINT_OF_OTE_BACKTEST_PARAMETER"
        level_policy = ("AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION" if auto_level_policy is not None
                        else "EXPLICIT_QUALIFIED_LEVELS_ONLY")
        level_evidence, blocking_reasons = (), ()
        status = "WAITING_FOR_ENTRY_GEOMETRY"
        if not opp.entry_search_allowed:
            status = opp.entry_plan_status if opp.entry_plan_status == "REJECTED_ENTRY_GEOMETRY" else "SOURCE_CONTEXT_BLOCKED"
            reasons.append(opp.entry_geometry_policy or "SOURCE_CONTEXT_NOT_ENTRY_ELIGIBLE")
        elif opp.entry_geometry_ready_time is not None and opp.entry_geometry_ready_time <= as_of:
            zone = PriceZone(opp.entry_zone_low, opp.entry_zone_high)
            entry = (zone.low + zone.high) / 2
            score += 20
            reasons.append("EXPECTED_OPPOSITE_STRUCTURE_AND_OTE_READY")
            status = "WAITING_FOR_SOURCE_LEVELS"
            levels = (qualified_levels or {}).get(key)
            if auto_level_policy is not None and not invalid:
                status = "WAITING_FOR_AUTO_LEVELS"
                automatic = ((automatic_results or {}).get(key) or derive_automatic_levels(
                    htf_candles, ltf_candles, htf_report, ltf_report, opp,
                    as_of=as_of, policy=auto_level_policy,
                ))
                level_evidence, blocking_reasons = automatic.evidence, automatic.blocked_reasons
                reasons.append(level_policy)
                if automatic.status == "READY":
                    if automatic.execution_zone is not None and automatic.entry_reference is not None:
                        zone = automatic.execution_zone
                        entry = automatic.entry_reference
                        entry_policy = automatic.entry_policy
                    status = "WAITING_FOR_SOURCE_LEVELS"
                    blocking_reasons = ("AUTO_RESEARCH_PROXY_NOT_SOURCE_QUALIFIED",)
                    reasons.append("AUTO_RESEARCH_PROXY_READY_NOT_SOURCE_QUALIFIED")
                else:
                    status = "WAITING_FOR_AUTO_LEVELS"
                    reasons.extend(blocking_reasons)
            if levels is not None and levels.known_at <= as_of and not invalid:
                qualification = levels.qualification
                blocker = _source_qualification_blocker(
                    qualification,
                    direction=opp.expected_direction,
                    htf_minutes=htf_minutes,
                    ltf_minutes=ltf_minutes,
                )
                if blocker is not None:
                    status = "WAITING_FOR_SOURCE_QUALIFICATION"
                    blocking_reasons = (blocker,)
                    reasons.append(blocker)
                else:
                    assert qualification is not None
                    qualified = attach_source_qualified_trade_levels(
                        opp, stop_loss_price=levels.stop_loss, target_price=levels.targets[0],
                        stop_loss_policy=levels.stop_policy, target_policy=levels.target_policy,
                    )
                    signed = [p if opp.expected_direction == Direction.LONG else -p for p in levels.targets]
                    if not signed[0] < signed[1] < signed[2]:
                        raise ValueError("TP1/TP2/TP3 must be strictly ordered in profit direction")
                    for target in levels.targets:
                        for edge in (zone.low, zone.high):
                            rr_ratio(direction=opp.expected_direction, entry_price=edge,
                                     stop_loss_price=qualified.stop_loss_price, target_price=target)
                    stop, targets = qualified.stop_loss_price, levels.targets
                    edge_rr = [rr_ratio(direction=opp.expected_direction, entry_price=edge,
                                       stop_loss_price=stop, target_price=targets[0])
                               for edge in (zone.low, zone.high)]
                    rr_minimum, rr_maximum = min(edge_rr), max(edge_rr)
                    rr_optimal = rr_ratio(direction=opp.expected_direction, entry_price=entry,
                                          stop_loss_price=stop, target_price=targets[0])
                    levels_time = levels.known_at
                    source_qualification_known_at = qualification.known_at
                    source_poi_kind = qualification.poi_kind
                    source_entry_path = qualification.entry_path
                    source_qualification_evidence = (
                        qualification.evidence + qualification.repeat_test_ltf_reaction_evidence
                    )
                    score += 15
                    freshness_reason = (
                        "SOURCE_POI_FRESH" if qualification.fresh_untested
                        else "SOURCE_OB_REPEAT_TEST_LTF_REACTION_CONFIRMED"
                    )
                    reasons.extend((
                        levels.stop_policy,
                        levels.target_policy,
                        f"SOURCE_POI_{qualification.poi_kind}",
                        f"SOURCE_ENTRY_PATH_{qualification.entry_path}",
                        "SOURCE_ORDER_FLOW_ALIGNED",
                        "SOURCE_OPPOSING_LIQUIDITY_CLEARED",
                        "SOURCE_PREMIUM_DISCOUNT_VALID",
                        freshness_reason,
                    ))
                    status = "READY_FOR_VIRTUAL_ENTRY"
        if invalid:
            status = "INVALIDATED"
        signals.append(StrategySignal(
            signal_id=key, symbol=symbol, htf_minutes=htf_minutes, ltf_minutes=ltf_minutes,
            direction=opp.expected_direction, event_time=as_of, sfp_time=opp.latest_sfp_time,
            bos_time=opp.ltf_bos_event_time, status=status, score=score, reasons=tuple(reasons),
            invalidation_reasons=("ALL_HTF_SFP_CONTEXTS_INVALIDATED",) if invalid else (),
            entry_zone=zone, optimal_entry=entry, stop_loss=stop, targets=targets, mode=mode,
            entry_geometry_ready_time=opp.entry_geometry_ready_time, levels_known_at=levels_time,
            level_policy=level_policy, level_evidence=level_evidence,
            level_blocking_reasons=blocking_reasons,
            entry_policy=entry_policy,
            rr_minimum=rr_minimum, rr_maximum=rr_maximum, rr_at_optimal_entry=rr_optimal,
            source_qualification_known_at=source_qualification_known_at,
            source_poi_kind=source_poi_kind,
            source_entry_path=source_entry_path,
            source_qualification_evidence=source_qualification_evidence,
        ))
    return tuple(signals)