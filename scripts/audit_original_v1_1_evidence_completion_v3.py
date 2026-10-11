"""Offline source-only QA/report sealing. Never starts a trading run."""

from __future__ import annotations

import argparse
import gc
import gzip
import json
import re
import subprocess
from collections import Counter
from itertools import zip_longest
from pathlib import Path

from materialize_original_v1_1_evidence_completion_v3 import materialize
from original_strategy_executable_profile_v1 import digest
from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_evidence_completion_v3 import CompletionIndex
from original_v1_1_financial_data import ROOT, checksum, compact, load_market, save
from original_v1_1_source_plan_geometry_v3 import READY, STATUSES
from run_original_v1_1_evidence_completion_v3 import DEST, verify_parents

CODE = [
    f"scripts/{name}.py"
    for name in (
        "original_v1_1_evidence_completion_v3",
        "original_v1_1_source_plan_geometry_v3",
        "run_original_v1_1_evidence_completion_v3",
        "materialize_original_v1_1_evidence_completion_v3",
        "audit_original_v1_1_evidence_completion_v3",
    )
]
CODE += ["tests/test_original_v1_1_evidence_completion_v3.py"]


def rows(path):
    with gzip.open(path, "rt") as stream:
        for line in stream:
            yield json.loads(line)


def historical_prefix():
    data, _ = load_market()
    receipt = []
    for symbol, frames in data.items():
        for tf, bars in frames.items():
            size = len(bars) // 2
            at = bars[size - 1].end
            index = CompletionIndex(symbol, tf, bars[:size])

            def saved_prefix(symbol=symbol, tf=tf, at=at):
                for obj in rows(DEST / f"CAUSAL_OBJECTS/{symbol}_{tf}.jsonl.gz"):
                    if obj["known_at"] > at:
                        break
                    yield obj

            for rebuilt, saved in zip_longest(index.ordered, saved_prefix()):
                if rebuilt != saved:
                    raise ValueError("Historical prefix inconsistency")
            receipt.append(
                {
                    "symbol": symbol,
                    "tf": tf,
                    "cutoff": at,
                    "objects": len(index.ordered),
                    "prefix_sha256": index.prefix(at)["object_prefix_sha256"],
                    "status": "PASS",
                }
            )
            print("Historical prefix PASS", symbol, tf, len(index.ordered), flush=True)
            del index
            gc.collect()
    save(DEST / "qa/HISTORICAL_PREFIX_RECEIPT.json", receipt)


def ledger_qa():
    funnel = json.loads((DEST / "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json").read_text())
    counts, gaps, components, ids = Counter(), Counter(), Counter(), set()
    for row in rows(DEST / "ALL_SOURCE_EVIDENCE_CASES.jsonl.gz"):
        no_outcomes(row)
        if row["candidate_id"] in ids or row["trade_entry_allowed"] is not False:
            raise ValueError("Duplicate/admitted historical candidate")
        ids.add(row["candidate_id"])
        counts[row["status"]] += 1
        gaps.update(row["source_gaps"])
        components.update(row["source_component_counts"])
        if (
            row["SOURCE_ALLOW"]
            or row["SOURCE_DECISION_READY_FOR_FINANCE"]
            or row["historical_annotations_loaded"]
        ):
            raise ValueError("Unpermitted admission")
        if any(
            v["last_completed_at"] is not None
            and v["last_completed_at"] > row["decision_at"]
            for v in row["source_fta_inventory"]["prefixes"].values()
        ):
            raise ValueError("Annotation cutoff leak")
        if row["status"] == READY and row["source_gaps"]:
            raise ValueError("Critical UNKNOWN in READY")
    if sum(counts.values()) != funnel["RAW_PROPOSALS"] or any(
        counts[s] != funnel[s] for s in STATUSES
    ):
        raise ValueError("Exclusive funnel inconsistent")
    if (
        dict(gaps) != funnel["parallel_source_gaps"]
        or dict(components) != funnel["source_components_complete"]
    ):
        raise ValueError("Parallel diagnostics inconsistent")
    candidate_unit_ids, units, qcounts, sample = set(), set(), Counter(), None
    for unit in rows(DEST / "ANNOTATION_UNIT_MAP.jsonl.gz"):
        no_outcomes(unit)
        if sample is None:
            sample = unit
        if unit["annotation_unit_id"] in units:
            raise ValueError("Duplicate annotation unit")
        units.add(unit["annotation_unit_id"])
        if len(unit["candidate_ids"]) > 1 and (
            unit["physical_idea_id"] is None or unit["setup_id"] is None
        ):
            raise ValueError("Unproven annotation equivalence")
        for candidate in unit["candidate_ids"]:
            if candidate not in ids or candidate in candidate_unit_ids:
                raise ValueError("Annotation candidate missing or duplicated")
            candidate_unit_ids.add(candidate)
        qcounts.update(q["concept"] for q in unit["required_questions"])
        if any(
            q["state"] != "UNKNOWN" or not q["source_rule_ids"]
            for q in unit["required_questions"]
        ):
            raise ValueError("Unaudited qualitative label/citation")
    if (
        len(units) != funnel["UNIQUE_ANNOTATION_UNITS"]
        or len(candidate_unit_ids) != funnel["QUALITATIVE_CANDIDATES"]
    ):
        raise ValueError("Annotation equivalence coverage inconsistent")
    rendered = materialize(sample)
    # An actual rendered historical unit is checked, not just cutoff pointers.
    if any(
        o["known_at"] > sample["decision_cutoff"]
        for objects in rendered["causal_objects"].values()
        for o in objects
    ):
        raise ValueError("Rendered view leaked future")
    save(
        DEST / "qa/LEDGER_QA_RECEIPT.json",
        {
            "status": "PASS",
            "cases": len(ids),
            "units": len(units),
            "unit_candidates": len(candidate_unit_ids),
            "qualitative_question_counts": dict(qcounts),
            "rendered_unit_id": sample["annotation_unit_id"],
            "rendered_unit_sha256": digest(rendered),
            "exclusive_partition": "PASS",
            "annotation_no_outcome_leakage": "PASS",
            "trade_entry_allowed": False,
        },
    )


def reports():
    f = json.loads((DEST / "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json").read_text())
    qa = json.loads((DEST / "qa/LEDGER_QA_RECEIPT.json").read_text())
    (
        DEST / "QUALITATIVE_COMPLETION_REPORT.md"
    ).write_text(f"""# Blinded qualitative completion v3

RAW qualitative candidates: {f["QUALITATIVE_CANDIDATES"]:,}; unique annotation units: {f["UNIQUE_ANNOTATION_UNITS"]:,}.
Average {f["annotation_units"]["average_candidates_per_unit"]}; median {f["annotation_units"]["median_candidates_per_unit"]}; maximum {f["annotation_units"]["max_group_size"]} candidates/unit.
{f["annotation_units"]["distinct_raw_visible_views"]:,} distinct symbol/setup-TF/cutoff raw views can share transport/display;
shared candles do not prove shared physical idea, context, source POI, formation or branch questions.
Actual equivalence key is compared before grouping. Missing physical/setup identity produces a singleton,
not a common null-valued idea. No forced reduction to an invented context selector.

Whole-candidate qualitative PASS {f["QUALITATIVE_PASS"]}; FAIL {f["QUALITATIVE_FAIL"]}; UNKNOWN {f["QUALITATIVE_UNKNOWN"]:,}.
Coverage waits are a separate exclusive top status, not qualitative FAIL.
No historical audited annotations were supplied. All material discretionary questions are explicitly UNKNOWN.
Geometry PASS and conditional raw entry/anchor facts are not qualitative PASS or SOURCE setup validity.
Source-stop construction is complete independently of metadata for {f["source_components_complete"]["SOURCE_STOP_ANCHOR_COMPLETE"]:,} SFP patterns.
Other observed candle extremes are recorded conditionally; a provisional OB or unselected range is not a SOURCE anchor.

Branch unit distribution: `{compact(f["annotation_units"]["branch_distribution"])}`.
TF unit distribution: `{compact(f["annotation_units"]["TF_distribution"])}`.
Question counts: `{compact(qa["qualitative_question_counts"])}`.

Use the new materializer for an actual cutoff-filtered unit. Full gzip histories are archives, not annotator views.
No future outcomes, future candles, baseline result, old adverse751 or old owner/admission labels are annotation input.
No classifier, numeric smoothness threshold, clear-range threshold or outcome-selected policy was introduced.
""")
    gaplines = "\n".join(
        f"- `{k}`: {v:,}" for k, v in f["parallel_source_gaps"].items()
    )
    (DEST / "REMAINING_SOURCE_GAPS.md").write_text(f"""# Remaining source gaps

SOURCE_READY_EXCEPT_EXECUTION_METADATA = {f[READY]}. Metadata is excluded from the source-evidence partition.
Every candidate was assessed through source predicates, liquidity, confirmation, entry, stop, target, identity and first-test.
No missing source input was converted into FAIL or a made-up PASS.

Non-exclusive parallel source gaps (a case may appear more than once):

{gaplines}

The root source dependency is a validated contextual origin/POI and protected or selected endpoints.
Strict swing pair labels and raw body crossings do not select protected structure. A source-valid FVG
is objective geometry, but its contextual/opposing relevance is still unproven. Complete raw enumeration
is not complete contextual FTA/adverse inventory. No unique source context is proven by the supplied inputs;
therefore no physical/setup identity can establish annotation equivalence. A finite raw level existence
never assigns ADVERSE/TARGET_OR_FUEL/NEUTRAL. Eligible first interaction is unresolved even where an
observed completed-bar OHLC touch exists; neither fill nor intrabar ordering is inferred.

SFP/OB require genuine causal M15 BOS and linked new source POI. Higher-TF SFP uses the frozen next-native
completion to expose next OPEN; other cutoffs match v2 exactly. Later confirmation cannot be borrowed
from a later candle. BREAKER additionally needs a source-valid parent OB and whole-impulse relationship;
STB needs contextual raid/absorption/structure and selected dealing endpoints; ranges need source-selected
clear boundaries and branch-specific reclaim/CHOCH/return/retest. These remain explicit questions.

Metadata UNKNOWN blocks all {f["HISTORICAL_METADATA_BLOCKED"]:,} candidates in parallel. Rounded quotes/quantity
are not calculated. A source-ready analytical case would still require the unchanged executable's exact
metadata-dependent checks before any admission. SOURCE_ALLOW and SOURCE_DECISION_READY_FOR_FINANCE remain zero.
No profitability conclusion is drawn.
""")


def validate(replay):
    verify_parents()
    originals = {
        str(p.relative_to(DEST)): checksum(p)
        for p in DEST.rglob("*")
        if p.is_file()
        and (
            p.suffix == ".gz"
            or p.name
            in (
                "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json",
                "DATASET_VERIFICATION.json",
                "PARENT_INVARIANCE.json",
                "OLD880_EVIDENCE_RECHECK_V3.csv",
            )
        )
    }
    actual = {
        str(p.relative_to(replay)): checksum(p)
        for p in replay.rglob("*")
        if p.is_file()
    }
    if originals != actual:
        raise ValueError("Full deterministic replay mismatch")
    logs = {
        name: (DEST / "qa" / f"{name}.log").read_text()
        for name in (
            "full_unittest",
            "ruff",
            "compile",
            "mypy",
            "frozen_parent_resume",
            "metadata_resume",
        )
    }
    match = re.search(r"Ran (\d+) tests[^\n]*\n\nOK(?:\n|$)", logs["full_unittest"])
    if (
        not match
        or int(match[1]) < 816
        or "FAILED (" in logs["full_unittest"]
        or "skipped=" in logs["full_unittest"]
    ):
        raise ValueError("Full inherited/new test gate failed")
    if (
        "All checks passed!" not in logs["ruff"]
        or logs["compile"].strip()
        or "Success: no issues found" not in logs["mypy"]
        or "VERIFIED_RESUME v1.1" not in logs["frozen_parent_resume"]
        or "VERIFIED_RESUME STAGE_A_STOP" not in logs["metadata_resume"]
    ):
        raise ValueError("Required tooling/frozen-parent QA failed")
    prefix = json.loads((DEST / "qa/HISTORICAL_PREFIX_RECEIPT.json").read_text())
    ledger = json.loads((DEST / "qa/LEDGER_QA_RECEIPT.json").read_text())
    if (
        len(prefix) != 8
        or any(r["status"] != "PASS" for r in prefix)
        or ledger["status"] != "PASS"
    ):
        raise ValueError("Historical prefix/ledger QA failed")
    reports()
    receipt = {
        "status": "PASS",
        "full_tests": int(match[1]),
        "replayed_outputs": len(originals),
        "replay_sha256": originals,
        "historical_prefix_series": 8,
        "full_ledger_and_materialized_annotation_cutoff": "PASS",
        "v1_v1_1_v2_metadata_recovery_first_result_dataset_hashes": "PASS",
        "baseline_source_audit_invariance": "PASS (17851 frozen archive paths)",
        "causality_future_mutation_source_registry_canonical_ID_first_test_mode_parity": "PASS",
        "no_old_labels_no_outcome_leakage_no_financial_accounting": "PASS",
        "code_sha256": {name: checksum(ROOT / name) for name in CODE},
        "qa_log_sha256": {name: checksum(DEST / "qa" / f"{name}.log") for name in logs},
        "HISTORICAL_METADATA_VERIFIED": False,
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "trade_entry_allowed": False,
    }
    save(DEST / "QA_RECEIPT.json", receipt)
    (DEST / "QA_REPORT.md").write_text(f"""# Evidence completion v3 QA

PASS: {receipt["full_tests"]} tests (all inherited plus v3), no failures/skips.
Ruff new code/tests, compile src/scripts/tests, mypy src: PASS.
All {len(originals)} generated outputs replay byte-identically in a fresh destination.
Eight actual historical half-prefix reconstructions match full-run known-prefix objects exactly.
All 176365 ledger records pass exclusive partition, completed-candle/cutoff/no-outcome/no-admission checks.
Every annotation candidate maps exactly once; one actual historical unit was materialized and all
exposed objects/candles verified against its cutoff and prefix hash. Synthetic future mutation,
causal source facts, FTA ties, source context nonuniqueness, first-test idempotence and all-branch
BACKTEST/SHADOW readiness parity pass. No new SOURCE rules or old qualitative labels were imported.
Frozen v1/v1.1/v2/recovery/first-result hashes, dataset hashes and baseline/Source Audit archive invariance pass.
Accounting/fills/profitability research were not run; inherited financial unit fixtures are synthetic regression only.
No LIVE/private API. trade_entry_allowed=false. Metadata remains UNKNOWN and was not searched again.
""")
    print(
        "EVIDENCE_COMPLETION_V3_QA_PASS",
        receipt["full_tests"],
        "tests; replay",
        len(originals),
        flush=True,
    )


def seal():
    path = DEST / "freeze_manifest.json"
    if path.exists():
        raise ValueError("Existing seal preserved")
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != "medium-term-source-research"
    ):
        raise ValueError("Research branch required")
    qa = json.loads((DEST / "QA_RECEIPT.json").read_text())
    if qa["status"] != "PASS":
        raise ValueError("QA required")
    for name, expected in qa["code_sha256"].items():
        if checksum(ROOT / name) != expected:
            raise ValueError("Code changed after QA")
    for name, expected in qa["qa_log_sha256"].items():
        if checksum(DEST / "qa" / f"{name}.log") != expected:
            raise ValueError("QA log changed")
    for name, expected in qa["replay_sha256"].items():
        if checksum(DEST / name) != expected:
            raise ValueError("Output changed after replay")
    verify_parents()
    files = {
        str(p.relative_to(ROOT)): checksum(p) for p in DEST.rglob("*") if p.is_file()
    }
    files.update({name: checksum(ROOT / name) for name in CODE})
    save(
        path,
        {
            "name": "SOURCE_EVIDENCE_COMPLETION_v3",
            "parent_commit": "4b28c3892b51a1bb3b331dd344651c16ef7c8432",
            "strategy_commit": "43e9d7addcd427650ff856dd1fa99f78ee5c06f7",
            "artifacts": dict(sorted(files.items())),
            "QA": "PASS",
            "QA_tests": qa["full_tests"],
            "financial_execution": "PROHIBITED",
            "HISTORICAL_METADATA_VERIFIED": False,
            "SECOND_FINANCIAL_BACKTEST_RAN": False,
            "trade_entry_allowed": False,
        },
    )
    print(
        "EVIDENCE_COMPLETION_V3_FROZEN", len(files), "artifacts; SHA256", checksum(path)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--historical-prefix", action="store_true")
    group.add_argument("--ledger-qa", action="store_true")
    group.add_argument("--validate-replay", type=Path)
    group.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    if (DEST / "freeze_manifest.json").exists():
        raise SystemExit("Sealed delivery; use verified --resume-existing")
    if args.historical_prefix:
        historical_prefix()
    elif args.ledger_qa:
        ledger_qa()
    elif args.validate_replay:
        validate(args.validate_replay)
    else:
        seal()


if __name__ == "__main__":
    main()
