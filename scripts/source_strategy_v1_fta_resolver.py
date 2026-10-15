"""Known-prefix contextual FTA inventory for Source Strategy Rebuild v1."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from original_strategy_executable_profile_v1 import digest


VERSION = "SOURCE_STRATEGY_REBUILD_v1_FTA_RESOLVER"
TRADE_ENTRY_ALLOWED = False
ACTIVE_TFS = (15, 60, 240, 1440)
POI_KINDS = {"POI", "OB", "breaker", "STB", "FVG", "refined_POI"}


def _iter_objects(indexes: Mapping[int, Any], at: int, extra_objects: Iterable[dict[str, Any]] = ()):
    seen: set[str] = set()
    for tf in ACTIVE_TFS:
        index = indexes.get(tf)
        if index is None:
            continue
        for obj in index.by_id.values():
            if obj.get("id") in seen or obj.get("known_at", at + 1) > at:
                continue
            seen.add(obj["id"])
            yield obj
    for obj in extra_objects:
        if obj.get("id") in seen or obj.get("known_at", at + 1) > at:
            continue
        seen.add(obj["id"])
        yield obj


def known_prefix_contextual_inventory(
    indexes: Mapping[int, Any],
    direction: str,
    entry_price: Decimal | str,
    at: int,
    *,
    consumed_ids: Iterable[str] = (),
    extra_objects: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Enumerate source-valid opposing POIs already known and ahead of entry.

    This implements the frozen U1/N11 nearest-opposing-POI convention without
    venue rounding, P&L, future objects or retrospective best-target selection.
    """
    if direction not in ("LONG", "SHORT"):
        raise ValueError("INVALID_DIRECTION")
    entry = Decimal(str(entry_price))
    consumed = set(consumed_ids)
    rows = []
    for obj in _iter_objects(indexes, at, extra_objects):
        if obj.get("kind") not in POI_KINDS or obj.get("source_validated") is not True:
            continue
        if obj.get("id") in consumed or obj.get("tf") not in ACTIVE_TFS:
            continue
        p = obj.get("payload", {})
        if not {"low", "high", "direction"} <= set(p):
            continue
        low, high = Decimal(str(p["low"])), Decimal(str(p["high"]))
        if low >= high or p["direction"] == direction:
            continue
        if direction == "LONG":
            if low <= entry:
                continue
            proximal = low
            distance = low - entry
        else:
            if high >= entry:
                continue
            proximal = high
            distance = entry - high
        rows.append(
            {
                "id": obj["id"],
                "kind": obj["kind"],
                "tf": obj["tf"],
                "direction": p["direction"],
                "low": str(low),
                "high": str(high),
                "proximal_target": str(proximal),
                "distance": str(distance),
                "known_at": obj["known_at"],
                "source_validated": True,
                "contextual_relation": "OPPOSING_SOURCE_POI_AHEAD_OF_ENTRY",
                "evidence": obj.get("evidence", "source-valid known-prefix POI"),
            }
        )
    rows.sort(key=lambda row: (Decimal(row["distance"]), row["tf"], row["known_at"], row["id"]))
    return {
        "id": digest([VERSION, direction, str(entry), at, [row["id"] for row in rows]]),
        "known_at": at,
        "complete_for_known_prefix": True,
        "direction": direction,
        "entry_price": str(entry),
        "contextual_pois": rows,
        "consumed_ids": sorted(consumed),
        "trade_entry_allowed": False,
    }


def nearest_contextual_fta(inventory: dict[str, Any]) -> dict[str, Any] | None:
    rows = inventory.get("contextual_pois", [])
    if not rows:
        return None
    minimum = Decimal(rows[0]["distance"])
    tied = [row for row in rows if Decimal(row["distance"]) == minimum]
    prices = {row["proximal_target"] for row in tied}
    if len(prices) != 1:
        raise ValueError("TIED_NEAREST_FTA_PRICE_DISAGREEMENT")
    return {
        "id": digest([VERSION, "NEAREST_FTA", inventory["id"], [row["id"] for row in tied]]),
        "kind": "NEAREST_CONTEXTUAL_FTA",
        "known_at": inventory["known_at"],
        "price": tied[0]["proximal_target"],
        "poi_ids": [row["id"] for row in tied],
        "distance": str(minimum),
        "user_resolution_id": "U1",
        "technical_normalization_id": "N11_TARGET",
        "source_validated": True,
        "trade_entry_allowed": False,
    }
