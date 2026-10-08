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


STRATEGY_VERSION = "0.4.20-replay.4"


class EngineMode(str, Enum):
    BACKTEST = "BACKTEST"
    SHADOW = "SHADOW"


@dataclass(frozen=True)
class QualifiedLevels:
    """Caller asserts source qualification and supplies its causal availability time."""
    known_at: datetime
    stop_loss: float
    targets: tuple[float, float, float]
    stop_policy: str
    target_policy: str

    def __post_init__(self):
        if self.known_at.utcoffset() is None:
            raise ValueError("known_at must be timezone-aware")
        if len(self.targets) != 3 or not all(isfinite(p) and p > 0 for p in (self.stop_loss, *self.targets)):
            raise ValueError("one positive finite stop and three targets are required")
        if not self.stop_policy.strip() or not self.target_policy.strip():
            raise ValueError("source qualification policies are required")


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
    trade_entry_allowed: bool = field(default=False, init=False)


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


def evaluate_snapshot(
    histories: Mapping[int, Sequence[Candle]], *, symbol: str, as_of: datetime,
    htf_minutes: int = 60, ltf_minutes: int = 5, mode: EngineMode | str = EngineMode.BACKTEST,
    qualified_levels: Mapping[str, QualifiedLevels] | None = None,
    auto_level_policy: AutoLevelPolicy | None = None,
) -> StrategySnapshot:
    """Read only history with close_time <= as_of; never backdate a decision.

    Both timeframes must be internally contiguous. Missing bars fail closed rather
    than interpreting separated candles as adjacent confirmations. Range clarity
    defaults to UNREVIEWED; this interface cannot silently approve past ranges.
    """
    mode = EngineMode(mode)  # LIVE/PAPER and arbitrary mode strings are rejected.
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
        level_policy = ("AUTO_NORMALIZED_EVIDENCE_PENDING_SOURCE_REVIEW" if auto_level_policy is not None
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
                    levels = QualifiedLevels(automatic.known_at, automatic.stop_loss, automatic.targets,
                                             automatic.stop_policy, automatic.target_policy)
                else:
                    status = "WAITING_FOR_AUTO_LEVELS"
                    reasons.extend(blocking_reasons)
            if levels is not None and levels.known_at <= as_of and not invalid:
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
                rr_minimum, rr_maximum = qualified.rr_minimum, qualified.rr_maximum
                rr_optimal = rr_ratio(direction=opp.expected_direction, entry_price=entry,
                                      stop_loss_price=stop, target_price=targets[0])
                levels_time = levels.known_at
                score += 15
                reasons.extend((levels.stop_policy, levels.target_policy))
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
            rr_minimum=rr_minimum, rr_maximum=rr_maximum, rr_at_optimal_entry=rr_optimal,
        ))
    return tuple(signals)
