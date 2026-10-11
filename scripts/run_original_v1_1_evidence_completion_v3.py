"""Frozen-cohort source evidence completion only; no execution/accounting."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from contextlib import ExitStack
from hashlib import sha256
from itertools import zip_longest
from pathlib import Path
from statistics import median

from original_strategy_executable_profile_v1 import ACTIVE, digest, load_tree
from original_v1_1_evidence_adapter import all_proposals
from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_evidence_completion_v3 import (
    CompletionIndex,
    annotation_signature,
    annotation_unit,
    inspect_candidate,
)
from original_v1_1_financial_data import (
    END,
    OUT,
    ROOT,
    checksum,
    compact,
    load_market,
    save,
    write_csv,
    write_rows,
)
from original_v1_1_source_plan_geometry_v3 import READY, STATUSES
from run_original_v1_1_evidence_adapter_v2 import DEST as V2
from run_original_v1_1_evidence_adapter_v2 import verify_freeze

DEST = ROOT / "docs/original_v1_1_evidence_completion_v3"
RECOVERY = ROOT / "docs/original_v1_1_metadata_recovery_v2"
PINS = {
    V2
    / "freeze_manifest.json": "79b922c5b9f9008acda333ce768330aa2c2687470d09c22936632b92783a4283",
    RECOVERY
    / "recovery_manifest.json": "a8df076d0f84ee566cee1c662480ec1e0d1a9406354974917f96e591fb3b35d6",
}
OUTPUTS = (
    "ALL_SOURCE_EVIDENCE_CASES.jsonl.gz",
    "QUALITATIVE_UNKNOWN_CASES.jsonl.gz",
    "SOURCE_READY_EXCEPT_METADATA.jsonl.gz",
    "SOURCE_FAIL_CASES.jsonl.gz",
    "LOWER_TF_WAIT_CASES.jsonl.gz",
    "OTHER_SOURCE_WAIT_CASES.jsonl.gz",
)


def verify_parents():
    receipt = {}
    for path, expected in PINS.items():
        if checksum(path) != expected:
            raise ValueError("Pinned parent manifest changed")
        manifest = json.loads(path.read_text())
        for name, value in manifest["artifacts"].items():
            if checksum(ROOT / name) != value:
                raise ValueError("Immutable artifact changed: " + name)
        receipt[str(path.relative_to(ROOT))] = {
            "sha256": expected,
            "artifacts": len(manifest["artifacts"]),
        }
    verify_freeze(V2)
    return receipt


def old880(indices, metadata, tree, lookup):
    fields = (
        "signal_id",
        "symbol",
        "legacy_style",
        "profile_branch",
        "decision_at",
        "direction",
        "setup_tf",
    )
    with (V2 / "OLD880_EVIDENCE_RECHECK.csv").open() as stream:
        roster = [{k: row[k] for k in fields} for row in csv.DictReader(stream)]
    rows = []
    for old in roster:
        at, tf, branch = (
            int(old["decision_at"]),
            int(old["setup_tf"]),
            old["profile_branch"],
        )
        matches = lookup.get((old["symbol"], tf, branch, old["direction"], at), [])
        details = None
        if branch not in ACTIVE:
            status, gaps = "REJECT_INACTIVE_PROFILE_BRANCH", []
        elif branch in ("SFP", "OB_CONSERVATIVE") and tf == 15:
            status, gaps = "WAIT_NO_AVAILABLE_LOWER_TF", ["WAIT_NO_AVAILABLE_LOWER_TF"]
        elif len(matches) == 1:
            # Original old880 cutoff retained. Never transplant later v2 followup.
            details = inspect_candidate(
                {**matches[0], "formation_at": at, "candidate_id": old["signal_id"]},
                indices,
                metadata,
                tree,
            )
            status, gaps = details["status"], details["source_gaps"]
        else:
            status, gaps = (
                "OTHER_SOURCE_WAIT",
                [
                    "LEGACY_EVENT_SOURCE_GEOMETRY_UNPROVEN"
                    if not matches
                    else "UNKNOWN_LEGACY_RAW_EVENT_NONUNIQUE"
                ],
            )
        rows.append(
            {
                **old,
                "setup_tf": tf,
                "decision_at": at,
                "status": status,
                "raw_event_match_count": len(matches),
                "source_gaps": gaps,
                "source_stop_anchor": details["source_stop_anchor"]
                if details
                else None,
                "source_rule_trace": details["source_rule_trace"] if details else [],
                "outcomes_used": False,
                "trade_entry_allowed": False,
            }
        )
    if len(rows) != 880 or len({r["signal_id"] for r in rows}) != 880:
        raise ValueError("Old880 identity roster changed")
    return rows


def run(output):
    if (output / "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json").exists():
        raise ValueError(
            "Completed stage preserved; use --resume-existing or fresh --replay-output"
        )
    parents = verify_parents()
    data, audit = load_market()
    metadata = json.loads(
        (RECOVERY / "HISTORICAL_INSTRUMENT_METADATA_v2.json").read_text()
    )
    tree = load_tree()
    indices = {}
    for symbol, frames in data.items():
        indices[symbol] = {}
        for tf, bars in frames.items():
            indices[symbol][tf] = CompletionIndex(symbol, tf, bars)
            print(
                "Completion index",
                symbol,
                tf,
                len(indices[symbol][tf].ordered),
                flush=True,
            )
    output.mkdir(parents=True, exist_ok=True)
    object_counts = Counter()
    for symbol, frames in indices.items():
        for tf, index in frames.items():
            write_rows(output / f"CAUSAL_OBJECTS/{symbol}_{tf}.jsonl.gz", index.ordered)
            object_counts.update(o["kind"] for o in index.ordered)
    counts, gaps, components, units, lookup = (
        Counter(),
        Counter(),
        Counter(),
        {},
        defaultdict(list),
    )
    unit_branches, unit_tfs, branches, views = (
        Counter(),
        Counter(),
        Counter(),
        Counter(),
    )
    raw_digest = sha256()
    parity_checked = set()
    with ExitStack() as stack:
        writers = {}
        for name in OUTPUTS:
            rawfile = stack.enter_context((output / name).open("wb"))
            writers[name] = stack.enter_context(
                gzip.GzipFile(filename="", mode="wb", fileobj=rawfile, mtime=0)
            )
        rawstream = stack.enter_context(
            gzip.open(OUT / "result/all_raw_proposals.jsonl.gz", "rt")
        )
        v2stream = stack.enter_context(
            gzip.open(V2 / "OBJECTIVE_EVIDENCE_CASES.jsonl.gz", "rt")
        )
        for n, (raw, oldline, v2line) in enumerate(
            zip_longest(all_proposals(data), rawstream, v2stream), 1
        ):
            if (
                raw is None
                or oldline is None
                or v2line is None
                or raw != json.loads(oldline)
            ):
                raise ValueError("Frozen raw cohort mismatch")
            raw_digest.update((compact(raw) + "\n").encode())
            initial = raw["decision_at"]
            index = indices[raw["symbol"]][raw["setup_tf"]]
            lookup[
                (
                    raw["symbol"],
                    raw["setup_tf"],
                    raw["branch"],
                    raw["direction"],
                    initial,
                )
            ].append(raw)
            nxt = (
                index.geometry.next_open(initial, END)
                if raw["branch"] == "SFP"
                else None
            )
            candidate = {
                **raw,
                "formation_at": initial,
                "decision_at": nxt["known_at"] if nxt else initial,
            }
            old = json.loads(v2line)
            for key in (
                "candidate_id",
                "symbol",
                "branch",
                "direction",
                "setup_tf",
                "decision_at",
                "formation_at",
            ):
                if candidate[key] != old[key]:
                    raise ValueError("Frozen candidate/cutoff changed: " + key)
            row = inspect_candidate(candidate, indices, metadata, tree)
            parity_key = (row["symbol"], row["branch"], row["setup_tf"])
            if parity_key not in parity_checked:
                shadow = inspect_candidate(
                    candidate, indices, metadata, tree, mode="SHADOW"
                )
                if shadow != row:
                    raise ValueError(
                        "Historical BACKTEST/SHADOW source evidence mismatch"
                    )
                parity_checked.add(parity_key)
            no_outcomes(row)
            for view in row["source_fta_inventory"]["prefixes"].values():
                if (
                    view["last_completed_at"] is not None
                    and view["last_completed_at"] > row["decision_at"]
                ):
                    raise ValueError("Future candle exposed")
            counts[row["status"]] += 1
            gaps.update(row["source_gaps"])
            components.update(row["source_component_counts"])
            branches[row["branch"]] += 1
            encoded = (compact(row) + "\n").encode()
            writers[OUTPUTS[0]].write(encoded)
            selected = {
                "QUALITATIVE_UNKNOWN": OUTPUTS[1],
                READY: OUTPUTS[2],
                "OBJECTIVE_SOURCE_FAIL": OUTPUTS[3],
                "QUALITATIVE_FAIL": OUTPUTS[3],
                "WAIT_NO_AVAILABLE_LOWER_TF": OUTPUTS[4],
                "OTHER_SOURCE_WAIT": OUTPUTS[5],
            }[row["status"]]
            # Subsets reference the immutable full case to avoid duplicate full ledgers.
            ref = {
                k: row[k]
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
            ref["case_ledger"] = OUTPUTS[0]
            writers[selected].write((compact(ref) + "\n").encode())
            if row["status"] in (
                "QUALITATIVE_UNKNOWN",
                "QUALITATIVE_FAIL",
                READY,
                "OTHER_SOURCE_WAIT",
            ):
                signature = annotation_signature(row)
                key = digest(signature)
                if key in units:
                    if units[key]["material_signature_sha256"] != key:
                        raise ValueError("Annotation signature mismatch")
                    units[key]["candidate_ids"].append(row["candidate_id"])
                    units[key]["why_safe_to_group"] = (
                        "Proven physical/setup identity and every material field/question/visible prefix identical"
                    )
                else:
                    units[key] = annotation_unit([row])
                    unit_branches[row["branch"]] += 1
                    unit_tfs[str(row["setup_tf"])] += 1
                counts["QUALITATIVE_CANDIDATES"] += 1
                views[(row["symbol"], row["setup_tf"], row["decision_at"])] += 1
            if n % 20000 == 0:
                print("Source evidence completion", n, flush=True)
    if (
        sum(counts[s] for s in STATUSES) != 176365
        or counts["WAIT_NO_AVAILABLE_LOWER_TF"] != 45266
    ):
        raise ValueError("Cohort partition/coverage changed")
    write_rows(
        output / "ANNOTATION_UNIT_MAP.jsonl.gz", (units[k] for k in sorted(units))
    )
    sizes = [len(u["candidate_ids"]) for u in units.values()]
    old = old880(indices, metadata, tree, lookup)
    write_csv(output / "OLD880_EVIDENCE_RECHECK_V3.csv", old, list(old[0]))
    funnel = {
        "version": "SOURCE_EVIDENCE_COMPLETION_v3",
        "RAW_PROPOSALS": sum(counts[s] for s in STATUSES),
        **{s: counts[s] for s in STATUSES},
        "QUALITATIVE_CANDIDATES": counts["QUALITATIVE_CANDIDATES"],
        "UNIQUE_ANNOTATION_UNITS": len(units),
        "QUALITATIVE_PASS": 0,
        "QUALITATIVE_UNKNOWN": counts["QUALITATIVE_UNKNOWN"],
        "HISTORICAL_METADATA_BLOCKED": 176365,
        "SOURCE_ALLOW": 0,
        "SOURCE_DECISION_READY_FOR_FINANCE": 0,
        "annotation_units": {
            "average_candidates_per_unit": sum(sizes) / len(sizes),
            "median_candidates_per_unit": median(sizes),
            "max_group_size": max(sizes),
            "branch_distribution": dict(unit_branches),
            "TF_distribution": dict(unit_tfs),
            "distinct_raw_visible_views": len(views),
            "shared_raw_views_do_not_prove_source_equivalence": True,
        },
        "parallel_source_gaps": dict(gaps.most_common()),
        "source_components_complete": dict(components),
        "objective_object_counts": dict(object_counts),
        "branch_totals": dict(branches),
        "old880_counts": dict(Counter(r["status"] for r in old)),
        "raw_cohort_sha256": raw_digest.hexdigest(),
        "frozen_raw_and_v2_decision_cutoff_equality": "PASS",
        "historical_mode_parity": {
            "status": "PASS",
            "distinct_symbol_branch_TF_checks": len(parity_checked),
        },
        "historical_source_annotations_loaded": 0,
        "metadata_role": "PARALLEL_EXECUTION_BLOCKER",
        "HISTORICAL_METADATA_VERIFIED": False,
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "trade_entry_allowed": False,
    }
    save(output / "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json", funnel)
    save(output / "DATASET_VERIFICATION.json", audit)
    save(output / "PARENT_INVARIANCE.json", parents)
    print(
        compact(
            {
                s: funnel[s]
                for s in (
                    "RAW_PROPOSALS",
                    "QUALITATIVE_CANDIDATES",
                    "UNIQUE_ANNOTATION_UNITS",
                    *STATUSES,
                )
            }
        ),
        flush=True,
    )
    return funnel


def resume():
    manifest = json.loads((DEST / "freeze_manifest.json").read_text())
    actual = {
        str(p.relative_to(ROOT))
        for p in DEST.rglob("*")
        if p.is_file() and p.name != "freeze_manifest.json"
    }
    declared = {
        n
        for n in manifest["artifacts"]
        if n.startswith(str(DEST.relative_to(ROOT)) + "/")
    }
    if actual != declared:
        raise ValueError("Sealed namespace membership changed")
    for name, expected in manifest["artifacts"].items():
        if checksum(ROOT / name) != expected:
            raise ValueError("Frozen v3 artifact changed: " + name)
    verify_parents()
    load_market()
    print(
        "VERIFIED_RESUME SOURCE_EVIDENCE_COMPLETION_v3",
        len(manifest["artifacts"]),
        "artifacts; finance NOT_RUN",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--resume-existing", action="store_true")
    group.add_argument("--replay-output", type=Path)
    args = parser.parse_args()
    if args.resume_existing:
        resume()
    else:
        run(args.replay_output or DEST)


if __name__ == "__main__":
    main()
