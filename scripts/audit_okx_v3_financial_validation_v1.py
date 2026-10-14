"""Audit sealed one-shot outputs; no signal discovery or trade re-evaluation."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter
from decimal import Decimal, localcontext

from build_okx_v3_compatibility_v1 import resume
from okx_qualification_data_v1 import ROOT, save
from okx_v3_compatibility_binding_v1 import DEST, digest, read_policy, scenarios
from okx_v3_compatibility_runner_v1 import OUT, verify_run_checkpoint
from okx_v3_input_bridge_v1 import load_native

AUDIT = ROOT / "docs/machine_strategy_v3_okx_financial_audit_v1"
READY_SHA = "5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1"
D = Decimal


def audit(expected):
    resume(READY_SHA)
    verify_run_checkpoint(expected)
    summary = json.loads((OUT / "FINANCIAL_RESULT.json").read_text())
    pre, _ = read_policy()
    all_cases, products, checks = [], {}, Counter()
    costs = json.loads((DEST / "COST_FUNDING_BINDING.json").read_text())[
        "source_inputs"
    ]
    with localcontext() as context:
        context.prec = 80
        for product in pre["scope"]["products"]:
            catalog = [
                json.loads(line)
                for line in gzip.decompress(
                    (OUT / (product + ".catalog.jsonl.gz")).read_bytes()
                ).splitlines()
            ]
            cases = [
                json.loads(line)
                for line in (OUT / (product + ".cases.jsonl")).read_text().splitlines()
            ]
            assert [r["case_id"] for r in catalog] == [r["case_id"] for r in cases], (
                "CATALOG_COVERAGE"
            )
            assert len({r["case_id"] for r in cases}) == len(cases), "UNIQUE_CASE_IDS"
            native = load_native(product)
            closes = {b.end: b.close for b in native}
            rates = {
                int(r["funding_time_utc_ms"]) // 1000: D(r["funding_rate"])
                for r in csv.DictReader(
                    (ROOT / costs[product.split("-")[0] + "_funding_csv"]).open()
                )
            }
            for order, case in zip(catalog, cases, strict=True):
                assert (
                    order["trade_entry_allowed"] is False
                    and case["trade_entry_allowed"] is False
                )
                assert (
                    order["venue"] == case["venue"] == "OKX"
                    and case["product"] == product
                )
                unit = D(order["fixed_R_unit"])
                assert unit == abs(D(order["entry"]) - D(order["stop"])) + D(
                    ".0008"
                ) * (D(order["entry"]) + D(order["stop"])), "FIXED_REFERENCE_UNIT"
                assert [s["scenario_id"] for s in case["all_scenarios"]] == [
                    s["id"] for s in scenarios(product)
                ], "ALL_SCENARIOS"
                closed = [s for s in case["all_scenarios"] if s["status"] == "CLOSED"]
                assert (case["status"] == "CLOSED") == (len(closed) == 9), (
                    "CLOSED_STATUS"
                )
                for state in closed:
                    q, entry, exit_price = (
                        D(state[k])
                        for k in ("quantity_base", "fill_price", "exit_price")
                    )
                    assert 0 < q <= 1 and D(state["fixed_R_unit"]) == unit
                    direction = D(1 if case["direction"] == "LONG" else -1)
                    witness = state["funding_timing_witness"]
                    f, x = (
                        tuple(witness["model_fill_event_slot"]),
                        tuple(witness["model_exit_event_slot"]),
                    )
                    assert f <= x
                    assert (
                        state["fill_time_bounds"][0]
                        <= f[0]
                        <= state["fill_time_bounds"][1]
                    )
                    assert (
                        state["event_time_bounds"][0]
                        <= x[0]
                        <= state["event_time_bounds"][1]
                    )
                    exposed = [t for t in rates if f < (t, 0) < x]
                    assert exposed == witness["settlements_included"], (
                        "COHERENT_SETTLEMENT_MEMBERSHIP"
                    )
                    funding = sum(
                        (-direction * rates[t] * q * closes[t] for t in exposed), D(0)
                    )
                    gross = direction * q * (exit_price - entry)
                    for column, multiplier in (("base", D(1)), ("doubled", D(2))):
                        value = state["columns"][column]
                        fee = multiplier * D(".0006") * q * (entry + exit_price)
                        slip = multiplier * D(".0002") * q * (entry + exit_price)
                        expected_cash = {
                            "gross_cash": gross,
                            "fees_cash": fee,
                            "slippage_cash": slip,
                            "funding_cash": funding,
                            "net_cash": gross - fee - slip + funding,
                        }
                        assert all(
                            D(value[k]) == v for k, v in expected_cash.items()
                        ), "CASH_IDENTITY"
                        assert D(value["net_R"]) == expected_cash["net_cash"] / unit, (
                            "FIXED_UNIT_NET_R"
                        )
                        checks["closed_scenario_cost_column_checks"] += 1
                for column in ("base", "doubled"):
                    if closed:
                        worst = min(
                            closed,
                            key=lambda s: (
                                D(s["columns"][column]["net_cash"]),
                                s["scenario_id"],
                            ),
                        )
                        assert (
                            case["adverse"][column]["scenario_id"]
                            == worst["scenario_id"]
                        ), "WORST_CASE_SELECTION"
                        assert (
                            case["adverse"][column]["net_cash"]
                            == worst["columns"][column]["net_cash"]
                        )
                checks["all_case_retention_checks"] += 1
            counts = Counter(r["status"] for r in cases)
            products[product] = {
                "catalog_cases": len(catalog),
                "case_status_counts": dict(counts),
                "native_bars": len(native),
                "funding_rows": len(rates),
            }
            all_cases.extend(cases)
        independently_rebuilt = {}
        closed_cases = [c for c in all_cases if c["status"] == "CLOSED"]
        for column in ("base", "doubled"):
            values = [D(c["adverse"][column]["net_R"]) for c in closed_cases]
            total = sum(values, D(0))
            gains = sum((v for v in values if v > 0), D(0))
            losses = -sum((v for v in values if v < 0), D(0))
            cash = sum(
                (D(c["adverse"][column]["net_cash"]) for c in closed_cases), D(0)
            )
            s = summary[column]
            assert (
                s["CLOSED"] == len(values)
                and s["WIN"] == sum(v > 0 for v in values)
                and s["LOSS"] == sum(v < 0 for v in values)
            )
            assert abs(D(s["net_PnL_R"]) - total) < D("1e-20") and abs(
                D(s["components"]["net_cash"]) - cash
            ) < D("1e-20"), "SUM_ACCOUNTING"
            if losses:
                assert abs(D(s["PF"]) - gains / losses) < D("1e-20"), (
                    "PF_RECONCILIATION"
                )
            independently_rebuilt[column] = {
                "CLOSED": len(values),
                "net_R": str(total),
                "net_cash": str(cash),
                "gains_R": str(gains),
                "losses_R": str(losses),
            }
        unresolved = sum(c["status"] == "COMPATIBILITY_DISAGREEMENT" for c in all_cases)
        assert unresolved == summary["compatibility_disagreements"]
        if unresolved:
            assert summary["decision"] == "MACHINE_STRATEGY_V3_QUALIFICATION_STOP", (
                "STOP_DOMINATES"
            )
    receipt = {
        "QA": "PASS",
        "ready_manifest_sha256": READY_SHA,
        "run_checkpoint_sha256": expected,
        "historical_backtest_re_evaluations": 0,
        "products": products,
        "checks": dict(checks),
        "independent_cash_R_reconciliation": independently_rebuilt,
        "source_output_sha256": {
            str(p.relative_to(ROOT)): digest(p) for p in OUT.iterdir() if p.is_file()
        },
        "trade_entry_allowed": False,
        "PAPER": False,
        "LIVE": False,
    }
    save(AUDIT / "ACCOUNTING_QA.json", receipt)
    return {
        "QA": "PASS",
        "cases": len(all_cases),
        "CLOSED": len(closed_cases),
        "unresolved": unresolved,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-run-checkpoint-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.expected_run_checkpoint_sha256), sort_keys=True))
