"""Read-only causal source lifecycle; no fill, exit or financial calculations."""

from __future__ import annotations

from copy import deepcopy

import machine_strategy_v3_contracts as core
import machine_strategy_v3_historical_adapter as raw
from machine_strategy_v4_readiness_core import V4Wait, dec, timestamp


class SourceLifecycle:
    def __init__(self, order, market):
        if order.get("first_test_mapping_status") != "NATIVE_ORIGIN_CONF":
            raise V4Wait("WAIT_VERSIONED_SELECTED_POI_FIRST_TEST_CONTRACT")
        self.order = deepcopy(order)
        self.native = market[15]
        self.frames = {
            tf: raw.HistoricalFrame(order["symbol"], tf, market[tf])
            for tf in (1440, 240, 60, 15)
        }
        self.cursor = 0
        self.poi_consumed_at = None
        self.last_cutoff = -1

    def flags(self, cutoff, scenario):
        timestamp(cutoff)
        if cutoff < self.last_cutoff:
            raise V4Wait("UNKNOWN_NONCAUSAL_LIFECYCLE")
        order = self.order
        direction = order["direction"]
        while self.cursor < len(self.native) and self.native[self.cursor].end <= cutoff:
            at = self.native[self.cursor].end
            for tf in (1440, 240, 60, 15):
                frame = self.frames[tf]
                if tf == order["entry_poi_tf"] and frame.cursor < len(frame.bars):
                    bar = frame.bars[frame.cursor]
                    if (
                        bar.end == at
                        and bar.start >= order["entry_poi_known_at"]
                        and frame.context
                        and frame.context["direction"] == direction
                    ):
                        zone = order["structural_entry_zone"]
                        if bar.low <= dec(zone["high"]) and bar.high >= dec(
                            zone["low"]
                        ):
                            self.poi_consumed_at = self.poi_consumed_at or at
                frame.advance(at)
            self.cursor += 1
        self.last_cutoff = cutoff
        if not self.cursor or self.native[self.cursor - 1].end != cutoff:
            raise V4Wait("UNKNOWN_DATA_GAP")
        latest = self.native[self.cursor - 1]
        setup = self.frames[order["setup_tf"]]
        anchor = dec(order["original_structural_anchor"])
        structural = any(
            (b.close < anchor if direction == "LONG" else b.close > anchor)
            for b in setup.bars[: setup.cursor]
            if order["formation_known_at"] < b.end <= cutoff
        )
        source_range = order.get("source_range_id")
        source_retired = bool(source_range and source_range in setup.retired_ranges)
        refinement = self.frames[15]
        opposite = any(
            e["direction"] != direction
            and order["confirmation_known_at"] < e["known_at"] <= cutoff
            for e in [*refinement.bos, *refinement.confirmations]
        )
        poi = self.frames[order["entry_poi_tf"]].zones.get(order["entry_poi_id"])
        consumed = self.poi_consumed_at is not None or bool(
            poi and poi.get("consumed_at") is not None
        )
        fta = order["selected_fta_object"]
        target_frame = self.frames[int(fta["tf"])]
        if fta["kind"] == "STRUCTURAL_LIQUIDITY":
            retired_target = fta["id"] not in target_frame.pools
        elif fta["kind"] == "RANGE_FAR_BOUNDARY_CAP":
            retired_target = fta["id"] in target_frame.retired_ranges
        else:
            target_zone = target_frame.zones.get(fta["id"])
            if target_zone is None:
                raise V4Wait("UNKNOWN_SELECTED_FTA_SOURCE")
            retired_target = target_zone.get("consumed_at") is not None
        states = {
            name: self.frames[tf].state(cutoff)
            for name, tf in (("H1", 60), ("H4", 240), ("D1", 1440))
        }
        parents = []
        for tf in (240, 1440):
            for zone in raw.visible_zones(self.frames[tf], direction):
                parents.append(
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
        invalid_context = False
        try:
            core.admit_context(
                states=states,
                direction=direction,
                formation_bar=order["formation_bar"],
                m15_confirmation={
                    "id": order["confirmation_id"],
                    "direction": direction,
                    "known_at": order["confirmation_known_at"],
                },
                parent_pois=parents,
                decision_at=cutoff,
                h4_range=self.frames[240].range_record(),
            )
        except (core.ContractWait, core.ContractReject):
            invalid_context = True
        return {
            "known_at": cutoff,
            "structural_break": structural,
            "source_retired": source_retired,
            "context_invalid": invalid_context,
            "poi_consumed": consumed,
            "refinement_stale": opposite,
            "target_completed": retired_target
            or (
                latest.close >= dec(scenario["target"])
                if direction == "LONG"
                else latest.close <= dec(scenario["target"])
            ),
            "data_integrity_stop": False,
        }
