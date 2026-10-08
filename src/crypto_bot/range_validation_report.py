from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from crypto_bot.strategy.range_validation import (
    OriginMtfFunnel,
    RangeAuditRow,
    RangeStageFunnel,
    RangeValidationMatrixRow,
)


AUDIT_FIELDS = [
    "range_id",
    "evaluation_context",
    "impulse_direction",
    "impulse_bos_time",
    "first_boundary_kind",
    "first_boundary_price",
    "first_boundary_time",
    "second_boundary_kind",
    "second_boundary_price",
    "second_boundary_time",
    "lower",
    "upper",
    "width",
    "midpoint",
    "status",
    "status_time",
    "midpoint_reaction_time",
    "midpoint_reaction_price",
    "midpoint_distance_fraction",
    "internal_bos_count",
    "upper_boundary_state",
    "lower_boundary_state",
    "boundary_sweep_episode_count",
    "sfp_formation_count",
    "first_sfp_time",
    "last_sfp_time",
    "boundary_clarity_review_key",
    "manual_boundary_clarity_review",
    "audit_window_start",
    "audit_window_end",
]

MATRIX_FIELDS = [
    "midpoint_tolerance_fraction",
    "wait_mode",
    "wait_value",
    "effective_wait_minutes",
    "range_candidate_count_loaded",
    "ever_validated_range_count_loaded",
    "ranges_with_boundary_sweep_loaded",
    "boundary_sweep_episode_count_loaded",
    "ranges_with_sfp_loaded",
    "range_sfp_formation_count_loaded",
    "range_sfp_context_count_evaluation",
    "range_invalidated_before_bos",
    "range_expired",
    "range_right_censored",
    "range_no_bos_available_data",
    "range_coverage_missing",
    "range_bos_confirmed_contexts",
    "opportunities_with_range_context",
]


def _iso(value):
    return value.isoformat() if value is not None else ""


def write_range_validation_audit_csv(rows: tuple[RangeAuditRow, ...], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "range_id": row.range_id,
                    "evaluation_context": row.evaluation_context,
                    "impulse_direction": row.impulse_direction,
                    "impulse_bos_time": _iso(row.impulse_bos_time),
                    "first_boundary_kind": row.first_boundary_kind,
                    "first_boundary_price": row.first_boundary_price,
                    "first_boundary_time": _iso(row.first_boundary_time),
                    "second_boundary_kind": row.second_boundary_kind,
                    "second_boundary_price": row.second_boundary_price,
                    "second_boundary_time": _iso(row.second_boundary_time),
                    "lower": row.lower,
                    "upper": row.upper,
                    "width": row.width,
                    "midpoint": row.midpoint,
                    "status": row.status,
                    "status_time": _iso(row.status_time),
                    "midpoint_reaction_time": _iso(row.midpoint_reaction_time),
                    "midpoint_reaction_price": row.midpoint_reaction_price if row.midpoint_reaction_price is not None else "",
                    "midpoint_distance_fraction": (
                        row.midpoint_distance_fraction if row.midpoint_distance_fraction is not None else ""
                    ),
                    "internal_bos_count": row.internal_bos_count,
                    "upper_boundary_state": row.upper_boundary_state,
                    "lower_boundary_state": row.lower_boundary_state,
                    "boundary_sweep_episode_count": row.boundary_sweep_episode_count,
                    "sfp_formation_count": row.sfp_formation_count,
                    "first_sfp_time": _iso(row.first_sfp_time),
                    "last_sfp_time": _iso(row.last_sfp_time),
                    "boundary_clarity_review_key": row.boundary_clarity_review_key,
                    "manual_boundary_clarity_review": row.manual_boundary_clarity_review,
                    "audit_window_start": _iso(row.audit_window_start),
                    "audit_window_end": _iso(row.audit_window_end),
                }
            )
    return destination


def write_range_validation_matrix_csv(
    rows: tuple[RangeValidationMatrixRow, ...] | list[RangeValidationMatrixRow],
    path: str | Path,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS)
        writer.writeheader()
        for row in rows:
            payload = asdict(row)
            writer.writerow({key: "" if payload[key] is None else payload[key] for key in MATRIX_FIELDS})
    return destination


def write_range_validation_funnel_json(
    *,
    stage: RangeStageFunnel,
    structural: OriginMtfFunnel,
    range_boundary: OriginMtfFunnel,
    midpoint_tolerance_fraction: float,
    wait_mode: str,
    wait_value: int | None,
    effective_wait_minutes: int | None,
    path: str | Path,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "range_stage_funnel": asdict(stage),
        "mtf_origin_funnels": {
            "STRUCTURAL_SWING": asdict(structural),
            "RANGE_BOUNDARY": asdict(range_boundary),
        },
        "parameter_context": {
            "midpoint_tolerance_fraction": midpoint_tolerance_fraction,
            "wait_mode": wait_mode,
            "wait_value": wait_value,
            "effective_wait_minutes": effective_wait_minutes,
        },
        "interpretation": {
            "range_stage_counts_are_not_all_one_to_one": True,
            "origin_opportunity_counts_are_not_additive_when_one_opportunity_has_mixed_origin_context": True,
            "trade_entries_created": 0,
            "boundary_clarity_rule": (
                "SOURCE NUANCE: non-crisp boundaries may define a valid price area; materially ambiguous boundaries should be skipped. No numeric clarity threshold is defined; "
                "manual review remains required and automatic Entry Engine stays blocked."
            ),
        },
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
