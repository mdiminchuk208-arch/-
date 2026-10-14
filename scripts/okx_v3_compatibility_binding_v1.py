"""Explicit synthetic execution binding; protected v3 signal bytecode is reused."""

from __future__ import annotations

import ast
import inspect
import json
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from hashlib import sha256
from pathlib import Path
from types import FunctionType

import machine_strategy_v3_contracts as core
import machine_strategy_v3_historical_adapter as inherited
from machine_strategy_v2_core import serial
from okx_qualification_data_v1 import ROOT
from okx_v3_input_bridge_v1 import aggregate, load_native

VERSION = "MACHINE_STRATEGY_v3_OKX_COMPATIBILITY_v1"
DEST = ROOT / "docs/machine_strategy_v3_okx_compatibility_v1"
POLICY_COMMIT = "23f275cae85d1cab4d91cc07351ffdef2560d75d"
POLICY_RECEIPT_SHA = "dcd8b0bc279afe8979dffd7532fcc5c358cfd9e867018bd59ac546cd6062e9d7"
PRODUCT_ALIAS = {"BTC-USDT-SWAP": "BTCUSDT", "ETH-USDT-SWAP": "ETHUSDT"}
READY_DECISION = "MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read_policy():
    if digest(DEST / "POLICY_FREEZE_RECEIPT.json") != POLICY_RECEIPT_SHA:
        raise core.ContractReject("REJECT_POLICY_FREEZE_RECEIPT_CHANGED")
    receipt = json.loads((DEST / "POLICY_FREEZE_RECEIPT.json").read_text())
    for name, expected in receipt["files_sha256"].items():
        if digest(ROOT / name) != expected:
            raise core.ContractReject("REJECT_PREREGISTERED_POLICY_CHANGED")
    pre = json.loads((DEST / "COMPATIBILITY_PREREGISTRATION.json").read_text())
    for name, expected in pre["protected_strategy"].items():
        if name.startswith("scripts/") and digest(ROOT / name) != expected:
            raise core.ContractReject("REJECT_PROTECTED_SIGNAL_BYTES_CHANGED")
    return pre, json.loads((DEST / "QUANTIZATION_STRESS_POLICY.json").read_text())


def scenarios(product):
    _, policy = read_policy()
    if product not in PRODUCT_ALIAS:
        raise core.ContractReject("REJECT_OKX_PRODUCT")
    p = policy["products"][product]
    result = []
    for price in policy["scenario_generation"]["price_tick_multipliers"]:
        for quantity in policy["scenario_generation"][
            "contract_lot_and_minimum_multipliers"
        ]:
            result.append(
                {
                    "id": f"P{int(price):02d}_Q{int(quantity):03d}",
                    "classification": "SYNTHETIC_COMPATIBILITY_NOT_HISTORICAL_EPOCH",
                    "product": product,
                    "symbol": PRODUCT_ALIAS[product],
                    "tick": str(Decimal(p["reference_tickSz"]) * Decimal(price)),
                    "lot": str(Decimal(p["reference_lotSz"]) * Decimal(quantity)),
                    "minimum": str(Decimal(p["reference_minSz"]) * Decimal(quantity)),
                    "contract_base": str(Decimal(p["ctVal"]) * Decimal(p["ctMult"])),
                }
            )
    if [r["id"] for r in result] != policy["scenario_generation"][
        "scenario_ids_in_order"
    ]:
        raise core.ContractReject("REJECT_SCENARIO_LADDER")
    return result


def modeled_grid(grids, symbol, contract_type, at, decision_at):
    core.exact_timestamp(at)
    core.exact_timestamp(decision_at)
    if len(grids) != 1 or contract_type != core.CONTRACT_TYPE:
        raise core.ContractReject("REJECT_SYNTHETIC_GRID_CONTRACT")
    grid = grids[0]
    if (
        grid.get("classification") != "SYNTHETIC_COMPATIBILITY_NOT_HISTORICAL_EPOCH"
        or grid.get("symbol") != symbol
        or "verified" in grid
    ):
        raise core.ContractReject("REJECT_FAKE_SOURCE_EPOCH")
    if core.decimal(grid["tick"]) <= 0:
        raise core.ContractReject("REJECT_SYNTHETIC_TICK")
    return grid


class ModelShim(ast.NodeTransformer):
    """Only the preregistered metadata/observed-grid substitution is permitted."""

    def __init__(self):
        self.resolver_names = 0
        self.order_id_labels = 0
        self.observed_grid_checks = 0

    def visit_Name(self, node):
        if node.id == "proven_tick_epoch":
            self.resolver_names += 1
            node.id = "modeled_grid"
        return node

    def visit_Constant(self, node):
        if node.value == "tick_epoch_id":
            self.order_id_labels += 1
            node.value = "model_grid_id"
        if node.value == "GRID_REPRESENTABILITY_ONLY":
            node.value = "SYNTHETIC_MODEL_PRICE_GRID_NOT_HISTORY"
        return node

    def visit_Tuple(self, node):
        if [getattr(x, "id", None) for x in node.elts] == [
            "o",
            "high",
            "low",
            "close",
            "e",
            "s",
            "t",
        ]:
            self.observed_grid_checks += 1
            node.elts = node.elts[-3:]
        return self.generic_visit(node)


def clone_model_contract(function, expected_changes):
    tree = ast.parse(inspect.getsource(function))
    shim = ModelShim()
    tree = ast.fix_missing_locations(shim.visit(tree))
    changes = (shim.resolver_names, shim.order_id_labels, shim.observed_grid_checks)
    if changes != expected_changes:
        raise core.ContractReject("REJECT_UNEXPECTED_CORE_SHIM_DIFF")
    scope = {**vars(core), "modeled_grid": modeled_grid}
    # No input data is executable: only a protected function AST and counted edits.
    exec(compile(tree, __file__ + ":model_shim", "exec"), scope)  # noqa: S102
    return scope[function.__name__]


read_policy()
_model_plan = clone_model_contract(core.executable_plan, (1, 1, 0))
_model_observer = clone_model_contract(core.observe_m15_bar, (2, 1, 1))


def capture_reference_plan(**kwargs):
    plan = _model_plan(**kwargs)
    plan["compatibility_plan_inputs"] = serial(
        {k: v for k, v in kwargs.items() if k != "epochs"}
    )
    return plan


_catalog_globals = {**vars(inherited), "executable_plan": capture_reference_plan}
_unchanged_plan_pending = FunctionType(
    inherited.HistoricalAdapter.plan_pending.__code__,
    _catalog_globals,
    inherited.HistoricalAdapter.plan_pending.__name__,
    inherited.HistoricalAdapter.plan_pending.__defaults__,
    inherited.HistoricalAdapter.plan_pending.__closure__,
)


def audited_reservation(registry, physical, poi):
    """Observe the protected caller's proposals, then preserve its exact result."""
    caller = inspect.currentframe().f_back
    try:
        if caller.f_code is not inherited.HistoricalAdapter.run.__code__:
            raise core.ContractReject("REJECT_UNEXPECTED_RESERVATION_CALLER")
        adapter = caller.f_locals["self"]
        proposals = caller.f_locals["ordered"]
        at = caller.f_locals["at"]

        def records(conflict=None):
            return [
                {
                    **p,
                    "compatibility_case_id": sha256(
                        f"{VERSION}|OKX|{adapter.product}|{p['case_id']}".encode()
                    ).hexdigest(),
                    "disposition": "RESERVATION_CONFLICT"
                    if conflict
                    else "EMITTED"
                    if index == 0
                    else "SIBLING_NOT_SELECTED",
                    "audit_reason": conflict
                    or (
                        "FROZEN_PRIORITY_SELECTED"
                        if index == 0
                        else "FROZEN_PRIORITY_SIBLING_REJECTED"
                    ),
                }
                for index, (_, p) in enumerate(proposals)
            ]

        try:
            result = inherited.reserve_idea(registry, physical, poi)
        except core.ContractReject as exc:
            adapter.reservation_audit.append(
                serial(
                    {
                        "decision_at": at,
                        "reason": exc.reason,
                        "proposals": records(exc.reason),
                    }
                )
            )
            raise
        adapter.reservation_audit.append(
            serial(
                {
                    "decision_at": at,
                    "reason": "RESERVED_WITH_FROZEN_PRIORITY",
                    "proposals": records(),
                }
            )
        )
        return result
    finally:
        del caller


_unchanged_run = FunctionType(
    inherited.HistoricalAdapter.run.__code__,
    {**vars(inherited), "reserve_idea": audited_reservation},
    inherited.HistoricalAdapter.run.__name__,
    inherited.HistoricalAdapter.run.__defaults__,
    inherited.HistoricalAdapter.run.__closure__,
)


class CompatibilityAdapter(inherited.HistoricalAdapter):
    plan_pending = _unchanged_plan_pending
    run = _unchanged_run

    def __init__(self, product, market, start, end):
        self.product = product
        self.raw_formations = []
        self.raw_native_formations = []
        self.reservation_audit = []
        self._logged_formations = set()
        self.model_grids = scenarios(product)
        super().__init__(
            PRODUCT_ALIAS[product],
            market,
            [self.model_grids[0]],
            evaluation_start=start,
            evaluation_end=end,
        )

    def discover(self, at):
        # Only audit output is added; the protected discovery runs unchanged first.
        super().discover(at)
        for tf in (60, 240):
            self.raw_native_formations.extend(
                serial(obj)
                for obj in self.frames[tf].new_events
                if obj["kind"] in ("SFP", "OB", "STB")
            )
        for key, pending in self.pending.items():
            if key not in self._logged_formations:
                self._logged_formations.add(key)
                self.raw_formations.append(
                    serial(
                        {
                            **pending,
                            "formation_bar": inherited.bar_record(
                                pending["formation_bar"]
                            ),
                            "discovered_at": at,
                        }
                    )
                )

    def catalog(self, cutoff=None):
        # The new UTC end is an H1 boundary; it is exclusive for new decisions.
        cutoff = self.end - 1 if cutoff is None else min(cutoff, self.end - 1)
        with localcontext() as context:
            context.prec = 28
            context.rounding = ROUND_HALF_EVEN
            orders, audit = self.run(cutoff)
        audit["raw_formations"] = self.raw_formations
        audit["raw_native_formations"] = self.raw_native_formations
        audit["reservation_audit"] = self.reservation_audit
        audit.update(venue="OKX", product=self.product, compatibility_version=VERSION)
        for order in orders:
            original_id = order["case_id"]
            order.update(
                base_signal_case_id=original_id,
                venue="OKX",
                product=self.product,
                compatibility_version=VERSION,
                fixed_R_unit=order["cash_stop_unit"],
                case_id=sha256(
                    f"{VERSION}|OKX|{self.product}|{original_id}".encode()
                ).hexdigest(),
            )
        return orders, audit


def market_inputs(product):
    from verify_okx_stage_a_v1 import resume

    pre, _ = read_policy()
    resume(pre["parent_stage_A"]["manifest_sha256"])
    native = load_native(product)
    market = {15: native}
    for seconds in (3600, 14400, 86400):
        market[seconds // 60], omitted = aggregate(native, seconds)
        if omitted:
            raise core.ContractWait("WAIT_COMPLETE_OKX_PREFIX")
    return market


def scenario_plan(order, grid):
    inputs = dict(order["compatibility_plan_inputs"])
    result = _model_plan(**inputs, epochs=[grid])
    if result["nearest_fta_id"] != order["nearest_fta_id"]:
        raise core.ContractReject("REJECT_STRESS_WOULD_CHANGE_FROZEN_FTA")
    impulse = order["selected_impulse"]
    low, high = Decimal(impulse["low"]), Decimal(impulse["high"])
    entry, stop = result["entry"], result["stop"]
    long = order["direction"] == "LONG"
    for pool in order["liquidity_inventory"]:
        p = Decimal(pool["price"])
        forward = p > entry if long else p < entry
        profit_side = pool["side"] == ("HIGH" if long else "LOW")
        beyond_stop = p < stop if long else p > stop
        if not forward and not profit_side and low < p < high and beyond_stop:
            raise core.ContractReject("REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP")
    v, lot, minimum = (Decimal(grid[k]) for k in ("contract_base", "lot", "minimum"))
    contracts = ((Decimal(1) / v) / lot).to_integral_value(rounding=ROUND_FLOOR) * lot
    if contracts <= 0 or contracts < minimum:
        raise core.ContractReject("REJECT_SCENARIO_QUANTITY")
    return {
        **order,
        **result,
        "scenario_id": grid["id"],
        "quantity_contracts": str(contracts),
        "quantity_base": str(contracts * v),
        "status": "PENDING",
    }
