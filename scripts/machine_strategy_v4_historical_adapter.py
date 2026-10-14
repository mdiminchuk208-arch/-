"""Causal pre-entry adapter for MACHINE_STRATEGY_v4 readiness.

No historical position/outcome simulation is present in this module.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from hashlib import sha256

import machine_strategy_v3_contracts as inherited_core
import machine_strategy_v3_historical_adapter as inherited
from machine_strategy_v2_core import serial
from machine_strategy_v4_readiness_core import (
    GateTelemetry,
    V4Reject,
    V4Wait,
    classify_approach,
    planned_payoff_gate,
    target_lifecycle_ok,
)
from machine_strategy_v4_readiness_core import (
    executable_plan as v4_executable_plan,
)
from okx_v3_compatibility_binding_v1 import PRODUCT_ALIAS, scenarios
from okx_v3_input_bridge_v1 import aggregate, load_native

VERSION = "MACHINE_STRATEGY_v4"
TRADE_ENTRY_ALLOWED = False


def identity(kind, *parts):
    return sha256(
        inherited.compact(serial([VERSION, kind, *parts])).encode()
    ).hexdigest()


def _rounded_entry(raw_entry: Decimal, tick: Decimal, direction: str) -> Decimal:
    mode = ROUND_FLOOR if direction == "LONG" else ROUND_CEILING
    return (raw_entry / tick).to_integral_value(rounding=mode) * tick


def _select_fta(targets, entry: Decimal, direction: str, decision_at: int):
    forward = []
    for candidate in targets:
        inherited_core.require_known_at(candidate, decision_at)
        if "zone_low" in candidate and "zone_high" in candidate:
            low = inherited_core.decimal(candidate["zone_low"])
            high = inherited_core.decimal(candidate["zone_high"])
            if low > high:
                raise V4Reject("REJECT_INVALID_FTA_ZONE")
            if low <= entry <= high:
                raise V4Reject("REJECT_ENTRY_IN_OPPOSING_POI")
        price = inherited_core.decimal(candidate["price"])
        distance = price - entry if direction == "LONG" else entry - price
        if distance > 0:
            forward.append((distance, str(candidate["id"]), candidate))
    if not forward:
        raise V4Wait("WAIT_NO_CAUSAL_FTA")
    nearest_distance, _, nearest = min(forward, key=lambda row: (row[0], row[1]))
    coincident = tuple(sorted(row[1] for row in forward if row[0] == nearest_distance))
    return nearest, coincident


def _structurally_retired(item, frame, at: int) -> bool:
    if item["branch"] == "RANGE":
        range_id = item.get("range", {}).get("id")
        if range_id in frame.retired_ranges:
            return True
    anchor = Decimal(str(item["extreme"]))
    direction = item["direction"]
    for bar in frame.bars[: frame.cursor]:
        if bar.end <= item["formation_at"] or bar.end > at:
            continue
        if direction == "LONG" and bar.close < anchor:
            return True
        if direction == "SHORT" and bar.close > anchor:
            return True
    return False


class V4HistoricalAdapter(inherited.HistoricalAdapter):
    """Five-family pre-entry adapter. It never imports an outcome runner."""

    def __init__(self, product, market, start, end):
        if product not in PRODUCT_ALIAS:
            raise V4Reject("REJECT_OKX_PRODUCT")
        self.product = product
        self.model_grids = scenarios(product)
        self.sinks = {}
        self._stage = "formation_discovery"
        self._context_id = None
        super().__init__(
            PRODUCT_ALIAS[product],
            market,
            [self.model_grids[0]],
            evaluation_start=start,
            evaluation_end=end,
        )

    def _emit(self, item, at, gate, status, reason=None, **diagnostics):
        key = (item["formation_id"], item["branch"])
        if key not in self.sinks:
            self.sinks[key] = GateTelemetry(
                item["formation_id"],
                identity(
                    "physical", self.symbol, item["formation_at"], item["direction"]
                ),
                item["branch"],
                item["direction"],
                item["formation_at"],
            )
        try:
            self.sinks[key].emit(
                {
                    "gate_name": gate,
                    "event_type": status,
                    "known_at": at,
                    "decision_cutoff": at,
                    "context_id": self._context_id,
                    "approach_state": None,
                    "reason_code": reason,
                    **diagnostics,
                }
            )
        except V4Reject as exc:
            raise RuntimeError("TELEMETRY_INTEGRITY_STOP") from exc

    def plan_pending(self, item, at):
        self._stage = "approach_state"
        self._context_id = None
        direction = item["direction"]
        if at >= item["formation_at"] + 57600:
            raise V4Reject("EXPIRED_PENDING")
        refinement = self.frames[15]
        confirms = [
            c
            for c in refinement.confirmations
            if c["known_at"] > item["reaction_at"]
            and c["direction"] == direction
            and refinement.bos_by_id[c["bos_id"]]["known_at"] >= item["reaction_at"]
            and c["known_at"] <= at
        ]
        conf = (
            max(confirms, key=lambda c: (c["known_at"], c["id"])) if confirms else None
        )
        opposite = [
            {"id": b["id"], "known_at": b["known_at"], "kind": "BOS"}
            for b in refinement.bos
            if b["direction"] != direction and item["reaction_at"] < b["known_at"] <= at
        ]
        opposite.extend(
            {"id": c["id"], "known_at": c["known_at"], "kind": "CONF"}
            for c in refinement.confirmations
            if c["direction"] != direction and item["reaction_at"] < c["known_at"] <= at
        )
        native_frame = self.frames[item["setup_tf"]]
        approach = classify_approach(
            direction=direction,
            reaction_at=item["reaction_at"],
            selected_conf=conf,
            opposing_events=opposite,
            decision_at=at,
            data_complete=True,
            structurally_retired=_structurally_retired(item, native_frame, at),
        )
        if approach["state"] == "APPROACH_INVALID":
            raise V4Reject("REJECT_STRUCTURAL_APPROACH_INVALID")

        self._emit(item, at, self._stage, "PASS", approach_state=approach["state"])
        self._stage = "refinement_and_poi"
        poi = item["zone"]
        if item["branch"] in ("SFP", "OB"):
            bos_at = refinement.bos_by_id[conf["bos_id"]]["known_at"]
            zones = [
                z
                for z in inherited.visible_zones(refinement, direction)
                if z["born_at"] >= bos_at
                and z["origin_bos_id"] == conf["bos_id"]
                and z["kind"] in ("OB", "FVG")
                and poi["low"] <= z["low"] <= z["high"] <= poi["high"]
            ]
            if not zones:
                raise V4Wait("WAIT_ORIGIN_BOUND_REFINEMENT_POI")
            poi = min(
                zones,
                key=lambda z: (
                    0 if z["kind"] == "OB" else 1,
                    -z["born_at"],
                    z["id"],
                ),
            )
        native = self.frames[item["setup_tf"]].zones.get(poi["id"])
        if (
            poi.get("consumed_at") is not None
            or (native and native.get("consumed_at") is not None)
            or poi["id"] in self.registry["pois"]
        ):
            raise V4Reject("REJECT_CONSUMED_OR_RESERVED_POI")

        self._emit(item, at, self._stage, "PASS", poi_id=poi["id"])
        self._stage = "htf_context"
        parent_pois = []
        for tf in (240, 1440):
            for zone in inherited.visible_zones(self.frames[tf], direction):
                parent_pois.append(
                    {
                        "id": zone["id"],
                        "tf": "H4" if tf == 240 else "D1",
                        "direction": direction,
                        "low": zone["low"],
                        "high": zone["high"],
                        "confirmed": True,
                        "consumed_at": None,
                        "known_at": max(
                            zone["born_at"],
                            self.frames[tf].confirmed_bos[zone["origin_bos_id"]],
                        ),
                    }
                )
        states = {
            name: self.frames[tf].state(at)
            for name, tf in (("H1", 60), ("H4", 240), ("D1", 1440))
        }
        context = inherited_core.admit_context(
            states=states,
            direction=direction,
            formation_bar=inherited.bar_record(item["formation_bar"]),
            m15_confirmation={
                "id": conf["id"],
                "direction": conf["direction"],
                "known_at": conf["known_at"],
            },
            parent_pois=parent_pois,
            decision_at=at,
            h4_range=self.frames[240].range_record(),
        )
        self._context_id = context.get("origin_id", context.get("context_id"))
        self._emit(item, at, self._stage, "PASS")
        self._stage = "entry_geometry"
        raw = inherited_core.raw_family_prices(
            family=item["branch"],
            direction=direction,
            zone_low=poi["low"],
            zone_high=poi["high"],
            stop_anchor=item["extreme"],
            atr14=item["atr"] if item["branch"] == "SFP" else None,
        )
        raw["known_at"] = at
        h1 = self.frames[60].context
        if h1 is None:
            raise V4Wait("WAIT_COMPLETE_H1_CONTEXT")
        targets, _ = inherited.inventories(
            self.frames,
            direction,
            raw["raw_entry"],
            raw["raw_stop_boundary"],
            h1,
        )
        if item["branch"] == "RANGE":
            if item["range"]["id"] in native_frame.retired_ranges:
                raise V4Reject("REJECT_RETIRED_SOURCE_RANGE")
            targets.append(
                {
                    "id": item["range"]["id"],
                    "tf": item["setup_tf"],
                    "kind": "RANGE_FAR_BOUNDARY_CAP",
                    "known_at": item["range"]["known_at"],
                    "price": item["range"]["high"]
                    if direction == "LONG"
                    else item["range"]["low"],
                }
            )

        reference_grid = self.model_grids[0]
        tick = Decimal(reference_grid["tick"])
        reference_entry = _rounded_entry(Decimal(raw["raw_entry"]), tick, direction)
        self._stage = "fta_lifecycle"
        nearest, coincident = _select_fta(targets, reference_entry, direction, at)
        raw_fta = Decimal(str(nearest["price"]))
        plan = v4_executable_plan(
            direction=direction,
            raw_entry=raw["raw_entry"],
            protective_boundary=raw["raw_stop_boundary"],
            raw_fta=raw_fta,
            structural_low=poi["low"],
            structural_high=poi["high"],
            tick=tick,
        )
        latest_m15 = self.frames[15].bars[self.frames[15].cursor - 1]
        target_lifecycle_ok(
            direction=direction,
            completed_close=latest_m15.close,
            raw_fta=raw_fta,
            inward_target=plan["target"],
        )
        self._emit(
            item, at, self._stage, "PASS", fta_id=nearest["id"], fta_price=str(raw_fta)
        )
        self._stage = "payoff_gate"
        payoff = planned_payoff_gate(
            direction=direction,
            entry=plan["entry"],
            stop=plan["stop"],
            target=plan["target"],
        )
        self._emit(
            item,
            at,
            self._stage,
            "PASS",
            net_target_R_doubled_cost=str(payoff["ratio"]),
        )
        self._stage = "adverse_liquidity"
        _, pools = inherited.inventories(
            self.frames, direction, plan["entry"], plan["stop"], h1
        )
        if any(pool["adverse"] for pool in pools):
            raise V4Reject("REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP")

        self._emit(item, at, self._stage, "PASS")
        physical = identity("physical", self.symbol, item["formation_at"], direction)
        setup = identity("setup", physical, item["formation_id"], conf["id"], poi["id"])
        record = {
            **plan,
            "version": VERSION,
            "venue": "OKX",
            "product": self.product,
            "symbol": self.symbol,
            "branch": item["branch"],
            "setup_tf": item["setup_tf"],
            "direction": direction,
            "decision_at": at,
            "known_at": at,
            "formation_known_at": item["formation_at"],
            "emission_decision_at": at,
            "formation_bar": inherited.bar_record(item["formation_bar"]),
            "original_structural_anchor": item["extreme"],
            "stop_anchor": item["extreme"],
            "setup_tf_seconds": item["setup_tf"] * 60,
            "contract_type": inherited_core.CONTRACT_TYPE,
            "expires_at": item["formation_at"] + 57600,
            "fixed_R_unit": payoff["planned_stop_unit"],
            "source_range_id": item.get("range", {}).get("id"),
            "selected_fta_object": nearest,
            "entry_poi_tf": 15 if item["branch"] in ("SFP", "OB") else item["setup_tf"],
            "entry_poi_known_at": max(
                poi["born_at"], refinement.confirmed_bos[poi["origin_bos_id"]]
            )
            if item["branch"] in ("SFP", "OB")
            else None,
            "first_test_mapping_status": "NATIVE_ORIGIN_CONF"
            if item["branch"] in ("SFP", "OB")
            else "UNRESOLVED_FROZEN_DESIGN",
            "implementation_readiness": "STOP_SELECTED_POI_FIRST_TEST",
            "parent_deadline_at": item["formation_at"] + 57600,
            "status": "PENDING",
            "physical_idea_id": physical,
            "entry_poi_id": poi["id"],
            "setup_id": setup,
            "case_id": identity("pre_entry_order", setup, at),
            "formation_id": item["formation_id"],
            "confirmation_id": conf["id"],
            "confirmation_known_at": conf["known_at"],
            "approach": approach,
            "context": context,
            "states": states,
            "selected_impulse": h1,
            "structural_entry_zone": {"low": poi["low"], "high": poi["high"]},
            "raw_entry": raw["raw_entry"],
            "protective_boundary": raw["raw_stop_boundary"],
            "raw_fta_price": raw_fta,
            "nearest_fta_id": nearest["id"],
            "coincident_fta_ids": coincident,
            "all_FTA_inventory": targets,
            "FTA_inventory_digest": identity("FTA_inventory", targets),
            "liquidity_inventory": pools,
            "liquidity_inventory_digest": identity("liquidity", pools),
            "planned_payoff": payoff,
            "reference_scenario_id": reference_grid["id"],
            "historical_position_evaluations": 0,
            "trade_entry_allowed": False,
        }
        return serial(record)

    def run(self, cutoff=None):
        """Source-only chronological loop. No order contacts or position events."""
        cutoff = (
            self.end - 1
            if cutoff is None
            else min(inherited_core.exact_timestamp(cutoff), self.end - 1)
        )
        orders, diagnostics, raw_origins = [], [], {}
        for bar in self.market[15]:
            at = bar.end
            if at > cutoff:
                break
            for tf in (1440, 240, 60, 15):
                self.frames[tf].advance(at)
            if at % 3600:
                continue  # Frozen H1-only new-signal clock, M15 states still advanced.
            before = set(self.pending)
            self.discover(at)
            for key in set(self.pending) - before:
                item = self.pending[key]
                raw_origins[key] = (
                    item["formation_id"],
                    item["branch"],
                    item["formation_at"],
                    item["direction"],
                )
                self._context_id = None
                self._emit(item, at, "formation_discovery", "PASS")
            proposals = []
            for key, item in list(self.pending.items()):
                self._stage = "reaction"
                self._context_id = None
                try:
                    if at >= item["formation_at"] + 57600:
                        raise V4Reject("EXPIRED_PENDING")
                    frame = self.frames[item["setup_tf"]]
                    native = frame.bars[frame.cursor - 1]
                    if _structurally_retired(item, frame, at):
                        raise V4Reject("REJECT_STRUCTURAL_APPROACH_INVALID")
                    if item["next_open_required"]:
                        if native.start < item["formation_at"]:
                            raise V4Wait("WAIT_SFP_NEXT_NATIVE_OPEN")
                        item["next_open_required"] = False
                        item["next_open_evidence"] = {
                            "actual_at": native.start,
                            "known_at": native.end,
                            "open": native.open,
                        }
                        if not (
                            native.open > item["level"]
                            if item["direction"] == "LONG"
                            else native.open < item["level"]
                        ):
                            raise V4Reject("REJECT_SFP_NEXT_OPEN")
                    if item["reaction_at"] is None:
                        if native.start < item[
                            "formation_at"
                        ] or not inherited.intersects(
                            native, item["zone"]["low"], item["zone"]["high"]
                        ):
                            raise V4Wait("WAIT_NATIVE_REACTION")
                        if (
                            item["branch"] == "RANGE"
                            and not item["range"]["low"]
                            < native.close
                            < item["range"]["high"]
                        ):
                            raise V4Wait("WAIT_RANGE_RECLAIM")
                        item["reaction_at"] = native.end
                    self._emit(item, at, "reaction", "PASS")
                    proposal = self.plan_pending(item, at)
                    proposals.append((key, item, proposal))
                    continue
                except (V4Wait, inherited_core.ContractWait) as exc:
                    reason = getattr(exc, "reason", str(exc))
                    self.counts[reason] += 1
                    item["last_wait"] = reason
                    self._emit(item, at, self._stage, "WAIT", reason)
                    continue
                except (V4Reject, inherited_core.ContractReject) as exc:
                    reason = getattr(exc, "reason", str(exc))
                    self.counts[reason] += 1
                    diagnostics.append(
                        {
                            "formation_id": item["formation_id"],
                            "branch": item["branch"],
                            "decision_at": at,
                            "reason": reason,
                        }
                    )
                    self._emit(item, at, self._stage, "REJECT", reason)
                    del self.pending[key]
            groups = {}
            for key, item, proposal in proposals:
                groups.setdefault(proposal["physical_idea_id"], []).append(
                    (key, item, proposal)
                )
            for physical, siblings in sorted(groups.items()):
                ordered = sorted(
                    siblings,
                    key=lambda row: (
                        inherited.PRIORITY[row[2]["branch"]],
                        -row[2]["setup_tf"],
                        row[2]["setup_id"],
                    ),
                )
                key, item, chosen = ordered[0]
                try:
                    self.registry = inherited_core.reserve_idea(
                        self.registry, physical, chosen["entry_poi_id"]
                    )
                    chosen["rejected_sibling_branches"] = [
                        {
                            "branch": p["branch"],
                            "formation_id": p["formation_id"],
                            "setup_id": p["setup_id"],
                        }
                        for _, _, p in ordered[1:]
                    ]
                    orders.append(chosen)
                    self._emit(
                        item,
                        at,
                        "reservation_and_order",
                        "ORDER_EMIT",
                        reservation_id=chosen["case_id"],
                    )
                    for _, other, _ in ordered[1:]:
                        self._emit(
                            other,
                            at,
                            "reservation_and_order",
                            "REJECT",
                            "PRIORITY_SIBLING",
                        )
                except inherited_core.ContractReject as exc:
                    for _, other, _ in ordered:
                        self._emit(
                            other, at, "reservation_and_order", "REJECT", exc.reason
                        )
                for key, _, _ in ordered:
                    del self.pending[key]
        for item in self.pending.values():
            self._emit(item, cutoff, "EOF", "EOF_CENSOR", "PENDING_SOURCE_EOF")
        snapshots = [sink.snapshot() for _, sink in sorted(self.sinks.items())]
        return orders, {
            "venue": "OKX",
            "product": self.product,
            "strategy_version": VERSION,
            "raw_origins": serial(sorted(raw_origins.values())),
            "diagnostics": diagnostics,
            "pending": serial(
                [
                    {k: v for k, v in p.items() if k != "formation_bar"}
                    for p in self.pending.values()
                ]
            ),
            "telemetry": snapshots,
            "counts": dict(self.counts),
            "cutoff": cutoff,
            "frame_prefix_digests": {
                str(tf): identity(
                    "frame",
                    tf,
                    f.context,
                    f.confirmations,
                    f.zones,
                    f.pools,
                    f.range_record(),
                )
                for tf, f in self.frames.items()
            },
            "historical_position_evaluations": 0,
            "financial_outcomes_generated": False,
            "trade_entry_allowed": False,
        }

    def catalog(self, cutoff=None):
        return self.run(cutoff)


def market_inputs(product):
    from okx_v3_compatibility_binding_v1 import read_policy
    from verify_okx_stage_a_v1 import resume

    pre, _ = read_policy()
    resume(pre["parent_stage_A"]["manifest_sha256"])
    native = load_native(product)
    market = {15: native}
    for seconds in (3600, 14400, 86400):
        market[seconds // 60], omitted = aggregate(native, seconds)
        if omitted:
            raise V4Wait("WAIT_COMPLETE_OKX_PREFIX")
    return market
