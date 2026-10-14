"""Nine-scenario non-financial execution binding for MACHINE_STRATEGY_v4."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_FLOOR, Decimal

from machine_strategy_v4_readiness_core import (
    V4Reject,
    V4Wait,
    dec,
    executable_plan,
    planned_payoff_gate,
    target_lifecycle_ok,
)
from okx_v3_compatibility_binding_v1 import scenarios

VERSION = "MACHINE_STRATEGY_v4"
TRADE_ENTRY_ALLOWED = False


def scenario_plan(order: Mapping, grid: Mapping, *, completed_close) -> dict:
    if order.get("version") != VERSION:
        raise V4Reject("REJECT_V4_ORDER_VERSION")
    if order.get("product") != grid.get("product"):
        raise V4Reject("REJECT_SCENARIO_PRODUCT")
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
        if (
            "zone_low" in target
            and "zone_high" in target
            and dec(target["zone_low"]) <= plan["entry"] <= dec(target["zone_high"])
        ):
            raise V4Reject("REJECT_ENTRY_IN_OPPOSING_POI")
    impulse = order.get("selected_impulse")
    if impulse:
        low, high = dec(impulse["low"]), dec(impulse["high"])
        for pool in order.get("liquidity_inventory", []):
            price = dec(pool["price"])
            forward = price > plan["entry"] if long else price < plan["entry"]
            profit_side = pool["side"] == ("HIGH" if long else "LOW")
            beyond = price < plan["stop"] if long else price > plan["stop"]
            if not forward and not profit_side and low < price < high and beyond:
                raise V4Reject("REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP")
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
    contract_base = dec(grid["contract_base"])
    lot = dec(grid["lot"])
    minimum = dec(grid["minimum"])
    if min(contract_base, lot, minimum) <= 0:
        raise V4Reject("REJECT_SCENARIO_QUANTITY_INPUT")
    contracts = ((Decimal(1) / contract_base) / lot).to_integral_value(
        rounding=ROUND_FLOOR
    ) * lot
    if contracts <= 0 or contracts < minimum:
        raise V4Reject("REJECT_SCENARIO_QUANTITY")
    return {
        "case_id": order["case_id"],
        "scenario_id": grid["id"],
        "status": "ELIGIBLE_PENDING",
        **plan,
        "planned_payoff": payoff,
        "nearest_fta_id": order.get("nearest_fta_id"),
        "fixed_R_unit": order.get("fixed_R_unit"),
        "quantity_contracts": contracts,
        "quantity_base": contracts * contract_base,
        "trade_entry_allowed": False,
    }


def all_scenario_plans(order: Mapping, *, completed_close) -> list[dict]:
    result = []
    for grid in scenarios(order["product"]):
        try:
            result.append(scenario_plan(order, grid, completed_close=completed_close))
        except V4Wait as exc:
            result.append(
                {
                    "case_id": order["case_id"],
                    "scenario_id": grid["id"],
                    "status": "UNRESOLVED",
                    "reason": str(exc),
                    "trade_entry_allowed": False,
                }
            )
        except V4Reject as exc:
            result.append(
                {
                    "case_id": order["case_id"],
                    "scenario_id": grid["id"],
                    "status": "INELIGIBLE",
                    "reason": str(exc),
                    "trade_entry_allowed": False,
                }
            )
    if len(result) != 9:
        raise V4Reject("REJECT_SCENARIO_LADDER")
    if result[0]["scenario_id"] != "P01_Q001":
        raise V4Reject("REJECT_REFERENCE_SCENARIO")
    return result
