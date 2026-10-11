"""Gated machine research stages. Financial execution requires a committed pre-outcome freeze."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
from collections import Counter
from pathlib import Path

from machine_strategy_research_io import (
    original_invariance,
    qa_stage,
    read,
    seal_machine,
    verify_machine,
)
from machine_strategy_v2_core import build_cohort
from machine_strategy_v2_execution import (
    ACCOUNTING,
    COST_MULTIPLIERS,
    FEE,
    SLIPPAGE,
    breakdowns,
    calendar,
    execute,
    stats,
)
from original_v1_1_financial_data import (
    ROOT,
    checksum,
    load_market,
    save,
    write_rows,
)

DESIGN = ROOT / "docs/machine_strategy_v2_design"
CODE = [
    "scripts/run_machine_strategy_research.py",
    "scripts/machine_strategy_v2_execution.py",
    "tests/test_machine_strategy_v2_execution.py",
]


def dest(version, stage):
    v = version.replace(".", "_")
    return ROOT / f"docs/machine_strategy_{v}_{stage}"


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def checked_commit(directory, *, message=None):
    path = str((directory / "freeze_manifest.json").relative_to(ROOT))
    sha = checksum(directory / "freeze_manifest.json")
    committed = subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT)
    from hashlib import sha256

    if sha256(committed).hexdigest() != sha:
        raise ValueError("Pre-outcome manifest is not committed")
    commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", path], cwd=ROOT, text=True
    ).strip()
    if (
        message
        and subprocess.check_output(
            ["git", "log", "-1", "--format=%s", commit], cwd=ROOT, text=True
        ).strip()
        != message
    ):
        raise ValueError("Wrong pre-outcome commit")
    return commit


def version_cases(version, cases):
    if version == "v2":
        return cases, []
    specification = read(dest(version, "design") / "VERSION_RULES.json")
    included = []
    excluded = []
    for case in cases:
        entry = float(case["theoretical_entry"])
        stop = float(case["fixed_initial_stop"])
        target = float(case["theoretical_target"])
        cost = (entry + target) * float(FEE + SLIPPAGE)
        edge = abs(target - entry) / cost
        rr = abs(target - entry) / abs(entry - stop)
        reasons = []
        if edge < specification["minimum_edge_cost_ratio"]:
            reasons.append("REJECTED_SCALP_POOR_EDGE_COST_RATIO")
        if rr < specification.get("minimum_structural_R", 0):
            reasons.append("REJECTED_STRUCTURAL_TARGET_INSIDE_ONE_R")
        record = {
            **case,
            "machine_version": version,
            "base_v2_case_id": case["case_id"],
            "expected_edge_cost_ratio": edge,
            "expected_structural_R": rr,
            "version_rule_ids": specification["rule_ids"],
        }
        if reasons:
            excluded.append(
                {
                    "case_id": case["case_id"],
                    "decision_at": case["decision_at"],
                    "reasons": reasons,
                    "edge_cost_ratio": edge,
                    "structural_R": rr,
                }
            )
        else:
            included.append(record)
    return included, excluded


def build_pre(version, output, *, cohort_mode="BACKTEST"):
    if (output / "PREREGISTRATION.json").exists():
        raise ValueError("Existing pre-outcome outputs preserved")
    invariance = original_invariance()
    base_design = verify_machine(DESIGN)
    output.mkdir(parents=True, exist_ok=True)
    market, dataset = load_market()
    if version == "v2":
        cases = []
        audits = []
        for symbol in ("BTCUSDT", "ETHUSDT"):
            records, audit = build_cohort(
                symbol,
                market[symbol],
                mode=cohort_mode,
                progress=lambda s, i, n: print("MACHINE_COHORT", s, i, n, flush=True),
            )
            cases.extend(records)
            audits.append(audit)
        excluded = []
        parents = {base_design["path"]: base_design["sha256"]}
    else:
        vdesign = verify_machine(dest(version, "design"))
        basepre = verify_machine(dest("v2", "pre_outcome"))
        cases, excluded = version_cases(
            version, rows(dest("v2", "pre_outcome") / "FROZEN_CASES.jsonl.gz")
        )
        audits = read(dest("v2", "pre_outcome") / "COHORT_FUNNEL.json")["symbol_audits"]
        parents = {
            base_design["path"]: base_design["sha256"],
            vdesign["path"]: vdesign["sha256"],
            basepre["path"]: basepre["sha256"],
        }
    cases.sort(key=lambda r: (r["decision_at"], r["symbol"], r["case_id"]))
    if len({r["case_id"] for r in cases}) != len(cases) or len(
        {r["physical_idea_id"] for r in cases}
    ) != len(cases):
        raise ValueError("Duplicate canonical machine cases")
    write_rows(output / "FROZEN_CASES.jsonl.gz", cases)
    write_rows(output / "EXCLUDED_VERSION_CASES.jsonl.gz", excluded)
    save(output / "DATASET_VERIFICATION.json", dataset)
    funnel = {
        "version": version,
        "raw_candidates": sum(a["raw_candidates"] for a in audits),
        "allowed_setups": len(cases),
        "excluded_version_rules": len(excluded),
        "symbol_audits": audits,
        "branches": dict(Counter(c["branch"] for c in cases)),
        "deterministic_definition_UNKNOWN": 0,
        "trade_entry_allowed": False,
    }
    save(output / "COHORT_FUNNEL.json", funnel)
    protocol = """# Machine financial preregistration\n\nIndependent machine cases, not exact Original, no shared project risk/position management. Run only the exact committed FROZEN_CASES cohort; all IDs/data/code/geometry frozen before financial outcomes. H1/H4 formation, H1 decision, M15 execution, D1/H4 context. Orders available only from first M15 OPEN at/after decision CLOSE; expire after one H1 cycle. Same physical event/POI never creates duplicate orders. No post-outcome admission reclassification.\n\nPrimary accounting NORMALIZED_R_RESEARCH_MODE_UNROUNDED_THEORETICAL_PRICES: one risk unit per independently evaluated case; prices unrounded, explicit outward/inward relative epsilon 1e-8; no verified exchange tick/qty execution assertion. Gap improvement at observable OPEN is modeled with actual fill-to-fixed-stop price-risk denominator. No dummy tick or qty. Fixed initial stop and full nearest FTA / coincident Range 80/20; no BE. SFP pattern body invalidation at native setup-TF CLOSE.\n\nM15 is finest history. OPEN before extrema. Both SL/FTA in one M15 bar -> WAIT_INTRABAR_ORDER. Wick limit+FTA in entry bar also unordered, regardless apparent outcome. Stop-only wick crossing is causally ordered under registered continuous within-bar path. Unresolved cases excluded from CLOSED primary sample and reported separately; exclusion may bias the resolved sample. No forced EOF liquidation: open filled/order cases censored. Fill and hold times use observed OPEN/completed candle timestamps and bounds.\n\nCosts: entry and exit fee 6bps each; entry and exit proportional price slippage 2bps each, modeled as separate debits. Funding unsupported and excluded, never silently zero; Net is ex-funding. All monetary quantities are risk units, not actual exchange account currency. Counterfactual cost diagnostics 0.5x/1x/2x preset; no selection of strategy on best multiplier.\n\nClosed-case diagnostic equity curve: initial 100 R units, constant 1 R per case, sorted exit time/case ID, no compounding. Drawdown is not simultaneous live portfolio drawdown. Report all metrics, branches/TFs/symbol/direction/year/month, unresolved and censored. Robustness gates from design READINESS_POLICY precede results. Dataset repeated-version retests are development results, not independent holdout validation.\n\nNo LIVE/private APIs. trade_entry_allowed=false.\n"""
    (output / "BACKTEST_PROTOCOL.md").write_text(protocol)
    (output / "EXECUTION_ASSUMPTIONS.md").write_text(
        """# Registered execution assumptions\n\nUNPROVEN_PRICE_ROUNDING_ASSUMPTION: no historical tick rounding; continuous theoretical prices used. Outward/inward epsilon is 1e-8 relative, not inferred historical tick. This research mode is authorized in the current user request and cannot support exchange-executable/live claims.\n\nUNPROVEN_WITHIN_BAR_CONTINUITY_ASSUMPTION: ordered stop-only limit crossings assume a continuous price path between observed extrema. Ambiguous profit/order chronology stays WAIT_INTRABAR_ORDER. No M1/M5 added.\n\nNOT_REQUIRED_FOR_THIS_ACCOUNTING_VIEW: qty_step, minimum_qty, quantity_precision, exchange lot sizing, display price_precision, base/quote currency labels for dimensionless R. Linear price payoff is an explicit theoretical model; historical contract/filter periods remain unverified. No account-sized Net, liquidation, leverage, spread, market impact or actual funding claim.\n"""
    )
    (output / "COST_MODEL.md").write_text(
        "# Cost model\n\nFor signed gross price PnL divided by abs(actual fill-fixed initial stop), fee_R=0.0006*(fill+exit)/risk, slippage_R=0.0002*(fill+exit)/risk. Net_R=gross_R-fee_R-slippage_R. Quantity cancels for this explicitly linear proportional model. Funding unavailable/excluded. Closed-primary costs and known entry fees for all FILLED are separate. Preset cost multipliers: 0.5, 1, 2.\n"
    )
    save(
        output / "PREREGISTRATION.json",
        {
            "version": version,
            "stage": "PRE_OUTCOME",
            "financial_outcomes_computed": False,
            "parents": parents,
            "dataset_sha256": checksum(output / "DATASET_VERIFICATION.json"),
            "frozen_cases_sha256": checksum(output / "FROZEN_CASES.jsonl.gz"),
            "case_ids": [r["case_id"] for r in cases],
            "case_count": len(cases),
            "symbol_scope": ["BTCUSDT", "ETHUSDT"],
            "accounting_mode": ACCOUNTING,
            "historical_exchange_execution_verified": False,
            "fee_each_leg": str(FEE),
            "slippage_each_leg": str(SLIPPAGE),
            "funding": "UNAVAILABLE_EXCLUDED",
            "cost_sensitivity": COST_MULTIPLIERS,
            "initial_equity_R": 100,
            "risk_R_per_independent_case": 1,
            "readiness_policy_sha256": checksum(DESIGN / "READINESS_POLICY.json"),
            "engine_code_sha256": {
                n: checksum(ROOT / n)
                for n in CODE + ["scripts/machine_strategy_v2_core.py"]
            },
            "unproven_price_rounding_assumption": "UNROUNDED_THEORETICAL_PRICES_WITH_EXPLICIT_EPSILON",
            "source_reference_unchanged": invariance,
            "trade_entry_allowed": False,
        },
    )
    print("PRE_OUTCOME_COMPLETE", version, len(cases), flush=True)


def run_result(version, output):
    if (output / "METRICS.json").exists():
        raise ValueError("Existing financial result preserved")
    pre = dest(version, "pre_outcome")
    verify_machine(pre)
    commit = checked_commit(pre)
    prereg = read(pre / "PREREGISTRATION.json")
    for name, sha in prereg["engine_code_sha256"].items():
        if checksum(ROOT / name) != sha:
            raise ValueError("Frozen executable code changed")
    cases = rows(pre / "FROZEN_CASES.jsonl.gz")
    if [r["case_id"] for r in cases] != prereg["case_ids"]:
        raise ValueError("Financial cohort changed")
    market, dataset = load_market()
    if dataset != read(pre / "DATASET_VERIFICATION.json"):
        raise ValueError("Financial dataset changed")
    output.mkdir(parents=True, exist_ok=True)
    starts = {s: [b.start for b in market[s][15]] for s in market}
    results = [
        execute(c, market[c["symbol"]], starts=starts[c["symbol"]]) for c in cases
    ]
    write_rows(output / "ALL_CASE_EXECUTIONS.jsonl.gz", results)
    write_rows(output / "ALL_TRADES.jsonl.gz", [r for r in results if r["filled"]])
    write_rows(output / "CLOSED_TRADES.jsonl.gz", [r for r in results if r["closed"]])
    metrics = stats(results)
    metrics["raw_candidates"] = read(pre / "COHORT_FUNNEL.json")["raw_candidates"]
    metrics["allowed_setups"] = len(cases)
    save(output / "METRICS.json", metrics)
    save(output / "BREAKDOWNS.json", breakdowns(results))
    save(
        output / "RESULT_PROVENANCE.json",
        {
            "version": version,
            "pre_outcome_commit": commit,
            "pre_outcome_manifest_sha256": checksum(pre / "freeze_manifest.json"),
            "dataset_sha256": prereg["dataset_sha256"],
            "exact_case_ids_preserved": True,
            "admission_reclassified_after_outcome": False,
            "financial_outcomes_computed": True,
            "accounting_mode": ACCOUNTING,
            "trade_entry_allowed": False,
        },
    )
    (output / "FINANCIAL_REPORT.md").write_text(
        "# Frozen machine financial result\n\n"
        + json.dumps(metrics, ensure_ascii=False, indent=2)
        + "\n\nSee ALL_CASE_EXECUTIONS/ALL_TRADES/CLOSED_TRADES and BREAKDOWNS for every case, WIN/LOSS and complete groups. Normalized risk units, funding excluded, theoretical unrounded execution; not exact Original or historical exchange-account PnL. Unresolved intrabar exclusions may bias resolved results. No strategy changes after outcomes.\n"
    )
    print("MACHINE_FINANCIAL_COMPLETE", version, json.dumps(metrics), flush=True)


def build_robustness(version, output):
    result = dest(version, "result")
    verify_machine(result)
    checked_commit(result)
    if (output / "ROBUSTNESS.json").exists():
        raise ValueError("Existing robustness preserved")
    trades = rows(result / "ALL_CASE_EXECUTIONS.jsonl.gz")
    metrics = read(result / "METRICS.json")
    groups = read(result / "BREAKDOWNS.json")
    policy = read(DESIGN / "READINESS_POLICY.json")
    closed = [r for r in trades if r["closed"]]
    rolling = []
    for year in (2023, 2024, 2025):
        for quarter in (1, 2, 3, 4):
            subset = [
                r
                for r in trades
                if calendar(r["decision_at"]).year == year
                and (calendar(r["decision_at"]).month - 1) // 3 + 1 == quarter
            ]
            rolling.append({"year": year, "quarter": quarter, "metrics": stats(subset)})
    holds = {
        label: stats([r for r in closed if lo <= r["hold_hours"] < hi])
        for label, lo, hi in (
            ("<1h", 0, 1),
            ("1-4h", 1, 4),
            ("4-24h", 4, 24),
            ("1-7d", 24, 168),
            (">=7d", 168, float("inf")),
        )
    }
    sensitivity = {
        multiplier: stats(trades, cost_multiplier=multiplier)
        for multiplier in COST_MULTIPLIERS
    }
    positive_years = sum(g["Net_R_ex_funding"] > 0 for g in groups["year"].values())
    concentration = {}
    for key in ("symbol", "direction", "branch", "setup_tf", "year"):
        positives = {
            name: max(0, g["Net_R_ex_funding"]) for name, g in groups[key].items()
        }
        concentration[key] = (
            max(positives.values()) / sum(positives.values())
            if sum(positives.values())
            else None
        )
    unresolved_fraction = (
        metrics["intrabar_unresolved"] / metrics["filled"] if metrics["filled"] else 1
    )
    failures = []
    if metrics["CLOSED"] < policy["minimum_closed"]:
        failures.append("INSUFFICIENT_CLOSED_SAMPLE")
    if metrics["PF_net"] is None or metrics["PF_net"] <= 1:
        failures.append("NET_PF_NOT_ABOVE_ONE")
    if metrics["Expectancy_R"] is None or metrics["Expectancy_R"] <= 0:
        failures.append("NONPOSITIVE_NET_EXPECTANCY")
    if metrics["MaxDD_R"] > policy["maximum_closed_return_drawdown_R"]:
        failures.append("EXCESS_CLOSED_RETURN_DRAWDOWN")
    if positive_years < policy["minimum_positive_calendar_years"]:
        failures.append("INSUFFICIENT_POSITIVE_YEARS")
    # Fixed H1 decision and two native setup TFs are not failures due to intentional role model.
    if any(
        v is not None
        and v > float(policy["maximum_single_group_net_positive_profit_share"])
        for k, v in concentration.items()
        if k in ("branch", "year")
    ):
        failures.append("CONCENTRATED_BRANCH_OR_YEAR_PROFIT")
    if unresolved_fraction > float(policy["maximum_intrabar_unresolved_fraction"]):
        failures.append("EXCESS_INTRABAR_UNRESOLVED")
    robustness = {
        "version": version,
        "research_quality_gate": "FAIL" if failures else "PASS",
        "failure_reasons": failures,
        "classification": "INSUFFICIENT_SAMPLE"
        if metrics["CLOSED"] < 200
        else "WEAK"
        if metrics["Expectancy_R"] is None or metrics["Expectancy_R"] <= 0
        else "CONCENTRATED"
        if "CONCENTRATED_BRANCH_OR_YEAR_PROFIT" in failures
        else "UNSTABLE"
        if failures
        else "STABLE_DESCRIPTIVE_RESEARCH",
        "positive_years": positive_years,
        "positive_profit_concentration": concentration,
        "unresolved_fraction": unresolved_fraction,
        "cost_sensitivity": sensitivity,
        "rolling_quarters": rolling,
        "holding_distribution": holds,
        "drawdown_concentration": {
            year: g["MaxDD_R"] for year, g in groups["year"].items()
        },
        "groups_reference": str((result / "BREAKDOWNS.json").relative_to(ROOT)),
        "out_of_sample_validation": False,
        "sample_limit": "Same 2023-2025 frozen data; no independent forward/OOS evidence. Resolved-only results may be affected by unknown intrabar order.",
        "production_execution_gate": "FAIL_UNVERIFIED_TICK_ROUNDING_AND_UNSUPPORTED_FUNDING_EXECUTION",
        "PAPER_TRADING_READY": False,
        "REAL_TRADING_READY": False,
        "trade_entry_allowed": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    save(output / "ROBUSTNESS.json", robustness)
    (output / "ROBUSTNESS_REPORT.md").write_text(
        "# Machine robustness\n\n"
        + json.dumps(robustness, ensure_ascii=False, indent=2)
        + "\n\nNo subgroup/period removed from frozen base result. Cost scenarios are predefined diagnostics; no winner selected. Independent-case drawdown is not exchange portfolio drawdown. Production execution assumptions and forward sample remain unverified.\n"
    )
    print(
        "ROBUSTNESS_COMPLETE",
        version,
        robustness["research_quality_gate"],
        failures,
        flush=True,
    )


PRE_FILES = [
    "FROZEN_CASES.jsonl.gz",
    "EXCLUDED_VERSION_CASES.jsonl.gz",
    "DATASET_VERIFICATION.json",
    "COHORT_FUNNEL.json",
    "BACKTEST_PROTOCOL.md",
    "EXECUTION_ASSUMPTIONS.md",
    "COST_MODEL.md",
    "PREREGISTRATION.json",
]
RESULT_FILES = [
    "ALL_CASE_EXECUTIONS.jsonl.gz",
    "ALL_TRADES.jsonl.gz",
    "CLOSED_TRADES.jsonl.gz",
    "METRICS.json",
    "BREAKDOWNS.json",
    "RESULT_PROVENANCE.json",
    "FINANCIAL_REPORT.md",
]
ROBUST_FILES = ["ROBUSTNESS.json", "ROBUSTNESS_REPORT.md"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", default="v2", choices=["v2", "v2.1", "v2.2"])
    p.add_argument(
        "--stage", required=True, choices=["pre_outcome", "result", "robustness"]
    )
    p.add_argument("--cohort-mode", default="BACKTEST", choices=["BACKTEST", "SHADOW"])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--replay-output", type=Path)
    g.add_argument("--validate-replay", type=Path)
    g.add_argument("--seal", action="store_true")
    g.add_argument("--resume-existing", action="store_true")
    a = p.parse_args()
    directory = dest(a.version, a.stage)
    files = {
        "pre_outcome": PRE_FILES,
        "result": RESULT_FILES,
        "robustness": ROBUST_FILES,
    }[a.stage]
    if a.resume_existing:
        verify_machine(directory)
        original_invariance()
        print("VERIFIED_RESUME MACHINE", a.version, a.stage)
    elif a.validate_replay:
        qa = qa_stage(directory, CODE, a.validate_replay, files, minimum_tests=930)
        (directory / "QA_REPORT.md").write_text(
            f"# Machine {a.version} {a.stage} QA\n\nPASS: {qa['tests']} inherited/new tests; {len(files)} deterministic output files byte-identical. Frozen parent/data/engine/cohort IDs verified. Synthetic/open-gap/limit/dual-hit/EOF/funding and cost identities pass; original source/baseline/audit and all predecessors unchanged. Completed candles/known_at/prefix/future mutation/LIVE rejection regression pass. Full new-file lint, inherited fatal lint, compile and mypy pass. trade_entry_allowed=false.\n"
        )
    elif a.seal:
        parent = (
            DESIGN
            if a.stage == "pre_outcome"
            else dest(a.version, "pre_outcome")
            if a.stage == "result"
            else dest(a.version, "result")
        )
        parents = {
            str((parent / "freeze_manifest.json").relative_to(ROOT)): checksum(
                parent / "freeze_manifest.json"
            )
        }
        if a.stage == "pre_outcome":
            parents.update(read(directory / "PREREGISTRATION.json")["parents"])
        seal_machine(
            directory,
            CODE,
            stage=a.stage,
            version=a.version,
            parents=parents,
            status="FROZEN",
            outcomes=a.stage != "pre_outcome",
        )
    else:
        {
            "pre_outcome": lambda v, o: build_pre(v, o, cohort_mode=a.cohort_mode),
            "result": run_result,
            "robustness": build_robustness,
        }[a.stage](a.version, a.replay_output or directory)


if __name__ == "__main__":
    main()
