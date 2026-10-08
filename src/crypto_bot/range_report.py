from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from crypto_bot.strategy.market_analysis import MarketEventKind
from crypto_bot.strategy.range_engine import RangeAnalysisReport, RangeDetectionParams, range_review_key


RANGE_FIELDS = [
    "range_id", "impulse_direction", "impulse_bos_kind", "impulse_bos_time",
    "first_boundary_kind", "first_boundary_price", "first_boundary_time",
    "second_boundary_kind", "second_boundary_price", "second_boundary_time",
    "lower", "upper", "midpoint", "status", "status_time",
    "boundary_clarity_review", "boundary_clarity_review_key",
    "midpoint_reaction_time", "midpoint_reaction_price", "midpoint_reaction_kind",
    "internal_bos_count",
    "upper_boundary_state", "lower_boundary_state", "recovery_transition_ids", "invalidating_recovery_transition_ids",
]

SWEEP_FIELDS = [
    "episode_id", "range_id", "side", "boundary_price", "sweep_candle_index",
    "sweep_time", "status", "resolved_index", "sfp_event_time",
]

EVENT_FIELDS = [
    "kind", "event_time", "candle_index", "price", "range_id", "level_id",
    "level_price", "episode_id", "sfp_pattern_extreme_price", "liquidity_origin", "note", "recovery_transition_ids",
]


def write_ranges_csv(report: RangeAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANGE_FIELDS)
        writer.writeheader()
        for r in report.ranges:
            writer.writerow({
                "range_id": r.range_id,
                "recovery_transition_ids": ";".join(map(str, r.recovery_transition_ids)),
                "invalidating_recovery_transition_ids": ";".join(map(str, r.invalidating_recovery_transition_ids)),
                "impulse_direction": r.impulse_direction.value,
                "impulse_bos_kind": r.impulse_bos_kind.value,
                "impulse_bos_time": r.impulse_bos_time.isoformat(),
                "first_boundary_kind": r.first_boundary_kind,
                "first_boundary_price": r.first_boundary_price,
                "first_boundary_time": r.first_boundary_time.isoformat(),
                "second_boundary_kind": r.second_boundary_kind,
                "second_boundary_price": r.second_boundary_price,
                "second_boundary_time": r.second_boundary_time.isoformat(),
                "lower": r.lower,
                "upper": r.upper,
                "midpoint": r.midpoint,
                "status": r.status.value,
                "status_time": r.status_time.isoformat(),
                "boundary_clarity_review": r.boundary_clarity_review.value,
                "boundary_clarity_review_key": chr(124).join(str(x.isoformat() if hasattr(x, "isoformat") else x) for x in range_review_key(r)),
                "midpoint_reaction_time": r.midpoint_reaction_time.isoformat() if r.midpoint_reaction_time else "",
                "midpoint_reaction_price": r.midpoint_reaction_price if r.midpoint_reaction_price is not None else "",
                "midpoint_reaction_kind": r.midpoint_reaction_kind or "",
                "internal_bos_count": r.internal_bos_count,
                "upper_boundary_state": r.upper_boundary_state.value,
                "lower_boundary_state": r.lower_boundary_state.value,
            })
    return destination


def write_range_sweeps_csv(report: RangeAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SWEEP_FIELDS)
        writer.writeheader()
        for ep in report.sweep_episodes:
            writer.writerow({
                "episode_id": ep.episode_id,
                "range_id": ep.range_id,
                "side": ep.side,
                "boundary_price": ep.boundary_price,
                "sweep_candle_index": ep.sweep_candle_index,
                "sweep_time": ep.sweep_time.isoformat(),
                "status": ep.status,
                "resolved_index": ep.resolved_index if ep.resolved_index is not None else "",
                "sfp_event_time": ep.sfp_event_time.isoformat() if ep.sfp_event_time else "",
            })
    return destination


def write_range_sfp_events_csv(report: RangeAnalysisReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
        writer.writeheader()
        for e in report.events:
            writer.writerow({
                "kind": e.kind.value,
                "event_time": e.event_time.isoformat(),
                "candle_index": e.candle_index,
                "price": e.price,
                "range_id": e.range_id if e.range_id is not None else "",
                "level_id": e.level_id,
                "level_price": e.level_price,
                "episode_id": e.episode_id if e.episode_id is not None else "",
                "sfp_pattern_extreme_price": e.sfp_pattern_extreme_price if e.sfp_pattern_extreme_price is not None else "",
                "liquidity_origin": e.liquidity_origin or "",
                "note": e.note,
                "recovery_transition_ids": ";".join(map(str, e.recovery_transition_ids)),
            })
    return destination


def write_range_summary_json(
    report: RangeAnalysisReport,
    params: RangeDetectionParams,
    path: str | Path,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    status_counts = Counter(r.status.value for r in report.ranges)
    sweep_counts = Counter(ep.status for ep in report.sweep_episodes)
    event_counts = Counter(e.kind.value for e in report.events)
    formation_kinds = {
        MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED.value,
        MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED.value,
    }
    payload = {
        "range_candidate_count": len(report.ranges),
        "ever_validated_count": report.validated_count,
        "status_counts": dict(sorted(status_counts.items())),
        "sweep_episode_count": len(report.sweep_episodes),
        "sweep_status_counts": dict(sorted(sweep_counts.items())),
        "range_sfp_formation_count": sum(event_counts.get(k, 0) for k in formation_kinds),
        "event_counts": dict(sorted(event_counts.items())),
        "params": {
            "midpoint_tolerance_fraction": params.midpoint_tolerance_fraction,
            "require_clean_internal_structure": params.require_clean_internal_structure,
        },
        "source_policy": report.source_policy,
        "impulse_proxy_policy": report.impulse_proxy_policy,
        "midpoint_policy": report.midpoint_policy,
        "internal_structure_policy": report.internal_structure_policy,
        "liquidity_policy": report.liquidity_policy,
        "boundary_clarity_policy": report.boundary_clarity_policy,
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
