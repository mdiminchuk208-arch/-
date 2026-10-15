"""Deterministic Range/Deviation/Reclaim resolver for Source Strategy Rebuild v1."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from original_strategy_executable_profile_v1 import digest
from source_strategy_v1_structure_resolver import first_directional_bos


VERSION = "SOURCE_STRATEGY_REBUILD_v1_RANGE_RESOLVER"
TRADE_ENTRY_ALLOWED = False


def _source_swings(index: Any, start_at: int, end_at: int) -> list[dict[str, Any]]:
    return sorted(
        (
            obj
            for obj in index.by_id.values()
            if obj.get("kind") == "swing"
            and obj.get("source_validated") is True
            and start_at <= obj.get("known_at", -1) <= end_at
            and obj.get("payload", {}).get("side") in ("HIGH", "LOW")
        ),
        key=lambda obj: (obj["known_at"], obj["id"]),
    )


def _has_directional_structure_inside(index: Any, low: Decimal, high: Decimal, start_at: int, end_at: int) -> bool:
    swings = [
        obj
        for obj in _source_swings(index, start_at, end_at)
        if low <= Decimal(str(obj["payload"]["price"])) <= high
    ]
    for pos in range(3, len(swings)):
        window = swings[pos - 3 : pos + 1]
        sides = [obj["payload"]["side"] for obj in window]
        if sides not in (["LOW", "HIGH", "LOW", "HIGH"], ["HIGH", "LOW", "HIGH", "LOW"]):
            continue
        highs = [Decimal(str(obj["payload"]["price"])) for obj in window if obj["payload"]["side"] == "HIGH"]
        lows = [Decimal(str(obj["payload"]["price"])) for obj in window if obj["payload"]["side"] == "LOW"]
        if len(highs) == len(lows) == 2 and (
            (highs[1] > highs[0] and lows[1] > lows[0])
            or (highs[1] < highs[0] and lows[1] < lows[0])
        ):
            return True
    return False


def _first_midpoint_reaction(index: Any, low: Decimal, high: Decimal, after_at: int, decision_at: int):
    midpoint = (low + high) / Decimal(2)
    for bar in index.bars:
        if bar.start < after_at or bar.end > decision_at:
            continue
        if bar.low <= midpoint <= bar.high and low < bar.close < high:
            return {
                "id": digest([VERSION, "MIDPOINT_REACTION", index.symbol, index.tf, bar.start, str(midpoint)]),
                "kind": "RANGE_MIDPOINT_REACTION",
                "known_at": bar.end,
                "completed_at": bar.end,
                "source_validated": True,
                "bar_start": bar.start,
                "midpoint": str(midpoint),
                "evidence": "Completed bar interacted with source 0.5 equilibrium and closed inside candidate range",
            }
    return None


def _first_deviation_reclaim(index: Any, low: Decimal, high: Decimal, after_at: int, decision_at: int):
    for bar in index.bars:
        if bar.start < after_at or bar.end > decision_at:
            continue
        below = bar.low < low and low < bar.close < high
        above = bar.high > high and low < bar.close < high
        if below and above:
            return None, "WAIT_RANGE_BOTH_SIDE_DEVIATION"
        if below:
            return {
                "id": digest([VERSION, "RANGE_DEVIATION", "LONG", index.symbol, index.tf, bar.start]),
                "kind": "RANGE_DEVIATION_RECLAIM",
                "direction": "LONG",
                "known_at": bar.end,
                "completed_at": bar.end,
                "source_validated": True,
                "bar_start": bar.start,
                "extreme": str(bar.low),
                "close": str(bar.close),
                "evidence": "Excursion below known lower range boundary followed by completed close back inside range",
            }, None
        if above:
            return {
                "id": digest([VERSION, "RANGE_DEVIATION", "SHORT", index.symbol, index.tf, bar.start]),
                "kind": "RANGE_DEVIATION_RECLAIM",
                "direction": "SHORT",
                "known_at": bar.end,
                "completed_at": bar.end,
                "source_validated": True,
                "bar_start": bar.start,
                "extreme": str(bar.high),
                "close": str(bar.close),
                "evidence": "Excursion above known upper range boundary followed by completed close back inside range",
            }, None
    return None, "WAIT_RANGE_DEVIATION"


def _first_boundary_retest(index: Any, low: Decimal, high: Decimal, direction: str, after_at: int, decision_at: int):
    boundary = low if direction == "LONG" else high
    for bar in index.bars:
        if bar.start < after_at or bar.end > decision_at:
            continue
        if bar.low <= boundary <= bar.high and low < bar.close < high:
            return {
                "id": digest([VERSION, "RANGE_RETEST", direction, index.symbol, index.tf, bar.start]),
                "kind": "RANGE_BOUNDARY_RETEST",
                "known_at": bar.end,
                "completed_at": bar.end,
                "source_validated": True,
                "bar_start": bar.start,
                "boundary": str(boundary),
                "evidence": "Later completed retest of reclaimed source range boundary with close retained inside range",
            }
    return None


def resolve_range_chain(index: Any, range_id: str, decision_at: int) -> dict[str, Any]:
    raw = index.by_id.get(range_id)
    if raw is None or raw.get("kind") != "range":
        return {"state": "OBJECTIVE_FAIL", "reason": "RANGE_NOT_FOUND", "trade_entry_allowed": False}
    if raw.get("known_at", decision_at + 1) > decision_at:
        return {"state": "UNKNOWN", "reason": "WAIT_RANGE_NOT_YET_KNOWN", "trade_entry_allowed": False}
    p = raw.get("payload", {})
    if not {"low", "high", "low_swing_id", "high_swing_id"} <= set(p):
        return {"state": "UNKNOWN", "reason": "WAIT_RANGE_BOUNDARY_IDENTITY", "trade_entry_allowed": False}
    low, high = Decimal(str(p["low"])), Decimal(str(p["high"]))
    if low >= high:
        return {"state": "OBJECTIVE_FAIL", "reason": "RANGE_BOUNDARIES_INVALID", "trade_entry_allowed": False}
    low_swing = index.by_id.get(p["low_swing_id"])
    high_swing = index.by_id.get(p["high_swing_id"])
    if not all(
        obj and obj.get("kind") == "swing" and obj.get("source_validated") is True
        for obj in (low_swing, high_swing)
    ):
        return {"state": "UNKNOWN", "reason": "WAIT_RANGE_SOURCE_SWINGS", "trade_entry_allowed": False}
    if max(low_swing["known_at"], high_swing["known_at"]) > raw["known_at"]:
        return {"state": "OBJECTIVE_FAIL", "reason": "RANGE_BACKDATED_BOUNDARY", "trade_entry_allowed": False}

    midpoint = _first_midpoint_reaction(index, low, high, raw["known_at"], decision_at)
    if midpoint is None:
        return {"state": "UNKNOWN", "reason": "WAIT_RANGE_MIDPOINT_REACTION", "trade_entry_allowed": False}

    deviation, reason = _first_deviation_reclaim(index, low, high, midpoint["known_at"], decision_at)
    if deviation is None:
        return {"state": "UNKNOWN", "reason": reason, "trade_entry_allowed": False}

    if _has_directional_structure_inside(index, low, high, raw["known_at"], deviation["known_at"]):
        return {
            "state": "OBJECTIVE_FAIL",
            "reason": "RANGE_INTERNAL_TREND_STRUCTURE",
            "source_rule_ids": ["S_RANGE_FORMATION"],
            "trade_entry_allowed": False,
        }

    direction = deviation["direction"]
    choch = first_directional_bos(index, direction, deviation["known_at"], decision_at)
    if choch is None:
        return {"state": "UNKNOWN", "reason": "WAIT_RANGE_RETURN_CHOCH", "trade_entry_allowed": False}

    retest = _first_boundary_retest(index, low, high, direction, choch["known_at"], decision_at)
    if retest is None:
        return {"state": "UNKNOWN", "reason": "WAIT_RANGE_RECLAIM_RETEST", "trade_entry_allowed": False}

    entry_boundary = low if direction == "LONG" else high
    opposite_boundary = high if direction == "LONG" else low
    return {
        "state": "SOURCE_CHAIN_READY",
        "branch": "RANGE_CONSERVATIVE",
        "direction": direction,
        "setup_tf": raw["tf"],
        "decision_at": retest["known_at"],
        "range_id": raw["id"],
        "boundary_swing_ids": [low_swing["id"], high_swing["id"]],
        "midpoint_reaction_id": midpoint["id"],
        "deviation_id": deviation["id"],
        "choch_structure_break_id": choch["id"],
        "retest_id": retest["id"],
        "entry": {
            "kind": "RANGE_RETEST_PROXIMAL_BOUNDARY",
            "price": str(entry_boundary),
            "technical_normalization_id": "N11_ENTRY",
        },
        "stop_anchor": {
            "kind": "DEVIATION_INVALIDATION_EXTREME",
            "price": deviation["extreme"],
        },
        "target_plan": {
            "kind": "RANGE_80_20_SAME_ZONE",
            "opposite_boundary": str(opposite_boundary),
            "allocation": ["0.80", "0.20"],
            "user_resolution_id": "U1",
            "note": "Exact tick-inside quote deferred to venue metadata stage; no P&L in source resolver.",
        },
        "source_rule_ids": ["S_RANGE_FORMATION", "S_RANGE_DEVIATION", "S_RANGE_CONSERVATIVE", "S_BOS"],
        "user_resolution_ids": ["U1", "U2", "U3", "U4"],
        "technical_normalization_ids": ["TN_RANGE_BOUNDARY_001", "TN_RANGE_REACTION_001", "TN_BOS_001", "N11_ENTRY"],
        "trade_entry_allowed": False,
    }
