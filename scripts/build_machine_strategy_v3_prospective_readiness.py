"""Prospective evidence/readiness freeze; never executes candidate behavior."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from hashlib import sha256
from pathlib import Path

from machine_strategy_v3_prospective_integrity import (
    CONTRACT,
    DAY,
    DEST,
    PINNED,
    ROOT,
    SYMBOLS,
    earliest_boundary,
    prospective_observation,
    selected_instrument,
    timestamp,
    utc,
)

DECISION = "V3_PROSPECTIVE_READINESS_FROZEN_STOP"
HEAD = "44b6821d5a209e41aa8279c5fd26645709b34782"
PARENTS = {
    "docs/machine_strategy_v3_design": "f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0",
    "docs/machine_strategy_v3_implementation_readiness": "d5eb8bd912a0b290679b30969dfa5e8015c4212c07b3263f42c9ca4a34d3a018",
    "docs/machine_strategy_v3_market_metadata_recovery": "74c7d32b4e832d01d0d8f1fd6bb56ac7e218730bcb5613f4986a24b339c70e80",
    "docs/machine_strategy_failure_audit_v1": "9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201",
}
CODE = [
    "scripts/machine_strategy_v3_prospective_integrity.py",
    "scripts/collect_machine_strategy_v3_prospective_public.py",
    "scripts/build_machine_strategy_v3_prospective_readiness.py",
    "tests/test_machine_strategy_v3_prospective_readiness.py",
]
OUTPUTS = [
    "CURRENT_METADATA_CAPTURE.json",
    "PROSPECTIVE_TICK_EPOCH_PROTOCOL.json",
    "WARMUP_SOURCE_INVENTORY.json",
    "WARMUP_CONTINUITY.json",
    "WARMUP_CONFLICTS.json",
    "RAW_ACCESS_EMBARGO_SPEC.json",
    "OOS_REGISTRATION_READINESS.json",
    "CONTROL_PLANE_GUARD_QA.json",
    "FROZEN_INPUT_VERIFICATION.json",
    "STATIC_OUTCOME_ISOLATION.json",
]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")


def verify_parent(path, expected):
    manifest = Path(path) / "freeze_manifest.json"
    if digest(manifest) != expected:
        raise ValueError("PARENT_MANIFEST_CHANGED")
    m = read(manifest)
    prefix = str(Path(path).relative_to(ROOT)) + "/"
    actual = {
        str(p.relative_to(ROOT))
        for p in Path(path).rglob("*")
        if p.is_file() and p != manifest
    }
    if actual != {p for p in m["artifacts"] if p.startswith(prefix)}:
        raise ValueError("FROZEN_NAMESPACE_MEMBERSHIP_CHANGED")
    for name, value in m["artifacts"].items():
        if digest(ROOT / name) != value:
            raise ValueError("FROZEN_ARTIFACT_CHANGED: " + name)
    if m.get("trade_entry_allowed") is not False or m.get("LIVE_enabled") is not False:
        raise ValueError("UNSAFE_PARENT")
    return {"path": str(manifest.relative_to(ROOT)), "sha256": expected}


def receipt_body(receipt_path):
    receipt_path = Path(receipt_path)
    r = read(receipt_path)
    name = r.get("body_path", r.get("raw_path", r.get("body_file")))
    if not name:
        raise ValueError("RAW_BODY_PATH_REQUIRED")
    if name.startswith("machine_strategy_v3_prospective_readiness/"):
        body = ROOT / "docs" / name
    else:
        body = receipt_path.parent / name
    body = body.resolve()
    if not body.is_relative_to(DEST / "evidence"):
        raise ValueError("RECEIPT_BODY_OUTSIDE_NEW_EVIDENCE")
    expected = r.get("body_sha256", r.get("raw_sha256"))
    if digest(body) != expected or body.stat().st_size != r.get(
        "body_bytes", r.get("raw_byte_count")
    ):
        raise ValueError("RECEIPT_BODY_HASH_OR_LENGTH_MISMATCH")
    started = r.get("request_started_at_utc", r.get("requested_at_utc"))
    ended = r.get("retrieved_at_utc", r.get("completed_at_utc"))
    if timestamp(ended) < timestamp(started):
        raise ValueError("RECEIPT_TIME_REVERSED")
    for k in r.get("response_headers_allowlist", r.get("headers", {})):
        if k.lower() in {
            "cookie",
            "set-cookie",
            "authorization",
            "proxy-authorization",
        }:
            raise ValueError("SENSITIVE_RECEIPT_HEADER")
    return r, body


def static_isolation():
    allowed = {
        "__future__",
        "argparse",
        "ast",
        "csv",
        "gzip",
        "json",
        "os",
        "sys",
        "datetime",
        "decimal",
        "hashlib",
        "pathlib",
        "subprocess",
        "uuid",
        "urllib",
        "machine_strategy_v3_prospective_integrity",
    }
    modules = {}
    for name in CODE[:3]:
        tree = ast.parse((ROOT / name).read_text())
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(x.name for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    raise ValueError("RELATIVE_IMPORT_NOT_ALLOWED")
                imports.append(node.module)
        if any(not module or module.split(".")[0] not in allowed for module in imports):
            raise ValueError("UNEXPECTED_INTEGRITY_IMPORT")
        modules[name] = sorted(imports)
    return {
        "allowed_import_graph": modules,
        "strategy_or_state_modules_imported": False,
        "financial_columns_parsed": False,
        "parent_verification": "HASH_ONLY; manifest schemas only",
        "runtime_boundary": "Fresh worker denies unallowlisted file/import/socket/subprocess audit events",
        "os_isolation": "NOT_ESTABLISHED; OOS registration STOP",
        "hostile_native_code_protection_claimed": False,
    }


def selected_capture(body, receipt, symbol):
    if receipt.get("response_truncated") is not False:
        return {"verified": False, "reason": "COMPLETE_RAW_RESPONSE_REQUIRED"}
    return selected_instrument(body, receipt["http_status"], symbol)


def prepare(output=DEST):
    output = Path(output)
    if (output / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_FREEZE_PRESERVED")
    output.mkdir(parents=True, exist_ok=True)
    parents = {p: verify_parent(ROOT / p, h) for p, h in PARENTS.items()}
    receipts = []
    for p in sorted((DEST / "evidence").rglob("*.receipt.json")):
        r, body = receipt_body(p)
        receipts.append(
            {
                "path": str(p.relative_to(ROOT)),
                "body_sha256": digest(body),
                "http_status": r.get("http_status"),
            }
        )
    captures = {}
    inventory = read(DEST / "evidence/metadata/CAPTURE_INVENTORY.json")
    for symbol in SYMBOLS:
        row = next(
            x for x in inventory["rows"] if "symbol=" + symbol in x["requested_url"]
        )
        r, body = receipt_body(ROOT / row["receipt_path"])
        chosen = selected_capture(body.read_bytes(), r, symbol)
        captures[symbol] = {
            "receipt": row["receipt_path"],
            "raw_sha256": digest(body),
            "selected_fields": chosen,
            "prospective_observation": prospective_observation(
                chosen, r["request_started_at_utc"], r["retrieved_at_utc"]
            ),
        }
    audit = read(DEST / "evidence/warmup/local_audit.json")
    worker = {
        s: read(DEST / "evidence/integrity_access" / (s + ".reviewed.json"))
        for s in SYMBOLS
    }
    for s in SYMBOLS:
        if worker[s]["code_sha256"] != digest(
            ROOT / "scripts/machine_strategy_v3_prospective_integrity.py"
        ):
            raise ValueError("WORKER_REPLAY_NOT_FINAL_CODE")
        local = audit["sources"][s]["combined_closed"]
        if (
            worker[s]["assessment"]["present_bars"] != local["present_bars"]
            or worker[s]["assessment"]["missing_bars"] != local["missing_bars"]
        ):
            raise ValueError("INDEPENDENT_WARMUP_REPLAY_MISMATCH")
        for source_path, h in PINNED[s].items():
            if digest(ROOT / source_path) != h:
                raise ValueError("PINNED_SOURCE_CHANGED")
    impl_time = int(
        subprocess.check_output(
            [
                "git",
                "show",
                "-s",
                "--format=%ct",
                "43e57ee5c7867dd9421961629746555c8a2e9556",
            ],
            cwd=ROOT,
        )
    )
    observed = int(timestamp(audit["audit_time_utc"]))
    illustrative = earliest_boundary(impl_time, observed)
    blockers = [
        "OFFICIAL_CURRENT_INSTRUMENT_CAPTURE_HTTP_403",
        "WARMUP_CLOSED_NATIVE_M15_GAPS_BOTH_SYMBOLS",
        "WARMUP_PUBLIC_MIRROR_AUTHENTICITY_UNVERIFIED",
        "LITERAL_COMPLETED_WARMUP_BEFORE_STRICT_NEXT_START_CONTRADICTION",
        "FROZEN_ACTIVE_TEST_HEADERS_CONFLICT_WITH_CURRENT_TASK",
        "NO_OS_LEVEL_STRATEGY_STATE_ISOLATION",
        "FROZEN_RUNNER_DIRECT_AUTH_DESIGN_REQUIRES_NEW_VERSION",
    ]
    result = {
        "CURRENT_METADATA_CAPTURE.json": {
            "verdict": "STOP",
            "symbols": captures,
            "receipts_verified": receipts,
            "current_tick_epochs": [],
            "historical_epochs_changed": False,
        },
        "PROSPECTIVE_TICK_EPOCH_PROTOCOL.json": {
            "contract": CONTRACT,
            "symbols": SYMBOLS,
            "official_capture_acceptance": "HTTPS production linear instruments-info; retCode0; unique symbol; LinearPerpetual/USDT quote+settle/Trading; positive exact string priceFilter.tickSize",
            "known_at": "Validated response completion UTC, never server Date or request start; no backdating",
            "notice_monitoring": "Separately append-only capture official index+dated notices, retain issuer publication/effective/retrieval times; search is bounded, not complete change proof",
            "opening": "Point-in-time capture no earlier than max(proven applied/effective boundary, actual knowledge). No continuous epoch from a snapshot alone",
            "closing": "Any filter change, ambiguous notice, failure or unknown interval closes eligibility before next decision; changed setting requires post-effective official applied capture",
            "between_captures": "UNVERIFIED, even when equal; no assumed unchanged interval",
            "freshness": "No retained snapshot alone authorizes a later candidate decision; per-decision causal production validation would require separate complete proof/control gate",
            "continuous_coverage_proven": False,
            "activated_daemon": False,
            "strategy_decisions_authorized": False,
        },
        "WARMUP_SOURCE_INVENTORY.json": {
            "sources": audit["sources"],
            "source_identity": "Row BYBIT/symbol/15/is_closed1 labels checked; public mirror attribution is not independent exchange authenticity",
            "acquisition": "Public official native M15 requests only; immutable receipt hashes; no privateAPI or country-block evasion",
            "raw_source_prices_modified": False,
        },
        "WARMUP_CONTINUITY.json": {
            "snapshot_utc": audit["audit_time_utc"],
            "illustrative_only": True,
            "interval": [audit["warmup_start"], audit["illustrative_end_exclusive"]],
            "completed_end_exclusive": audit["closed_window_end_exclusive"],
            "expected_completed_bars": audit["closed_expected_bars"],
            "unfinished_future_bars": audit["unfinished_remaining_bars"],
            "symbols": {s: worker[s]["assessment"] for s in SYMBOLS},
            "independent_worker_replay": "PASS",
            "365_day_verified": False,
            "interpolation": False,
            "H1_H4_D1_derived": False,
        },
        "WARMUP_CONFLICTS.json": {
            "overlap": audit["overlap"],
            "proof_limit": "Zero shared bars provides no corroboration; zero conflicts is not independent authenticity proof",
            "source_choice_from_behavior": False,
        },
        "RAW_ACCESS_EMBARGO_SPEC.json": {
            "locked_duration_seconds": 365 * DAY,
            "pre_start_warmup_seconds": 365 * DAY,
            "allowed": [
                "logged hash",
                "closed native M15 continuity",
                "duplicate/identity/exact overlap checks",
                "metadata chronology",
            ],
            "forbidden": [
                "candidate signals",
                "positions",
                "trade labels",
                "case outcomes",
                "equity",
                "interim optimization",
                "raw-price inference of candidate behavior",
            ],
            "worker": "Fresh standalone integrity process, exact raw-path+hash allowlist; no candidate imports; append-only exclusive-create access records",
            "dynamic_audit_hook_boundary": "deny unexpected file/import/socket/subprocess",
            "os_filesystem_sandbox": "NOT_ESTABLISHED",
            "registration": "STOP until independent OS-level no-state access enforcement exists",
            "invalidation": [
                "any post-registration material implementation change",
                "embargo breach",
                "unresolved gaps/conflicts/metadata",
                "uncommitted hashes",
                "date shift after exposure",
            ],
            "orders_or_positions_started": False,
        },
        "OOS_REGISTRATION_READINESS.json": {
            "state": DECISION,
            "ready": False,
            "registration_created": False,
            "registration_commit": None,
            "actual_start": None,
            "actual_end_exclusive": None,
            "formula": "First UTC D1 open STRICTLY AFTER MAX(implementation freeze committer time, separate registration committer time)",
            "implementation_commit_time": impl_time,
            "illustrative_calculation_only": {
                "proposed_commit_time": observed,
                "start": illustrative,
                "start_utc": utc(illustrative),
                "end_exclusive": illustrative + 365 * DAY,
                "warmup_start": illustrative - 365 * DAY,
            },
            "timing_conflict": "Last completed warmup bar closes at start; any commit after its close moves strict next-D1 start. A conditional tail is a possible independently reviewed operational clarification, not adopted here",
            "blockers": blockers,
            "historical_financial_authorized": False,
            "trade_entry_allowed": False,
        },
        "CONTROL_PLANE_GUARD_QA.json": {
            "new_facade": "All missing/invalid/forged/self-declared auth rejected before artifact/data reads; explicit no capability in this gate",
            "phase_header_dependency": False,
            "frozen_runner_replaced_or_patched": False,
            "underlying_direct_runner_hardened": False,
            "full_current_phase_suite_required": True,
            "full_suite_status": "UNRESOLVED_IMMUTABLE_FALSE_HEADER_ASSERTIONS",
            "test_byte_injection_skip_or_weakened_assertions": False,
            "immutable_test_paths": [
                "tests/test_machine_strategy_v3_readiness_conformance.py",
                "tests/test_machine_strategy_v3_outcome_guard.py",
                "tests/test_machine_strategy_v3_market_metadata_recovery.py",
            ],
            "governance_resolution_needed": "Separately authorize a new active runner/test version and preserve original frozen bytes; current gate cannot revise hash-pinned tests",
        },
        "FROZEN_INPUT_VERIFICATION.json": {
            "status": "PASS",
            "start_head": HEAD,
            "parents": parents,
            "strategy_adapter_runner_test_bytes_changed": False,
        },
        "STATIC_OUTCOME_ISOLATION.json": static_isolation(),
    }
    for name, value in result.items():
        save(output / name, value)
    return {name: digest(output / name) for name in OUTPUTS}


def seal():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_FREEZE_PRESERVED")
    qa = read(DEST / "QA_RECEIPT.json")
    if (
        qa["targeted_status"] != "PASS"
        or qa["full_current_phase_status"] != "FAIL"
        or qa["scope"] != "OBJECTIVE_STOP_WITH_IMMUTABLE_TEST_CONFLICT"
    ):
        raise ValueError("HONEST_STOP_QA_REQUIRED")
    if (
        "FINAL_REVIEW_PASS_FOR_PROSPECTIVE_STOP"
        not in (DEST / "reviews/final_independent_reviewer.md").read_text()
    ):
        raise ValueError("FINAL_INDEPENDENT_REVIEW_REQUIRED")
    for mapping in (qa["code_sha256"], qa["log_sha256"], qa["replay_sha256"]):
        for name, value in mapping.items():
            if digest(ROOT / name) != value:
                raise ValueError("POST_QA_BYTES_CHANGED")
    paths = [p for p in DEST.rglob("*") if p.is_file()]
    if any("__pycache__" in p.parts or p.suffix == ".pyc" for p in paths):
        raise ValueError("BUILD_CACHES_NOT_FREEZE_ARTIFACTS")
    artifacts = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    artifacts.update({p: digest(ROOT / p) for p in CODE})
    for name, h in PARENTS.items():
        verify_parent(ROOT / name, h)
        artifacts[name + "/freeze_manifest.json"] = h
        artifacts.update(read(ROOT / name / "freeze_manifest.json")["artifacts"])
    save(
        DEST / "freeze_manifest.json",
        {
            "stage": "MACHINE_STRATEGY_v3_PROSPECTIVE_READINESS",
            "decision": DECISION,
            "artifacts": dict(sorted(artifacts.items())),
            "QA_full_current_phase": "FAIL",
            "QA_targeted": "PASS",
            "registration_created": False,
            "candidate_state_or_outcomes_observed": False,
            "historical_financial_authorized": False,
            "trade_entry_allowed": False,
            "LIVE_enabled": False,
            "PAPER_enabled": False,
        },
    )
    return digest(DEST / "freeze_manifest.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--output", type=Path, default=DEST)
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    if args.prepare:
        result = prepare(args.output)
    elif args.freeze:
        result = seal()
    else:
        if not args.expected_manifest_sha256:
            raise ValueError("EXTERNALLY_PINNED_MANIFEST_REQUIRED")
        result = verify_parent(DEST, args.expected_manifest_sha256)
    print(
        json.dumps(
            {"status": "METADATA_INTEGRITY_ONLY", "result": result}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
