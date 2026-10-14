"""Design integrity/freeze verifier. No adapter, outcome or historical execution imports."""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_1_design_v1"
MANIFEST = DEST / "DESIGN_FREEZE_MANIFEST.json"
PARENTS = {
    "docs/machine_strategy_v4_design_v1/DESIGN_FREEZE_MANIFEST.json": "b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b",
    "docs/machine_strategy_v4_implementation_readiness_v1/IMPLEMENTATION_FREEZE_MANIFEST.json": "6e325d6e5b3cffc4f143bfd4d390712b39ea940bccd4504c85148ed904bbcd7e",
}
NORMATIVE = (
    "MACHINE_STRATEGY_v4_1_SPEC.md",
    "SELECTED_POI_CONTRACT.json",
    "ARITHMETIC_SCOPE_CONTRACT.json",
    "PREREGISTRATION.json",
    "FIELD_PROVENANCE.json",
    "FIRST_TEST_DECISION_TREE.json",
    "RULE_REGISTRY.json",
    "SYNTHETIC_WITNESS_REGISTRY.json",
    "INHERITANCE_AND_SOURCE_CITATIONS.json",
)
CODE = (
    "scripts/machine_strategy_v4_1_design_reference.py",
    "scripts/verify_machine_strategy_v4_1_design_v1.py",
    "tests/test_machine_strategy_v4_1_design.py",
)
VERSION = "MACHINE_STRATEGY_v4.1"
PASS = "MACHINE_STRATEGY_V4_1_DESIGN_PASS"
STOP = "MACHINE_STRATEGY_V4_1_DESIGN_STOP"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    verify_pins(PARENTS)
    pins = dict(PARENTS)
    for name in PARENTS:
        parent = json.loads((ROOT / name).read_text())
        inherited = parent["artifact_sha256"]
        verify_pins(inherited)
        for path, sha in inherited.items():
            require(
                path not in pins or pins[path] == sha, "PARENT_PIN_CONFLICT:" + path
            )
            pins[path] = sha
    return pins


def pointer(document, path):
    for component in path.split("/")[1:]:
        component = component.replace("~1", "/").replace("~0", "~")
        document = (
            document[int(component)]
            if isinstance(document, list)
            else document[component]
        )
    return document


def check_design():
    parent_pins()
    inputs = read("DESIGN_INPUTS.json")
    verify_pins(inputs["input_sha256"])
    require(
        inputs["frozen_v4_design_manifest_sha256"]
        == PARENTS["docs/machine_strategy_v4_design_v1/DESIGN_FREEZE_MANIFEST.json"],
        "DESIGN_PARENT_DRIFT",
    )
    require(
        inputs["v4_STOP_checkpoint_manifest_sha256"]
        == PARENTS[
            "docs/machine_strategy_v4_implementation_readiness_v1/IMPLEMENTATION_FREEZE_MANIFEST.json"
        ],
        "STOP_PARENT_DRIFT",
    )
    for key in (
        "historical_financial_authorized",
        "implementation_authorized",
        "source_rule_changes_authorized",
        "trade_entry_allowed",
    ):
        require(inputs[key] is False, "INPUT_AUTHORIZATION_DRIFT:" + key)
    for name in NORMATIVE:
        require((DEST / name).is_file(), "REQUIRED_ARTIFACT_MISSING:" + name)
    selected = read("SELECTED_POI_CONTRACT.json")
    arithmetic = read("ARITHMETIC_SCOPE_CONTRACT.json")
    prereg = read("PREREGISTRATION.json")
    require(
        selected["version"] == VERSION and selected["normative"] is True,
        "WRONG_SELECTED_CONTRACT",
    )
    require(
        set(selected["families"]) == {"SFP", "OB", "STB", "BREAKER", "RANGE"},
        "FAMILY_DRIFT",
    )
    require(
        selected["common"]["retroactive_close_cancel_allowed"] is False,
        "RETROACTIVE_CANCEL",
    )
    require(
        selected["common"]["same_physical_poi_retry_allowed"] is False, "RETRY_DRIFT"
    )
    require(
        "FIRST admissible completed M15" in selected["common"]["eligibility_rule"],
        "CLOCK_AMBIGUITY",
    )
    for family in selected["families"].values():
        require(
            family["eligibility_at"].startswith("FIRST admissible completed M15"),
            "FAMILY_CLOCK_DRIFT",
        )
    require(
        selected["deadline"]["seconds"] == 57600
        and selected["deadline"]["anchor"] == "formation_known_at",
        "DEADLINE_DRIFT",
    )
    require(
        selected["safety"]
        == {"LIVE": False, "PAPER": False, "trade_entry_allowed": False},
        "TRADING_ENABLED",
    )
    require(
        arithmetic["design_scope"]["decimal_precision"] == 50
        and arithmetic["ledger_scope"]["decimal_precision"] == 80,
        "PRECISION_DRIFT",
    )
    require(
        arithmetic["rounding"] == "ROUND_HALF_EVEN"
        and arithmetic["ledger_scope"]["may_recompute_design_geometry"] is False,
        "LEDGER_RECOMPUTATION",
    )
    require(
        arithmetic["financial_validation_authorized"] is False
        and selected["financial_validation_authorized"] is False,
        "FINANCIAL_AUTHORIZATION",
    )
    require(
        all(v is False for v in prereg["outcome_isolation"].values()), "OUTCOME_ACCESS"
    )
    require(
        prereg["trade_entry_allowed"] is False
        and prereg["PAPER"] is False
        and prereg["LIVE"] is False,
        "TRADING_ENABLED",
    )
    parent = json.loads(
        (
            ROOT / "docs/machine_strategy_v4_design_v1/V4_PREREGISTRATION.json"
        ).read_text()
    )["qualification"]
    aliases = {
        "win_rate_min": "win_rate_min",
        "closed_trades_min": "closed_trades_min",
        "profit_factor_min": "profit_factor_min",
        "net_expectancy_R_strictly_positive": "net_expectancy_R_min_exclusive",
        "net_PnL_strictly_positive": "net_PnL_min_exclusive",
        "doubled_cost_profit_factor_min": "doubled_cost_profit_factor_min",
        "doubled_cost_net_PnL_strictly_positive": "doubled_cost_net_positive",
        "max_drawdown_R_max": "case_ledger_max_drawdown_R_max",
        "max_consecutive_net_losses_max": "max_consecutive_net_losses_max",
        "each_coin_direction_closed_min": "each_coin_direction_closed_min",
        "each_coin_direction_net_positive": "each_coin_direction_net_positive",
        "wilson_95pct_lower_bound_min": "wilson_95pct_win_rate_lower_bound_min",
        "largest_calendar_quarter_profit_share_max": "largest_calendar_quarter_profit_share_max",
        "largest_coin_profit_share_max": "largest_coin_profit_share_max",
        "filled_unknown_exit_max": "filled_unknown_exit_max",
    }
    require(set(prereg["qualification"]) == set(aliases), "QUALIFICATION_SCHEMA_DRIFT")
    for field, parent_field in aliases.items():
        actual = prereg["qualification"][field]
        expected = parent[parent_field]
        if field in ("net_expectancy_R_strictly_positive", "net_PnL_strictly_positive"):
            require(
                actual is True and Decimal(expected) == 0,
                "POSITIVE_QUALIFICATION_DRIFT",
            )
        elif type(expected) is bool:
            require(actual is expected, "QUALIFICATION_DRIFT:" + field)
        else:
            require(
                type(actual) is not bool
                and Decimal(str(actual)) == Decimal(str(expected)),
                "QUALIFICATION_DRIFT:" + field,
            )
    require(
        parent["no_critical_causality_or_integrity_failure"] is True,
        "INHERITED_INTEGRITY_GATE_MISSING",
    )
    registry = read("RULE_REGISTRY.json")
    require(registry["outcome_selected_rules"] is False, "OUTCOME_SELECTED_RULE")
    for rule in registry["rules"]:
        require(
            rule["classification"] in {"PROJECT_POLICY", "TECHNICAL_NORMALIZATION"}
            and rule["source_rule_claim"] is False,
            "SOURCE_PROMOTION",
        )
        require(bool(rule["citations"]), "MISSING_CITATIONS")
        for citation in rule["citations"]:
            verify_pins({citation["artifact"]: citation["sha256"]})
            pointer(
                json.loads((ROOT / citation["artifact"]).read_text()),
                citation["pointer"],
            )
    citations = read("INHERITANCE_AND_SOURCE_CITATIONS.json")
    verify_pins(
        {
            citations["inherited_v4_citations_artifact"]: citations[
                "inherited_v4_citations_sha256"
            ]
        }
    )
    require(
        citations["new_source_rules"] == []
        and citations["source_selector_equivalence"] is False,
        "SOURCE_PROMOTION",
    )
    for concept in citations["source_concepts"]:
        for citation in concept["citations"]:
            verify_pins(
                {
                    citation["source_document"]: citation["source_sha256"],
                    citation["text"]: citation["text_sha256"],
                }
            )
    witnesses = read("SYNTHETIC_WITNESS_REGISTRY.json")
    require(witnesses["financial_data_allowed"] is False, "FINANCIAL_FIXTURES")
    require(
        len({w["id"] for w in witnesses["witnesses"]}) == len(witnesses["witnesses"]),
        "DUPLICATE_WITNESS_ID",
    )
    return {
        "artifact_integrity": "PASS",
        "design_gate_decision": "NOT_YET_FROZEN",
        "historical_position_evaluations": 0,
        "historical_financial_authorized": False,
        "registered_witnesses": len(witnesses["witnesses"]),
    }


def freeze(decision):
    require(not MANIFEST.exists(), "ALREADY_FROZEN_USE_EXTERNAL_PIN")
    check_design()
    qa = read("QA_RECEIPT.json")
    require(qa["status"] == "PASS", "QA_REQUIRED")
    verify_pins(qa["tested_sha256"])
    verify_pins(qa["log_sha256"])
    final = read("INDEPENDENT_REVIEW_RECEIPT.json")
    require(final["decision"] == decision, "INDEPENDENT_VERDICT_MISMATCH")
    verify_pins(final["reviewed_sha256"])
    required_review = (
        {str((DEST / name).relative_to(ROOT)) for name in NORMATIVE}
        | set(CODE)
        | {str((DEST / "QA_RECEIPT.json").relative_to(ROOT))}
    )
    require(
        required_review <= set(final["reviewed_sha256"]),
        "FINAL_REVIEW_COVERAGE_MISSING",
    )
    for role in ("EXECUTION_AUDITOR", "NO_LOOKAHEAD_AUDITOR"):
        review = read("reviews/" + role + ".json")
        require(
            review["decision"] == PASS or decision == STOP, "SPECIALIST_REVIEW_REQUIRED"
        )
        verify_pins(review["reviewed_sha256"])
    pins = parent_pins()
    for path in DEST.rglob("*"):
        if path.is_file() and path != MANIFEST:
            pins[str(path.relative_to(ROOT))] = digest(path)
    for name in CODE:
        pins[name] = digest(ROOT / name)
    verify_pins(pins)
    result = {
        "version": VERSION,
        "decision": decision,
        "artifact_sha256": pins,
        "parents": PARENTS,
        "historical_position_evaluations": 0,
        "historical_financial_authorized": False,
        "complete_implementation_freeze": False,
        "implementation_ready": False,
        "may_open_separate_implementation_gate": decision == PASS,
        "PAPER": False,
        "LIVE": False,
        "trade_entry_allowed": False,
    }
    MANIFEST.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return {
        "decision": decision,
        "design_manifest_sha256": digest(MANIFEST),
        "historical_financial_authorized": False,
    }


def resume(expected):
    require(
        len(expected) == 64 and MANIFEST.is_file() and digest(MANIFEST) == expected,
        "EXTERNAL_MANIFEST_PIN_MISMATCH",
    )
    manifest = json.loads(MANIFEST.read_text())
    require(manifest["decision"] in (PASS, STOP), "INVALID_DESIGN_VERDICT")
    require(
        manifest["historical_financial_authorized"] is False
        and manifest["implementation_ready"] is False
        and manifest["complete_implementation_freeze"] is False
        and manifest["PAPER"] is False
        and manifest["LIVE"] is False
        and manifest["version"] == VERSION
        and manifest["trade_entry_allowed"] is False,
        "DESIGN_AUTHORITY_ESCALATION",
    )
    verify_pins(manifest["artifact_sha256"])
    require(manifest["parents"] == PARENTS, "PARENT_PIN_DRIFT")
    return {
        "decision": manifest["decision"],
        "verified_resume": True,
        "historical_position_evaluations": 0,
        "historical_financial_authorized": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--decision", choices=(PASS, STOP))
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    if args.freeze and not args.decision:
        parser.error("explicit independently reviewed decision required")
    if args.resume_existing and not args.expected_manifest_sha256:
        parser.error("external manifest SHA required")
    result = (
        check_design()
        if args.check
        else freeze(args.decision)
        if args.freeze
        else resume(args.expected_manifest_sha256)
    )
    print(json.dumps(result, sort_keys=True))
