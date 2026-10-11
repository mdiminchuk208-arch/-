"""Tick-independent SOURCE evidence assessment, never SOURCE_ALLOW or execution.

Uses frozen pure source predicates. No substitute metadata/tick is injected into
frozen evaluate. Symbolic downstream rounding stays blocked separately.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache

from original_strategy_executable_profile_v1 import (
    ACTIVE,
    SPEC,
    UNIVERSE,
    atr14,
    causal,
    digest,
    encode,
    fact,
    identity,
    liquidity_decision,
    load_tree,
    number,
    sfp_valid,
    zone,
)
from original_strategy_spec_contract import predicate
from original_v1_1_evidence_adapter_v2 import BRANCH_CONCEPTS, no_outcomes

READY = "SOURCE_READY_EXCEPT_EXECUTION_METADATA"
STATUSES = (
    "OBJECTIVE_SOURCE_FAIL",
    "WAIT_NO_AVAILABLE_LOWER_TF",
    "QUALITATIVE_FAIL",
    "QUALITATIVE_UNKNOWN",
    "OTHER_SOURCE_WAIT",
    READY,
)
STOP_KINDS = {
    "OB_CONSERVATIVE": "SOURCE_OB_EXTREME",
    "BREAKER": "RAID_IMPULSE_EXTREME",
    "SFP": "SFP_PATTERN_EXTREME",
    "STB_BTS": "MANIPULATION_RAID_EXTREME",
    "RANGE_CONSERVATIVE": "DEVIATION_INVALIDATION_EXTREME",
    "RANGE_RETURN_CHOCH": "DEVIATION_INVALIDATION_EXTREME",
}
EXTRA = {
    "SFP": ["ltf_bos_source_entry"],
    "OB_CONSERVATIVE": [],
    "BREAKER": ["breaker_confirmation"],
    "STB_BTS": [],
    "RANGE_CONSERVATIVE": ["range_reclaim_retest"],
    "RANGE_RETURN_CHOCH": ["range_reclaim_retest"],
}


@lru_cache(maxsize=1)
def source_categories():
    registry = json.loads(
        (SPEC / "original_strategy_rule_registry_v1_1.json").read_text()
    )
    return {r["rule_id"]: r["category"] for r in registry["rules"]}


def source_entry(case):
    bounds = zone(case.get("entry_poi"), case)
    if bounds is None:
        return None
    low, high = bounds
    price = (
        (low + high) / 2
        if case["branch"] == "STB_BTS"
        else (high if case["direction"] == "LONG" else low)
    )
    return {
        "poi_id": case["entry_poi"]["id"],
        "unrounded_reference": encode(price),
        "construction": "SOURCE_MIDPOINT"
        if case["branch"] == "STB_BTS"
        else "SOURCE_PROXIMAL_EDGE",
        "known_at": case["entry_poi"]["known_at"],
        "tick_rounded_entry_price": "BLOCKED_EXECUTION_METADATA",
    }


def source_stop(case):
    anchor = case.get("stop_anchor")
    if (
        not causal(anchor, case)
        or anchor.get("source_validated") is not True
        or anchor.get("unique") is not True
        or anchor.get("kind") != STOP_KINDS[case["branch"]]
    ):
        return None
    raw = number(anchor["price"])
    long = case["direction"] == "LONG"
    result = {
        "kind": anchor["kind"],
        "source_extreme": encode(raw),
        "known_at": anchor["known_at"],
        "fixed_initial_source_stop": True,
        "tick_rounded_stop_price": "BLOCKED_EXECUTION_METADATA",
    }
    if case["branch"] == "SFP":
        raid = case.get("sfp", {}).get("raid")
        if not causal(raid, case) or raw != number(raid["low" if long else "high"]):
            return None
        atr = atr14(case)
        if atr is None:
            return None
        result.update(
            atr_sma14=encode(atr),
            unrounded_reference=encode(raw - atr if long else raw + atr),
            construction="SFP_EXTREME_MINUS_ATR" if long else "SFP_EXTREME_PLUS_ATR",
            normalization_ids=["N11_ATR_SMA14"],
        )
    else:
        bounds = zone(case.get("source_defining_zone"), case)
        if bounds is None or raw != bounds[0 if long else 1]:
            return None
        result.update(
            unrounded_reference=encode(raw),
            construction="STRICTLY_BEYOND_SOURCE_EXTREME",
            strict_side="BELOW" if long else "ABOVE",
            normalization_ids=["N11_STOP_TICK"],
        )
    result["expression_id"] = digest(
        [
            "SOURCE_STOP_EXPRESSION_v3",
            case["branch"],
            case["direction"],
            result["source_extreme"],
            result["construction"],
            result.get("atr_sma14"),
        ]
    )
    return result


def source_target(case, entry):
    long = case["direction"] == "LONG"
    entry = Decimal(entry["unrounded_reference"])
    if case["branch"].startswith("RANGE"):
        boundary = case.get("range_exit")
        if (
            not causal(boundary, case)
            or boundary.get("unique") is not True
            or boundary.get("source_validated") is not True
        ):
            return None, "UNKNOWN_SOURCE_RANGE_EXIT"
        low, high = number(boundary["low"]), number(boundary["high"])
        if not low < entry < high:
            return None, "UNKNOWN_SOURCE_RANGE_EXIT"
        result = {
            "kind": "SOURCE_RANGE_EXIT_ZONE",
            "zone_id": boundary["id"],
            "low": encode(low),
            "high": encode(high),
            "side": "INSIDE_UPPER_BOUNDARY" if long else "INSIDE_LOWER_BOUNDARY",
            "fractions_same_zone": ["0.8", "0.2"],
            "known_at": boundary["known_at"],
        }
        fta = boundary.get("source_exit_poi")
        if fta is not None:
            bounds = zone(fta, case)
            if (
                bounds is None
                or fta.get("contextual") is not True
                or fta.get("opposing") is not True
            ):
                return None, "UNKNOWN_SOURCE_RANGE_EXIT"
            raw = bounds[0 if long else 1]
            if not (raw > entry if long else raw < entry):
                return None, "UNKNOWN_SOURCE_RANGE_EXIT"
            result["optional_source_exit_poi_id"] = fta["id"]
            result["symbolic_target"] = (
                "MIN(INSIDE_UPPER_BOUNDARY, FTA_PROXIMAL)"
                if long
                else "MAX(INSIDE_LOWER_BOUNDARY, FTA_PROXIMAL)"
            )
        result["tick_rounded_target_price"] = "BLOCKED_EXECUTION_METADATA"
        return result, None
    inventory = case.get("contextual_poi_inventory")
    if (
        not causal(inventory, case)
        or inventory.get("complete_for_known_prefix") is not True
    ):
        return None, "UNKNOWN_FTA_INVENTORY_COMPLETENESS"
    candidates = []
    for poi in case.get("contextual_pois", []):
        if type(poi.get("known_at")) is int and poi["known_at"] > case["decision_at"]:
            continue
        if not causal(poi, case):
            return None, "UNKNOWN_CONTEXTUAL_FTA_RELATION"
        if poi.get("opposing") is False or poi.get("contextual") is False:
            continue
        bounds = zone(poi, case)
        if (
            bounds is None
            or poi.get("contextual") is not True
            or poi.get("opposing") is not True
        ):
            return None, "UNKNOWN_CONTEXTUAL_FTA_RELATION"
        low, high = bounds
        if low <= entry <= high:
            return None, "UNKNOWN_CONTEXTUAL_FTA_RELATION"
        if (long and low > entry) or (not long and high < entry):
            candidates.append((low if long else high, poi))
    if not candidates:
        return None, "UNKNOWN_NO_SOURCE_FTA"
    edge = min(p for p, _ in candidates) if long else max(p for p, _ in candidates)
    selected = [poi for p, poi in candidates if p == edge]
    if len({p["id"] for p in selected}) != 1:
        return None, "UNKNOWN_FTA_NONUNIQUE"
    poi = selected[0]
    return {
        "kind": "FULL_CONTEXTUAL_FTA_EXIT",
        "poi_id": poi["id"],
        "tf": poi.get("tf"),
        "low": poi["low"],
        "high": poi["high"],
        "unrounded_proximal_edge": encode(edge),
        "known_at": poi["known_at"],
        "tick_rounded_target_price": "BLOCKED_EXECUTION_METADATA",
    }, None


def unique_source_objects(objects, *, at, reason):
    selected = {
        o["id"]: o
        for o in objects
        if o.get("source_validated") is True
        and type(o.get("known_at")) is int
        and o["known_at"] <= at
    }
    if not selected:
        return None, reason + "_UNPROVEN"
    if len(selected) > 1:
        return None, reason + "_NONUNIQUE"
    return next(iter(selected.values())), None


def branch_confirmation(case):
    """Branch-specific source link proof; raw body crosses cannot satisfy it.

    Formation/context attestations must already have passed the frozen blinded
    annotation contract. This checks relationships, not discretionary labels.
    """
    branch = case["branch"]
    if branch in ("SFP", "OB_CONSERVATIVE"):
        reaction, bos, poi = (case.get(k) for k in ("reaction", "bos", "entry_poi"))
        if not all(
            causal(o, case) and o.get("source_validated") is True
            for o in (reaction, bos, poi)
        ):
            return None
        if (
            bos.get("kind") != "BOS"
            or bos.get("tf") != 15
            or not reaction["known_at"] <= bos["known_at"]
        ):
            return None
        if branch == "SFP":
            opening = case.get("sfp", {}).get("next_open")
            if not opening or reaction["known_at"] < opening["known_at"]:
                return None
        formation = poi.get("formation_known_at")
        if (
            type(formation) is not int
            or not bos["known_at"] <= formation <= poi["known_at"]
        ):
            return None
        if poi.get("confirmation_id") != bos.get("id") or not bos.get("id"):
            return None
        return {
            "state": "COMPLETE",
            "branch": branch,
            "confirmation_id": bos["id"],
            "entry_poi_id": poi["id"],
            "known_at": poi["known_at"],
        }
    formation, confirmation = (
        case.get(k) for k in ("source_formation", "source_confirmation")
    )
    if not all(
        causal(o, case) and o.get("source_validated") is True and o.get("id")
        for o in (formation, confirmation)
    ):
        return None
    fp, cp = formation.get("payload", {}), confirmation.get("payload", {})
    if not formation["known_at"] <= confirmation["known_at"]:
        return None
    if branch == "BREAKER":
        prior = case.get("source_parent_ob")
        if (
            not causal(prior, case)
            or prior.get("source_validated") is not True
            or prior.get("kind") != "OB"
        ):
            return None
        if formation.get("kind") != "breaker" or fp.get("prior_OB_id") != prior.get(
            "id"
        ):
            return None
        if (
            cp.get("formation_id") != formation["id"]
            or confirmation.get("kind") != "confirmation"
        ):
            return None
    elif branch == "STB_BTS":
        if formation.get("kind") != "STB" or confirmation.get("kind") not in (
            "BOS",
            "confirmation",
        ):
            return None
        if cp.get("formation_id") != formation["id"] or not cp.get("structure_id"):
            return None
    else:
        dealing = case.get("source_selected_range")
        if (
            not causal(dealing, case)
            or dealing.get("source_validated") is not True
            or dealing.get("kind") != "range"
        ):
            return None
        if fp.get("range_id") != dealing.get("id") or cp.get("range_id") != dealing.get(
            "id"
        ):
            return None
        if (
            cp.get("deviation_id") != formation["id"]
            or cp.get("event") != "range_boundary_return_retest"
        ):
            return None
        if (
            branch == "RANGE_RETURN_CHOCH"
            and fact(case, "return_choch_zone") is not True
        ):
            return None
    return {
        "state": "COMPLETE",
        "branch": branch,
        "formation_id": formation["id"],
        "confirmation_id": confirmation["id"],
        "known_at": confirmation["known_at"],
    }


def assess_source(case, *, tree=None, required_qualitative=()):
    """Evaluate all evidence without short-circuiting on unknown exchange metadata.

    A ready result is an analytical source-evidence status, not a frozen executable
    ALLOW. Exact rounding-dependent geometry/clearance must still be checked by
    the unchanged executable after real metadata is recovered.
    """
    no_outcomes(case)
    if (
        case.get("mode") not in ("BACKTEST", "SHADOW")
        or case.get("event") not in ("OPEN", "CLOSE")
        or case.get("direction") not in ("LONG", "SHORT")
        or type(case.get("decision_at")) is not int
    ):
        raise ValueError("Explicit causal offline event required")
    branch = case.get("branch")
    if branch not in ACTIVE or case.get("setup_tf") not in UNIVERSE:
        raise ValueError("Inactive/outside-universe input must be handled separately")
    tree = tree or load_tree()
    coverage_wait = branch in ("SFP", "OB_CONSERVATIVE") and (
        case.get("trigger_tf") != 15 or 15 >= case["setup_tf"]
    )
    trace, objective_fail, qualitative_fail, qualitative_unknown, gaps = (
        [],
        [],
        [],
        [],
        [],
    )
    if coverage_wait:
        gaps.append("WAIT_NO_AVAILABLE_LOWER_TF")
    for node in tree["source_nodes"]:
        if node["branch_id"] != branch:
            continue
        if source_categories().get(node["rule_id"]) != "SOURCE_RULE":
            raise ValueError("Non-source rule injected into source evidence")
        name = node["predicate"]
        objective = name in (
            "sfp_geometry",
            "sfp_next_open",
            "sfp_tf",
            "conservative_tf",
        )
        if name in ("sfp_geometry", "sfp_next_open"):
            value = sfp_valid(case, next_open=name == "sfp_next_open")
        elif name in ("sfp_tf", "conservative_tf"):
            value = predicate(case, name)
        else:
            value = fact(case, name)
        trace.append(
            {
                "rule_id": node["rule_id"],
                "predicate": name,
                "value": value,
                "state": "PASS"
                if value is True
                else "FAIL"
                if value is False
                else "UNKNOWN",
            }
        )
        if value is False and name == "conservative_tf" and coverage_wait:
            gaps.append("WAIT_NO_AVAILABLE_LOWER_TF")
        elif value is False:
            (objective_fail if objective else qualitative_fail).append(name)
        elif value is None:
            (gaps if objective else qualitative_unknown).append(name)
    for name in EXTRA[branch]:
        value = fact(case, name)
        if value is False:
            qualitative_fail.append(name)
        elif value is None:
            qualitative_unknown.append(name)
    material = set(required_qualitative) | set(BRANCH_CONCEPTS[branch])
    for name in sorted(material):
        value = fact(case, name)
        if value is False:
            qualitative_fail.append(name)
        elif value is None:
            qualitative_unknown.append(name)
    confirmation_geometry = branch_confirmation(case)
    if confirmation_geometry is None:
        gaps.append("UNKNOWN_SOURCE_CONFIRMATION")
    liquidity = liquidity_decision(case)
    if liquidity not in ("PASS", "REVALIDATE_SOURCE"):
        gaps.append(liquidity)
    entry = source_entry(case)
    if entry is None:
        gaps.append("UNKNOWN_SOURCE_ENTRY_POI")
    stop = source_stop(case)
    if stop is None:
        gaps.append("UNKNOWN_SOURCE_STOP_ANCHOR")
    if entry and stop:
        stop_reference = number(stop["unrounded_reference"])
        entry_reference = number(entry["unrounded_reference"])
        if (
            stop_reference <= 0
            or (
                stop_reference > entry_reference
                if case["direction"] == "LONG"
                else stop_reference < entry_reference
            )
            or (
                stop_reference == entry_reference
                and stop["construction"] != "STRICTLY_BEYOND_SOURCE_EXTREME"
            )
        ):
            objective_fail.append("SOURCE_STOP_WRONG_SIDE")
        # Equal boundary and strictly-beyond construction is valid symbolically;
        # exact positivity/order/clearance after rounding remains execution-blocked.
    target, target_gap = (
        source_target(case, entry)
        if entry
        else (None, "UNKNOWN_SOURCE_FTA_ENTRY_UNRESOLVED")
    )
    if target_gap:
        gaps.append(target_gap)
    ids = identity(case) if entry else None
    if ids is None:
        gaps.append("UNKNOWN_CANONICAL_SOURCE_CONTEXT_AND_IDENTITY")
    if (
        case.get("source_context") is None
        or not causal(case["source_context"], case)
        or case["source_context"].get("source_validated") is not True
        or case["source_context"].get("id")
        != case.get("identity_evidence", {}).get("context", {}).get("id")
    ):
        gaps.append("UNKNOWN_CANONICAL_SOURCE_CONTEXT")
    first = case.get("zone_first_test")
    if (
        not causal(first, case)
        or first.get("value") is not True
        or first.get("source_validated") is not True
    ):
        gaps.append("WAIT_FIRST_TEST_ONLY")
    # This attests the chosen source expression/inventory, never an invented rounded quote.
    clearance = case.get("source_stop_clearance")
    if (
        not stop
        or not causal(clearance, case)
        or clearance.get("source_validated") is not True
        or clearance.get("value") is not True
        or clearance.get("expression_id") != stop["expression_id"]
    ):
        gaps.append("UNKNOWN_SOURCE_STOP_LIQUIDITY_CLEARANCE")
    # Readiness requires explicit inventory/context/endpoint declarations where needed.
    for field in ("source_context_inventory", "branch_conflict_resolution"):
        record = case.get(field)
        if (
            not causal(record, case)
            or record.get("source_validated") is not True
            or record.get("value") is not True
        ):
            gaps.append("UNKNOWN_" + field.upper())
    status = (
        "OBJECTIVE_SOURCE_FAIL"
        if objective_fail
        else "WAIT_NO_AVAILABLE_LOWER_TF"
        if coverage_wait
        else "QUALITATIVE_FAIL"
        if qualitative_fail
        else "QUALITATIVE_UNKNOWN"
        if qualitative_unknown
        else "OTHER_SOURCE_WAIT"
        if gaps
        else READY
    )
    return {
        "status": status,
        "source_rule_trace": trace,
        "objective_fail_reasons": sorted(set(objective_fail)),
        "qualitative_fail": sorted(set(qualitative_fail)),
        "qualitative_unknown": sorted(set(qualitative_unknown)),
        "source_gaps": sorted(set(gaps + qualitative_unknown)),
        "source_confirmation_geometry": confirmation_geometry,
        "source_entry_geometry": entry,
        "source_stop_anchor": stop,
        "source_exit_geometry": target,
        "source_identity": ids,
        "liquidity_decision": liquidity,
        "metadata_role": "PARALLEL_EXECUTION_BLOCKER",
        "execution_blockers": [
            "HISTORICAL_INSTRUMENT_METADATA",
            "TICK_ROUNDED_ENTRY",
            "TICK_ROUNDED_STOP",
            "TICK_ROUNDED_TARGET",
            "EXECUTABLE_QUANTITY",
        ],
        "SOURCE_ALLOW": 0,
        "SOURCE_DECISION_READY_FOR_FINANCE": 0,
        "trade_entry_allowed": False,
    }
