from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from crypto_bot.common.models import Direction
from crypto_bot.strategy.market_analysis import StructureAnalysisMode
from crypto_bot.strategy.mtf_sfp import MtfOpportunity, MtfSfpReport


PRODUCTION_GLOBAL_CLUSTER_WINDOW_MINUTES = 0


@dataclass(frozen=True)
class PairOpportunityRef:
    symbol: str
    pair_label: str
    htf_minutes: int
    ltf_minutes: int
    local_opportunity_id: int
    expected_direction: Direction
    confirmation_time: datetime
    context_count: int
    recovery_context_refs: tuple[str, ...] = ()
    entry_search_allowed: bool = True


@dataclass(frozen=True)
class GlobalOpportunity:
    global_opportunity_id: int
    symbol: str
    expected_direction: Direction
    cluster_start_time: datetime
    cluster_end_time: datetime
    representative_confirmation_time: datetime
    pair_labels: tuple[str, ...]
    local_opportunity_ids: tuple[str, ...]
    context_count: int
    local_opportunity_count: int
    cluster_window_minutes: int
    trade_entry_allowed: bool = False
    note: str = ""
    # Phase 1.4.12 fields are appended after the v0.4.11 positional surface.
    entry_search_allowed: bool = False
    recovery_context_refs: tuple[str, ...] = ()
    analysis_mode: StructureAnalysisMode = StructureAnalysisMode.SOURCE_CONSERVATIVE


class GlobalOpportunityError(ValueError):
    pass


def _refs_for_report(symbol: str, pair_label: str, report: MtfSfpReport) -> list[PairOpportunityRef]:
    refs: list[PairOpportunityRef] = []
    for opp in report.opportunities:
        refs.append(
            PairOpportunityRef(
                symbol=symbol,
                pair_label=pair_label,
                htf_minutes=report.htf_minutes,
                ltf_minutes=report.ltf_minutes,
                local_opportunity_id=opp.opportunity_id,
                expected_direction=opp.expected_direction,
                confirmation_time=opp.ltf_bos_event_time,
                context_count=opp.context_count,
                recovery_context_refs=tuple(
                    f"{pair_label}:{tf}:{rid}"
                    for tf, ids in (("HTF", opp.htf_recovery_transition_ids), ("LTF", opp.ltf_recovery_transition_ids))
                    for rid in ids
                ),
                entry_search_allowed=opp.entry_search_allowed,
            )
        )
    return refs


def cluster_cross_pair_opportunities(
    symbol: str,
    pair_reports: tuple[tuple[str, MtfSfpReport], ...] | list[tuple[str, MtfSfpReport]],
    *,
    cluster_window_minutes: int = PRODUCTION_GLOBAL_CLUSTER_WINDOW_MINUTES,
) -> tuple[GlobalOpportunity, ...]:
    """De-duplicate pair-local MTF opportunities across timeframe-pair reports.

    TECHNICAL NORMALIZATION / BACKTEST PARAMETER:
    - Exact-time clustering (window=0) merges only same-symbol, same-direction opportunities
      whose confirmation timestamps are identical across timeframe-pair reports.
    - A positive window additionally merges same-direction confirmations that fall within
      `cluster_window_minutes` of the first confirmation in the current cluster. The source
      does not prescribe such a window; positive windows remain experimental BACKTEST_PARAMETER values.
      Phase 1.4.13 freezes the production policy at exact timestamp only (0 minutes).
    - Opposite directions never share one global opportunity.
    - This creates entry-search opportunities only; it does not place trades.
    """
    if not symbol:
        raise GlobalOpportunityError("symbol is required")
    if cluster_window_minutes < 0:
        raise GlobalOpportunityError("cluster_window_minutes must be >= 0")

    refs: list[PairOpportunityRef] = []
    seen_pair_labels: set[str] = set()
    analysis_modes = {report.analysis_mode for _, report in pair_reports}
    if len(analysis_modes) > 1:
        raise GlobalOpportunityError("all pair reports must use the same analysis mode")
    for pair_label, report in pair_reports:
        if not pair_label:
            raise GlobalOpportunityError("pair_label is required")
        if pair_label in seen_pair_labels:
            raise GlobalOpportunityError(f"duplicate pair_label: {pair_label}")
        seen_pair_labels.add(pair_label)
        refs.extend(_refs_for_report(symbol, pair_label, report))

    # Cluster independently by direction so an opposite-direction confirmation between two
    # same-direction confirmations cannot split a potential cross-pair duplicate cluster.
    groups: list[list[PairOpportunityRef]] = []
    for direction in (Direction.LONG, Direction.SHORT):
        direction_refs = sorted(
            (r for r in refs if r.expected_direction == direction),
            key=lambda r: (r.confirmation_time, r.pair_label, r.local_opportunity_id),
        )
        direction_groups: list[list[PairOpportunityRef]] = []
        for ref in direction_refs:
            if not direction_groups:
                direction_groups.append([ref])
                continue
            current = direction_groups[-1]
            anchor = current[0]
            used_pairs = {r.pair_label for r in current}
            within = ref.confirmation_time - anchor.confirmation_time <= timedelta(minutes=cluster_window_minutes)
            # Global de-dup is cross-pair only: two distinct opportunities from the SAME
            # HTF/LTF pair are never collapsed merely because they are close in time.
            if within and ref.pair_label not in used_pairs:
                current.append(ref)
            else:
                direction_groups.append([ref])
        groups.extend(direction_groups)

    groups.sort(
        key=lambda g: (
            min(r.confirmation_time for r in g),
            g[0].expected_direction.value,
            min(r.pair_label for r in g),
        )
    )

    result: list[GlobalOpportunity] = []
    for gid, group in enumerate(groups, start=1):
        first = group[0]
        times = tuple(r.confirmation_time for r in group)
        pair_labels = tuple(sorted({r.pair_label for r in group}))
        local_ids = tuple(f"{r.pair_label}#{r.local_opportunity_id}" for r in group)
        representative = min(group, key=lambda r: (r.confirmation_time, r.pair_label, r.local_opportunity_id))
        result.append(
            GlobalOpportunity(
                global_opportunity_id=gid,
                symbol=symbol,
                expected_direction=first.expected_direction,
                cluster_start_time=min(times),
                cluster_end_time=max(times),
                representative_confirmation_time=representative.confirmation_time,
                pair_labels=pair_labels,
                local_opportunity_ids=local_ids,
                context_count=sum(r.context_count for r in group),
                local_opportunity_count=len(group),
                cluster_window_minutes=cluster_window_minutes,
                recovery_context_refs=tuple(sorted({r for ref in group for r in ref.recovery_context_refs})),
                entry_search_allowed=all(ref.entry_search_allowed for ref in group)
                and not any(ref.recovery_context_refs for ref in group),
                note=(
                    "Cross-pair de-duplication only. Exact-time mode is deterministic; positive windows are "
                    "BACKTEST_PARAMETER experiments. Trade entry remains blocked."
                ),
                analysis_mode=next(iter(analysis_modes)),
            )
        )
    return tuple(result)
