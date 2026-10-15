"""Production-intent source/lifecycle adapter for MACHINE_STRATEGY_v4.1.

This module is deliberately pre-financial.  It walks sealed OKX completed bars,
tracks the frozen v4.1 selected-POI lifecycle on every M15 cutoff, and can emit
pre-entry proposal records.  It never evaluates historical fills, exits, P&L,
WR/PF/DD, PAPER, LIVE, or private exchange actions.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from hashlib import sha256

import machine_strategy_v3_contracts as inherited_core
import machine_strategy_v3_historical_adapter as inherited
import machine_strategy_v4_historical_adapter as v4
from machine_strategy_v2_core import serial
from machine_strategy_v4_1_contracts import V41Reject, V41Wait, canonical_decimal
from machine_strategy_v4_1_selected_poi_inventory import SelectedPoiInventory
from machine_strategy_v4_readiness_core import (
    V4Reject,
    V4Wait,
    classify_approach,
    planned_payoff_gate,
    target_lifecycle_ok,
)
from machine_strategy_v4_readiness_core import executable_plan as v4_executable_plan
from okx_v3_compatibility_binding_v1 import PRODUCT_ALIAS, scenarios

VERSION = "MACHINE_STRATEGY_v4.1"
TRADE_ENTRY_ALLOWED = False


def identity(kind: str, *parts: object) -> str:
    return sha256(
        inherited.compact(serial([VERSION, kind, *parts])).encode("utf-8")
    ).hexdigest()


def _rounded_entry(raw_entry: Decimal, tick: Decimal, direction: str) -> Decimal:
    mode = ROUND_FLOOR if direction == "LONG" else ROUND_CEILING
    return (raw_entry / tick).to_integral_value(rounding=mode) * tick


def _bar_intersects(bar, low: Decimal, high: Decimal) -> bool:
    return bar.low <= high and bar.high >= low


class V41HistoricalSourceAdapter(v4.V4HistoricalAdapter):
    """v4.1 source-only adapter with monotonic selected-POI ownership."""

    def __init__(self, product, market, start, end):
        if product not in PRODUCT_ALIAS:
            raise V41Reject("REJECT_OKX_PRODUCT")
        super().__init__(product, market, start, end)
        self.poi_inventory = SelectedPoiInventory()
        self._item_to_poi: dict[tuple[str, str], str] = {}
        self._poi_meta: dict[str, dict] = {}
        self._source_events: list[dict] = []
        self._historical_position_engine_calls = 0

    @staticmethod
    def _item_key(item) -> tuple[str, str]:
        return str(item["formation_id"]), str(item["branch"])

    def _latest_m15_conf(self, item, at: int):
        reaction_at = item.get("reaction_at")
        if reaction_at is None:
            return None
        refinement = self.frames[15]
        candidates = [
            conf
            for conf in refinement.confirmations
            if reaction_at < conf["known_at"] <= at
            and conf["direction"] == item["direction"]
            and refinement.bos_by_id[conf["bos_id"]]["known_at"] >= reaction_at
        ]
        return (
            max(candidates, key=lambda row: (row["known_at"], row["id"]))
            if candidates
            else None
        )

    def _refined_poi(self, item, conf):
        if conf is None:
            return None
        refinement = self.frames[15]
        bos_at = refinement.bos_by_id[conf["bos_id"]]["known_at"]
        parent = item["zone"]
        zones = [
            zone
            for zone in refinement.zones.values()
            if zone["direction"] == item["direction"]
            and zone["born_at"] >= bos_at
            and zone["origin_bos_id"] == conf["bos_id"]
            and zone["kind"] in ("OB", "FVG")
            and parent["low"] <= zone["low"] <= zone["high"] <= parent["high"]
        ]
        if not zones:
            return None
        return min(
            zones,
            key=lambda zone: (
                0 if zone["kind"] == "OB" else 1,
                -zone["born_at"],
                zone["id"],
            ),
        )

    def _register_selected_poi(self, item, at: int) -> str | None:
        key = self._item_key(item)
        if key in self._item_to_poi:
            return self._item_to_poi[key]
        branch = item["branch"]
        direction = item["direction"]
        zone = item["zone"]
        kwargs: dict = {
            "family": branch,
            "formation_id": item["formation_id"],
            "formation_known_at": item["formation_at"],
            "reaction_required_at": None,
            "direction": direction,
        }
        selected_zone = zone
        if branch in ("SFP", "OB"):
            conf = self._latest_m15_conf(item, at)
            selected_zone = self._refined_poi(item, conf)
            if selected_zone is None:
                return None
            kwargs.update(
                source_parent_id=zone["id"],
                native_tf=15,
                existing_id=selected_zone["id"],
            )
        elif branch == "STB":
            kwargs.update(
                source_parent_id=zone.get("raw", {}).get("id", zone["id"]),
                native_tf=item["setup_tf"],
                body_low=zone["low"],
                body_high=zone["high"],
                reaction_required_at=item["formation_at"],
            )
        elif branch == "BREAKER":
            parent_id = zone.get("raw", {}).get("id") or zone.get("source_parent_id")
            if not parent_id:
                parent_id = item["formation_id"]
            kwargs.update(
                source_parent_id=parent_id,
                native_tf=item["setup_tf"],
                breaker_formation_known_at=item["formation_at"],
                reaction_required_at=item["formation_at"],
            )
        elif branch == "RANGE":
            range_id = item["range"]["id"]
            boundary = (
                item["range"]["low"]
                if direction == "LONG"
                else item["range"]["high"]
            )
            kwargs.update(
                source_parent_id=range_id,
                native_tf=item["setup_tf"],
                range_id=range_id,
                boundary_price=boundary,
            )
        else:
            raise V41Reject("REJECT_FAMILY")

        state = self.poi_inventory.register(**kwargs)
        self._item_to_poi[key] = state.selected_poi_id
        self._poi_meta[state.selected_poi_id] = {
            "family": branch,
            "direction": direction,
            "low": Decimal(str(selected_zone["low"])),
            "high": Decimal(str(selected_zone["high"])),
            "item_key": key,
        }
        self._source_events.append(
            {
                "event": "SELECTED_POI_REGISTERED",
                "selected_poi_id": state.selected_poi_id,
                "formation_id": item["formation_id"],
                "family": branch,
                "known_at": at,
            }
        )
        return state.selected_poi_id

    def _set_reaction_if_known(self, item, selected_id: str) -> None:
        reaction_at = item.get("reaction_at")
        if reaction_at is None:
            return
        state = self.poi_inventory.state_object(selected_id)
        if state.reaction_required_at is None:
            self.poi_inventory.set_reaction_required_at(
                selected_id, known_at=reaction_at
            )

    def _approach_conf(self, item, at: int):
        conf = self._latest_m15_conf(item, at)
        if conf is None:
            raise V41Wait("WAIT_REFINEMENT_BOS_CONF")
        refinement = self.frames[15]
        opposite = [
            {"id": bos["id"], "known_at": bos["known_at"], "kind": "BOS"}
            for bos in refinement.bos
            if bos["direction"] != item["direction"]
            and item["reaction_at"] < bos["known_at"] <= at
        ]
        opposite.extend(
            {
                "id": row["id"],
                "known_at": row["known_at"],
                "kind": "CONF",
            }
            for row in refinement.confirmations
            if row["direction"] != item["direction"]
            and item["reaction_at"] < row["known_at"] <= at
        )
        approach = classify_approach(
            direction=item["direction"],
            reaction_at=item["reaction_at"],
            selected_conf=conf,
            opposing_events=opposite,
            decision_at=at,
            data_complete=True,
            structurally_retired=v4._structurally_retired(
                item, self.frames[item["setup_tf"]], at
            ),
        )
        if approach["state"] == "APPROACH_INVALID":
            raise V41Reject("REJECT_STRUCTURAL_APPROACH_INVALID")
        return conf, approach

    def _context_for(self, item, conf, at: int):
        direction = item["direction"]
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
        return context, states

    def _latch_item_eligibility(self, item, at: int) -> None:
        selected_id = self._register_selected_poi(item, at)
        if selected_id is None:
            return
        self._set_reaction_if_known(item, selected_id)
        state = self.poi_inventory.state_object(selected_id)
        if state.eligibility_at is not None or state.terminal:
            return
        if at >= state.deadline:
            self.poi_inventory.retire(
                selected_id, known_at=at, reason="EXPIRED_PENDING"
            )
            return
        if item.get("reaction_at") is None and item["branch"] in (
            "SFP",
            "OB",
            "RANGE",
        ):
            return
        conf, _ = self._approach_conf(item, at)
        try:
            self._context_for(item, conf, at)
            context_ok = True
        except inherited_core.ContractWait:
            context_ok = False
        self.poi_inventory.latch_m15(
            selected_id,
            cutoff=at,
            origin_conf_id=conf["id"],
            origin_conf_known_at=conf["known_at"],
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=context_ok,
        )

    def _native_contact_publication(self, at: int, context_at_open: dict) -> None:
        for selected_id in self.poi_inventory.ids():
            state = self.poi_inventory.state_object(selected_id)
            if state.eligibility_at is None or state.terminal:
                continue
            tf = state.selected_poi_native_tf
            frame = self.frames[tf]
            if not frame.cursor:
                continue
            bar = frame.bars[frame.cursor - 1]
            if bar.end != at:
                continue
            meta = self._poi_meta[selected_id]
            prior = context_at_open.get(tf)
            context_ok = bool(
                prior
                and prior.get("known_at", bar.end + 1) <= bar.start
                and prior.get("direction") == meta["direction"]
            )
            is_required_reaction = bool(
                meta["family"] == "RANGE"
                and state.reaction_required_at is not None
                and bar.end == state.reaction_required_at
            )
            self.poi_inventory.observe_native_bar(
                selected_id,
                native_bar_open=bar.start,
                native_bar_close=bar.end,
                intersects=_bar_intersects(bar, meta["low"], meta["high"]),
                native_context_admissible_at_open=context_ok,
                is_required_reaction_contact=is_required_reaction,
            )

    def _advance_family_reaction(self, item, at: int) -> None:
        """Update native family prerequisites only from a newly completed native bar."""
        frame = self.frames[item["setup_tf"]]
        if not frame.cursor:
            return
        native = frame.bars[frame.cursor - 1]
        if native.end != at:
            return
        if item.get("next_open_required"):
            if native.start < item["formation_at"]:
                return
            item["next_open_required"] = False
            item["next_open_evidence"] = {
                "actual_at": native.start,
                "known_at": native.end,
                "open": native.open,
            }
            valid = (
                native.open > item["level"]
                if item["direction"] == "LONG"
                else native.open < item["level"]
            )
            if not valid:
                item["terminal_source_reason"] = "REJECT_SFP_NEXT_OPEN"
                return
        if item.get("reaction_at") is not None:
            return
        if native.start < item["formation_at"]:
            return
        if not inherited.intersects(native, item["zone"]["low"], item["zone"]["high"]):
            return
        if (
            item["branch"] == "RANGE"
            and not item["range"]["low"] < native.close < item["range"]["high"]
        ):
            return
        item["reaction_at"] = native.end
        selected_id = self._register_selected_poi(item, at)
        if selected_id is not None:
            self._set_reaction_if_known(item, selected_id)

    def _proposal_record(self, item, at: int) -> dict:
        key = self._item_key(item)
        selected_id = self._item_to_poi.get(key)
        if selected_id is None:
            raise V41Wait("WAIT_SELECTED_POI_REGISTRATION")
        state = self.poi_inventory.state_object(selected_id)
        if state.eligibility_at is None:
            raise V41Wait("WAIT_SELECTED_POI_ELIGIBILITY")
        if state.consumed_at is not None and state.consumed_at <= at:
            raise V41Reject("REJECT_SELECTED_POI_PRECONSUMED")
        if state.retired_at is not None and state.retired_at <= at:
            raise V41Reject("REJECT_SELECTED_POI_RETIRED")

        conf, approach = self._approach_conf(item, at)
        context, states = self._context_for(item, conf, at)
        meta = self._poi_meta[selected_id]
        direction = item["direction"]
        raw = inherited_core.raw_family_prices(
            family=item["branch"],
            direction=direction,
            zone_low=meta["low"],
            zone_high=meta["high"],
            stop_anchor=item["extreme"],
            atr14=item["atr"] if item["branch"] == "SFP" else None,
        )
        raw["known_at"] = at
        h1 = self.frames[60].context
        if h1 is None:
            raise V41Wait("WAIT_COMPLETE_H1_CONTEXT")
        targets, pools = inherited.inventories(
            self.frames, direction, raw["raw_entry"], raw["raw_stop_boundary"], h1
        )
        if item["branch"] == "RANGE":
            if item["range"]["id"] in self.frames[item["setup_tf"]].retired_ranges:
                raise V41Reject("REJECT_RETIRED_SOURCE_RANGE")
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
        nearest, coincident = v4._select_fta(targets, reference_entry, direction, at)
        raw_fta = Decimal(str(nearest["price"]))
        plan = v4_executable_plan(
            direction=direction,
            raw_entry=raw["raw_entry"],
            protective_boundary=raw["raw_stop_boundary"],
            raw_fta=raw_fta,
            structural_low=meta["low"],
            structural_high=meta["high"],
            tick=tick,
        )
        latest_m15 = self.frames[15].bars[self.frames[15].cursor - 1]
        target_lifecycle_ok(
            direction=direction,
            completed_close=latest_m15.close,
            raw_fta=raw_fta,
            inward_target=plan["target"],
        )
        payoff = planned_payoff_gate(
            direction=direction,
            entry=plan["entry"],
            stop=plan["stop"],
            target=plan["target"],
        )
        if any(pool["adverse"] for pool in pools):
            raise V41Reject("REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP")

        state = self.poi_inventory.emit_h1_proposal(
            selected_id,
            emission_decision_at=at,
            proposal_selected_conf_id=conf["id"],
        )
        physical = identity("physical", self.symbol, item["formation_at"], direction)
        setup = identity(
            "setup", physical, item["formation_id"], conf["id"], selected_id
        )
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
            "parent_deadline_at": item["formation_at"] + 57600,
            "status": "PENDING_SOURCE_ONLY",
            "physical_idea_id": physical,
            "entry_poi_id": selected_id,
            "selected_poi_kind": state.selected_poi_kind,
            "selected_poi_native_tf": state.selected_poi_native_tf,
            "origin_conf_id": state.origin_conf_id,
            "origin_conf_known_at": state.origin_conf_known_at,
            "eligibility_at": state.eligibility_at,
            "proposal_selected_conf_id": state.proposal_selected_conf_id,
            "setup_id": setup,
            "case_id": identity("pre_entry_order", setup, at),
            "formation_id": item["formation_id"],
            "confirmation_id": conf["id"],
            "confirmation_known_at": conf["known_at"],
            "approach": approach,
            "context": context,
            "states": states,
            "selected_impulse": h1,
            "structural_entry_zone": {
                "low": canonical_decimal(meta["low"]),
                "high": canonical_decimal(meta["high"]),
            },
            "raw_entry": canonical_decimal(raw["raw_entry"]),
            "protective_boundary": canonical_decimal(raw["raw_stop_boundary"]),
            "raw_fta_price": canonical_decimal(raw_fta),
            "nearest_fta_id": nearest["id"],
            "coincident_fta_ids": coincident,
            "all_FTA_inventory": targets,
            "FTA_inventory_digest": identity("FTA_inventory", targets),
            "liquidity_inventory": pools,
            "liquidity_inventory_digest": identity("liquidity", pools),
            "planned_payoff": {
                "planned_stop_unit": canonical_decimal(payoff["planned_stop_unit"]),
                "net_target_doubled": canonical_decimal(payoff["net_target_doubled"]),
                "ratio": canonical_decimal(payoff["ratio"]),
            },
            "reference_scenario_id": reference_grid["id"],
            "historical_position_evaluations": 0,
            "financial_outcomes_generated": False,
            "trade_entry_allowed": False,
        }
        return serial(record)

    def run(self, cutoff=None):
        cutoff = (
            self.end - 1
            if cutoff is None
            else min(inherited_core.exact_timestamp(cutoff), self.end - 1)
        )
        proposals: list[dict] = []
        diagnostics: list[dict] = []
        raw_origins: dict = {}

        for m15_bar in self.market[15]:
            at = m15_bar.end
            if at > cutoff:
                break

            # Native context at OPEN must be captured before the current bars close.
            context_at_open = {
                tf: deepcopy(self.frames[tf].context) for tf in (15, 60, 240)
            }
            for tf in (1440, 240, 60, 15):
                self.frames[tf].advance(at)

            # H1/H4 formation discovery remains on completed source-native closes.
            if at % 3600 == 0:
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
                    self._register_selected_poi(item, at)

            # Native family prerequisites are updated only when their own bar closes.
            for item in list(self.pending.values()):
                self._advance_family_reaction(item, at)

            # Register newly materialized refined SFP/OB POIs before eligibility.
            for item in list(self.pending.values()):
                self._register_selected_poi(item, at)

            # Contacts from the bar that just completed become known now, before
            # any equal-cutoff H1 proposal is allowed to reserve the POI.
            self._native_contact_publication(at, context_at_open)

            # Every completed M15 cutoff may become the FIRST eligibility latch.
            for key, item in list(self.pending.items()):
                try:
                    if item.get("terminal_source_reason"):
                        raise V41Reject(item["terminal_source_reason"])
                    if at >= item["formation_at"] + 57600:
                        selected = self._item_to_poi.get(self._item_key(item))
                        if selected:
                            self.poi_inventory.retire(
                                selected, known_at=at, reason="EXPIRED_PENDING"
                            )
                        raise V41Reject("EXPIRED_PENDING")
                    if v4._structurally_retired(
                        item, self.frames[item["setup_tf"]], at
                    ):
                        selected = self._item_to_poi.get(self._item_key(item))
                        if selected:
                            self.poi_inventory.retire(
                                selected,
                                known_at=at,
                                reason="REJECT_STRUCTURAL_APPROACH_INVALID",
                            )
                        raise V41Reject("REJECT_STRUCTURAL_APPROACH_INVALID")
                    self._latch_item_eligibility(item, at)
                except (
                    V41Wait,
                    V4Wait,
                    inherited_core.ContractWait,
                ) as exc:
                    reason = getattr(exc, "reason", str(exc))
                    self.counts[reason] += 1
                except (
                    V41Reject,
                    V4Reject,
                    inherited_core.ContractReject,
                ) as exc:
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
                    del self.pending[key]

            # New trade proposals remain H1-only.  No fill or position engine runs.
            if at % 3600:
                continue
            candidates = []
            for key, item in list(self.pending.items()):
                try:
                    proposal = self._proposal_record(item, at)
                    candidates.append((key, item, proposal))
                except (
                    V41Wait,
                    V4Wait,
                    inherited_core.ContractWait,
                ) as exc:
                    reason = getattr(exc, "reason", str(exc))
                    self.counts[reason] += 1
                    continue
                except (
                    V41Reject,
                    V4Reject,
                    inherited_core.ContractReject,
                ) as exc:
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
                    del self.pending[key]

            groups: dict[str, list] = {}
            for key, item, proposal in candidates:
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
                            "branch": proposal["branch"],
                            "formation_id": proposal["formation_id"],
                            "setup_id": proposal["setup_id"],
                        }
                        for _, _, proposal in ordered[1:]
                    ]
                    proposals.append(chosen)
                except inherited_core.ContractReject as exc:
                    diagnostics.append(
                        {
                            "formation_id": item["formation_id"],
                            "branch": item["branch"],
                            "decision_at": at,
                            "reason": exc.reason,
                        }
                    )
                for pending_key, _, _ in ordered:
                    self.pending.pop(pending_key, None)

        for item in self.pending.values():
            diagnostics.append(
                {
                    "formation_id": item["formation_id"],
                    "branch": item["branch"],
                    "decision_at": cutoff,
                    "reason": "PENDING_SOURCE_EOF",
                }
            )
        return proposals, {
            "venue": "OKX",
            "product": self.product,
            "strategy_version": VERSION,
            "raw_origins": serial(sorted(raw_origins.values())),
            "diagnostics": diagnostics,
            "pending_source_count": len(self.pending),
            "selected_poi_inventory": self.poi_inventory.snapshot(),
            "counts": dict(self.counts),
            "cutoff": cutoff,
            "frame_prefix_digests": {
                str(tf): identity(
                    "frame",
                    tf,
                    frame.context,
                    frame.confirmations,
                    frame.zones,
                    frame.pools,
                    frame.range_record(),
                )
                for tf, frame in self.frames.items()
            },
            "historical_position_engine_calls": self._historical_position_engine_calls,
            "historical_position_evaluations": 0,
            "financial_outcomes_generated": False,
            "trade_entry_allowed": False,
        }

    def catalog(self, cutoff=None):
        return self.run(cutoff)


def market_inputs(product):
    return v4.market_inputs(product)
