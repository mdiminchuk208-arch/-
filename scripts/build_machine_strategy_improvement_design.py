"""Separate post-diagnosis designs; previous machine results and source freezes immutable."""

from __future__ import annotations

import argparse
from pathlib import Path

from machine_strategy_research_io import (
    original_invariance,
    qa_stage,
    seal_machine,
    verify_machine,
)
from original_v1_1_financial_data import ROOT, checksum, save, write_csv
from run_machine_strategy_research import DESIGN, checked_commit, dest, read

CODE = [
    "scripts/continue_machine_strategy_workflow.py",
    "scripts/build_machine_strategy_improvement_design.py",
    "scripts/commit_machine_research_stage.py",
    "tests/test_machine_strategy_improvements.py",
]
FILES = [
    "VERSION_RULES.json",
    "MACHINE_STRATEGY_SPEC.md",
    "MACHINE_RULE_REGISTRY.csv",
    "DECISION_TREE.md",
    "DIAGNOSIS.json",
    "PARENT_INVARIANCE.json",
]


def configuration(version):
    if version == "v2.1":
        return {
            "version": version,
            "classification": "MACHINE_RULE_PRE_BACKTEST",
            "rule_ids": ["M21_EDGE_COST_BUDGET"],
            "minimum_edge_cost_ratio": 5,
            "minimum_structural_R": 0,
            "definition": "Before READY/order, abs(structural FTA-entry)/((entry+FTA)*(fee+slippage each leg)) must be >=5. Known H1/H4/D1 setup/context and causal structural FTA are inherited mandatory gates. Target/stop are not moved.",
            "rationale": "Economic budget: estimated full round-trip costs may consume at most 20% of structural gross potential. Five follows this declared cost budget, not a parameter sweep or best historical WR/PF. v2 positive Gross is overwhelmed by modeled costs.",
            "holding_duration_used_for_admission": False,
            "outcome_labels_used_for_admission": False,
            "TP_percent_fixed": False,
            "base_geometry_changed": False,
            "trade_entry_allowed": False,
        }
    if version == "v2.2":
        return {
            "version": version,
            "classification": "MACHINE_RULE_PRE_BACKTEST",
            "rule_ids": ["M21_EDGE_COST_BUDGET", "M22_STRUCTURAL_ONE_R"],
            "minimum_edge_cost_ratio": 5,
            "minimum_structural_R": 1,
            "definition": "Retain v2.1 cost budget. Structural target distance must additionally cover at least one initial planned stop distance: abs(FTA-entry)/abs(entry-fixed stop)>=1. No farther substitute target; reject before order when nearest causal FTA fails.",
            "rationale": "A new risk-budget hypothesis: a full nearest-target win must offer at least the gross price risk of one planned stop. Unity is risk symmetry, not a searched optimum. It does not guarantee positive expectancy or solve sample/OOS/execution gaps.",
            "holding_duration_used_for_admission": False,
            "outcome_labels_used_for_admission": False,
            "TP_percent_fixed": False,
            "base_geometry_changed": False,
            "trade_entry_allowed": False,
        }
    raise ValueError("Only two bounded improvement cycles authorized")


def build(version, output):
    if (output / "VERSION_RULES.json").exists():
        raise ValueError("Existing improvement design preserved")
    previous = "v2" if version == "v2.1" else "v2.1"
    robust = dest(previous, "robustness")
    result = dest(previous, "result")
    a = verify_machine(robust)
    b = verify_machine(result)
    checked_commit(robust)
    checked_commit(result)
    status = read(robust / "ROBUSTNESS.json")
    if status["research_quality_gate"] != "FAIL":
        raise ValueError("Improvement stage is not triggered by the quality gate")
    invariance = original_invariance()
    verify_machine(DESIGN)
    metrics = read(result / "METRICS.json")
    config = configuration(version)
    output.mkdir(parents=True, exist_ok=True)
    save(output / "VERSION_RULES.json", config)
    save(
        output / "DIAGNOSIS.json",
        {
            "previous_version": previous,
            "frozen_result": b,
            "frozen_robustness": a,
            "previous_metrics": metrics,
            "previous_failures": status["failure_reasons"],
            "single_new_hypothesis": config["rule_ids"][-1],
            "brute_force_search": False,
            "threshold_candidates_tested": 1,
            "branch_or_coin_removed": False,
            "outcome_relabeling": False,
            "same_dataset_development_retest": True,
            "trade_entry_allowed": False,
        },
    )
    rows = [
        {
            "rule_id": rid,
            "classification": "MACHINE_RULE_PRE_BACKTEST",
            "definition": config["definition"],
            "rationale": config["rationale"],
            "promoted_to_SOURCE_RULE": False,
        }
        for rid in config["rule_ids"]
    ]
    write_csv(output / "MACHINE_RULE_REGISTRY.csv", rows, list(rows[0]))
    (output / "MACHINE_STRATEGY_SPEC.md").write_text(
        "# Machine "
        + version
        + "\n\nFrozen base v2 engine, five branches, TF roles, structure/liquidity/FTA, FIRST_TEST_ONLY, fixed stop, no BE and theoretical accounting remain unchanged. Inherited geometry/case IDs identify the same market opportunities across strategy versions; version-specific admission is frozen separately. Exact Original stays the source reference.\n\n"
        + config["definition"]
        + "\n\n"
        + config["rationale"]
        + "\n\nThis design is created only after the previous version result and robustness commits. One new pre-entry hypothesis, no parameter sweep, no removal based on realized WIN/LOSS, hold duration, coin, branch or period. No target percentage substitution, no farther target chosen for R. Version P&L will be calculated only after its own pre-outcome commit. Reusing fully viewed 2023-2025 data is development diagnosis, not independent validation. Production requires real execution evidence and forward paper; trade_entry_allowed=false.\n"
    )
    (output / "DECISION_TREE.md").write_text(
        "# Decision tree\n\nFrozen v2 machine structural/branch/context/POI/stop/FTA/identity selection -> known structural distance and complete registered round-trip fee/slippage estimate -> version cost-budget gate -> "
        + ("structural one-R gate -> " if version == "v2.2" else "")
        + "unique version ALLOWED setup -> frozen next-H1-cycle order.\n\nNo branch fallback after rejected base sibling selection. All base branches remain represented; entire physical setup is rejected if new economic gate fails. Base source model and previous financial outcomes never rewritten. No future holding-time filter.\n"
    )
    save(output / "PARENT_INVARIANCE.json", invariance)
    print("IMPROVEMENT_DESIGN_COMPLETE", version, config["rule_ids"], flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", required=True, choices=["v2.1", "v2.2"])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--replay-output", type=Path)
    g.add_argument("--validate-replay", type=Path)
    g.add_argument("--seal", action="store_true")
    g.add_argument("--resume-existing", action="store_true")
    a = p.parse_args()
    directory = dest(a.version, "design")
    if a.resume_existing:
        verify_machine(directory)
        original_invariance()
        print("VERIFIED_RESUME IMPROVEMENT", a.version)
    elif a.validate_replay:
        qa = qa_stage(directory, CODE, a.validate_replay, FILES, minimum_tests=930)
        (directory / "QA_REPORT.md").write_text(
            f"# Improvement design QA\n\nPASS: {qa['tests']} inherited/new tests, {len(FILES)} deterministic files. Previous result/robustness are committed and hash verified; one economic pre-entry hypothesis per version, no parameter search. Threshold equality, case identity, immutable geometry, cost-only/structural-R gates and absence of holding/outcome admission inputs regression tested. Original/current predecessors unchanged; trade_entry_allowed=false.\n"
        )
    elif a.seal:
        previous = "v2" if a.version == "v2.1" else "v2.1"
        parent = dest(previous, "robustness") / "freeze_manifest.json"
        seal_machine(
            directory,
            CODE,
            stage="DESIGN",
            version=a.version,
            parents={str(parent.relative_to(ROOT)): checksum(parent)},
            status="PRE_OUTCOME_SINGLE_HYPOTHESIS",
        )
    else:
        build(a.version, a.replay_output or directory)


if __name__ == "__main__":
    main()
