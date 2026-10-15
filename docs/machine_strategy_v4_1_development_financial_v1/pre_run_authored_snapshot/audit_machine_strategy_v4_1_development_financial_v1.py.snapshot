"""Independent post-result auditor for the v4.1 one-shot development gate.

This module cannot generate signals, fills, exits or financial cases. It only
verifies already checkpointed one-shot outputs against preregistered rules.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from okx_qualification_data_v1 import ROOT
from okx_v3_compatibility_binding_v1 import scenarios

OUT = ROOT / "docs/machine_strategy_v4_1_development_financial_v1"
PREREG = OUT / "PREREGISTRATION.json"
CHECKPOINT = OUT / "RUN_CHECKPOINT.json"
AUDIT = OUT / "INDEPENDENT_FINANCIAL_AUDIT.json"


class AuditStop(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_jsonl_gz(path: Path) -> list[dict]:
    return [json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines() if line]


def _d(value) -> Decimal:
    return Decimal(str(value))


def _wilson(wins: int, n: int):
    if not n:
        return None
    p = Decimal(wins) / Decimal(n)
    z = Decimal("1.959963984540054")
    return (
        p
        + z * z / (2 * n)
        - z * (p * (1 - p) / n + z * z / (4 * n * n)).sqrt()
    ) / (1 + z * z / n)


def _stats(cases: list[dict], column: str) -> dict:
    closed = [row for row in cases if row["status"] == "CLOSED"]
    ledger = sorted(closed, key=lambda r: (r["adverse"][column]["observed_at"], r["case_id"]))
    vals = [_d(row["adverse"][column]["net_R"]) for row in ledger]
    cash = [_d(row["adverse"][column]["net_cash"]) for row in ledger]
    wins = sum(v > 0 for v in vals)
    gains = sum((v for v in vals if v > 0), Decimal(0))
    losses = -sum((v for v in vals if v < 0), Decimal(0))
    equity = peak = dd = Decimal(0)
    streak = max_streak = 0
    for v in vals:
        equity += v
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        streak = streak + 1 if v < 0 else 0
        max_streak = max(max_streak, streak)
    n = len(vals)
    return {
        "CLOSED": n,
        "WIN": wins,
        "LOSS": n - wins,
        "win_rate": Decimal(wins) / n if n else None,
        "wilson_95pct_lower": _wilson(wins, n),
        "profit_factor_R": gains / losses if losses else Decimal("Infinity") if gains else None,
        "expectancy_R": sum(vals, Decimal(0)) / n if n else None,
        "net_R": sum(vals, Decimal(0)),
        "net_cash": sum(cash, Decimal(0)),
        "max_drawdown_R": dd,
        "max_consecutive_net_losses": max_streak,
    }


def _verify_case_arithmetic(catalog_by_id: dict[str, dict], cases: list[dict]) -> dict:
    checks = 0
    expected_ids = None
    unknown = 0
    disagreements = 0
    for case in cases:
        order = catalog_by_id[case["case_id"]]
        scenario_ids = [row["scenario_id"] for row in case["all_scenarios"]]
        expected = [grid["id"] for grid in scenarios(case["product"])]
        if scenario_ids != expected:
            raise AuditStop("SCENARIO_ORDER_OR_COVERAGE")
        expected_ids = expected
        if case["status"] == "COMPATIBILITY_DISAGREEMENT":
            disagreements += 1
        for state in case["all_scenarios"]:
            if state["status"] in {"WAIT_INTRABAR_ORDER", "OPEN_CENSORED_EOF", "UNKNOWN_DATA_GAP"}:
                unknown += 1
            if state["status"] != "CLOSED":
                continue
            q = _d(state["quantity_base"])
            e = _d(state["fill_price"])
            x = _d(state["exit_price"])
            d = Decimal(1 if state["direction"] == "LONG" else -1)
            gross = d * q * (x - e)
            u = _d(state["fixed_R_unit"])
            if u != _d(order["fixed_R_unit"]):
                raise AuditStop("FIXED_U_CHANGED")
            for name, mult in (("base", Decimal(1)), ("doubled", Decimal(2))):
                col = state["columns"][name]
                fee = mult * Decimal("0.0006") * q * (e + x)
                slip = mult * Decimal("0.0002") * q * (e + x)
                funding = _d(col["funding_cash"])
                net = gross - fee - slip + funding
                expected_values = {
                    "gross_cash": gross,
                    "fees_cash": fee,
                    "slippage_cash": slip,
                    "net_cash": net,
                    "gross_R": gross / u,
                    "fees_R": fee / u,
                    "slippage_R": slip / u,
                    "funding_R": funding / u,
                    "net_R": net / u,
                }
                for key, value in expected_values.items():
                    if _d(col[key]) != value:
                        raise AuditStop(f"REALIZED_ARITHMETIC_MISMATCH:{key}")
                    checks += 1
    return {
        "closed_arithmetic_checks": checks,
        "compatibility_disagreements": disagreements,
        "filled_unknown_exit_states": unknown,
        "scenario_ids": expected_ids,
    }


def _concentration(cases: list[dict]) -> dict:
    quarters = defaultdict(Decimal)
    coins = defaultdict(Decimal)
    for row in cases:
        if row["status"] != "CLOSED":
            continue
        value = _d(row["adverse"]["base"]["net_R"])
        at = datetime.fromtimestamp(row["adverse"]["base"]["observed_at"], UTC)
        quarters[f"{at.year}-Q{(at.month - 1) // 3 + 1}"] += value
        coins[row["product"]] += value
    qp = {k: v for k, v in quarters.items() if v > 0}
    cp = {k: v for k, v in coins.items() if v > 0}
    qsum = sum(qp.values(), Decimal(0))
    csum = sum(cp.values(), Decimal(0))
    return {
        "largest_calendar_quarter_profit_share": max(qp.values()) / qsum if qsum else None,
        "largest_coin_profit_share": max(cp.values()) / csum if csum else None,
        "quarters_R": dict(sorted(quarters.items())),
        "coins_R": dict(sorted(coins.items())),
    }


def _group(cases: list[dict]) -> dict:
    buckets = defaultdict(list)
    for row in cases:
        if row["status"] == "CLOSED":
            buckets[row["product"] + ":" + row["direction"]].append(row)
    return {key: _stats(rows, "base") for key, rows in sorted(buckets.items())}


def _serialize(value):
    if isinstance(value, Decimal):
        if value.is_infinite():
            return "Infinity"
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


def audit(write: bool = False) -> dict:
    if not CHECKPOINT.exists():
        raise AuditStop("RUN_CHECKPOINT_REQUIRED")
    checkpoint = json.loads(CHECKPOINT.read_text())
    for name, expected in checkpoint["artifacts_sha256"].items():
        if _sha(OUT / name) != expected:
            raise AuditStop(f"CHECKPOINT_ARTIFACT_CHANGED:{name}")
    prereg = json.loads(PREREG.read_text())
    catalogs = {}
    cases = []
    for product in prereg["products"]:
        catalog = _load_jsonl_gz(OUT / f"{product}.catalog.jsonl.gz")
        product_cases = _load_jsonl_gz(OUT / f"{product}.cases.jsonl.gz")
        if [r["case_id"] for r in catalog] != [r["case_id"] for r in product_cases]:
            raise AuditStop("CATALOG_CASE_COVERAGE")
        if len({r["case_id"] for r in catalog}) != len(catalog):
            raise AuditStop("DUPLICATE_CASE_ID")
        for order in catalog:
            u = _d(order["fixed_R_unit"])
            e = _d(order["entry"])
            s = _d(order["stop"])
            expected_u = abs(e - s) + Decimal("0.0008") * (e + s)
            if u != expected_u:
                raise AuditStop("REFERENCE_U_FORMULA")
        catalogs.update({row["case_id"]: row for row in catalog})
        cases.extend(product_cases)
    arithmetic = _verify_case_arithmetic(catalogs, cases)
    base = _stats(cases, "base")
    doubled = _stats(cases, "doubled")
    groups = _group(cases)
    concentration = _concentration(cases)
    q = prereg["qualification"]

    def pf_ok(value, minimum):
        return value is not None and value >= Decimal(str(minimum))

    required = [
        "BTC-USDT-SWAP:LONG",
        "BTC-USDT-SWAP:SHORT",
        "ETH-USDT-SWAP:LONG",
        "ETH-USDT-SWAP:SHORT",
    ]
    checks = {
        "closed_trades_min": base["CLOSED"] >= q["closed_trades_min"],
        "win_rate_min": base["win_rate"] is not None and base["win_rate"] >= _d(q["win_rate_min"]),
        "profit_factor_min": pf_ok(base["profit_factor_R"], q["profit_factor_min"]),
        "expectancy_positive": base["expectancy_R"] is not None and base["expectancy_R"] > 0,
        "net_R_positive": base["net_R"] > 0,
        "net_cash_positive": base["net_cash"] > 0,
        "doubled_profit_factor_min": pf_ok(doubled["profit_factor_R"], q["doubled_cost_profit_factor_min"]),
        "doubled_net_positive": doubled["net_R"] > 0 and doubled["net_cash"] > 0,
        "max_drawdown": base["max_drawdown_R"] <= _d(q["max_drawdown_R_max"]),
        "max_loss_streak": base["max_consecutive_net_losses"] <= q["max_consecutive_net_losses_max"],
        "wilson": base["wilson_95pct_lower"] is not None and base["wilson_95pct_lower"] >= _d(q["wilson_95pct_win_rate_lower_bound_min"]),
        "coin_direction_closed_min": all(key in groups and groups[key]["CLOSED"] >= q["each_coin_direction_closed_min"] for key in required),
        "coin_direction_net_positive": all(key in groups and groups[key]["net_R"] > 0 and groups[key]["net_cash"] > 0 for key in required),
        "quarter_concentration": concentration["largest_calendar_quarter_profit_share"] is not None and concentration["largest_calendar_quarter_profit_share"] <= _d(q["largest_calendar_quarter_profit_share_max"]),
        "coin_concentration": concentration["largest_coin_profit_share"] is not None and concentration["largest_coin_profit_share"] <= _d(q["largest_coin_profit_share_max"]),
        "filled_unknown_exit": arithmetic["filled_unknown_exit_states"] <= q["filled_unknown_exit_max"],
        "compatibility_agreement": arithmetic["compatibility_disagreements"] == 0,
    }
    decision = (
        "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_PASS"
        if all(checks.values())
        else "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP"
    )
    result = _serialize(
        {
            "decision": decision,
            "checks": checks,
            "candidate_count": len(catalogs),
            "case_count": len(cases),
            "base": base,
            "doubled": doubled,
            "coin_direction": groups,
            "concentration": concentration,
            "arithmetic": arithmetic,
            "runner_reported_decision": json.loads((OUT / "FINANCIAL_RESULT.json").read_text())["qualification"]["decision"],
        }
    )
    if write:
        AUDIT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.write), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
