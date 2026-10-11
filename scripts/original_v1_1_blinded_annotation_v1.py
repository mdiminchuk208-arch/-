"""Chronological blinded source sufficiency annotation; never a fitted classifier."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from original_strategy_executable_profile_v1 import digest
from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_financial_data import ROOT, checksum, save
from original_v1_1_staged_research_common import (
    read,
    rows,
    seal,
    validate_qa,
    verify_originals,
    verify_stage,
    writer,
)
from run_original_v1_1_evidence_completion_v3 import DEST as V3

DEST = ROOT / "docs/original_v1_1_blinded_annotation_v1"
CODE = [
    "scripts/original_v1_1_staged_research_common.py",
    "scripts/original_v1_1_blinded_annotation_v1.py",
    "tests/test_original_v1_1_blinded_annotation_v1.py",
]
ANNOTATOR = "SOURCE_INPUT_SUFFICIENCY_REVIEW_v1"
BATCH_SIZE = 100
REASONS = {
    "market_context": (
        "UNKNOWN_SOURCE_CONTEXT_SELECTION",
        "Key HH/HL/LH/LL require source contextual endpoints; raw strict swings do not uniquely select them.",
    ),
    "protected_endpoints": (
        "UNKNOWN_PROTECTED_SELECTION",
        "SOURCE key/protected endpoint selection is not established by the view; no last-swing/size selector is substituted.",
    ),
    "flow_context": (
        "UNKNOWN_SOURCE_FLOW",
        "Source flow requires structural selection, raids and an untested contextual delivery POI; geometric crosses alone do not select flow.",
    ),
    "smooth_approach": (
        "UNKNOWN_SMOOTH_APPROACH",
        "Source says smooth structural approach but does not give a unique machine condition; no ATR/distance/percentage surrogate is used.",
    ),
    "clear_range": (
        "UNKNOWN_CLEAR_SOURCE_RANGE",
        "Source requires impulse-end/correction-end boundaries and midpoint reaction; last-swing bracket alone is not a uniquely selected clear range.",
    ),
    "selected_range": (
        "UNKNOWN_SELECTED_RANGE",
        "No source-selected impulse/correction endpoint pair is established; multiple raw brackets are not resolved by fitted priority.",
    ),
    "selected_impulse": (
        "UNKNOWN_SELECTED_IMPULSE",
        "Source-valid impulse endpoints are not uniquely selected; Fib/PD cannot select their own endpoints.",
    ),
    "whole_impulse": (
        "UNKNOWN_WHOLE_IMPULSE",
        "Source whole movement without chopping requires an explicit interval/new structural extreme; raw OB break is insufficient.",
    ),
    "reasonable_tilt": (
        "UNKNOWN_SOURCE_EQ_PAIR",
        "EQ orientation is conditional on a source-selected substructural pair; raw equality/proximity does not establish that pair or meaningful scope.",
    ),
    "meaningful_liquidity": (
        "UNKNOWN_MEANINGFUL_SOURCE_POOL",
        "Source contextual significance is not implied by existence of a geometric swing pool.",
    ),
    "liquidity_context": (
        "UNKNOWN_SOURCE_LIQUIDITY_CONTEXT",
        "No unique contextual source pool/direction relationship is selected by the visible raid alone.",
    ),
    "adverse_liquidity": (
        "UNKNOWN_ADVERSE_ROLE",
        "Source requires pool ID, direction, spatial and structural/flow relation; no source role witness establishes ADVERSE/TARGET_OR_FUEL/NEUTRAL.",
    ),
    "contextual_poi_relation": (
        "UNKNOWN_CONTEXTUAL_POI_RELATION",
        "A geometrically valid FVG/provisional OB does not prove contextual/opposing source POI relevance.",
    ),
    "inventory_completeness": (
        "UNKNOWN_SOURCE_INVENTORY_COMPLETENESS",
        "Raw known-prefix enumeration is complete; contextual FTA/adverse relevance/consumption remain unidentified, so SOURCE completeness is not established.",
    ),
    "zone_first_test": (
        "UNKNOWN_FIRST_ELIGIBLE_TEST",
        "Observed OHLC zone touch does not establish selected source POI, eligibility or intrabar ordering; no cooldown/retry proxy is used.",
    ),
    "source_stop_anchor": (
        "UNKNOWN_SOURCE_STOP_SELECTION",
        "Observed raw candle/deviation extreme is conditional on valid source formation/selected range; metadata is not required to select an anchor.",
    ),
    "sl_off_liquidity": (
        "UNKNOWN_SOURCE_STOP_CLEARANCE",
        "Selected source stop expression and meaningful contextual pool scope/clearance must be established; geometric pool existence is insufficient.",
    ),
}
DEPENDENCIES = {
    "higher_poi": "UNKNOWN_CONTEXTUAL_POI_RELATION",
    "outside_poi": "UNKNOWN_CONTEXTUAL_POI_RELATION",
    "poi_reaction": "UNKNOWN_CONTEXTUAL_POI_RELATION",
    "trend_aligned": "UNKNOWN_SOURCE_CONTEXT_SELECTION",
    "pd_context": "UNKNOWN_SELECTED_IMPULSE",
    "ob_formation": "UNKNOWN_SOURCE_OB_CONTEXT",
    "breaker_formation": "UNKNOWN_SOURCE_PARENT_OB_AND_IMPULSE",
    "breaker_confirmation": "UNKNOWN_SOURCE_PARENT_OB_AND_CONFIRMATION",
    "stb_raid_absorption_structure": "UNKNOWN_SOURCE_STRUCTURE_AND_STB",
    "reaction_bos_new_poi": "UNKNOWN_SOURCE_REACTION_BOS_NEW_POI",
    "ltf_bos_source_entry": "UNKNOWN_SOURCE_M15_BOS_ENTRY",
    "range_deviation": "UNKNOWN_SELECTED_RANGE",
    "range_reclaim_retest": "UNKNOWN_SELECTED_RANGE_AND_RETEST",
    "return_choch_zone": "UNKNOWN_SELECTED_RANGE_AND_CHOCH",
    "canonical_source_context": "UNKNOWN_SOURCE_CONTEXT_SELECTION",
    "source_confirmation": "UNKNOWN_BRANCH_SOURCE_CONFIRMATION",
    "source_entry_poi": "UNKNOWN_SOURCE_ENTRY_POI_RELATION",
    "source_fta_inventory": "UNKNOWN_SOURCE_INVENTORY_COMPLETENESS",
}


class KnownPrefix:
    """One chronological archive cursor. The buffered future row is never exposed."""

    def __init__(self, objects, candles):
        self.object_iter = iter(objects)
        self.candle_iter = iter(candles)
        self.pending_object = next(self.object_iter, None)
        self.pending_candle = next(self.candle_iter, None)
        self.at = -1
        self.objects = {}
        self.object_count = 0
        self.candle_count = 0
        self.object_hash = "0" * 64
        self.last_completed = None
        self.kinds = Counter()
        self.contextual_witnesses = Counter()
        self.primitives = Counter()

    def advance(self, at):
        if type(at) is not int or at < self.at:
            raise ValueError("Blinded prefix cannot run backward")
        pending_parent_links = []
        while self.pending_object is not None and self.pending_object["known_at"] <= at:
            obj = self.pending_object
            no_outcomes(obj)
            if obj["completed_at"] > obj["known_at"] or obj["id"] in self.objects:
                raise ValueError("Uncompleted/duplicate causal object")
            pending_parent_links.extend(
                (obj["id"], p, obj["known_at"]) for p in obj["parent_ids"]
            )
            self.objects[obj["id"]] = obj
            self.object_count += 1
            self.kinds[obj["kind"]] += 1
            self.object_hash = digest(
                ["CAUSAL_OBJECT_PREFIX_v3", self.object_hash, obj["id"]]
            )
            if obj["source_validated"]:
                self.primitives[obj["kind"]] += 1
            if obj.get("protected_endpoint") is True:
                self.contextual_witnesses["protected_endpoints"] += 1
            if obj.get("selected_source_endpoint") is True:
                self.contextual_witnesses["selected_endpoints"] += 1
            if obj.get("contextual_validity") == "SOURCE_CONTEXT_VALIDATED":
                self.contextual_witnesses["source_context"] += 1
            if (
                obj["kind"] in ("BOS", "confirmation", "structure")
                and obj["source_validated"]
            ):
                self.contextual_witnesses[obj["kind"]] += 1
            self.pending_object = next(self.object_iter, None)
        for child_id, parent_id, child_known in pending_parent_links:
            if (
                parent_id not in self.objects
                or self.objects[parent_id]["known_at"] > child_known
            ):
                raise ValueError("Missing/future visible canonical parent: " + child_id)
        while self.pending_candle is not None and self.pending_candle["known_at"] <= at:
            bar = self.pending_candle
            no_outcomes(bar)
            if bar["completed_at"] > bar["known_at"] or bar["known_at"] > at:
                raise ValueError("Future/uncompleted candle")
            self.candle_count += 1
            self.last_completed = bar["completed_at"]
            self.pending_candle = next(self.candle_iter, None)
        self.at = at

    def verify(self, view):
        self.advance(view["decision_cutoff"])
        if (
            self.object_count != view["objects"]
            or self.object_hash != view["object_prefix_sha256"]
            or self.candle_count != view["completed_candles"]
            or self.last_completed != view["last_completed_at"]
            or dict(self.kinds) != view["kind_counts"]
        ):
            raise ValueError("Materialized cutoff prefix differs from frozen view")
        return {
            "objects": self.object_count,
            "completed_candles": self.candle_count,
            "last_completed_at": self.last_completed,
            "object_prefix_sha256": self.object_hash,
            "source_contextual_witness_counts": dict(self.contextual_witnesses),
            "source_primitive_counts": dict(self.primitives),
            "full_prefix_available_at_cutoff": True,
        }


def citations():
    registry = read(
        ROOT
        / "docs/original_strategy_spec_v1_1/original_strategy_rule_registry_v1_1.json"
    )
    return {
        r["rule_id"]: {
            "category": r["category"],
            "literal_meaning": r["literal_meaning"],
            "executable_interpretation": r["executable_interpretation"],
            "normalization_dependencies": r["normalization_dependencies"],
            "primary_passages": [
                {
                    k: p[k]
                    for k in (
                        "source_id",
                        "source_document",
                        "source_sha256",
                        "page_or_paragraph",
                        "literal_passage",
                    )
                }
                for p in r["page_diagram"]
            ],
        }
        for r in registry["rules"]
        if r["category"] == "SOURCE_RULE"
    }


def annotation(unit, question, view, citation_index, *, view_sha=None):
    """Underidentified source relations stay UNKNOWN; raw geometry is not a role selector."""
    no_outcomes(unit)
    no_outcomes(view)
    name = question["concept"]
    rules = question["source_rule_ids"]
    cutoff = unit["decision_cutoff"]
    if not rules or any(r not in citation_index for r in rules):
        raise ValueError("Non-source/unknown citation")
    if any(
        v["last_completed_at"] is not None and v["last_completed_at"] > cutoff
        for v in view["causal_inventory"].values()
    ):
        raise ValueError("Future annotation view")
    witnesses = Counter()
    for frame in view["causal_inventory"].values():
        witnesses.update(frame["source_contextual_witness_counts"])
    if witnesses:
        # This sufficiency reviewer does not override an actual contextual
        # witness; such a case needs its explicit branch relation reviewed.
        reason_code = "UNKNOWN_UNREVIEWED_CONTEXTUAL_RELATION"
        reason = "Source contextual witnesses exist; this input-sufficiency reviewer cannot assign their material relationship without an explicit source relation proof."
    elif name in REASONS:
        reason_code, reason = REASONS[name]
    elif name in DEPENDENCIES:
        reason_code = DEPENDENCIES[name]
        reason = (
            "Source predicate "
            + name
            + " depends on uniquely selected contextual/protected/branch objects not established by the causal view; raw conditional geometry is retained without promotion."
        )
    else:
        raise ValueError("Question lacks source review framing: " + name)
    result = {
        "candidate_id": unit["candidate_ids"][0],
        "question": name,
        "answer": "UNKNOWN",
        "source_rule_ids": rules,
        "source_citations": [
            {"rule_id": r, "registry": "SOURCE_CITATIONS.json"} for r in rules
        ],
        "visible_cutoff": cutoff,
        "known_at": cutoff,
        "completed_at": max(
            (v["last_completed_at"] or 0) for v in view["causal_inventory"].values()
        ),
        "annotator_provenance": {
            "annotator_id": ANNOTATOR,
            "method": "SOURCE_INPUT_SUFFICIENCY_REVIEW",
            "claimed_human_chart_review": False,
            "view_sha256": view_sha or digest(view),
            "annotation_unit_id": unit["annotation_unit_id"],
        },
        "reason": reason,
        "unknown_reason": reason_code,
        "source_validated": False,
        "trade_entry_allowed": False,
    }
    no_outcomes(result)
    return result


def validate_annotation(record, *, unit, view, citation_index, view_sha=None):
    no_outcomes(record)
    if (
        record["candidate_id"] not in unit["candidate_ids"]
        or record["visible_cutoff"] != unit["decision_cutoff"]
    ):
        raise ValueError("Annotation identity/cutoff mismatch")
    if (
        not 0
        <= record["completed_at"]
        <= record["known_at"]
        <= record["visible_cutoff"]
    ):
        raise ValueError("Noncausal annotation time")
    questions = {q["concept"]: q["source_rule_ids"] for q in unit["required_questions"]}
    if (
        record["question"] not in questions
        or record["source_rule_ids"] != questions[record["question"]]
    ):
        raise ValueError("Annotation question/citation mismatch")
    if any(
        r not in citation_index or citation_index[r]["category"] != "SOURCE_RULE"
        for r in record["source_rule_ids"]
    ):
        raise ValueError("Non-source annotation citation")
    if (
        record["annotator_provenance"]["view_sha256"] != (view_sha or digest(view))
        or not record["reason"]
    ):
        raise ValueError("Unbound annotation provenance")
    if record["answer"] == "UNKNOWN":
        if not record["unknown_reason"] or record["source_validated"] is not False:
            raise ValueError("Unknown annotation misrepresented as proof")
    elif record["answer"] in ("PASS", "FAIL"):
        if not record.get("source_witness") or record["source_validated"] is not True:
            raise ValueError("PASS/FAIL requires explicit causal source witness")
        raise ValueError(
            "Positive discretionary witness validation is outside this sufficiency-only reviewer"
        )
    else:
        raise ValueError("Invalid annotation answer")
    return record


def build(output):
    if (output / "ANNOTATION_COUNTS.json").exists():
        raise ValueError("Existing stage preserved")
    parents = verify_originals()
    units = list(rows(V3 / "ANNOTATION_UNIT_MAP.jsonl.gz"))
    units.sort(
        key=lambda u: (
            u["decision_cutoff"],
            u["symbol"],
            u["setup_tf"],
            u["branch"],
            u["annotation_unit_id"],
        )
    )
    if len(units) != 131099 or any(len(u["candidate_ids"]) != 1 for u in units):
        raise ValueError("Frozen current equivalence cohort changed")
    source = citations()
    output.mkdir(parents=True, exist_ok=True)
    save(output / "SOURCE_CITATIONS.json", source)
    frames = {}
    for unit in units:
        for tf, desc in unit["blinded_prefixes"].items():
            key = (unit["symbol"], tf)
            if key not in frames:
                frames[key] = KnownPrefix(
                    rows(V3 / desc["objects_file"]),
                    rows(ROOT / desc["blinded_candles_file"]),
                )
    counts, reasons, by_question, by_branch, by_tf = (
        Counter(),
        Counter(),
        Counter(),
        Counter(),
        Counter(),
    )
    batches = []
    candidate_ledger_index = []
    total = 0
    with writer(output / "ANNOTATION_LEDGER.jsonl.gz") as emit:
        for offset in range(0, len(units), BATCH_SIZE):
            group = units[offset : offset + BATCH_SIZE]
            batch = len(batches) + 1
            filename = f"BATCH_VIEWS/{batch:04d}.jsonl.gz"
            candidate_ids = []
            with writer(output / filename) as emit_view:
                for unit in group:
                    inventories = {
                        tf: frames[(unit["symbol"], tf)].verify(desc)
                        for tf, desc in unit["blinded_prefixes"].items()
                    }
                    relevant = {oid for oid in unit["context_ids"]}
                    # Canonical formation/context IDs from the frozen unit are
                    # fetched only from already-visible objects, not global history.
                    observed = []
                    for oid in sorted(relevant):
                        found = [
                            f.objects[oid]
                            for (s, _tf), f in frames.items()
                            if s == unit["symbol"] and oid in f.objects
                        ]
                        if (
                            len(found) != 1
                            or found[0]["known_at"] > unit["decision_cutoff"]
                        ):
                            raise ValueError("Missing/future relevant canonical object")
                        observed.append(found[0])
                    view = {
                        "annotation_unit": unit,
                        "causal_inventory": inventories,
                        "visible_related_objects": observed,
                        "full_visible_object_set": unit["blinded_prefixes"],
                        "materialization": "FULL_KNOWN_PREFIX_WITH_VERIFIED_LAZY_ARCHIVE_VIEW",
                        "future_objects_exposed": False,
                        "trade_entry_allowed": False,
                    }
                    no_outcomes(view)
                    view_sha = digest(view)
                    emit_view(view)
                    candidate_ids.append(unit["candidate_ids"][0])
                    first = total
                    for question in unit["required_questions"]:
                        record = annotation(
                            unit, question, view, source, view_sha=view_sha
                        )
                        validate_annotation(
                            record, unit=unit, view=view, citation_index=source
                        )
                        emit(record)
                        total += 1
                        counts[record["answer"]] += 1
                        reasons[record["unknown_reason"]] += 1
                        by_question[record["question"]] += 1
                    candidate_ledger_index.append(
                        {
                            "candidate_id": unit["candidate_ids"][0],
                            "batch": batch,
                            "first_annotation_record": first,
                            "annotations": total - first,
                            "visible_cutoff": unit["decision_cutoff"],
                            "view_sha256": view_sha or digest(view),
                        }
                    )
                    by_branch[unit["branch"]] += 1
                    by_tf[str(unit["setup_tf"])] += 1
            batches.append(
                {
                    "batch": batch,
                    "file": filename,
                    "sha256": checksum(output / filename),
                    "candidate_ids": candidate_ids,
                    "unit_cutoffs": [u["decision_cutoff"] for u in group],
                    "candidates": len(group),
                    "source_citations_sha256": checksum(
                        output / "SOURCE_CITATIONS.json"
                    ),
                    "no_batch_maximum_cutoff_used": True,
                }
            )
            if batch % 100 == 0:
                print(
                    "Blinded annotation batch",
                    batch,
                    "cases",
                    offset + len(group),
                    "annotations",
                    total,
                    flush=True,
                )
    with writer(output / "CANDIDATE_ANNOTATION_INDEX.jsonl.gz") as emit:
        for record in candidate_ledger_index:
            emit(record)
    save(
        output / "BATCH_MANIFEST.json",
        {
            "batch_size": BATCH_SIZE,
            "batching_is_transport_only": True,
            "batches": batches,
        },
    )
    save(
        output / "ANNOTATION_COUNTS.json",
        {
            "candidates": len(units),
            "annotation_units": len(units),
            "annotations": total,
            "batches": len(batches),
            "answers": dict(counts),
            "whole_candidate_PASS": 0,
            "whole_candidate_FAIL": 0,
            "whole_candidate_UNKNOWN": len(units),
            "question_counts": dict(by_question),
            "branch_distribution": dict(by_branch),
            "TF_distribution": dict(by_tf),
            "annotator": ANNOTATOR,
            "historical_human_discretionary_annotations": 0,
            "trade_entry_allowed": False,
        },
    )
    save(output / "UNKNOWN_REASON_BREAKDOWN.json", dict(reasons.most_common()))
    save(
        output / "NO_OUTCOME_LEAKAGE_QA.json",
        {
            "status": "PASS",
            "candidates": len(units),
            "annotations": total,
            "causal_prefix_cursors": len(frames),
            "all_unit_prefix_hashes_counts_verified": True,
            "all_annotation_cutoffs_validated": True,
            "actual_visible_object_identity_queries": "PASS",
            "no_future_no_old_labels_no_outcomes": "PASS",
            "BACKTEST_SHADOW_view_identity": "PASS (mode is not an annotation input)",
            "human_chart_review_claimed": False,
            "new_qualitative_selector_added": False,
            "trade_entry_allowed": False,
        },
    )
    save(output / "PARENT_INVARIANCE.json", parents)
    print("BLINDED_ANNOTATION_COMPLETE", len(units), total, dict(counts), flush=True)


def generated(output):
    names = [
        "SOURCE_CITATIONS.json",
        "ANNOTATION_LEDGER.jsonl.gz",
        "CANDIDATE_ANNOTATION_INDEX.jsonl.gz",
        "BATCH_MANIFEST.json",
        "ANNOTATION_COUNTS.json",
        "UNKNOWN_REASON_BREAKDOWN.json",
        "NO_OUTCOME_LEAKAGE_QA.json",
        "PARENT_INVARIANCE.json",
    ]
    names.extend(b["file"] for b in read(output / "BATCH_MANIFEST.json")["batches"])
    return names


def validate(replay):
    qa = validate_qa(DEST, CODE, replay, generated(DEST), minimum_tests=823)
    counts = read(DEST / "ANNOTATION_COUNTS.json")
    if counts["candidates"] != 131099 or counts["annotations"] != 2186597:
        raise ValueError("Frozen questions/cohort coverage changed")
    (DEST / "QA_REPORT.md").write_text(f"""# Stage 1 QA

PASS: {qa["tests"]} inherited/new tests; {qa["deterministic_replay_outputs"]} output files byte-identical in a fresh replay.
All 131099 candidate views materialized with exact four-TF cutoff prefix counts/hashes.
Every annotation ID/question/citation/cutoff/provenance validated before writing. All questions covered exactly once.
Actual frozen prefixes were advanced chronologically; future rows never entered the annotator view.
Source citations include unchanged primary file/page/hash/literal passages. No machine selector was promoted to SOURCE.
Completed-candle/known_at, prefix/future mutation, canonical IDs, first-test semantics and mode parity are regression covered.
Frozen v1/v1.1/v2/v3/recovery/first result/dataset and baseline/Source Audit archive hashes pass.
The reviewer records source underdetermination; it does not claim 131099 human visual chart reviews.
All material qualitative answers remain UNKNOWN; no absence of proof became FAIL.
No financial run, LIVE/private API or source policy mutation. trade_entry_allowed=false.
""")
    print("BLINDED_ANNOTATION_QA_PASS", qa["tests"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--replay-output", type=Path)
    group.add_argument("--validate-replay", type=Path)
    group.add_argument("--seal", action="store_true")
    group.add_argument("--resume-existing", action="store_true")
    args = parser.parse_args()
    if args.resume_existing:
        verify_stage(DEST)
        verify_originals()
        print("VERIFIED_RESUME BLINDED_ANNOTATION_v1")
    elif args.seal:
        seal(
            DEST,
            CODE,
            name="BLINDED_SOURCE_ANNOTATION_v1",
            parent={
                "evidence_v3_manifest_sha256": checksum(V3 / "freeze_manifest.json")
            },
            status="FROZEN_QUALITATIVE_UNKNOWN",
        )
    elif args.validate_replay:
        validate(args.validate_replay)
    else:
        build(args.replay_output or DEST)


if __name__ == "__main__":
    main()
