"""Exact READY/STOP implementation sealing; never grants financial execution."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_1_implementation_readiness_v1"
MANIFEST = DEST / "IMPLEMENTATION_FREEZE_MANIFEST.json"
DESIGN_SHA = "4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790"
DESIGN = ROOT / "docs/machine_strategy_v4_1_design_v1/DESIGN_FREEZE_MANIFEST.json"
READY = "MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY"
STOP = "MACHINE_STRATEGY_V4_1_IMPLEMENTATION_STOP"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify_pins(pins, root=ROOT):
    require(bool(pins), "EMPTY_PINS")
    for name, expected in pins.items():
        path = (root / name).resolve()
        require(
            not Path(name).is_absolute() and path.is_relative_to(root.resolve()),
            "UNSAFE_PIN_PATH",
        )
        require(path.is_file() and digest(path) == expected, "PIN_CHANGED:" + name)


def read(name):
    return json.loads((DEST / name).read_text())


def parent_pins():
    require(digest(DESIGN) == DESIGN_SHA, "EXTERNAL_DESIGN_PIN_MISMATCH")
    parent = json.loads(DESIGN.read_text())
    pins = dict(parent["artifact_sha256"])
    pins[str(DESIGN.relative_to(ROOT))] = DESIGN_SHA
    verify_pins(pins)
    return pins


def check_source(receipt):
    require(receipt["source_only_causality"] == "PASS", "SOURCE_NOT_PASS")
    require(
        receipt["historical_position_evaluations"] == 0
        and receipt["historical_financial_authorized"] is False
        and receipt["trade_entry_allowed"] is False,
        "SOURCE_SCOPE_DRIFT",
    )
    require(
        set(receipt["products"]) == {"BTC-USDT-SWAP", "ETH-USDT-SWAP"},
        "SOURCE_PRODUCT_GAP",
    )
    verify_pins(receipt["run_context"]["source_code_sha256"])
    require(
        receipt["run_context"]["design_manifest_sha256"] == DESIGN_SHA,
        "SOURCE_DESIGN_DRIFT",
    )
    require(
        receipt["run_context"]["preregistration_sha256"]
        == digest(DEST / "SOURCE_REPLAY_PREREGISTRATION.json"),
        "SOURCE_PREREG_DRIFT",
    )
    for product, result in receipt["products"].items():
        require(result["native_bar_count"] == 105120, "SOURCE_NOT_FULL_GRID:" + product)
        require(
            result["full_deterministic_replay"] == "PASS"
            and result["position_engine_trap_active"] is True,
            "FULL_REPLAY_OR_ENGINE_TRAP_MISSING",
        )
        verify_pins({result["source_artifact"]: result["source_artifact_sha256"]})
        require(
            set(result["cutoffs"]) == set(map(str, receipt["cutoffs_UTC_seconds"]))
            and len(result["cutoffs"]) == 3,
            "SOURCE_CHECKPOINT_GAP",
        )
        for cutoff, comparison in result["cutoffs"].items():
            require(
                comparison["deterministic_source_replay"] == "PASS"
                and len(
                    {
                        comparison["full_stream"],
                        comparison["truncated"],
                        comparison["future_mutated"],
                        result["full_checkpoint_digests"][cutoff],
                    }
                )
                == 1,
                "PREFIX_MUTATION_MISMATCH",
            )


def check():
    parent_pins()
    inputs = read("IMPLEMENTATION_INPUTS.json")
    verify_pins(inputs["input_sha256"])
    qa = read("QA_RECEIPT.json")
    require(
        qa["component_QA_status"] == "PASS"
        and qa["commands"]
        and all(c["exit_code"] == 0 for c in qa["commands"]),
        "QA_NOT_PASS",
    )
    verify_pins(qa["tested_sha256"])
    verify_pins(qa["log_sha256"])
    require(
        qa["historical_position_evaluations"] == 0
        and qa["historical_financial_authorized"] is False
        and qa["trade_entry_allowed"] is False,
        "QA_SCOPE_DRIFT",
    )
    check_source(read("SOURCE_PREFIX_REPLAY_RECEIPT.json"))
    require(
        read("DATA_GRID_AUTHENTICITY_AND_CONTINUITY.json")["data_decision"] == "PASS",
        "DATA_NOT_PASS",
    )
    source_fields = read("FULL_SOURCE_CONFORMANCE_RECEIPT.json")
    require(
        len(source_fields["products"]) == 2
        and all(
            row["all_raw_and_inventory_and_proposal_fields_validated"] is True
            for row in source_fields["products"].values()
        ),
        "FULL_SOURCE_FIELD_PROVENANCE_INCOMPLETE",
    )
    conformance = read("RULE_TO_CODE_CONFORMANCE.json")
    require(
        conformance["complete_rule_coverage"] is True
        and conformance["frozen_rules_changed"] is False,
        "RULE_CONFORMANCE_INCOMPLETE",
    )
    for name in ("EXECUTION_AUDITOR.json", "NO_LOOKAHEAD_AUDITOR.json"):
        review = read("reviews/" + name)
        require(
            review["verdict"] == "PASS" and review["blockers"] == [],
            "INDEPENDENT_REVIEW_NOT_PASS:" + name,
        )
        verify_pins(review["reviewed_sha256"])
    return {
        "component_and_source_QA": "PASS",
        "final_freeze_authority": False,
        "historical_financial_authorized": False,
        "trade_entry_allowed": False,
    }


def freeze(decision):
    require(not MANIFEST.exists(), "ALREADY_FROZEN_USE_EXTERNAL_PIN")
    pins = parent_pins()
    review = read("INDEPENDENT_REVIEW_RECEIPT.json")
    require(
        review["decision"] == decision
        and review["independent_final_acceptance"] is True,
        "FINAL_INDEPENDENT_ACCEPTANCE_REQUIRED",
    )
    verify_pins(review["reviewed_sha256"])
    if decision == READY:
        check()
    elif decision == STOP:
        require(
            bool(read("STOP_BLOCKERS.json")["blockers"]), "EXACT_STOP_BLOCKERS_REQUIRED"
        )
    else:
        raise ValueError("UNKNOWN_DECISION")
    for path in sorted(DEST.rglob("*")):
        if path.is_file() and path != MANIFEST:
            require(
                "__pycache__" not in path.parts and path.suffix != ".pyc",
                "NAMESPACE_CACHE_FORBIDDEN",
            )
            pins[str(path.relative_to(ROOT))] = digest(path)
    for pattern in (
        "scripts/machine_strategy_v4_1_*.py",
        "scripts/check_machine_strategy_v4_1_*.py",
        "scripts/verify_machine_strategy_v4_1_*.py",
        "tests/test_machine_strategy_v4_1*.py",
        "AGENTS.md",
        ".codex/config.toml",
        ".codex/agents/*.toml",
        ".agents/skills/crypto-strategy-research/SKILL.md",
        "agent_control/V4_1_IMPLEMENTATION_READINESS_WORK_ORDER.md",
    ):
        for path in ROOT.glob(pattern):
            pins[str(path.relative_to(ROOT))] = digest(path)
    verify_pins(pins)
    manifest = {
        "decision": decision,
        "version": "MACHINE_STRATEGY_v4.1",
        "complete_implementation_freeze": decision == READY,
        "implementation_ready": decision == READY,
        "checkpoint_only": decision == STOP,
        "artifact_sha256": pins,
        "historical_financial_authorized": False,
        "historical_position_evaluations": 0,
        "production_candidate": None,
        "PAPER": False,
        "LIVE": False,
        "trade_entry_allowed": False,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {
        "decision": decision,
        "manifest_sha256": digest(MANIFEST),
        "historical_financial_authorized": False,
    }


def resume(expected):
    require(
        isinstance(expected, str)
        and len(expected) == 64
        and digest(MANIFEST) == expected,
        "EXTERNAL_IMPLEMENTATION_PIN_MISMATCH",
    )
    manifest = json.loads(MANIFEST.read_text())
    require(manifest["decision"] in {READY, STOP}, "UNKNOWN_FROZEN_DECISION")
    require(
        manifest["complete_implementation_freeze"] == (manifest["decision"] == READY)
        and manifest["implementation_ready"] == (manifest["decision"] == READY),
        "FROZEN_DECISION_DRIFT",
    )
    require(
        manifest["historical_financial_authorized"] is False
        and manifest["historical_position_evaluations"] == 0
        and manifest["trade_entry_allowed"] is False
        and manifest["PAPER"] is False
        and manifest["LIVE"] is False,
        "FROZEN_SAFETY_DRIFT",
    )
    verify_pins(manifest["artifact_sha256"])
    return {
        "decision": manifest["decision"],
        "verified_resume": True,
        "historical_financial_authorized": False,
        "historical_position_evaluations": 0,
        "trade_entry_allowed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--decision", choices=(READY, STOP))
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    if args.freeze and not args.decision:
        parser.error("--decision required")
    print(
        json.dumps(
            resume(args.expected_manifest_sha256)
            if args.resume_existing
            else freeze(args.decision)
            if args.freeze
            else check(),
            sort_keys=True,
        )
    )
