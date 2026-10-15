"""Preregistered full-period source replay; historical position engines are trapped."""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import importlib.abc
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from machine_strategy_v4_1_historical_adapter import (
    V41HistoricalAdapter,
    market_inputs,
)
from okx_v3_input_bridge_v1 import aggregate

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_1_implementation_readiness_v1"
START = 1728777600
CUTS = tuple(
    int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())
    for s in ("2024-10-20", "2025-10-13", "2026-10-06")
)
FORBIDDEN = {
    "observe_m15_bar",
    "_drive_case",
    "_cash",
    "_funding_min",
    "_closed_cash",
    "evaluate_fixture",
    "evaluate_historical_catalog",
    "adverse_funding_witness",
}
FORBIDDEN_MODULES = {
    "okx_v3_compatibility_runner_v1",
    "machine_strategy_v4_guarded_runner",
    "machine_strategy_v4_1_guarded_runner",
}


class FinancialImportTrap(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in FORBIDDEN_MODULES:
            raise RuntimeError("HISTORICAL_FINANCIAL_RUNNER_IMPORT_FORBIDDEN")


def trap(frame, event, arg):
    if event == "call" and frame.f_code.co_name in FORBIDDEN:
        raise RuntimeError("HISTORICAL_POSITION_ENGINE_FORBIDDEN")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def persist(progress):
    path = DEST / "SOURCE_REPLAY_PROGRESS.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n")
    temp.replace(path)
    print("VERIFIABLE_SOURCE_PROGRESS", digest(path), flush=True)


def check(resume_existing=False, expected_progress_sha=None):
    prereg = {
        "scope": "FULL_SEALED_HISTORY_SOURCE_ONLY",
        "cutoffs_UTC_seconds": CUTS,
        "evaluation_start": START,
        "products": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"],
        "policy_selection_by_catalog_counts": False,
        "historical_position_evaluations": 0,
        "trade_entry_allowed": False,
    }
    file = DEST / "SOURCE_REPLAY_PREREGISTRATION.json"
    expected = json.dumps(prereg, indent=2, sort_keys=True) + "\n"
    if file.exists() and file.read_text() != expected:
        raise RuntimeError("REPLAY_PREREG_CHANGED")
    file.write_text(expected)
    receipt = {**prereg, "products": {}, "historical_financial_authorized": False}
    source_files = [
        "scripts/machine_strategy_v4_1_historical_adapter.py",
        "scripts/machine_strategy_v4_1_contracts.py",
        "scripts/machine_strategy_v4_1_selected_poi_inventory.py",
        "scripts/machine_strategy_v4_1_execution_binding.py",
        "scripts/check_machine_strategy_v4_1_source_replay.py",
        "scripts/verify_machine_strategy_v4_1_source_adapter.py",
    ]
    context = {
        "source_code_sha256": {name: digest(ROOT / name) for name in source_files},
        "design_manifest_sha256": "4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790",
        "StageA_manifest_sha256": "e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0",
        "preregistration_sha256": digest(file),
    }
    progress_file = DEST / "SOURCE_REPLAY_PROGRESS.json"
    if resume_existing:
        if not expected_progress_sha or digest(progress_file) != expected_progress_sha:
            raise RuntimeError("EXTERNAL_SOURCE_PROGRESS_PIN_MISMATCH")
        receipt = json.loads(progress_file.read_text())
        if receipt["run_context"] != context:
            raise RuntimeError("SOURCE_CODE_OR_INPUT_CONTEXT_CHANGED")
    elif progress_file.exists():
        raise RuntimeError("SOURCE_PROGRESS_EXISTS_USE_VERIFIED_RESUME")
    else:
        receipt["run_context"] = context
    old = sys.getprofile()
    if FORBIDDEN_MODULES.intersection(sys.modules):
        raise RuntimeError("FINANCIAL_RUNNER_PREIMPORTED")
    import_trap = FinancialImportTrap()
    sys.meta_path.insert(0, import_trap)
    sys.setprofile(trap)
    try:
        for product in prereg["products"]:
            market = market_inputs(product)
            end = market[15][-1].end
            if product in receipt["products"]:
                record = receipt["products"][product]
                if (
                    digest(ROOT / record["source_artifact"])
                    != record["source_artifact_sha256"]
                ):
                    raise RuntimeError("SAVED_SOURCE_ARTIFACT_CHANGED")
                checkpoints = {
                    int(k): v for k, v in record["full_checkpoint_digests"].items()
                }
                print("VERIFIED_SOURCE_REUSE", product, flush=True)
            else:
                adapter = V41HistoricalAdapter(product, market, START, end)
                print("SOURCE_ONLY", product, "full_stream_start", flush=True)
                orders, audit = adapter.run(end, CUTS)
                checkpoints = dict(adapter.checkpoint_digests)
                payload = json.dumps(
                    {"preentry_model_catalog": orders, "source_only_audit": audit},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                stem = product.replace("-", "_")
                artifact = DEST / (stem + ".source_only.json.gz")
                artifact.write_bytes(gzip.compress(payload, mtime=0))
                record = {
                    "native_bar_count": len(market[15]),
                    "data_start": market[15][0].start,
                    "data_end_exclusive": end,
                    "source_artifact": str(artifact.relative_to(ROOT)),
                    "source_artifact_sha256": digest(artifact),
                    "full_checkpoint_digests": {
                        str(k): v for k, v in checkpoints.items()
                    },
                    "raw_family_coverage": dict(
                        Counter(row[1] for row in audit["raw_origins"])
                    ),
                    "raw_family_tf_direction_coverage": dict(
                        Counter(
                            f"{row[1]}|H{row[4] // 60}|{row[3]}"
                            for row in audit["raw_origins"]
                        )
                    ),
                    "raw_field_provenance_validated": all(
                        row[4] in (60, 240)
                        and row[3] in ("LONG", "SHORT")
                        and row[2] % (row[4] * 60) == 0
                        and bool(row[0])
                        and bool(row[5])
                        for row in audit["raw_origins"]
                    ),
                    "cutoffs": {},
                    "position_engine_trap_active": True,
                }
                del adapter, orders, audit, payload
                gc.collect()
                receipt["products"][product] = record
                persist(receipt)
                print("SOURCE_ONLY", product, "full_stream_complete", flush=True)
            if not record.get("full_deterministic_replay"):
                replay = V41HistoricalAdapter(product, market, START, end)
                replay_rows, replay_audit = replay.run(end, CUTS)
                replay_payload = json.dumps(
                    {
                        "preentry_model_catalog": replay_rows,
                        "source_only_audit": replay_audit,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                if (
                    hashlib.sha256(gzip.compress(replay_payload, mtime=0)).hexdigest()
                    != record["source_artifact_sha256"]
                ):
                    raise RuntimeError("FULL_SOURCE_REPLAY_BYTES_DIFFER")
                record["full_deterministic_replay"] = "PASS"
                persist(receipt)
                print(
                    "SOURCE_ONLY", product, "full_deterministic_replay_PASS", flush=True
                )
                del replay, replay_rows, replay_audit, replay_payload
                gc.collect()
            for cutoff in CUTS:
                if str(cutoff) in record["cutoffs"]:
                    continue
                prefix = {
                    tf: [b for b in bars if b.end <= cutoff]
                    for tf, bars in market.items()
                }
                trimmed = V41HistoricalAdapter(product, prefix, START, end)
                rows, _ = trimmed.catalog(cutoff)
                prefix_digest = trimmed.source_digest(cutoff, rows)
                del trimmed, rows, prefix
                gc.collect()
                native = [
                    b
                    if b.end <= cutoff
                    else replace(
                        b,
                        **{
                            key: getattr(b, key) * Decimal(2)
                            for key in ("open", "high", "low", "close")
                        },
                    )
                    for b in market[15]
                ]
                mutated = {15: native}
                for tf in (60, 240, 1440):
                    mutated[tf], _ = aggregate(native, tf * 60)
                changed = V41HistoricalAdapter(product, mutated, START, end)
                rows, _ = changed.catalog(cutoff)
                changed_digest = changed.source_digest(cutoff, rows)
                if not checkpoints[cutoff] == prefix_digest == changed_digest:
                    raise RuntimeError(
                        "SOURCE_PREFIX_FUTURE_MUTATION_MISMATCH:"
                        + product
                        + ":"
                        + str(cutoff)
                    )
                record["cutoffs"][str(cutoff)] = {
                    "full_stream": checkpoints[cutoff],
                    "truncated": prefix_digest,
                    "future_mutated": changed_digest,
                    "deterministic_source_replay": "PASS",
                }
                receipt["products"][product] = record
                persist(receipt)
                del changed, rows, native, mutated
                gc.collect()
                print("SOURCE_ONLY", product, "checkpoint", cutoff, "PASS", flush=True)
            receipt["products"][product] = record
            (DEST / "SOURCE_PREFIX_REPLAY_RECEIPT.partial.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n"
            )
            del market
            gc.collect()
    finally:
        sys.setprofile(old)
        sys.meta_path.remove(import_trap)
    receipt["source_only_causality"] = "PASS"
    persist(receipt)
    (DEST / "SOURCE_PREFIX_REPLAY_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return {
        "source_only_causality": "PASS",
        "products": 2,
        "checkpoints": 6,
        "historical_position_evaluations": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-progress-sha256")
    args = parser.parse_args()
    if args.resume_existing and not args.expected_progress_sha256:
        parser.error("external progress SHA required")
    print(
        json.dumps(
            check(args.resume_existing, args.expected_progress_sha256), sort_keys=True
        )
    )
