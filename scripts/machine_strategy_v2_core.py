"""Pre-outcome Machine v2: causal selectors; original SOURCE policies remain untouched."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from decimal import Decimal

from original_strategy_executable_profile_v1 import digest
from original_v1_1_financial_data import START, TFS, validate_bars
from original_v1_1_objective_geometry_v2 import GeometryIndex

D = Decimal
VERSION = "MACHINE_STRATEGY_v2"
BRANCHES = ("SFP", "OB", "BREAKER", "STB", "RANGE")
PRIORITY = {name: i for i, name in enumerate(("BREAKER", "STB", "SFP", "OB", "RANGE"))}
PARAMETERS = {
    "swing_bars": 3,
    "ATR": 14,
    "EQ": "0.5",
    "OTE": ["0.705", "0.79"],
    "pending_H1_cycles": 16,
    "order_H1_cycles": 1,
    "theoretical_outside_epsilon_relative": "0.00000001",
}


def ident(kind, *values):
    return digest([VERSION, kind, *values])


def price(obj):
    return D(obj["payload"]["price"])


def direction_cross(bar, level, direction):
    return bar.close > level if direction == "LONG" else bar.close < level


def intersects(bar, low, high):
    return bar.low <= high and bar.high >= low


def epsilon(value):
    return max(abs(value), D(1)) * D(PARAMETERS["theoretical_outside_epsilon_relative"])


class Frame:
    """Forward-only completed-prefix structure and first-eligible-test inventory."""

    def __init__(self, symbol, tf, bars):
        validate_bars(bars, tf)
        self.symbol, self.tf, self.bars = symbol, tf, bars
        self.ends = [b.end for b in bars]
        self.index = GeometryIndex(symbol, tf, bars)
        self.cursor = 0
        self.latest = {"HIGH": None, "LOW": None}
        self.context = None
        self.pending = None
        self.bos = []
        self.bos_by_id = {}
        self.bos_times = []
        self.confirm_times = []
        self.confirmed_bos = {}
        self.active_zones = set()
        self.confirmations = []
        self.zones = {}
        self.pools = {}
        self.range = None
        self.range_mid_reacted = False
        self.new_events = []
        self.last_at = -1

    def advance(self, cutoff):
        if cutoff < self.last_at:
            raise ValueError("Noncausal backward frame")
        self.new_events = []
        while self.cursor < len(self.bars) and self.bars[self.cursor].end <= cutoff:
            self.step(self.bars[self.cursor])
            self.cursor += 1
        self.last_at = cutoff

    def step(self, bar):
        previous_context = self.context
        # Consumption uses context known at OPEN, never the bar's future close.
        for zone_id in list(self.active_zones):
            zone = self.zones[zone_id]
            if zone["consumed_at"] is not None or zone["born_at"] > bar.start:
                continue
            if (
                previous_context
                and previous_context["known_at"] <= bar.start
                and zone["direction"] == previous_context["direction"]
                and self.confirmed_bos.get(zone["origin_bos_id"], bar.end + 1)
                <= bar.start
                and intersects(bar, zone["low"], zone["high"])
            ):
                zone["consumed_at"] = bar.end
                self.active_zones.discard(zone_id)
                zone["first_eligible_touch"] = ident(
                    "eligible_touch", zone["id"], bar.start
                )
        if self.context:
            long = self.context["direction"] == "LONG"
            if (
                bar.close < self.context["protected_price"]
                if long
                else bar.close > self.context["protected_price"]
            ):
                self.context = None
                self.range = None
        if self.pending and not direction_cross(
            bar, self.pending["origin_price"], self.pending["direction"]
        ):
            self.pending = None
        # Levels and origin swings must have been known by this bar OPEN.
        for direction, side, opposite in (
            ("LONG", "HIGH", "LOW"),
            ("SHORT", "LOW", "HIGH"),
        ):
            reference, origin = self.latest[side], self.latest[opposite]
            if (
                not reference
                or not origin
                or max(reference["known_at"], origin["known_at"]) > bar.start
            ):
                continue
            if (
                self.cursor
                and direction_cross(bar, price(reference), direction)
                and not direction_cross(
                    self.bars[self.cursor - 1], price(reference), direction
                )
            ):
                bos = {
                    "id": ident(
                        "BOS",
                        self.symbol,
                        self.tf,
                        reference["id"],
                        origin["id"],
                        bar.end,
                    ),
                    "known_at": bar.end,
                    "bar_start": bar.start,
                    "direction": direction,
                    "reference_id": reference["id"],
                    "reference_price": price(reference),
                    "origin": origin,
                    "origin_price": price(origin),
                }
                if (direction == "LONG" and bos["origin_price"] < bar.close) or (
                    direction == "SHORT" and bos["origin_price"] > bar.close
                ):
                    self.pending = bos
                    self.bos.append(bos)
                    self.bos_by_id[bos["id"]] = bos
                    self.bos_times.append(bos["known_at"])
        objects = [self.index.by_id[k] for k in self.index.events.get(bar.end, [])]
        swings = [o for o in objects if o["kind"] == "swing"]
        for swing in sorted(swings, key=lambda o: o["id"]):
            side = swing["payload"]["side"]
            self.latest[side] = swing
            if self.pending:
                p = self.pending
                expected = "HIGH" if p["direction"] == "LONG" else "LOW"
                endpoint_time = swing["payload"]["center_start"]
                beyond = (
                    price(swing) > p["reference_price"]
                    if p["direction"] == "LONG"
                    else price(swing) < p["reference_price"]
                )
                if side == expected and endpoint_time >= p["bar_start"] and beyond:
                    a, b = p["origin_price"], price(swing)
                    low, high = min(a, b), max(a, b)
                    if low < high:
                        conf_id = ident("CONF", p["id"], swing["id"])
                        context = {
                            "id": ident("context", p["id"], swing["id"]),
                            "bos_id": p["id"],
                            "confirmation_id": conf_id,
                            "known_at": bar.end,
                            "direction": p["direction"],
                            "protected_id": p["origin"]["id"],
                            "protected_price": a,
                            "start_swing_id": p["origin"]["id"],
                            "end_swing_id": swing["id"],
                            "end_swing_at": endpoint_time,
                            "low": low,
                            "high": high,
                            "EQ": (low + high) / 2,
                            "OTE": sorted(
                                [b - (b - a) * D(r) for r in PARAMETERS["OTE"]]
                            ),
                        }
                        self.context = context
                        self.confirmations.append(context)
                        self.confirm_times.append(bar.end)
                        self.confirmed_bos[p["id"]] = bar.end
                        self.pending = None
                        self.range = None
                        self.range_mid_reacted = False
            if self.context:
                c = self.context
                correction_side = "LOW" if c["direction"] == "LONG" else "HIGH"
                if (
                    side == correction_side
                    and swing["payload"]["center_start"] > c["end_swing_at"]
                    and c["low"] < price(swing) < c["high"]
                ):
                    low, high = (
                        (price(swing), c["high"])
                        if correction_side == "LOW"
                        else (c["low"], price(swing))
                    )
                    self.range = {
                        "id": ident("range", c["id"], swing["id"]),
                        "known_at": bar.end,
                        "low": low,
                        "high": high,
                        "EQ": (low + high) / 2,
                        "context_id": c["id"],
                    }
                    self.range_mid_reacted = False
        for obj in objects:
            p = obj["payload"]
            if obj["kind"] == "liquidity_pool":
                self.pools[obj["id"]] = obj
            elif obj["kind"] == "sweep":
                self.pools.pop(p["pool_id"], None)
            elif obj["kind"] in ("OB", "STB", "FVG"):
                direction = p["direction"]
                origin = (
                    self.pending
                    if self.pending and self.pending["direction"] == direction
                    else self.context
                )
                origin_id = (
                    origin.get("bos_id", origin.get("id"))
                    if origin and origin["direction"] == direction
                    else None
                )
                self.zones[obj["id"]] = {
                    "id": obj["id"],
                    "kind": obj["kind"],
                    "tf": self.tf,
                    "low": D(p["low"]),
                    "high": D(p["high"]),
                    "direction": direction,
                    "born_at": obj["known_at"],
                    "origin_bos_id": origin_id,
                    "consumed_at": None,
                    "first_eligible_touch": None,
                    "contextual_at_birth": origin_id is not None,
                    "raw": obj,
                }
                if origin_id is not None:
                    self.active_zones.add(obj["id"])
        if self.range and self.range["known_at"] <= bar.start:
            r = self.range
            if intersects(bar, r["EQ"], r["EQ"]) and r["low"] < bar.close < r["high"]:
                self.range_mid_reacted = True
        self.new_events.extend(objects)

    def visible_context(self):
        return self.context

    def candidates_zones(self, direction, *, after=0):
        return [
            z
            for z in (self.zones[k] for k in sorted(self.active_zones))
            if z["direction"] == direction
            and z["born_at"] >= after
            and z["consumed_at"] is None
            and z["contextual_at_birth"]
            and z["origin_bos_id"] in self.confirmed_bos
        ]


def serial(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def liquidity_inventory(frames, context, direction, entry, stop):
    rows = []
    for tf in (60, 240, 1440):
        for pool in frames[tf].pools.values():
            p = price(pool)
            side = pool["payload"]["side"]
            structural = pool["payload"].get("swing_id") in (
                context["protected_id"],
                context["end_swing_id"],
            )
            scope = "INTERNAL" if context["low"] < p < context["high"] else "EXTERNAL"
            forward = p > entry if direction == "LONG" else p < entry
            target_side = side == ("HIGH" if direction == "LONG" else "LOW")
            beyond_stop = p < stop if direction == "LONG" else p > stop
            role = (
                "TARGET_FUEL"
                if forward and target_side
                else (
                    "ADVERSE"
                    if not forward
                    and not target_side
                    and beyond_stop
                    and scope == "INTERNAL"
                    else "NEUTRAL"
                )
            )
            rows.append(
                {
                    "id": pool["id"],
                    "tf": tf,
                    "price": p,
                    "known_at": pool["known_at"],
                    "structural": structural,
                    "scope": scope,
                    "role": role,
                }
            )
    return sorted(rows, key=lambda r: (r["tf"], r["known_at"], r["id"]))


def plan_case(symbol, pending, frames, at, used_pois):
    """Unique causal selector; absent observations yield a named WAIT, never discretionary UNKNOWN."""
    h1, h4, d1 = (frames[tf].context for tf in (60, 240, 1440))
    if not h1 or not h4 or not d1:
        return None, "WAIT_NO_CONFIRMED_CONTEXT"
    if any(c["known_at"] > at for c in (h1, h4, d1)):
        raise ValueError("Future machine context")
    direction = pending["direction"]
    if direction != h1["direction"]:
        return None, "WAIT_H1_DIRECTION_CONFIRMATION"
    original = pending["zone"]
    context_relation = "TREND" if h4["direction"] == direction else "COUNTER_AT_HTF_POI"
    if context_relation != "TREND":
        higher = [
            z
            for tf in (240, 1440)
            for z in frames[tf].candidates_zones(direction)
            if intersects(pending["formation_bar"], z["low"], z["high"])
        ]
        if not higher:
            return None, "WAIT_COUNTERTREND_ORIGIN_POI"
    refinement = frames[15]
    confirms = [
        c
        for c in refinement.confirmations[
            bisect_right(refinement.confirm_times, pending["reaction_at"]) :
        ]
        if c["known_at"] > pending["reaction_at"]
        and c["direction"] == direction
        and refinement.bos_by_id[c["bos_id"]]["known_at"] >= pending["reaction_at"]
    ]
    if not confirms:
        return None, "WAIT_REFINEMENT_BOS_CONF"
    conf = max(confirms, key=lambda c: (c["known_at"], c["id"]))
    if any(
        b["direction"] != direction
        and pending["reaction_at"] < b["known_at"] <= conf["known_at"]
        for b in refinement.bos[
            bisect_right(refinement.bos_times, pending["reaction_at"]) :
        ]
    ):
        return None, "REJECT_NON_SMOOTH_STRUCTURAL_APPROACH"
    branch = pending["branch"]
    if branch in ("SFP", "OB"):
        bos_at = refinement.bos_by_id[conf["bos_id"]]["known_at"]
        zones = [
            z
            for z in refinement.candidates_zones(direction, after=bos_at)
            if z["origin_bos_id"] == conf["bos_id"] and z["kind"] in ("OB", "FVG")
        ]
        if not zones:
            return None, "WAIT_NEW_REFINEMENT_POI"
        # Source/machine refinement must remain inside the original raid/origin interval.
        zones = [
            z
            for z in zones
            if original["low"] <= z["low"] <= z["high"] <= original["high"]
        ]
        if not zones:
            return None, "REJECT_REFINEMENT_OUTSIDE_ORIGIN"
        poi = min(
            zones, key=lambda z: (0 if z["kind"] == "OB" else 1, -z["born_at"], z["id"])
        )
    else:
        poi = original
    native = getattr(frames[pending["setup_tf"]], "zones", {}).get(poi["id"])
    if poi["born_at"] > at or conf["known_at"] > at:
        raise ValueError("Future POI/confirmation")
    if (
        poi["id"] in used_pois
        or poi.get("consumed_at") is not None
        or (native and native["consumed_at"] is not None)
    ):
        return None, "REJECT_CONSUMED_OR_ALREADY_ORDERED_POI"
    entry = (
        (poi["low"] + poi["high"]) / 2
        if branch == "STB"
        else (poi["high"] if direction == "LONG" else poi["low"])
    )
    if branch == "RANGE":
        entry = (
            pending["range"]["low"] if direction == "LONG" else pending["range"]["high"]
        )
    extreme = pending["extreme"]
    stop = (
        extreme - pending["atr"]
        if branch == "SFP" and direction == "LONG"
        else (
            extreme + pending["atr"]
            if branch == "SFP"
            else extreme - epsilon(extreme)
            if direction == "LONG"
            else extreme + epsilon(extreme)
        )
    )
    if not (D(0) < stop < entry if direction == "LONG" else stop > entry > D(0)):
        return None, "REJECT_INVALID_FIXED_STOP"
    pools = liquidity_inventory(frames, h1, direction, entry, stop)
    if any(p["role"] == "ADVERSE" for p in pools):
        return None, "REJECT_STOP_BEFORE_INTERNAL_ADVERSE_LIQUIDITY"
    targets = [
        {
            "price": p["price"],
            "id": p["id"],
            "kind": "STRUCTURAL_LIQUIDITY",
            "known_at": p["known_at"],
        }
        for p in pools
        if p["role"] == "TARGET_FUEL"
    ]
    for tf in (60, 240, 1440):
        for z in frames[tf].candidates_zones(
            "SHORT" if direction == "LONG" else "LONG"
        ):
            target = z["low"] if direction == "LONG" else z["high"]
            if z["low"] <= entry <= z["high"]:
                return None, "REJECT_ENTRY_IN_OPPOSING_CONTEXTUAL_POI"
            if target > entry if direction == "LONG" else target < entry:
                targets.append(
                    {
                        "price": target,
                        "id": z["id"],
                        "kind": z["kind"],
                        "known_at": z["born_at"],
                    }
                )
    if branch == "RANGE":
        r = pending["range"]
        boundary = (
            r["high"] - epsilon(r["high"])
            if direction == "LONG"
            else r["low"] + epsilon(r["low"])
        )
        if boundary > entry if direction == "LONG" else boundary < entry:
            targets.append(
                {
                    "price": boundary,
                    "id": r["id"],
                    "kind": "RANGE_BOUNDARY_80_20_SAME_ZONE",
                    "known_at": r["known_at"],
                }
            )
    if not targets:
        return None, "WAIT_NO_CAUSAL_FTA"
    fta = min(targets, key=lambda t: (abs(t["price"] - entry), t["id"]))
    if any(t["known_at"] > at for t in targets):
        raise ValueError("Future FTA")
    physical = ident("physical", symbol, pending["formation_at"], direction)
    setup = ident("setup", physical, pending["formation_id"], conf["id"], poi["id"])
    case = {
        "version": VERSION,
        "symbol": symbol,
        "branch": branch,
        "setup_tf": pending["setup_tf"],
        "decision_tf": 60,
        "entry_tf": 15,
        "direction": direction,
        "decision_at": at,
        "known_at": at,
        "physical_idea_id": physical,
        "setup_id": setup,
        "case_id": ident("case", setup, at),
        "formation_id": pending["formation_id"],
        "formation_at": pending["formation_at"],
        "confirmation_id": conf["id"],
        "confirmation_known_at": conf["known_at"],
        "context_id": h1["id"],
        "H4_context_id": h4["id"],
        "D1_context_id": d1["id"],
        "context_relation": context_relation,
        "entry_poi_id": poi["id"],
        "poi_born_at": poi["born_at"],
        "first_eligible_touch": None,
        "consumed_at": None,
        "source_geometry_references": [pending["formation_id"], poi["id"]],
        "source_validated": False,
        "rule_class": "MACHINE_RULE_PRE_BACKTEST",
        "machine_validated": True,
        "theoretical_entry": entry,
        "fixed_initial_stop": stop,
        "stop_anchor": extreme,
        "theoretical_target": fta["price"],
        "FTA_id": fta["id"],
        "FTA_kind": fta["kind"],
        "FTA_known_at": fta["known_at"],
        "FTA_inventory_digest": ident("FTA_inventory", serial(targets)),
        "liquidity_inventory": pools,
        "liquidity_inventory_digest": ident("liquidity", serial(pools)),
        "selected_impulse": h1,
        "PD_at_entry": "DISCOUNT"
        if entry < h1["EQ"]
        else "PREMIUM"
        if entry > h1["EQ"]
        else "EQ",
        "OTE_at_entry": h1["OTE"][0] <= entry <= h1["OTE"][1],
        "unrounded_theoretical_prices": True,
        "historical_exchange_execution_verified": False,
        "order_expires_at": at + 3600,
        "fixed_stop": True,
        "BE_enabled": False,
        "exit_model": "RANGE_80_20_SAME_ZONE"
        if branch == "RANGE"
        else "FULL_NEAREST_CONTEXTUAL_FTA",
        "trade_entry_allowed": False,
    }
    return serial(case), "ALLOWED_MACHINE_SETUP"


def raw_pending(obj, frame, frames, bar, branch):
    p = obj["payload"]
    direction = p["direction"]
    extreme = D(p["low"] if direction == "LONG" else p["high"])
    low, high = D(p["low"]), D(p["high"])
    if branch == "STB":
        low, high = D(p["body_low"]), D(p["body_high"])
    zone = frame.zones.get(
        obj["id"],
        {
            "id": obj["id"],
            "low": low,
            "high": high,
            "direction": direction,
            "born_at": obj["known_at"],
            "consumed_at": None,
        },
    )
    if branch == "STB":
        zone = {**zone, "low": low, "high": high}
    atr = D(0)
    if branch == "SFP":
        i = bisect_right(frame.ends, bar.end) - 1
        if i < 14:
            return None
        atr = (
            sum(
                (
                    max(
                        b.high - b.low,
                        abs(b.high - frame.bars[k - 1].close),
                        abs(b.low - frame.bars[k - 1].close),
                    )
                    for k, b in enumerate(frame.bars[i - 13 : i + 1], start=i - 13)
                ),
                D(0),
            )
            / 14
        )
    return {
        "branch": branch,
        "direction": direction,
        "setup_tf": frame.tf,
        "formation_id": obj["id"],
        "formation_at": obj["known_at"],
        "formation_bar": bar,
        "zone": zone,
        "reaction_at": obj["known_at"] if branch in ("SFP", "STB", "BREAKER") else None,
        "extreme": extreme,
        "atr": atr,
        "expiry": obj["known_at"] + 16 * 3600,
        "next_open_required": branch == "SFP",
        "level": D(p.get("price", "0")),
    }


def build_cohort(symbol, market, *, mode="BACKTEST", progress=None):
    if mode not in ("BACKTEST", "SHADOW"):
        raise ValueError("Offline machine modes only")
    frames = {tf: Frame(symbol, tf, market[tf]) for tf in TFS}
    pending, records, audit = {}, [], []
    emitted_physical, used_pois, broken_obs, seen_ranges = set(), set(), set(), set()
    counts = Counter()
    for i, decision in enumerate(market[60]):
        at = decision.end
        for tf in (1440, 240, 60, 15):
            frames[tf].advance(at)
        for tf in (60, 240):
            frame = frames[tf]
            if not frame.cursor or frame.bars[frame.cursor - 1].end != at:
                continue
            current = frame.bars[frame.cursor - 1]
            for obj in frame.new_events:
                branch = {"SFP": "SFP", "OB": "OB", "STB": "STB"}.get(obj["kind"])
                if branch and obj["known_at"] >= START:
                    item = raw_pending(obj, frame, frames, current, branch)
                    if item:
                        pending[(obj["id"], branch)] = item
                        counts["RAW_" + branch] += 1
            # Broken existing machine-contextual OB produces a new Breaker identity.
            for z in list(frame.zones.values()):
                if (
                    z["kind"] != "OB"
                    or z["born_at"] > current.start
                    or z["id"] in broken_obs
                    or not z["contextual_at_birth"]
                ):
                    continue
                direction = "LONG" if z["direction"] == "SHORT" else "SHORT"
                boundary = z["high"] if direction == "LONG" else z["low"]
                if direction_cross(current, boundary, direction):
                    broken_obs.add(z["id"])
                    if at >= START:
                        start_index = bisect_right(frame.ends, z["born_at"]) - 1
                        movement = frame.bars[max(0, start_index) : frame.cursor]
                        obj = {
                            "id": ident("breaker", z["id"], current.end),
                            "known_at": current.end,
                            "payload": {
                                "direction": direction,
                                "low": str(min(b.low for b in movement)),
                                "high": str(max(b.high for b in movement)),
                            },
                        }
                        item = raw_pending(obj, frame, frames, current, "BREAKER")
                        item["zone"] = {
                            **z,
                            "id": obj["id"],
                            "direction": direction,
                            "born_at": current.end,
                            "consumed_at": None,
                            "low": D(z["raw"]["payload"]["body_low"]),
                            "high": D(z["raw"]["payload"]["body_high"]),
                        }
                        pending[(obj["id"], "BREAKER")] = item
                        counts["RAW_BREAKER"] += 1
            r = frame.range
            if (
                r
                and r["known_at"] <= current.start
                and frame.range_mid_reacted
                and at >= START
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
                        and key not in seen_ranges
                    ):
                        seen_ranges.add(key)
                        obj = {
                            "id": ident(
                                "range_deviation", r["id"], current.end, direction
                            ),
                            "known_at": current.end,
                            "payload": {
                                "direction": direction,
                                "low": str(current.low),
                                "high": str(current.high),
                            },
                        }
                        item = raw_pending(obj, frame, frames, current, "RANGE")
                        item["range"] = r.copy()
                        item["reaction_at"] = None
                        boundary = r["low"] if direction == "LONG" else r["high"]
                        item["zone"] = {
                            "id": obj["id"],
                            "low": boundary,
                            "high": boundary,
                            "born_at": current.end,
                            "consumed_at": None,
                        }
                        pending[(obj["id"], "RANGE")] = item
                        counts["RAW_RANGE"] += 1
        proposals = []
        for key, item in list(pending.items()):
            if at > item["expiry"]:
                counts["EXPIRED_PENDING"] += 1
                audit.append(
                    {
                        "formation_id": item["formation_id"],
                        "branch": item["branch"],
                        "decision_at": at,
                        "status": "EXPIRED_PENDING",
                        "last_wait": item.get("last_wait"),
                    }
                )
                del pending[key]
                continue
            frame = frames[item["setup_tf"]]
            b = frame.bars[frame.cursor - 1]
            if item["next_open_required"]:
                if b.start < item["formation_at"]:
                    continue
                item["next_open_required"] = False
                if not (
                    b.open > item["level"]
                    if item["direction"] == "LONG"
                    else b.open < item["level"]
                ):
                    counts["REJECT_SFP_NEXT_OPEN"] += 1
                    del pending[key]
                    continue
            if item["reaction_at"] is None:
                if b.start < item["formation_at"]:
                    continue
                z = item["zone"]
                touched = intersects(b, z["low"], z["high"])
                reclaimed = (
                    True
                    if item["branch"] != "RANGE"
                    else item["range"]["low"] < b.close < item["range"]["high"]
                )
                if touched and reclaimed:
                    item["reaction_at"] = b.end
                else:
                    continue
            case, reason = plan_case(symbol, item, frames, at, used_pois)
            if case:
                proposals.append((key, case))
            elif reason.startswith("WAIT"):
                item["last_wait"] = reason
            elif reason.startswith("REJECT"):
                counts[reason] += 1
                audit.append(
                    {
                        "formation_id": item["formation_id"],
                        "branch": item["branch"],
                        "decision_at": at,
                        "status": reason,
                    }
                )
                del pending[key]
        groups = {}
        for key, case in proposals:
            groups.setdefault(case["physical_idea_id"], []).append((key, case))
        for physical, siblings in sorted(groups.items()):
            ordered = sorted(
                siblings,
                key=lambda x: (
                    PRIORITY[x[1]["branch"]],
                    -x[1]["setup_tf"],
                    x[1]["setup_id"],
                ),
            )
            _chosen_key, chosen = ordered[0]
            if physical in emitted_physical or chosen["entry_poi_id"] in used_pois:
                counts["REJECT_DUPLICATE_PHYSICAL_OR_POI"] += len(ordered)
            else:
                counts["REJECT_SIBLING_BRANCH"] += len(ordered) - 1
                chosen["rejected_sibling_branches"] = [
                    c["branch"] for _, c in ordered[1:]
                ]
                records.append(chosen)
                emitted_physical.add(physical)
                used_pois.add(chosen["entry_poi_id"])
                counts["ALLOWED_" + chosen["branch"]] += 1
            for key, _ in ordered:
                del pending[key]
        if progress and i % 5000 == 0:
            progress(symbol, i, len(records))
    counts["WAIT_PENDING_EOF"] = len(pending)
    records.sort(key=lambda r: (r["decision_at"], r["case_id"]))
    return records, {
        "symbol": symbol,
        "counts": dict(counts),
        "raw_candidates": sum(counts["RAW_" + b] for b in BRANCHES),
        "allowed_setups": len(records),
        "pending_EOF": len(pending),
        "audit": audit,
        "deterministic_definition_UNKNOWN": 0,
        "mode_parity": mode in ("BACKTEST", "SHADOW"),
        "trade_entry_allowed": False,
    }
