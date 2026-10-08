from __future__ import annotations

import csv
import json
from pathlib import Path

from crypto_bot.strategy.global_opportunity import GlobalOpportunity
from crypto_bot.strategy.mtf_diagnostics import BosInventory, CandidateBosDiagnostic


GLOBAL_FIELDS = [
    "global_opportunity_id",
    "symbol",
    "direction",
    "cluster_start_time",
    "cluster_end_time",
    "representative_confirmation_time",
    "pair_labels",
    "local_opportunity_ids",
    "context_count",
    "local_opportunity_count",
    "cluster_window_minutes",
    "trade_entry_allowed",
    "note",
    "recovery_context_refs",
    "entry_search_allowed",
    "analysis_mode",
]

DIAGNOSTIC_FIELDS = [
    "candidate_id",
    "sfp_time",
    "direction",
    "candidate_status",
    "invalidation_time",
    "first_expected_bos_after_sfp",
    "first_opposite_bos_after_sfp",
    "expected_bos_exists_after_sfp",
    "expected_bos_before_invalidation",
]


def write_global_opportunities_csv(opportunities: tuple[GlobalOpportunity, ...], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GLOBAL_FIELDS)
        writer.writeheader()
        for o in opportunities:
            writer.writerow(
                {
                    "global_opportunity_id": o.global_opportunity_id,
                    "symbol": o.symbol,
                    "direction": o.expected_direction.value,
                    "cluster_start_time": o.cluster_start_time.isoformat(),
                    "cluster_end_time": o.cluster_end_time.isoformat(),
                    "representative_confirmation_time": o.representative_confirmation_time.isoformat(),
                    "pair_labels": ";".join(o.pair_labels),
                    "local_opportunity_ids": ";".join(o.local_opportunity_ids),
                    "context_count": o.context_count,
                    "local_opportunity_count": o.local_opportunity_count,
                    "cluster_window_minutes": o.cluster_window_minutes,
                    "trade_entry_allowed": o.trade_entry_allowed,
                    "note": o.note,
                    "recovery_context_refs": ";".join(o.recovery_context_refs),
                    "entry_search_allowed": o.entry_search_allowed,
                    "analysis_mode": o.analysis_mode.value,
                }
            )
    return destination


def write_global_summary_json(
    opportunities: tuple[GlobalOpportunity, ...],
    *,
    symbol: str,
    cluster_window_minutes: int,
    pair_local_opportunity_count: int,
    path: str | Path,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "symbol": symbol,
        "analysis_mode": (
            next(iter({o.analysis_mode for o in opportunities})).value
            if opportunities and len({o.analysis_mode for o in opportunities}) == 1
            else ("MIXED" if opportunities else None)
        ),
        "cluster_window_minutes": cluster_window_minutes,
        "pair_local_opportunity_count": pair_local_opportunity_count,
        "global_opportunity_count": len(opportunities),
        "cross_pair_duplicates_collapsed": max(0, pair_local_opportunity_count - len(opportunities)),
        "trade_entry_allowed_count": sum(o.trade_entry_allowed for o in opportunities),
        "policy": (
            "Cross-pair de-duplication is TECHNICAL_NORMALIZATION. Exact timestamp (0 minutes) is deterministic; "
            "positive windows are BACKTEST_PARAMETER and are not source rules."
        ),
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def write_bos_diagnostic_csv(rows: tuple[CandidateBosDiagnostic, ...], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DIAGNOSTIC_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "candidate_id": r.candidate_id,
                    "sfp_time": r.sfp_time.isoformat(),
                    "direction": r.direction,
                    "candidate_status": r.candidate_status,
                    "invalidation_time": r.invalidation_time.isoformat() if r.invalidation_time else "",
                    "first_expected_bos_after_sfp": r.first_expected_bos_after_sfp.isoformat() if r.first_expected_bos_after_sfp else "",
                    "first_opposite_bos_after_sfp": r.first_opposite_bos_after_sfp.isoformat() if r.first_opposite_bos_after_sfp else "",
                    "expected_bos_exists_after_sfp": r.expected_bos_exists_after_sfp,
                    "expected_bos_before_invalidation": r.expected_bos_before_invalidation,
                }
            )
    return destination


def write_bos_inventory_json(inventory: BosInventory, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bullish_structure_broken_bos": inventory.bullish_structure_broken_bos,
        "bearish_structure_broken_bos": inventory.bearish_structure_broken_bos,
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
