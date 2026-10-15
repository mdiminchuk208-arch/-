"""U3 conservative OB entry-chain resolver for Source Strategy Rebuild v1."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from source_strategy_v1_sfp_resolver import first_new_source_poi
from source_strategy_v1_structure_resolver import first_directional_bos


VERSION = "SOURCE_STRATEGY_REBUILD_v1_OB_ENTRY_RESOLVER"
TRADE_ENTRY_ALLOWED = False


def _swings_between(index: Any, start_at: int, end_at: int) -> list[dict[str, Any]]:
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


def _corrective_structure_into_ob(index: Any, trade_direction: str, start_at: int, touch_at: int):
    swings = _swings_between(index, start_at, touch_at)
    wanted = "SHORT" if trade_direction == "LONG" else "LONG"
    for pos in range(3, len(swings)):
        window = swings[pos - 3 : pos + 1]
        sides = [obj["payload"]["side"] for obj in window]
        if sides not in (["LOW", "HIGH", "LOW", "HIGH"], ["HIGH", "LOW", "HIGH", "LOW"]):
            continue
        highs = [Decimal(str(obj["payload"]["price"])) for obj in window if obj["payload"]["side"] == "HIGH"]
        lows = [Decimal(str(obj["payload"]["price"])) for obj in window if obj["payload"]["side"] == "LOW"]
        if len(highs) != 2 or len(lows) != 2:
            continue
        direction = (
            "LONG"
            if highs[1] > highs[0] and lows[1] > lows[0]
            else "SHORT"
            if highs[1] < highs[0] and lows[1] < lows[0]
            else None
        )
        if direction == wanted:
            return {
                "state": "PASS",
                "direction": direction,
                "swing_ids": [obj["id"] for obj in window],
                "known_at": max(obj["known_at"] for obj in window),
                "technical_normalization_id": "TN_OB_APPROACH_001",
            }
    return None


def _first_reaction(m15_index: Any, direction: str, low: Decimal, high: Decimal, after_at: int, decision_at: int):
    for bar in m15_index.bars:
        if bar.start < after_at or bar.end > decision_at:
            continue
        touches = bar.low <= high and bar.high >= low
        if not touches:
            continue
        reacted = bar.close > high if direction == "LONG" else bar.close < low
        if reacted:
            return {
                "kind": "OB_REACTION",
                "direction": direction,
                "bar_start": bar.start,
                "known_at": bar.end,
                "completed_at": bar.end,
                "source_validated": True,
                "technical_normalization_id": "TN_OB_REACTION_001",
                "evidence": "First M15 zone contact that closes back away from the OB in source trade direction",
            }
    return None


def resolve_ob_entry_chain(
    formation: dict[str, Any],
    m15_index: Any,
    decision_at: int,
) -> dict[str, Any]:
    if formation.get("state") != "SOURCE_FORMATION_READY" or formation.get("branch") != "OB_CONSERVATIVE":
        return {"state": "UNKNOWN", "reason": "WAIT_OB_SOURCE_FORMATION", "trade_entry_allowed": False}
    if formation.get("setup_tf") == 15:
        return {
            "state": "UNKNOWN",
            "reason": "WAIT_NO_AVAILABLE_LOWER_TF",
            "ob_id": formation.get("ob_id"),
            "trade_entry_allowed": False,
        }
    direction = formation["direction"]
    low = Decimal(str(formation["zone"]["low"]))
    high = Decimal(str(formation["zone"]["high"]))
    reaction = _first_reaction(m15_index, direction, low, high, formation["decision_at"], decision_at)
    if reaction is None:
        return {"state": "UNKNOWN", "reason": "WAIT_CAUSAL_OB_REACTION", "trade_entry_allowed": False}
    approach = _corrective_structure_into_ob(
        m15_index,
        direction,
        formation["decision_at"],
        reaction["bar_start"],
    )
    if approach is None:
        return {
            "state": "NORMALIZATION_FAIL",
            "reason": "OB_SMOOTH_STRUCTURAL_APPROACH_FAIL",
            "technical_normalization_id": "TN_OB_APPROACH_001",
            "trade_entry_allowed": False,
        }
    bos = first_directional_bos(m15_index, direction, reaction["known_at"], decision_at)
    if bos is None:
        return {
            "state": "UNKNOWN",
            "reason": "WAIT_CAUSAL_REACTION_BOS",
            "ob_id": formation["ob_id"],
            "trade_entry_allowed": False,
        }
    poi, reason = first_new_source_poi(m15_index, bos, direction, decision_at)
    if poi is None:
        return {
            "state": "UNKNOWN",
            "reason": reason or "WAIT_NEW_POI_AFTER_BOS",
            "ob_id": formation["ob_id"],
            "bos_id": bos["id"],
            "trade_entry_allowed": False,
        }
    return {
        **formation,
        "state": "SOURCE_CHAIN_READY",
        "decision_at": max(formation["decision_at"], reaction["known_at"], bos["known_at"], poi["known_at"]),
        "approach": approach,
        "reaction": reaction,
        "m15_bos_id": bos["id"],
        "entry_poi_id": poi["id"],
        "entry_poi": {
            "kind": poi["kind"],
            "low": poi["payload"]["low"],
            "high": poi["payload"]["high"],
        },
        "stop_anchor": {
            "kind": "SOURCE_OB_EXTREME",
            "price": formation["source_extreme"],
        },
        "remaining_requirements": [],
        "technical_normalization_ids": sorted(
            set(formation.get("technical_normalization_ids", []))
            | {"TN_OB_APPROACH_001", "TN_OB_REACTION_001"}
        ),
        "user_resolution_ids": ["U2", "U3", "U4"],
        "trade_entry_allowed": False,
    }
