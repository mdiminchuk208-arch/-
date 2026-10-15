"""Deterministic STB/BTS resolver for Source Strategy Rebuild v1."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from original_strategy_executable_profile_v1 import digest
from source_strategy_v1_structure_resolver import first_directional_bos, source_trend_alignment


VERSION = "SOURCE_STRATEGY_REBUILD_v1_STB_RESOLVER"
TRADE_ENTRY_ALLOWED = False


def _bar_by_start(index: Any, start: int):
    for bar in index.bars:
        if bar.start == start:
            return bar
    return None


def resolve_stb_chain(index: Any, stb_id: str, decision_at: int) -> dict[str, Any]:
    raw = index.by_id.get(stb_id)
    if raw is None or raw.get("kind") != "STB":
        return {"state": "OBJECTIVE_FAIL", "reason": "STB_NOT_FOUND", "trade_entry_allowed": False}
    if raw.get("known_at", decision_at + 1) > decision_at:
        return {"state": "UNKNOWN", "reason": "WAIT_STB_NOT_YET_KNOWN", "trade_entry_allowed": False}
    payload = raw.get("payload", {})
    direction = payload.get("direction")
    if direction not in ("LONG", "SHORT"):
        return {"state": "OBJECTIVE_FAIL", "reason": "STB_DIRECTION_INVALID", "trade_entry_allowed": False}

    level = index.by_id.get(payload.get("level_id"))
    if not level or level.get("kind") != "swing" or level.get("known_at", decision_at + 1) > payload.get("source_bar_start", -1):
        return {"state": "OBJECTIVE_FAIL", "reason": "STB_NO_PREEXISTING_LIQUIDITY", "trade_entry_allowed": False}

    source_bar = _bar_by_start(index, payload.get("source_bar_start"))
    engulf_bar = _bar_by_start(index, payload.get("engulf_bar_start"))
    if source_bar is None or engulf_bar is None:
        return {"state": "UNKNOWN", "reason": "WAIT_STB_NATIVE_BARS", "trade_entry_allowed": False}

    level_price = Decimal(str(level["payload"]["price"]))
    if direction == "LONG":
        raid = source_bar.low < level_price
        source_opposite = source_bar.close < source_bar.open
        engulf_direction = engulf_bar.close > engulf_bar.open
    else:
        raid = source_bar.high > level_price
        source_opposite = source_bar.close > source_bar.open
        engulf_direction = engulf_bar.close < engulf_bar.open
    full_engulf = engulf_bar.low <= source_bar.low and engulf_bar.high >= source_bar.high
    if not (raid and source_opposite and engulf_direction and full_engulf):
        return {"state": "OBJECTIVE_FAIL", "reason": "STB_RAID_OR_FULL_ENGULF_FAIL", "trade_entry_allowed": False}

    trend = source_trend_alignment(index, direction, source_bar.start)
    if trend is None:
        return {"state": "UNKNOWN", "reason": "WAIT_STB_MARKET_STRUCTURE", "trade_entry_allowed": False}
    if not trend["aligned"]:
        return {
            "state": "OBJECTIVE_FAIL",
            "reason": "STB_MAIN_TREND_MISMATCH",
            "structure_id": trend["id"],
            "trade_entry_allowed": False,
        }

    bos = first_directional_bos(index, direction, raw["known_at"], decision_at)
    if bos is None:
        return {
            "state": "UNKNOWN",
            "reason": "WAIT_STB_BOS_OR_CONFIRMATION",
            "structure_id": trend["id"],
            "trade_entry_allowed": False,
        }

    zone_low = Decimal(str(payload["low"]))
    zone_high = Decimal(str(payload["high"]))
    if zone_low >= zone_high:
        return {"state": "OBJECTIVE_FAIL", "reason": "STB_ZONE_INVALID", "trade_entry_allowed": False}
    midpoint = (zone_low + zone_high) / Decimal(2)
    stop_anchor = source_bar.low if direction == "LONG" else source_bar.high

    return {
        "state": "SOURCE_CHAIN_READY",
        "branch": "STB_BTS",
        "direction": direction,
        "setup_tf": raw["tf"],
        "decision_at": bos["known_at"],
        "stb_id": raw["id"],
        "liquidity_level_id": level["id"],
        "structure_id": trend["id"],
        "bos_confirmation_id": bos["id"],
        "entry": {
            "kind": "STB_MIDPOINT",
            "price": str(midpoint),
            "zone_low": str(zone_low),
            "zone_high": str(zone_high),
        },
        "stop_anchor": {
            "kind": "MANIPULATION_RAID_EXTREME",
            "price": str(stop_anchor),
            "source_bar_start": source_bar.start,
        },
        "source_rule_ids": ["S_STB_FORMATION", "S_STB_ENTRY", "S_STRUCTURE", "S_BOS"],
        "user_resolution_ids": ["U2", "U3", "U4"],
        "physical_idea_id": digest([VERSION, index.symbol, raw["id"], direction]),
        "trade_entry_allowed": False,
    }
