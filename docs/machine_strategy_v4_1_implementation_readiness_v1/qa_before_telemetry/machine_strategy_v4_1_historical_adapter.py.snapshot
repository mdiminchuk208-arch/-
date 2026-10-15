"""Causal pre-entry adapter for MACHINE_STRATEGY_v4.1 readiness.

No historical position/outcome simulation is present in this module.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from hashlib import sha256

import machine_strategy_v3_contracts as inherited_core
import machine_strategy_v3_historical_adapter as inherited
from machine_strategy_v4_1_contracts import V41Reject, V41Wait, canonical_decimal
from machine_strategy_v4_1_execution_binding import all_scenario_plans
from machine_strategy_v4_1_selected_poi_inventory import SelectedPoiInventory
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

VERSION = "MACHINE_STRATEGY_v4.1"
TRADE_ENTRY_ALLOWED = False


def serial(value):
    """Canonical design transport; never round or rebuild geometry at serialization."""
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


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
    for bar in frame.bars[
        bisect_right(frame.ends, item["formation_at"]) : frame.cursor
    ]:
        if bar.end <= item["formation_at"] or bar.end > at:
            continue
        if direction == "LONG" and bar.close < anchor:
            return True
        if direction == "SHORT" and bar.close > anchor:
            return True
    return False


class V41HistoricalAdapter(inherited.HistoricalAdapter):
    """Five-family pre-entry adapter. It never imports an outcome runner."""

    def __init__(self, product, market, start, end):
        if product not in PRODUCT_ALIAS:
            raise V4Reject("REJECT_OKX_PRODUCT")
        self.product = product
        self.model_grids = scenarios(product)
        self.sinks = {}
        self.inventory = SelectedPoiInventory()
        self.meta = {}
        self.native_context_open = {}
        self.conditional_pending = {}
        self.conditional_lifecycle = []
        self.zones_by_bos = {}
        self.family_sources = {}
        self.raw_origin_records = {}
        self.contact_active = set()
        self._context_cache = {}
        self._context_cache_at = None
        self._stage = "formation_discovery"
        self._context_id = None
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.rounding = ROUND_HALF_EVEN
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
        direction = item["direction"]
        conf, poi, context, states, approach, pstate = self.prepare(item, at, False)
        if pstate.consumed_at is not None and pstate.consumed_at <= at:
            raise V41Reject("REJECT_SELECTED_POI_PRECONSUMED")
        if pstate.reserved_at is not None:
            raise V41Reject("REJECT_ALREADY_RESERVED")
        native_frame = self.frames[item["setup_tf"]]
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
            "entry_poi_known_at": pstate.eligibility_at,
            "origin_conf_id": pstate.origin_conf_id,
            "origin_conf_known_at": pstate.origin_conf_known_at,
            "proposal_selected_conf_id": conf["id"],
            "selected_poi_state": self.inventory.state(pstate.selected_poi_id),
            "first_test_mapping_status": "V41_CAUSAL_PHYSICAL_INVENTORY",
            "implementation_readiness": "PENDING_INDEPENDENT_QA",
            "parent_deadline_at": item["formation_at"] + 57600,
            "status": "PENDING",
            "physical_idea_id": physical,
            "entry_poi_id": pstate.selected_poi_id,
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
        record = serial(record)
        record["fixed_R_unit"] = canonical_decimal(payoff["planned_stop_unit"])
        plans = all_scenario_plans(record, completed_close=latest_m15.close)
        if plans[0]["status"] != "ELIGIBLE_PENDING":
            raise V41Reject(plans[0].get("reason", "REJECT_REFERENCE_PLAN"))
        record["scenario_plans"] = plans
        return record

    def _register(self, item, poi):
        family = item["branch"]
        parent = (
            poi.get("raw", {}).get("id")
            if family == "BREAKER"
            else item.get("range", {}).get("id")
            if family == "RANGE"
            else item["zone"]["id"]
        )
        origin = None
        if family in ("SFP", "OB"):
            refinement = self.frames[15]
            origin_at = refinement.confirmed_bos.get(poi["origin_bos_id"])
            origin = next(
                (
                    c
                    for c in (
                        refinement.confirmations[
                            bisect_left(
                                refinement.confirm_times, origin_at
                            ) : bisect_right(refinement.confirm_times, origin_at)
                        ]
                        if origin_at is not None
                        else []
                    )
                    if c["bos_id"] == poi["origin_bos_id"]
                ),
                None,
            )
        state = self.inventory.register(
            family=family,
            formation_id=item["formation_id"],
            source_parent_id=parent,
            native_tf=15 if family in ("SFP", "OB") else item["setup_tf"],
            formation_known_at=item["formation_at"],
            reaction_required_at=item["reaction_at"],
            existing_id=poi["id"] if family in ("SFP", "OB") else None,
            direction=item["direction"],
            body_low=poi["low"],
            body_high=poi["high"],
            breaker_formation_known_at=item["formation_at"],
            range_id=item.get("range", {}).get("id"),
            boundary_price=poi["low"],
            zone_born_at=poi["born_at"] if family in ("SFP", "OB") else None,
            origin_bos_id=poi.get("origin_bos_id") if family in ("SFP", "OB") else None,
            expected_origin_conf_id=origin["confirmation_id"] if origin else None,
            expected_origin_conf_known_at=origin["known_at"] if origin else None,
            registration_known_at=max(item["formation_at"], poi["born_at"]),
        )
        self.meta.setdefault(
            state.selected_poi_id,
            {
                "direction": item["direction"],
                "low": poi["low"],
                "high": poi["high"],
                "tf": state.selected_poi_native_tf,
            },
        )
        return state, origin

    def register_family_inventory(self, item, at):
        """Register completed physical evidence even while prerequisites/context WAIT.

        The latest proposal CONF does not define the physical inventory. All own
        BOS-bound contained refined zones remain tracked across later CONF changes.
        """
        if item["branch"] not in ("SFP", "OB"):
            self._register(item, item["zone"])
            return [item["zone"]]
        refinement = self.frames[15]
        zones = []
        for bos in refinement.bos[
            bisect_right(refinement.bos_times, item["formation_at"] - 1) :
        ]:
            if bos["known_at"] > at or bos["direction"] != item["direction"]:
                continue
            for z in self.zones_by_bos.get(bos["id"], []):
                if (
                    bos["known_at"] <= z["born_at"] <= at
                    and z["kind"] in ("OB", "FVG")
                    and item["zone"]["low"]
                    <= z["low"]
                    <= z["high"]
                    <= item["zone"]["high"]
                ):
                    self._register(item, z)
                    zones.append(z)
        return zones

    def _reaction(self, item, at):
        if at >= item["formation_at"] + 57600:
            raise V41Reject("EXPIRED_PENDING")
        frame = self.frames[item["setup_tf"]]
        native = frame.bars[frame.cursor - 1]
        if _structurally_retired(item, frame, at):
            raise V41Reject("REJECT_STRUCTURAL_APPROACH_INVALID")
        if item["next_open_required"]:
            if native.start < item["formation_at"]:
                raise V41Wait("WAIT_SFP_NEXT_NATIVE_OPEN")
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
                raise V41Reject("REJECT_SFP_NEXT_OPEN")
        if item["reaction_at"] is None:
            if native.start < item["formation_at"] or not inherited.intersects(
                native, item["zone"]["low"], item["zone"]["high"]
            ):
                raise V41Wait("WAIT_NATIVE_REACTION")
            if (
                item["branch"] == "RANGE"
                and not item["range"]["low"] < native.close < item["range"]["high"]
            ):
                raise V41Wait("WAIT_RANGE_RECLAIM")
            item["reaction_at"] = native.end

    def _context(self, item, conf, at):
        direction = item["direction"]
        parents = []
        if self._context_cache_at != at:
            self._context_cache = {}
            self._context_cache_at = at
        if direction in self._context_cache:
            states, parents = self._context_cache[direction]
        else:
            states = {
                name: self.frames[tf].state(at)
                for name, tf in [("H1", 60), ("H4", 240), ("D1", 1440)]
            }
            for tf in (240, 1440):
                frame = self.frames[tf]
                for z in inherited.visible_zones(frame, direction):
                    parents.append(
                        {
                            "id": z["id"],
                            "tf": "H4" if tf == 240 else "D1",
                            "direction": direction,
                            "low": z["low"],
                            "high": z["high"],
                            "confirmed": True,
                            "consumed_at": None,
                            "known_at": max(
                                z["born_at"], frame.confirmed_bos[z["origin_bos_id"]]
                            ),
                        }
                    )
            self._context_cache[direction] = (states, parents)
        context = inherited_core.admit_context(
            states=states,
            direction=direction,
            formation_bar=inherited.bar_record(item["formation_bar"]),
            m15_confirmation={
                "id": conf["id"],
                "direction": conf["direction"],
                "known_at": conf["known_at"],
            },
            parent_pois=parents,
            decision_at=at,
            h4_range=self.frames[240].range_record(),
        )
        return context, states

    def prepare(self, item, at, latch):
        physical_zones = self.register_family_inventory(item, at)
        previous_reaction = item["reaction_at"]
        self._reaction(item, at)
        if item["reaction_at"] != previous_reaction:
            # Publish completed reaction provenance before any later M4/context WAIT.
            physical_zones = self.register_family_inventory(item, at)
        direction = item["direction"]
        refinement = self.frames[15]
        confirms = [
            c
            for c in refinement.confirmations[
                bisect_right(refinement.confirm_times, item["reaction_at"]) :
            ]
            if c["direction"] == direction
            and refinement.bos_by_id[c["bos_id"]]["known_at"] >= item["reaction_at"]
            and c["known_at"] <= at
        ]
        conf = (
            max(confirms, key=lambda c: (c["known_at"], c["id"])) if confirms else None
        )
        opposites = [
            {"id": b["id"], "known_at": b["known_at"], "kind": "BOS"}
            for b in refinement.bos[
                bisect_right(refinement.bos_times, item["reaction_at"]) :
            ]
            if b["direction"] != direction and b["known_at"] <= at
        ]
        opposites.extend(
            {"id": c["id"], "known_at": c["known_at"], "kind": "CONF"}
            for c in refinement.confirmations[
                bisect_right(refinement.confirm_times, item["reaction_at"]) :
            ]
            if c["direction"] != direction and c["known_at"] <= at
        )
        approach = classify_approach(
            direction=direction,
            reaction_at=item["reaction_at"],
            selected_conf=conf,
            opposing_events=opposites,
            decision_at=at,
            data_complete=True,
            structurally_retired=False,
        )
        if approach["state"] == "APPROACH_INVALID":
            raise V41Reject("REJECT_STRUCTURAL_APPROACH_INVALID")
        context, states = self._context(item, conf, at)
        if item["branch"] in ("SFP", "OB"):
            bos_at = refinement.bos_by_id[conf["bos_id"]]["known_at"]
            zones = [
                z
                for z in physical_zones
                if z["origin_bos_id"] == conf["bos_id"]
                and z["born_at"] >= bos_at
                and z["kind"] in ("OB", "FVG")
                and item["zone"]["low"] <= z["low"] <= z["high"] <= item["zone"]["high"]
            ]
            if not zones and not latch:
                raise V41Wait("WAIT_ORIGIN_BOUND_REFINEMENT_POI")
        else:
            zones = [item["zone"]]
        candidates = []
        for poi in physical_zones if latch else zones:
            state, origin = self._register(item, poi)
            if item["branch"] in ("SFP", "OB") and (
                origin is None
                or origin["known_at"] > at
                or refinement.bos_by_id[poi["origin_bos_id"]]["known_at"]
                < item["reaction_at"]
            ):
                continue
            if latch and state.eligibility_at is None:
                state = self.inventory.latch_m15(
                    state.selected_poi_id,
                    cutoff=at,
                    origin_conf_id=origin["confirmation_id"]
                    if origin
                    else conf["confirmation_id"],
                    origin_conf_known_at=origin["known_at"]
                    if origin
                    else conf["known_at"],
                    family_prerequisites_complete=True,
                    m4_gate_admissible=True,
                    completed_context_admissible=True,
                    formation_id=item["formation_id"],
                )
                self.contact_active.add(state.selected_poi_id)
            if (
                state.eligibility_at is not None
                and state.consumed_at is None
                and state.reserved_at is None
            ):
                candidates.append((poi, state))
        if not candidates:
            examined = (
                [self.inventory.state(p["id"]) for p in zones]
                if item["branch"] in ("SFP", "OB")
                else [
                    self.inventory.state(
                        self._register(item, item["zone"])[0].selected_poi_id
                    )
                ]
            )
            if examined and all(s["consumed_at"] is not None for s in examined):
                raise V41Reject("REJECT_SELECTED_POI_PRECONSUMED")
            if examined and all(s["reserved_at"] is not None for s in examined):
                raise V41Reject("REJECT_ALREADY_RESERVED")
            raise V41Wait("WAIT_UNCONSUMED_SELECTED_POI")
        poi, state = min(
            candidates,
            key=lambda ps: (
                0 if ps[0].get("kind") == "OB" else 1,
                -ps[0]["born_at"],
                ps[0]["id"],
            ),
        )
        return conf, poi, context, states, approach, state

    def lifecycle_flags(self, order, at, scenario):
        direction = order["direction"]
        setup = self.frames[order["setup_tf"]]
        anchor = Decimal(order["original_structural_anchor"])
        broken = any(
            (b.close < anchor if direction == "LONG" else b.close > anchor)
            for b in setup.bars[
                bisect_right(setup.ends, order["formation_known_at"]) : setup.cursor
            ]
        )
        source = order.get("source_range_id")
        ref = self.frames[15]
        stale = any(
            b["direction"] != direction
            for b in ref.bos[
                bisect_right(ref.bos_times, order["confirmation_known_at"]) :
            ]
        ) or any(
            c["direction"] != direction
            for c in ref.confirmations[
                bisect_right(ref.confirm_times, order["confirmation_known_at"]) :
            ]
        )
        invalid_context = False
        try:
            self._context(
                self.family_sources[order["formation_id"]],
                {
                    "id": order["confirmation_id"],
                    "direction": direction,
                    "known_at": order["confirmation_known_at"],
                },
                at,
            )
        except (inherited_core.ContractWait, inherited_core.ContractReject):
            invalid_context = True
        fta = order["selected_fta_object"]
        tf = self.frames[int(fta["tf"])]
        target_retired = (
            fta["id"] not in tf.pools
            if fta["kind"] == "STRUCTURAL_LIQUIDITY"
            else fta["id"] in tf.retired_ranges
            if fta["kind"] == "RANGE_FAR_BOUNDARY_CAP"
            else tf.zones.get(fta["id"], {}).get("consumed_at") is not None
        )
        latest = self.frames[15].bars[self.frames[15].cursor - 1]
        target_done = (
            latest.close >= Decimal(scenario["target"])
            if direction == "LONG"
            else latest.close <= Decimal(scenario["target"])
        )
        pstate = self.inventory.state(order["entry_poi_id"])
        return {
            "known_at": at,
            "structural_break": broken,
            "source_retired": bool(source and source in setup.retired_ranges),
            "context_invalid": invalid_context,
            "poi_consumed": pstate["consumed_at"] is not None
            and pstate["consumed_at"] <= at,
            "refinement_stale": stale,
            "target_completed": target_retired or target_done,
            "deadline": at >= order["parent_deadline_at"],
            "data_integrity_stop": False,
        }

    def run(self, cutoff=None, checkpoints=()):
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.rounding = ROUND_HALF_EVEN
            return self._source_run(cutoff, checkpoints)

    def _source_run(self, cutoff=None, checkpoints=()):
        cutoff = (
            self.end
            if cutoff is None
            else min(inherited_core.exact_timestamp(cutoff), self.end)
        )
        orders = []
        last_end = None
        self.checkpoint_digests = {}
        for bar in self.market[15]:
            if bar.end > cutoff:
                break
            if last_end is not None and last_end != bar.start:
                raise RuntimeError("SOURCE_DATA_GAP_STOP")
            for tf, frame in self.frames.items():
                if (
                    frame.cursor < len(frame.bars)
                    and frame.bars[frame.cursor].start == bar.start
                ):
                    self.native_context_open[(tf, bar.start)] = (
                        frame.context["direction"]
                        if frame.context and frame.context["known_at"] <= bar.start
                        else None
                    )
            # Conditional pending-only retirement flags. No historical fill/position inference.
            if self.frames[15].cursor:
                for case, order in list(self.conditional_pending.items()):
                    flags = self.lifecycle_flags(
                        order, bar.start, order["scenario_plans"][0]
                    )
                    if any(v for k, v in flags.items() if k != "known_at"):
                        self.conditional_lifecycle.append(
                            {
                                "case_id": case,
                                "known_at": bar.start,
                                "scope": "IF_STILL_PENDING",
                                "flags": flags,
                            }
                        )
                        del self.conditional_pending[case]
            for tf in (1440, 240, 60, 15):
                self.frames[tf].advance(bar.end)
            for obj in self.frames[15].new_events:
                if obj["kind"] in ("OB", "FVG"):
                    z = self.frames[15].zones[obj["id"]]
                    self.zones_by_bos.setdefault(z["origin_bos_id"], []).append(z)
            before = set(self.pending)
            if bar.end % 3600 == 0:
                self.discover(bar.end)
            for key in sorted(set(self.pending) - before):
                item = self.pending[key]
                self.family_sources[item["formation_id"]] = item
                self.raw_origin_records[key] = (
                    item["formation_id"],
                    item["branch"],
                    item["formation_at"],
                    item["direction"],
                    item["setup_tf"],
                    item["zone"]["id"],
                )
                if item["branch"] not in ("SFP", "OB"):
                    self._register(item, item["zone"])
            for key, item in list(self.pending.items()):
                self._stage = "preproposal_inventory"
                self._context_id = None
                try:
                    with localcontext() as ctx:
                        ctx.prec = 50
                        ctx.rounding = ROUND_HALF_EVEN
                        self.prepare(item, bar.end, True)
                    self._emit(item, bar.end, "physical_eligibility", "PASS")
                except (V41Wait, V4Wait, inherited_core.ContractWait) as exc:
                    self._emit(
                        item,
                        bar.end,
                        "physical_eligibility",
                        "WAIT",
                        getattr(exc, "reason", str(exc)),
                    )
                except (V41Reject, V4Reject, inherited_core.ContractReject) as exc:
                    self._emit(
                        item,
                        bar.end,
                        "physical_eligibility",
                        "REJECT",
                        getattr(exc, "reason", str(exc)),
                    )
                    del self.pending[key]
            self.publish_contacts(bar.end)
            if self.start <= bar.end < self.end and bar.end % 3600 == 0:
                proposals = []
                for key, item in list(self.pending.items()):
                    try:
                        with localcontext() as ctx:
                            ctx.prec = 50
                            ctx.rounding = ROUND_HALF_EVEN
                            proposal = self.plan_pending(item, bar.end)
                        proposals.append((key, item, proposal))
                    except (V41Wait, V4Wait, inherited_core.ContractWait) as exc:
                        self._emit(
                            item,
                            bar.end,
                            self._stage,
                            "WAIT",
                            getattr(exc, "reason", str(exc)),
                        )
                    except (V41Reject, V4Reject, inherited_core.ContractReject) as exc:
                        self._emit(
                            item,
                            bar.end,
                            self._stage,
                            "REJECT",
                            getattr(exc, "reason", str(exc)),
                        )
                        del self.pending[key]
                groups = {}
                for triple in proposals:
                    groups.setdefault(triple[2]["physical_idea_id"], []).append(triple)
                for physical, siblings in sorted(groups.items()):
                    siblings.sort(
                        key=lambda row: (
                            inherited.PRIORITY[row[2]["branch"]],
                            -row[2]["setup_tf"],
                            row[2]["setup_id"],
                        )
                    )
                    _, item, chosen = siblings[0]
                    try:
                        new_registry = inherited_core.reserve_idea(
                            self.registry, physical, chosen["entry_poi_id"]
                        )
                        self.inventory.emit_h1_proposal(
                            chosen["entry_poi_id"],
                            emission_decision_at=bar.end,
                            proposal_selected_conf_id=chosen[
                                "proposal_selected_conf_id"
                            ],
                            formation_id=item["formation_id"],
                        )
                        chosen["selected_poi_state"] = self.inventory.state(
                            chosen["entry_poi_id"]
                        )
                        self.registry = new_registry
                        orders.append(chosen)
                        self.conditional_pending[chosen["case_id"]] = chosen
                        self._emit(
                            item,
                            bar.end,
                            "reservation",
                            "ORDER_EMIT",
                            reservation_id=chosen["case_id"],
                        )
                    except (V41Reject, inherited_core.ContractReject) as exc:
                        self._emit(item, bar.end, "reservation", "REJECT", exc.reason)
                    for key, other, _ in siblings:
                        if other is not item:
                            self._emit(
                                other,
                                bar.end,
                                "reservation",
                                "REJECT",
                                "PRIORITY_SIBLING",
                            )
                        self.pending.pop(key, None)
            last_end = bar.end
            if bar.end in checkpoints:
                self.checkpoint_digests[bar.end] = self.source_digest(bar.end, orders)
        return orders, {
            "strategy_version": VERSION,
            "product": self.product,
            "cutoff": cutoff,
            "raw_origins": serial(sorted(self.raw_origin_records.values())),
            "inventory": self.inventory.snapshot(),
            "conditional_pending_lifecycle": self.conditional_lifecycle,
            "telemetry": [s.snapshot() for _, s in sorted(self.sinks.items())],
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
            "historical_position_engine_calls": 0,
            "historical_position_evaluations": 0,
            "financial_outcomes_generated": False,
            "trade_entry_allowed": False,
        }

    def publish_contacts(self, at):
        for pid in sorted(self.contact_active):
            meta = self.meta[pid]
            frame = self.frames[meta["tf"]]
            native = frame.bars[frame.cursor - 1] if frame.cursor else None
            if native is not None and native.end == at:
                self.inventory.observe_native_bar(
                    pid,
                    native_bar_open=native.start,
                    native_bar_close=native.end,
                    intersects=native.low <= meta["high"]
                    and native.high >= meta["low"],
                    native_context_admissible_at_open=self.native_context_open.get(
                        (meta["tf"], native.start)
                    )
                    == meta["direction"],
                )
                if self.inventory.state(pid)["consumed_at"] is not None:
                    self.contact_active.discard(pid)

    def source_digest(self, at, orders):
        return identity(
            "source_checkpoint",
            at,
            orders,
            self.inventory.snapshot(),
            self.conditional_lifecycle,
            [sink.snapshot() for _, sink in sorted(self.sinks.items())],
            {
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
        )

    def catalog(self, cutoff=None):
        return self.run(cutoff)


# Public source-only spelling retained from incoming authored checkpoint.
V41HistoricalSourceAdapter = V41HistoricalAdapter


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
