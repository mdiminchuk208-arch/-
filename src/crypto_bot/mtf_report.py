from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from crypto_bot.strategy.mtf_sfp import MtfSfpReport


MTF_FIELDS = [
    "candidate_id",
    "opportunity_id",
    "htf_minutes",
    "ltf_minutes",
    "htf_sfp_kind",
    "htf_sfp_event_time",
    "htf_sfp_candle_index",
    "htf_episode_id",
    "htf_level_id",
    "htf_level_price",
    "htf_liquidity_origin",
    "htf_range_id",
    "sfp_invalidation_price",
    "sfp_invalidation_event_time",
    "sfp_invalidation_candle_index",
    "sfp_invalidation_close_price",
    "expected_direction",
    "expected_ltf_bos_kind",
    "status",
    "ltf_bos_event_time",
    "ltf_bos_candle_index",
    "ltf_bos_level_id",
    "ltf_bos_level_price",
    "elapsed_ltf_bars",
    "elapsed_minutes",
    "max_wait_ltf_bars",
    "max_wait_minutes",
    "deadline_event_time",
    "entry_search_allowed",
    "trade_entry_allowed",
    "note",
    "htf_recovery_transition_ids",
    "ltf_recovery_transition_ids",
]

OPPORTUNITY_FIELDS = [
    "opportunity_id",
    "status",
    "expected_direction",
    "ltf_bos_kind",
    "ltf_bos_event_time",
    "ltf_bos_candle_index",
    "ltf_bos_level_id",
    "ltf_bos_level_price",
    "candidate_ids",
    "htf_episode_ids",
    "htf_level_ids",
    "context_count",
    "earliest_sfp_time",
    "latest_sfp_time",
    "representative_candidate_id",
    "entry_search_allowed",
    "trade_entry_allowed",
    "note",
    "htf_recovery_transition_ids",
    "ltf_recovery_transition_ids",
    "entry_geometry_ready_time",
    "entry_geometry_transition_id",
    "impulse_start_price",
    "impulse_end_price",
    "entry_zone_low",
    "entry_zone_high",
    "entry_anchor_level_id",
    "entry_correction_level_id",
    "entry_correction_price",
    "entry_geometry_policy",
    "stop_loss_price",
    "target_price",
    "stop_loss_policy",
    "target_policy",
    "rr_minimum",
    "rr_maximum",
    "entry_plan_status",
]

AUDIT_FIELDS = [
    "candidate_id",
    "outcome",
    "direction",
    "sfp_time",
    "sfp_level",
    "sfp_liquidity_origin",
    "sfp_range_id",
    "sfp_extreme",
    "invalidation_time",
    "invalidation_close",
    "ltf_bos_time",
    "ltf_bos_level",
    "elapsed_ltf_bars",
    "elapsed_minutes",
    "deadline",
    "opportunity_id",
    "shared_opportunity_context_count",
    "note",
    "htf_recovery_transition_ids",
    "ltf_recovery_transition_ids",
]


def write_mtf_candidates_csv(report: MtfSfpReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MTF_FIELDS)
        writer.writeheader()
        for c in report.candidates:
            writer.writerow(
                {
                    "candidate_id": c.candidate_id,
                    "opportunity_id": c.opportunity_id if c.opportunity_id is not None else "",
                    "htf_minutes": c.htf_minutes,
                    "ltf_minutes": c.ltf_minutes,
                    "htf_sfp_kind": c.htf_sfp_kind.value,
                    "htf_sfp_event_time": c.htf_sfp_event_time.isoformat(),
                    "htf_sfp_candle_index": c.htf_sfp_candle_index,
                    "htf_episode_id": c.htf_episode_id if c.htf_episode_id is not None else "",
                    "htf_level_id": c.htf_level_id,
                    "htf_level_price": c.htf_level_price,
                    "htf_liquidity_origin": c.htf_liquidity_origin or "",
                    "htf_range_id": c.htf_range_id if c.htf_range_id is not None else "",
                    "sfp_invalidation_price": c.sfp_invalidation_price if c.sfp_invalidation_price is not None else "",
                    "sfp_invalidation_event_time": c.sfp_invalidation_event_time.isoformat() if c.sfp_invalidation_event_time else "",
                    "sfp_invalidation_candle_index": c.sfp_invalidation_candle_index if c.sfp_invalidation_candle_index is not None else "",
                    "sfp_invalidation_close_price": c.sfp_invalidation_close_price if c.sfp_invalidation_close_price is not None else "",
                    "expected_direction": c.expected_direction.value,
                    "expected_ltf_bos_kind": c.expected_ltf_bos_kind.value,
                    "status": c.status.value,
                    "ltf_bos_event_time": c.ltf_bos_event_time.isoformat() if c.ltf_bos_event_time else "",
                    "ltf_bos_candle_index": c.ltf_bos_candle_index if c.ltf_bos_candle_index is not None else "",
                    "ltf_bos_level_id": c.ltf_bos_level_id if c.ltf_bos_level_id is not None else "",
                    "ltf_bos_level_price": c.ltf_bos_level_price if c.ltf_bos_level_price is not None else "",
                    "elapsed_ltf_bars": c.elapsed_ltf_bars if c.elapsed_ltf_bars is not None else "",
                    "elapsed_minutes": c.elapsed_minutes if c.elapsed_minutes is not None else "",
                    "max_wait_ltf_bars": c.max_wait_ltf_bars if c.max_wait_ltf_bars is not None else "",
                    "max_wait_minutes": c.max_wait_minutes if c.max_wait_minutes is not None else "",
                    "deadline_event_time": c.deadline_event_time.isoformat() if c.deadline_event_time else "",
                    "entry_search_allowed": c.entry_search_allowed,
                    "trade_entry_allowed": c.trade_entry_allowed,
                    "note": c.note,
                    "htf_recovery_transition_ids": ";".join(map(str, c.htf_recovery_transition_ids)),
                    "ltf_recovery_transition_ids": ";".join(map(str, c.ltf_recovery_transition_ids)),
                }
            )
    return destination


def write_mtf_opportunities_csv(report: MtfSfpReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OPPORTUNITY_FIELDS)
        writer.writeheader()
        for o in report.opportunities:
            writer.writerow(
                {
                    "opportunity_id": o.opportunity_id,
                    "status": o.status.value,
                    "expected_direction": o.expected_direction.value,
                    "ltf_bos_kind": o.ltf_bos_kind.value,
                    "ltf_bos_event_time": o.ltf_bos_event_time.isoformat(),
                    "ltf_bos_candle_index": o.ltf_bos_candle_index,
                    "ltf_bos_level_id": o.ltf_bos_level_id,
                    "ltf_bos_level_price": o.ltf_bos_level_price,
                    "candidate_ids": ";".join(str(x) for x in o.candidate_ids),
                    "htf_episode_ids": ";".join(str(x) for x in o.htf_episode_ids),
                    "htf_level_ids": ";".join(str(x) for x in o.htf_level_ids),
                    "context_count": o.context_count,
                    "earliest_sfp_time": o.earliest_sfp_time.isoformat(),
                    "latest_sfp_time": o.latest_sfp_time.isoformat(),
                    "representative_candidate_id": o.representative_candidate_id,
                    "entry_search_allowed": o.entry_search_allowed,
                    "trade_entry_allowed": o.trade_entry_allowed,
                    "note": o.note,
                    "htf_recovery_transition_ids": ";".join(map(str, o.htf_recovery_transition_ids)),
                    "ltf_recovery_transition_ids": ";".join(map(str, o.ltf_recovery_transition_ids)),
                    "entry_geometry_ready_time": o.entry_geometry_ready_time.isoformat() if o.entry_geometry_ready_time else "",
                    "entry_geometry_transition_id": o.entry_geometry_transition_id if o.entry_geometry_transition_id is not None else "",
                    "impulse_start_price": o.impulse_start_price if o.impulse_start_price is not None else "",
                    "impulse_end_price": o.impulse_end_price if o.impulse_end_price is not None else "",
                    "entry_zone_low": o.entry_zone_low if o.entry_zone_low is not None else "",
                    "entry_zone_high": o.entry_zone_high if o.entry_zone_high is not None else "",
                    "entry_anchor_level_id": o.entry_anchor_level_id if o.entry_anchor_level_id is not None else "",
                    "entry_correction_level_id": o.entry_correction_level_id if o.entry_correction_level_id is not None else "",
                    "entry_correction_price": o.entry_correction_price if o.entry_correction_price is not None else "",
                    "entry_geometry_policy": o.entry_geometry_policy,
                    "stop_loss_price": o.stop_loss_price if o.stop_loss_price is not None else "",
                    "target_price": o.target_price if o.target_price is not None else "",
                    "stop_loss_policy": o.stop_loss_policy,
                    "target_policy": o.target_policy,
                    "rr_minimum": o.rr_minimum if o.rr_minimum is not None else "",
                    "rr_maximum": o.rr_maximum if o.rr_maximum is not None else "",
                    "entry_plan_status": o.entry_plan_status,
                }
            )
    return destination


def write_candidate_quality_audit_csv(report: MtfSfpReport, path: str | Path) -> Path:
    """Write an all-candidate audit table for manual chart review."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    opportunity_context_count = {o.opportunity_id: o.context_count for o in report.opportunities}
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        for c in report.candidates:
            writer.writerow(
                {
                    "candidate_id": c.candidate_id,
                    "outcome": c.status.value,
                    "direction": c.expected_direction.value,
                    "sfp_time": c.htf_sfp_event_time.isoformat(),
                    "sfp_level": c.htf_level_price,
                    "sfp_liquidity_origin": c.htf_liquidity_origin or "",
                    "sfp_range_id": c.htf_range_id if c.htf_range_id is not None else "",
                    "sfp_extreme": c.sfp_invalidation_price if c.sfp_invalidation_price is not None else "",
                    "invalidation_time": c.sfp_invalidation_event_time.isoformat() if c.sfp_invalidation_event_time else "",
                    "invalidation_close": c.sfp_invalidation_close_price if c.sfp_invalidation_close_price is not None else "",
                    "ltf_bos_time": c.ltf_bos_event_time.isoformat() if c.ltf_bos_event_time else "",
                    "ltf_bos_level": c.ltf_bos_level_price if c.ltf_bos_level_price is not None else "",
                    "elapsed_ltf_bars": c.elapsed_ltf_bars if c.elapsed_ltf_bars is not None else "",
                    "elapsed_minutes": c.elapsed_minutes if c.elapsed_minutes is not None else "",
                    "deadline": c.deadline_event_time.isoformat() if c.deadline_event_time else "",
                    "opportunity_id": c.opportunity_id if c.opportunity_id is not None else "",
                    "shared_opportunity_context_count": opportunity_context_count.get(c.opportunity_id, ""),
                    "note": c.note,
                    "htf_recovery_transition_ids": ";".join(map(str, c.htf_recovery_transition_ids)),
                    "ltf_recovery_transition_ids": ";".join(map(str, c.ltf_recovery_transition_ids)),
                }
            )
    return destination


def write_mtf_summary_json(report: MtfSfpReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(c.status.value for c in report.candidates)
    direction_counts = Counter(c.expected_direction.value for c in report.candidates)
    liquidity_origin_counts = Counter((c.htf_liquidity_origin or "UNKNOWN") for c in report.candidates)
    context_distribution = Counter(o.context_count for o in report.opportunities)
    payload = {
        "analysis_mode": report.analysis_mode.value,
        "htf_minutes": report.htf_minutes,
        "ltf_minutes": report.ltf_minutes,
        "max_wait_ltf_bars": report.max_wait_ltf_bars,
        "max_wait_minutes": report.max_wait_minutes,
        "max_wait_effective_minutes": (report.max_wait_minutes if report.max_wait_minutes is not None else (report.max_wait_ltf_bars * report.ltf_minutes if report.max_wait_ltf_bars is not None else None)),
        "candidate_count": len(report.candidates),
        "status_counts": dict(sorted(counts.items())),
        "direction_counts": dict(sorted(direction_counts.items())),
        "liquidity_origin_counts": dict(sorted(liquidity_origin_counts.items())),
        "entry_search_allowed_link_count": sum(c.entry_search_allowed for c in report.candidates),
        "trade_entry_allowed_count": sum(c.trade_entry_allowed for c in report.candidates),
        "confirmed_link_count": report.confirmed_count,
        "invalidated_before_bos_count": report.invalidated_count,
        "unique_ltf_bos_count": report.unique_ltf_bos_count,
        "shared_bos_link_count": report.shared_bos_link_count,
        "opportunity_count": report.opportunity_count,
        "opportunity_context_count_distribution": {str(k): v for k, v in sorted(context_distribution.items())},
        "candidate_not_before": report.candidate_not_before.isoformat() if report.candidate_not_before else None,
        "ltf_observation_start": report.ltf_observation_start.isoformat() if report.ltf_observation_start else None,
        "ltf_observation_end": report.ltf_observation_end.isoformat() if report.ltf_observation_end else None,
        "source_policy": report.source_policy,
        "mapping_policy": report.mapping_policy,
        "expiry_policy": report.expiry_policy,
        "entry_policy": report.entry_policy,
        "linkage_policy": report.linkage_policy,
        "invalidation_policy": report.invalidation_policy,
        "opportunity_policy": report.opportunity_policy,
        "opportunity_dedup_scope": report.opportunity_dedup_scope,
        "entry_engine_blocking_reasons": list(report.entry_engine_blocking_reasons),
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
