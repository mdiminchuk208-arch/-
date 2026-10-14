"""Seal/verify an implementation STOP checkpoint; never creates READY authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_implementation_readiness_v1"
MANIFEST = DEST / "IMPLEMENTATION_FREEZE_MANIFEST.json"
DECISION = "MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP"
DESIGN_SHA = "b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(pins):
    for name, expected in pins.items():
        path = (ROOT / name).resolve()
        if (
            not path.is_relative_to(ROOT)
            or not path.is_file()
            or digest(path) != expected
        ):
            raise ValueError("CHECKPOINT_INPUT_CHANGED:" + name)


def freeze_stop():
    if MANIFEST.exists():
        raise ValueError("CHECKPOINT_ALREADY_FROZEN_USE_EXTERNAL_PIN")
    design_path = (
        ROOT / "docs/machine_strategy_v4_design_v1/DESIGN_FREEZE_MANIFEST.json"
    )
    if digest(design_path) != DESIGN_SHA:
        raise ValueError("FROZEN_DESIGN_CHANGED")
    review = json.loads((DEST / "INDEPENDENT_REVIEW_RECEIPT.json").read_text())
    if review["decision"] != DECISION:
        raise ValueError("INDEPENDENT_STOP_ACCEPTANCE_REQUIRED")
    verify(review["reviewed_sha256"])
    qa = json.loads((DEST / "QA_RECEIPT.json").read_text())
    if qa["component_QA_status"] != "PASS" or qa["implementation_ready"] is not False:
        raise ValueError("INCOMPLETE_OR_MISSTATED_QA")
    verify(qa["tested_sha256"])
    verify(qa["log_sha256"])
    design = json.loads(design_path.read_text())
    pins = dict(design["artifact_sha256"])
    pins[str(design_path.relative_to(ROOT))] = DESIGN_SHA
    for parent in [
        "docs/machine_strategy_v3_okx_failure_audit_v1/freeze_manifest.json",
        "docs/machine_strategy_v3_okx_qualification_v1/freeze_manifest.json",
    ]:
        path = ROOT / parent
        data = json.loads(path.read_text())
        pins[parent] = digest(path)
        pins.update(data.get("artifacts", {}))
    for path in sorted(DEST.rglob("*")):
        if path.is_file() and path != MANIFEST:
            pins[str(path.relative_to(ROOT))] = digest(path)
    for pattern in [
        "scripts/machine_strategy_v4_*.py",
        "scripts/check_machine_strategy_v4_source_prefix.py",
        "scripts/verify_machine_strategy_v4_implementation_v1.py",
        "tests/test_machine_strategy_v4_*.py",
        "AGENTS.md",
        ".codex/config.toml",
        ".codex/agents/backtest-engineer.toml",
        ".codex/agents/historical-data-engineer.toml",
        ".codex/agents/execution-auditor.toml",
        ".codex/agents/no-lookahead-auditor.toml",
        ".codex/agents/final-independent-reviewer.toml",
        ".agents/skills/crypto-strategy-research/SKILL.md",
        "agent_control/V4_IMPLEMENTATION_READINESS_WORK_ORDER.md",
    ]:
        for path in ROOT.glob(pattern):
            pins[str(path.relative_to(ROOT))] = digest(path)
    verify(pins)
    manifest = {
        "decision": DECISION,
        "version": "MACHINE_STRATEGY_v4",
        "checkpoint_only": True,
        "complete_implementation_freeze": False,
        "implementation_ready": False,
        "blocked_on": "selected-POI first-test origin/eligibility requires a separate v4.1 design",
        "artifact_sha256": pins,
        "historical_financial_authorized": False,
        "historical_position_evaluations": 0,
        "PAPER": False,
        "LIVE": False,
        "trade_entry_allowed": False,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {
        "decision": DECISION,
        "checkpoint_manifest_sha256": digest(MANIFEST),
        "complete_implementation_freeze": False,
    }


def resume(expected):
    if len(expected) != 64 or digest(MANIFEST) != expected:
        raise ValueError("EXTERNAL_CHECKPOINT_PIN_MISMATCH")
    manifest = json.loads(MANIFEST.read_text())
    if (
        manifest["decision"] != DECISION
        or manifest["complete_implementation_freeze"] is not False
        or manifest["historical_financial_authorized"] is not False
    ):
        raise ValueError("CHECKPOINT_IS_NOT_STOP_AUTHORITY")
    verify(manifest["artifact_sha256"])
    return {
        "decision": DECISION,
        "verified_resume": True,
        "historical_position_evaluations": 0,
        "implementation_ready": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze-stop", action="store_true")
    g.add_argument("--resume-existing", action="store_true")
    p.add_argument("--expected-manifest-sha256")
    args = p.parse_args()
    if args.resume_existing and not args.expected_manifest_sha256:
        p.error("external checkpoint SHA required")
    print(
        json.dumps(
            resume(args.expected_manifest_sha256)
            if args.resume_existing
            else freeze_stop(),
            sort_keys=True,
        )
    )
