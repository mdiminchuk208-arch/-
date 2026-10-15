"""Deterministic SFP source-evidence resolver for Source Strategy Rebuild v1.

This module resolves source facts only. It never computes fills, outcomes or P&L.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from original_strategy_executable_profile_v1 import digest


VERSION = "SOURCE_STRATEGY_REBUILD_v1_SFP_RESOLVER"
TRADE_ENTRY_ALLOWED = False
_FORBIDDEN = {
    "pnl",
    "win",
    "loss",
    "profit",
    "profit_factor",
    "win_rate",
    "mfe",
    "mae",
    "fees",
    "funding",
    "slippage",
    "holding_time",
    "outcome",
}


def _no_outcomes(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in _FORBIDDEN:
                raise ValueError("FINANCIAL_OR_OUTCOME_FIELD_FORBIDDEN")
            _no_outcomes(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _no_outcomes(nested)


def _bar_by_start(index: Any, start: int):
    for bar in index.bars:
        if bar.start == start:
            return bar
    return None


def _source_fact(name: str, known_at: int, evidence: str, **payload: Any) -> dict[str, Any]:
    result = {
        "id": digest([VERSION, name, known_at, payload]),
        "kind": name,
        "known_at": known_at,
        "completed_at": known_at,
        "source_validated": True,
        "evidence": evidence,
        **payload,
    }
    _no_outcomes(result)
    return result


def validate_raw_sfp(index: Any, sfp: dict[str, Any], decision_at: int) -> dict[str, Any] | None:
    """Validate only literal sweep + body reclaim against a pre-existing swing/range level."""
    _no_outcomes(sfp)
    if sfp.get("kind") != "SFP" or sfp.get("known_at", decision_at + 1) > decision_at:
        return None
    payload = sfp.get("payload", {})
    direction = payload.get("direction")
    if direction not in ("LONG", "SHORT"):
        return None
    level = index.by_id.get(payload.get("level_id"))
    if not level or level.get("kind") not in ("swing", "range_boundary", "liquidity_pool"):
        return None
    if level.get("known_at", decision_at + 1) > payload.get("bar_start", -1):
        return None
    bar = _bar_by_start(index, payload.get("bar_start"))
    if bar is None or bar.end != sfp.get("known_at"):
        return None
    price = Decimal(str(level["payload"].get("price", payload.get("price"))))
    if direction == "LONG":
        literal = bar.low < price < bar.close
    else:
        literal = bar.high > price > bar.close
    if not literal:
        return None
    result = deepcopy(sfp)
    result["source_validated"] = True
    result["source_rule_ids"] = sorted(
        set(result.get("source_rule_ids", []))
        | {"S_SFP_FORMATION", "S_LIQUIDITY_CONTEXT", "S_SFP_TF"}
    )
    result["source_attestation"] = {
        "known_at": sfp["known_at"],
        "completed_at": sfp["known_at"],
        "level_id": level["id"],
        "level_kind": level["kind"],
        "evidence": "Causal pre-existing source swing/range liquidity sweep with completed body reclaim",
    }
    result["context"] = {
        "liquidity_context": True,
        "meaningful_for_this_setup": True,
        "reason": "The SFP directly raids the pre-existing structural/range level that defines the setup; no distance score used.",
    }
    _no_outcomes(result)
    return result


def next_native_open_confirmation(index: Any, sfp: dict[str, Any], decision_at: int) -> dict[str, Any] | None:
    """Confirm that the next native OPEN remains on the reclaimed side of the swept level."""
    if not sfp.get("source_validated"):
        return None
    payload = sfp["payload"]
    next_bar = _bar_by_start(index, sfp["known_at"])
    if next_bar is None or next_bar.end > decision_at:
        return None
    level = Decimal(str(payload["price"]))
    direction = payload["direction"]
    passed = next_bar.open >= level if direction == "LONG" else next_bar.open <= level
    if not passed:
        return _source_fact(
            "SFP_NEXT_OPEN_FAIL",
            next_bar.end,
            "Next native OPEN is not on the reclaimed side",
            sfp_id=sfp["id"],
            direction=direction,
            open=str(next_bar.open),
            level=str(level),
            passed=False,
        )
    return _source_fact(
        "SFP_NEXT_OPEN_CONFIRMATION",
        next_bar.end,
        "Next native OPEN remains on reclaimed side; archived OPEN becomes conservatively knowable at bar completion",
        sfp_id=sfp["id"],
        direction=direction,
        open=str(next_bar.open),
        level=str(level),
        actual_open_time=next_bar.start,
        passed=True,
    )


def first_pattern_invalidation(index: Any, sfp: dict[str, Any], decision_at: int) -> dict[str, Any] | None:
    """N11_BODY_TF: strict completed pattern-TF body close beyond the SFP raid extreme."""
    payload = sfp["payload"]
    direction = payload["direction"]
    extreme = Decimal(str(payload["low"] if direction == "LONG" else payload["high"]))
    for bar in index.bars:
        if bar.start < sfp["known_at"] or bar.end > decision_at:
            continue
        invalid = bar.close < extreme if direction == "LONG" else bar.close > extreme
        if invalid:
            return _source_fact(
                "SFP_PATTERN_INVALIDATION",
                bar.end,
                "Completed pattern-TF close strictly beyond raid extreme",
                sfp_id=sfp["id"],
                direction=direction,
                extreme=str(extreme),
                close=str(bar.close),
                bar_start=bar.start,
            )
    return None


def _latest_opposite_m15_swing(m15_index: Any, direction: str, at: int) -> dict[str, Any] | None:
    wanted = "HIGH" if direction == "LONG" else "LOW"
    candidates = [
        obj
        for obj in m15_index.by_id.values()
        if obj.get("kind") == "swing"
        and obj.get("source_validated") is True
        and obj.get("known_at", at + 1) <= at
        and obj.get("payload", {}).get("side") == wanted
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda obj: (obj["known_at"], obj["id"]))


def first_m15_bos_after_sfp(
    m15_index: Any,
    sfp: dict[str, Any],
    decision_at: int,
    invalidation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """U3: completed SFP -> M15 BOS. No arbitrary time window is imposed."""
    if sfp.get("tf") == 15:
        return None
    direction = sfp["payload"]["direction"]
    level = _latest_opposite_m15_swing(m15_index, direction, sfp["known_at"])
    if level is None:
        return None
    price = Decimal(str(level["payload"]["price"]))
    invalid_at = invalidation["known_at"] if invalidation else None
    for bar in m15_index.bars:
        if bar.start < sfp["known_at"] or bar.end > decision_at or level["known_at"] > bar.start:
            continue
        if invalid_at is not None and bar.end >= invalid_at:
            return None
        passed = bar.close > price if direction == "LONG" else bar.close < price
        if passed:
            return _source_fact(
                "M15_BOS_AFTER_SFP",
                bar.end,
                "Completed M15 body close beyond the latest already-known opposite structural swing",
                sfp_id=sfp["id"],
                direction=direction,
                protected_swing_id=level["id"],
                protected_price=str(price),
                close=str(bar.close),
                tf=15,
                source_rule_ids=["S_SFP_REFINE", "S_BOS"],
            )
    return None


def first_new_source_poi(m15_index: Any, bos: dict[str, Any], direction: str, decision_at: int):
    """Return first new source-valid POI event after BOS without retrospective best-POI selection."""
    candidates = [
        obj
        for obj in m15_index.by_id.values()
        if obj.get("source_validated") is True
        and obj.get("kind") in ("FVG", "refined_POI", "breaker")
        and bos["known_at"] <= obj.get("known_at", decision_at + 1) <= decision_at
        and obj.get("payload", {}).get("direction") == direction
        and {"low", "high"} <= set(obj.get("payload", {}))
    ]
    if not candidates:
        return None, "WAIT_NEW_POI_AFTER_BOS"
    first_at = min(obj["known_at"] for obj in candidates)
    first = sorted((obj for obj in candidates if obj["known_at"] == first_at), key=lambda obj: obj["id"])
    zones = {(str(obj["payload"]["low"]), str(obj["payload"]["high"])) for obj in first}
    if len(zones) != 1:
        return None, "WAIT_NONUNIQUE_NEW_POI"
    selected = deepcopy(first[0])
    selected["source_validated"] = True
    selected["source_attestation"] = {
        "known_at": first_at,
        "completed_at": first_at,
        "bos_id": bos["id"],
        "equivalent_source_ids": [obj["id"] for obj in first],
        "evidence": "First causal matching source-valid POI event after M15 BOS; no future ranking",
    }
    _no_outcomes(selected)
    return selected, None


def resolve_sfp_chain(parent_index: Any, m15_index: Any, sfp_id: str, decision_at: int) -> dict[str, Any]:
    """Resolve SFP source chain through U3 entry-POI evidence, without execution/P&L."""
    raw = parent_index.by_id.get(sfp_id)
    if raw is None:
        return {"state": "OBJECTIVE_FAIL", "reason": "SFP_NOT_FOUND", "trade_entry_allowed": False}
    sfp = validate_raw_sfp(parent_index, raw, decision_at)
    if sfp is None:
        return {"state": "OBJECTIVE_FAIL", "reason": "SFP_LITERAL_FORMATION_FAIL", "trade_entry_allowed": False}
    if sfp.get("tf") == 15:
        return {
            "state": "UNKNOWN",
            "reason": "WAIT_NO_AVAILABLE_LOWER_TF",
            "sfp_id": sfp_id,
            "trade_entry_allowed": False,
        }
    next_open = next_native_open_confirmation(parent_index, sfp, decision_at)
    if next_open is None:
        return {"state": "UNKNOWN", "reason": "WAIT_SFP_NEXT_OPEN", "sfp_id": sfp_id, "trade_entry_allowed": False}
    if not next_open.get("passed"):
        return {"state": "OBJECTIVE_FAIL", "reason": "SFP_NEXT_OPEN_FAIL", "sfp_id": sfp_id, "trade_entry_allowed": False}
    invalidation = first_pattern_invalidation(parent_index, sfp, decision_at)
    bos = first_m15_bos_after_sfp(m15_index, sfp, decision_at, invalidation)
    if bos is None:
        return {
            "state": "UNKNOWN" if invalidation is None else "OBJECTIVE_FAIL",
            "reason": "WAIT_SFP_LOWER_BOS_ENTRY_SEARCH" if invalidation is None else "SFP_INVALIDATED_BEFORE_M15_BOS",
            "sfp_id": sfp_id,
            "invalidation_id": invalidation["id"] if invalidation else None,
            "trade_entry_allowed": False,
        }
    poi, reason = first_new_source_poi(m15_index, bos, sfp["payload"]["direction"], decision_at)
    if poi is None:
        return {
            "state": "UNKNOWN",
            "reason": reason,
            "sfp_id": sfp_id,
            "bos_id": bos["id"],
            "trade_entry_allowed": False,
        }
    result = {
        "state": "SOURCE_CHAIN_READY",
        "branch": "SFP",
        "direction": sfp["payload"]["direction"],
        "setup_tf": sfp["tf"],
        "decision_at": max(next_open["known_at"], bos["known_at"], poi["known_at"]),
        "sfp_id": sfp["id"],
        "liquidity_level_id": sfp["payload"]["level_id"],
        "next_open_confirmation_id": next_open["id"],
        "m15_bos_id": bos["id"],
        "entry_poi_id": poi["id"],
        "entry_poi": {
            "low": poi["payload"]["low"],
            "high": poi["payload"]["high"],
            "kind": poi["kind"],
        },
        "source_rule_ids": [
            "S_SFP_FORMATION",
            "S_SFP_TF",
            "S_LIQUIDITY_CONTEXT",
            "S_SFP_REFINE",
            "S_BOS",
        ],
        "user_resolution_ids": ["U3", "U4"],
        "trade_entry_allowed": False,
    }
    _no_outcomes(result)
    return result
