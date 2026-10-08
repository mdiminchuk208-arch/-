from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from itertools import groupby

from crypto_bot.common.models import Direction
from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEvent, MarketEventKind, StructureAnalysisMode
from crypto_bot.strategy.trade_plan import TradePlanGeometryError, build_trade_plan_geometry, derive_structural_impulse_context


class MtfSfpStatus(str, Enum):
    LTF_BOS_CONFIRMED = "LTF_BOS_CONFIRMED"
    INVALIDATED_BEFORE_LTF_BOS = "INVALIDATED_BEFORE_LTF_BOS"
    NO_LTF_BOS_IN_AVAILABLE_DATA = "NO_LTF_BOS_IN_AVAILABLE_DATA"
    EXPIRED_BY_BACKTEST_PARAMETER = "EXPIRED_BY_BACKTEST_PARAMETER"
    RIGHT_CENSORED_BEFORE_DEADLINE = "RIGHT_CENSORED_BEFORE_DEADLINE"
    LTF_COVERAGE_MISSING_AT_SFP = "LTF_COVERAGE_MISSING_AT_SFP"


class MtfOpportunityStatus(str, Enum):
    ENTRY_SEARCH_CANDIDATE = "ENTRY_SEARCH_CANDIDATE"


@dataclass(frozen=True)
class MtfSfpCandidate:
    candidate_id: int
    htf_minutes: int
    ltf_minutes: int
    htf_sfp_kind: MarketEventKind
    htf_sfp_event_time: datetime
    htf_sfp_candle_index: int
    htf_episode_id: int | None
    htf_level_id: int
    htf_level_price: float
    expected_direction: Direction
    expected_ltf_bos_kind: MarketEventKind
    status: MtfSfpStatus
    htf_liquidity_origin: str | None = None
    htf_range_id: int | None = None
    ltf_bos_event_time: datetime | None = None
    ltf_bos_candle_index: int | None = None
    ltf_bos_level_id: int | None = None
    ltf_bos_level_price: float | None = None
    elapsed_ltf_bars: int | None = None
    elapsed_minutes: int | None = None
    max_wait_ltf_bars: int | None = None
    max_wait_minutes: int | None = None
    entry_search_allowed: bool = False
    trade_entry_allowed: bool = False
    note: str = ""
    sfp_invalidation_price: float | None = None
    sfp_invalidation_event_time: datetime | None = None
    sfp_invalidation_candle_index: int | None = None
    sfp_invalidation_close_price: float | None = None
    deadline_event_time: datetime | None = None
    opportunity_id: int | None = None
    htf_recovery_transition_ids: tuple[int, ...] = ()
    ltf_recovery_transition_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class MtfOpportunity:
    opportunity_id: int
    status: MtfOpportunityStatus
    expected_direction: Direction
    ltf_bos_kind: MarketEventKind
    ltf_bos_event_time: datetime
    ltf_bos_candle_index: int
    ltf_bos_level_id: int
    ltf_bos_level_price: float
    candidate_ids: tuple[int, ...]
    htf_episode_ids: tuple[int, ...]
    htf_level_ids: tuple[int, ...]
    earliest_sfp_time: datetime
    latest_sfp_time: datetime
    representative_candidate_id: int
    entry_search_allowed: bool = True
    trade_entry_allowed: bool = False
    note: str = ""
    # Phase 1.4.12 provenance fields are appended after the v0.4.11 positional
    # surface so older callers keep their entry/trade/note values intact.
    htf_recovery_transition_ids: tuple[int, ...] = ()
    ltf_recovery_transition_ids: tuple[int, ...] = ()
    # Phase 1.4.20 fields are appended to preserve the existing positional surface.
    entry_geometry_ready_time: datetime | None = None
    entry_geometry_transition_id: int | None = None
    impulse_start_price: float | None = None
    impulse_end_price: float | None = None
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    entry_anchor_level_id: int | None = None
    entry_correction_level_id: int | None = None
    entry_correction_price: float | None = None
    entry_geometry_policy: str = ""
    stop_loss_price: float | None = None
    target_price: float | None = None
    stop_loss_policy: str = ""
    target_policy: str = ""
    rr_minimum: float | None = None
    rr_maximum: float | None = None
    entry_plan_status: str = "WAITING_FOR_ENTRY_GEOMETRY"

    @property
    def context_count(self) -> int:
        return len(self.candidate_ids)


@dataclass(frozen=True)
class MtfSfpReport:
    htf_minutes: int
    ltf_minutes: int
    max_wait_ltf_bars: int | None
    candidates: tuple[MtfSfpCandidate, ...]
    source_policy: str
    mapping_policy: str
    expiry_policy: str
    entry_policy: str
    linkage_policy: str = ""
    candidate_not_before: datetime | None = None
    ltf_observation_start: datetime | None = None
    ltf_observation_end: datetime | None = None
    opportunities: tuple[MtfOpportunity, ...] = ()
    invalidation_policy: str = ""
    opportunity_policy: str = ""
    opportunity_dedup_scope: str = "PAIR_LOCAL_EXACT_LTF_BOS"
    max_wait_minutes: int | None = None
    entry_engine_blocking_reasons: tuple[str, ...] = (
        "RANGE_BOUNDARY_SFP_NOT_IMPLEMENTED",
        "SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED",
    )
    # Append after all v0.4.11 fields to preserve positional compatibility.
    analysis_mode: StructureAnalysisMode = StructureAnalysisMode.SOURCE_CONSERVATIVE

    @property
    def confirmed_count(self) -> int:
        return sum(c.status == MtfSfpStatus.LTF_BOS_CONFIRMED for c in self.candidates)

    @property
    def invalidated_count(self) -> int:
        return sum(c.status == MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS for c in self.candidates)

    @property
    def unique_ltf_bos_count(self) -> int:
        keys = {
            _candidate_bos_key(c)
            for c in self.candidates
            if c.status == MtfSfpStatus.LTF_BOS_CONFIRMED and c.ltf_bos_event_time is not None
        }
        return len(keys)

    @property
    def shared_bos_link_count(self) -> int:
        return max(0, self.confirmed_count - self.unique_ltf_bos_count)

    @property
    def opportunity_count(self) -> int:
        return len(self.opportunities)


class MtfSfpError(ValueError):
    pass


def _sfp_direction_and_bos_kind(kind: MarketEventKind) -> tuple[Direction, MarketEventKind]:
    if kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED:
        return Direction.SHORT, MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS
    if kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED:
        return Direction.LONG, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS
    raise MtfSfpError(f"unsupported HTF event kind for SFP->LTF linking: {kind}")


def _expected_invalidation_kind(sfp_kind: MarketEventKind) -> MarketEventKind:
    if sfp_kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED:
        return MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE
    if sfp_kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED:
        return MarketEventKind.BULLISH_SFP_INVALIDATED_CLOSE
    raise MtfSfpError(f"unsupported SFP kind for invalidation: {sfp_kind}")


def _matching_invalidation(sfp: MarketEvent, htf_report: MarketAnalysisReport) -> MarketEvent | None:
    expected_kind = _expected_invalidation_kind(sfp.kind)
    matches = []
    for event in htf_report.events:
        if event.kind != expected_kind or event.event_time <= sfp.event_time:
            continue
        if sfp.episode_id is not None and event.episode_id == sfp.episode_id:
            matches.append(event)
        elif sfp.episode_id is None and event.level_id == sfp.level_id:
            matches.append(event)
    return min(matches, key=lambda e: (e.event_time, e.candle_index, e.level_id)) if matches else None


def _candidate_bos_key(candidate: MtfSfpCandidate) -> tuple:
    return (
        candidate.ltf_bos_event_time,
        candidate.expected_direction.value,
        candidate.expected_ltf_bos_kind.value,
        candidate.ltf_bos_candle_index,
        candidate.ltf_bos_level_id,
    )


def cluster_entry_search_opportunities(
    candidates: tuple[MtfSfpCandidate, ...] | list[MtfSfpCandidate],
) -> tuple[tuple[MtfSfpCandidate, ...], tuple[MtfOpportunity, ...]]:
    """Collapse shared SFP->same-BOS context links into one entry-search opportunity.

    This is a TECHNICAL NORMALIZATION, not a source trading rule. It prevents one LTF BOS
    from being counted as multiple independent trade opportunities merely because several
    still-relevant HTF SFP contexts preceded it. All source contexts remain attached.
    """
    confirmed = [
        c
        for c in candidates
        if c.status == MtfSfpStatus.LTF_BOS_CONFIRMED
        and c.ltf_bos_event_time is not None
        and c.ltf_bos_candle_index is not None
        and c.ltf_bos_level_id is not None
        and c.ltf_bos_level_price is not None
    ]
    confirmed.sort(key=lambda c: (_candidate_bos_key(c), c.htf_sfp_event_time, c.candidate_id))

    candidate_to_opportunity: dict[int, int] = {}
    opportunities: list[MtfOpportunity] = []
    for opportunity_id, (_, group_iter) in enumerate(groupby(confirmed, key=_candidate_bos_key), start=1):
        group = list(group_iter)
        # Latest context is selected only as a deterministic display representative. It does
        # not receive extra score/weight and does not discard older source contexts.
        representative = max(group, key=lambda c: (c.htf_sfp_event_time, c.candidate_id))
        candidate_ids = tuple(c.candidate_id for c in group)
        for candidate_id in candidate_ids:
            candidate_to_opportunity[candidate_id] = opportunity_id
        first = group[0]
        opportunities.append(
            MtfOpportunity(
                opportunity_id=opportunity_id,
                status=MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE,
                expected_direction=first.expected_direction,
                ltf_bos_kind=first.expected_ltf_bos_kind,
                ltf_bos_event_time=first.ltf_bos_event_time,  # type: ignore[arg-type]
                ltf_bos_candle_index=first.ltf_bos_candle_index,  # type: ignore[arg-type]
                ltf_bos_level_id=first.ltf_bos_level_id,  # type: ignore[arg-type]
                ltf_bos_level_price=first.ltf_bos_level_price,  # type: ignore[arg-type]
                candidate_ids=candidate_ids,
                htf_episode_ids=tuple(c.htf_episode_id for c in group if c.htf_episode_id is not None),
                htf_level_ids=tuple(c.htf_level_id for c in group),
                earliest_sfp_time=min(c.htf_sfp_event_time for c in group),
                latest_sfp_time=max(c.htf_sfp_event_time for c in group),
                representative_candidate_id=representative.candidate_id,
                htf_recovery_transition_ids=tuple(sorted({rid for c in group for rid in c.htf_recovery_transition_ids})),
                ltf_recovery_transition_ids=tuple(sorted({rid for c in group for rid in c.ltf_recovery_transition_ids})),
                entry_search_allowed=all(c.entry_search_allowed for c in group),
                note=(
                    "One expected-direction LTF BOS defines one entry-search opportunity in this HTF/LTF report. "
                    f"{len(group)} preceding valid SFP context link(s) are preserved; they are not separate trades."
                ),
            )
        )

    updated = tuple(
        replace(c, opportunity_id=candidate_to_opportunity.get(c.candidate_id))
        if c.candidate_id in candidate_to_opportunity
        else c
        for c in candidates
    )
    return updated, tuple(opportunities)


def _attach_entry_geometry(
    opportunities: tuple[MtfOpportunity, ...],
    ltf_report: MarketAnalysisReport,
) -> tuple[MtfOpportunity, ...]:
    # Attach only causal source-conservative OTE geometry; trade entry remains blocked.
    enriched: list[MtfOpportunity] = []
    for opportunity in opportunities:
        if not opportunity.entry_search_allowed:
            enriched.append(opportunity)
            continue
        try:
            context = derive_structural_impulse_context(
                direction=opportunity.expected_direction,
                ltf_report=ltf_report,
                bos_kind=opportunity.ltf_bos_kind,
                bos_index=opportunity.ltf_bos_candle_index,
                bos_time=opportunity.ltf_bos_event_time,
            )
        except TradePlanGeometryError as exc:
            # A valid opposite structure does not guarantee that the frozen
            # broken-extreme -> selected-anchor normalization is a directional
            # impulse. Reject its entry geometry, preserving the raw SFP/BOS audit.
            enriched.append(replace(
                opportunity, entry_search_allowed=False,
                entry_plan_status="REJECTED_ENTRY_GEOMETRY",
                entry_geometry_policy=f"Entry geometry rejected: {exc}",
                trade_entry_allowed=False,
            ))
            continue
        if context is None:
            enriched.append(opportunity)
            continue
        enriched.append(
            replace(
                opportunity,
                entry_geometry_ready_time=context.ready_time,
                entry_geometry_transition_id=context.transition_id,
                impulse_start_price=context.impulse_start_price,
                impulse_end_price=context.impulse_end_price,
                entry_zone_low=context.entry_zone.low,
                entry_zone_high=context.entry_zone.high,
                entry_anchor_level_id=context.anchor_level_id,
                entry_correction_level_id=context.correction_level_id,
                entry_correction_price=context.correction_price,
                entry_geometry_policy=(
                    "Phase 1.4.20: expected-opposite post-BOS structure resolved; OTE 0.705-0.79 "
                    "is measured from the broken pre-BOS structural extreme to the selected post-BOS anchor. "
                    "SL/target selection and trade entry remain blocked."
                ),
                entry_plan_status="WAITING_FOR_SOURCE_SL_TARGET",
                trade_entry_allowed=False,
            )
        )
    return tuple(enriched)


def link_sfp_formations_to_ltf_bos(
    htf_report: MarketAnalysisReport,
    ltf_report: MarketAnalysisReport,
    *,
    htf_minutes: int,
    ltf_minutes: int,
    max_wait_ltf_bars: int | None = None,
    max_wait_minutes: int | None = None,
    candidate_not_before: datetime | None = None,
    ltf_observation_start: datetime | None = None,
    ltf_observation_end: datetime | None = None,
) -> MtfSfpReport:
    """Causally link completed HTF SFPs to a later, still-valid LTF BOS.

    SOURCE RULES:
      - Complete SFP first, then move to a lower timeframe and wait for BOS; only after
        that may an entry point be searched for.
      - SFP may form on any timeframe; H1+ is explicitly preferred for searching.
      - A formed SFP becomes irrelevant if any later candle body closes below the SFP
        minimum for a bullish/long pattern, or above the SFP maximum for bearish/short.

    TECHNICAL NORMALIZATIONS / BACKTEST PARAMETERS:
      - Exact HTF:LTF pair is a BACKTEST_PARAMETER.
      - Source defines no post-SFP BOS expiry. A positive max_wait_ltf_bars or
        max_wait_minutes is a BACKTEST_PARAMETER; None is observationally unbounded
        within available data.
      - The SFP min/max used by the machine is the completed sweep candle's low/high,
        recorded at formation time. It is causal and does not use future candle extremes.
      - If BOS and HTF invalidation have the exact same timestamp, invalidation wins
        conservatively because event order inside that timestamp cannot be established.
      - Shared links to the same LTF BOS are clustered into one entry-search opportunity.
        This de-duplicates software opportunities; it is not a source trading rule.
      - No actual trade is placed in Phase 1.4.5.
    """
    if htf_report.analysis_mode != ltf_report.analysis_mode:
        raise MtfSfpError("HTF/LTF analysis modes must match")
    if htf_minutes <= 0 or ltf_minutes <= 0:
        raise MtfSfpError("timeframes must be positive minutes")
    if ltf_minutes >= htf_minutes:
        raise MtfSfpError("LTF must be strictly lower than HTF")
    if max_wait_ltf_bars is not None and max_wait_ltf_bars <= 0:
        raise MtfSfpError("max_wait_ltf_bars must be positive or None")
    if max_wait_minutes is not None and max_wait_minutes <= 0:
        raise MtfSfpError("max_wait_minutes must be positive or None")
    if max_wait_ltf_bars is not None and max_wait_minutes is not None:
        raise MtfSfpError("use either max_wait_ltf_bars or max_wait_minutes, not both")
    if (ltf_observation_start is None) != (ltf_observation_end is None):
        raise MtfSfpError("LTF observation start/end must be supplied together")
    if ltf_observation_start is not None and ltf_observation_end is not None:
        if ltf_observation_end <= ltf_observation_start:
            raise MtfSfpError("LTF observation end must be after start")
    for name, value in (
        ("candidate_not_before", candidate_not_before),
        ("ltf_observation_start", ltf_observation_start),
        ("ltf_observation_end", ltf_observation_end),
    ):
        if value is not None and value.utcoffset() is None:
            raise MtfSfpError(f"{name} must be timezone-aware")

    sfp_kinds = {
        MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
        MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED,
    }
    htf_sfps = sorted(
        (
            e
            for e in htf_report.events
            if e.kind in sfp_kinds and (candidate_not_before is None or e.event_time >= candidate_not_before)
        ),
        key=lambda e: (e.event_time, e.candle_index, e.kind.value, e.level_id),
    )
    for sfp in htf_sfps:
        if sfp.sfp_pattern_extreme_price is None:
            raise MtfSfpError(
                "SFP formation is missing sfp_pattern_extreme_price; Phase 1.4.5 requires causal invalidation data"
            )

    ltf_bos_kinds = {
        MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
        MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
    }
    ltf_bos_events = sorted(
        (e for e in ltf_report.events if e.kind in ltf_bos_kinds),
        key=lambda e: (e.event_time, e.candle_index, e.kind.value, e.level_id),
    )

    candidates: list[MtfSfpCandidate] = []
    for candidate_id, sfp in enumerate(htf_sfps, start=1):
        direction, expected_bos_kind = _sfp_direction_and_bos_kind(sfp.kind)
        eligible_from = sfp.event_time
        deadline = None
        if max_wait_minutes is not None:
            deadline = eligible_from + timedelta(minutes=max_wait_minutes)
        elif max_wait_ltf_bars is not None:
            deadline = eligible_from + timedelta(minutes=ltf_minutes * max_wait_ltf_bars)
        invalidation = _matching_invalidation(sfp, htf_report)

        common = dict(
            candidate_id=candidate_id,
            htf_minutes=htf_minutes,
            ltf_minutes=ltf_minutes,
            htf_sfp_kind=sfp.kind,
            htf_sfp_event_time=sfp.event_time,
            htf_sfp_candle_index=sfp.candle_index,
            htf_episode_id=sfp.episode_id,
            htf_level_id=sfp.level_id,
            htf_level_price=sfp.level_price,
            htf_liquidity_origin=sfp.liquidity_origin,
            htf_range_id=sfp.range_id,
            htf_recovery_transition_ids=sfp.recovery_transition_ids,
            expected_direction=direction,
            expected_ltf_bos_kind=expected_bos_kind,
            max_wait_ltf_bars=max_wait_ltf_bars,
            max_wait_minutes=max_wait_minutes,
            sfp_invalidation_price=sfp.sfp_pattern_extreme_price,
            sfp_invalidation_event_time=invalidation.event_time if invalidation else None,
            sfp_invalidation_candle_index=invalidation.candle_index if invalidation else None,
            sfp_invalidation_close_price=invalidation.price if invalidation else None,
            deadline_event_time=deadline,
            trade_entry_allowed=False,
        )

        if ltf_observation_start is not None and ltf_observation_end is not None:
            if eligible_from < ltf_observation_start or eligible_from >= ltf_observation_end:
                candidates.append(
                    MtfSfpCandidate(
                        **common,
                        status=MtfSfpStatus.LTF_COVERAGE_MISSING_AT_SFP,
                        entry_search_allowed=False,
                        note=(
                            "The completed HTF SFP falls outside the available LTF observation window; "
                            "no BOS/invalidation comparison is scored."
                        ),
                    )
                )
                continue

        matching_bos: MarketEvent | None = None
        for bos in ltf_bos_events:
            if bos.event_time <= eligible_from:
                continue
            if ltf_observation_end is not None and bos.event_time > ltf_observation_end:
                break
            if deadline is not None and bos.event_time > deadline:
                break
            if invalidation is not None and bos.event_time >= invalidation.event_time:
                # Equal timestamp is deliberately conservative: invalidation wins.
                break
            if bos.kind != expected_bos_kind:
                continue
            matching_bos = bos
            break

        if matching_bos is not None:
            elapsed_seconds = (matching_bos.event_time - eligible_from).total_seconds()
            elapsed_bars = int(elapsed_seconds // (ltf_minutes * 60))
            candidates.append(
                MtfSfpCandidate(
                    **common,
                    status=MtfSfpStatus.LTF_BOS_CONFIRMED,
                    ltf_bos_event_time=matching_bos.event_time,
                    ltf_bos_candle_index=matching_bos.candle_index,
                    ltf_bos_level_id=matching_bos.level_id,
                    ltf_bos_level_price=matching_bos.level_price,
                    elapsed_ltf_bars=elapsed_bars,
                    elapsed_minutes=int(elapsed_seconds // 60),
                    ltf_recovery_transition_ids=matching_bos.recovery_transition_ids,
                    entry_search_allowed=not (sfp.recovery_transition_ids or matching_bos.recovery_transition_ids),
                    note=(
                        "Completed HTF SFP remained valid until a causally later expected-direction LTF BOS. "
                        "Recovery ancestry, when present, is diagnostic only and blocks source entry search; actual trade entry remains blocked."
                    ),
                )
            )
            continue

        invalidation_before_deadline = invalidation is not None and (
            deadline is None or invalidation.event_time <= deadline
        )
        invalidation_in_observation = invalidation is not None and (
            ltf_observation_end is None or invalidation.event_time <= ltf_observation_end
        )
        if invalidation_before_deadline and invalidation_in_observation:
            candidates.append(
                MtfSfpCandidate(
                    **common,
                    status=MtfSfpStatus.INVALIDATED_BEFORE_LTF_BOS,
                    entry_search_allowed=False,
                    note=(
                        "SFP became irrelevant by a source-defined candle-close invalidation before the expected LTF BOS."
                    ),
                )
            )
            continue

        if max_wait_ltf_bars is not None or max_wait_minutes is not None:
            if ltf_observation_end is not None and deadline is not None and ltf_observation_end < deadline:
                status = MtfSfpStatus.RIGHT_CENSORED_BEFORE_DEADLINE
                note = (
                    "Available common history ends before the configured BOS wait window expires; "
                    "the setup is right-censored, not expired."
                )
            else:
                status = MtfSfpStatus.EXPIRED_BY_BACKTEST_PARAMETER
                note = "No valid matching LTF BOS was observed before the configured backtest deadline."
        else:
            status = MtfSfpStatus.NO_LTF_BOS_IN_AVAILABLE_DATA
            note = (
                "No valid matching LTF BOS was observed after the completed SFP in available data; "
                "the source itself defines no expiry window."
            )

        candidates.append(
            MtfSfpCandidate(
                **common,
                status=status,
                entry_search_allowed=False,
                note=note,
            )
        )

    updated_candidates, opportunities = cluster_entry_search_opportunities(candidates)
    opportunities = _attach_entry_geometry(opportunities, ltf_report)
    blockers = [
        "SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED",
    ]
    # Preserve order while removing duplicate not-implemented fallbacks.
    blockers = list(dict.fromkeys(blockers))
    return MtfSfpReport(
        htf_minutes=htf_minutes,
        ltf_minutes=ltf_minutes,
        analysis_mode=htf_report.analysis_mode,
        max_wait_ltf_bars=max_wait_ltf_bars,
        candidates=updated_candidates,
        source_policy=(
            "Completed SFP -> move to lower timeframe -> wait for BOS -> only then search for entry. "
            "SFP is valid on any timeframe; H1+ is source-preferred. A candle-body close beyond the SFP "
            "minimum/maximum makes the pattern no longer relevant."
        ),
        mapping_policy=(
            "Specific HTF->LTF pair selection is not specified by the source and is a BACKTEST_PARAMETER."
        ),
        expiry_policy=(
            "Source defines no maximum wait after SFP. None is observational/unbounded within available data; "
            "any positive max_wait_ltf_bars or max_wait_minutes is a BACKTEST_PARAMETER. Truncated data is right-censored."
        ),
        entry_policy=(
            "Valid LTF BOS unlocks entry-search only. Phase 1.4.20 provides OTE geometry, source-qualified OB/SL-reference geometry, first-opposing-POI FTA selection and RR derivation when qualified inputs are supplied; automatic OB/POI detection and qualification plus trade entry remain blocked."
        ),
        linkage_policy=(
            "Raw SFP->BOS links remain auditable, but links sharing the same expected-direction LTF BOS are clustered into one opportunity."
        ),
        candidate_not_before=candidate_not_before,
        ltf_observation_start=ltf_observation_start,
        ltf_observation_end=ltf_observation_end,
        opportunities=opportunities,
        max_wait_minutes=max_wait_minutes,
        invalidation_policy=(
            "Source: a formed SFP is no longer relevant after a candle body closes beyond its minimum/maximum. "
            "Technical normalization: the machine uses the completed sweep candle low/high as the causal pattern extreme; exact-timestamp tie goes to invalidation."
        ),
        opportunity_policy=(
            "One LTF BOS + one direction = one entry-search opportunity inside this HTF/LTF report. "
            "All contributing SFP contexts are retained. This report remains pair-local; the Phase 1.4.12 global layer de-duplicates across requested HTF/LTF reports separately."
        ),
        opportunity_dedup_scope="PAIR_LOCAL_EXACT_LTF_BOS",
        entry_engine_blocking_reasons=tuple(blockers),
    )


def attach_source_qualified_trade_levels(opportunity: MtfOpportunity, *, stop_loss_price: float, target_price: float, stop_loss_policy: str, target_policy: str) -> MtfOpportunity:
    """Attach caller-supplied source-qualified SL/target and derive RR; never unlock trading."""
    if not stop_loss_policy.strip() or not target_policy.strip():
        raise ValueError("SL and target policies must be explicit")
    required=(opportunity.impulse_start_price, opportunity.impulse_end_price, opportunity.entry_zone_low, opportunity.entry_zone_high)
    if any(v is None for v in required):
        raise ValueError("entry geometry must be ready before attaching SL/target")
    plan=build_trade_plan_geometry(direction=opportunity.expected_direction, impulse_start_price=opportunity.impulse_start_price, impulse_end_price=opportunity.impulse_end_price, stop_loss_price=stop_loss_price, target_price=target_price)
    if abs(plan.entry_zone.low-opportunity.entry_zone_low)>1e-12 or abs(plan.entry_zone.high-opportunity.entry_zone_high)>1e-12:
        raise ValueError("stored entry geometry does not match the trade-plan geometry")
    return replace(opportunity, stop_loss_price=plan.stop_loss_price, target_price=plan.target_price, stop_loss_policy=stop_loss_policy, target_policy=target_policy, rr_minimum=plan.rr.minimum, rr_maximum=plan.rr.maximum, entry_plan_status="RR_READY_SOURCE_LEVELS", trade_entry_allowed=False)
