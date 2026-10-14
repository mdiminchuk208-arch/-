"""One-shot guarded OKX model runner; historical outputs require committed READY."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import subprocess
from bisect import bisect_left
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from functools import wraps
from hashlib import sha256
from typing import Any

import machine_strategy_v3_contracts as core
from machine_strategy_v2_core import serial
from okx_qualification_data_v1 import ROOT, compact, millis, save
from okx_v3_compatibility_binding_v1 import (
    DEST,
    POLICY_COMMIT,
    READY_DECISION,
    VERSION,
    CompatibilityAdapter,
    _model_observer,
    capture_reference_plan,
    digest,
    market_inputs,
    read_policy,
    scenario_plan,
    scenarios,
)

OUT = ROOT / "docs/machine_strategy_v3_okx_financial_validation_v1"
_MARKER = object()
TOY_NAMES = (
    "LONG",
    "SHORT",
    "LONG_ETH",
    "SHORT_ETH",
    "LONG_NEGATIVE_FUNDING",
    "SHORT_NEGATIVE_FUNDING",
    "LONG_INTRABAR",
    "LONG_UNFILLED",
    "LONG_ELIGIBILITY_DISAGREEMENT",
)
_ISSUED: dict[int, Any] = {}
_ACTIVE: ContextVar[dict[str, Any] | None] = ContextVar(
    "okx_compatibility_evaluation_scope", default=None
)


class FinancialBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class Capability:
    marker: object
    manifest_sha256: str
    freeze_commit: str


def campaign_permits_historical(task):
    if not task.splitlines():
        return False
    header = task.splitlines()[0]
    return (
        header
        in (
            "# Current Campaign — STRATEGY_AUTONOMY_TO_PLATFORM_RECONNECT",
            "# Current Campaign — OKX Compatibility Implementation + READY Review",
        )
        and "one-shot" in task
        and "READY" in task
    )


def authorize(expected, freeze_commit):
    path = DEST / "freeze_manifest.json"
    if not expected or not path.exists() or digest(path) != expected:
        raise FinancialBlocked("COMMITTED_READY_MANIFEST_REQUIRED")
    manifest = json.loads(path.read_text())
    if manifest["decision"] != READY_DECISION:
        raise FinancialBlocked("COMPATIBILITY_NOT_READY")
    task = (ROOT / "agent_control/CURRENT_BATCH.md").read_text()
    if not campaign_permits_historical(task):
        raise FinancialBlocked("AUTONOMOUS_HISTORICAL_GATE_NOT_ACTIVE")
    relative = str(path.relative_to(ROOT))
    committed = subprocess.check_output(
        ["git", "show", freeze_commit + ":" + relative], cwd=ROOT
    )
    if sha256(committed).hexdigest() != expected:
        raise FinancialBlocked("READY_COMMIT_BYTES_MISMATCH")
    for commit in (POLICY_COMMIT, freeze_commit):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True
        )
    for name, h in manifest["artifacts"].items():
        if digest(ROOT / name) != h:
            raise FinancialBlocked("READY_ARTIFACT_CHANGED")
    namespace = {
        str(p.relative_to(ROOT)) for p in DEST.rglob("*") if p.is_file() and p != path
    }
    if namespace != {
        n
        for n in manifest["artifacts"]
        if n.startswith(str(DEST.relative_to(ROOT)) + "/")
    }:
        raise FinancialBlocked("READY_NAMESPACE_MEMBERSHIP_CHANGED")
    read_policy()
    capability = Capability(_MARKER, expected, freeze_commit)
    _ISSUED[id(capability)] = capability
    return capability


def check(capability):
    if (
        not isinstance(capability, Capability)
        or capability.marker is not _MARKER
        or _ISSUED.get(id(capability)) is not capability
    ):
        raise FinancialBlocked("NO_COMMITTED_HISTORICAL_CAPABILITY")
    if digest(DEST / "freeze_manifest.json") != capability.manifest_sha256:
        raise FinancialBlocked("READY_MANIFEST_CHANGED")
    read_policy()
    authority = json.loads((DEST / "AUTHORIZATION_SOURCE.json").read_text())
    for name, h in {
        **authority["control_sha256"],
        **authority["implementation_sha256"],
    }.items():
        if digest(ROOT / name) != h:
            raise FinancialBlocked("CAMPAIGN_AUTHORIZATION_SOURCE_CHANGED")


def fingerprint(order, native, funding):
    return sha256(
        compact(
            serial(
                [
                    order,
                    [{**inherited_bar(b), "product": b.product} for b in native],
                    funding,
                ]
            )
        ).encode()
    ).hexdigest()


@contextmanager
def _evaluation_scope(capability=None, fixture=None):
    if fixture is None:
        check(capability)
    elif fixture not in TOY_NAMES:
        raise FinancialBlocked("UNREGISTERED_TOY_SCOPE")
    else:
        read_policy()
    scope = {
        "capability": capability,
        "fixture": fixture,
        "closed_states": set(),
        "scenario_states": set(),
        "case_hashes": set(),
    }
    token = _ACTIVE.set(scope)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def guarded(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        scope = _ACTIVE.get()
        if scope is None:
            raise FinancialBlocked("NO_AUTHORIZED_EVALUATION_SCOPE")
        if scope["fixture"] is None:
            check(scope["capability"])
        else:
            read_policy()
        return function(*args, **kwargs)

    return wrapper


def _active_scope():
    value = _ACTIVE.get()
    if value is None:
        raise FinancialBlocked("NO_AUTHORIZED_EVALUATION_SCOPE")
    return value


def funding_inputs(product, native):
    binding = json.loads((DEST / "COST_FUNDING_BINDING.json").read_text())
    side = product.split("-")[0]
    path = ROOT / binding["source_inputs"][side + "_funding_csv"]
    if digest(path) != binding["source_inputs"][side + "_funding_csv_sha256"]:
        raise FinancialBlocked("FUNDING_SOURCE_CHANGED")
    rows = list(csv.DictReader(path.open()))
    result = []
    closes = {b.end: b.close for b in native}
    for r in rows:
        at = int(r["funding_time_utc_ms"]) // 1000
        if r["instrument_name"] != product or at not in closes:
            raise FinancialBlocked("FUNDING_IDENTITY_OR_MARK_PROXY_MISSING")
        result.append((at, Decimal(r["funding_rate"]), closes[at]))
    return result


@guarded
def _funding_min(state, rows, quantity):
    """Minimize over coherent event orders; never select a favorable credit."""
    if _active_scope()["fixture"] is not None and serial(rows) != serial(
        toy_fixture(_active_scope()["fixture"])[2]
    ):
        raise FinancialBlocked("FUNDING_NOT_FROM_REGISTERED_TOY")
    flo, fhi = state["fill_time_bounds"]
    xlo, xhi = state["event_time_bounds"]
    relevant = [r for r in rows if flo <= r[0] <= xhi]
    fill_slots = {(flo, -1), (flo, 1), (fhi, -1), (fhi, 1)}
    exit_slots = {(xlo, -1), (xlo, 1), (xhi, -1), (xhi, 1)}
    for t, _, _ in relevant:
        if flo <= t <= fhi:
            fill_slots.update(((t, -1), (t, 1)))
        if xlo <= t <= xhi:
            exit_slots.update(((t, -1), (t, 1)))
    direction = Decimal(1 if state["direction"] == "LONG" else -1)
    values = []
    for f in sorted(fill_slots):
        for x in sorted(exit_slots):
            if f > x:
                continue
            selected = [r for r in relevant if f < (r[0], 0) < x]
            cash = sum(
                (-direction * rate * quantity * price for _, rate, price in selected),
                Decimal(0),
            )
            values.append((cash, f, x, [r[0] for r in selected]))
    if not values:
        raise core.ContractWait("WAIT_COHERENT_FUNDING_TIMELINE")
    cash, f, x, times = min(values, key=lambda r: (r[0], r[1], r[2]))
    return cash, {
        "model_fill_event_slot": f,
        "model_exit_event_slot": x,
        "settlements_included": times,
        "slot_order": "-1 before same-timestamp settlement, +1 after; modeled witness, not exact observed time",
    }


@guarded
def _closed_cash(state, funding):
    if (
        _active_scope()["fixture"] is not None
        and sha256(compact(serial(state)).encode()).hexdigest()
        not in _active_scope()["closed_states"]
    ):
        raise FinancialBlocked("STATE_NOT_FROM_REGISTERED_TOY")
    with localcontext() as ctx:
        ctx.prec = 80
        q, e, x, unit = (
            Decimal(state[k])
            for k in ("quantity_base", "fill_price", "exit_price", "fixed_R_unit")
        )
        if unit <= 0 or q <= 0:
            raise core.ContractReject("REJECT_FIXED_CASH_R_UNIT")
        funded, witness = _funding_min(state, funding, q)
        d = Decimal(1 if state["direction"] == "LONG" else -1)
        gross = d * q * (x - e)
        result = {}
        for name, multiplier in (("base", Decimal(1)), ("doubled", Decimal(2))):
            fees = multiplier * Decimal("0.0006") * q * (e + x)
            slip = multiplier * Decimal("0.0002") * q * (e + x)
            net = gross - fees - slip + funded
            result[name] = {
                "gross_cash": gross,
                "fees_cash": fees,
                "slippage_cash": slip,
                "funding_cash": funded,
                "net_cash": net,
                "net_R": net / unit,
                "gross_R": gross / unit,
                "fees_R": fees / unit,
                "slippage_R": slip / unit,
                "funding_R": funded / unit,
            }
        return {"columns": result, "funding_timing_witness": witness}


@guarded
def _drive_case(order, native, funding):
    scope = _active_scope()
    if scope["fixture"] is not None and fingerprint(
        order, native, funding
    ) != fingerprint(*toy_fixture(scope["fixture"])):
        raise FinancialBlocked("INPUTS_DO_NOT_MATCH_REGISTERED_TOY")
    states = []
    starts = [b.start for b in native]
    initial = bisect_left(starts, order["decision_at"])
    for grid in scenarios(order["product"]):
        try:
            state = scenario_plan(order, grid)
        except (core.ContractReject, core.ContractWait) as exc:
            failure = {
                "scenario_id": grid["id"],
                "status": "SCENARIO_INELIGIBLE",
                "reason": exc.reason,
            }
            states.append(failure)
            scope["scenario_states"].add(
                sha256(compact(serial(failure)).encode()).hexdigest()
            )
            continue
        for bar in native[initial:]:
            state = _model_observer(state, inherited_bar(bar), [grid])
            if state["status"] not in ("PENDING", "FILLED"):
                break
        if state["status"] in ("PENDING", "FILLED"):
            state = core.censor_eof(state, native[-1].end)
        if state["status"] == "EXIT_OBSERVED":
            state["status"] = "CLOSED"
            scope["closed_states"].add(
                sha256(compact(serial(state)).encode()).hexdigest()
            )
            state.update(_closed_cash(state, funding))
            state["holding_time_bounds"] = core.holding_duration_bounds(
                state["fill_time_bounds"], state["event_time_bounds"]
            )
        states.append(state)
        scope["scenario_states"].add(
            sha256(compact(serial(state)).encode()).hexdigest()
        )
    return _adverse_case(order, states)


def inherited_bar(bar):
    return {
        "start": bar.start,
        "end": bar.end,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
    }


@guarded
def _adverse_case(order, states):
    scope = _active_scope()
    if scope["fixture"] is not None and (
        compact(serial(order)) != compact(serial(toy_fixture(scope["fixture"])[0]))
        or any(
            sha256(compact(serial(s)).encode()).hexdigest()
            not in scope["scenario_states"]
            for s in states
        )
    ):
        raise FinancialBlocked("RESULT_NOT_FROM_REGISTERED_TOY_STATES")
    if [s["scenario_id"] for s in states] != [
        s["id"] for s in scenarios(order["product"])
    ]:
        raise FinancialBlocked("ALL_PREREGISTERED_SCENARIOS_REQUIRED")
    closed = [s for s in states if s["status"] == "CLOSED"]
    if len(closed) == len(states) == 9:
        status = "CLOSED"
    elif all(
        s["status"]
        in ("UNFILLED_EXPIRED", "ORDER_CENSORED_EOF", "GAP_INVALIDATED_BEFORE_FILL")
        for s in states
    ):
        status = "ALL_SCENARIOS_NO_FILL"
    else:
        status = "COMPATIBILITY_DISAGREEMENT"
    adverse = {}
    for column in ("base", "doubled"):
        if closed:
            worst = min(
                closed,
                key=lambda s: (s["columns"][column]["net_cash"], s["scenario_id"]),
            )
            adverse[column] = {
                **worst["columns"][column],
                "scenario_id": worst["scenario_id"],
                "observed_at": worst["observed_at"],
                "event_time_bounds": worst["event_time_bounds"],
                "holding_time_bounds": worst["holding_time_bounds"],
                "exit_reason": worst["exit_reason"],
            }
    # Canonical signal/geometry is retained once in the catalog, not copied 9 times.
    duplicated = {
        "compatibility_plan_inputs",
        "all_FTA_inventory",
        "liquidity_inventory",
        "selected_impulse",
        "states",
        "source_geometry_references",
    }
    compact_states = [
        {k: v for k, v in s.items() if k not in duplicated} for s in states
    ]
    result = serial(
        {
            "case_id": order["case_id"],
            "base_signal_case_id": order["base_signal_case_id"],
            "venue": "OKX",
            "strategy_symbol_alias": order["symbol"],
            "contract_type": core.CONTRACT_TYPE,
            "product": order["product"],
            "direction": order["direction"],
            "branch": order["branch"],
            "setup_tf": order["setup_tf"],
            "decision_at": order["decision_at"],
            "context": order["context"],
            "states_at_decision": order["states"],
            "reference_geometry": {
                k: order[k]
                for k in ("entry", "stop", "target", "fixed_R_unit", "nearest_fta_id")
            },
            "status": status,
            "adverse": adverse,
            "all_scenarios": compact_states,
            "closed_values_diagnostic_only": status != "CLOSED",
            "trade_entry_allowed": False,
        }
    )
    scope["case_hashes"].add(sha256(compact(result).encode()).hexdigest())
    return result


def evaluate_case(order, native, funding, capability=None):
    check(capability)
    with _evaluation_scope(capability):
        return _drive_case(order, native, funding)


def toy_fixture(name):
    if name not in TOY_NAMES:
        raise FinancialBlocked("UNREGISTERED_TOY_FIXTURE")
    from okx_v3_input_bridge_v1 import NativeBar

    long = not name.startswith("SHORT")
    product = "ETH-USDT-SWAP" if name.endswith("_ETH") else "BTC-USDT-SWAP"
    symbol = "ETHUSDT" if name.endswith("_ETH") else "BTCUSDT"
    grid = scenarios(product)[0]
    kw = {
        "raw": {
            "direction": "LONG" if long else "SHORT",
            "raw_entry": "100",
            "raw_stop_boundary": "90" if long else "110",
            "known_at": 0,
        },
        "targets": [{"id": "toy_fta", "known_at": 0, "price": "120" if long else "80"}],
        "zone_low": "99",
        "zone_high": "101",
        "epochs": [grid],
        "symbol": symbol,
        "contract_type": core.CONTRACT_TYPE,
        "decision_at": 0,
    }
    if name == "LONG_ELIGIBILITY_DISAGREEMENT":
        kw["raw"]["raw_entry"] = "100.15"
        kw["zone_low"], kw["zone_high"] = "100.1", "100.3"
    plan = capture_reference_plan(**kw)
    order = serial(
        {
            **plan,
            "fixed_R_unit": plan["cash_stop_unit"],
            "case_id": "toy_" + name,
            "base_signal_case_id": "toy_" + name,
            "product": product,
            "venue": "OKX",
            "symbol": symbol,
            "contract_type": core.CONTRACT_TYPE,
            "direction": "LONG" if long else "SHORT",
            "branch": "OB",
            "setup_tf": 60,
            "decision_at": 0,
            "expires_at": 3600,
            "status": "PENDING",
            "selected_impulse": {"low": "80", "high": "120"},
            "liquidity_inventory": [],
            "context": "TOY",
            "states": {},
        }
    )
    p = product
    if long:
        values = [("101", "102", "99", "100"), ("100", "121", "99", "118")]
    else:
        values = [("99", "101", "98", "100"), ("100", "101", "79", "82")]
    if name == "LONG_INTRABAR":
        values[0] = ("101", "121", "80", "100")
    if name == "LONG_UNFILLED":
        values = [("105", "106", "104", "105")] * 2
    bars = [
        NativeBar(i * 900, (i + 1) * 900, *(Decimal(x) for x in v), p)
        for i, v in enumerate(values)
    ]
    return (
        order,
        bars,
        [
            (
                900,
                Decimal("-0.0001" if "NEGATIVE_FUNDING" in name else "0.0001"),
                Decimal(100),
            )
        ],
    )


def run_registered_toy(name):
    # No caller-supplied order, data, funding or synthetic boolean is accepted.
    read_policy()
    with _evaluation_scope(fixture=name):
        return _drive_case(*toy_fixture(name))


def run_registered_toy_summary(name):
    with _evaluation_scope(fixture=name):
        result = _drive_case(*toy_fixture(name))
        return _qualification([result])


@guarded
def _stats(cases, column):
    scope = _active_scope()
    if scope["fixture"] is not None and any(
        sha256(compact(r).encode()).hexdigest() not in scope["case_hashes"]
        for r in cases
    ):
        raise FinancialBlocked("METRICS_NOT_FROM_REGISTERED_TOY")
    closed = [r for r in cases if r["status"] == "CLOSED"]
    ledger = sorted(
        closed, key=lambda r: (r["adverse"][column]["observed_at"], r["case_id"])
    )
    values = [Decimal(r["adverse"][column]["net_R"]) for r in ledger]
    wins = sum(v > 0 for v in values)
    gains = sum((v for v in values if v > 0), Decimal(0))
    losses = -sum((v for v in values if v < 0), Decimal(0))
    cash_values = [Decimal(r["adverse"][column]["net_cash"]) for r in ledger]
    cash_gains = sum((v for v in cash_values if v > 0), Decimal(0))
    cash_losses = -sum((v for v in cash_values if v < 0), Decimal(0))
    gross_values = [Decimal(r["adverse"][column]["gross_R"]) for r in ledger]
    gross_gains = sum((v for v in gross_values if v > 0), Decimal(0))
    gross_losses = -sum((v for v in gross_values if v < 0), Decimal(0))
    total = sum(values, Decimal(0))
    equity = peak = drawdown = Decimal(0)
    streak = maximum = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if value < 0 else 0
        maximum = max(maximum, streak)
    n = len(values)
    rate = Decimal(wins) / n if n else None
    wilson = None
    if n:
        z = Decimal("1.959963984540054")
        wilson = (
            rate
            + z * z / (2 * n)
            - z * (rate * (1 - rate) / n + z * z / (4 * n * n)).sqrt()
        ) / (1 + z * z / n)
    pf = gains / losses if losses else "Infinity" if gains else None
    components = {
        k: sum((Decimal(r["adverse"][column][k]) for r in closed), Decimal(0))
        for k in (
            "gross_R",
            "fees_R",
            "slippage_R",
            "funding_R",
            "gross_cash",
            "fees_cash",
            "slippage_cash",
            "funding_cash",
            "net_cash",
        )
    }
    groups, quarters, coins, diagnostic_groups, holding = {}, {}, {}, {}, {}
    for r in closed:
        value = Decimal(r["adverse"][column]["net_R"])
        groups.setdefault(r["product"] + ":" + r["direction"], []).append(
            (value, Decimal(r["adverse"][column]["net_cash"]))
        )
        coins[r["product"]] = coins.get(r["product"], Decimal(0)) + value
        at = datetime.fromtimestamp(r["adverse"][column]["observed_at"], UTC)
        key = f"{at.year}-Q{(at.month - 1) // 3 + 1}"
        quarters[key] = quarters.get(key, Decimal(0)) + value
        fields = {
            "branch": r["branch"],
            "TF": str(r["setup_tf"]),
            "year": str(at.year),
            "month": f"{at.year}-{at.month:02d}",
            "exit_reason": r["adverse"][column]["exit_reason"],
            "context": compact(r["context"]).strip(),
        }
        for dimension, label in fields.items():
            bucket = diagnostic_groups.setdefault(dimension, {}).setdefault(
                label, {"CLOSED": 0, "net_R": Decimal(0), "net_cash": Decimal(0)}
            )
            bucket["CLOSED"] += 1
            bucket["net_R"] += value
            bucket["net_cash"] += Decimal(r["adverse"][column]["net_cash"])
        duration = r["adverse"][column]["holding_time_bounds"]
        lo, hi = duration["minimum_seconds"], duration["maximum_seconds"]
        label = (
            "<1h"
            if hi < 3600
            else "1h-4h"
            if 3600 <= lo and hi < 14400
            else "4h-1d"
            if 14400 <= lo and hi < 86400
            else ">=1d"
            if lo >= 86400
            else "crosses_bucket_boundary"
        )
        holding[label] = holding.get(label, 0) + 1

    def share(buckets):
        positive = [v for v in buckets.values() if v > 0]
        return max(positive) / sum(positive) if positive else None

    return serial(
        {
            "metric_scope": "ALL_SCENARIOS_CLOSED_SUBSET; unresolved cases retained and STOP dominates",
            "CLOSED": n,
            "WIN": wins,
            "LOSS": sum(v < 0 for v in values),
            "BREAKEVEN": sum(v == 0 for v in values),
            "WinRate": rate,
            "PF": pf,
            "Gross_PF_R": gross_gains / gross_losses
            if gross_losses
            else "Infinity"
            if gross_gains
            else None,
            "PF_cash": cash_gains / cash_losses
            if cash_losses
            else "Infinity"
            if cash_gains
            else None,
            "payoff_ratio_R": (gains / wins) / (losses / sum(v < 0 for v in values))
            if wins and losses
            else None,
            "Expectancy_R": total / n if n else None,
            "Avg_R": total / n if n else None,
            "net_PnL_R": total,
            "max_case_ledger_drawdown_R": drawdown,
            "max_net_loss_streak": maximum,
            "wilson_95pct_lower": wilson,
            "components": components,
            "coin_direction": {
                k: {
                    "CLOSED": len(v),
                    "net_R": sum((r[0] for r in v), Decimal(0)),
                    "net_cash": sum((r[1] for r in v), Decimal(0)),
                }
                for k, v in groups.items()
            },
            "largest_coin_profit_share": share(coins),
            "largest_quarter_profit_share": share(quarters),
            "diagnostic_partitions_not_selection_rules": diagnostic_groups,
            "holding_time_interval_distribution": holding,
        }
    )


@guarded
def _qualification(cases):
    base, double = _stats(cases, "base"), _stats(cases, "doubled")
    q = read_policy()[0]["qualification_unchanged"]

    def decimal_field(d, key):
        return Decimal(d[key]) if d[key] is not None else None

    failures = []
    for key, threshold, greater in [
        ("CLOSED", q["closed_trades_min"], True),
        ("WinRate", q["win_rate_min"], True),
        ("PF", q["profit_factor_min"], True),
        ("wilson_95pct_lower", q["wilson_95pct_win_rate_lower_bound_min"], True),
        ("max_case_ledger_drawdown_R", q["case_ledger_max_drawdown_R_max"], False),
        ("max_net_loss_streak", q["max_consecutive_net_losses_max"], False),
        ("largest_coin_profit_share", q["largest_coin_profit_share_max"], False),
        (
            "largest_quarter_profit_share",
            q["largest_calendar_quarter_profit_share_max"],
            False,
        ),
    ]:
        value = decimal_field(base, key)
        if value is None or (
            value < Decimal(threshold) if greater else value > Decimal(threshold)
        ):
            failures.append(key)
    for key in ("net_PnL_R", "Expectancy_R"):
        value = decimal_field(base, key)
        if value is None or value <= 0:
            failures.append(key)
    if Decimal(base["components"]["net_cash"]) <= 0:
        failures.append("NET_USDT_CASH")
    if (
        Decimal(double["net_PnL_R"]) <= 0
        or Decimal(double["components"]["net_cash"]) <= 0
        or double["PF"] is None
        or Decimal(double["PF"]) < Decimal(q["doubled_cost_profit_factor_min"])
    ):
        failures.append("DOUBLED_COST_EDGE")
    for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP"):
        for direction in ("LONG", "SHORT"):
            row = base["coin_direction"].get(
                product + ":" + direction, {"CLOSED": 0, "net_R": "0", "net_cash": "0"}
            )
            if (
                row["CLOSED"] < q["coin_and_direction_closed_min"]
                or Decimal(row["net_R"]) <= 0
                or Decimal(row["net_cash"]) <= 0
            ):
                failures.append("COIN_DIRECTION:" + product + ":" + direction)
    unresolved = sum(r["status"] == "COMPATIBILITY_DISAGREEMENT" for r in cases)
    decision = (
        "MACHINE_STRATEGY_V3_QUALIFICATION_STOP"
        if unresolved
        else "MACHINE_STRATEGY_V3_QUALIFIED_FAIL"
        if failures
        else "MACHINE_STRATEGY_V3_QUALIFIED_PASS"
    )
    return {
        "decision": decision,
        "model": VERSION,
        "catalog_cases": len(cases),
        "case_status_counts": dict(Counter(r["status"] for r in cases)),
        "scenario_status_counts": dict(
            Counter(s["status"] for r in cases for s in r["all_scenarios"])
        ),
        "FILLED_cases_at_least_one_scenario": sum(
            any("fill_price" in s for s in r["all_scenarios"]) for r in cases
        ),
        "all_scenarios_CLOSED_cases": base["CLOSED"],
        "compatibility_disagreements": unresolved,
        "base": base,
        "doubled": double,
        "numeric_failures": failures,
        "all_case_ids_retained": True,
        "PAPER": False,
        "LIVE": False,
        "trade_entry_allowed": False,
    }


def checkpoint_run():
    """Externally pin this receipt for an exact resume; never trust case IDs alone."""
    path = OUT / "RUN_CHECKPOINT.json"
    files = {p.name: digest(p) for p in OUT.iterdir() if p.is_file() and p != path}
    temporary = OUT / ".checkpoint.tmp"
    temporary.write_text(compact({"files_sha256": files}))
    temporary.replace(path)
    return digest(path)


def verify_run_checkpoint(expected):
    path = OUT / "RUN_CHECKPOINT.json"
    if not expected or not path.exists() or digest(path) != expected:
        raise FinancialBlocked("EXTERNAL_RUN_CHECKPOINT_PIN_REQUIRED")
    receipt = json.loads(path.read_text())
    names = {p.name for p in OUT.iterdir() if p.is_file() and p != path}
    if names != set(receipt["files_sha256"]):
        raise FinancialBlocked("RUN_NAMESPACE_CHANGED")
    for name, h in receipt["files_sha256"].items():
        if digest(OUT / name) != h:
            raise FinancialBlocked("RUN_CHECKPOINT_BYTES_CHANGED")


def run_once(capability, resume=False, expected_run_checkpoint=None):
    check(capability)
    with _evaluation_scope(capability):
        return _run_once(capability, resume, expected_run_checkpoint)


@guarded
def _run_once(capability, resume=False, expected_run_checkpoint=None):
    OUT.mkdir(parents=True, exist_ok=True)
    lock = OUT / "RUN_AUTHORITY.json"
    authority = {
        "model_manifest_sha256": capability.manifest_sha256,
        "freeze_commit": capability.freeze_commit,
        "policy_commit": POLICY_COMMIT,
        "version": VERSION,
        "scope": "ONE_SHOT_DEVELOPMENT_NOT_OOS",
    }
    if lock.exists():
        if not resume or json.loads(lock.read_text()) != authority:
            raise FinancialBlocked("EXISTING_RUN_REQUIRES_MATCHED_RESUME")
        verify_run_checkpoint(expected_run_checkpoint)
    else:
        if any(OUT.iterdir()) or resume:
            raise FinancialBlocked("NEW_RUN_REQUIRES_EMPTY_NAMESPACE")
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "w") as stream:
            stream.write(compact(authority))
        print("RUN_CHECKPOINT_SHA256=" + checkpoint_run(), flush=True)
    all_cases = []
    pre, _ = read_policy()
    for product in pre["scope"]["products"]:
        path = OUT / (product + ".cases.jsonl")
        complete = OUT / (product + ".complete.json")
        if complete.exists():
            receipt = json.loads(complete.read_text())
            if digest(path) != receipt["cases_sha256"]:
                raise FinancialBlocked("COMPLETED_SEGMENT_CHANGED")
            all_cases.extend(json.loads(line) for line in path.read_text().splitlines())
            continue
        market = market_inputs(product)
        adapter = CompatibilityAdapter(
            product,
            market,
            millis(pre["scope"]["development_start"]) // 1000,
            millis(pre["scope"]["development_end_exclusive"]) // 1000,
        )
        orders, audit = adapter.catalog()
        audit_path = OUT / (product + ".catalog_audit.json")
        if audit_path.exists() and json.loads(audit_path.read_text()) != audit:
            raise FinancialBlocked("CATALOG_AUDIT_REPLAY_CHANGED")
        save(audit_path, audit)
        catalog_file = OUT / (product + ".catalog.jsonl.gz")
        catalog_bytes = "".join(compact(order) for order in orders).encode()
        if (
            catalog_file.exists()
            and gzip.decompress(catalog_file.read_bytes()) != catalog_bytes
        ):
            raise FinancialBlocked("CATALOG_REPLAY_CHANGED")
        if not catalog_file.exists():
            catalog_file.write_bytes(gzip.compress(catalog_bytes, mtime=0))
        print("RUN_CHECKPOINT_SHA256=" + checkpoint_run(), flush=True)
        previous = (
            [json.loads(line) for line in path.read_text().splitlines()]
            if path.exists()
            else []
        )
        if [r["case_id"] for r in previous] != [
            r["case_id"] for r in orders[: len(previous)]
        ]:
            raise FinancialBlocked("PARTIAL_CASE_PREFIX_CHANGED")
        funding = funding_inputs(product, market[15])
        with path.open("a") as stream:
            for order in orders[len(previous) :]:
                result = evaluate_case(order, market[15], funding, capability)
                stream.write(compact(result))
                stream.flush()
                os.fsync(stream.fileno())
                previous.append(result)
                print("RUN_CHECKPOINT_SHA256=" + checkpoint_run(), flush=True)
        save(
            complete,
            {
                "cases_sha256": digest(path),
                "cases": len(previous),
                "catalog_sha256": digest(catalog_file),
                "model_manifest_sha256": capability.manifest_sha256,
            },
        )
        print("RUN_CHECKPOINT_SHA256=" + checkpoint_run(), flush=True)
        all_cases.extend(previous)
    summary = _qualification(all_cases)
    save(OUT / "FINANCIAL_RESULT.json", summary)
    print("RUN_CHECKPOINT_SHA256=" + checkpoint_run(), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--registered-toy", choices=TOY_NAMES)
    action.add_argument("--run-historical-once", action="store_true")
    parser.add_argument("--resume-run", action="store_true")
    parser.add_argument("--expected-ready-manifest-sha256")
    parser.add_argument("--ready-freeze-commit")
    parser.add_argument("--expected-run-checkpoint-sha256")
    args = parser.parse_args()
    result = (
        run_registered_toy(args.registered_toy)
        if args.registered_toy
        else run_once(
            authorize(args.expected_ready_manifest_sha256, args.ready_freeze_commit),
            args.resume_run,
            args.expected_run_checkpoint_sha256,
        )
    )
    print(json.dumps(result, sort_keys=True))
