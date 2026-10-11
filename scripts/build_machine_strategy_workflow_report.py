"""Compare immutable development versions and report blocked downstream gates."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from machine_strategy_research_io import (
    original_invariance,
    qa_stage,
    read,
    seal_machine,
    verify_machine,
)
from original_v1_1_financial_data import ROOT, checksum, save, write_csv
from run_machine_strategy_research import DESIGN, dest, rows

CODE = ["scripts/build_machine_strategy_workflow_report.py"]
PRESERVE = ROOT / "docs/machine_strategy_preservation"
REPORT = ROOT / "docs/machine_strategy_workflow_report"
PRESERVE_FILES = ["PRESERVATION_REPORT.json", "PRESERVATION_REPORT.md"]
REPORT_FILES = [
    "ALL_FILLED_TRADES_VERSIONS.csv",
    "COMPARATIVE_REPORT.json",
    "MASTER_STAGE_REPORT.json",
    "MASTER_REPORT.md",
]


def commit_for(path):
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", str(path.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
    ).strip()


def preservation(output):
    result = original_invariance()
    verify_machine(DESIGN)
    initial = read(DESIGN / "STAGE_0_PRESERVATION.json")
    changes = subprocess.check_output(
        ["git", "diff", "--name-status", "6918d82..HEAD"], cwd=ROOT, text=True
    )
    if any(not row.startswith("A\t") for row in changes.splitlines()):
        raise ValueError("A predecessor was modified or deleted")
    output.mkdir(parents=True, exist_ok=True)
    save(
        output / "PRESERVATION_REPORT.json",
        {
            "stage": 0,
            "status": "PASS_PRESERVED",
            "initial_before_outcome_proof": str(
                (DESIGN / "STAGE_0_PRESERVATION.json").relative_to(ROOT)
            ),
            "initial_proof_commit": commit_for(DESIGN / "STAGE_0_PRESERVATION.json"),
            "archival_note": "Stage 0 hash verification was performed before design/cohort/outcomes and recorded in the design freeze. This separate namespace archives and re-verifies that proof; it does not backdate a new commit.",
            "initial_proof_sha256": checksum(DESIGN / "STAGE_0_PRESERVATION.json"),
            "preserved_concepts": initial["concepts"],
            "original_v1_v1_1_U1_U6_N11_v2_v3_v4_metadata_first_result_baseline_audit_dataset": result,
            "git_changes_after_frozen_parent": "ADDITIONS_ONLY",
            "main_modified": False,
            "trade_entry_allowed": False,
        },
    )
    (output / "PRESERVATION_REPORT.md").write_text(
        "# Preservation\n\nPASS: all immutable Original/evidence/metadata/first financial result/baseline/audit/dataset hashes. SFP/OB/Breaker/STB/BTS/Range/FVG/IMB/liquidity/BOS/CONF/OTE/PD/FTA/FIRST_TEST_ONLY/fixed stop/M15-H1-H4-D1 preserved. All tracked changes after 6918d82 are additions. Initial pre-outcome preservation proof is in the design commit; this independent archive/checkpoint does not claim an earlier commit date. No main modification, LIVE/private API or production activation. trade_entry_allowed=false.\n"
    )


def build_report(output):
    if (output / "MASTER_STAGE_REPORT.json").exists():
        raise ValueError("Existing master report preserved")
    original_invariance()
    verify_machine(PRESERVE)
    exported = []
    variants = {}
    stages = []
    versions = []
    for version in ("v2", "v2.1", "v2.2"):
        if not (dest(version, "robustness") / "freeze_manifest.json").exists():
            continue
        versions.append(version)
        for name in ("design", "pre_outcome", "result", "robustness"):
            directory = (
                DESIGN if version == "v2" and name == "design" else dest(version, name)
            )
            frozen = verify_machine(directory)
            path = directory / "freeze_manifest.json"
            key = {
                "design": "DETERMINISTIC",
                "pre_outcome": "PRE_OUTCOME_COMMITTED",
                "result": "FINANCIAL_RESULT_FROZEN",
                "robustness": read(dest(version, "robustness") / "ROBUSTNESS.json")[
                    "research_quality_gate"
                ],
            }[name]
            stages.append(
                {
                    "stage": {
                        "design": 1,
                        "pre_outcome": 2,
                        "result": 3,
                        "robustness": 4,
                    }[name]
                    if version == "v2"
                    else 5
                    if version == "v2.1"
                    else 6,
                    "substage": name,
                    "version": version,
                    "status": key,
                    "commit": commit_for(path),
                    "manifest": frozen["path"],
                    "manifest_sha256": frozen["sha256"],
                    "next_gate": "NEXT_SEQUENTIAL_STAGE"
                    if name != "robustness"
                    else "QUALITY_AND_EXECUTION_READINESS",
                }
            )
        metrics = read(dest(version, "result") / "METRICS.json")
        robust = read(dest(version, "robustness") / "ROBUSTNESS.json")
        for trade in rows(dest(version, "result") / "ALL_TRADES.jsonl.gz"):
            exported.append(
                {
                    "machine_version": version,
                    **{
                        key: trade.get(key)
                        for key in (
                            "case_id",
                            "symbol",
                            "branch",
                            "direction",
                            "setup_tf",
                            "decision_at",
                            "fill_at",
                            "exit_at",
                            "status",
                            "fill_price",
                            "fixed_initial_stop",
                            "theoretical_target",
                            "exit_price",
                            "exit_reason",
                            "WIN",
                            "LOSS",
                            "Gross_R",
                            "Fees_R",
                            "Slippage_R",
                            "Funding_R",
                            "Net_R",
                            "hold_hours",
                            "trade_entry_allowed",
                        )
                    },
                }
            )
        variants[version] = {
            "metrics": metrics,
            "robustness_classification": robust["classification"],
            "quality_gate": robust["research_quality_gate"],
            "failure_reasons": robust["failure_reasons"],
            "production_execution_gate": robust["production_execution_gate"],
            "all_trades": str(
                (dest(version, "result") / "ALL_TRADES.jsonl.gz").relative_to(ROOT)
            ),
            "breakdowns": str(
                (dest(version, "result") / "BREAKDOWNS.json").relative_to(ROOT)
            ),
        }
    if not versions:
        raise ValueError("No completed financial/robustness version")
    # Matched diagnostics use outcomes only after every version's immutable result.
    base = rows(dest("v2", "result") / "ALL_CASE_EXECUTIONS.jsonl.gz")
    base_by_id = {r["case_id"]: r for r in base}
    matched = {}
    for version in versions[1:]:
        actual = rows(dest(version, "result") / "ALL_CASE_EXECUTIONS.jsonl.gz")
        excluded = rows(
            dest(version, "pre_outcome") / "EXCLUDED_VERSION_CASES.jsonl.gz"
        )
        for r in actual:
            b = base_by_id[r["case_id"]]
            for key in (
                "status",
                "filled",
                "closed",
                "fill_price",
                "exit_price",
                "Gross_R",
                "Fees_R",
                "Slippage_R",
                "Net_R",
                "fixed_initial_stop",
                "theoretical_target",
            ):
                if r[key] != b[key]:
                    raise ValueError(
                        "Matched unchanged entry/management produced a different result"
                    )
        removed = {r["case_id"] for r in excluded}
        short = [r for r in base if r["closed"] and r["hold_hours"] < 1]
        matched[version] = {
            "remaining_case_count": len(actual),
            "removed_pre_entry_cases": len(removed),
            "old_v2_closed_short_under_1h": len(short),
            "old_short_cases_excluded_by_causal_filter": sum(
                r["case_id"] in removed for r in short
            ),
            "old_v2_losses_excluded": sum(
                r["closed"] and r["LOSS"] and r["case_id"] in removed for r in base
            ),
            "old_v2_wins_excluded": sum(
                r["closed"] and r["WIN"] and r["case_id"] in removed for r in base
            ),
            "matched_execution_identity": "PASS",
            "holding_time_used_for_admission": False,
            "interpretation": "Removed wins and losses are cohort changes by pre-entry economic rules, not relabeled false positives. Holding-duration comparison is retrospective diagnosis only.",
        }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "ALL_FILLED_TRADES_VERSIONS.csv", exported, list(exported[0]))
    save(
        output / "COMPARATIVE_REPORT.json",
        {
            "versions": variants,
            "matched_diagnostics": matched,
            "changes": {
                "v2.1": "One pre-entry cost budget: edge/cost>=5; costs at most 20% of structural potential.",
                "v2.2": "Retain v2.1 and require nearest structural FTA distance >=1 planned initial stop distance.",
            },
            "parameters_searched": False,
            "development_dataset_reused": True,
            "independent_validation": False,
            "production_candidate_selected": False,
            "trade_entry_allowed": False,
        },
    )
    stages.insert(
        0,
        {
            "stage": 0,
            "version": "Original/reference",
            "status": "HASH_VERIFIED_PRESERVED",
            "commit": commit_for(PRESERVE / "freeze_manifest.json"),
            "manifest": str((PRESERVE / "freeze_manifest.json").relative_to(ROOT)),
            "manifest_sha256": checksum(PRESERVE / "freeze_manifest.json"),
            "next_gate": "INITIAL_PROOF_PRECEDES_MACHINE_DESIGN",
        },
    )
    stages.extend(
        {
            "stage": i,
            "version": None,
            "status": "BLOCKED_NOT_RUN",
            "commit": None,
            "manifest": None,
            "next_gate": gate,
        }
        for i, gate in (
            (7, "QUALIFIED_BASE_PRODUCTION_CANDIDATE"),
            (8, "SATISFACTORY_BACKTEST_ROBUSTNESS_AND_TESTED_OVERLAYS"),
            (9, "SUCCESSFUL_200_CLOSED_30_DAY_FORWARD_PAPER_GATE"),
        )
    )
    stop = [
        "No production candidate selected: completed development versions do not establish qualified backtest/robustness and exchange execution evidence.",
        "Theoretical unrounded tick/epsilon execution and unavailable funding cannot establish realistic exchange performance.",
        "No independent forward/OOS validation; same-history v2.1/v2.2 results are development diagnostics.",
        "No paper session started; 0 CLOSED virtual paper trades and 0 calendar days. Historical CLOSED is not forward paper evidence.",
    ]
    summary = {
        "stages": stages,
        "CURRENT_PRODUCTION_CANDIDATE": None,
        "machine_version_selected": None,
        "candidate_metrics": {
            k: None
            for k in (
                "Backtest_CLOSED",
                "WR",
                "PF",
                "Expectancy",
                "AvgR",
                "Net",
                "MaxDD",
                "Robustness",
            )
        },
        "completed_versions": versions,
        "Paper_trades": 0,
        "Paper_days": 0,
        "PAPER_TRADING_READY": False,
        "REAL_TRADING_READY": False,
        "project_overlays": "BLOCKED_NOT_RUN",
        "trade_entry_allowed": False,
        "STOP_REASONS": stop,
        "Original_source_ready_unchanged": 0,
        "main_modified": False,
        "all_key_artifact_paths": {
            v: {
                name: str(
                    (
                        DESIGN if v == "v2" and name == "design" else dest(v, name)
                    ).relative_to(ROOT)
                )
                for name in ("design", "pre_outcome", "result", "robustness")
            }
            for v in versions
        },
    }
    save(output / "MASTER_STAGE_REPORT.json", summary)
    lines = [
        "# Machine strategy workflow report",
        "",
        "| Stage | Version | Status | Commit | Manifest | Next gate |",
        "|---|---|---|---|---|---|",
    ]
    for r in stages:
        lines.append(
            "| "
            + " | ".join(
                str(r.get(k) or "—")
                for k in (
                    "stage",
                    "version",
                    "status",
                    "commit",
                    "manifest",
                    "next_gate",
                )
            )
            + " |"
        )
    lines += [
        "",
        "| Version | CLOSED | WR % | PF | Expectancy/AvgR | Net ex-funding R | MaxDD R | Robustness |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for v, r in variants.items():
        m = r["metrics"]
        lines.append(
            f"| {v} | {m['CLOSED']} | {m['WR_percent']} | {m['PF_net']} | {m['Expectancy_R']} | {m['Net_R_ex_funding']} | {m['MaxDD_R']} | {r['robustness_classification']} |"
        )
    lines += [
        "",
        "CURRENT_PRODUCTION_CANDIDATE=null. PAPER_TRADING_READY=false. REAL_TRADING_READY=false. trade_entry_allowed=false.",
        "",
        "STOP:",
    ] + ["- " + s for s in stop]
    lines += [
        "",
        "v2.1: edge/cost>=5. v2.2: retain cost budget and add structural target>=1 initial R. Stops/targets/branches/periods remain unchanged; rejected wins and losses are reported. No threshold sweep or best subgroup selection. No prior frozen version rewritten.",
        "",
        "QA: exact matched execution identity, inherited source/data/archive hashes, deterministic outputs and mode/prefix/future-mutation checks. All trades/metrics/breakdowns/holding/cost sensitivity in version result and robustness namespaces. Funding excluded; unrounded theoretical prices. Values are independent-case normalized risk units and diagnostic closed-return drawdown, not account currency or a live portfolio. Backtest results do not guarantee future profits.",
    ]
    (output / "MASTER_REPORT.md").write_text("\n".join(lines) + "\n")
    print("MASTER_REPORT_COMPLETE", versions, "NO_PRODUCTION_CANDIDATE", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", required=True, choices=["preservation", "report"])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--replay-output", type=Path)
    g.add_argument("--validate-replay", type=Path)
    g.add_argument("--seal", action="store_true")
    g.add_argument("--resume-existing", action="store_true")
    a = p.parse_args()
    directory = PRESERVE if a.stage == "preservation" else REPORT
    files = PRESERVE_FILES if a.stage == "preservation" else REPORT_FILES
    if a.resume_existing:
        verify_machine(directory)
        original_invariance()
        print("VERIFIED_RESUME MASTER", a.stage)
    elif a.validate_replay:
        qa = qa_stage(directory, CODE, a.validate_replay, files, minimum_tests=939)
        (directory / "QA_REPORT.md").write_text(
            f"# {a.stage} QA\n\nPASS: {qa['tests']} inherited/new tests; {len(files)} deterministic output files. Original and every completed machine freeze verified; all tracked predecessor changes are additions. Matched cases preserve unchanged prices/execution/cost results; prospective economic filters are separate from retrospective duration/win/loss diagnostics. No financial or paper sample misrepresented. trade_entry_allowed=false.\n"
        )
    elif a.seal:
        parents = {
            str((DESIGN / "freeze_manifest.json").relative_to(ROOT)): checksum(
                DESIGN / "freeze_manifest.json"
            )
        }
        if a.stage == "report":
            parents[str((PRESERVE / "freeze_manifest.json").relative_to(ROOT))] = (
                checksum(PRESERVE / "freeze_manifest.json")
            )
            for v in read(REPORT / "MASTER_STAGE_REPORT.json")["completed_versions"]:
                path = dest(v, "robustness") / "freeze_manifest.json"
                parents[str(path.relative_to(ROOT))] = checksum(path)
        seal_machine(
            directory,
            CODE,
            stage=a.stage,
            version="ALL_FROZEN_VERSIONS",
            parents=parents,
            status="PRESERVED"
            if a.stage == "preservation"
            else "STOP_NO_QUALIFIED_PRODUCTION_CANDIDATE",
            outcomes=a.stage == "report",
        )
    else:
        (preservation if a.stage == "preservation" else build_report)(
            a.replay_output or directory
        )


if __name__ == "__main__":
    main()
