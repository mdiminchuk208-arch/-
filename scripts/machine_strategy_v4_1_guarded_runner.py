"""V4.1 guarded execution. Readiness exposes named synthetic fixtures only."""

from __future__ import annotations

import csv
import json
from contextvars import ContextVar
from copy import deepcopy
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from functools import wraps
from hashlib import sha256
from pathlib import Path

import machine_strategy_v3_contracts as core
from machine_strategy_v2_core import serial
from machine_strategy_v4_1_execution_binding import (
    all_scenario_plans as _serialized_plans,
)
from machine_strategy_v4_readiness_core import GateTelemetry, V4Wait, dec, pending_alive
from okx_v3_compatibility_binding_v1 import _model_observer, scenarios

ROOT = Path(__file__).resolve().parents[1]
_ACTIVE = ContextVar("v4_registered_fixture_nonce", default=None)


class FinancialBlocked(RuntimeError):
    pass


def _design_scope(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_HALF_EVEN
            return function(*args, **kwargs)

    return scoped


def fingerprint(value):
    return sha256(
        json.dumps(serial(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _authorization_hooks():
    # Issued nonces live in a closure, not in a caller-settable context dictionary.
    issued = {}

    def issue(name):
        order, bars, funding, events = fixture(name)
        nonce = object()
        issued[nonce] = {
            "fixture_name": name,
            "allowed_inputs": frozenset({fingerprint([order, bars, funding])}),
            "events": deepcopy(events),
        }
        return nonce

    def scope():
        nonce = _ACTIVE.get()
        try:
            result = issued.get(nonce)
        except TypeError:
            result = None
        if result is None:
            raise FinancialBlocked("NO_AUTHORIZED_V4_SCOPE")
        return deepcopy(result)

    def revoke(nonce):
        issued.pop(nonce, None)

    return issue, scope, revoke


_fixture_issue, _scope, _fixture_revoke = _authorization_hooks()


def _registered_state(state, rows):
    scope = _scope()
    order, bars, funding, _ = fixture(scope["fixture_name"])
    if (
        fingerprint(rows) != fingerprint(funding)
        or state.get("case_id") != order["case_id"]
    ):
        raise FinancialBlocked("FINANCIAL_INPUT_NOT_REGISTERED_FIXTURE")
    if (
        state.get("direction") != order["direction"]
        or dec(state["fixed_R_unit"]) != order["fixed_R_unit"]
    ):
        raise FinancialBlocked("FIXTURE_RISK_OR_DIRECTION_CHANGED")
    plan = next(
        (
            p
            for p in all_scenario_plans(order, completed_close=order["decision_close"])
            if p["scenario_id"] == state.get("scenario_id")
        ),
        None,
    )
    if plan is None or plan["status"] != "ELIGIBLE_PENDING":
        raise FinancialBlocked("FIXTURE_SCENARIO_CHANGED")
    if (
        dec(state["fill_price"]) != plan["entry"]
        or dec(state["quantity_base"]) != plan["quantity_base"]
    ):
        raise FinancialBlocked("FIXTURE_FILL_OR_SIZE_CHANGED")
    allowed = {
        plan["stop"],
        plan["target"],
        *[dec(b[k]) for b in bars for k in ("open", "close")],
    }
    if dec(state["exit_price"]) not in allowed:
        raise FinancialBlocked("FIXTURE_EXIT_CHANGED")
    if any(
        type(t) is not int or not bars[0]["start"] <= t <= bars[-1]["end"]
        for key in ("fill_time_bounds", "event_time_bounds")
        for t in state[key]
    ):
        raise FinancialBlocked("FIXTURE_EVENT_TIME_CHANGED")


def _funding_min(state, rows):
    _registered_state(state, rows)
    flo, fhi = state["fill_time_bounds"]
    xlo, xhi = state["event_time_bounds"]
    relevant = [r for r in rows if flo <= r[0] <= xhi]
    fs = {(flo, -1), (flo, 1), (fhi, -1), (fhi, 1)}
    xs = {(xlo, -1), (xlo, 1), (xhi, -1), (xhi, 1)}
    for t, _, _ in relevant:
        if flo <= t <= fhi:
            fs.update(((t, -1), (t, 1)))
        if xlo <= t <= xhi:
            xs.update(((t, -1), (t, 1)))
    d = Decimal(1 if state["direction"] == "LONG" else -1)
    q = dec(state["quantity_base"])
    values = []
    for f in sorted(fs):
        for x in sorted(xs):
            if f > x:
                continue
            selected = [r for r in relevant if f < (r[0], 0) < x]
            cash = sum(
                (-d * dec(rate) * q * dec(price) for _, rate, price in selected),
                Decimal(0),
            )
            values.append((cash, f, x, [r[0] for r in selected]))
    if not values:
        raise V4Wait("WAIT_COHERENT_FUNDING_TIMELINE")
    cash, f, x, times = min(values, key=lambda r: (r[0], r[1], r[2]))
    return cash, {
        "model_fill_event_slot": f,
        "model_exit_event_slot": x,
        "settlements_included": times,
        "slot_order": "-1 before same-timestamp settlement,+1 after; modeled coherent witness",
    }


def _cash(state, rows):
    _registered_state(state, rows)
    if state["status"] != "CLOSED":
        raise FinancialBlocked("CASH_REQUIRES_CLOSED_STATE")
    with localcontext() as ctx:
        ctx.prec = 80
        ctx.rounding = ROUND_HALF_EVEN
        q, e, x, u = (
            dec(state[k])
            for k in ("quantity_base", "fill_price", "exit_price", "fixed_R_unit")
        )
        if min(q, e, x, u) <= 0:
            raise FinancialBlocked("INVALID_CASH_INPUT")
        funding, witness = _funding_min(state, rows)
        gross = (1 if state["direction"] == "LONG" else -1) * q * (x - e)
        columns = {}
        for name, m in (("base", Decimal(1)), ("doubled", Decimal(2))):
            fees = m * Decimal("0.0006") * q * (e + x)
            slip = m * Decimal("0.0002") * q * (e + x)
            net = gross - fees - slip + funding
            columns[name] = {
                "gross_cash": gross,
                "fees_cash": fees,
                "slippage_cash": slip,
                "funding_cash": funding,
                "net_cash": net,
                "net_R": net / u,
                "gross_R": gross / u,
                "fees_R": fees / u,
                "slippage_R": slip / u,
                "funding_R": funding / u,
            }
        return {"columns": columns, "funding_timing_witness": witness}


def _adverse(order, states):
    _scope()
    ids = [s["scenario_id"] for s in states]
    if ids != [s["id"] for s in scenarios(order["product"])]:
        raise FinancialBlocked("INCOMPLETE_SCENARIO_SET")
    closed = [s for s in states if s["status"] == "CLOSED"]
    nofill = {
        "UNFILLED_EXPIRED",
        "GAP_INVALIDATED_BEFORE_FILL",
        "RETIRED_PENDING",
        "ORDER_CENSORED_EOF",
    }
    ineligible = [s for s in states if s["status"] == "INELIGIBLE"]
    known_filled = [s for s in states if "fill_price" in s]
    disagreement = (
        bool(ineligible and len(ineligible) != 9)
        or bool(closed and len(closed) != 9)
        or bool(known_filled and any(s["status"] in nofill for s in states))
    )
    unknown = any(
        s["status"]
        in {
            "UNRESOLVED",
            "UNKNOWN_DATA_GAP",
            "WAIT_INTRABAR_ORDER",
            "OPEN_CENSORED_EOF",
        }
        for s in states
    )
    columns = {}
    if closed:
        for name in ("base", "doubled"):
            worst = min(
                closed,
                key=lambda s: (dec(s["columns"][name]["net_cash"]), s["scenario_id"]),
            )
            columns[name] = {
                "scenario_id": worst["scenario_id"],
                **worst["columns"][name],
            }
    return {
        "case_id": order["case_id"],
        "scenario_states": states,
        "adverse_columns": columns,
        "status": "COMPATIBILITY_DISAGREEMENT"
        if disagreement
        else "CLOSED"
        if len(closed) == 9
        else "NO_FILL"
        if all(s["status"] in nofill for s in states)
        else "UNRESOLVED",
        "qualification_stop": disagreement or unknown,
        "fixed_R_unit": order["fixed_R_unit"],
        "trade_entry_allowed": False,
    }


def all_scenario_plans(order, *, completed_close):
    # Decode frozen design strings exactly; no geometry/quantity recomputation at ledger precision.
    results = _serialized_plans(order, completed_close=completed_close)
    for plan in results:
        if plan["status"] == "ELIGIBLE_PENDING":
            plan["canonical_design_transport"] = {
                key: plan[key]
                for key in (
                    "entry",
                    "stop",
                    "target",
                    "tick",
                    "quantity_base",
                    "quantity_contracts",
                    "exec_low",
                    "exec_high",
                )
            }
            for key in plan["canonical_design_transport"]:
                plan[key] = Decimal(plan[key])
    return results


@_design_scope
def _drive_case(order, bars, funding):
    scope = _scope()
    if fingerprint([order, bars, funding]) not in scope["allowed_inputs"]:
        raise FinancialBlocked("INPUTS_NOT_REGISTERED")
    # Reference catalog emission requires all immutable lifecycle/risk handles.
    required = {
        "fixed_R_unit",
        "entry_poi_id",
        "selected_fta_object",
        "formation_known_at",
        "confirmation_known_at",
        "emission_decision_at",
        "stop_anchor",
        "setup_tf_seconds",
        "parent_deadline_at",
    }
    if not required <= order.keys():
        raise FinancialBlocked("INCOMPLETE_FROZEN_ORDER")
    plans = all_scenario_plans(order, completed_close=order["decision_close"])
    states = []
    for grid, plan in zip(scenarios(order["product"]), plans, strict=True):
        if plan["status"] != "ELIGIBLE_PENDING":
            states.append(plan)
            continue
        state = {
            **deepcopy(order),
            **plan,
            "status": "PENDING",
            "model_grid_id": grid["id"],
            "expires_at": order["parent_deadline_at"],
            "last_observed_end": order["decision_at"],
        }
        if "_h4_" in scope["fixture_name"]:
            from machine_strategy_v4_1_synthetic_source_bridge import ClosedSourceBridge

            lifecycle = ClosedSourceBridge(order, bars)
        else:
            lifecycle = FixtureLifecycle(scope["events"])
        sink = GateTelemetry(
            order["formation_id"],
            order["physical_idea_id"],
            order["branch"],
            order["direction"],
            order["formation_known_at"],
        )
        for bar in bars:
            if bar["start"] < order["decision_at"]:
                continue
            if state["status"] not in {"PENDING", "FILLED"}:
                break
            if bar["start"] != state["last_observed_end"]:
                state.update(status="UNKNOWN_DATA_GAP", reason="WAIT_DATA_GAP")
                break
            try:
                if state["status"] == "PENDING":
                    flags = lifecycle.flags(bar["start"], state)
                    if flags.get("known_at", bar["start"]) > bar["start"]:
                        raise V4Wait("UNKNOWN_FUTURE_LIFECYCLE")
                    if not pending_alive(
                        formation_known_at=order["formation_known_at"],
                        bar_open_at=bar["start"],
                        lifecycle_flags=flags,
                    ):
                        state.update(
                            status="UNFILLED_EXPIRED"
                            if bar["start"] >= state["expires_at"]
                            else "RETIRED_PENDING",
                            observed_at=bar["start"],
                        )
                        break
                previous = state["status"]
                state = _model_observer(state, bar, [grid])
                if hasattr(lifecycle, "advance"):
                    # Publish completed source facts even while the owner is FILLED.
                    # They never retroactively cancel a fill or an exited exposure.
                    lifecycle.advance(bar["end"])
                if "fill_price" in state and previous == "PENDING":
                    at = state["fill_observed_at"]
                    sink.emit(
                        {
                            "gate_name": "execution",
                            "event_type": "FILL",
                            "known_at": at,
                            "decision_cutoff": at,
                            "emission_decision_at": order["decision_at"],
                        }
                    )
                if state["status"] == "EXIT_OBSERVED":
                    state["status"] = "CLOSED"
                    state.update(_cash(state, funding))
                    state["holding_time_bounds"] = core.holding_duration_bounds(
                        state["fill_time_bounds"], state["event_time_bounds"]
                    )
                    at = state["observed_at"]
                    sink.emit(
                        {
                            "gate_name": "execution",
                            "event_type": "EXIT",
                            "known_at": at,
                            "decision_cutoff": at,
                            "emission_decision_at": order["decision_at"],
                        }
                    )
                elif state["status"] == "PENDING":
                    # Current CLOSE is first known after this bar's contact tests.
                    flags = lifecycle.flags(bar["end"], state)
                    if flags.get("known_at", bar["end"]) > bar["end"]:
                        raise V4Wait("UNKNOWN_FUTURE_LIFECYCLE")
                    if not pending_alive(
                        formation_known_at=order["formation_known_at"],
                        bar_open_at=bar["end"],
                        lifecycle_flags=flags,
                    ):
                        state.update(
                            status="UNFILLED_EXPIRED"
                            if bar["end"] >= state["expires_at"]
                            else "RETIRED_PENDING",
                            observed_at=bar["end"],
                        )
            except (core.ContractWait, V4Wait) as exc:
                state.update(
                    status="UNKNOWN_DATA_GAP"
                    if "DATA_GAP" in str(exc)
                    else "UNRESOLVED",
                    reason=getattr(exc, "reason", str(exc)),
                )
                break
        if state["status"] in {"PENDING", "FILLED"}:
            state = core.censor_eof(state, state["last_observed_end"])
        if hasattr(lifecycle, "finish"):
            lifecycle.finish()
            state["source_bridge_receipt"] = lifecycle.receipt()
        state["execution_telemetry"] = sink.snapshot()
        states.append(state)
    return _adverse(order, states)


class FixtureLifecycle:
    def __init__(self, events):
        self.events = deepcopy(events)

    def flags(self, at, scenario):
        flags = {"known_at": at}
        for t, event in self.events:
            if t <= at:
                flags.update(event)
        return flags


@_design_scope
def fixture(name):
    """Finite named registry; no caller-supplied historical prices or callbacks."""
    families = ("SFP", "OB", "BREAKER", "STB", "RANGE")
    registry = {
        f"{d.lower()}_{f.lower()}_target" for d in ("LONG", "SHORT") for f in families
    }
    registry.update(
        f"{d}_{f.lower()}_h4_{mode}"
        for d in ("long", "short")
        for f in families
        for mode in ("midbar", "no_fill", "context_late", "equal_cutoff")
    )
    registry.update(
        {
            "long_sfp_body",
            "short_sfp_body",
            "long_gap",
            "long_wick_ambiguity",
            "long_data_gap",
            "long_pending_eof",
            "long_pending_retire",
            "long_postfill_context",
            "long_funding",
            "short_funding",
            "long_deadline",
        }
    )
    if name not in registry:
        raise FinancialBlocked("UNREGISTERED_SYNTHETIC_FIXTURE")
    direction = "SHORT" if name.startswith("short") else "LONG"
    branch = next((f for f in families if f.lower() in name), "OB")
    long = direction == "LONG"
    order = {
        "version": "MACHINE_STRATEGY_v4.1",
        "venue": "OKX",
        "product": "BTC-USDT-SWAP",
        "symbol": "BTCUSDT",
        "contract_type": core.CONTRACT_TYPE,
        "case_id": "fixture:" + name,
        "formation_id": "fixture-origin",
        "physical_idea_id": "fixture-physical",
        "entry_poi_id": "fixture-poi",
        "confirmation_id": "fixture-conf",
        "confirmation_known_at": 0,
        "formation_known_at": 0,
        "emission_decision_at": 0,
        "decision_at": 0,
        "decision_close": "100",
        "parent_deadline_at": 57600,
        "raw_entry": "100",
        "protective_boundary": "90" if long else "110",
        "raw_fta_price": "130" if long else "70",
        "structural_entry_zone": {"low": "100", "high": "100"},
        "branch": branch,
        "direction": direction,
        "setup_tf": 60,
        "setup_tf_seconds": 3600,
        "stop_anchor": "99" if long else "101",
        "selected_fta_object": {
            "id": "fixture-fta",
            "tf": 60,
            "kind": "STRUCTURAL_LIQUIDITY",
            "price": "130" if long else "70",
        },
        "nearest_fta_id": "fixture-fta",
        "all_FTA_inventory": [],
        "liquidity_inventory": [],
        "selected_impulse": {"low": "80", "high": "140"},
        "trade_entry_allowed": False,
    }
    plan = all_scenario_plans(order, completed_close=order["decision_close"])[0]
    order["fixed_R_unit"] = abs(plan["entry"] - plan["stop"]) + Decimal("0.0008") * (
        plan["entry"] + plan["stop"]
    )

    def bar(start, o, h, l, c):
        return {
            "start": start,
            "end": start + 900,
            "open": str(o),
            "high": str(h),
            "low": str(l),
            "close": str(c),
        }

    bars = (
        [bar(0, 100, 103, 99, 102), bar(900, 102, 135, 101, 130)]
        if long
        else [bar(0, 100, 101, 97, 98), bar(900, 98, 99, 65, 70)]
    )
    events = []
    funding = []
    if name.endswith("body"):
        bars = [bar(i * 900, 100, 101, 99.5, 100) for i in range(3)]
        bars.append(
            bar(2700, 100, 101, 97, 98) if long else bar(2700, 100, 103, 99, 102)
        )
    elif name == "long_gap":
        bars = [bar(0, 80, 85, 79, 82)]
    elif name == "long_wick_ambiguity":
        bars = [bar(0, 105, 135, 99, 110)]
    elif name == "long_data_gap":
        bars[1]["start"], bars[1]["end"] = 1800, 2700
    elif name in {"long_pending_eof", "long_pending_retire"}:
        bars = [bar(0, 105, 107, 104, 106)]
        if name.endswith("retire"):
            events = [(900, {"poi_consumed": True})]
    elif name == "long_postfill_context":
        events = [(900, {"context_invalid": True, "poi_consumed": True})]
    elif name.endswith("funding"):
        funding = [
            (0, Decimal("0.001"), Decimal(100)),
            (900, Decimal("-0.001"), Decimal(100)),
        ]
    elif name == "long_deadline":
        order.update(decision_at=57600, emission_decision_at=57600)
        bars = [bar(57600, 100, 103, 99, 102)]
    if "_h4_" in name:
        from machine_strategy_v4_1_contracts import selected_poi_identity

        order.update(
            setup_tf=240,
            setup_tf_seconds=14400,
            formation_known_at=14400,
            confirmation_known_at=27900,
            decision_at=32400,
            emission_decision_at=32400,
            parent_deadline_at=72000,
            formation_id="fixture-origin:" + name,
            selected_eligibility_at=29700 if name.endswith("context_late") else 28800,
            native_context_known_at=29700 if name.endswith("context_late") else 0,
            original_structural_anchor=order["stop_anchor"]
            if branch == "SFP"
            else order["protective_boundary"],
        )
        order["formation_bar"] = {
            "start": 0,
            "end": 14400,
            "open": "100",
            "high": "110",
            "low": "90",
            "close": "100",
        }
        order["raw_entry"] = (
            ("100.013" if long else "100.017") if name.endswith("no_fill") else "100"
        )
        order["structural_entry_zone"] = {
            "low": order["raw_entry"],
            "high": order["raw_entry"],
        }
        order["entry_poi_id"] = selected_poi_identity(
            family=branch,
            existing_id="registered-refined:" + name,
            formation_id=order["formation_id"],
            source_parent_id="registered-source-parent",
            direction=direction,
            body_low=order["raw_entry"],
            body_high=order["raw_entry"],
            breaker_formation_known_at=14400,
            range_id="registered-range",
            boundary_price=order["raw_entry"],
        )
        plan = all_scenario_plans(order, completed_close=order["decision_close"])[0]
        order["fixed_R_unit"] = abs(plan["entry"] - plan["stop"]) + Decimal(
            "0.0008"
        ) * (plan["entry"] + plan["stop"])
        bars = []
        for at in range(28800, 46800, 900):
            if name.endswith("equal_cutoff") and at == 31500:
                bars.append(bar(at, 100, 101, 99, 100))
            elif at <= 32400:
                bars.append(
                    bar(at, 105, 106, 104, 105) if long else bar(at, 95, 96, 94, 95)
                )
            elif name.endswith("no_fill"):
                bars.append(bar(at, "100.015", "100.018", "100.012", "100.015"))
            elif at == 33300:
                bars.append(
                    bar(at, 105, 106, 99, 100) if long else bar(at, 95, 101, 94, 100)
                )
            elif at == 34200:
                bars.append(
                    bar(at, 100, 135, 99, 130) if long else bar(at, 100, 101, 65, 70)
                )
            else:
                bars.append(
                    bar(at, 130, 131, 129, 130) if long else bar(at, 70, 71, 69, 70)
                )
        funding = []
        events = []
        if name.endswith("equal_cutoff"):
            # Complete an H4 contact bar [08,12) then emit exactly at 12.
            # It must be rejected before any reservation/execution.
            order.update(decision_at=43200, emission_decision_at=43200)
    return order, bars, funding, events


def evaluate_fixture(name):
    order, bars, funding, _ = fixture(name)
    nonce = _fixture_issue(name)
    token = _ACTIVE.set(nonce)
    try:
        return _drive_case(order, bars, funding)
    finally:
        _ACTIVE.reset(token)
        _fixture_revoke(nonce)


def funding_inputs(product, native):
    """Exact inherited signed rows and settlement-close proxy, no signal use."""
    binding = json.loads(
        (
            ROOT
            / "docs/machine_strategy_v3_okx_compatibility_v1/COST_FUNDING_BINDING.json"
        ).read_text()
    )
    side = product.split("-")[0]
    path = ROOT / binding["source_inputs"][side + "_funding_csv"]
    if (
        sha256(path.read_bytes()).hexdigest()
        != binding["source_inputs"][side + "_funding_csv_sha256"]
    ):
        raise FinancialBlocked("FUNDING_SOURCE_CHANGED")
    closes = {b.end: b.close for b in native}
    result = []
    with path.open() as stream:
        for r in csv.DictReader(stream):
            at = int(r["funding_time_utc_ms"]) // 1000
            if r["instrument_name"] != product or at not in closes:
                raise FinancialBlocked("FUNDING_IDENTITY_OR_PROXY_MISSING")
            result.append((at, dec(r["funding_rate"]), closes[at]))
    return result


def evaluate_historical_catalog(*args, **kwargs):
    """This unqualified v4 checkpoint can never authorize historical finance."""
    raise FinancialBlocked("HISTORICAL_FINANCIAL_GATE_NOT_AUTHORIZED")
