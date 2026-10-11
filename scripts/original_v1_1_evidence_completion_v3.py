"""Causal completion objects and outcome-free historical source readiness."""

from __future__ import annotations

import heapq
from bisect import bisect_left, bisect_right
from collections import Counter
from decimal import Decimal

from original_strategy_executable_profile_v1 import digest
from original_v1_1_evidence_adapter_v2 import (
    BRANCH_CONCEPTS,
    QUALITATIVE,
    build_case,
    no_outcomes,
)
from original_v1_1_objective_geometry_v2 import GeometryIndex, object_record
from original_v1_1_source_plan_geometry_v3 import assess_source, source_stop

COMMON = (
    "adverse_liquidity",
    "protected_endpoints",
    "contextual_poi_relation",
    "inventory_completeness",
    "zone_first_test",
    "sl_off_liquidity",
)
ADDED_QUESTIONS = {
    "canonical_source_context": ["S_STRUCTURE", "S_POI"],
    "source_confirmation": ["S_BOS", "S_CONF"],
    "source_entry_poi": ["S_PLAN", "S_POI"],
    "source_fta_inventory": ["S_FTA"],
}


def normalize_object(obj, *, parent_objects):
    payload = obj["payload"]
    parents = {
        v for k, v in payload.items() if k.endswith("_id") and isinstance(v, str)
    }
    parents.update(payload.get("swings", []))
    # Only explicit object links; source candle timestamps are not arbitrary parent IDs.
    for parent_id in parents:
        parent = parent_objects.get(parent_id)
        if parent is None or parent["known_at"] > obj["known_at"]:
            raise ValueError("Missing/future canonical parent")
    return {
        **obj,
        "canonical_id": obj["id"],
        "parent_ids": sorted(parents),
        "direction": payload.get("direction", "UNKNOWN"),
        "validity_state": "SOURCE_PRIMITIVE_VALIDATED"
        if obj["source_validated"]
        else "SOURCE_RELATION_UNKNOWN",
        "contextual_validity": "UNKNOWN",
        "consumed_source_state": "UNKNOWN",
    }


class TouchIndex:
    """Find first observed OHLC zone intersection, never a fill/eligible source test.

    Segment pruning uses exact extrema; no distance/horizon threshold. Returned
    records are exposed only after the intersecting native candle completed.
    """

    def __init__(self, bars):
        self.bars = bars
        self.ends = [bar.end for bar in bars]
        self.size = 1
        while self.size < len(bars):
            self.size *= 2
        self.highs = [Decimal("-Infinity")] * (2 * self.size)
        self.lows = [Decimal("Infinity")] * (2 * self.size)
        for i, bar in enumerate(bars):
            self.highs[self.size + i] = bar.high
            self.lows[self.size + i] = bar.low
        for i in range(self.size - 1, 0, -1):
            self.highs[i] = max(self.highs[2 * i], self.highs[2 * i + 1])
            self.lows[i] = min(self.lows[2 * i], self.lows[2 * i + 1])

    def first(self, born_at, low, high, cutoff):
        start, stop = bisect_right(self.ends, born_at), bisect_right(self.ends, cutoff)

        def search(node, left, right):
            if (
                right <= start
                or left >= stop
                or self.highs[node] < low
                or self.lows[node] > high
            ):
                return None
            if right - left == 1:
                return left if left < len(self.bars) else None
            middle = (left + right) // 2
            result = search(2 * node, left, middle)
            return result if result is not None else search(2 * node + 1, middle, right)

        i = search(1, 0, self.size)
        if i is None:
            return None
        bar = self.bars[i]
        return {
            "observed_bar_start": bar.start,
            "known_at": bar.end,
            "completed_at": bar.end,
            "source_eligible_test": "UNKNOWN",
            "intrabar_interaction_order": "UNOBSERVED",
            "evidence": "First post-birth completed OHLC intersecting this candidate zone; not a source test or fill",
        }


class CompletionIndex:
    def __init__(self, symbol, tf, bars):
        self.geometry = GeometryIndex(symbol, tf, bars)
        self.bars, self.symbol, self.tf = bars, symbol, tf
        self.touch = TouchIndex(bars)
        self.objects = dict(self.geometry.by_id)
        self._raw_body_crosses()
        self._first_geometric_touches()
        self.ordered = sorted(
            (
                normalize_object(o, parent_objects=self.objects)
                for o in self.objects.values()
            ),
            key=lambda o: (o["known_at"], o["id"]),
        )
        self.known = [o["known_at"] for o in self.ordered]
        self.prefix_hashes, self.kind_counts = [], []
        cumulative, prefix = Counter(), "0" * 64
        for obj in self.ordered:
            prefix = digest(["CAUSAL_OBJECT_PREFIX_v3", prefix, obj["id"]])
            cumulative[obj["kind"]] += 1
            self.prefix_hashes.append(prefix)
            self.kind_counts.append(dict(cumulative))

    def add(self, kind, at, payload, rules):
        obj = object_record(kind, self.symbol, self.tf, at, payload, rules)
        self.objects[obj["id"]] = obj
        return obj

    def _raw_body_crosses(self):
        highs, lows = [], []
        for bar in self.bars:
            for pending, broken in (
                (highs, lambda price, close=bar.close: price < close),
                (lows, lambda price, close=bar.close: -price > close),
            ):
                while pending and broken(pending[0][0]):
                    _price, swing_id = heapq.heappop(pending)
                    swing = self.objects[swing_id]
                    if swing["known_at"] > bar.start:
                        raise ValueError("Body crossing used future swing")
                    self.add(
                        "raw_body_cross",
                        bar.end,
                        {
                            "level_id": swing_id,
                            "bar_start": bar.start,
                            "close": str(bar.close),
                            "price": swing["payload"]["price"],
                            "direction": "LONG"
                            if swing["payload"]["side"] == "HIGH"
                            else "SHORT",
                            "BOS_or_CONF_source_role": "UNKNOWN",
                            "protected_endpoint": "UNKNOWN",
                        },
                        ["S_BOS", "S_CONF"],
                    )
            for swing in self.geometry.event_objects(bar.end, "swing"):
                price = Decimal(swing["payload"]["price"])
                heapq.heappush(
                    highs if swing["payload"]["side"] == "HIGH" else lows,
                    (
                        price if swing["payload"]["side"] == "HIGH" else -price,
                        swing["id"],
                    ),
                )

    def _first_geometric_touches(self):
        # Same physical raw POI is a shared object for OB/STB interpretations.
        # Only this raw touch is computed, never an automatically eligible test.
        for poi in self.geometry.by_id.values():
            if poi["kind"] != "POI":
                continue
            p = poi["payload"]
            touch = self.touch.first(
                poi["known_at"],
                Decimal(p["low"]),
                Decimal(p["high"]),
                self.bars[-1].end,
            )
            if touch:
                self.add(
                    "raw_first_zone_touch",
                    touch["known_at"],
                    {
                        "poi_id": poi["id"],
                        "direction": p["direction"],
                        "low": p["low"],
                        "high": p["high"],
                        "born_at": poi["known_at"],
                        **{
                            k: touch[k]
                            for k in (
                                "observed_bar_start",
                                "source_eligible_test",
                                "intrabar_interaction_order",
                            )
                        },
                    },
                    ["S_OB_FIRST_TEST"],
                )

    def prefix(self, at):
        count = bisect_right(self.known, at)
        candles = bisect_right(self.geometry.ends, at)
        return {
            "symbol": self.symbol,
            "tf": self.tf,
            "decision_cutoff": at,
            "objects": count,
            "object_prefix_sha256": self.prefix_hashes[count - 1]
            if count
            else "0" * 64,
            "kind_counts": self.kind_counts[count - 1] if count else {},
            "completed_candles": candles,
            "last_completed_at": self.geometry.ends[candles - 1] if candles else None,
            "objects_file": f"CAUSAL_OBJECTS/{self.symbol}_{self.tf}.jsonl.gz",
            "blinded_candles_file": f"docs/original_v1_1_evidence_adapter_v2/BLINDED_QUALITATIVE_ANNOTATION_PACK/candles/{self.symbol}_{self.tf}.jsonl.gz",
        }

    def at(self, at, kind=None):
        return [
            o
            for o in self.ordered[
                bisect_left(self.known, at) : bisect_right(self.known, at)
            ]
            if kind is None or o["kind"] == kind
        ]


def questions_for(branch, *, stop_complete=False, eq_level=False):
    questions = set(BRANCH_CONCEPTS[branch]) | set(COMMON) | set(ADDED_QUESTIONS)
    if not stop_complete:
        questions.add("source_stop_anchor")
    if branch.startswith("RANGE"):
        questions.add("selected_range")
    if eq_level:
        questions.add("reasonable_tilt")
    return sorted(questions)


def formation_objects(raw, index):
    geo = index.geometry
    at, direction, branch = (
        raw.get("formation_at", raw["decision_at"]),
        raw["direction"],
        raw["branch"],
    )
    kind = {"SFP": "SFP", "OB_CONSERVATIVE": "OB", "STB_BTS": "STB"}.get(branch)
    if kind:
        return [
            o
            for o in geo.event_objects(at, kind)
            if o["payload"]["direction"] == direction
        ]
    if branch == "BREAKER":
        obj = geo.ob_alias.get(raw.get("anchor"))
        return [geo.by_id[obj]] if obj else []
    result = []
    if branch.startswith("RANGE") and isinstance(raw.get("anchor"), list):
        for side, known in zip(("LOW", "HIGH"), raw["anchor"], strict=True):
            oid = geo.references[side].get(known)
            if oid:
                result.append(geo.by_id[oid])
    return result


def inspect_candidate(raw, indices, metadata, tree, *, mode="BACKTEST"):
    no_outcomes(raw)
    index = indices[raw["symbol"]][raw["setup_tf"]]
    at = raw["decision_at"]
    branch = raw["branch"]
    geo = index.geometry
    case = build_case(raw, geo, metadata, mode=mode)
    # Frozen build_case returns partial source geometry; metadata absence never
    # terminates this new analytical assessment.
    answer = assess_source(case, tree=tree, required_qualitative=COMMON)
    origins = formation_objects(raw, index)
    stop = source_stop(case)
    eq = any(o["payload"].get("pair_classification") in ("EQH", "EQL") for o in origins)
    questions = questions_for(branch, stop_complete=stop is not None, eq_level=eq)
    object_ids = {o["id"] for o in origins}
    for o in origins:
        if "level_id" in o["payload"]:
            object_ids.add(o["payload"]["level_id"])
    snapshot = {
        str(tf): frame.prefix(at) for tf, frame in indices[raw["symbol"]].items()
    }
    conditional_stop = None
    if (
        branch != "SFP"
        and len(origins) == 1
        and branch in ("OB_CONSERVATIVE", "STB_BTS")
    ):
        p = origins[0]["payload"]
        conditional_stop = {
            "object_id": origins[0]["id"],
            "source_candle_low": p["low"],
            "source_candle_high": p["high"],
            "unique_observed_extreme": p["low"]
            if raw["direction"] == "LONG"
            else p["high"],
            "state": "CONDITIONAL_ON_SOURCE_FORMATION_VALIDITY",
            "blocked_by_metadata": False,
        }
    elif branch.startswith("RANGE") and len(origins) == 2:
        conditional_stop = {
            "boundary_object_ids": [o["id"] for o in origins],
            "raw_deviation_low": raw["bar"]["low"],
            "raw_deviation_high": raw["bar"]["high"],
            "state": "CONDITIONAL_ON_SOURCE_SELECTED_RANGE",
            "blocked_by_metadata": False,
        }
    conditional_formation = {
        "source_object_ids": sorted(object_ids),
        "canonical_source_context": "UNKNOWN_CONTEXT_UNPROVEN",
        "source_valid_contexts": 0,
        "physical_idea_id": None,
        "setup_id": None,
        "reason": "Strict swings/FVG/raw raid geometry do not select protected source endpoints/context or contextual POI",
    }
    observed = []
    formation_at = raw.get("formation_at", at)
    for event in index.at(formation_at, "raw_body_cross"):
        observed.append(event["id"])
    if branch in ("SFP", "OB_CONSERVATIVE") and raw["setup_tf"] > 15:
        lower = indices[raw["symbol"]][15]
        for event in lower.ordered[
            bisect_right(lower.known, formation_at) : bisect_right(lower.known, at)
        ]:
            if event["kind"] in ("raw_body_cross", "FVG", "formation", "POI"):
                observed.append(event["id"])
    object_ids.update(observed)
    # These are conditional confirmations only; raw crosses are not source BOS/CONF.
    confirmation = {
        "branch": branch,
        "state": "QUALITATIVE_REQUIRED",
        "observed_conditional_object_ids": sorted(observed),
        "required_sequence": {
            "SFP": "completed SFP + observed next OPEN -> causal M15 BOS -> source entry search",
            "OB_CONSERVATIVE": "reaction -> M15 BOS -> new SOURCE POI",
            "BREAKER": "prior SOURCE OB -> whole impulse break -> new structure confirmation",
            "STB_BTS": "raid/engulf -> SOURCE BOS/CONF",
            "RANGE_CONSERVATIVE": "selected clear range -> deviation/reclaim -> return/retest",
            "RANGE_RETURN_CHOCH": "selected clear range -> return CHOCH -> return/retest",
        }[branch],
        "missing": "Protected/contextual selection and branch-specific source relationship not attested",
    }
    first_touches = []
    for o in geo.event_objects(formation_at, "POI"):
        if o["payload"]["direction"] != raw["direction"]:
            continue
        touch = index.touch.first(
            o["known_at"],
            Decimal(o["payload"]["low"]),
            Decimal(o["payload"]["high"]),
            at,
        )
        first_touches.append(
            {
                "poi_id": o["id"],
                "born_at": o["known_at"],
                "first_geometric_touch": touch,
                "first_eligible_source_test": "UNKNOWN",
                "consumed_source_at": None,
            }
        )
    counts = {tf: view["kind_counts"] for tf, view in snapshot.items()}
    # All contextual classifications stay UNKNOWN. Complete raw enumeration is not
    # proof of complete SOURCE inventory or absence of an adverse pool.
    inventory = {
        "state": "QUALITATIVE_REQUIRED",
        "inventory_complete_for_SOURCE_prefix": False,
        "geometrically_valid_FVGs_across_four_TFs": sum(
            c.get("FVG", 0) for c in counts.values()
        ),
        "opposing_contextual_source_POIs": 0,
        "selected_source_FTA": None,
        "first_test_state": "UNKNOWN",
        "prefixes": snapshot,
    }
    result = {
        k: raw[k]
        for k in (
            "candidate_id",
            "symbol",
            "branch",
            "direction",
            "setup_tf",
            "decision_at",
            "event",
        )
    }
    result.update(
        formation_at=formation_at,
        **answer,
        canonical_source_context=conditional_formation,
        source_confirmation=confirmation,
        source_entry_poi={"state": "UNKNOWN_SOURCE_ENTRY_POI", "resolved_id": None},
        conditional_stop_geometry=conditional_stop,
        source_fta_inventory=inventory,
        raw_first_test_observations=first_touches,
        relevant_object_ids=sorted(object_ids),
        required_questions=questions,
        qualitative_answers={q: "UNKNOWN" for q in questions},
        historical_annotations_loaded=0,
        source_component_counts={
            "SOURCE_STOP_ANCHOR_COMPLETE": int(stop is not None),
            "CANONICAL_SOURCE_CONTEXT_COMPLETE": 0,
            "SOURCE_CONFIRMATION_COMPLETE": 0,
            "SOURCE_ENTRY_POI_COMPLETE": 0,
            "SOURCE_FTA_COMPLETE": 0,
            "SOURCE_FIRST_TEST_COMPLETE": 0,
        },
        evidence_complete=False,
        metadata_verified=False,
        execution_metadata="UNKNOWN_PARALLEL_BLOCKER",
    )
    no_outcomes(result)
    return result


def annotation_signature(row):
    no_outcomes(row)
    context = row["canonical_source_context"]
    signature = {
        "symbol": row["symbol"],
        "direction": row["direction"],
        "branch": row["branch"],
        "setup_tf": row["setup_tf"],
        "decision_cutoff": row["decision_at"],
        "physical_idea_id": context["physical_idea_id"],
        "setup_id": context["setup_id"],
        "context_object_ids": context["source_object_ids"],
        "relevant_object_ids": row["relevant_object_ids"],
        "question_set": row["required_questions"],
        "source_stop_anchor": row["source_stop_anchor"],
        "visible_prefixes": row["source_fta_inventory"]["prefixes"],
        "source_confirmation": row["source_confirmation"],
        "first_test": row["raw_first_test_observations"],
    }
    # Missing identities never establish equivalence. Do not merge unrelated nulls.
    if signature["physical_idea_id"] is None or signature["setup_id"] is None:
        signature["unresolved_identity_singleton"] = row["candidate_id"]
    return signature


def annotation_unit(rows):
    if not rows:
        raise ValueError("Empty annotation unit")
    signatures = [annotation_signature(row) for row in rows]
    if any(signature != signatures[0] for signature in signatures[1:]):
        raise ValueError("Materially different annotation evidence cannot be grouped")
    row = rows[0]
    signature = signatures[0]
    unit_id = digest(["ANNOTATION_UNIT_v3", signature])
    required = [
        {
            "concept": q,
            "source_rule_ids": QUALITATIVE.get(q, ADDED_QUESTIONS.get(q)),
            "state": "UNKNOWN",
            "reason": "No source-validated contextual selection/discretionary annotation supplied",
        }
        for q in row["required_questions"]
    ]
    if any(not question["source_rule_ids"] for question in required):
        raise ValueError("Question lacks SOURCE citation")
    return {
        "annotation_unit_id": unit_id,
        "candidate_ids": sorted(r["candidate_id"] for r in rows),
        "physical_idea_id": signature["physical_idea_id"],
        "setup_id": signature["setup_id"],
        "context_ids": signature["context_object_ids"],
        "decision_cutoff": row["decision_at"],
        "symbol": row["symbol"],
        "direction": row["direction"],
        "branch": row["branch"],
        "setup_tf": row["setup_tf"],
        "required_questions": required,
        "material_signature_sha256": digest(signature),
        "why_safe_to_group": "Singleton: source identity/equivalence unproven; nulls do not establish equivalence"
        if len(rows) == 1
        else "Every material field, question set and visible source prefix byte-identical; proven physical/setup identity",
        "blinded_prefixes": row["source_fta_inventory"]["prefixes"],
        "trade_entry_allowed": False,
    }
