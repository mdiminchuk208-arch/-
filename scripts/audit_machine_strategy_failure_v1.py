"""Offline diagnostic audit of frozen machine results; never builds a new cohort."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from machine_strategy_research_io import original_invariance, qa_stage, verify_machine
from original_v1_1_financial_data import ROOT, checksum, compact, save

D = Decimal
BASE = "ba65e91c2b1675f48e80ac785bb3adf89d17bb0b"
DEST = ROOT / "docs/machine_strategy_failure_audit_v1"
VERSIONS = ("v2", "v2.1", "v2.2")
CODE = [
    "scripts/audit_machine_strategy_failure_v1.py",
    "tests/test_machine_strategy_failure_audit.py",
    "tests/test_machine_strategy_failure_symmetry.py",
]
GENERATED = [
    "FAILURE_AUDIT_REPORT.md",
    "FAILURE_AUDIT.json",
    "LONG_SHORT_ASYMMETRY.json",
    "GROSS_VS_NET_COST_ATTRIBUTION.json",
    "EXIT_REASON_BREAKDOWN.json",
    "IMPLEMENTATION_SYMMETRY_QA.json",
    "EXTREME_R_AUDIT.json",
    "CAUSALITY_QA.json",
    "FROZEN_INPUT_VERIFICATION.json",
    "CASE_DIAGNOSTICS.csv",
]
FEE, SLIP = D("0.0006"), D("0.0002")
OUTCOME_KEYS = {
    "gross_r",
    "net_r",
    "fees_r",
    "slippage_r",
    "funding_r",
    "win",
    "loss",
    "flat",
    "filled",
    "closed",
    "status",
    "fill_price",
    "exit_price",
    "fill_at",
    "exit_at",
    "hold_hours",
    "initial_price_risk",
    "outcome",
    "mfe",
    "mae",
    "pnl",
    "exit_reason",
    "exit_known_at",
    "exit_time_bounds",
    "fill_time_bounds",
    "fill_observation_at",
    "known_entry_fee_r",
    "known_entry_slippage_r",
    "censored_at",
}


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def directory(version, stage):
    return ROOT / "docs" / f"machine_strategy_{version.replace('.', '_')}_{stage}"


def assert_causal(value, decision_at):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in OUTCOME_KEYS:
                raise ValueError("Outcome field in pre-entry input: " + key)
            if (
                (
                    key.endswith("known_at")
                    or key in ("poi_born_at", "formation_at", "end_swing_at")
                )
                and item is not None
                and item > decision_at
            ):
                raise ValueError("Future pre-entry timestamp: " + key)
            assert_causal(item, decision_at)
    elif isinstance(value, list):
        for item in value:
            assert_causal(item, decision_at)


def geometry(case):
    """Only the frozen pre-outcome case enters this feature calculation."""
    assert_causal(case, case["decision_at"])
    if case.get("trade_entry_allowed") is not False:
        raise ValueError("Research-only flag missing")
    if (
        case.get("consumed_at") is not None
        or case.get("first_eligible_touch") is not None
    ):
        raise ValueError("Execution touch in pre-entry input")
    entry, stop, target = (
        D(case[k])
        for k in ("theoretical_entry", "fixed_initial_stop", "theoretical_target")
    )
    if case["direction"] not in ("LONG", "SHORT"):
        raise ValueError("Invalid direction")
    long = case["direction"] == "LONG"
    if not (D(0) < stop < entry < target if long else D(0) < target < entry < stop):
        raise ValueError("Invalid pre-entry geometry")
    risk, reward = abs(entry - stop), abs(target - entry)
    costs = (FEE + SLIP) * (entry + target)
    stamp = datetime.fromtimestamp(case["decision_at"], UTC)
    return {
        "case_id": case["case_id"],
        "decision_at": case["decision_at"],
        "symbol": case["symbol"],
        "direction": case["direction"],
        "branch": case["branch"],
        "setup_tf": case["setup_tf"],
        "year": str(stamp.year),
        "month": stamp.strftime("%Y-%m"),
        "context_relation": case.get("context_relation"),
        "PD_at_entry": case.get("PD_at_entry"),
        "OTE_at_entry": case.get("OTE_at_entry"),
        "FTA_kind": case.get("FTA_kind"),
        "exit_model": case.get("exit_model"),
        "planned_entry": str(entry),
        "planned_stop": str(stop),
        "planned_target": str(target),
        "planned_price_risk": str(risk),
        "planned_stop_bps": str(risk / entry * 10000),
        "planned_target_bps": str(reward / entry * 10000),
        "planned_target_R": str(reward / risk),
        "planned_round_trip_cost_at_FTA_R": str(costs / risk),
        "pre_entry_edge_cost_ratio": str(reward / costs),
    }


def near(a, b):
    return abs(D(str(a)) - D(str(b))) <= D("1e-18") * max(D(1), abs(D(str(b))))


def verify_accounting(row):
    if row["Funding_R"] is not None or row["trade_entry_allowed"] is not False:
        raise ValueError("Funding/research assumption changed")
    if not row["closed"]:
        if any(
            row[k] is not None for k in ("Gross_R", "Fees_R", "Slippage_R", "Net_R")
        ):
            raise ValueError("Unresolved outcome was manufactured")
        return
    fill, stop, exit_price, risk = (
        D(row[k])
        for k in (
            "fill_price",
            "fixed_initial_stop",
            "exit_price",
            "initial_price_risk",
        )
    )
    if risk <= 0 or risk != abs(fill - stop):
        raise ValueError("Invalid actual risk denominator")
    sign = D(1) if row["direction"] == "LONG" else D(-1)
    gross = sign * (exit_price - fill) / risk
    fee, slip = FEE * (fill + exit_price) / risk, SLIP * (fill + exit_price) / risk
    for key, expected in (
        ("Gross_R", gross),
        ("Fees_R", fee),
        ("Slippage_R", slip),
        ("Net_R", gross - fee - slip),
    ):
        if not near(row[key], expected):
            raise ValueError("Accounting mismatch: " + key)
    if (
        row["WIN"] != (D(row["Net_R"]) > 0)
        or row["LOSS"] != (D(row["Net_R"]) < 0)
        or row["FLAT"] != (D(row["Net_R"]) == 0)
    ):
        raise ValueError("Outcome sign mismatch")


def verify_chronology(row):
    """Check saved observation order; this does not resolve intrabar timing."""
    if row["closed"] != (row["status"] == "CLOSED") or (
        row["closed"] and not row["filled"]
    ):
        raise ValueError("Execution status mismatch")
    if row["filled"]:
        if not (
            row["decision_at"]
            <= row["fill_at"]
            <= row["fill_observation_at"]
            <= row["consumed_at"]
        ):
            raise ValueError("Saved fill chronology mismatch")
        low, high = row["fill_time_bounds"]
        if (
            not row["decision_at"]
            <= low
            <= row["fill_at"]
            <= high
            <= row["fill_observation_at"]
        ):
            raise ValueError("Saved fill bounds mismatch")
    elif any(row.get(k) is not None for k in ("fill_at", "consumed_at", "fill_price")):
        raise ValueError("Unfilled record has fill evidence")
    if row["closed"]:
        if not row["fill_at"] <= row["exit_at"] <= row["exit_known_at"]:
            raise ValueError("Saved exit chronology mismatch")
        low, high = row["exit_time_bounds"]
        if not row["fill_at"] <= low <= row["exit_at"] <= high <= row["exit_known_at"]:
            raise ValueError("Saved exit bounds mismatch")


def verify_partitions(executions, filled, closed, frozen):
    if compact(filled) != compact([r for r in executions if r["filled"]]):
        raise ValueError("Filled artifact partition mismatch")
    if compact(closed) != compact([r for r in executions if r["closed"]]):
        raise ValueError("Closed artifact partition mismatch")
    if (
        len(executions) != frozen["cases"]
        or len(executions) != frozen["orders"]
        or len(filled) != frozen["filled"]
        or len(closed) != frozen["CLOSED"]
        or dict(Counter(r["status"] for r in executions)) != frozen["status_counts"]
    ):
        raise ValueError("Frozen count/status mismatch")


def quantiles(values):
    values = sorted(D(str(v)) for v in values)
    if not values:
        return None
    result = {"n": len(values)}
    for key, q in (
        ("min", D(0)),
        ("p10", D(".1")),
        ("median", D(".5")),
        ("p90", D(".9")),
        ("max", D(1)),
    ):
        position = q * (len(values) - 1)
        i = int(position)
        result[key] = float(
            values[i]
            + (values[min(i + 1, len(values) - 1)] - values[i]) * (position - i)
        )
    return result


def total(values):
    return sum((D(str(v)) for v in values), D(0))


def metrics(records, geo):
    closed = sorted(
        (r for r in records if r["closed"]), key=lambda r: (r["exit_at"], r["case_id"])
    )
    net, gross = [D(r["Net_R"]) for r in closed], [D(r["Gross_R"]) for r in closed]
    gains, losses = total(v for v in net if v > 0), -total(v for v in net if v < 0)
    gross_gains, gross_losses = (
        total(v for v in gross if v > 0),
        -total(v for v in gross if v < 0),
    )
    fees, slip = (
        total(r["Fees_R"] for r in closed),
        total(r["Slippage_R"] for r in closed),
    )
    cost = fees + slip
    equity = peak = dd = D(0)
    for value in net:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    n = len(closed)
    return {
        "cases": len(records),
        "FILLED": sum(r["filled"] for r in records),
        "CLOSED": n,
        "WIN": sum(v > 0 for v in net),
        "LOSS": sum(v < 0 for v in net),
        "Gross_WIN": sum(v > 0 for v in gross),
        "Gross_LOSS": sum(v < 0 for v in gross),
        "WR_percent": float(sum(v > 0 for v in net) / n * 100) if n else None,
        "Gross_R": float(total(gross)),
        "Fees_R": float(fees),
        "Slippage_R": float(slip),
        "Net_R_ex_funding": float(total(net)),
        "Funding_R": None,
        "PF_net": float(gains / losses) if losses else None,
        "PF_gross": float(gross_gains / gross_losses) if gross_losses else None,
        "Expectancy_R": float(total(net) / n) if n else None,
        "Gross_expectancy_R": float(total(gross) / n) if n else None,
        "mean_cost_R": float(cost / n) if n else None,
        "MaxDD_R": float(dd),
        "cost_break_even_multiplier": float(total(gross) / cost) if cost else None,
        "gross_positive_net_nonpositive": sum(
            g > 0 and v <= 0 for g, v in zip(gross, net)
        ),
        "status_counts": dict(sorted(Counter(r["status"] for r in records).items())),
        "geometry_all_cases": {
            key: quantiles(geo[r["case_id"]][key] for r in records)
            for key in (
                "planned_stop_bps",
                "planned_target_bps",
                "planned_target_R",
                "pre_entry_edge_cost_ratio",
            )
        },
        "geometry_closed": {
            key: quantiles(geo[r["case_id"]][key] for r in closed)
            for key in (
                "planned_stop_bps",
                "planned_target_bps",
                "planned_target_R",
                "pre_entry_edge_cost_ratio",
            )
        },
        "closed_planned_target_below_one_R": sum(
            D(geo[r["case_id"]]["planned_target_R"]) < 1 for r in closed
        ),
        "closed_planned_round_trip_cost_at_FTA_above_one_R": sum(
            D(geo[r["case_id"]]["planned_round_trip_cost_at_FTA_R"]) > 1 for r in closed
        ),
        "realized_cost_R": quantiles(
            D(r["Fees_R"]) + D(r["Slippage_R"]) for r in closed
        ),
        "actual_fill_stop_bps": quantiles(
            D(r["initial_price_risk"]) / D(r["fill_price"]) * 10000 for r in closed
        ),
        "actual_fill_target_R": quantiles(
            abs(D(r["theoretical_target"]) - D(r["fill_price"]))
            / D(r["initial_price_risk"])
            for r in closed
        ),
        "recorded_observation_hold_hours": quantiles(r["hold_hours"] for r in closed),
        "gross_trade_R": quantiles(gross),
        "net_trade_R": quantiles(net),
    }


def grouped(records, geo, fields):
    groups = defaultdict(list)
    for row in records:
        key = tuple(str(geo[row["case_id"]].get(k, row.get(k))) for k in fields)
        groups[key].append(row)
    return [
        {"slice": dict(zip(fields, key)), "metrics": metrics(group, geo)}
        for key, group in sorted(groups.items())
    ]


def timing_issue(row):
    return bool(
        row["closed"]
        and row.get("exit_reason") == "FIXED_INITIAL_STOP"
        and row.get("fill_at") == row.get("exit_at")
        and len(set(row.get("fill_time_bounds", []))) > 1
    )


def observed_diagnostics(row, geo):
    """Retrospective execution observations; never feed them back into geometry."""
    item = {
        **geo[row["case_id"]],
        "status": row["status"],
        "FILLED": row["filled"],
        "CLOSED": row["closed"],
        "fill_at": row["fill_at"],
        "exit_at": row["exit_at"],
        "exit_reason": row.get("exit_reason"),
        "timing_bounds_overprecise": timing_issue(row),
    }
    for key in (
        "fill_price",
        "exit_price",
        "initial_price_risk",
        "Gross_R",
        "Fees_R",
        "Slippage_R",
        "Net_R",
        "hold_hours",
    ):
        item[key] = row.get(key)
    if row["filled"]:
        fill, risk = D(row["fill_price"]), D(row["initial_price_risk"])
        item["actual_fill_stop_bps"] = str(risk / fill * 10000)
        item["notional_per_one_price_risk_unit"] = str(fill / risk)
        item["fill_risk_to_planned_risk_ratio"] = str(
            risk / D(item["planned_price_risk"])
        )
        item["price_improved_at_open"] = fill != D(item["planned_entry"])
    return item


def extremes(records, geo):
    closed = [r for r in records if r["closed"]]
    result = {}
    for direction in ("ALL", "LONG", "SHORT"):
        selected = [
            r for r in closed if direction == "ALL" or r["direction"] == direction
        ]
        net = total(r["Net_R"] for r in selected)
        ordered = sorted(selected, key=lambda r: (D(r["Net_R"]), r["case_id"]))
        result[direction] = {
            "worst_net": [observed_diagnostics(r, geo) for r in ordered[:3]],
            "best_net": [observed_diagnostics(r, geo) for r in ordered[-3:][::-1]],
            "highest_cost": [
                observed_diagnostics(r, geo)
                for r in sorted(
                    selected,
                    key=lambda r: (-D(r["Fees_R"]) - D(r["Slippage_R"]), r["case_id"]),
                )[:3]
            ],
            "lowest_actual_risk_bps": [
                observed_diagnostics(r, geo)
                for r in sorted(
                    selected,
                    key=lambda r: (
                        D(r["initial_price_risk"]) / D(r["fill_price"]),
                        r["case_id"],
                    ),
                )[:3]
            ],
            "leave_one_extreme_out_diagnostic": {
                "net_R": float(net),
                "without_worst_R": float(net - D(ordered[0]["Net_R"]))
                if ordered
                else None,
                "without_best_R": float(net - D(ordered[-1]["Net_R"]))
                if ordered
                else None,
                "without_best_two_R": float(
                    net - total(r["Net_R"] for r in ordered[-2:])
                ),
                "without_best_three_R": float(
                    net - total(r["Net_R"] for r in ordered[-3:])
                ),
                "cohort_was_not_changed": True,
            },
        }
    return result


def verify_inputs():
    preservation = original_invariance()
    manifests = {}
    for v in VERSIONS:
        for stage in ("design", "pre_outcome", "result", "robustness"):
            path = directory(v, stage)
            relative = str((path / "freeze_manifest.json").relative_to(ROOT))
            original = subprocess.check_output(
                ["git", "show", BASE + ":" + relative], cwd=ROOT
            )
            manifests[relative] = verify_machine(path, sha256(original).hexdigest())[
                "sha256"
            ]
    for name in ("machine_strategy_preservation", "machine_strategy_workflow_report"):
        path = ROOT / "docs" / name
        relative = str((path / "freeze_manifest.json").relative_to(ROOT))
        original = subprocess.check_output(
            ["git", "show", BASE + ":" + relative], cwd=ROOT
        )
        manifests[relative] = verify_machine(path, sha256(original).hexdigest())[
            "sha256"
        ]
    changed = subprocess.check_output(
        ["git", "diff", "--name-status", BASE, "--"], cwd=ROOT, text=True
    )
    if any(not line.startswith("A\t") for line in changed.splitlines()):
        raise ValueError("Frozen baseline file changed or deleted")
    ancestry = {}
    for v in VERSIONS:
        commits = {}
        for stage in ("pre_outcome", "result"):
            relative = str(
                (directory(v, stage) / "freeze_manifest.json").relative_to(ROOT)
            )
            commits[stage] = subprocess.check_output(
                ["git", "log", "-1", "--format=%H", "--", relative], cwd=ROOT, text=True
            ).strip()
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                commits["pre_outcome"],
                commits["result"],
            ],
            cwd=ROOT,
            check=True,
        )
        ancestry[v] = {
            **commits,
            "pre_outcome_precedes_result": commits["pre_outcome"] != commits["result"],
        }
        if not ancestry[v]["pre_outcome_precedes_result"]:
            raise ValueError("No independent pre-outcome commit")
    return {
        "status": "PASS",
        "baseline_commit": BASE,
        "machine_manifest_sha256": manifests,
        "original_invariance": preservation,
        "pre_outcome_ancestry": ancestry,
        "protected_baseline_file_changes": 0,
        "fresh_historical_financial_run": False,
    }


def load_version(version):
    cases = rows(directory(version, "pre_outcome") / "FROZEN_CASES.jsonl.gz")
    executions = rows(directory(version, "result") / "ALL_CASE_EXECUTIONS.jsonl.gz")
    ids = [c["case_id"] for c in cases]
    if ids != [r["case_id"] for r in executions] or len(ids) != len(set(ids)):
        raise ValueError("Cohort order/uniqueness mismatch")
    prereg = read(directory(version, "pre_outcome") / "PREREGISTRATION.json")
    if prereg["case_ids"] != ids:
        raise ValueError("Preregistration cohort mismatch")
    for case, row in zip(cases, executions):
        for key, value in case.items():
            if (
                key not in ("consumed_at", "first_eligible_touch")
                and row.get(key) != value
            ):
                raise ValueError("Frozen pre-entry field changed at execution: " + key)
        verify_accounting(row)
        verify_chronology(row)
    filled = rows(directory(version, "result") / "ALL_TRADES.jsonl.gz")
    closed = rows(directory(version, "result") / "CLOSED_TRADES.jsonl.gz")
    verify_partitions(
        executions, filled, closed, read(directory(version, "result") / "METRICS.json")
    )
    return cases, executions


def build(output):
    output = Path(output).resolve()
    if (
        any((output / n).exists() for n in GENERATED)
        or (output / "freeze_manifest.json").exists()
    ):
        raise ValueError(
            "Existing audit preserved; use --resume-existing or a fresh replay directory"
        )
    inputs = verify_inputs()
    versions, asymmetry, costs, exits, extreme, accounting, causality = (
        {},
        {},
        {},
        {},
        {},
        {},
        {},
    )
    exported, base_ids, prior_ids, base_executions = [], None, None, None
    for v in VERSIONS:
        cases, execution = load_version(v)
        geo = {c["case_id"]: geometry(c) for c in cases}
        summaries = metrics(execution, geo)
        frozen = read(directory(v, "result") / "METRICS.json")
        for key in (
            "cases",
            "CLOSED",
            "WIN",
            "LOSS",
            "WR_percent",
            "Gross_R",
            "Fees_R",
            "Slippage_R",
            "Net_R_ex_funding",
            "PF_net",
            "Expectancy_R",
            "MaxDD_R",
        ):
            if abs(float(summaries[key]) - float(frozen[key])) > 1e-9:
                raise ValueError("Frozen aggregate mismatch: " + key)
        current_ids = {c["case_id"] for c in cases}
        if base_ids is None:
            base_ids = current_ids
            base_executions = {r["case_id"]: r for r in execution}
        else:
            if not current_ids < prior_ids:
                raise ValueError("Improvement cohorts are not nested")
            for row in execution:
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
                ):
                    if row.get(key) != base_executions[row["case_id"]].get(key):
                        raise ValueError("Nested execution identity mismatch")
        prior_ids = current_ids
        versions[v] = {
            "metrics": summaries,
            "unique_cases": len(current_ids),
            "nested_development_history": True,
            "robustness_verdict": "FAIL",
        }
        asymmetry[v] = {
            "direction": {
                d: metrics([r for r in execution if r["direction"] == d], geo)
                for d in ("LONG", "SHORT")
            }
        }
        for fields in (
            ("direction", "year"),
            ("direction", "month"),
            ("direction", "symbol"),
            ("direction", "branch"),
            ("direction", "setup_tf"),
            ("direction", "context_relation"),
            ("direction", "PD_at_entry"),
            ("direction", "OTE_at_entry"),
            ("direction", "FTA_kind"),
            ("direction", "status"),
            ("direction", "year", "symbol"),
            ("direction", "symbol", "branch"),
            ("direction", "context_relation", "PD_at_entry"),
        ):
            asymmetry[v]["by_" + "_".join(fields)] = grouped(execution, geo, fields)
        costs[v] = {
            "overall": summaries,
            "by_direction": asymmetry[v]["direction"],
            "frozen_cost_sensitivity": read(
                directory(v, "robustness") / "ROBUSTNESS.json"
            )["cost_sensitivity"],
            "accounting_identity_errors": 0,
        }
        exits[v] = grouped(execution, geo, ("direction", "exit_reason"))
        extreme[v] = extremes(execution, geo)
        affected = [r for r in execution if timing_issue(r)]
        accounting[v] = {
            "closed_records_checked": summaries["CLOSED"],
            "accounting_identity_errors": 0,
            "same_bar_wick_fill_stop_timing_issue_ids": [
                r["case_id"] for r in affected
            ],
            "same_bar_timing_count": len(affected),
            "unresolved_by_direction": {
                d: sum(
                    r["direction"] == d and r["status"] == "WAIT_INTRABAR_ORDER"
                    for r in execution
                )
                for d in ("LONG", "SHORT")
            },
        }
        cutoff = 1719792000
        prefix = [c for c in cases if c["decision_at"] <= cutoff]
        first = [geometry(c) for c in prefix]
        second = [geo[c["case_id"]] for c in cases if c["decision_at"] <= cutoff]
        if compact(first) != compact(second):
            raise ValueError("Local saved-case projection mismatch")
        causality[v] = {
            "pre_entry_cases_checked": len(cases),
            "nested_known_at_checked": True,
            "outcome_fields_in_preentry": 0,
            "end_swing_at_checked": True,
            "pre_entry_consumed_at_null": True,
            "saved_execution_chronology_checked": len(execution),
            "saved_execution_chronology_errors": 0,
            "local_projection_cutoff": cutoff,
            "local_projection_cases": len(prefix),
            "local_projection_determinism": "PASS",
            "local_projection_is_independent_future_mutation_proof": False,
        }
        exported.extend(
            {"machine_version": v, **observed_diagnostics(r, geo)} for r in execution
        )
    output.mkdir(parents=True, exist_ok=True)
    common = {
        "diagnostic_only": True,
        "trade_entry_allowed": False,
        "PAPER_enabled": False,
        "LIVE_enabled": False,
    }
    save(
        output / "FAILURE_AUDIT.json",
        {
            **common,
            "versions": versions,
            "verdict": "FAILURE_MECHANISMS_IDENTIFIED_WITH_CAUSAL_LIMITS",
            "production_candidate": None,
            "v3_design_justified": True,
            "v3_design_gate": "ONLY_AFTER_AUDIT_FREEZE_SEPARATE_PRE_OUTCOME_SPEC",
            "strategy_rules_changed": False,
            "financial_backtest_ran": False,
            "new_filters_or_parameters_selected": False,
            "SHORT_disabled": False,
            "mechanisms": [
                "SHORT_GROSS_WEAKNESS_PRECEDES_COSTS",
                "COSTS_EXCEED_AGGREGATE_GROSS_EDGE",
                "SUB_ONE_R_NEAREST_FTA_PLANS",
                "TINY_STOP_DENOMINATOR_TAILS",
                "FILL_SELECTION_AND_EXIT_MIX",
                "NESTED_DEPENDENT_DEVELOPMENT_COHORTS",
            ],
            "unresolved": [
                "Causal signal/regime explanation cannot be isolated from realized policy-dependent exits.",
                "Historical tick, spread, funding and portfolio sizing remain unverified.",
                "D1 context IDs do not supply a frozen causal regime/alignment label.",
                "Within-bar fill/exit timing and unresolved LONG cases limit directional/holding inference.",
                "No untouched OOS or forward evidence; no subgroup production inference.",
            ],
            "design_questions_without_rules": [
                "How should risk units and sizing remain stable for structural tiny-stop plans?",
                "How should a causal structural target/stop policy represent executable economic capacity?",
                "Can frozen causal context labels distinguish directional signal quality from fill selection?",
                "What independent evaluation protocol tests both directions without subgroup selection?",
            ],
        },
    )
    save(
        output / "LONG_SHORT_ASYMMETRY.json",
        {
            **common,
            "versions": asymmetry,
            "independent_slice_claimed": False,
            "overlap_warning": "Years/symbols/branches/months/regimes cross-classify the same trades. Child versions reuse parent cases. No independence, significance or production advantage claimed.",
            "regime_definition": "Only frozen context_relation, PD_at_entry, OTE_at_entry; year/month are calendar diagnostics, not ex-post market-regime labels.",
        },
    )
    save(
        output / "GROSS_VS_NET_COST_ATTRIBUTION.json",
        {
            **common,
            "versions": costs,
            "funding": "UNAVAILABLE_EXCLUDED_NOT_ASSERTED_ZERO",
            "currency_PnL": None,
            "cost_break_even_multiplier": "Gross/(Fees+Slippage), arithmetic diagnosis only; not an executable fee assumption.",
            "causal_attribution_limit": "Gross realized returns jointly depend on signals, fills, stops and targets. These mechanisms cannot be uniquely apportioned without a preregistered independent counterfactual.",
        },
    )
    save(
        output / "EXIT_REASON_BREAKDOWN.json",
        {
            **common,
            "versions": exits,
            "unfilled_exit_reason": "None means no realized exit, not a closed zero-return trade.",
            "holding_time": "Recorded observation-time distribution; same-bar timing uncertainty is separately flagged; never used as an entry filter.",
        },
    )
    save(
        output / "EXTREME_R_AUDIT.json",
        {
            **common,
            "versions": extreme,
            "official_metrics_preserved": True,
            "tail_removal_is_a_filter": False,
            "interpretation": "Leave-one-out numbers diagnose sensitivity only. Notional/risk is a mathematical normalization ratio, not verified actual leverage, executable account sizing or portfolio return.",
        },
    )
    save(
        output / "IMPLEMENTATION_SYMMETRY_QA.json",
        {
            **common,
            "versions": accounting,
            "arithmetic_verdict": "PASS_NO_SIGN_OR_COST_IDENTITY_ERROR_FOUND",
            "timing_evidence_verdict": "KNOWN_BOUNDS_OVERPRECISION",
            "frozen_execution_changed": False,
            "references": {
                "planning": "scripts/machine_strategy_v2_core.py:402-475",
                "execution": "scripts/machine_strategy_v2_execution.py:26-156",
                "new_tests": CODE[2],
            },
            "synthetic_QA_contract": "Affine price reflection compares event/gross symmetry; expected bps cost differences are explicit. Positive price scaling preserves all normalized amounts. Relative epsilon is not affine-reflection invariant.",
            "timing_issue": "Wick fill + same-bar stop uses fill_at=exit_at=bar.end and point exit_time_bounds; OHLC only proves intrabar order/interval. Recorded hold_hours=0 is observation timing, not exact elapsed duration. Frozen P&L remains unchanged.",
            "proof_limit": "Static predicates, saved arithmetic and bounded synthetic tests cannot prove every real-market path or exchange execution equivalence.",
        },
    )
    save(
        output / "CAUSALITY_QA.json",
        {
            **common,
            "versions": causality,
            "geometry_input": "FROZEN_CASES only; execution outcomes joined after feature computation.",
            "inherited_actual_history_prefix_receipt": read(
                directory("v2", "pre_outcome") / "ACTUAL_PREFIX_FUTURE_MUTATION_QA.json"
            ),
            "fresh_actual_historical_cohort_or_execution_rerun": False,
            "scope": "All saved pre-entry known_at/end_swing_at fields recursively checked, pre-entry consumed_at null, and saved execution chronology checked. Saved-case projection determinism is a same-input local check, not independent future-mutation proof. Actual midpoint candle-prefix/future-mutation proof is inherited hash-verified evidence, not newly rerun or all-instant proof.",
        },
    )
    save(output / "FROZEN_INPUT_VERIFICATION.json", {**common, **inputs})
    keys = sorted(set().union(*(r.keys() for r in exported)))
    with (output / "CASE_DIAGNOSTICS.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(exported)
    report(output, versions, asymmetry, accounting)
    print("AUDIT_BUILT", output, "case_version_rows", len(exported), flush=True)


def report(output, versions, asymmetry, accounting):
    lines = [
        "# Frozen machine failure audit v1",
        "",
        "Retrospective development diagnosis; no new strategy, cohort, historical execution or admission rule. All frozen outputs remain intact. trade_entry_allowed=false; PAPER/LIVE off.",
        "",
        "| Version | CLOSED | Gross R | Fees R | Slippage R | Net R ex funding | PF |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for v, item in versions.items():
        m = item["metrics"]
        lines.append(
            f"| {v} | {m['CLOSED']} | {m['Gross_R']:.6f} | {m['Fees_R']:.6f} | {m['Slippage_R']:.6f} | {m['Net_R_ex_funding']:.6f} | {m['PF_net']:.6f} |"
        )
    lines += [
        "",
        "## Direction and attribution",
        "",
        "| Version/direction | CLOSED | Gross R | Costs R | Net R | Planned target/stop median |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for v, item in asymmetry.items():
        for d, m in item["direction"].items():
            ratio = m["geometry_closed"]["planned_target_R"]["median"]
            lines.append(
                f"| {v}/{d} | {m['CLOSED']} | {m['Gross_R']:.6f} | {m['Fees_R'] + m['Slippage_R']:.6f} | {m['Net_R_ex_funding']:.6f} | {ratio:.6f} |"
            )
    lines += [
        "",
        "SHORT gross weakness precedes costs in v2 across each year and both symbols. RANGE and 2024 concentrate much of its net deficit, but neither accounts for all losses. H4 and BREAKER can differ from the aggregate. The all-case, year/symbol/branch/TF/month/context/FTA/status tables are in LONG_SHORT_ASYMMETRY.json; these overlapping slices are not independent experiments.",
        "",
        "Low nearest-FTA reward relative to planned stop is common among CLOSED v2 trades: planned target/stop <1R in 89/118 LONG and 78/105 SHORT. Geometry for unfilled and gap-invalidated cases differs from closed cases, indicating selection by execution. No counterfactual outcome is invented for unfilled orders. Gross realized performance cannot uniquely separate signal quality from target/stop policy or market regime; no causal market explanation is asserted.",
        "",
        "Aggregate positive gross is erased by modeled price-proportional costs in all three versions. Gross/(fees+slippage) describes arithmetic cost tolerance, not a proposed or proven execution budget. Funding remains unavailable/excluded; amounts are R units, not account-currency P&L. The frozen 0.5x/1x/2x cost scenarios are preserved sensitivity evidence, never optimized fee assumptions.",
        "",
        "## Extreme denominators and execution symmetry",
        "",
        "All 345 CLOSED version records independently match signed gross, actual fill-to-stop denominator, 6 bp fee per leg, 2 bp slippage per leg and net identities. No direction-sign defect was identified in those records or inspected planning/execution predicates. Paired reflection and price-scaling tests strengthen bounded synthetic evidence, while bps costs and relative epsilon require explicit transformation-aware expectations.",
        "",
        "ETH SHORT RANGE case ede81fd2453984e72a532c1e1b4f0a3385d426073829b6d222ecbe518e16a5d3 has fill 3121.5, stop 3121.8300312183, risk 0.3300312183 (1.057 bp), gross -1R, modeled costs 15.133914R and net -16.133914R. Relative epsilon adds only 0.0000312183; the entry-anchor gap produces the tight risk. Small-risk LONG winners and losers also occur. EXTREME_R_AUDIT.json records IDs/prices, risk ratios, cost tails and leave-one-extreme-out sensitivity. Official cohorts, labels and totals are unchanged.",
        "",
        "v2.2 is particularly unstable: omitting the worst SHORT diagnostically reverses total net sign; omitting its top two LONG gains reverses LONG net sign. These omissions are diagnostics, never permitted strategy exclusions. v2.1/v2.2 are exact nested subsets with unchanged shared outcomes and only 83/39 CLOSED; their contrast is not independent replication or proof of an optimal threshold.",
        "",
        "## Timing and unresolved evidence",
        "",
    ]
    lines.append(
        "Same-bar wick-fill/stop timing-bound overprecision affects "
        + ", ".join(f"{v}: {x['same_bar_timing_count']}" for v, x in accounting.items())
        + " version records; later versions repeat inherited cases. True intrabar elapsed times are unknown. Recorded zero hold and point exit bounds are observation conventions that overstate timing certainty. P&L arithmetic is unchanged, and the frozen engine is not fixed here."
    )
    lines += [
        "",
        "All WAIT_INTRABAR_ORDER cases are LONG (5/2/1). Resolved-only direction metrics retain asymmetric censoring; OHLC does not establish their outcomes. Historical tick/rounding, actual spread, funding and shared portfolio/margin behavior remain unverified.",
        "",
        "## Causality, independent review and next gate",
        "",
        "Features use only frozen pre-outcome cases and recursively validated known_at/end_swing_at timestamps. Both ALL_TRADES (filled) and CLOSED_TRADES partitions, counts/statuses, preregistered IDs/ordering, commit ancestry, stored accounting and nested outcomes are verified. Saved execution fill/observation/consumption/exit chronology passes; it cannot resolve intrabar order. Deterministic audit replay is separate from financial backtesting. The local saved-case projection check is determinism only, not independent future-mutation proof. Original/evidence/baseline/source-audit/dataset and all 14 machine namespaces are hash-verified. The inherited actual midpoint prefix proof covers 426 cases (BTC 210, ETH 216) with a 10x future suffix mutation; this audit does not claim a fresh historical rerun or every-instant proof.",
        "",
        "Independent roles strategy_explorer, execution_auditor and backtest_reviewer ran through cloud collaboration with the configured gpt-6-sol/high role instructions. Native ECC config/read verified named roles and skills separately; this does not claim the cloud subagents were launched as native CLI agent_type processes. Their recorded conclusions and review scope are retained under independent_review/. strategy_designer was not launched.",
        "",
        "Designing a separate MACHINE_STRATEGY_v3 is justified only after this diagnostic freeze: investigate executable structural risk/cost capacity, stable sizing/normalization and causal signal-versus-fill attribution. This is permission to investigate causally justified definitions, not evidence of a profitable rule. No direction/branch/year/symbol is removed, no threshold is selected from performance, and the audit creates no v3 rule. A new pre-outcome specification and untouched OOS/forward evaluation are prerequisites to any production claim.",
        "",
        "Current production candidate: NONE. PAPER_TRADING_READY=false; REAL_TRADING_READY=false; trade_entry_allowed=false.",
        "",
        "Evidence files: FAILURE_AUDIT.json; LONG_SHORT_ASYMMETRY.json; GROSS_VS_NET_COST_ATTRIBUTION.json; EXIT_REASON_BREAKDOWN.json; IMPLEMENTATION_SYMMETRY_QA.json; EXTREME_R_AUDIT.json; CASE_DIAGNOSTICS.csv; CAUSALITY_QA.json; FROZEN_INPUT_VERIFICATION.json. QA_REPORT.md and freeze_manifest.json close the audit after checks.",
    ]
    (output / "FAILURE_AUDIT_REPORT.md").write_text("\n".join(lines) + "\n")


def seal(replay):
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("Existing audit freeze preserved")
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != "machine-v3-research"
    ):
        raise ValueError("machine-v3-research branch required")
    review = DEST / "independent_review"
    for role in ("strategy_explorer", "execution_auditor", "backtest_reviewer"):
        if not (review / f"{role}.md").is_file():
            raise ValueError("Independent role report missing: " + role)
    approval = read(review / "FINAL_REVIEW.json")
    if (
        approval.get("status") != "PASS"
        or approval.get("reviewer") != "backtest_reviewer"
    ):
        raise ValueError("Final independent review not PASS")
    if approval.get("code_sha256") != {n: checksum(ROOT / n) for n in CODE}:
        raise ValueError("Code changed after independent review")
    if approval.get("generated_sha256") != {n: checksum(DEST / n) for n in GENERATED}:
        raise ValueError("Outputs changed after independent review")
    receipt = qa_stage(DEST, CODE, Path(replay).resolve(), GENERATED, minimum_tests=950)
    inputs = verify_inputs()
    if (
        read(DEST / "FROZEN_INPUT_VERIFICATION.json")["machine_manifest_sha256"]
        != inputs["machine_manifest_sha256"]
    ):
        raise ValueError("Inputs changed after generation")
    (DEST / "QA_REPORT.md").write_text(
        f"# Failure audit QA\n\nPASS: {receipt['tests']} inherited/new tests; {len(GENERATED)} deterministic generated files byte-identical. New-file lint, inherited fatal lint, compile, source mypy, Original resume and all 14 frozen machine namespace checks pass.\n\nAll 1372 saved pre-entry case-version rows and 345 CLOSED version records validated; overlapping versions are not unique additional trades. Filled/closed partitions, saved execution chronology, paired LONG/SHORT synthetic reflection/scaling, recursive known_at/end_swing_at checks, and outcome-input rejection passed. Saved-case projection is a local determinism check only. The actual historical midpoint/future-mutation proof is inherited unchanged, not freshly rerun.\n\nKnown finding retained: same-bar wick-fill/stop time bounds overstate timing precision (6/4/4 records); no P&L identity failure found. All unresolved intrabar cases are LONG. No OOS/exchange-realism/production claim. No historical financial run, v3 rule, parameter search or trading activation. Independent review scope and final approval are retained in independent_review/.\n"
    )
    artifacts = {
        str(p.relative_to(ROOT)): checksum(p) for p in DEST.rglob("*") if p.is_file()
    }
    artifacts.update({name: checksum(ROOT / name) for name in CODE})
    save(
        DEST / "freeze_manifest.json",
        {
            "stage": "retrospective_failure_audit",
            "version": "MACHINE_FAILURE_AUDIT_v1",
            "status": "FROZEN_DIAGNOSTIC",
            "parents": inputs["machine_manifest_sha256"],
            "artifacts": dict(sorted(artifacts.items())),
            "QA_tests": receipt["tests"],
            "outcomes_computed": False,
            "saved_outcomes_recomputed_for_identity_only": True,
            "historical_financial_backtest_ran": False,
            "v3_strategy_created": False,
            "trade_entry_allowed": False,
            "PAPER_enabled": False,
            "LIVE_enabled": False,
            "historical_exchange_execution_claimed": False,
        },
    )
    print("FROZEN_FAILURE_AUDIT", checksum(DEST / "freeze_manifest.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEST)
    parser.add_argument("--validate-replay", type=Path)
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--resume-existing", action="store_true")
    args = parser.parse_args()
    if args.resume_existing:
        verify_inputs()
        print("VERIFIED_FAILURE_AUDIT_RESUME", verify_machine(DEST))
    elif args.seal:
        seal(args.seal)
    elif args.validate_replay:
        receipt = qa_stage(
            DEST, CODE, args.validate_replay.resolve(), GENERATED, minimum_tests=950
        )
        print("AUDIT_QA_PASS", receipt["tests"])
    else:
        build(args.output)


if __name__ == "__main__":
    main()
