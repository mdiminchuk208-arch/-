"""Causal source structure resolver shared by Source Strategy Rebuild v1 branches."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from original_strategy_executable_profile_v1 import digest


VERSION = "SOURCE_STRATEGY_REBUILD_v1_STRUCTURE_RESOLVER"
TRADE_ENTRY_ALLOWED = False


def _swings(index: Any, at: int) -> list[dict[str, Any]]:
    return sorted(
        (
            obj
            for obj in index.by_id.values()
            if obj.get("kind") == "swing"
            and obj.get("source_validated") is True
            and obj.get("known_at", at + 1) <= at
            and obj.get("payload", {}).get("side") in ("HIGH", "LOW")
        ),
        key=lambda obj: (obj["known_at"], obj["id"]),
    )


def latest_source_structure(index: Any, at: int) -> dict[str, Any] | None:
    """Latest causal 4-swing alternating HH/HL or LH/LL structure."""
    swings = _swings(index, at)
    best = None
    for pos in range(3, len(swings)):
        window = swings[pos - 3 : pos + 1]
        sides = [obj["payload"]["side"] for obj in window]
        if sides not in (["LOW", "HIGH", "LOW", "HIGH"], ["HIGH", "LOW", "HIGH", "LOW"]):
            continue
        highs = [obj for obj in window if obj["payload"]["side"] == "HIGH"]
        lows = [obj for obj in window if obj["payload"]["side"] == "LOW"]
        high_prices = [Decimal(str(obj["payload"]["price"])) for obj in highs]
        low_prices = [Decimal(str(obj["payload"]["price"])) for obj in lows]
        if high_prices[1] > high_prices[0] and low_prices[1] > low_prices[0]:
            direction = "LONG"
            protected = lows[1]
        elif high_prices[1] < high_prices[0] and low_prices[1] < low_prices[0]:
            direction = "SHORT"
            protected = highs[1]
        else:
            continue
        best = {
            "id": digest([VERSION, "STRUCTURE", index.symbol, index.tf, [obj["id"] for obj in window]]),
            "kind": "structure",
            "symbol": index.symbol,
            "tf": index.tf,
            "known_at": max(obj["known_at"] for obj in window),
            "completed_at": max(obj["known_at"] for obj in window),
            "source_validated": True,
            "payload": {
                "direction": direction,
                "swing_ids": [obj["id"] for obj in window],
                "protected_endpoint_id": protected["id"],
                "protected_endpoint_price": protected["payload"]["price"],
            },
            "source_rule_ids": ["S_STRUCTURE", "S_SWING"],
            "technical_normalization_ids": ["TN_SWING_001"],
            "evidence": "Latest completed alternating four-swing source structure; no future bars or fitted owner labels",
        }
    return best


def latest_opposite_swing(index: Any, direction: str, at: int) -> dict[str, Any] | None:
    side = "HIGH" if direction == "LONG" else "LOW"
    candidates = [obj for obj in _swings(index, at) if obj["payload"]["side"] == side]
    return candidates[-1] if candidates else None


def first_directional_bos(index: Any, direction: str, after_at: int, decision_at: int) -> dict[str, Any] | None:
    """Completed close beyond the latest already-known opposite swing; no wick-only BOS."""
    level = latest_opposite_swing(index, direction, after_at)
    if level is None:
        return None
    price = Decimal(str(level["payload"]["price"]))
    for bar in index.bars:
        if bar.start < after_at or bar.end > decision_at or level["known_at"] > bar.start:
            continue
        passed = bar.close > price if direction == "LONG" else bar.close < price
        if not passed:
            continue
        return {
            "id": digest([VERSION, "BOS", index.symbol, index.tf, direction, level["id"], bar.start]),
            "kind": "BOS",
            "symbol": index.symbol,
            "tf": index.tf,
            "known_at": bar.end,
            "completed_at": bar.end,
            "source_validated": True,
            "payload": {
                "direction": direction,
                "broken_swing_id": level["id"],
                "broken_price": str(price),
                "bar_start": bar.start,
                "close": str(bar.close),
            },
            "source_rule_ids": ["S_BOS"],
            "technical_normalization_ids": ["TN_BOS_001"],
            "evidence": "Completed body close beyond already-known opposite structural swing",
        }
    return None


def source_trend_alignment(index: Any, direction: str, at: int) -> dict[str, Any] | None:
    structure = latest_source_structure(index, at)
    if structure is None:
        return None
    result = deepcopy(structure)
    result["aligned"] = structure["payload"]["direction"] == direction
    return result
