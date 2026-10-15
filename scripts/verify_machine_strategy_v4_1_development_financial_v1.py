"""Seal the exact first development outcome; never run or repair financial cases."""

from __future__ import annotations

import argparse
import json
import subprocess
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/machine_strategy_v4_1_development_financial_v1"
MANIFEST = OUT / "RESULT_FREEZE_MANIFEST.json"
PARENT = (
    ROOT
    / "docs/machine_strategy_v4_1_implementation_readiness_v1/IMPLEMENTATION_FREEZE_MANIFEST.json"
)
PARENT_SHA = "e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61"
PASS = "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_PASS"
STOP = "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP"
PRE_RUN_COMMIT = "1ae16d34cc0fe3260b041db9bc70c009db45203a"
PRE_RUN_TESTED = {
    "scripts/run_machine_strategy_v4_1_development_financial_v1.py",
    "scripts/audit_machine_strategy_v4_1_development_financial_v1.py",
    "tests/test_machine_strategy_v4_1_development_financial_runner.py",
}
AUDIT_CHECKS = {
    "closed_trades_min",
    "win_rate_min",
    "profit_factor_min",
    "expectancy_positive",
    "net_R_positive",
    "net_cash_positive",
    "doubled_profit_factor_min",
    "doubled_net_positive",
    "max_drawdown",
    "max_loss_streak",
    "wilson",
    "coin_direction_closed_min",
    "coin_direction_net_positive",
    "quarter_concentration",
    "coin_concentration",
    "filled_unknown_exit",
    "compatibility_agreement",
}
FILES = {
    f"{product}.{kind}.jsonl.gz"
    for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP")
    for kind in ("catalog", "cases")
} | {"FINANCIAL_RESULT.json", "RUN_RECEIPT.json"}
ROLES = (
    "BACKTEST_REVIEWER",
    "COST_FUNDING_AUDITOR",
    "STATISTICS_ROBUSTNESS_ANALYST",
    "OVERFIT_RED_TEAM",
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(test, reason):
    if not test:
        raise ValueError(reason)


def verify_pins(pins, root=None):
    root = ROOT if root is None else root
    require(bool(pins), "EMPTY_PINS")
    for name, expected in pins.items():
        path = (root / name).resolve()
        require(
            not Path(name).is_absolute() and path.is_relative_to(root.resolve()),
            "UNSAFE_PIN_PATH",
        )
        require(path.is_file() and digest(path) == expected, "PIN_CHANGED:" + name)


def read(name):
    return json.loads((OUT / name).read_text())


def checkpoint(expected):
    require(
        isinstance(expected, str) and len(expected) == 64,
        "EXTERNAL_CHECKPOINT_PIN_REQUIRED",
    )
    path = OUT / "RUN_CHECKPOINT.json"
    require(
        path.is_file() and digest(path) == expected, "EXTERNAL_CHECKPOINT_PIN_MISMATCH"
    )
    data = read("RUN_CHECKPOINT.json")
    require(data["historical_run_count"] == 1, "RUN_COUNT_DRIFT")
    require(set(data["artifacts_sha256"]) == FILES, "INCOMPLETE_CHECKPOINT")
    verify_pins(
        {
            str((OUT / name).relative_to(ROOT)): sha
            for name, sha in data["artifacts_sha256"].items()
        }
    )
    return data


def parent_pins():
    require(digest(PARENT) == PARENT_SHA, "EXTERNAL_IMPLEMENTATION_PIN_CHANGED")
    data = json.loads(PARENT.read_text())
    require(data["implementation_ready"] is True, "IMPLEMENTATION_NOT_READY")
    pins = {**data["artifact_sha256"], str(PARENT.relative_to(ROOT)): PARENT_SHA}
    verify_pins(pins)
    return pins


def decision_allowed(runner, auditor, final):
    require(final in (PASS, STOP), "UNKNOWN_DECISION")
    require(
        final != PASS or runner == auditor == PASS,
        "PASS_WITHOUT_CONCORDANT_QUALIFICATION",
    )


def committed_bytes(commit, name):
    return subprocess.check_output(["git", "show", commit + ":" + name], cwd=ROOT)


def pre_run_qa(qa):
    logs = {
        str((OUT / f"qa/pre_run_{index:02d}.log").relative_to(ROOT))
        for index in range(7)
    }
    require(
        qa["status"] == "PASS"
        and len(qa["commands"]) == 7
        and all(c["exit_code"] == 0 for c in qa["commands"])
        and {c["log"] for c in qa["commands"]} == logs
        and set(qa["tested_sha256"]) == PRE_RUN_TESTED
        and set(qa["log_sha256"]) == logs,
        "INCOMPLETE_PRE_RUN_QA",
    )
    require(
        qa["historical_financial_runs"] == 0
        and qa["historical_outcomes_viewed"] is False,
        "PRE_RUN_OUTCOME_CONTAMINATION",
    )
    pins = {**qa["tested_sha256"], **qa["log_sha256"]}
    receipt = str((OUT / "PRE_RUN_QA_RECEIPT.json").relative_to(ROOT))
    pins[receipt] = digest(OUT / "PRE_RUN_QA_RECEIPT.json")
    verify_pins(pins)
    for name in pins:
        require(
            (ROOT / name).read_bytes() == committed_bytes(PRE_RUN_COMMIT, name),
            "PRE_OUTCOME_QA_BYTES_CHANGED:" + name,
        )
    return pins


def review_receipt(review, role, sequence, anchors, previous):
    require(
        review["role"] == role
        and review["sequence"] == sequence
        and review["review_completed"] is True,
        "REVIEW_ROLE_SEQUENCE_INCOMPLETE:" + role,
    )
    require(review["previous_review_sha256"] == previous, "REVIEW_CHAIN_CHANGED")
    pins = review["reviewed_sha256"]
    require(
        all(pins.get(name) == sha for name, sha in anchors.items()),
        "INCOMPLETE_REVIEW_ANCHORS:" + role,
    )
    verify_pins(pins)


def audit_integrity(audit, runner):
    require(
        set(audit["checks"]) == AUDIT_CHECKS
        and all(type(value) is bool for value in audit["checks"].values()),
        "INCOMPLETE_AUDIT_CHECKS",
    )
    require(audit["runner_reported_decision"] == runner, "AUDIT_RUNNER_DRIFT")
    require(
        audit["decision"] == (PASS if all(audit["checks"].values()) else STOP),
        "AUDIT_DECISION_INCOHERENT",
    )


def final_decision(decision, review, checked, expected):
    final = review["decision"]
    decision_allowed(checked["runner_decision"], checked["auditor_decision"], final)
    require(
        decision["decision"] == final
        and decision["runner_decision"] == checked["runner_decision"]
        and decision["auditor_decision"] == checked["auditor_decision"]
        and decision["checkpoint_sha256"] == expected,
        "FINAL_DECISION_INCOHERENT",
    )
    if final == STOP:
        require(bool(decision["stop_reasons"]), "EXACT_STOP_REASONS_REQUIRED")
    else:
        require(not decision["stop_reasons"], "PASS_WITH_STOP_REASONS")
        require(not checked["critical_blockers"], "CRITICAL_REVIEW_BLOCKER")
    return final


def namespace_files():
    result = set()
    for path in OUT.rglob("*"):
        if path.is_file() and path != MANIFEST:
            require(
                "__pycache__" not in path.parts and path.suffix != ".pyc",
                "NAMESPACE_CACHE_FORBIDDEN",
            )
            result.add(str(path.relative_to(ROOT)))
    return result


def check(expected):
    parent_pins()
    saved = checkpoint(expected)
    qa_pins = pre_run_qa(read("PRE_RUN_QA_RECEIPT.json"))
    result = read("FINANCIAL_RESULT.json")
    audit = read("INDEPENDENT_FINANCIAL_AUDIT.json")
    require(
        result["trade_entry_allowed"] is False
        and result["PAPER"] is False
        and result["LIVE"] is False,
        "RESULT_SAFETY_DRIFT",
    )
    require(
        saved["decision"] == result["qualification"]["decision"],
        "CHECKPOINT_DECISION_CHANGED",
    )
    audit_integrity(audit, saved["decision"])
    publication = read("ONE_SHOT_RESULT_PUBLICATION.json")
    require(
        publication["checkpoint_sha256"] == expected
        and publication["historical_run_count"] == 1
        and publication["actual_runner_exit_code"] == 0,
        "FIRST_OUTCOME_PUBLICATION_DRIFT",
    )
    commit = publication["first_outcome_commit"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", PRE_RUN_COMMIT, commit],
        cwd=ROOT,
        check=True,
    )
    anchors = dict(qa_pins)
    for name in FILES | {"RUN_CHECKPOINT.json"}:
        relative = str((OUT / name).relative_to(ROOT))
        require(
            (OUT / name).read_bytes() == committed_bytes(commit, relative),
            "FIRST_OUTCOME_BYTES_CHANGED:" + name,
        )
        anchors[relative] = digest(OUT / name)
    for name in (
        "INDEPENDENT_FINANCIAL_AUDIT.json",
        "ONE_SHOT_RESULT_PUBLICATION.json",
    ):
        anchors[str((OUT / name).relative_to(ROOT))] = digest(OUT / name)
    critical_blockers = []
    previous = None
    for sequence, role in enumerate(ROLES, 1):
        review = read("reviews/" + role + ".json")
        review_receipt(review, role, sequence, anchors, previous)
        critical_blockers.extend(review.get("critical_blockers", []))
        path = OUT / "reviews" / (role + ".json")
        previous = digest(path)
        anchors[str(path.relative_to(ROOT))] = previous
    return {
        "runner_decision": saved["decision"],
        "auditor_decision": audit["decision"],
        "qualification_concordant": saved["decision"] == audit["decision"],
        "critical_blockers": critical_blockers,
        "historical_runs": 1,
        "trade_entry_allowed": False,
        "final_freeze_authority": False,
        "final_review_required_anchors": anchors,
        "previous_review_sha256": previous,
    }


def freeze(expected):
    require(not MANIFEST.exists(), "ALREADY_FROZEN_USE_EXTERNAL_RESUME")
    checked = check(expected)
    review = read("FINAL_REVIEW_RECEIPT.json")
    require(
        review["independent_final_acceptance"] is True,
        "SEPARATE_FINAL_ACCEPTANCE_REQUIRED",
    )
    anchors = checked["final_review_required_anchors"]
    decision_path = OUT / "FINAL_DECISION.json"
    anchors[str(decision_path.relative_to(ROOT))] = digest(decision_path)
    review_receipt(
        review,
        "FINAL_INDEPENDENT_REVIEWER",
        5,
        anchors,
        checked["previous_review_sha256"],
    )
    checked["critical_blockers"].extend(review.get("critical_blockers", []))
    final = final_decision(read("FINAL_DECISION.json"), review, checked, expected)
    pins = parent_pins()
    for name in namespace_files():
        pins[name] = digest(ROOT / name)
    for pattern in (
        "scripts/*machine_strategy_v4_1_development_financial*.py",
        "tests/*machine_strategy_v4_1_development_financial*.py",
        "agent_control/V4_1_DEVELOPMENT_FINANCIAL_WORK_ORDER.md",
        ".codex/config.toml",
        ".codex/agents/*.toml",
        "AGENTS.md",
        ".agents/skills/crypto-strategy-research/SKILL.md",
    ):
        for path in ROOT.glob(pattern):
            pins[str(path.relative_to(ROOT))] = digest(path)
    verify_pins(pins)
    data = {
        "gate": "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_V1",
        "decision": final,
        "historical_run_count": 1,
        "checkpoint_sha256": expected,
        "implementation_manifest_sha256": PARENT_SHA,
        "artifact_sha256": pins,
        "data_classification": "EXPOSED_DEVELOPMENT_NOT_PRISTINE_OOS",
        "production_candidate": None,
        "PAPER": False,
        "LIVE": False,
        "private_exchange_api_allowed": False,
        "trade_entry_allowed": False,
        "further_historical_financial_runs_authorized": False,
    }
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return {
        "decision": final,
        "manifest_sha256": digest(MANIFEST),
        "trade_entry_allowed": False,
        "further_historical_financial_runs_authorized": False,
    }


def resume(expected):
    require(
        isinstance(expected, str)
        and len(expected) == 64
        and digest(MANIFEST) == expected,
        "EXTERNAL_RESULT_MANIFEST_PIN_MISMATCH",
    )
    data = read("RESULT_FREEZE_MANIFEST.json")
    require(
        data["decision"] in (PASS, STOP) and data["historical_run_count"] == 1,
        "RESULT_SCOPE_DRIFT",
    )
    require(
        data["trade_entry_allowed"] is False
        and data["PAPER"] is False
        and data["LIVE"] is False
        and data["private_exchange_api_allowed"] is False
        and data["further_historical_financial_runs_authorized"] is False,
        "FROZEN_SAFETY_DRIFT",
    )
    verify_pins(data["artifact_sha256"])
    prefix = str(OUT.relative_to(ROOT)) + "/"
    require(
        {name for name in data["artifact_sha256"] if name.startswith(prefix)}
        == namespace_files(),
        "FROZEN_NAMESPACE_MEMBERSHIP_CHANGED",
    )
    require(
        read("FINAL_DECISION.json")["decision"] == data["decision"],
        "SEALED_DECISION_DRIFT",
    )
    return {
        "decision": data["decision"],
        "verified_resume": True,
        "historical_run_count": 1,
        "trade_entry_allowed": False,
        "further_historical_financial_runs_authorized": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-checkpoint-sha256")
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    print(
        json.dumps(
            resume(args.expected_manifest_sha256)
            if args.resume_existing
            else freeze(args.expected_checkpoint_sha256)
            if args.freeze
            else check(args.expected_checkpoint_sha256),
            sort_keys=True,
        )
    )
