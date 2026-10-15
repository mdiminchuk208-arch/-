"""Deterministic OB and Breaker formation resolvers for Source Strategy Rebuild v1."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from original_strategy_executable_profile_v1 import digest
from source_strategy_v1_structure_resolver import first_directional_bos


VERSION = "SOURCE_STRATEGY_REBUILD_v1_OB_BREAKER_RESOLVER"
TRADE_ENTRY_ALLOWED = False


def _bar_by_start(index: Any, start: int):
    for bar in index.bars:
        if bar.start == start:
            return bar
    return None


def _body_wicks(bar: Any) -> tuple[Decimal, Decimal, Decimal]:
    body = abs(bar.close - bar.open)
    upper = bar.high - max(bar.open, bar.close)
    lower = min(bar.open, bar.close) - bar.low
    return body, upper, lower


def _matching_fvg(index: Any, direction: str, required_bar_starts: set[int], decision_at: int):
    candidates = []
    for obj in index.by_id.values():
        if obj.get("kind") != "FVG" or obj.get("source_validated") is not True:
            continue
        if obj.get("known_at", decision_at + 1) > decision_at:
            continue
        payload = obj.get("payload", {})
        if payload.get("direction") != direction:
            continue
        starts = set(payload.get("bar_starts", []))
        if required_bar_starts <= starts:
            candidates.append(obj)
    return min(candidates, key=lambda obj: (obj["known_at"], obj["id"])) if candidates else None


def resolve_ob_formation(index: Any, ob_id: str, decision_at: int) -> dict[str, Any]:
    """Resolve whether the market object itself is a source-valid OB.

    Trading the OB is a separate U3 conservative reaction->M15 BOS->new-POI chain.
    A Breaker may descend from this valid market object even when the OB trade setup was never completed.
    """
    raw = index.by_id.get(ob_id)
    if raw is None or raw.get("kind") != "OB":
        return {"state": "OBJECTIVE_FAIL", "reason": "OB_NOT_FOUND", "trade_entry_allowed": False}
    if raw.get("known_at", decision_at + 1) > decision_at:
        return {"state": "UNKNOWN", "reason": "WAIT_OB_NOT_YET_KNOWN", "trade_entry_allowed": False}
    p = raw.get("payload", {})
    direction = p.get("direction")
    if direction not in ("LONG", "SHORT"):
        return {"state": "OBJECTIVE_FAIL", "reason": "OB_DIRECTION_INVALID", "trade_entry_allowed": False}
    source_bar = _bar_by_start(index, p.get("source_bar_start"))
    impulse_bar = _bar_by_start(index, p.get("engulf_bar_start"))
    level = index.by_id.get(p.get("level_id"))
    if source_bar is None or impulse_bar is None or not level or level.get("kind") != "swing":
        return {"state": "UNKNOWN", "reason": "WAIT_OB_SOURCE_GEOMETRY", "trade_entry_allowed": False}
    if level.get("known_at", decision_at + 1) > source_bar.start:
        return {"state": "OBJECTIVE_FAIL", "reason": "OB_RAID_LEVEL_NOT_PREEXISTING", "trade_entry_allowed": False}
    price = Decimal(str(level["payload"]["price"]))
    raid = source_bar.low < price if direction == "LONG" else source_bar.high > price
    if not raid:
        return {"state": "OBJECTIVE_FAIL", "reason": "OB_NO_HIGH_LOW_WICK_RAID", "trade_entry_allowed": False}

    body, upper_wick, lower_wick = _body_wicks(source_bar)
    body_geometry_pass = body > 0 and body > upper_wick and body > lower_wick
    if not body_geometry_pass:
        return {
            "state": "NORMALIZATION_FAIL",
            "reason": "OB_BODY_WICK_NORMALIZATION_FAIL",
            "technical_normalization_id": "TN_OB_BODY_001",
            "trade_entry_allowed": False,
        }

    fvg = _matching_fvg(index, direction, {source_bar.start, impulse_bar.start}, decision_at)
    if fvg is None:
        return {"state": "UNKNOWN", "reason": "WAIT_OB_FOLLOWING_IMBALANCE", "trade_entry_allowed": False}

    bos = first_directional_bos(index, direction, source_bar.end, decision_at)
    if bos is None:
        return {"state": "UNKNOWN", "reason": "WAIT_OB_STRUCTURE_UPDATE", "trade_entry_allowed": False}

    return {
        "state": "SOURCE_OB_VALID",
        "branch": "OB_CONSERVATIVE",
        "direction": direction,
        "setup_tf": raw["tf"],
        "decision_at": max(raw["known_at"], fvg["known_at"], bos["known_at"]),
        "ob_id": raw["id"],
        "raid_level_id": level["id"],
        "imbalance_id": fvg["id"],
        "structure_update_id": bos["id"],
        "zone": {"low": p["low"], "high": p["high"], "body_low": p["body_low"], "body_high": p["body_high"]},
        "source_extreme": str(source_bar.low if direction == "LONG" else source_bar.high),
        "technical_normalization_ids": ["TN_OB_BODY_001", "TN_BOS_001", "TN_IMBALANCE_001"],
        "source_rule_ids": ["S_OB_FORMATION", "S_OB_ZONE", "S_FVG", "S_BOS"],
        "trade_entry_allowed": False,
    }


def resolve_breaker_from_ob(
    index: Any,
    ob: dict[str, Any],
    decision_at: int,
    *,
    whole_impulse: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A Breaker descends from a source-valid OB market object plus causal whole impulse."""
    if ob.get("state") != "SOURCE_OB_VALID" or ob.get("branch") != "OB_CONSERVATIVE":
        return {"state": "UNKNOWN", "reason": "WAIT_SOURCE_VALID_OB", "trade_entry_allowed": False}
    if (
        not whole_impulse
        or whole_impulse.get("source_validated") is not True
        or whole_impulse.get("value") is not True
        or whole_impulse.get("known_at", decision_at + 1) > decision_at
        or not {"low", "high", "known_at", "evidence"} <= set(whole_impulse)
    ):
        return {"state": "UNKNOWN", "reason": "WAIT_BREAKER_WHOLE_IMPULSE", "trade_entry_allowed": False}

    original_direction = ob["direction"]
    direction = "SHORT" if original_direction == "LONG" else "LONG"
    low = Decimal(str(ob["zone"]["low"]))
    high = Decimal(str(ob["zone"]["high"]))
    impulse_low = Decimal(str(whole_impulse["low"]))
    impulse_high = Decimal(str(whole_impulse["high"]))
    if impulse_low >= impulse_high:
        return {"state": "OBJECTIVE_FAIL", "reason": "BREAKER_IMPULSE_GEOMETRY_INVALID", "trade_entry_allowed": False}

    for bar in index.bars:
        if bar.start < ob["decision_at"] or bar.end > decision_at:
            continue
        if whole_impulse.get("interval_start", bar.start) > bar.start or whole_impulse.get("interval_end", bar.end) < bar.end:
            continue
        broken = bar.close < low if direction == "SHORT" else bar.close > high
        if not broken:
            continue
        fvg = _matching_fvg(index, direction, {bar.start}, decision_at)
        if fvg is None:
            continue
        bos = first_directional_bos(index, direction, bar.start, decision_at)
        if bos is None:
            continue
        stop_anchor = impulse_high if direction == "SHORT" else impulse_low
        return {
            "state": "SOURCE_FORMATION_READY",
            "branch": "BREAKER",
            "direction": direction,
            "setup_tf": ob["setup_tf"],
            "decision_at": max(bar.end, fvg["known_at"], bos["known_at"], whole_impulse["known_at"]),
            "parent_ob_id": ob["ob_id"],
            "break_bar_start": bar.start,
            "break_imbalance_id": fvg["id"],
            "structure_confirmation_id": bos["id"],
            "whole_impulse_evidence": whole_impulse["evidence"],
            "entry_zone": {"low": ob["zone"]["body_low"], "high": ob["zone"]["body_high"]},
            "stop_anchor": {"kind": "RAID_IMPULSE_EXTREME", "price": str(stop_anchor)},
            "source_rule_ids": ["S_BREAKER_FORMATION", "S_BREAKER_STOPS", "S_BOS", "S_FVG"],
            "user_resolution_ids": ["U2", "U3"],
            "physical_idea_id": digest([VERSION, "BREAKER", ob["ob_id"], direction, bar.start]),
            "trade_entry_allowed": False,
        }
    return {"state": "UNKNOWN", "reason": "WAIT_BREAKER_CONFIRMATION", "trade_entry_allowed": False}
