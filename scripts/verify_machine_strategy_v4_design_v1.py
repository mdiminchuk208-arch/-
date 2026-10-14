"""Verify/freeze design artifacts only; never imports an adapter or evaluates trades."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_design_v1"
SELF = "scripts/verify_machine_strategy_v4_design_v1.py"
TEST = "tests/test_machine_strategy_v4_design_v1.py"
DECISION = "MACHINE_STRATEGY_V4_DESIGN_PASS"
REQUIRED = (
    "MACHINE_STRATEGY_V4_SPEC.md",
    "DECISION_TREE.json",
    "DECISION_TREE.md",
    "RULE_REGISTRY.json",
    "RULE_PROVENANCE_REGISTRY.json",
    "V3_TO_V4_CHANGELOG.md",
    "TELEMETRY_SCHEMA.json",
    "OBSERVER_TELEMETRY_SCHEMA.json",
    "TF_ROLE_MATRIX.csv",
    "ENTRY_EXIT_CONTRACT.json",
    "EXECUTION_CONTRACT.json",
    "V4_PREREGISTRATION.json",
    "QUALIFICATION_PREREGISTRATION.json",
    "PROJECT_POLICY_REGISTRY.json",
    "TECHNICAL_NORMALIZATION_REGISTRY.json",
    "SOURCE_CONFLICT_REGISTRY.json",
    "INHERITED_INPUTS_AND_SOURCE_CITATIONS.json",
    "AMBIGUITY_AND_STOP_REGISTRY.json",
    "DETERMINISTIC_REVIEW_CLARIFICATIONS.md",
    "DESIGN_GATE_PROTOCOL.md",
    "DESIGN_INPUTS.json",
)
QUALIFICATION = {
    "win_rate_min": "0.70",
    "closed_trades_min": 200,
    "profit_factor_min": "1.20",
    "net_expectancy_R_min_exclusive": "0",
    "net_PnL_min_exclusive": "0",
    "doubled_cost_profit_factor_min": "1.00",
    "doubled_cost_net_positive": True,
    "case_ledger_max_drawdown_R_max": "20",
    "max_consecutive_net_losses_max": 10,
    "each_coin_direction_closed_min": 30,
    "each_coin_direction_net_positive": True,
    "wilson_95pct_win_rate_lower_bound_min": "0.60",
    "largest_calendar_quarter_profit_share_max": "0.50",
    "largest_coin_profit_share_max": "0.80",
    "filled_unknown_exit_max": 0,
    "no_critical_causality_or_integrity_failure": True,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str) -> dict:
    return json.loads((DEST / name).read_text())


def require(value: object, message: str) -> None:
    if not value:
        raise ValueError(message)


def verify_pins(pins: dict[str, str], root: Path = ROOT) -> None:
    require(bool(pins), "empty pin set")
    for name, expected in pins.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root.resolve()), "unsafe pin path")
        require(path.is_file() and digest(path) == expected, f"changed pin: {name}")


def check_design() -> dict:
    for name in REQUIRED:
        require((DEST / name).is_file(), f"missing required design artifact: {name}")
    for path in DEST.rglob("*.json"):
        json.loads(path.read_text())
    inputs = read("DESIGN_INPUTS.json")
    inherited = read("INHERITED_INPUTS_AND_SOURCE_CITATIONS.json")
    verify_pins(inputs["input_sha256"])
    verify_pins(inherited["inherited_input_sha256"])
    prereg = read("V4_PREREGISTRATION.json")
    require(prereg == read("QUALIFICATION_PREREGISTRATION.json"), "prereg alias drift")
    require(prereg["qualification"] == QUALIFICATION, "qualification drift")
    parent = json.loads(
        (
            ROOT
            / "docs/machine_strategy_v3_okx_compatibility_v1/COMPATIBILITY_PREREGISTRATION.json"
        ).read_text()
    )["qualification_unchanged"]
    aliases = {
        "net_PnL_min_exclusive": "net_PnL_cash_risk_units_min_exclusive",
        "doubled_cost_net_positive": "doubled_total_fees_and_slippage_net_positive",
        "each_coin_direction_closed_min": "coin_and_direction_closed_min",
        "each_coin_direction_net_positive": "each_coin_and_direction_net_positive",
    }
    for key, value in QUALIFICATION.items():
        require(
            parent[aliases.get(key, key)] == value,
            f"parent qualification mismatch: {key}",
        )
    require(prereg["safety"]["trade_entry_allowed"] is False, "trading enabled")
    require(
        prereg["safety"]["PAPER"] is False and prereg["safety"]["LIVE"] is False,
        "trading mode enabled",
    )
    require(
        prereg["design_outcome_isolation"]["v4_financial_validation_authorized"]
        is False,
        "financial authorization in design gate",
    )
    require(
        prereg["design_outcome_isolation"]["v4_financial_outcomes_seen"] is False,
        "v4 outcomes seen before freeze",
    )
    entry, execution = read("ENTRY_EXIT_CONTRACT.json"), read("EXECUTION_CONTRACT.json")
    require(
        set(entry["families"]) == {"SFP", "OB", "BREAKER", "STB", "RANGE"},
        "family deletion",
    )
    require(
        execution["lifetime"]["deadline_seconds_after_anchor"] == 57600,
        "duration retuned",
    )
    require(
        execution["safety"]["financial_validation_authorized"] is False,
        "execution grants financial run",
    )
    telemetry = read("TELEMETRY_SCHEMA.json")
    require(
        telemetry == read("OBSERVER_TELEMETRY_SCHEMA.json"), "telemetry alias drift"
    )
    require(
        telemetry["observer_only"] is True
        and telemetry["outcome_fields_forbidden"] is True,
        "outcome readback",
    )
    registry = read("RULE_REGISTRY.json")
    rules = registry["rules"]
    require(len({r["rule_id"] for r in rules}) == len(rules), "duplicate rule IDs")
    require(
        {r["hypothesis"] for r in rules if r["hypothesis"]}
        == {f"H{i:02d}" for i in range(6)},
        "unclassified hypothesis",
    )
    source_ids = {r["rule_id"] for r in inherited["source_concepts"]}
    for rule in rules:
        require(
            rule["classification"] != "SOURCE_RULE", "machine rule source promotion"
        )
        require(rule["historical_PnL_selection"] is False, "outcome-selected rule")
        require(
            set(rule["source_concept_refs"]) <= source_ids, "missing source concept"
        )
        pointer = rule["normative_pointer"].split("#", 1)[0]
        path = ROOT / pointer if pointer.startswith("docs/") else DEST / pointer
        require(path.is_file(), f"missing normative file: {pointer}")
    for name, classification in [
        ("PROJECT_POLICY_REGISTRY.json", "PROJECT_POLICY"),
        ("TECHNICAL_NORMALIZATION_REGISTRY.json", "TECHNICAL_NORMALIZATION"),
    ]:
        require(
            read(name)["rules"]
            == [r for r in rules if r["classification"] == classification],
            f"classification partition drift: {name}",
        )
    return {
        "status": "PASS_DESIGN_CONSISTENCY_ONLY",
        "new_trade_evaluations": 0,
        "new_financial_backtests": 0,
        "design_financial_authorization": False,
    }


def freeze() -> dict:
    check_design()
    qa = read("QA_RECEIPT.json")
    require(qa["status"] == "PASS", "QA not pass")
    verify_pins(qa["tested_sha256"])
    require(all(r["exit_code"] == 0 for r in qa["commands"]), "QA command failed")
    verify_pins(qa["log_sha256"])
    reviews = read("INDEPENDENT_REVIEW_RECEIPT.json")
    require(reviews["decision"] == DECISION, "independent design acceptance absent")
    require(
        {r["role"] for r in reviews["reviews"]}
        >= {"execution_auditor", "backtest_reviewer", "final_independent_reviewer"},
        "missing actual independent role",
    )
    require(all(r["decision"] == "PASS" for r in reviews["reviews"]), "review not pass")
    verify_pins(reviews["reviewed_sha256"])
    path = DEST / "DESIGN_FREEZE_MANIFEST.json"
    require(
        not path.exists(), "design already frozen; externally pinned resume required"
    )
    pins = dict(read("DESIGN_INPUTS.json")["input_sha256"])
    pins.update(
        read("INHERITED_INPUTS_AND_SOURCE_CITATIONS.json")["inherited_input_sha256"]
    )
    for p in sorted(DEST.rglob("*")):
        if p.is_file() and p != path:
            pins[str(p.relative_to(ROOT))] = digest(p)
    for name in (SELF, TEST):
        pins[name] = digest(ROOT / name)
    manifest = {
        "decision": DECISION,
        "version": "MACHINE_STRATEGY_v4",
        "artifact_sha256": pins,
        "implementation_started": False,
        "implementation_frozen": False,
        "implementation_readiness_may_open": True,
        "financial_validation_authorized": False,
        "new_trade_evaluations": 0,
        "trade_entry_allowed": False,
        "PAPER": False,
        "LIVE": False,
        "controls_excluded": "Mutable campaign files are publication state, not design authority",
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {
        "decision": DECISION,
        "manifest_sha256": digest(path),
        "new_trade_evaluations": 0,
    }


def resume(expected: str) -> dict:
    path = DEST / "DESIGN_FREEZE_MANIFEST.json"
    require(
        len(expected) == 64 and digest(path) == expected,
        "external manifest pin mismatch",
    )
    manifest = read("DESIGN_FREEZE_MANIFEST.json")
    require(
        manifest["decision"] == DECISION
        and manifest["financial_validation_authorized"] is False,
        "invalid design decision or authority",
    )
    verify_pins(manifest["artifact_sha256"])
    return {"decision": DECISION, "verified_resume": True, "new_trade_evaluations": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    if args.resume_existing:
        require(
            bool(args.expected_manifest_sha256), "resume requires external manifest SHA"
        )
        result = resume(args.expected_manifest_sha256)
    elif args.freeze:
        result = freeze()
    else:
        result = check_design()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
