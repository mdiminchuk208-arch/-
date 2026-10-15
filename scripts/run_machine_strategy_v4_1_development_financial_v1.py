"""Guarded one-shot development financial runner for frozen MACHINE_STRATEGY_v4.1.

This file is intentionally separate from implementation readiness. Historical
financial evaluation is permitted only by the committed v4.1 development gate.
It never enables PAPER/LIVE/private APIs/orders and never retunes strategy rules.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from functools import wraps
from hashlib import sha256
from pathlib import Path

import machine_strategy_v3_contracts as core
from machine_strategy_v4_1_historical_adapter import V41HistoricalAdapter, market_inputs
from okx_qualification_data_v1 import ROOT
from okx_v3_compatibility_binding_v1 import DEST as V3_COMPAT_DEST
from okx_v3_compatibility_binding_v1 import _model_observer, scenarios

VERSION = "MACHINE_STRATEGY_v4.1"
GATE = "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_V1"
OUT = ROOT / "docs/machine_strategy_v4_1_development_financial_v1"
PREREG = OUT / "PREREGISTRATION.json"
AUTH = OUT / "AUTHORIZATION.json"
IMPLEMENTATION_MANIFEST = (
    ROOT
    / "docs/machine_strategy_v4_1_implementation_readiness_v1/IMPLEMENTATION_FREEZE_MANIFEST.json"
)
IMPLEMENTATION_MANIFEST_SHA256 = (
    "e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61"
)
IMPLEMENTATION_FREEZE_COMMIT = "bf9bb4c7ed9e82df42b4fc2eec5df28695edf155"
PREREG_COMMIT = "f5e60538a2c6ea4194177971ac1d433143ddf3a2"
AUTH_COMMIT = "4a0a1471c040522058cb0520b0dc25a8dd20d4b5"
TRADE_ENTRY_ALLOWED = False


def _precision(digits):
    def decorate(function):
        @wraps(function)
        def scoped(*args, **kwargs):
            with localcontext() as context:
                context.prec = digits
                context.rounding = ROUND_HALF_EVEN
                return function(*args, **kwargs)

        return scoped

    return decorate


FINAL_FILES = (
    "BTC-USDT-SWAP.catalog.jsonl.gz",
    "ETH-USDT-SWAP.catalog.jsonl.gz",
    "BTC-USDT-SWAP.cases.jsonl.gz",
    "ETH-USDT-SWAP.cases.jsonl.gz",
    "FINANCIAL_RESULT.json",
    "RUN_RECEIPT.json",
    "RUN_CHECKPOINT.json",
)


class FinancialGateBlocked(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git_show(commit: str, relative: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT)


def _assert_ancestor(commit: str) -> None:
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _verify_committed_file(path: Path, commit: str) -> None:
    relative = str(path.relative_to(ROOT)).replace("\\", "/")
    if path.read_bytes() != _git_show(commit, relative):
        raise FinancialGateBlocked(f"COMMITTED_BYTES_CHANGED:{relative}")


def _authorization() -> dict:
    from verify_machine_strategy_v4_1_implementation_v1 import resume

    resume(IMPLEMENTATION_MANIFEST_SHA256)
    if _sha(IMPLEMENTATION_MANIFEST) != IMPLEMENTATION_MANIFEST_SHA256:
        raise FinancialGateBlocked("IMPLEMENTATION_MANIFEST_CHANGED")
    for commit in (IMPLEMENTATION_FREEZE_COMMIT, PREREG_COMMIT, AUTH_COMMIT):
        _assert_ancestor(commit)
    _verify_committed_file(IMPLEMENTATION_MANIFEST, IMPLEMENTATION_FREEZE_COMMIT)
    _verify_committed_file(PREREG, PREREG_COMMIT)
    _verify_committed_file(AUTH, AUTH_COMMIT)
    prereg = json.loads(PREREG.read_text())
    auth = json.loads(AUTH.read_text())
    if prereg.get("gate") != GATE or auth.get("gate") != GATE:
        raise FinancialGateBlocked("WRONG_FINANCIAL_GATE")
    if (
        auth.get("authorization_state")
        != "ONE_SHOT_HISTORICAL_DEVELOPMENT_FINANCIAL_RUN_AUTHORIZED"
    ):
        raise FinancialGateBlocked("ONE_SHOT_NOT_AUTHORIZED")
    if auth.get("historical_runs_remaining") != 1:
        raise FinancialGateBlocked("ONE_SHOT_COUNT_NOT_ONE")
    if prereg.get("implementation_manifest_sha256") != IMPLEMENTATION_MANIFEST_SHA256:
        raise FinancialGateBlocked("PREREG_IMPLEMENTATION_PIN_MISMATCH")
    batch = (ROOT / "agent_control/CURRENT_BATCH.md").read_text()
    if (
        "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_OPEN" not in batch
        or "one-shot" not in batch.lower()
    ):
        raise FinancialGateBlocked("FINANCIAL_CAMPAIGN_NOT_ACTIVE")
    for name in (*FINAL_FILES, "RUN_STARTED.json"):
        if (OUT / name).exists():
            raise FinancialGateBlocked("ONE_SHOT_OUTPUT_ALREADY_EXISTS")
    return prereg


def _epoch(text: str) -> int:
    return int(datetime.fromisoformat(text).timestamp())


def _jsonable(value):
    if isinstance(value, Decimal):
        if value == 0:
            return "0"
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _compact(value) -> bytes:
    return json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _bar_record(bar) -> dict:
    return {
        "start": bar.start,
        "end": bar.end,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
    }


def _funding_inputs(product: str, native) -> list[tuple[int, Decimal, Decimal]]:
    binding = json.loads((V3_COMPAT_DEST / "COST_FUNDING_BINDING.json").read_text())
    side = product.split("-")[0]
    relative = binding["source_inputs"][side + "_funding_csv"]
    expected = binding["source_inputs"][side + "_funding_csv_sha256"]
    path = ROOT / relative
    if _sha(path) != expected:
        raise FinancialGateBlocked("FUNDING_SOURCE_CHANGED")
    closes = {b.end: b.close for b in native}
    rows = []
    for row in csv.DictReader(path.open()):
        at = int(row["funding_time_utc_ms"]) // 1000
        if row["instrument_name"] != product or at not in closes:
            raise FinancialGateBlocked("FUNDING_IDENTITY_OR_MARK_PROXY_MISSING")
        rows.append((at, Decimal(row["funding_rate"]), closes[at]))
    return rows


def _funding_min(state: dict, rows, quantity: Decimal):
    flo, fhi = state["fill_time_bounds"]
    xlo, xhi = state["event_time_bounds"]
    relevant = [r for r in rows if flo <= r[0] <= xhi]
    fill_slots = {(flo, -1), (flo, 1), (fhi, -1), (fhi, 1)}
    exit_slots = {(xlo, -1), (xlo, 1), (xhi, -1), (xhi, 1)}
    for at, _, _ in relevant:
        if flo <= at <= fhi:
            fill_slots.update(((at, -1), (at, 1)))
        if xlo <= at <= xhi:
            exit_slots.update(((at, -1), (at, 1)))
    direction = Decimal(1 if state["direction"] == "LONG" else -1)
    values = []
    for fill in sorted(fill_slots):
        for exit_ in sorted(exit_slots):
            if fill > exit_:
                continue
            selected = [r for r in relevant if fill < (r[0], 0) < exit_]
            cash = sum(
                (-direction * rate * quantity * price for _, rate, price in selected),
                Decimal(0),
            )
            values.append((cash, fill, exit_, [r[0] for r in selected]))
    if not values:
        raise core.ContractWait("WAIT_COHERENT_FUNDING_TIMELINE")
    cash, fill, exit_, settlements = min(
        values, key=lambda row: (row[0], row[1], row[2])
    )
    return cash, {
        "model_fill_event_slot": fill,
        "model_exit_event_slot": exit_,
        "settlements_included": settlements,
        "slot_order": "-1 before same-timestamp settlement, +1 after; modeled witness, not exact observed time",
    }


def _closed_cash(state: dict, funding_rows) -> dict:
    with localcontext() as ctx:
        ctx.prec = 80
        ctx.rounding = ROUND_HALF_EVEN
        q = Decimal(state["quantity_base"])
        entry = Decimal(state["fill_price"])
        exit_price = Decimal(state["exit_price"])
        unit = Decimal(state["fixed_R_unit"])
        if q <= 0 or unit <= 0:
            raise core.ContractReject("REJECT_FIXED_CASH_R_UNIT")
        funded, witness = _funding_min(state, funding_rows, q)
        direction = Decimal(1 if state["direction"] == "LONG" else -1)
        gross = direction * q * (exit_price - entry)
        columns = {}
        for name, multiplier in (("base", Decimal(1)), ("doubled", Decimal(2))):
            fees = multiplier * Decimal("0.0006") * q * (entry + exit_price)
            slippage = multiplier * Decimal("0.0002") * q * (entry + exit_price)
            net = gross - fees - slippage + funded
            columns[name] = {
                "gross_cash": gross,
                "fees_cash": fees,
                "slippage_cash": slippage,
                "funding_cash": funded,
                "net_cash": net,
                "gross_R": gross / unit,
                "fees_R": fees / unit,
                "slippage_R": slippage / unit,
                "funding_R": funded / unit,
                "net_R": net / unit,
            }
        return {"columns": columns, "funding_timing_witness": witness}


def _scenario_state(order: dict, plan: dict, grid: dict) -> dict:
    if plan["status"] != "ELIGIBLE_PENDING":
        return {
            "scenario_id": plan["scenario_id"],
            "status": "UNRESOLVED"
            if plan["status"] == "UNRESOLVED"
            else "SCENARIO_INELIGIBLE",
            "reason": plan.get("reason", "INELIGIBLE_AT_EMISSION"),
            "trade_entry_allowed": False,
        }
    state = {
        **order,
        **plan,
        "status": "PENDING",
        "scenario_id": plan["scenario_id"],
        "model_grid_id": grid["id"],
        "expires_at": order["parent_deadline_at"],
        "fixed_R_unit": order["fixed_R_unit"],
        "trade_entry_allowed": False,
    }
    return state


def _retire_pending(state: dict, flags: dict) -> dict:
    reasons = sorted(k for k, value in flags.items() if k != "known_at" and value)
    if "data_integrity_stop" in reasons:
        return {
            **state,
            "status": "UNKNOWN_DATA_GAP",
            "observed_at": flags["known_at"],
            "retirement_reasons": reasons,
        }
    return {
        **state,
        "status": "UNFILLED_EXPIRED" if flags.get("deadline") else "UNFILLED_RETIRED",
        "observed_at": flags["known_at"],
        "retirement_reasons": reasons,
    }


@_precision(50)
def _drive_decision_group(
    product: str, market, funding_rows, orders: list[dict], start: int, end: int
):
    decision = orders[0]["decision_at"]
    if any(order["decision_at"] != decision for order in orders):
        raise FinancialGateBlocked("MIXED_DECISION_GROUP")
    adapter = V41HistoricalAdapter(product, market, start, end)
    replay_orders, _ = adapter.catalog(cutoff=decision)
    replay = {row["case_id"]: row for row in replay_orders}
    for order in orders:
        if order["case_id"] not in replay or _compact(
            replay[order["case_id"]]
        ) != _compact(order):
            raise FinancialGateBlocked("CATALOG_REPLAY_MISMATCH")

    grids = {grid["id"]: grid for grid in scenarios(product)}
    states = {
        order["case_id"]: [
            _scenario_state(order, plan, grids[plan["scenario_id"]])
            for plan in order["scenario_plans"]
        ]
        for order in orders
    }
    native = market[15]
    future = [bar for bar in native if decision <= bar.start < end]

    def active(state):
        return state["status"] in {"PENDING", "FILLED"}

    for bar in future:
        if not any(active(s) for rows in states.values() for s in rows):
            break
        # Preserve native context exactly as known at OPEN before advancing this bar.
        for tf, frame in adapter.frames.items():
            if (
                frame.cursor < len(frame.bars)
                and frame.bars[frame.cursor].start == bar.start
            ):
                adapter.native_context_open[(tf, bar.start)] = (
                    frame.context["direction"]
                    if frame.context and frame.context["known_at"] <= bar.start
                    else None
                )

        for order in orders:
            rows = states[order["case_id"]]
            plans = {p["scenario_id"]: p for p in order["scenario_plans"]}
            for index, state in enumerate(rows):
                if active(state) and bar.start != state.get(
                    "last_observed_end", decision
                ):
                    rows[index] = {
                        **state,
                        "status": "UNKNOWN_DATA_GAP",
                        "observed_at": bar.start,
                    }
                    continue
                if state["status"] == "PENDING":
                    flags = adapter.lifecycle_flags(
                        order, bar.start, plans[state["scenario_id"]]
                    )
                    if flags["known_at"] > bar.start:
                        raise FinancialGateBlocked("FUTURE_PENDING_LIFECYCLE")
                    if any(value for key, value in flags.items() if key != "known_at"):
                        rows[index] = _retire_pending(state, flags)
                        continue
                if state["status"] not in {"PENDING", "FILLED"}:
                    continue
                grid = grids[state["scenario_id"]]
                try:
                    next_state = _model_observer(state, _bar_record(bar), [grid])
                except core.ContractWait as exc:
                    rows[index] = {
                        **state,
                        "status": "UNKNOWN_DATA_GAP"
                        if "DATA_GAP" in str(exc)
                        else "UNRESOLVED",
                        "reason": str(exc),
                        "observed_at": bar.end,
                    }
                    continue
                if next_state["status"] == "EXIT_OBSERVED":
                    next_state = {**next_state, "status": "CLOSED"}
                    next_state.update(_closed_cash(next_state, funding_rows))
                    next_state["holding_time_bounds"] = core.holding_duration_bounds(
                        next_state["fill_time_bounds"], next_state["event_time_bounds"]
                    )
                rows[index] = next_state

        # Current-bar execution has happened. Only now publish completed source state/contact.
        for tf in (1440, 240, 60, 15):
            adapter.frames[tf].advance(bar.end)
        adapter.publish_contacts(bar.end)
        for order in orders:
            for index, state in enumerate(states[order["case_id"]]):
                if state["status"] == "PENDING":
                    flags = adapter.lifecycle_flags(
                        order, bar.end, plans_for(order, state)
                    )
                    if flags["known_at"] > bar.end:
                        raise FinancialGateBlocked("FUTURE_PENDING_LIFECYCLE")
                    if any(value for key, value in flags.items() if key != "known_at"):
                        states[order["case_id"]][index] = _retire_pending(state, flags)

    observed_through = market[15][-1].end
    for rows in states.values():
        for index, state in enumerate(rows):
            if state["status"] in {"PENDING", "FILLED"}:
                rows[index] = core.censor_eof(state, observed_through)
    return states


def plans_for(order, state):
    return next(
        p for p in order["scenario_plans"] if p["scenario_id"] == state["scenario_id"]
    )


@_precision(80)
def _adverse_case(order: dict, states: list[dict]) -> dict:
    expected = [grid["id"] for grid in scenarios(order["product"])]
    if [row["scenario_id"] for row in states] != expected:
        raise FinancialGateBlocked("ALL_NINE_SCENARIOS_REQUIRED")
    closed = [row for row in states if row["status"] == "CLOSED"]
    if len(closed) == 9:
        status = "CLOSED"
    elif all(
        row["status"]
        in {
            "UNFILLED_RETIRED",
            "UNFILLED_EXPIRED",
            "ORDER_CENSORED_EOF",
            "GAP_INVALIDATED_BEFORE_FILL",
        }
        for row in states
    ):
        status = "ALL_SCENARIOS_NO_FILL"
    else:
        status = "COMPATIBILITY_DISAGREEMENT"
    adverse = {}
    for column in ("base", "doubled"):
        if closed:
            worst = min(
                closed,
                key=lambda row: (
                    Decimal(row["columns"][column]["net_cash"]),
                    row["scenario_id"],
                ),
            )
            adverse[column] = {
                **worst["columns"][column],
                "scenario_id": worst["scenario_id"],
                "observed_at": worst["observed_at"],
                "event_time_bounds": worst["event_time_bounds"],
                "holding_time_bounds": worst["holding_time_bounds"],
                "exit_reason": worst["exit_reason"],
            }
    return _jsonable(
        {
            "case_id": order["case_id"],
            "venue": "OKX",
            "product": order["product"],
            "direction": order["direction"],
            "branch": order["branch"],
            "setup_tf": order["setup_tf"],
            "decision_at": order["decision_at"],
            "context": order["context"],
            "reference_geometry": {
                "entry": order["entry"],
                "stop": order["stop"],
                "target": order["target"],
                "fixed_R_unit": order["fixed_R_unit"],
                "nearest_fta_id": order["nearest_fta_id"],
            },
            "status": status,
            "adverse": adverse,
            "all_scenarios": states,
            "closed_values_diagnostic_only": status != "CLOSED",
            "trade_entry_allowed": False,
        }
    )


@_precision(80)
def _group_stats(cases: list[dict], column: str) -> dict:
    closed = [row for row in cases if row["status"] == "CLOSED"]
    ledger = sorted(
        closed,
        key=lambda row: (row["adverse"][column]["observed_at"], row["case_id"]),
    )
    values = [Decimal(row["adverse"][column]["net_R"]) for row in ledger]
    cash = [Decimal(row["adverse"][column]["net_cash"]) for row in ledger]
    gross = [Decimal(row["adverse"][column]["gross_R"]) for row in ledger]
    wins = sum(value > 0 for value in values)
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    n = len(values)
    rate = Decimal(wins) / n if n else None
    wilson = None
    if rate is not None:
        z = Decimal("1.959963984540054")
        wilson = (
            rate
            + z * z / (2 * n)
            - z * (rate * (1 - rate) / n + z * z / (4 * n * n)).sqrt()
        ) / (1 + z * z / n)
    equity = peak = drawdown = Decimal(0)
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if value < 0 else 0
        max_streak = max(max_streak, streak)
    components = {
        key: sum((Decimal(row["adverse"][column][key]) for row in closed), Decimal(0))
        for key in (
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
    return _jsonable(
        {
            "CLOSED": n,
            "WIN": wins,
            "LOSS": n - wins,
            "win_rate": rate,
            "wilson_95pct_lower": wilson,
            "profit_factor_R": gains / losses
            if losses
            else "Infinity"
            if gains
            else None,
            "expectancy_R": sum(values, Decimal(0)) / n if n else None,
            "net_R": sum(values, Decimal(0)),
            "gross_R": sum(gross, Decimal(0)),
            "net_cash": sum(cash, Decimal(0)),
            "max_drawdown_R": drawdown,
            "max_consecutive_net_losses": max_streak,
            "components": components,
        }
    )


def _breakdowns(cases: list[dict], column: str) -> dict:
    dimensions = {
        "product": lambda row: row["product"],
        "direction": lambda row: row["direction"],
        "coin_direction": lambda row: row["product"] + ":" + row["direction"],
        "family": lambda row: row["branch"],
        "setup_tf": lambda row: str(row["setup_tf"]),
    }
    result = {}
    for dimension, key_fn in dimensions.items():
        buckets = defaultdict(list)
        for row in cases:
            if row["status"] == "CLOSED":
                buckets[key_fn(row)].append(row)
        result[dimension] = {
            key: _group_stats(rows, column) for key, rows in sorted(buckets.items())
        }
    return result


@_precision(80)
def _concentration(cases: list[dict], column: str) -> dict:
    quarters: defaultdict[str, Decimal] = defaultdict(Decimal)
    coins: defaultdict[str, Decimal] = defaultdict(Decimal)
    for row in cases:
        if row["status"] != "CLOSED":
            continue
        value = Decimal(row["adverse"][column]["net_R"])
        at = datetime.fromtimestamp(row["adverse"][column]["observed_at"], UTC)
        quarter = f"{at.year}-Q{(at.month - 1) // 3 + 1}"
        quarters[quarter] += value
        coins[row["product"]] += value
    positive_quarters = {k: v for k, v in quarters.items() if v > 0}
    positive_coins = {k: v for k, v in coins.items() if v > 0}
    q_total = sum(positive_quarters.values(), Decimal(0))
    c_total = sum(positive_coins.values(), Decimal(0))
    return _jsonable(
        {
            "calendar_quarters_R": dict(sorted(quarters.items())),
            "coins_R": dict(sorted(coins.items())),
            "largest_calendar_quarter_profit_share": (
                max(positive_quarters.values()) / q_total if q_total else None
            ),
            "largest_coin_profit_share": max(positive_coins.values()) / c_total
            if c_total
            else None,
        }
    )


def _pf_number(value):
    if value == "Infinity":
        return Decimal("Infinity")
    return Decimal(value) if value is not None else None


@_precision(80)
def _qualification(cases: list[dict], prereg: dict) -> dict:
    base = _group_stats(cases, "base")
    doubled = _group_stats(cases, "doubled")
    breakdowns = _breakdowns(cases, "base")
    concentration = _concentration(cases, "base")
    disagreements = sum(row["status"] == "COMPATIBILITY_DISAGREEMENT" for row in cases)
    unknown_statuses = {
        "WAIT_INTRABAR_ORDER",
        "OPEN_CENSORED_EOF",
        "UNKNOWN_DATA_GAP",
        "UNRESOLVED",
    }
    unknown = sum(
        1
        for row in cases
        for state in row["all_scenarios"]
        if state["status"] in unknown_statuses
    )
    q = prereg["qualification"]
    checks = {}
    checks["closed_trades_min"] = base["CLOSED"] >= q["closed_trades_min"]
    checks["win_rate_min"] = base["win_rate"] is not None and Decimal(
        base["win_rate"]
    ) >= Decimal(q["win_rate_min"])
    pf = _pf_number(base["profit_factor_R"])
    checks["profit_factor_min"] = pf is not None and pf >= Decimal(
        q["profit_factor_min"]
    )
    checks["expectancy_positive"] = (
        base["expectancy_R"] is not None and Decimal(base["expectancy_R"]) > 0
    )
    checks["net_R_positive"] = Decimal(base["net_R"]) > 0
    checks["net_cash_positive"] = Decimal(base["net_cash"]) > 0
    doubled_pf = _pf_number(doubled["profit_factor_R"])
    checks["doubled_profit_factor_min"] = (
        doubled_pf is not None
        and doubled_pf >= Decimal(q["doubled_cost_profit_factor_min"])
    )
    checks["doubled_net_positive"] = (
        Decimal(doubled["net_R"]) > 0 and Decimal(doubled["net_cash"]) > 0
    )
    checks["max_drawdown"] = Decimal(base["max_drawdown_R"]) <= Decimal(
        q["max_drawdown_R_max"]
    )
    checks["max_loss_streak"] = (
        base["max_consecutive_net_losses"] <= q["max_consecutive_net_losses_max"]
    )
    checks["wilson"] = base["wilson_95pct_lower"] is not None and Decimal(
        base["wilson_95pct_lower"]
    ) >= Decimal(q["wilson_95pct_win_rate_lower_bound_min"])
    coin_direction = breakdowns["coin_direction"]
    required_groups = [
        "BTC-USDT-SWAP:LONG",
        "BTC-USDT-SWAP:SHORT",
        "ETH-USDT-SWAP:LONG",
        "ETH-USDT-SWAP:SHORT",
    ]
    checks["coin_direction_closed_min"] = all(
        key in coin_direction
        and coin_direction[key]["CLOSED"] >= q["each_coin_direction_closed_min"]
        for key in required_groups
    )
    checks["coin_direction_net_positive"] = all(
        key in coin_direction
        and Decimal(coin_direction[key]["net_R"]) > 0
        and Decimal(coin_direction[key]["net_cash"]) > 0
        for key in required_groups
    )
    quarter_share = concentration["largest_calendar_quarter_profit_share"]
    coin_share = concentration["largest_coin_profit_share"]
    checks["quarter_concentration"] = quarter_share is not None and Decimal(
        quarter_share
    ) <= Decimal(q["largest_calendar_quarter_profit_share_max"])
    checks["coin_concentration"] = coin_share is not None and Decimal(
        coin_share
    ) <= Decimal(q["largest_coin_profit_share_max"])
    checks["filled_unknown_exit"] = unknown <= q["filled_unknown_exit_max"]
    checks["compatibility_agreement"] = disagreements == 0
    decision = (
        "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_PASS"
        if all(checks.values())
        else "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP"
    )
    return {
        "decision": decision,
        "checks": checks,
        "base": base,
        "doubled": doubled,
        "breakdowns": breakdowns,
        "concentration": concentration,
        "compatibility_disagreements": disagreements,
        "filled_unknown_exit_states": unknown,
    }


def _write_gzip_jsonl(path: Path, rows: list[dict]) -> None:
    payload = b"\n".join(_compact(row) for row in rows) + (b"\n" if rows else b"")
    path.write_bytes(gzip.compress(payload, mtime=0))


@_precision(50)
def _run() -> dict:
    prereg = _authorization()
    # Atomic durable reservation prevents concurrent runs and silent failed-run retries.
    with (OUT / "RUN_STARTED.json").open("x") as started:
        json.dump(
            {
                "gate": GATE,
                "state": "ONE_SHOT_RESERVED",
                "runner_sha256": _sha(Path(__file__)),
                "preregistration_sha256": _sha(PREREG),
                "authorization_sha256": _sha(AUTH),
                "trade_entry_allowed": False,
            },
            started,
        )
    start = _epoch(prereg["development_window"]["start_utc"])
    end = _epoch(prereg["development_window"]["end_exclusive_utc"])
    catalogs = {}
    cases_by_product = {}
    catalog_audit = {}

    # Build the frozen catalog first. Candidate counts are recorded but never used for rule selection.
    markets = {}
    funding = {}
    for product in prereg["products"]:
        market = market_inputs(product)
        markets[product] = market
        adapter = V41HistoricalAdapter(product, market, start, end)
        orders, audit = adapter.catalog()
        if (
            audit["historical_position_engine_calls"] != 0
            or audit["financial_outcomes_generated"]
        ):
            raise FinancialGateBlocked("SOURCE_ADAPTER_FINANCIAL_ISOLATION_BROKEN")
        source_receipt = json.loads(
            (
                IMPLEMENTATION_MANIFEST.parent / "SOURCE_PREFIX_REPLAY_RECEIPT.json"
            ).read_text()
        )
        frozen_source = ROOT / source_receipt["products"][product]["source_artifact"]
        frozen_catalog = json.loads(gzip.decompress(frozen_source.read_bytes()))[
            "preentry_model_catalog"
        ]
        if _compact(orders) != _compact(frozen_catalog):
            raise FinancialGateBlocked("FROZEN_SOURCE_CATALOG_CHANGED_BEFORE_FINANCE")
        del frozen_catalog
        catalogs[product] = orders
        catalog_audit[product] = {
            "candidate_count": len(orders),
            "raw_origin_count": len(audit["raw_origins"]),
            "source_digest": sha256(
                _compact({"orders": orders, "audit": audit})
            ).hexdigest(),
        }
        funding[product] = _funding_inputs(product, market[15])
        del adapter, audit
        print("SOURCE_CATALOG_COMPLETE", product, flush=True)

    for product in prereg["products"]:
        groups = defaultdict(list)
        for order in catalogs[product]:
            groups[order["decision_at"]].append(order)
        evaluated = {}
        for decision, orders in sorted(groups.items()):
            group_states = _drive_decision_group(
                product,
                markets[product],
                funding[product],
                sorted(orders, key=lambda row: row["case_id"]),
                start,
                end,
            )
            for order in orders:
                evaluated[order["case_id"]] = _adverse_case(
                    order, group_states[order["case_id"]]
                )
            print("DECISION_GROUP_COMPLETE", product, decision, flush=True)
        cases_by_product[product] = [
            evaluated[row["case_id"]] for row in catalogs[product]
        ]

    all_cases = [
        row for product in prereg["products"] for row in cases_by_product[product]
    ]
    qualification = _qualification(all_cases, prereg)
    result = _jsonable(
        {
            "gate": GATE,
            "strategy_version": VERSION,
            "venue": "OKX",
            "development_window": prereg["development_window"],
            "candidate_count": sum(len(rows) for rows in catalogs.values()),
            "candidate_count_by_product": {k: len(v) for k, v in catalogs.items()},
            "case_status_counts": {
                status: sum(row["status"] == status for row in all_cases)
                for status in sorted({row["status"] for row in all_cases})
            },
            "qualification": qualification,
            "model_limitations": [
                "historical tick/lot epochs unverified; nine synthetic compatibility grids are modeled stress",
                "historical ordinary account-applicable OKX fee is unverified; frozen model costs used",
                "mark/queue/fill reality and API publication delay are unverified",
                "development history is exposed and is not pristine OOS",
            ],
            "trade_entry_allowed": False,
            "PAPER": False,
            "LIVE": False,
        }
    )

    OUT.mkdir(parents=True, exist_ok=True)
    for product in prereg["products"]:
        _write_gzip_jsonl(OUT / f"{product}.catalog.jsonl.gz", catalogs[product])
        _write_gzip_jsonl(OUT / f"{product}.cases.jsonl.gz", cases_by_product[product])
    (OUT / "FINANCIAL_RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    receipt = {
        "gate": GATE,
        "implementation_manifest_sha256": IMPLEMENTATION_MANIFEST_SHA256,
        "implementation_freeze_commit": IMPLEMENTATION_FREEZE_COMMIT,
        "preregistration_commit": PREREG_COMMIT,
        "authorization_commit": AUTH_COMMIT,
        "catalog_audit": catalog_audit,
        "historical_run_count": 1,
        "financial_result_decision": result["qualification"]["decision"],
        "trade_entry_allowed": False,
    }
    (OUT / "RUN_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    artifacts = {
        name: _sha(OUT / name)
        for name in FINAL_FILES
        if name != "RUN_CHECKPOINT.json" and (OUT / name).exists()
    }
    checkpoint = {
        "gate": GATE,
        "state": "ONE_SHOT_RESULT_COMMITTED_TO_FILESYSTEM",
        "artifacts_sha256": artifacts,
        "decision": result["qualification"]["decision"],
        "historical_run_count": 1,
    }
    (OUT / "RUN_CHECKPOINT.json").write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return result


def _verify_existing(expected: str | None) -> dict:
    if not isinstance(expected, str) or len(expected) != 64:
        raise FinancialGateBlocked("EXTERNAL_RUN_CHECKPOINT_PIN_REQUIRED")
    if not (OUT / "RUN_CHECKPOINT.json").exists():
        raise FinancialGateBlocked("NO_RUN_CHECKPOINT")
    checkpoint = json.loads((OUT / "RUN_CHECKPOINT.json").read_text())
    if set(checkpoint["artifacts_sha256"]) != set(FINAL_FILES) - {
        "RUN_CHECKPOINT.json"
    }:
        raise FinancialGateBlocked("INCOMPLETE_RUN_CHECKPOINT")
    for name, digest in checkpoint["artifacts_sha256"].items():
        if _sha(OUT / name) != digest:
            raise FinancialGateBlocked(f"RESULT_ARTIFACT_CHANGED:{name}")
    current = _sha(OUT / "RUN_CHECKPOINT.json")
    if expected and current != expected:
        raise FinancialGateBlocked("RUN_CHECKPOINT_SHA_MISMATCH")
    return {"checkpoint_sha256": current, "decision": checkpoint["decision"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-authorization", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-checkpoint-sha256")
    args = parser.parse_args()
    selected = sum((args.verify_authorization, args.run, args.resume_existing))
    if selected != 1:
        raise SystemExit("choose exactly one mode")
    if args.verify_authorization:
        prereg = _authorization()
        print(json.dumps({"gate": prereg["gate"], "authorized": True}, sort_keys=True))
    elif args.run:
        print(json.dumps(_run(), ensure_ascii=False, sort_keys=True))
    else:
        print(
            json.dumps(
                _verify_existing(args.expected_checkpoint_sha256), sort_keys=True
            )
        )


if __name__ == "__main__":
    main()
