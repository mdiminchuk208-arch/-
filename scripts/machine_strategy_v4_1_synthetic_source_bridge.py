"""Closed registered source-state seeds for production lifecycle/kernel parity.

Seed context facts are supplied synthetic evidence, not discovered historical
signals. Contact publication and lifecycle_flags are the actual adapter methods.
No caller-provided source state, bars, context or financial authorization allowed.
"""

from __future__ import annotations

from bisect import bisect_right
from decimal import Decimal
from types import SimpleNamespace

from machine_strategy_v4_1_historical_adapter import V41HistoricalAdapter
from machine_strategy_v4_1_selected_poi_inventory import SelectedPoiInventory


class SeedFrame:
    def __init__(self, tf, bars, direction, target):
        self.tf = tf
        self.bars = bars
        self.ends = [b.end for b in bars]
        self.cursor = 0
        self.direction = direction
        self.context = {"direction": direction, "known_at": 0}
        self.bos = []
        self.bos_times = []
        self.confirmations = []
        self.confirm_times = []
        self.retired_ranges = {}
        self.zones = {}
        self.confirmed_bos = {}
        self.pools = {"fixture-fta": {"price": target, "known_at": 0}}

    def advance(self, at):
        self.cursor = bisect_right(self.ends, at)

    def state(self, at):
        return {
            "state": "TREND_UP" if self.direction == "LONG" else "TREND_DOWN",
            "direction": self.direction,
            "context_id": "registered-completed-seed",
            "known_at": 0,
        }

    def range_record(self):
        return None

    def candidates_zones(self, direction, **kwargs):
        return []


class ClosedSourceBridge:
    def __init__(self, order, bars):
        # Instantiation only from the guarded driver's sealed named fixture scope.
        source = object.__new__(V41HistoricalAdapter)
        source.inventory = SelectedPoiInventory()
        source.meta = {}
        source.contact_active = set()
        source.native_context_open = {}
        source._context_cache = {}
        source._context_cache_at = None
        source.family_sources = {}
        direction = order["direction"]
        native = [
            SimpleNamespace(
                start=b["start"],
                end=b["end"],
                **{k: Decimal(b[k]) for k in ("open", "high", "low", "close")},
            )
            for b in bars
        ]
        market = {15: native}
        for tf in (60, 240, 1440):
            seconds = tf * 60
            groups = {}
            for bar in native:
                groups.setdefault(bar.start // seconds * seconds, []).append(bar)
            market[tf] = [
                SimpleNamespace(
                    start=at,
                    end=at + seconds,
                    open=g[0].open,
                    high=max(b.high for b in g),
                    low=min(b.low for b in g),
                    close=g[-1].close,
                )
                for at, g in sorted(groups.items())
                if len(g) == tf // 15 and g[0].start == at and g[-1].end == at + seconds
            ]
        source.frames = {
            tf: SeedFrame(tf, data, direction, Decimal(order["raw_fta_price"]))
            for tf, data in market.items()
        }
        source.family_sources[order["formation_id"]] = {
            "direction": direction,
            "formation_bar": SimpleNamespace(**order["formation_bar"]),
        }
        for key in ("open", "high", "low", "close"):
            setattr(
                source.family_sources[order["formation_id"]]["formation_bar"],
                key,
                Decimal(order["formation_bar"][key]),
            )
        selected_tf = 15 if order["branch"] in ("SFP", "OB") else 240
        state = source.inventory.register(
            family=order["branch"],
            formation_id=order["formation_id"],
            source_parent_id="registered-source-parent",
            native_tf=selected_tf,
            formation_known_at=order["formation_known_at"],
            reaction_required_at=order["formation_known_at"],
            existing_id=order["entry_poi_id"] if selected_tf == 15 else None,
            direction=direction,
            body_low=order["raw_entry"],
            body_high=order["raw_entry"],
            breaker_formation_known_at=order["formation_known_at"],
            range_id="registered-range",
            boundary_price=order["raw_entry"],
            zone_born_at=28800 if selected_tf == 15 else None,
            origin_bos_id="registered-BOS" if selected_tf == 15 else None,
            expected_origin_conf_id=order["confirmation_id"]
            if selected_tf == 15
            else None,
            expected_origin_conf_known_at=order["confirmation_known_at"]
            if selected_tf == 15
            else None,
        )
        if state.selected_poi_id != order["entry_poi_id"]:
            raise ValueError("FIXTURE_PHYSICAL_ID_MISMATCH")
        source.meta[state.selected_poi_id] = {
            "direction": direction,
            "low": Decimal(order["raw_entry"]),
            "high": Decimal(order["raw_entry"]),
            "tf": selected_tf,
        }
        source.inventory.latch_m15(
            state.selected_poi_id,
            cutoff=order["selected_eligibility_at"],
            origin_conf_id=order["confirmation_id"],
            origin_conf_known_at=order["confirmation_known_at"],
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        source.contact_active.add(state.selected_poi_id)
        self.source = source
        self.order = order
        self.native = native
        self.cursor = 0
        self.flag_trace = []
        self.advance(order["decision_at"])
        source.inventory.emit_h1_proposal(
            state.selected_poi_id,
            emission_decision_at=order["decision_at"],
            proposal_selected_conf_id=order["confirmation_id"],
        )

    def advance(self, at):
        while self.cursor < len(self.native) and self.native[self.cursor].end <= at:
            bar = self.native[self.cursor]
            for tf, frame in self.source.frames.items():
                if bar.start % (tf * 60) == 0:
                    self.source.native_context_open[(tf, bar.start)] = (
                        frame.direction
                        if bar.start >= self.order["native_context_known_at"]
                        else None
                    )
            for tf in (1440, 240, 60, 15):
                self.source.frames[tf].advance(bar.end)
            self.source.publish_contacts(bar.end)
            self.cursor += 1

    def flags(self, at, scenario):
        self.advance(at)
        result = self.source.lifecycle_flags(self.order, at, scenario)
        self.flag_trace.append({"open": at, "flags": dict(result)})
        return result

    def finish(self):
        self.advance(self.native[-1].end)

    def receipt(self):
        return {
            "scope": "REGISTERED_SYNTHETIC_CLOSED_SOURCE_SEED",
            "selected_state": self.source.inventory.state(self.order["entry_poi_id"]),
            "M15_OPEN_flag_trace": self.flag_trace,
            "actual_adapter_contact_method": True,
            "actual_adapter_lifecycle_flags": True,
            "historical_source_used": False,
        }
