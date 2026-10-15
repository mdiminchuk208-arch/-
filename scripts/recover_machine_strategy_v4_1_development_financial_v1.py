"""Bounded, immutable recovery of the SIGKILL pre-output attempt; no rule changes."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from hashlib import sha256

import run_machine_strategy_v4_1_development_financial_v1 as original
from verify_machine_strategy_v4_1_development_financial_v1 import (
    parent_pins,
    require,
    verify_pins,
)

ROOT = original.ROOT
OUT = original.OUT
STAGE = OUT / "recovery"
STATE = STAGE / "STATE.json"
FAILURE_COMMIT = "682235766e08d8efeacab7f4ea7170d6b83cd2dd"
ORIGINAL_SOURCES = {
    "scripts/run_machine_strategy_v4_1_development_financial_v1.py",
    "scripts/audit_machine_strategy_v4_1_development_financial_v1.py",
    "tests/test_machine_strategy_v4_1_development_financial_runner.py",
}
RECOVERY_SOURCES = {
    "scripts/recover_machine_strategy_v4_1_development_financial_v1.py",
    "tests/test_machine_strategy_v4_1_development_financial_recovery.py",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def published(path):
    original._verify_committed_file(path, "HEAD")
    original._verify_committed_file(path, "origin/machine-v3-research")


def load(path):
    return json.loads(path.read_text())


def exclusive_json(path, value):
    with path.open("x") as handle:
        handle.write(
            json.dumps(original._jsonable(value), sort_keys=True, indent=2) + "\n"
        )


def atomic_state(value):
    temp = STATE.with_suffix(".tmp")
    exclusive_json(temp, value)
    temp.replace(STATE)


def code_pins():
    # The original three files are also compared byte-for-byte to the original QA commit.
    pins = {name: digest(ROOT / name) for name in ORIGINAL_SOURCES | RECOVERY_SOURCES}
    for name in ORIGINAL_SOURCES:
        original._verify_committed_file(
            ROOT / name, "1ae16d34cc0fe3260b041db9bc70c009db45203a"
        )
    return pins


def authorize():
    parent_pins()
    for commit in (
        original.IMPLEMENTATION_FREEZE_COMMIT,
        original.PREREG_COMMIT,
        original.AUTH_COMMIT,
        FAILURE_COMMIT,
    ):
        original._assert_ancestor(commit)
    for path, commit in (
        (original.PREREG, original.PREREG_COMMIT),
        (original.AUTH, original.AUTH_COMMIT),
        (OUT / "FAILED_ATTEMPT_1.json", FAILURE_COMMIT),
        (OUT / "RUN_STARTED.json", FAILURE_COMMIT),
    ):
        original._verify_committed_file(path, commit)
    failed = load(OUT / "FAILED_ATTEMPT_1.json")
    require(
        failed["signal"] == 9
        and failed["historical_financial_evaluations_completed"] == 0
        and failed["case_level_financial_outputs_exposed"] is False
        and not any(failed["required_output_presence"].values()),
        "RECOVERY_NOT_PRE_OUTPUT",
    )
    require(
        digest(OUT / "RUN_STARTED.json") == failed["run_started_sha256"]
        and digest(OUT / "qa/one_shot_attempt1_sigkill.log") == failed["log_sha256"],
        "FAILED_ATTEMPT_EVIDENCE_CHANGED",
    )
    started = load(OUT / "RUN_STARTED.json")
    require(
        started["runner_sha256"]
        == digest(
            ROOT / "scripts/run_machine_strategy_v4_1_development_financial_v1.py"
        )
        and started["preregistration_sha256"] == digest(original.PREREG)
        and started["authorization_sha256"] == digest(original.AUTH),
        "RESERVATION_PIN_DRIFT",
    )
    prereg, auth = load(original.PREREG), load(original.AUTH)
    require(
        prereg["gate"] == auth["gate"] == original.GATE
        and auth["historical_runs_remaining"] == 1
        and auth["authorization_state"]
        == "ONE_SHOT_HISTORICAL_DEVELOPMENT_FINANCIAL_RUN_AUTHORIZED",
        "WRONG_RECOVERY_GATE",
    )
    batch = (ROOT / "agent_control/CURRENT_BATCH.md").read_text()
    require(
        "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_OPEN" in batch,
        "RECOVERY_GATE_NOT_ACTIVE",
    )
    qa_path, review_path = (
        OUT / "RECOVERY_PRE_RUN_QA.json",
        OUT / "RECOVERY_PRE_RUN_REVIEW.json",
    )
    qa, review = load(qa_path), load(review_path)
    pins = code_pins()
    require(
        qa["status"] == "PASS"
        and qa["tested_sha256"] == pins
        and len(qa["commands"]) >= 5
        and all(command["exit_code"] == 0 for command in qa["commands"]),
        "RECOVERY_QA_INCOMPLETE",
    )
    verify_pins(qa["log_sha256"])
    require(
        review["independent_execution_acceptance"] is True
        and not review["critical_blockers"]
        and all(
            review["reviewed_sha256"].get(name) == sha
            for name, sha in {**pins, rel(qa_path): digest(qa_path)}.items()
        ),
        "RECOVERY_REVIEW_INCOMPLETE",
    )
    verify_pins(review["reviewed_sha256"])
    for path in (qa_path, review_path, *[ROOT / name for name in pins]):
        published(path)
    return prereg


def groups_for(catalogs):
    groups = []
    for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP"):
        buckets = defaultdict(list)
        for order in catalogs[product]:
            buckets[order["decision_at"]].append(order["case_id"])
        for decision, case_ids in sorted(buckets.items()):
            groups.append(
                {
                    "index": len(groups),
                    "product": product,
                    "decision_at": decision,
                    "case_ids": sorted(case_ids),
                }
            )
    return groups


def state_load(expected, require_published=True):
    require(
        isinstance(expected, str) and len(expected) == 64 and digest(STATE) == expected,
        "EXTERNAL_RECOVERY_STATE_PIN_MISMATCH",
    )
    state = load(STATE)
    require(
        state["gate"] == original.GATE
        and state["completed_financial_evaluations"] in (0, 1)
        and state["trade_entry_allowed"] is False,
        "RECOVERY_STATE_SCOPE_DRIFT",
    )
    require(state["code_sha256"] == code_pins(), "RECOVERY_CODE_CHANGED_AFTER_OUTPUT")
    verify_pins(state["artifacts_sha256"])
    if require_published:
        published(STATE)
        for name in state["artifacts_sha256"]:
            published(ROOT / name)
    return state


def catalogs_from(state):
    catalogs = {
        product: [
            json.loads(line)
            for line in gzip.decompress(
                (STAGE / f"{product}.catalog.jsonl.gz").read_bytes()
            ).splitlines()
        ]
        for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP")
    }
    require(groups_for(catalogs) == state["groups"], "GROUP_PARTITION_DRIFT")
    return catalogs


@original._precision(50)
def initialize():
    prereg = authorize()
    require(not STATE.exists() and not STAGE.exists(), "RECOVERY_ALREADY_INITIALIZED")
    require(
        not any((OUT / name).exists() for name in original.FINAL_FILES),
        "FINAL_OUTPUT_ALREADY_EXISTS",
    )
    STAGE.mkdir()
    exclusive_json(
        STAGE / "INITIALIZATION_STARTED.json",
        {"code_sha256": code_pins(), "trade_entry_allowed": False},
    )
    catalogs, audits = {}, {}
    start, end = (
        original._epoch(prereg["development_window"]["start_utc"]),
        original._epoch(prereg["development_window"]["end_exclusive_utc"]),
    )
    source_receipt = load(
        original.IMPLEMENTATION_MANIFEST.parent / "SOURCE_PREFIX_REPLAY_RECEIPT.json"
    )
    for product in prereg["products"]:
        market = original.market_inputs(product)
        orders, audit = original.V41HistoricalAdapter(
            product, market, start, end
        ).catalog()
        frozen = json.loads(
            gzip.decompress(
                (
                    ROOT / source_receipt["products"][product]["source_artifact"]
                ).read_bytes()
            )
        )["preentry_model_catalog"]
        require(
            original._compact(orders) == original._compact(frozen)
            and audit["historical_position_engine_calls"] == 0
            and not audit["financial_outcomes_generated"],
            "FROZEN_CATALOG_DRIFT",
        )
        original._write_gzip_jsonl(STAGE / f"{product}.catalog.jsonl.gz", orders)
        catalogs[product] = orders
        audits[product] = {
            "candidate_count": len(orders),
            "raw_origin_count": len(audit["raw_origins"]),
            "source_digest": sha256(
                original._compact({"orders": orders, "audit": audit})
            ).hexdigest(),
        }
        del market, frozen, audit
        print("RECOVERY_SOURCE_COMPLETE", product, flush=True)
    exclusive_json(STAGE / "CATALOG_AUDIT.json", audits)
    state = {
        "gate": original.GATE,
        "groups": groups_for(catalogs),
        "next_group": 0,
        "completed_financial_evaluations": 0,
        "code_sha256": code_pins(),
        "artifacts_sha256": {rel(p): digest(p) for p in STAGE.iterdir() if p.is_file()},
        "trade_entry_allowed": False,
    }
    atomic_state(state)
    return {
        "state_sha256": digest(STATE),
        "groups": len(state["groups"]),
        "financial_outputs_emitted": False,
    }


def validate_group(group, cases):
    require(
        [case["case_id"] for case in cases] == group["case_ids"],
        "GROUP_CASE_PARTITION_DRIFT",
    )
    require(
        all(
            case["product"] == group["product"]
            and case["decision_at"] == group["decision_at"]
            and case["trade_entry_allowed"] is False
            for case in cases
        ),
        "GROUP_CASE_IDENTITY_DRIFT",
    )
    expected = [grid["id"] for grid in original.scenarios(group["product"])]
    require(
        all(
            [state["scenario_id"] for state in case["all_scenarios"]] == expected
            for case in cases
        ),
        "GROUP_ALL_NINE_COVERAGE_DRIFT",
    )


@original._precision(50)
def next_group(expected):
    prereg = authorize()
    state = state_load(expected)
    require(
        not any((OUT / name).exists() for name in original.FINAL_FILES),
        "FINAL_OUTPUT_ALREADY_EXISTS",
    )
    require(
        state["completed_financial_evaluations"] == 0
        and state["next_group"] < len(state["groups"]),
        "NO_UNFINISHED_GROUP",
    )
    catalogs = catalogs_from(state)
    group = state["groups"][state["next_group"]]
    index, product = group["index"], group["product"]
    shard = STAGE / f"group_{index:03d}.jsonl.gz"
    marker = STAGE / f"group_{index:03d}.started.json"
    require(not shard.exists(), "EXISTING_SHARD_NO_REEXECUTION")
    exclusive_json(
        marker,
        {
            "input_state_sha256": expected,
            "group": group,
            "code_sha256": state["code_sha256"],
            "trade_entry_allowed": False,
        },
    )
    market = original.market_inputs(product)
    funding = original._funding_inputs(product, market[15])
    selected = sorted(
        [row for row in catalogs[product] if row["case_id"] in group["case_ids"]],
        key=lambda row: row["case_id"],
    )
    states = original._drive_decision_group(
        product,
        market,
        funding,
        selected,
        original._epoch(prereg["development_window"]["start_utc"]),
        original._epoch(prereg["development_window"]["end_exclusive_utc"]),
    )
    cases = [
        original._adverse_case(order, states[order["case_id"]]) for order in selected
    ]
    validate_group(group, cases)
    # Exclusive create: a durable group can never be replaced by another execution.
    with shard.open("xb") as handle:
        handle.write(
            gzip.compress(
                b"\n".join(original._compact(case) for case in cases) + b"\n", mtime=0
            )
        )
    receipt = STAGE / f"group_{index:03d}.receipt.json"
    exclusive_json(
        receipt,
        {
            "group": group,
            "shard_sha256": digest(shard),
            "input_state_sha256": expected,
            "code_sha256": state["code_sha256"],
            "trade_entry_allowed": False,
        },
    )
    for path in (marker, shard, receipt):
        state["artifacts_sha256"][rel(path)] = digest(path)
    state["next_group"] += 1
    atomic_state(state)
    return {
        "completed_group": index,
        "groups_complete": state["next_group"],
        "shard_sha256": digest(shard),
        "state_sha256": digest(STATE),
        "financial_values_printed": False,
    }


def collect_cases(state, catalogs):
    require(state["next_group"] == len(state["groups"]), "INCOMPLETE_GROUP_COVERAGE")
    seen = {}
    for group in state["groups"]:
        path = STAGE / f"group_{group['index']:03d}.jsonl.gz"
        cases = [
            json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()
        ]
        validate_group(group, cases)
        receipt = load(STAGE / f"group_{group['index']:03d}.receipt.json")
        require(
            receipt["group"] == group
            and receipt["shard_sha256"] == digest(path)
            and receipt["code_sha256"] == state["code_sha256"],
            "SHARD_RECEIPT_DRIFT",
        )
        for case in cases:
            require(case["case_id"] not in seen, "DUPLICATE_CASE_IN_RECOVERY")
            seen[case["case_id"]] = case
    expected = [order["case_id"] for rows in catalogs.values() for order in rows]
    require(
        len(expected) == len(set(expected)) and set(seen) == set(expected),
        "CATALOG_CASE_SET_DRIFT",
    )
    return {
        product: [seen[order["case_id"]] for order in orders]
        for product, orders in catalogs.items()
    }


@original._precision(50)
def finalize(expected):
    prereg = authorize()
    state = state_load(expected)
    require(
        not any((OUT / name).exists() for name in original.FINAL_FILES),
        "FINAL_OUTPUT_ALREADY_EXISTS",
    )
    require(
        state["completed_financial_evaluations"] == 0, "EVALUATION_ALREADY_COMPLETED"
    )
    catalogs = catalogs_from(state)
    cases_by_product = collect_cases(state, catalogs)
    all_cases = [
        case for product in prereg["products"] for case in cases_by_product[product]
    ]
    qualification = original._qualification(all_cases, prereg)
    result = original._jsonable(
        {
            "gate": original.GATE,
            "strategy_version": original.VERSION,
            "venue": "OKX",
            "development_window": prereg["development_window"],
            "candidate_count": sum(len(rows) for rows in catalogs.values()),
            "candidate_count_by_product": {k: len(v) for k, v in catalogs.items()},
            "case_status_counts": {
                status: sum(row["status"] == status for row in all_cases)
                for status in sorted({row["status"] for row in all_cases})
            },
            "qualification": qualification,
            "model_limitations": [
                "historical tick/lot epochs unverified; nine synthetic compatibility grids are modeled stress",
                "historical ordinary account-applicable OKX fee is unverified; frozen model costs used",
                "mark/queue/fill reality and API publication delay are unverified",
                "development history is exposed and is not pristine OOS",
            ],
            "trade_entry_allowed": False,
            "PAPER": False,
            "LIVE": False,
        }
    )
    for product in prereg["products"]:
        original._write_gzip_jsonl(
            OUT / f"{product}.catalog.jsonl.gz", catalogs[product]
        )
        original._write_gzip_jsonl(
            OUT / f"{product}.cases.jsonl.gz", cases_by_product[product]
        )
    exclusive_json(OUT / "FINANCIAL_RESULT.json", result)
    exclusive_json(
        OUT / "RUN_RECEIPT.json",
        {
            "gate": original.GATE,
            "implementation_manifest_sha256": original.IMPLEMENTATION_MANIFEST_SHA256,
            "implementation_freeze_commit": original.IMPLEMENTATION_FREEZE_COMMIT,
            "preregistration_commit": original.PREREG_COMMIT,
            "authorization_commit": original.AUTH_COMMIT,
            "catalog_audit": load(STAGE / "CATALOG_AUDIT.json"),
            "historical_run_count": 1,
            "historical_execution_attempts": 2,
            "attempt1": "FAILED_SIGKILL_BEFORE_EMITTED_OUTCOMES",
            "recovery": "UNCHANGED_PRIMITIVES_PUBLISHED_IMMUTABLE_GROUPS",
            "financial_result_decision": result["qualification"]["decision"],
            "trade_entry_allowed": False,
        },
    )
    exclusive_json(
        OUT / "RUN_CHECKPOINT.json",
        {
            "gate": original.GATE,
            "state": "ONE_SHOT_RESULT_COMMITTED_TO_FILESYSTEM",
            "artifacts_sha256": {
                name: digest(OUT / name)
                for name in original.FINAL_FILES
                if name != "RUN_CHECKPOINT.json"
            },
            "decision": result["qualification"]["decision"],
            "historical_run_count": 1,
        },
    )
    for name in original.FINAL_FILES:
        state["artifacts_sha256"][rel(OUT / name)] = digest(OUT / name)
    state["completed_financial_evaluations"] = 1
    atomic_state(state)
    return {
        "checkpoint_sha256": digest(OUT / "RUN_CHECKPOINT.json"),
        "state_sha256": digest(STATE),
        "completed_financial_evaluations": 1,
        "financial_values_printed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--next-group", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    mode.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-state-sha256")
    args = parser.parse_args()
    if args.initialize:
        response = initialize()
    elif args.next_group:
        response = next_group(args.expected_state_sha256)
    elif args.finalize:
        response = finalize(args.expected_state_sha256)
    else:
        authorize()
        saved = state_load(args.expected_state_sha256)
        response = {
            "verified_resume": True,
            "state_sha256": digest(STATE),
            "groups_complete": saved["next_group"],
            "completed_financial_evaluations": saved["completed_financial_evaluations"],
            "historical_engine_calls": 0,
        }
    print(json.dumps(response, sort_keys=True))
