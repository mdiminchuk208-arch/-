"""Render the published one-shot bytes; no adapter, engine, or strategy calls."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, localcontext

from verify_machine_strategy_v4_1_development_financial_v1 import (
    OUT,
    checkpoint,
    read,
    require,
)


def utc(epoch):
    return datetime.fromtimestamp(epoch, UTC).isoformat() if epoch is not None else ""


def short(value):
    if value is None:
        return "undefined"
    if isinstance(value, str):
        try:
            with localcontext() as context:
                context.prec = 80
                return format(Decimal(value), ".6f")
        except ArithmeticError:
            pass
    return str(value)


def write_csv(name, rows, fields):
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def report(expected):
    checkpoint(expected)
    publication = read("ONE_SHOT_RESULT_PUBLICATION.json")
    require(
        publication["checkpoint_sha256"] == expected, "PUBLISHED_CHECKPOINT_REQUIRED"
    )
    cases = []
    for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP"):
        cases.extend(
            json.loads(line)
            for line in gzip.decompress(
                (OUT / f"{product}.cases.jsonl.gz").read_bytes()
            ).splitlines()
        )
    cases.sort(key=lambda row: (row["decision_at"], row["case_id"]))
    result = read("FINANCIAL_RESULT.json")
    audit = read("INDEPENDENT_FINANCIAL_AUDIT.json")
    qualification = result["qualification"]
    counts = Counter(
        state["status"] for case in cases for state in case["all_scenarios"]
    )
    summary = {
        "checkpoint_sha256": expected,
        "qualification_population": "Only cases CLOSED under all nine scenarios; no profitable subset selection",
        "candidate_count": len(cases),
        "case_status_counts": dict(Counter(case["status"] for case in cases)),
        "scenario_state_counts": dict(sorted(counts.items())),
        "scenario_records": sum(counts.values()),
        "cases_with_any_fill_evidence": sum(
            any("fill_price" in state for state in case["all_scenarios"])
            for case in cases
        ),
        "cases_with_all_nine_fill_evidence": sum(
            all("fill_price" in state for state in case["all_scenarios"])
            for case in cases
        ),
        "filled_unknown_exit_states_actual": sum(
            "fill_price" in state
            and state["status"]
            in {
                "WAIT_INTRABAR_ORDER",
                "OPEN_CENSORED_EOF",
                "UNKNOWN_DATA_GAP",
                "UNRESOLVED",
            }
            for case in cases
            for state in case["all_scenarios"]
        ),
        "runner_unknown_check_scope": "Runner/auditor frozen field filled_unknown_exit_states conservatively includes all four unknown statuses even without fill evidence; unchanged",
        "runner_qualification": qualification,
        "independent_audit": audit,
        "holding_time_method": "Intervals from observer; never a pre-entry filter. Lower/upper bin inventories bound duration uncertainty; no exact fill/exit time asserted.",
        "holding_time_bins_lower": {},
        "holding_time_bins_upper": {},
        "trade_entry_allowed": False,
    }
    case_rows = []
    scenario_rows = []
    bins = (
        (3600, "<1h"),
        (14400, "1h-4h"),
        (86400, "4h-1d"),
        (604800, "1d-7d"),
        (None, ">=7d"),
    )

    def duration_bin(seconds):
        return next(label for bound, label in bins if bound is None or seconds < bound)

    for case in cases:
        row = {
            key: case[key]
            for key in (
                "case_id",
                "product",
                "direction",
                "branch",
                "setup_tf",
                "status",
            )
        }
        row["decision_at_utc"] = utc(case["decision_at"])
        row["diagnostic_only"] = case["closed_values_diagnostic_only"]
        for column in ("base", "doubled"):
            adverse = (
                case["adverse"].get(column, {}) if case["status"] == "CLOSED" else {}
            )
            for key in (
                "net_R",
                "gross_R",
                "fees_R",
                "slippage_R",
                "funding_R",
                "net_cash",
                "gross_cash",
                "fees_cash",
                "slippage_cash",
                "funding_cash",
                "scenario_id",
                "exit_reason",
                "holding_time_bounds",
            ):
                value = adverse.get(key, "")
                row[column + "_" + key] = (
                    json.dumps(value) if isinstance(value, (list, dict)) else value
                )
        if case["status"] == "CLOSED":
            bounds = case["adverse"]["base"]["holding_time_bounds"]
            lower, upper = bounds["minimum_seconds"], bounds["maximum_seconds"]
            for which, value in (("lower", lower), ("upper", upper)):
                inventory = summary["holding_time_bins_" + which]
                label = duration_bin(value)
                inventory[label] = inventory.get(label, 0) + 1
        case_rows.append(row)
        for state in case["all_scenarios"]:
            flat = {
                key: case[key]
                for key in ("case_id", "product", "direction", "branch", "setup_tf")
            }
            flat.update(
                {
                    key: state.get(key, "")
                    for key in (
                        "scenario_id",
                        "status",
                        "reason",
                        "quantity_base",
                        "fill_price",
                        "exit_price",
                        "exit_reason",
                        "fixed_R_unit",
                    )
                }
            )
            flat["case_status"] = case["status"]
            flat["diagnostic_only"] = case["closed_values_diagnostic_only"]
            for column in ("base", "doubled"):
                for key in (
                    "gross_cash",
                    "fees_cash",
                    "slippage_cash",
                    "funding_cash",
                    "net_cash",
                    "net_R",
                ):
                    flat[column + "_" + key] = (
                        state.get("columns", {}).get(column, {}).get(key, "")
                    )
            scenario_rows.append(flat)
    write_csv(
        "ALL_CASES.csv", case_rows, list(case_rows[0]) if case_rows else ["case_id"]
    )
    write_csv(
        "ALL_SCENARIO_STATES.csv",
        scenario_rows,
        list(scenario_rows[0]) if scenario_rows else ["case_id"],
    )
    (OUT / "REPORT_DATA.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    lines = [
        "# v4.1 one-shot development financial report",
        "",
        f"Runner: `{qualification['decision']}`; independent auditor: `{audit['decision']}`. Final gate acceptance requires the separate serial reviews and result freeze.",
        "",
        f"First outcome commit: `{publication['first_outcome_commit']}`. External checkpoint SHA256: `{expected}`.",
        "",
        "Exposed OKX development history [2024-10-13, 2026-10-13), BTC/ETH USDT swaps, both directions and all five preregistered families. This is not pristine OOS. All nine frozen modeled compatibility scenarios retained.",
        "",
        f"Candidates: {len(cases)}; case statuses: `{json.dumps(summary['case_status_counts'], sort_keys=True)}`; all scenario records: {sum(counts.values())}.",
        "",
        f"Cases with any/all-nine fill evidence: {summary['cases_with_any_fill_evidence']} / {summary['cases_with_all_nine_fill_evidence']}. Scenario terminal statuses: `{json.dumps(summary['scenario_state_counts'], sort_keys=True)}`.",
        "",
        "Only all-nine CLOSED cases enter qualification statistics. Incompatible cases retain all state-level diagnostic values in the immutable raw files and ALL_SCENARIO_STATES.csv; their values never enter the qualified population.",
        "",
        "| Metric | Base | Doubled fee/slippage |",
        "|---|---:|---:|",
    ]
    for key in (
        "CLOSED",
        "WIN",
        "LOSS",
        "win_rate",
        "profit_factor_R",
        "expectancy_R",
        "net_R",
        "gross_R",
        "net_cash",
        "max_drawdown_R",
        "max_consecutive_net_losses",
        "wilson_95pct_lower",
    ):
        lines.append(
            f"| {key} | {short(qualification['base'][key])} | {short(qualification['doubled'][key])} |"
        )
    for key in (
        "gross_cash",
        "fees_cash",
        "slippage_cash",
        "funding_cash",
        "net_cash",
        "fees_R",
        "slippage_R",
        "funding_R",
    ):
        lines.append(
            f"| {key} | {short(qualification['base']['components'][key])} | {short(qualification['doubled']['components'][key])} |"
        )
    lines += [
        "",
        "Cash is modeled USDT using retained scenario quantities. R uses each case's immutable reference P01_Q001 U. No common account equity or portfolio-return claim is made. Fees/slippage are fixed modeled per-leg assumptions; funding uses sealed actual signed rates and the conservative coherent timing witness with settlement-close proxy. Doubled costs reuse the exact same event paths.",
        "",
        "## Preregistered checks",
        "",
        "| Check | Runner | Auditor |",
        "|---|---|---|",
    ]
    for key, value in qualification["checks"].items():
        lines.append(f"| {key} | {value} | {audit['checks'][key]} |")
    for dimension, groups in qualification["breakdowns"].items():
        lines += [
            "",
            "## " + dimension,
            "",
            "| Group | CLOSED | WIN | LOSS | WR | PF R | Expectancy R | Net R | Net cash |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for group, metrics in groups.items():
            lines.append(
                "| "
                + group
                + " | "
                + " | ".join(
                    short(metrics[key])
                    for key in (
                        "CLOSED",
                        "WIN",
                        "LOSS",
                        "win_rate",
                        "profit_factor_R",
                        "expectancy_R",
                        "net_R",
                        "net_cash",
                    )
                )
                + " |"
            )
        if not groups:
            lines.append(
                "| No qualified CLOSED cases | 0 | 0 | 0 | undefined | undefined | undefined | 0 | 0 |"
            )
    lines += [
        "",
        "## Concentration and uncertainty",
        "",
        "```json",
        json.dumps(qualification["concentration"], indent=2, sort_keys=True),
        "```",
        "",
        f"Compatibility disagreements: {qualification['compatibility_disagreements']}. Frozen conservative unknown counter: {qualification['filled_unknown_exit_states']}; actual filled-with-unknown states from stored fill evidence: {summary['filled_unknown_exit_states_actual']}.",
        "",
        summary["runner_unknown_check_scope"],
        "",
        summary["holding_time_method"],
        "",
        f"Holding lower bins: `{json.dumps(summary['holding_time_bins_lower'], sort_keys=True)}`; upper bins: `{json.dumps(summary['holding_time_bins_upper'], sort_keys=True)}`.",
        "",
        "## All cases",
        "",
        "ALL_CASES.csv lists every candidate chronologically; ALL_SCENARIO_STATES.csv lists every one of its nine states, including all rejects, unfilled and unknown states. Raw catalog/case JSONL preserves complete geometry, context, lifecycle and funding witness. No direction, family, interval or grid has been removed based on outcomes.",
        "",
        "## Limits",
        "",
        *["- " + limitation for limitation in result["model_limitations"]],
        "",
        "No parameter search, financial replay, new robustness experiment or OOS evaluation was performed by this renderer. PAPER/LIVE/private API/orders remain prohibited; trade_entry_allowed=false; production candidate NONE.",
    ]
    (OUT / "FINANCIAL_REPORT.md").write_text("\n".join(lines) + "\n")
    return {
        "rendered_from_checkpoint": expected,
        "case_rows": len(case_rows),
        "scenario_rows": len(scenario_rows),
        "historical_engine_calls": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-checkpoint-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.expected_checkpoint_sha256), sort_keys=True))
