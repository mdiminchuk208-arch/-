"""Assemble source/user-resolved pre-venue trade plans without fills or P&L."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from original_strategy_executable_profile_v1 import digest
from source_strategy_v1_fta_resolver import known_prefix_contextual_inventory, nearest_contextual_fta


VERSION = "SOURCE_STRATEGY_REBUILD_v1_PLAN_RESOLVER"
TRADE_ENTRY_ALLOWED = False


def _proximal_entry(direction: str, zone: Mapping[str, Any]) -> Decimal:
    low, high = Decimal(str(zone["low"])), Decimal(str(zone["high"]))
    if low >= high:
        raise ValueError("INVALID_ENTRY_ZONE")
    return high if direction == "LONG" else low


def atr_sma14_from_pattern(index: Any, pattern_bar_start: int) -> Decimal | None:
    """N11_ATR_SMA14: 14 True Ranges need 15 contiguous completed pattern-TF bars."""
    position = next((i for i, bar in enumerate(index.bars) if bar.start == pattern_bar_start), None)
    if position is None or position < 14:
        return None
    window = index.bars[position - 14 : position + 1]
    if len(window) != 15:
        return None
    step = window[0].end - window[0].start
    if any(bar.end - bar.start != step for bar in window):
        return None
    if any(window[i].start != window[i - 1].end for i in range(1, len(window))):
        return None
    values = []
    for i in range(1, len(window)):
        bar, previous = window[i], window[i - 1]
        values.append(
            max(
                bar.high - bar.low,
                abs(bar.high - previous.close),
                abs(bar.low - previous.close),
            )
        )
    return sum(values, Decimal(0)) / Decimal(14)


def _sfp_stop(chain: dict[str, Any], parent_index: Any) -> dict[str, Any] | None:
    sfp = parent_index.by_id.get(chain.get("sfp_id"))
    if not sfp:
        return None
    p = sfp.get("payload", {})
    pattern_start = p.get("bar_start")
    atr = atr_sma14_from_pattern(parent_index, pattern_start)
    if atr is None:
        return None
    direction = chain["direction"]
    extreme = Decimal(str(p["low"] if direction == "LONG" else p["high"]))
    price = extreme - atr if direction == "LONG" else extreme + atr
    return {
        "kind": "SFP_PATTERN_EXTREME_ATR14",
        "price": str(price),
        "pattern_extreme": str(extreme),
        "atr14": str(atr),
        "user_resolution_id": "U2",
        "technical_normalization_id": "N11_ATR_SMA14",
    }


def _entry_and_stop(chain: dict[str, Any], parent_index: Any | None) -> tuple[Decimal, dict[str, Any]] | None:
    branch, direction = chain.get("branch"), chain.get("direction")
    if branch in ("SFP", "OB_CONSERVATIVE"):
        zone = chain.get("entry_poi")
        if not zone:
            return None
        entry = _proximal_entry(direction, zone)
        if branch == "SFP":
            if parent_index is None:
                return None
            stop = _sfp_stop(chain, parent_index)
        else:
            stop = chain.get("stop_anchor")
    elif branch == "BREAKER":
        entry = _proximal_entry(direction, chain["entry_zone"])
        stop = chain.get("stop_anchor")
    elif branch == "STB_BTS":
        entry = Decimal(str(chain["entry"]["price"]))
        stop = chain.get("stop_anchor")
    elif branch == "RANGE_CONSERVATIVE":
        entry = Decimal(str(chain["entry"]["price"]))
        stop = chain.get("stop_anchor")
    else:
        return None
    if stop is None or "price" not in stop:
        return None
    return entry, stop


def assemble_source_plan(
    chain: dict[str, Any],
    indexes: Mapping[int, Any],
    *,
    parent_index: Any | None = None,
    consumed_ids: Iterable[str] = (),
    extra_target_objects: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Assemble U1/U2/U3 plan before tick rounding/execution compatibility."""
    if chain.get("state") not in ("SOURCE_CHAIN_READY", "SOURCE_FORMATION_READY"):
        return {"state": "UNKNOWN", "reason": "WAIT_SOURCE_CHAIN_READY", "trade_entry_allowed": False}
    if chain.get("branch") == "BREAKER" and chain.get("state") != "SOURCE_FORMATION_READY":
        return {"state": "UNKNOWN", "reason": "WAIT_BREAKER_FORMATION", "trade_entry_allowed": False}
    resolved = _entry_and_stop(chain, parent_index)
    if resolved is None:
        return {"state": "UNKNOWN", "reason": "WAIT_ENTRY_OR_STOP_GEOMETRY", "trade_entry_allowed": False}
    entry, stop = resolved
    stop_price = Decimal(str(stop["price"]))
    direction = chain["direction"]
    if (direction == "LONG" and stop_price >= entry) or (direction == "SHORT" and stop_price <= entry):
        return {"state": "OBJECTIVE_FAIL", "reason": "STOP_NOT_PROTECTIVE", "trade_entry_allowed": False}

    if chain["branch"] == "RANGE_CONSERVATIVE":
        target_price = Decimal(str(chain["target_plan"]["opposite_boundary"]))
        target = {
            **chain["target_plan"],
            "price_pre_tick": str(target_price),
            "technical_normalization_id": "N11_TARGET",
        }
        inventory = None
    else:
        inventory = known_prefix_contextual_inventory(
            indexes,
            direction,
            entry,
            chain["decision_at"],
            consumed_ids=consumed_ids,
            extra_objects=extra_target_objects,
        )
        target = nearest_contextual_fta(inventory)
        if target is None:
            return {
                "state": "UNKNOWN",
                "reason": "WAIT_CONTEXTUAL_FTA",
                "entry_price_pre_tick": str(entry),
                "stop_anchor": stop,
                "inventory_id": inventory["id"],
                "trade_entry_allowed": False,
            }
        target_price = Decimal(str(target["price"]))

    if (direction == "LONG" and target_price <= entry) or (direction == "SHORT" and target_price >= entry):
        return {"state": "OBJECTIVE_FAIL", "reason": "TARGET_NOT_DIRECTIONAL", "trade_entry_allowed": False}

    plan_id = digest(
        [
            VERSION,
            chain["branch"],
            direction,
            chain["decision_at"],
            str(entry),
            str(stop_price),
            str(target_price),
            chain.get("sfp_id") or chain.get("ob_id") or chain.get("stb_id") or chain.get("range_id") or chain.get("parent_ob_id"),
        ]
    )
    return {
        "state": "SOURCE_PLAN_READY_PRE_VENUE",
        "plan_id": plan_id,
        "branch": chain["branch"],
        "direction": direction,
        "setup_tf": chain["setup_tf"],
        "decision_at": chain["decision_at"],
        "entry": {
            "price_pre_tick": str(entry),
            "technical_normalization_id": "N11_ENTRY",
        },
        "stop": stop,
        "target": target,
        "target_inventory_id": inventory["id"] if inventory else None,
        "user_resolution_ids": sorted(set(chain.get("user_resolution_ids", [])) | {"U1", "U2", "U3"}),
        "venue_metadata_required_next": True,
        "financial_outcomes_generated": False,
        "trade_entry_allowed": False,
    }
