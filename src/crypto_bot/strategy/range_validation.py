from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from crypto_bot.strategy.market_analysis import MarketEventKind
from crypto_bot.strategy.mtf_sfp import MtfSfpReport, MtfSfpStatus
from crypto_bot.strategy.range_engine import RangeAnalysisReport, RangeStatus, range_review_key_text


@dataclass(frozen=True)
class OriginMtfFunnel:
    """Audit-only outcome funnel for one HTF SFP liquidity origin.

    Counts are context counts, not trade counts. An opportunity can contain contexts from
    more than one origin, so ``opportunities_with_origin_context`` is intentionally not
    additive across origins.
    """

    origin: str
    sfp_context_count: int
    invalidated_before_bos: int
    expired: int
    right_censored: int
    no_bos_in_available_data: int
    coverage_missing: int
    bos_confirmed_contexts: int
    opportunities_with_origin_context: int


@dataclass(frozen=True)
class RangeStageFunnel:
    """Range-level validation funnel.

    ``ranges_with_sweep`` and ``ranges_with_sfp`` are unique range counts, while episode
    counts expose the raw boundary-event volume. This avoids pretending that every stage is
    a one-to-one trade funnel.
    """

    range_candidate_count: int
    ever_validated_range_count: int
    rejected_internal_structure_count: int
    invalidated_internal_structure_count: int
    ranges_with_boundary_sweep: int
    boundary_sweep_episode_count: int
    ranges_with_sfp: int
    range_sfp_formation_count: int


@dataclass(frozen=True)
class RangeAuditRow:
    range_id: int
    evaluation_context: bool
    impulse_direction: str
    impulse_bos_time: datetime
    first_boundary_kind: str
    first_boundary_price: float
    first_boundary_time: datetime
    second_boundary_kind: str
    second_boundary_price: float
    second_boundary_time: datetime
    lower: float
    upper: float
    width: float
    midpoint: float
    status: str
    status_time: datetime
    midpoint_reaction_time: datetime | None
    midpoint_reaction_price: float | None
    midpoint_distance_fraction: float | None
    internal_bos_count: int
    upper_boundary_state: str
    lower_boundary_state: str
    boundary_sweep_episode_count: int
    sfp_formation_count: int
    first_sfp_time: datetime | None
    last_sfp_time: datetime | None
    boundary_clarity_review_key: str
    manual_boundary_clarity_review: str
    audit_window_start: datetime
    audit_window_end: datetime


@dataclass(frozen=True)
class RangeValidationMatrixRow:
    midpoint_tolerance_fraction: float
    wait_mode: str
    wait_value: int | None
    effective_wait_minutes: int | None
    range_candidate_count_loaded: int
    ever_validated_range_count_loaded: int
    ranges_with_boundary_sweep_loaded: int
    boundary_sweep_episode_count_loaded: int
    ranges_with_sfp_loaded: int
    range_sfp_formation_count_loaded: int
    range_sfp_context_count_evaluation: int
    range_invalidated_before_bos: int
    range_expired: int
    range_right_censored: int
    range_no_bos_available_data: int
    range_coverage_missing: int
    range_bos_confirmed_contexts: int
    opportunities_with_range_context: int


FORMATION_KINDS = {
    MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
    MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED,
}


def build_origin_mtf_funnel(report: MtfSfpReport, origin: str) -> OriginMtfFunnel:
    origin_candidates = [c for c in report.candidates if (c.htf_liquidity_origin or "UNKNOWN") == origin]
    counts = Counter(c.status for c in origin_candidates)
    candidate_ids = {c.candidate_id for c in origin_candidates}
    opportunity_count = sum(
        1 for o in report.opportunities if any(candidate_id in candidate_ids for candidate_id in o.candidate_ids)
    )
    return OriginMtfFunnel(
        origin=origin,
        sfp_context_count=len(origin_candidates),
        invalidated_before_bos=counts[MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS],
        expired=counts[MtfSfpStatus.EXPIRED_BY_BACKTEST_PARAMETER],
        right_censored=counts[MtfSfpStatus.RIGHT_CENSORED_BEFORE_DEADLINE],
        no_bos_in_available_data=counts[MtfSfpStatus.NO_LTF_BOS_IN_AVAILABLE_DATA],
        coverage_missing=counts[MtfSfpStatus.LTF_COVERAGE_MISSING_AT_SFP],
        bos_confirmed_contexts=counts[MtfSfpStatus.LTF_BOS_CONFIRMED],
        opportunities_with_origin_context=opportunity_count,
    )


def build_range_stage_funnel(report: RangeAnalysisReport) -> RangeStageFunnel:
    sweep_range_ids = {ep.range_id for ep in report.sweep_episodes}
    sfp_events = [e for e in report.events if e.kind in FORMATION_KINDS]
    sfp_range_ids = {e.range_id for e in sfp_events if e.range_id is not None}
    status_counts = Counter(r.status for r in report.ranges)
    return RangeStageFunnel(
        range_candidate_count=len(report.ranges),
        ever_validated_range_count=report.validated_count,
        rejected_internal_structure_count=status_counts[RangeStatus.REJECTED_INTERNAL_STRUCTURE],
        invalidated_internal_structure_count=status_counts[RangeStatus.INVALIDATED_INTERNAL_STRUCTURE],
        ranges_with_boundary_sweep=len(sweep_range_ids),
        boundary_sweep_episode_count=len(report.sweep_episodes),
        ranges_with_sfp=len(sfp_range_ids),
        range_sfp_formation_count=len(sfp_events),
    )


def build_range_audit_rows(
    report: RangeAnalysisReport,
    *,
    evaluation_start: datetime,
    htf_minutes: int,
    pre_context_bars: int = 12,
    post_context_bars: int = 24,
) -> tuple[RangeAuditRow, ...]:
    if evaluation_start.tzinfo is None or evaluation_start.utcoffset() is None:
        raise ValueError("evaluation_start must be timezone-aware")
    if htf_minutes <= 0:
        raise ValueError("htf_minutes must be positive")
    if pre_context_bars < 0 or post_context_bars < 0:
        raise ValueError("context bar counts cannot be negative")

    episodes_by_range: dict[int, list] = {}
    for ep in report.sweep_episodes:
        episodes_by_range.setdefault(ep.range_id, []).append(ep)
    sfps_by_range: dict[int, list] = {}
    for event in report.events:
        if event.kind in FORMATION_KINDS and event.range_id is not None:
            sfps_by_range.setdefault(event.range_id, []).append(event)

    rows: list[RangeAuditRow] = []
    bar = timedelta(minutes=htf_minutes)
    for item in report.ranges:
        eps = episodes_by_range.get(item.range_id, [])
        sfps = sorted(sfps_by_range.get(item.range_id, []), key=lambda e: e.event_time)
        width = item.upper - item.lower
        distance_fraction = None
        if item.midpoint_reaction_price is not None and width > 0:
            distance_fraction = abs(item.midpoint_reaction_price - item.midpoint) / width
        latest_relevant = max(
            [item.status_time, *(e.event_time for e in sfps), *(e.sweep_time for e in eps)]
        )
        evaluation_context = (
            item.second_boundary_time >= evaluation_start
            or item.status_time >= evaluation_start
            or any(e.event_time >= evaluation_start for e in sfps)
            or any(e.sweep_time >= evaluation_start for e in eps)
        )
        rows.append(
            RangeAuditRow(
                range_id=item.range_id,
                evaluation_context=evaluation_context,
                impulse_direction=item.impulse_direction.value,
                impulse_bos_time=item.impulse_bos_time,
                first_boundary_kind=item.first_boundary_kind,
                first_boundary_price=item.first_boundary_price,
                first_boundary_time=item.first_boundary_time,
                second_boundary_kind=item.second_boundary_kind,
                second_boundary_price=item.second_boundary_price,
                second_boundary_time=item.second_boundary_time,
                lower=item.lower,
                upper=item.upper,
                width=width,
                midpoint=item.midpoint,
                status=item.status.value,
                status_time=item.status_time,
                midpoint_reaction_time=item.midpoint_reaction_time,
                midpoint_reaction_price=item.midpoint_reaction_price,
                midpoint_distance_fraction=distance_fraction,
                internal_bos_count=item.internal_bos_count,
                upper_boundary_state=item.upper_boundary_state.value,
                lower_boundary_state=item.lower_boundary_state.value,
                boundary_sweep_episode_count=len(eps),
                sfp_formation_count=len(sfps),
                first_sfp_time=sfps[0].event_time if sfps else None,
                last_sfp_time=sfps[-1].event_time if sfps else None,
                boundary_clarity_review_key=range_review_key_text(item),
                manual_boundary_clarity_review=item.boundary_clarity_review.value,
                audit_window_start=item.impulse_bos_time - pre_context_bars * bar,
                audit_window_end=latest_relevant + post_context_bars * bar,
            )
        )
    return tuple(rows)


def build_range_validation_matrix_row(
    *,
    midpoint_tolerance_fraction: float,
    wait_mode: str,
    wait_value: int | None,
    effective_wait_minutes: int | None,
    range_report: RangeAnalysisReport,
    mtf_report: MtfSfpReport,
) -> RangeValidationMatrixRow:
    stage = build_range_stage_funnel(range_report)
    origin = build_origin_mtf_funnel(mtf_report, "RANGE_BOUNDARY")
    return RangeValidationMatrixRow(
        midpoint_tolerance_fraction=midpoint_tolerance_fraction,
        wait_mode=wait_mode,
        wait_value=wait_value,
        effective_wait_minutes=effective_wait_minutes,
        range_candidate_count_loaded=stage.range_candidate_count,
        ever_validated_range_count_loaded=stage.ever_validated_range_count,
        ranges_with_boundary_sweep_loaded=stage.ranges_with_boundary_sweep,
        boundary_sweep_episode_count_loaded=stage.boundary_sweep_episode_count,
        ranges_with_sfp_loaded=stage.ranges_with_sfp,
        range_sfp_formation_count_loaded=stage.range_sfp_formation_count,
        range_sfp_context_count_evaluation=origin.sfp_context_count,
        range_invalidated_before_bos=origin.invalidated_before_bos,
        range_expired=origin.expired,
        range_right_censored=origin.right_censored,
        range_no_bos_available_data=origin.no_bos_in_available_data,
        range_coverage_missing=origin.coverage_missing,
        range_bos_confirmed_contexts=origin.bos_confirmed_contexts,
        opportunities_with_range_context=origin.opportunities_with_origin_context,
    )


def unique_sorted_tolerances(values: Iterable[float]) -> tuple[float, ...]:
    out: list[float] = []
    for raw in values:
        value = float(raw)
        if not (0.0 <= value <= 0.5):
            raise ValueError("range midpoint tolerances must be within [0, 0.5]")
        if value not in out:
            out.append(value)
    if not out:
        raise ValueError("at least one range midpoint tolerance is required")
    return tuple(sorted(out))
