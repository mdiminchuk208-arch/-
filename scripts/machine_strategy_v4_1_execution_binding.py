"""Nine-scenario non-financial execution binding for MACHINE_STRATEGY_v4.1.

The binding applies frozen v4 H04/H05 execution rules under the independently
frozen v4.1 Decimal50 design scope. It only builds eligibility/pending plans; it
cannot execute historical positions or compute financial outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext

from machine_strategy_v4_1_contracts import (
    DESIGN_PRECISION,
    V41Reject,
    canonical_decimal,
    design_decimal,
)
from machine_strategy_v4_readiness_core import (
    V4Reject,
    V4Wait,
    executable_plan,
    planned_payoff_gate,
    target_lifecycle_ok,
)
from okx_v3_compatibility_binding_v1 import scenarios

VERSION = "MACHINE_STRATEGY_v4.1"
TRADE_ENTRY_ALLOWED = False


def _serialized_plan(plan: Mapping) -> dict:
    return {
        "entry": canonical_decimal(plan["entry"]),
        "stop": canonical_decimal(plan["stop"]),
        "target": canonical_decimal(plan["target"]),
        "exec_low": canonical_decimal(plan["exec_low"]),
        "exec_high": canonical_decimal(plan["exec_high"]),
        "tick": canonical_decimal(plan["tick"]),
    }


def scenario_plan(order: Mapping, grid: Mapping, *, completed_close: object) -> dict:
    """Build one preregistered scenario without fill/exit/P&L evaluation."""
    if order.get("version") != VERSION:
        raise V41Reject("REJECT_V4_1_ORDER_VERSION")
    if order.get("product") != grid.get("product"):
        raise V41Reject("REJECT_SCENARIO_PRODUCT")

    with localcontext() as ctx:
        ctx.prec = DESIGN_PRECISION
        ctx.rounding = ROUND_HALF_EVEN

        plan = executable_plan(
            direction=order["direction"],
            raw_entry=order["raw_entry"],
            protective_boundary=order["protective_boundary"],
            raw_fta=order["raw_fta_price"],
            structural_low=order["structural_entry_zone"]["low"],
            structural_high=order["structural_entry_zone"]["high"],
            tick=grid["tick"],
        )
        long = order["direction"] == "LONG"

        for target in order.get("all_FTA_inventory", []):
            if "zone_low" in target and "zone_high" in target:
                low = design_decimal(target["zone_low"])
                high = design_decimal(target["zone_high"])
                if low <= plan["entry"] <= high:
                    raise V41Reject("REJECT_ENTRY_IN_OPPOSING_POI")

        impulse = order.get("selected_impulse")
        if impulse:
            low = design_decimal(impulse["low"])
            high = design_decimal(impulse["high"])
            for pool in order.get("liquidity_inventory", []):
                price = design_decimal(pool["price"])
                forward = price > plan["entry"] if long else price < plan["entry"]
                profit_side = pool["side"] == ("HIGH" if long else "LOW")
                beyond = price < plan["stop"] if long else price > plan["stop"]
                if not forward and not profit_side and low < price < high and beyond:
                    raise V41Reject("REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP")

        target_lifecycle_ok(
            direction=order["direction"],
            completed_close=completed_close,
            raw_fta=order["raw_fta_price"],
            inward_target=plan["target"],
        )
        payoff = planned_payoff_gate(
            direction=order["direction"],
            entry=plan["entry"],
            stop=plan["stop"],
            target=plan["target"],
        )

        contract_base = design_decimal(grid["contract_base"])
        lot = design_decimal(grid["lot"])
        minimum = design_decimal(grid["minimum"])
        if min(contract_base, lot, minimum) <= 0:
            raise V41Reject("REJECT_SCENARIO_QUANTITY_INPUT")
        contracts = ((Decimal(1) / contract_base) / lot).to_integral_value(
            rounding=ROUND_FLOOR
        ) * lot
        if contracts <= 0 or contracts < minimum:
            raise V41Reject("REJECT_SCENARIO_QUANTITY")
        quantity_base = contracts * contract_base

        serialized = _serialized_plan(plan)
        return {
            "version": VERSION,
            "case_id": order["case_id"],
            "product": order["product"],
            "scenario_id": grid["id"],
            "status": "ELIGIBLE_PENDING",
            **serialized,
            "planned_payoff": {
                "planned_stop_unit": canonical_decimal(payoff["planned_stop_unit"]),
                "net_target_doubled": canonical_decimal(payoff["net_target_doubled"]),
                "ratio": canonical_decimal(payoff["ratio"]),
            },
            "nearest_fta_id": order.get("nearest_fta_id"),
            "fixed_R_unit": order.get("fixed_R_unit"),
            "quantity_contracts": canonical_decimal(contracts),
            "quantity_base": canonical_decimal(quantity_base),
            "decimal_scope": "DESIGN_PRECISION_50_HALF_EVEN",
            "ledger_recompute_geometry_allowed": False,
            "trade_entry_allowed": False,
        }


def all_scenario_plans(order: Mapping, *, completed_close: object) -> list[dict]:
    """Retain every preregistered scenario, including adverse/unresolved states."""
    result: list[dict] = []
    for grid in scenarios(order["product"]):
        try:
            result.append(scenario_plan(order, grid, completed_close=completed_close))
        except V4Wait as exc:
            result.append(
                {
                    "version": VERSION,
                    "case_id": order["case_id"],
                    "scenario_id": grid["id"],
                    "status": "UNRESOLVED",
                    "reason": exc.reason,
                    "trade_entry_allowed": False,
                }
            )
        except (V4Reject, V41Reject) as exc:
            reason = getattr(exc, "reason", str(exc))
            result.append(
                {
                    "version": VERSION,
                    "case_id": order["case_id"],
                    "scenario_id": grid["id"],
                    "status": "INELIGIBLE",
                    "reason": reason,
                    "trade_entry_allowed": False,
                }
            )
    if len(result) != 9:
        raise V41Reject("REJECT_SCENARIO_LADDER")
    if result[0]["scenario_id"] != "P01_Q001":
        raise V41Reject("REJECT_REFERENCE_SCENARIO")
    if len({row["scenario_id"] for row in result}) != 9:
        raise V41Reject("REJECT_DUPLICATE_SCENARIO")
    return result
