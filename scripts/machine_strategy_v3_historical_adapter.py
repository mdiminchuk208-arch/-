"""Historical pre-entry adapter for the frozen v3; never simulates a position."""

from __future__ import annotations

import csv
import gzip
import json
from bisect import bisect_right
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256

from machine_strategy_v2_core import (
    Frame,
    direction_cross,
    intersects,
    raw_pending,
    serial,
)
from machine_strategy_v3_contracts import (
    CONTRACT_TYPE,
    ContractReject,
    ContractWait,
    admit_context,
    completed_atr14,
    exact_timestamp,
    executable_plan,
    first_test,
    frame_state,
    raw_family_prices,
    reserve_idea,
)
from original_v1_1_financial_data import (
    END,
    ROOT,
    START,
    WARMUP,
    Bar,
    compact,
    validate_bars,
)

VERSION = "MACHINE_STRATEGY_v3"
FAMILIES = ("SFP", "OB", "BREAKER", "STB", "RANGE")
PRIORITY = {name: i for i, name in enumerate(("BREAKER", "STB", "SFP", "OB", "RANGE"))}


def identity(kind, *parts):
    return sha256(compact(serial([VERSION, kind, *parts])).encode()).hexdigest()


def bar_record(bar):
    return {
        "start": bar.start,
        "end": bar.end,
        **{k: str(getattr(bar, k)) for k in ("open", "high", "low", "close")},
    }


def load_primary(symbol, *, warmup=WARMUP, end=END):
    if symbol not in ("BTCUSDT", "ETHUSDT"):
        raise ContractReject("REJECT_UNSUPPORTED_HISTORICAL_SYMBOL")
    path = ROOT / f"data/history/public_research/bybit_mirror/{symbol}/15.csv.gz"
    inventory = json.loads(
        (
            ROOT / "docs/machine_strategy_v3_design/DATA_EXPOSURE_INVENTORY.json"
        ).read_text()
    )
    expected = next(
        r["stored_sha256"]
        for r in inventory["series"]
        if r["path"] == str(path.relative_to(ROOT))
    )
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ContractReject("REJECT_HISTORICAL_SOURCE_HASH")
    result = []
    with gzip.open(path, "rt") as stream:
        for row in csv.DictReader(stream):
            ms = int(row["open_time_ms"])
            if ms % 1000:
                raise ContractReject("REJECT_SUBSECOND_BAR_GRID")
            at = ms // 1000
            if at < warmup or at + 900 > end:
                continue
            if (
                row["symbol"] != symbol
                or row["exchange"] != "BYBIT"
                or row["interval"] != "15"
                or row["is_closed"] != "1"
            ):
                raise ContractReject("REJECT_SOURCE_IDENTITY_OR_COMPLETION")
            result.append(
                Bar(
                    at,
                    at + 900,
                    *(Decimal(row[k]) for k in ("open", "high", "low", "close")),
                )
            )
    validate_primary(result)
    return result, {
        "path": str(path.relative_to(ROOT)),
        "sha256": actual,
        "symbol": symbol,
        "contract_type": CONTRACT_TYPE,
        "origin": "PINNED_PUBLIC_HISTORICAL_MIRROR",
        "contract_identity_evidence": "Frozen source provenance; not independent exchange capture",
        "first_open": result[0].start,
        "end_exclusive": result[-1].end,
        "bars": len(result),
    }


def validate_primary(bars):
    for bar in bars:
        exact_timestamp(bar.start)
        exact_timestamp(bar.end)
    try:
        validate_bars(bars, 15)
    except ValueError as exc:
        raise ContractWait("WAIT_DATA_GRID_OR_CONTINUITY") from exc


def derive_market(m15):
    """Only complete, contiguous UTC groups; incomplete edge groups are recorded."""
    validate_primary(m15)
    market, receipt = {15: list(m15)}, {}
    for tf in (60, 240, 1440):
        seconds = tf * 60
        groups: dict[int, list[Bar]] = {}
        for bar in m15:
            groups.setdefault(bar.start // seconds * seconds, []).append(bar)
        derived, excluded = [], []
        for at, group in sorted(groups.items()):
            if (
                len(group) != tf // 15
                or group[0].start != at
                or group[-1].end != at + seconds
            ):
                excluded.append(
                    {
                        "start": at,
                        "observed_M15_bars": len(group),
                        "expected_M15_bars": tf // 15,
                    }
                )
                continue
            derived.append(
                Bar(
                    at,
                    at + seconds,
                    group[0].open,
                    max(b.high for b in group),
                    min(b.low for b in group),
                    group[-1].close,
                )
            )
        if derived:
            validate_bars(derived, tf)
        market[tf] = derived
        receipt[str(tf)] = {
            "bars": len(derived),
            "first_open": derived[0].start if derived else None,
            "end_exclusive": derived[-1].end if derived else None,
            "excluded_incomplete_groups": excluded,
            "content_sha256": identity(
                "derived_bars", tf, [bar_record(b) for b in derived]
            ),
        }
    return market, receipt


class HistoricalFrame(Frame):
    """Reuse only pinned raw/BOS/CONF primitives; override v3 lifetime/evidence."""

    def __init__(self, symbol, tf, bars):
        super().__init__(symbol, tf, bars)
        self.retired_ranges = {}
        self.range_reactions = {}

    def step(self, bar):
        old_range = deepcopy(self.range)
        locked = bool(old_range and self.range_mid_reacted)
        old_context = self.context
        eligible_before = tuple(self.active_zones)
        super().step(bar)
        # Native eligibility/consumption comes from the inherited known-at OPEN test.
        for key in eligible_before:
            zone = self.zones[key]
            if zone.get("consumed_at") == bar.end:
                evidence = first_test(
                    {**zone, "known_at": zone["born_at"], "consumed_at": None},
                    bar_record(bar),
                    eligibility_at=bar.start,
                )
                zone["first_touch_time_bounds"] = evidence["first_touch_time_bounds"]
                zone["first_touch_observed_at"] = evidence["first_touch_observed_at"]
        if old_range:
            context_changed = (
                not self.context
                or not old_context
                or self.context["id"] != old_context["id"]
            )
            boundary_close = not old_range["low"] < bar.close < old_range["high"]
            if context_changed or boundary_close:
                self.retired_ranges[old_range["id"]] = bar.end
                if self.range and self.range["id"] == old_range["id"]:
                    self.range, self.range_mid_reacted = None, False
            elif locked:
                # Once EQ-confirmed, a later correction cannot replace this live range.
                self.range, self.range_mid_reacted = old_range, True
        if self.range:
            if (
                self.range["id"] in self.retired_ranges
                or not self.range["low"] < bar.close < self.range["high"]
            ):
                self.retired_ranges[self.range["id"]] = bar.end
                self.range, self.range_mid_reacted = None, False
            elif self.range_mid_reacted:
                self.range_reactions.setdefault(self.range["id"], bar.end)

    def range_record(self):
        if not self.range:
            return None
        return {
            **self.range,
            "eq_reacted_at": self.range_reactions.get(self.range["id"]),
            "invalidated_at": self.retired_ranges.get(self.range["id"]),
        }

    def state(self, cutoff):
        if not self.cursor:
            return {"state": "UNCERTAIN", "direction": None, "known_at": cutoff}
        visible = [c for c in self.confirmations if c["known_at"] <= cutoff]
        if visible:
            latest_at = visible[-1]["known_at"]
            if len({c["direction"] for c in visible if c["known_at"] == latest_at}) > 1:
                return {"state": "UNCERTAIN", "direction": None, "known_at": latest_at}

        def leg(context):
            if context is None:
                return None
            return {
                "id": context["id"],
                "direction": context["direction"],
                "origin": context["protected_price"],
                "endpoint": context["high"]
                if context["direction"] == "LONG"
                else context["low"],
                "known_at": context["known_at"],
                "end_swing_at": context["end_swing_at"],
            }

        previous = next(
            (
                c
                for c in reversed(visible)
                if self.context and c["known_at"] < self.context["known_at"]
            ),
            None,
        )
        latest = self.bars[self.cursor - 1]
        return frame_state(
            current=leg(self.context),
            previous=leg(previous),
            range_event=self.range_record(),
            latest_close=latest.close,
            latest_close_known_at=latest.end,
            decision_at=cutoff,
        )


def visible_zones(frame, direction):
    return frame.candidates_zones(direction)


def inventories(frames, direction, entry, stop, context):
    targets, liquidity = [], []
    for tf in (60, 240, 1440):
        frame = frames[tf]
        for pool in sorted(frame.pools.values(), key=lambda p: p["id"]):
            value, side = Decimal(pool["payload"]["price"]), pool["payload"]["side"]
            forward = value > entry if direction == "LONG" else value < entry
            profit_side = side == ("HIGH" if direction == "LONG" else "LOW")
            internal = context["low"] < value < context["high"]
            beyond_stop = value < stop if direction == "LONG" else value > stop
            adverse = not forward and not profit_side and internal and beyond_stop
            liquidity.append(
                {
                    "id": pool["id"],
                    "tf": tf,
                    "known_at": pool["known_at"],
                    "price": value,
                    "side": side,
                    "scope": "INTERNAL" if internal else "EXTERNAL",
                    "adverse": adverse,
                }
            )
            # Rounding may move the executable entry past a raw-entry comparison.
            # Keep every profit-side candidate; the frozen planner selects relative
            # to the rounded entry and rejects a colliding nearest barrier.
            if profit_side:
                targets.append(
                    {
                        "id": pool["id"],
                        "tf": tf,
                        "kind": "STRUCTURAL_LIQUIDITY",
                        "known_at": pool["known_at"],
                        "price": value,
                    }
                )
        opposite = "SHORT" if direction == "LONG" else "LONG"
        for zone in visible_zones(frame, opposite):
            eligible_at = max(
                zone["born_at"], frame.confirmed_bos[zone["origin_bos_id"]]
            )
            targets.append(
                {
                    "id": zone["id"],
                    "tf": tf,
                    "kind": zone["kind"],
                    "known_at": eligible_at,
                    "price": zone["low"] if direction == "LONG" else zone["high"],
                    "zone_low": zone["low"],
                    "zone_high": zone["high"],
                }
            )
    return targets, liquidity


class HistoricalAdapter:
    """Pre-entry state/setup discovery. No exit/outcome module imported or called."""

    def __init__(
        self, symbol, market, epochs, *, evaluation_start=START, evaluation_end=END
    ):
        if symbol not in ("BTCUSDT", "ETHUSDT"):
            raise ContractReject("REJECT_ADAPTER_SYMBOL")
        if any(not market.get(tf) for tf in (15, 60, 240, 1440)):
            raise ContractWait("WAIT_COMPLETE_TF_PREFIX")
        self.symbol, self.market, self.epochs = symbol, market, epochs
        self.start, self.end = (
            exact_timestamp(evaluation_start),
            exact_timestamp(evaluation_end),
        )
        self.frames = {
            tf: HistoricalFrame(symbol, tf, market[tf]) for tf in (15, 60, 240, 1440)
        }
        self.pending, self.broken_obs, self.seen_ranges = {}, set(), set()
        self.registry = {"physical": (), "pois": ()}
        self.counts: Counter[str] = Counter()

    def discover(self, at):
        for tf in (60, 240):
            frame = self.frames[tf]
            if not frame.cursor or frame.bars[frame.cursor - 1].end != at:
                continue
            current = frame.bars[frame.cursor - 1]
            for obj in frame.new_events:
                if (
                    obj["kind"] not in ("SFP", "OB", "STB")
                    or obj["known_at"] < self.start
                ):
                    continue
                branch = obj["kind"]
                if branch == "SFP" and frame.cursor < 15:
                    self.counts["WAIT_ATR14_PREFIX"] += 1
                    continue
                item = raw_pending(obj, frame, self.frames, current, branch)
                if item:
                    if branch == "SFP":
                        item["atr"] = completed_atr14(
                            [bar_record(b) for b in frame.bars[: frame.cursor]],
                            at,
                            tf * 60,
                            current.end,
                        )
                    self.pending[(obj["id"], branch)] = item
                    self.counts["RAW_" + branch] += 1
            for zone in list(frame.zones.values()):
                if (
                    zone["kind"] != "OB"
                    or zone["born_at"] > current.start
                    or zone["id"] in self.broken_obs
                    or not zone["contextual_at_birth"]
                ):
                    continue
                direction = "LONG" if zone["direction"] == "SHORT" else "SHORT"
                if not direction_cross(
                    current,
                    zone["high"] if direction == "LONG" else zone["low"],
                    direction,
                ):
                    continue
                self.broken_obs.add(zone["id"])
                if at < self.start:
                    continue
                i = bisect_right(frame.ends, zone["born_at"]) - 1
                movement = frame.bars[max(0, i) : frame.cursor]
                obj = {
                    "id": identity("breaker", zone["id"], at),
                    "known_at": at,
                    "payload": {
                        "direction": direction,
                        "low": str(min(b.low for b in movement)),
                        "high": str(max(b.high for b in movement)),
                    },
                }
                item = raw_pending(obj, frame, self.frames, current, "BREAKER")
                item["zone"] = {
                    **zone,
                    "id": obj["id"],
                    "direction": direction,
                    "born_at": at,
                    "consumed_at": None,
                    "low": Decimal(zone["raw"]["payload"]["body_low"]),
                    "high": Decimal(zone["raw"]["payload"]["body_high"]),
                }
                self.pending[(obj["id"], "BREAKER")] = item
                self.counts["RAW_BREAKER"] += 1
            r = frame.range_record()
            if (
                r
                and r["known_at"] <= current.start
                and r["eq_reacted_at"] is not None
                and at >= self.start
            ):
                for direction in ("LONG", "SHORT"):
                    raid = (
                        current.low < r["low"]
                        if direction == "LONG"
                        else current.high > r["high"]
                    )
                    key = (r["id"], direction)
                    if (
                        raid
                        and r["low"] < current.close < r["high"]
                        and key not in self.seen_ranges
                    ):
                        self.seen_ranges.add(key)
                        obj = {
                            "id": identity("range_deviation", r["id"], at, direction),
                            "known_at": at,
                            "payload": {
                                "direction": direction,
                                "low": str(current.low),
                                "high": str(current.high),
                            },
                        }
                        item = raw_pending(obj, frame, self.frames, current, "RANGE")
                        boundary = r["low"] if direction == "LONG" else r["high"]
                        item.update(
                            range=deepcopy(r),
                            reaction_at=None,
                            zone={
                                "id": obj["id"],
                                "low": boundary,
                                "high": boundary,
                                "born_at": at,
                                "consumed_at": None,
                            },
                        )
                        self.pending[(obj["id"], "RANGE")] = item
                        self.counts["RAW_RANGE"] += 1

    def plan_pending(self, item, at):
        frames, direction = self.frames, item["direction"]
        refinement = frames[15]
        confirms = [
            c
            for c in refinement.confirmations
            if c["known_at"] > item["reaction_at"]
            and c["direction"] == direction
            and refinement.bos_by_id[c["bos_id"]]["known_at"] >= item["reaction_at"]
        ]
        if not confirms:
            raise ContractWait("WAIT_REFINEMENT_BOS_CONF")
        conf = max(confirms, key=lambda c: (c["known_at"], c["id"]))
        if any(
            b["direction"] != direction
            and item["reaction_at"] < b["known_at"] <= conf["known_at"]
            for b in refinement.bos
        ):
            raise ContractReject("REJECT_NON_SMOOTH_STRUCTURAL_APPROACH")
        poi = item["zone"]
        if item["branch"] in ("SFP", "OB"):
            bos_at = refinement.bos_by_id[conf["bos_id"]]["known_at"]
            zones = [
                z
                for z in visible_zones(refinement, direction)
                if z["born_at"] >= bos_at
                and z["origin_bos_id"] == conf["bos_id"]
                and z["kind"] in ("OB", "FVG")
                and poi["low"] <= z["low"] <= z["high"] <= poi["high"]
            ]
            if not zones:
                raise ContractWait("WAIT_ORIGIN_BOUND_REFINEMENT_POI")
            poi = min(
                zones,
                key=lambda z: (0 if z["kind"] == "OB" else 1, -z["born_at"], z["id"]),
            )
        native = frames[item["setup_tf"]].zones.get(poi["id"])
        if (
            poi.get("consumed_at") is not None
            or (native and native.get("consumed_at") is not None)
            or poi["id"] in self.registry["pois"]
        ):
            raise ContractReject("REJECT_CONSUMED_OR_RESERVED_POI")
        parent_pois = []
        for tf in (240, 1440):
            for z in visible_zones(frames[tf], direction):
                parent_pois.append(
                    {
                        "id": z["id"],
                        "tf": "H4" if tf == 240 else "D1",
                        "direction": direction,
                        "low": z["low"],
                        "high": z["high"],
                        "confirmed": True,
                        "consumed_at": None,
                        "known_at": max(
                            z["born_at"], frames[tf].confirmed_bos[z["origin_bos_id"]]
                        ),
                    }
                )
        states = {
            name: frames[tf].state(at)
            for name, tf in (("H1", 60), ("H4", 240), ("D1", 1440))
        }
        context = admit_context(
            states=states,
            direction=direction,
            formation_bar=bar_record(item["formation_bar"]),
            m15_confirmation={
                "id": conf["id"],
                "direction": conf["direction"],
                "known_at": conf["known_at"],
            },
            parent_pois=parent_pois,
            decision_at=at,
            h4_range=frames[240].range_record(),
        )
        raw = raw_family_prices(
            family=item["branch"],
            direction=direction,
            zone_low=poi["low"],
            zone_high=poi["high"],
            stop_anchor=item["extreme"],
            atr14=item["atr"] if item["branch"] == "SFP" else None,
        )
        raw["known_at"] = at
        h1 = frames[60].context
        if h1 is None:
            raise ContractWait("WAIT_COMPLETE_H1_CONTEXT")
        targets, _ = inventories(
            frames, direction, raw["raw_entry"], raw["raw_stop_boundary"], h1
        )
        if item["branch"] == "RANGE":
            if item["range"]["id"] in frames[item["setup_tf"]].retired_ranges:
                raise ContractReject("REJECT_RETIRED_SOURCE_RANGE")
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
        plan = executable_plan(
            raw=raw,
            targets=targets,
            zone_low=poi["low"],
            zone_high=poi["high"],
            epochs=self.epochs,
            symbol=self.symbol,
            contract_type=CONTRACT_TYPE,
            decision_at=at,
        )
        _, pools = inventories(frames, direction, plan["entry"], plan["stop"], h1)
        if any(p["adverse"] for p in pools):
            raise ContractReject("REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP")
        physical = identity("physical", self.symbol, item["formation_at"], direction)
        setup = identity("setup", physical, item["formation_id"], conf["id"], poi["id"])
        return serial(
            {
                **plan,
                "version": VERSION,
                "symbol": self.symbol,
                "contract_type": CONTRACT_TYPE,
                "branch": item["branch"],
                "setup_tf_seconds": item["setup_tf"] * 60,
                "setup_tf": item["setup_tf"],
                "direction": direction,
                "decision_at": at,
                "known_at": at,
                "expires_at": at + 3600,
                "status": "PENDING",
                "physical_idea_id": physical,
                "entry_poi_id": poi["id"],
                "setup_id": setup,
                "case_id": identity("pre_entry_order", setup, at),
                "formation_id": item["formation_id"],
                "formation_at": item["formation_at"],
                "confirmation_id": conf["id"],
                "confirmation_known_at": conf["known_at"],
                "stop_anchor": item["extreme"],
                "raw_stop_boundary": raw["raw_stop_boundary"],
                "context": context,
                "states": states,
                "selected_impulse": h1,
                "source_geometry_references": [item["formation_id"], poi["id"]],
                "all_FTA_inventory": targets,
                "FTA_inventory_digest": identity("FTA_inventory", targets),
                "liquidity_inventory": pools,
                "liquidity_inventory_digest": identity("liquidity", pools),
                "PD_at_entry": "DISCOUNT"
                if Decimal(plan["entry"]) < h1["EQ"]
                else "PREMIUM"
                if Decimal(plan["entry"]) > h1["EQ"]
                else "EQ",
                "OTE_at_entry": h1["OTE"][0] <= Decimal(plan["entry"]) <= h1["OTE"][1],
                "source_validated": False,
                "trade_entry_allowed": False,
            }
        )

    def run(self, cutoff=None):
        if cutoff is None:
            cutoff = self.end
        exact_timestamp(cutoff)
        orders, diagnostics, last_decision = [], [], None
        for decision in self.market[60]:
            at = decision.end
            if at > cutoff or at > self.end:
                break
            last_decision = at
            for tf in (1440, 240, 60, 15):
                self.frames[tf].advance(at)
            self.discover(at)
            proposals = []
            for key, item in list(self.pending.items()):
                reason = None
                if at > item["expiry"]:
                    reason = "EXPIRED_PENDING"
                else:
                    frame = self.frames[item["setup_tf"]]
                    b = frame.bars[frame.cursor - 1]
                    if item["next_open_required"]:
                        if b.start < item["formation_at"]:
                            continue
                        item["next_open_required"] = False
                        item["next_open_evidence"] = {
                            "actual_at": b.start,
                            "known_at": b.end,
                            "open": b.open,
                        }
                        if not (
                            b.open > item["level"]
                            if item["direction"] == "LONG"
                            else b.open < item["level"]
                        ):
                            reason = "REJECT_SFP_NEXT_OPEN"
                    if reason is None and item["reaction_at"] is None:
                        if b.start < item["formation_at"]:
                            continue
                        touched = intersects(
                            b, item["zone"]["low"], item["zone"]["high"]
                        )
                        reclaimed = (
                            item["branch"] != "RANGE"
                            or item["range"]["low"] < b.close < item["range"]["high"]
                        )
                        if not touched or not reclaimed:
                            continue
                        item["reaction_at"] = b.end
                    if reason is None:
                        try:
                            proposal = self.plan_pending(item, at)
                            proposals.append((key, proposal))
                            continue
                        except (ContractWait, ContractReject) as exc:
                            reason = exc.reason
                self.counts[reason] += 1
                if reason.startswith("WAIT"):
                    item["last_wait"] = reason
                else:
                    diagnostics.append(
                        {
                            "formation_id": item["formation_id"],
                            "branch": item["branch"],
                            "decision_at": at,
                            "reason": reason,
                        }
                    )
                    del self.pending[key]
            groups: dict[str, list[tuple[tuple, dict]]] = {}
            for key, proposal in proposals:
                groups.setdefault(proposal["physical_idea_id"], []).append(
                    (key, proposal)
                )
            for _, siblings in sorted(groups.items()):
                ordered = sorted(
                    siblings,
                    key=lambda x: (
                        PRIORITY[x[1]["branch"]],
                        -x[1]["setup_tf"],
                        x[1]["setup_id"],
                    ),
                )
                chosen = ordered[0][1]
                try:
                    self.registry = reserve_idea(
                        self.registry,
                        chosen["physical_idea_id"],
                        chosen["entry_poi_id"],
                    )
                    chosen["rejected_sibling_branches"] = [
                        {
                            "branch": p["branch"],
                            "formation_id": p["formation_id"],
                            "setup_id": p["setup_id"],
                        }
                        for _, p in ordered[1:]
                    ]
                    orders.append(chosen)
                    self.counts["PRE_ENTRY_ORDER_RESERVED"] += 1
                except ContractReject as exc:
                    self.counts[exc.reason] += len(ordered)
                for key, _ in ordered:
                    del self.pending[key]
        return orders, {
            "symbol": self.symbol,
            "known_through": last_decision,
            "counts": dict(sorted(self.counts.items())),
            "pending": serial(
                [
                    {**p, "formation_bar": bar_record(p["formation_bar"])}
                    for p in self.pending.values()
                ]
            ),
            "diagnostics": diagnostics,
            "frame_snapshot": {
                str(tf): {
                    "state": f.state(min(cutoff, self.end)),
                    "context": serial(f.context),
                    "zones": serial(f.zones),
                    "pools": serial(f.pools),
                    "range": serial(f.range_record()),
                    "retired_ranges": f.retired_ranges,
                }
                for tf, f in self.frames.items()
            },
            "historical_position_evaluations": 0,
            "trade_entry_allowed": False,
        }
