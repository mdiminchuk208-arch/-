"""Nonfinancial preparation, QA, sealing and externally pinned READY verification."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from hashlib import sha256

from okx_qualification_data_v1 import ROOT, compact, save
from okx_v3_compatibility_binding_v1 import (
    DEST,
    POLICY_COMMIT,
    POLICY_RECEIPT_SHA,
    READY_DECISION,
    digest,
    read_policy,
)
from okx_v3_compatibility_runner_v1 import OUT, TOY_NAMES, run_registered_toy
from verify_okx_stage_a_v1 import resume as resume_stage_a

CODE = [
    "scripts/okx_v3_compatibility_binding_v1.py",
    "scripts/okx_v3_compatibility_runner_v1.py",
    "scripts/build_okx_v3_compatibility_v1.py",
    "tests/test_okx_v3_compatibility_v1.py",
]


def pins():
    return {name: digest(ROOT / name) for name in CODE}


def assert_pre_outcome():
    if OUT.exists():
        raise ValueError("HISTORICAL_OUTPUT_NAMESPACE_MUST_NOT_EXIST_BEFORE_READY")
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_READY_PRESERVED_USE_EXTERNAL_RESUME")


def parent():
    pre, _ = read_policy()
    result = resume_stage_a(pre["parent_stage_A"]["manifest_sha256"])
    path = ROOT / "docs/machine_strategy_v3_okx_qualification_v1/freeze_manifest.json"
    return result, path, json.loads(path.read_text())


def prepare():
    assert_pre_outcome()
    result, _, _ = parent()
    receipt_path = DEST / "POLICY_FREEZE_RECEIPT.json"
    committed = subprocess.check_output(
        ["git", "show", POLICY_COMMIT + ":" + str(receipt_path.relative_to(ROOT))],
        cwd=ROOT,
    )
    if sha256(committed).hexdigest() != POLICY_RECEIPT_SHA:
        raise ValueError("POLICY_WAS_NOT_COMMITTED_BEFORE_IMPLEMENTATION")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", POLICY_COMMIT, "HEAD"],
        cwd=ROOT,
        check=True,
    )
    controls = ["agent_control/CURRENT_BATCH.md", "agent_control/NEXT_TASK.md"]
    save(
        DEST / "AUTHORIZATION_SOURCE.json",
        {
            "control_sha256": {n: digest(ROOT / n) for n in controls},
            "implementation_sha256": pins(),
            "scope": "READY_ONLY_AUTHORIZES_ONE_SHOT_DEVELOPMENT_NOT_OOS_PAPER_LIVE",
            "trade_entry_allowed": False,
        },
    )
    replays = {}
    for name in TOY_NAMES:
        a, b = compact(run_registered_toy(name)), compact(run_registered_toy(name))
        if a != b:
            raise ValueError("REGISTERED_TOY_REPLAY_CHANGED")
        replays[name] = {"sha256": sha256(a.encode()).hexdigest(), "identical": True}
    save(
        DEST / "TOY_REPLAY_RECEIPT.json",
        {
            "registered_toy_only": True,
            "historical_financial_evaluations": 0,
            "fixtures": replays,
            "code_sha256": pins(),
        },
    )
    save(
        DEST / "SOURCE_INTEGRITY_RECEIPT.json",
        {
            "parent_stage_A": result,
            "policy_commit": POLICY_COMMIT,
            "policy_receipt_sha256": POLICY_RECEIPT_SHA,
            "sealed_source_reused_without_recollection": True,
            "protected_signal_files_unchanged": True,
            "historical_financial_evaluations": 0,
        },
    )
    return {"preparation": "PASS", "historical_financial_evaluations": 0}


def qa():
    assert_pre_outcome()
    before = pins()
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", name, "-v"]
        for name in (
            "test_okx_v3_compatibility_v1.py",
            "test_okx_qualification_data_v1.py",
            "test_okx_v3_input_bridge_v1.py",
            "test_verify_okx_stage_a_v1.py",
        )
    ]
    commands += [
        [str(sys.executable).rsplit("/", 1)[0] + "/ruff", "check", *CODE],
        [str(sys.executable).rsplit("/", 1)[0] + "/ruff", "format", "--check", *CODE],
        [
            str(sys.executable).rsplit("/", 1)[0] + "/mypy",
            "--follow-imports=silent",
            *CODE[:3],
        ],
        [sys.executable, "-m", "py_compile", *CODE],
    ]
    records = []
    for index, command in enumerate(commands):
        process = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False
        )
        log = DEST / f"qa/{index:02d}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(process.stdout + process.stderr)
        records.append(
            {
                "command": command,
                "exit_code": process.returncode,
                "log": str(log.relative_to(ROOT)),
                "log_sha256": digest(log),
            }
        )
    if before != pins():
        raise ValueError("IMPLEMENTATION_CHANGED_DURING_QA")
    status = "PASS" if all(r["exit_code"] == 0 for r in records) else "STOP"
    save(
        DEST / "QA_RECEIPT.json",
        {
            "status": status,
            "commands": records,
            "code_sha256": before,
            "historical_financial_evaluations": 0,
            "registered_toy_only": True,
        },
    )
    (DEST / "QA_REPORT.md").write_text(
        f"# Compatibility v1 QA\n\nStatus: {status}. Exact commands, exit codes, byte pins and logs are in QA_RECEIPT.json. "
        "Only registered synthetic toy outcomes and synthetic nonfinancial causal prefixes were evaluated. "
        "The three sealed Stage-A suites exercise source continuity, official evidence identity, normalization, "
        "and immutable namespace verification; source collection and historical financial evaluation were not run. "
        "This is targeted QA, not a claim that every legacy repository test passes.\n"
    )
    if status != "PASS":
        raise ValueError("QA_FAILED_READ_RETAINED_LOGS")
    return {"QA": status, "commands": len(records)}


def freeze_ready():
    assert_pre_outcome()
    _, parent_path, parent_manifest = parent()
    qa_receipt = json.loads((DEST / "QA_RECEIPT.json").read_text())
    toy = json.loads((DEST / "TOY_REPLAY_RECEIPT.json").read_text())
    if (
        qa_receipt["status"] != "PASS"
        or qa_receipt["code_sha256"] != pins()
        or toy["code_sha256"] != pins()
    ):
        raise ValueError("PRE_OUTCOME_QA_BYTES_REQUIRED")
    for r in qa_receipt["commands"]:
        if digest(ROOT / r["log"]) != r["log_sha256"]:
            raise ValueError("QA_LOG_CHANGED")
    for name, expected_marker in (
        ("CAUSALITY_REVIEW.json", "CAUSALITY_REVIEW_PASS"),
        ("FINAL_REVIEW.json", "FINAL_COMPATIBILITY_READY_REVIEW_PASS"),
    ):
        review = json.loads((DEST / name).read_text())
        if review["decision"] != expected_marker or review["code_sha256"] != pins():
            raise ValueError("INDEPENDENT_REVIEW_OF_EXACT_CODE_REQUIRED")
    authority = json.loads((DEST / "AUTHORIZATION_SOURCE.json").read_text())
    if any(digest(ROOT / n) != h for n, h in authority["control_sha256"].items()):
        raise ValueError("AUTONOMOUS_AUTHORIZATION_CHANGED")
    paths = [p for p in DEST.rglob("*") if p.is_file()]
    if any("__pycache__" in p.parts or p.suffix in (".pyc", ".tmp") for p in paths):
        raise ValueError("NAMESPACE_CACHE_OR_TEMP_FORBIDDEN")
    artifacts = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    artifacts.update(pins())
    artifacts[str(parent_path.relative_to(ROOT))] = digest(parent_path)
    artifacts.update(parent_manifest["artifacts"])
    save(
        DEST / "freeze_manifest.json",
        {
            "version": "MACHINE_STRATEGY_v3_OKX_COMPATIBILITY_v1",
            "decision": READY_DECISION,
            "artifacts": artifacts,
            "policy_commit": POLICY_COMMIT,
            "historical_financial_evaluations_before_freeze": 0,
            "authorization": "ONE_SHOT_DEVELOPMENT_ONLY_NOT_OOS",
            "PAPER": False,
            "LIVE": False,
            "trade_entry_allowed": False,
        },
    )
    return {
        "decision": READY_DECISION,
        "manifest_sha256": digest(DEST / "freeze_manifest.json"),
    }


def resume(expected):
    path = DEST / "freeze_manifest.json"
    if not expected or digest(path) != expected:
        raise ValueError("EXTERNALLY_PINNED_READY_MANIFEST_REQUIRED")
    manifest = json.loads(path.read_text())
    names = {
        str(p.relative_to(ROOT)) for p in DEST.rglob("*") if p.is_file() and p != path
    }
    if names != {
        n
        for n in manifest["artifacts"]
        if n.startswith(str(DEST.relative_to(ROOT)) + "/")
    }:
        raise ValueError("FROZEN_NAMESPACE_MEMBERSHIP_CHANGED")
    for n, h in manifest["artifacts"].items():
        if digest(ROOT / n) != h:
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
    return {
        "decision": manifest["decision"],
        "manifest_sha256": expected,
        "verified_resume": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    for name in ("prepare", "qa", "freeze-ready", "resume-existing"):
        action.add_argument("--" + name, action="store_true")
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    value = (
        prepare()
        if args.prepare
        else qa()
        if args.qa
        else freeze_ready()
        if args.freeze_ready
        else resume(args.expected_manifest_sha256)
    )
    print(json.dumps(value, sort_keys=True))
