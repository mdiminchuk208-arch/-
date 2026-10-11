"""Source-only assembly of frozen v3 evidence plus frozen blinded annotations."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from original_strategy_executable_profile_v1 import ACTIVE
from original_v1_1_evidence_adapter_v2 import QUALITATIVE, no_outcomes
from original_v1_1_evidence_completion_v3 import ADDED_QUESTIONS
from original_v1_1_financial_data import ROOT, checksum, save, write_csv
from original_v1_1_source_plan_geometry_v3 import READY, STATUSES
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

ANN = ROOT / "docs/original_v1_1_blinded_annotation_v1"
DEST = ROOT / "docs/original_v1_1_evidence_completion_v4"
ANNOTATION_MANIFEST_SHA = "8f2a7e150802ba6a066592cd9052f82dba1711ec18e45de10eac80b0de8a9ce1"
CODE = [
    "scripts/original_v1_1_evidence_completion_v4.py",
    "tests/test_original_v1_1_evidence_completion_v4.py",
]
FILES = [
    "ALL_SOURCE_EVIDENCE_CASES.jsonl.gz",
    "SOURCE_READY_EXCEPT_METADATA.jsonl.gz",
    "QUALITATIVE_UNKNOWN_CASES.jsonl.gz",
    "SOURCE_FAIL_CASES.jsonl.gz",
    "LOWER_TF_WAIT_CASES.jsonl.gz",
    "OTHER_SOURCE_WAIT_CASES.jsonl.gz",
    "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json",
    "OLD880_EVIDENCE_RECHECK_V4.csv",
    "PARENT_INVARIANCE.json",
    "ANNOTATION_JOIN_QA.json",
]


def annotation_summaries():
    index = {
        r["candidate_id"]: r for r in rows(ANN / "CANDIDATE_ANNOTATION_INDEX.jsonl.gz")
    }
    summaries = {}
    total = 0
    for record in rows(ANN / "ANNOTATION_LEDGER.jsonl.gz"):
        key = record["candidate_id"]
        view = index.get(key)
        if (
            view is None
            or record["visible_cutoff"] != view["visible_cutoff"]
            or record["annotator_provenance"]["view_sha256"] != view["view_sha256"]
        ):
            raise ValueError("Unbound source annotation join")
        if not record["completed_at"] <= record["known_at"] <= record["visible_cutoff"]:
            raise ValueError("Future annotation evidence")
        q = record["question"]
        allowed = QUALITATIVE.get(q, ADDED_QUESTIONS.get(q))
        if not allowed or record["source_rule_ids"] != allowed:
            raise ValueError("Non-source or wrong predicate citation")
        if (
            record["answer"] != "UNKNOWN"
            or record["source_validated"] is not False
            or not record["unknown_reason"]
        ):
            # This consumes the frozen sufficiency-only Stage 1 ledger. A future
            # positive discretionary witness must get a separate new freeze.
            raise ValueError("Unexpected unvalidated source witness in Stage 1")
        summary = summaries.setdefault(key, {"answers": {}, "view": view, "records": 0})
        if q in summary["answers"]:
            raise ValueError("Duplicate qualitative annotation")
        summary["answers"][q] = record["answer"]
        summary["records"] += 1
        total += 1
    for key, summary in summaries.items():
        if summary["records"] != index[key]["annotations"]:
            raise ValueError("Incomplete annotation ledger span")
    if len(summaries) != 131099 or total != 2186597:
        raise ValueError("Stage 1 annotation cohort changed")
    return summaries, total


def source_complete(base):
    """Critical proof must be present independently of qualitative labels."""
    at = base["decision_at"]
    context = base.get("canonical_source_context", {})
    identity = base.get("source_identity")
    if (
        not identity
        or not identity.get("physical_id")
        or not identity.get("setup_id")
        or context.get("physical_idea_id") != identity["physical_id"]
        or context.get("setup_id") != identity["setup_id"]
        or context.get("canonical_source_context") != "SOURCE_CONTEXT_COMPLETE"
    ):
        return False
    for key in (
        "source_entry_geometry",
        "source_stop_anchor",
        "source_exit_geometry",
        "source_confirmation_geometry",
    ):
        obj = base.get(key)
        if not obj or type(obj.get("known_at")) is not int or obj["known_at"] > at:
            return False
    if base["source_confirmation_geometry"].get("state") != "COMPLETE":
        return False
    if base.get("liquidity_decision") not in ("PASS", "REVALIDATE_SOURCE"):
        return False
    if not base.get("source_fta_inventory", {}).get(
        "inventory_complete_for_SOURCE_prefix"
    ):
        return False
    if (
        any(v != 1 for v in base.get("source_component_counts", {}).values())
        or len(base.get("source_component_counts", {})) < 6
    ):
        return False
    return not base["source_gaps"]


def assemble(base, summary, *, mode="BACKTEST"):
    no_outcomes(base)
    if mode not in ("BACKTEST", "SHADOW"):
        raise ValueError("Offline source assembly only")
    if summary is not None:
        no_outcomes(summary)
        if (
            summary["view"]["candidate_id"] != base["candidate_id"]
            or summary["view"]["visible_cutoff"] != base["decision_at"]
        ):
            raise ValueError("Annotation identity/cutoff mismatch")
        if set(summary["answers"]) != set(base["required_questions"]):
            raise ValueError("Material question set differs")
    answers = {
        q: summary["answers"].get(q, "UNKNOWN") if summary else "UNKNOWN"
        for q in base["required_questions"]
    }
    if any(a != "UNKNOWN" for a in answers.values()):
        raise ValueError(
            "Positive/negative source witnesses require a new annotation freeze"
        )
    unknown = [q for q, a in answers.items() if a == "UNKNOWN"]
    failed = [q for q, a in answers.items() if a == "FAIL"]
    coverage = base["branch"] in ("SFP", "OB_CONSERVATIVE") and base["setup_tf"] == 15
    gaps = sorted(set(base["source_gaps"]) | set(unknown))
    # Geometry/contact/context unknowns are never cleared by a label alone.
    proven = source_complete(base)
    status = (
        "OBJECTIVE_SOURCE_FAIL"
        if base["objective_fail_reasons"]
        else "WAIT_NO_AVAILABLE_LOWER_TF"
        if coverage
        else "QUALITATIVE_FAIL"
        if failed or base["qualitative_fail"]
        else "QUALITATIVE_UNKNOWN"
        if unknown
        else "OTHER_SOURCE_WAIT"
        if gaps or not proven
        else READY
    )
    result = {
        **base,
        "status": status,
        "qualitative_answers": answers,
        "qualitative_unknown": unknown,
        "qualitative_fail": failed,
        "source_gaps": gaps,
        "evidence_complete": status == READY,
        "annotation_stage": "BLINDED_SOURCE_ANNOTATION_v1",
        "annotation_binding": summary["view"]
        if summary
        else {"reason": "NOT_IN_QUALITATIVE_BATCH_FIXED_LOWER_TF_COVERAGE"},
        "annotations_consumed": summary["records"] if summary else 0,
        "SOURCE_ALLOW": 0,
        "SOURCE_DECISION_READY_FOR_FINANCE": 0,
        "metadata_role": "PARALLEL_EXECUTION_BLOCKER",
        "trade_entry_allowed": False,
    }
    no_outcomes(result)
    return result


def recheck_old880():
    fields = [
        "signal_id",
        "symbol",
        "legacy_style",
        "profile_branch",
        "decision_at",
        "direction",
        "setup_tf",
        "raw_event_match_count",
        "source_gaps",
        "source_stop_anchor",
        "source_rule_trace",
    ]
    with (V3 / "OLD880_EVIDENCE_RECHECK_V3.csv").open() as stream:
        roster = [{key: row[key] for key in fields} for row in csv.DictReader(stream)]
    output = []
    import json

    for old in roster:
        branch = old["profile_branch"]
        tf = int(old["setup_tf"])
        matches = int(old["raw_event_match_count"])
        trace = json.loads(old["source_rule_trace"])
        gaps = json.loads(old["source_gaps"])
        objective = {"sfp_geometry", "sfp_next_open", "sfp_tf", "conservative_tf"}
        if branch not in ACTIVE:
            status = "REJECT_INACTIVE_PROFILE_BRANCH"
        elif branch in ("SFP", "OB_CONSERVATIVE") and tf == 15:
            status = "WAIT_NO_AVAILABLE_LOWER_TF"
        elif matches != 1:
            status = "OTHER_SOURCE_WAIT"
        elif any(r["value"] is False and r["predicate"] in objective for r in trace):
            status = "OBJECTIVE_SOURCE_FAIL"
        elif any(
            r["value"] is False and r["predicate"] not in objective for r in trace
        ):
            status = "QUALITATIVE_FAIL"
        elif any(r["value"] is None and r["predicate"] not in objective for r in trace):
            status = "QUALITATIVE_UNKNOWN"
        else:
            status = "OTHER_SOURCE_WAIT"
        output.append(
            {
                **old,
                "decision_at": int(old["decision_at"]),
                "setup_tf": tf,
                "status": status,
                "source_rule_trace": trace,
                "source_gaps": gaps,
                "annotation_transfer": "NOT_TRANSFERRED_WITHOUT_PROVEN_IDENTITY_AND_IDENTICAL_OLD_CUTOFF",
                "outcomes_used": False,
                "SOURCE_ALLOW": 0,
                "trade_entry_allowed": False,
            }
        )
    if len(output) != 880 or len({r["signal_id"] for r in output}) != 880:
        raise ValueError("Old880 roster changed")
    return output


def build(output):
    if (output / "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json").exists():
        raise ValueError("Existing stage preserved")
    parents = verify_originals()
    parents["annotation_stage"] = verify_stage(
        ANN, expected_sha=ANNOTATION_MANIFEST_SHA
    )
    summaries, total = annotation_summaries()
    counts, gaps, components = Counter(), Counter(), Counter()
    seen = set()
    parity = set()
    joined = 0
    output.mkdir(parents=True, exist_ok=True)
    from contextlib import ExitStack

    with ExitStack() as stack:
        emit = {
            name: stack.enter_context(writer(output / name))
            for name in FILES
            if name.endswith(".jsonl.gz")
        }
        for base in rows(V3 / "ALL_SOURCE_EVIDENCE_CASES.jsonl.gz"):
            summary = summaries.get(base["candidate_id"])
            result = assemble(base, summary)
            if summary:
                joined += 1
            key = (base["symbol"], base["branch"], base["setup_tf"])
            if key not in parity:
                if result != assemble(base, summary, mode="SHADOW"):
                    raise ValueError("Historical source mode parity failed")
                parity.add(key)
            if result["candidate_id"] in seen:
                raise ValueError("Duplicate source candidate")
            seen.add(result["candidate_id"])
            counts[result["status"]] += 1
            gaps.update(result["source_gaps"])
            components.update(result["source_component_counts"])
            emit[FILES[0]](result)
            subset = {
                READY: FILES[1],
                "QUALITATIVE_UNKNOWN": FILES[2],
                "QUALITATIVE_FAIL": FILES[3],
                "OBJECTIVE_SOURCE_FAIL": FILES[3],
                "WAIT_NO_AVAILABLE_LOWER_TF": FILES[4],
                "OTHER_SOURCE_WAIT": FILES[5],
            }[result["status"]]
            emit[subset](
                {
                    k: result[k]
                    for k in (
                        "candidate_id",
                        "symbol",
                        "branch",
                        "setup_tf",
                        "decision_at",
                        "status",
                        "source_gaps",
                    )
                }
            )
            if len(seen) % 20000 == 0:
                print("Evidence v4", len(seen), flush=True)
    if (
        len(seen) != 176365
        or counts["WAIT_NO_AVAILABLE_LOWER_TF"] != 45266
        or joined != 131099
    ):
        raise ValueError("Source cohort/annotation coverage changed")
    old = recheck_old880()
    write_csv(output / FILES[7], old, list(old[0]))
    funnel = {
        "version": "SOURCE_EVIDENCE_COMPLETION_v4",
        "RAW_PROPOSALS": len(seen),
        **{s: counts[s] for s in STATUSES},
        "QUALITATIVE_CANDIDATES": joined,
        "QUALITATIVE_PASS": 0,
        "UNIQUE_ANNOTATION_UNITS": joined,
        "ANNOTATIONS_CONSUMED": total,
        "SOURCE_ALLOW": 0,
        "SOURCE_DECISION_READY_FOR_FINANCE": 0,
        "HISTORICAL_METADATA_BLOCKED": len(seen),
        "source_components_complete": dict(components),
        "parallel_source_gaps": dict(gaps.most_common()),
        "old880_counts": dict(Counter(r["status"] for r in old)),
        "historical_mode_parity_combinations": len(parity),
        "GATE_2": "PASS" if counts[READY] > 0 else "STOP_NO_SOURCE_READY_CASES",
        "dependent_financial_stages": "BLOCKED"
        if not counts[READY]
        else "REQUIRE_METADATA_GATE",
        "metadata_stage_independent": True,
        "HISTORICAL_METADATA_VERIFIED": False,
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "trade_entry_allowed": False,
    }
    save(output / FILES[6], funnel)
    save(output / FILES[8], parents)
    save(
        output / FILES[9],
        {
            "status": "PASS",
            "candidate_join_count": joined,
            "annotations": total,
            "unjoined_qualitative_candidates": 0,
            "old880_outcomes_used": False,
            "future_annotations_used": False,
            "old_cutoff_labels_transplanted": False,
            "trade_entry_allowed": False,
        },
    )
    print("EVIDENCE_V4_COMPLETE", dict(counts), flush=True)


def validate(replay):
    verify_stage(ANN, expected_sha=ANNOTATION_MANIFEST_SHA)
    qa = validate_qa(DEST, CODE, replay, FILES, minimum_tests=849)
    f = read(DEST / FILES[6])
    stop = f["GATE_2"]
    (DEST / "QA_REPORT.md").write_text(f"""# Evidence completion v4 QA

PASS: {qa["tests"]} inherited/new tests; all {len(FILES)} generated outputs byte-identical in fresh replay.
Full v3 cohort IDs/cutoffs retained. Stage 1 annotations joined by candidate/cutoff/exact question set and view digest.
All {f["ANNOTATIONS_CONSUMED"]} source annotations validated; UNKNOWN never becomes a source proof or FAIL.
Source geometry/context/identity/first-test gaps persist independently of metadata. No label alone closes a critical object gap.
Historical BACKTEST/SHADOW parity: {f["historical_mode_parity_combinations"]} actual symbol/branch/TF combinations.
Old880 re-evaluated from frozen outcome-free causal trace; old machine/outcome labels never imported.
Known_at, completed candles, prefix/future mutation, canonical IDs, first-test and source registry consistency regression pass.
Frozen strategy/evidence/recovery/result/dataset/baseline/audit hashes pass. No financial run, LIVE/private API.
GATE_2={stop}; independent metadata work remains authorized. trade_entry_allowed=false.
""")
    (DEST / "REMAINING_SOURCE_GAPS.md").write_text(
        "# Remaining source gaps\n\n"
        + "\n".join(f"- `{k}`: {v}" for k, v in f["parallel_source_gaps"].items())
        + "\n\nSource context/protected/selected endpoints and contextual role relations remain underdetermined by the source framing and current view. No new selector is introduced.\n"
        + "SOURCE_READY_EXCEPT_EXECUTION_METADATA=0 is an evidence gate result; no maximum achievable trade count or profitability verdict is claimed.\n"
    )
    print("EVIDENCE_V4_QA_PASS", qa["tests"], flush=True)


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
        verify_stage(ANN, expected_sha=ANNOTATION_MANIFEST_SHA)
        verify_originals()
        print("VERIFIED_RESUME EVIDENCE_COMPLETION_v4")
    elif args.seal:
        seal(
            DEST,
            CODE,
            name="SOURCE_EVIDENCE_COMPLETION_v4",
            parent={
                "annotation_manifest_sha256": ANNOTATION_MANIFEST_SHA,
                "v3_manifest_sha256": checksum(V3 / "freeze_manifest.json"),
            },
            status=read(DEST / FILES[6])["GATE_2"],
        )
    elif args.validate_replay:
        validate(args.validate_replay)
    else:
        build(args.replay_output or DEST)


if __name__ == "__main__":
    main()
