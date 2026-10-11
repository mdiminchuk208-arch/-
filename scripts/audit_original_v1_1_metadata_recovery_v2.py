"""Audit the Stage A STOP delivery. No financial runner or trading API is called."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from hashlib import sha256
from pathlib import Path

from original_v1_1_evidence_adapter_v2 import metadata_at
from run_original_v1_1_evidence_adapter_v2 import verify_freeze

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/original_v1_1_metadata_recovery_v2"
PARENT = ROOT / "docs/original_v1_1_evidence_adapter_v2"
START, END = 1672531200, 1764977401
PARENT_COMMIT = "29f6eacb18e6b09fe87ca372f2d697cf45c27e48"
PARENT_SHA = "79b922c5b9f9008acda333ce768330aa2c2687470d09c22936632b92783a4283"
STOP_REASON = "NO_VERIFIED_HISTORICAL_INSTRUMENT_METADATA"
REQUIRED = [
    "tick_size",
    "price_precision",
    "qty_step",
    "quantity_precision",
    "minimum_qty",
    "contract_type",
    "linear_perpetual",
    "base_asset",
    "quote_asset",
]
CODE = [
    "scripts/collect_original_v1_1_metadata_recovery_v2.py",
    "scripts/collect_original_v1_1_metadata_announcements_v2.py",
    "scripts/audit_original_v1_1_metadata_recovery_v2.py",
    "tests/test_original_v1_1_metadata_recovery_v2.py",
]
REPLAY_FILES = [
    "HISTORICAL_INSTRUMENT_METADATA_v2.json",
    "STAGE_A_STOP_STATUS.json",
    "HISTORICAL_METADATA_EVIDENCE_REPORT.md",
    "REPRODUCIBILITY.md",
]


def digest(path):
    hashed = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def verified_file(name, expected):
    if digest(ROOT / name) != expected:
        raise ValueError("Evidence hash changed: " + name)


def validate_provenance():
    provenance = DEST / "provenance"
    search = read(provenance / "HISTORICAL_METADATA_SEARCH_RECEIPT_v2.json")
    documents = read(provenance / "OFFICIAL_DOCUMENT_EXAMPLE_ASSESSMENT.json")
    notices = read(provenance / "ANNOUNCEMENT_RECOVERY_RECEIPT.json")
    partial = read(provenance / "PARTIAL_METADATA_SOURCE_ASSESSMENT.json")
    for source in documents:
        verified_file(source["file"], source["document_sha256"])
        if (
            source["period_proof"] is not False
            or source["effective_from"] is not None
            or source["effective_to"] is not None
        ):
            raise ValueError(
                "Documentation example incorrectly promoted to interval proof"
            )
        if any(
            r["admissible_as_historical_interval"] is not False
            for r in source["response_projection"]
        ):
            raise ValueError("Unreviewed document sample admission")
    for record in search["searches"]:
        if "output" in record and "sha256" in record:
            verified_file(record["output"], record["sha256"])
        for matched in record.get("matched_files", []):
            verified_file(matched["path"], matched["sha256"])
    for record in notices["articles"]:
        verified_file(record["file"], record["file_sha256"])
        if record["http_code"] != "200" or record["exit_code"] != 0:
            raise ValueError("Unreviewed missing announcement")
        verified_file(record["text_file"], record["text_sha256"])
        literal = (ROOT / record["text_file"]).read_text()
        for symbol in ("BTCUSDT", "ETHUSDT"):
            exact = bool(
                re.search(r"(?<![A-Z0-9])" + symbol + r"(?![A-Z0-9])", literal)
            )
            if record["mentions_" + symbol] != exact:
                raise ValueError("Substring is not exact contract identity")
    for record in partial["partial_source_observations"]:
        verified_file(record["source_file"], record["source_sha256"])
        verified_file(record["literal_text_file"], record["literal_text_sha256"])
        if (
            record["effective_period_proof"] is not False
            or record["admitted_as_VERIFIED_interval"] is not False
            or record["historical_known_at"] is not None
        ):
            raise ValueError(
                "Current notice/date discrepancy cannot prove historical known interval"
            )
    if partial["verified_historical_instrument_intervals"] != 0:
        raise ValueError(
            "New proof requires a new audit; this delivery records a zero-interval STOP"
        )
    if len(documents) != 5 or len(notices["articles"]) != 72:
        raise ValueError("Incomplete recovery collection")
    return search, documents, notices, partial


def make_metadata(partial):
    if partial["verified_historical_instrument_intervals"] != 0:
        raise ValueError(
            "This builder must not suppress newly recovered interval proof"
        )
    return {
        "version": "2",
        "scope": [START, END],
        "intervals": "[effective_from,effective_to)",
        "scope_UTC": ["2023-01-01 00:00:00 UTC", "2025-12-05 23:30:00 UTC inclusive"],
        "verification_status_mapping": {
            "VERIFIED": "VERIFIED_HISTORICAL (frozen adapter contract)",
            "UNKNOWN": "UNKNOWN",
        },
        "metadata_verified_periods": 0,
        "verdict": "UNKNOWN_ALL_REQUESTED_PERIODS",
        "required_values": REQUIRED,
        "required_interval_fields": ["effective_from", "effective_to"],
        "records": [
            {
                "symbol": symbol,
                "effective_from": START,
                "effective_to": END,
                "status": "UNKNOWN",
                "verification_status": "UNKNOWN",
                "values": None,
                "missing_verified_values": REQUIRED,
                "provenance": {
                    "effective_period_proof": False,
                    "historical_known_at": None,
                    "authoritative": False,
                    "assessment": "Official partial tick-change notices and dated documentation samples do not prove complete historical filter intervals",
                    "source_assessment": "docs/original_v1_1_metadata_recovery_v2/provenance/PARTIAL_METADATA_SOURCE_ASSESSMENT.json",
                },
            }
            for symbol in ("BTCUSDT", "ETHUSDT")
        ],
        "partial_source_observations": partial["partial_source_observations"],
        "not_inferred_from": [
            "current API",
            "OHLC decimal representation",
            "sample launchTime",
            "documentation commit time",
            "testnet fixture",
            "absence of search hits",
            "current page publication date",
        ],
        "trade_entry_allowed": False,
    }


def validate_stop_map(metadata):
    if (
        metadata["scope"] != [START, END]
        or metadata["metadata_verified_periods"] != 0
        or metadata["trade_entry_allowed"] is not False
    ):
        raise ValueError("Unsafe or incomplete Stage A metadata map")
    records = metadata["records"]
    if len(records) != 2 or {r["symbol"] for r in records} != {"BTCUSDT", "ETHUSDT"}:
        raise ValueError("Exact symbol coverage required")
    for record in records:
        if (
            record["effective_from"] != START
            or record["effective_to"] != END
            or record["status"] != "UNKNOWN"
            or record["verification_status"] != "UNKNOWN"
            or record["values"] is not None
            or set(record["missing_verified_values"]) != set(REQUIRED)
            or record["provenance"]["effective_period_proof"] is not False
            or record["provenance"]["historical_known_at"] is not None
        ):
            raise ValueError("Unproved values or interval gap in Stage A STOP map")
        for at in (START, START + 1, (START + END) // 2, END - 1, END):
            if metadata_at(metadata, record["symbol"], at) is not None:
                raise ValueError("Unknown record passed frozen metadata gate")
    for observation in metadata["partial_source_observations"]:
        if (
            observation["admitted_as_VERIFIED_interval"] is not False
            or observation["effective_period_proof"] is not False
        ):
            raise ValueError("Partial observation incorrectly admitted")
    return 0


def make_status(metadata, inherited):
    validate_stop_map(metadata)
    return {
        "status": "STOP",
        "exact_stop_stage": "STAGE_A_GATE_A",
        "STOP_REASON": STOP_REASON,
        "metadata_verified_periods": 0,
        "metadata_UNKNOWN_intervals": 2,
        "metadata_coverage": "BTCUSDT and ETHUSDT entire requested interval UNKNOWN",
        "annotation_units": None,
        "annotation_unit_status": "NOT_RUN_STAGE_C_BLOCKED_BY_GATE_A",
        "raw_qualitative_candidates": inherited["QUALITATIVE_REQUIRED"],
        "evidence_complete": inherited["EVIDENCE_COMPLETE"],
        "SOURCE_ALLOW": 0,
        "SOURCE_ALLOW_provenance": "Inherited frozen v2 SOURCE_DECISION_READY=0; no new Stage E evaluation",
        "remaining_UNKNOWN_partition": inherited["REMAINING_UNKNOWN"],
        "qualitative_required_partition": inherited["QUALITATIVE_REQUIRED"],
        "critical_metadata_unresolved_candidates": inherited["RAW_PROPOSALS"],
        "count_provenance": "INHERITED_FROZEN_V2_NOT_RECOMPUTED_AT_STAGE_A",
        "inherited_v2_funnel_file": "docs/original_v1_1_evidence_adapter_v2/EVIDENCE_FUNNEL.json",
        "inherited_v2_funnel_sha256": digest(PARENT / "EVIDENCE_FUNNEL.json"),
        "inherited_blocker_breakdown": inherited["gap_counts"],
        "stages": {
            "A": "ATTEMPTED_GATE_FAIL",
            **{stage: "NOT_RUN_GATE_A_STOP" for stage in "BCDEFGH"},
        },
        "Evidence_v3_freeze_created": False,
        "second_preregistration_created": False,
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "financial_outcomes_computed": False,
        "READY_FOR_SECOND_FINANCIAL_BACKTEST": False,
        "trade_entry_allowed": False,
        "production_integration": False,
        "LIVE_private_API": False,
    }


def validate_status(status):
    if (
        status["status"] != "STOP"
        or status["exact_stop_stage"] != "STAGE_A_GATE_A"
        or status["STOP_REASON"] != STOP_REASON
        or status["metadata_verified_periods"] != 0
        or status["annotation_units"] is not None
        or status["evidence_complete"] != 0
        or status["SOURCE_ALLOW"] != 0
        or any(
            status[k] is not False
            for k in (
                "SECOND_FINANCIAL_BACKTEST_RAN",
                "financial_outcomes_computed",
                "trade_entry_allowed",
                "Evidence_v3_freeze_created",
                "second_preregistration_created",
                "READY_FOR_SECOND_FINANCIAL_BACKTEST",
            )
        )
        or any(status["stages"][stage] != "NOT_RUN_GATE_A_STOP" for stage in "BCDEFGH")
    ):
        raise ValueError("STOP semantics changed or unrun stage mislabeled")


def build(output):
    if output.exists() and any((output / name).exists() for name in REPLAY_FILES):
        raise ValueError(
            "Existing outputs preserved; use --resume-existing or a fresh replay directory"
        )
    search, _documents, notices, partial = validate_provenance()
    metadata = make_metadata(partial)
    inherited = read(PARENT / "EVIDENCE_FUNNEL.json")
    status = make_status(metadata, inherited)
    validate_status(status)
    output.mkdir(parents=True, exist_ok=True)
    save(output / REPLAY_FILES[0], metadata)
    save(output / REPLAY_FILES[1], status)
    source_rows = "\n".join(
        "| "
        + " | ".join(
            [
                r["symbol"],
                r["tick_size_before"] + " → " + r["tick_size_after"],
                r["title_claimed_date"],
                r["body_claimed_date"],
                "[" + r["article_title"] + "](" + r["source_url"] + ")",
            ]
        )
        + " |"
        for r in partial["partial_source_observations"]
    )
    (
        output / REPLAY_FILES[2]
    ).write_text(f"""# Historical instrument metadata recovery v2 — Stage A STOP

Gate A FAIL. `STOP_REASON={STOP_REASON}`. `metadata_verified_periods=0`.
`SECOND_FINANCIAL_BACKTEST_RAN=FALSE`. `trade_entry_allowed=false`.

Scope: BTCUSDT / ETHUSDT, Bybit mainnet linear USDT perpetual, 2023-01-01 00:00 UTC through
2025-12-05 23:30 UTC inclusive. The interval map is half-open `[1672531200,1764977401)`;
full metadata is UNKNOWN for both symbols. Individual source observations are retained separately.

## Recovered primary public evidence

Official Bybit docs full Git clone: {search["sources"][0]["reachable_commit_count"]} reachable commits,
HEAD `{search["sources"][0]["pinned_commit"]}`. Official instrument document history: 96 non-merge changes;
full filter diffs and V5 changelog retained. Five full immutable document versions: pre-2023,
end-2023, end-2024, requested end, current. Official pybit clone: {search["sources"][1]["reachable_commit_count"]}
commits, HEAD `{search["sources"][1]["pinned_commit"]}`; no filter/effective-date snapshot found in SDK history.
SDK code/tests were not executed.

Documentation examples include ETHUSDT linear tick 0.05 / qty step 0.01 / min qty 0.01 in December 2022,
BTCUSDT linear tick 0.50 / qty step 0.001 / min qty 0.001 in the 2023 version, then BTC tick 0.10.
Commit `208e13bc0447b0d520593b6872d025264d0a93ae` (2024-02-06) changes the BTC sample tick 0.50→0.10.
That is a documentation edit date, not the exchange parameter effective date.
Saved requests include testnet hosts; examples/server time/launchTime do not prove mainnet historical applicability.
No value is backdated from a current API or candle digits.

The public announcement frontend is reachable. Its ordinary public search endpoint/schema was read from
saved frontend JS; no credentials, cookies, market-API aliases or proxy bypass were used.
Six parameter queries retrieve {notices["unique_search_hits"]} unique indexed hits. All 145 tick-size hits
were retrieved across 3 pages. Five minimum-order-quantity and four trading-parameter hits were also retained;
quantity-step, minimum-order-size, and order-quantity-perpetual queries return zero hits.
All {len(notices["articles"])} selected historical derivative parameter notices were fetched and their complete
literal content inspected. Selection is retrieval triage, not a strategy filter; no lower date bound.
Two exact symbol matches provide partial tick-change evidence:

| Symbol | Tick change stated | Title date | Body date stated | Official primary reference |
| --- | --- | --- | --- | --- |
{source_rows}

The current titles and bodies disagree on dates. Both versions are retained explicitly; no silent date resolver.
A 2024 notice contains NEIROETHUSDT, which is not ETHUSDT and is excluded as an exact-symbol match.
The date on a current mutable announcement page does not prove when its present body was historically known.
No original publication snapshot/version history or confirmation of actual implementation was recovered.
These notices support announced partial changes, not complete VERIFIED instrument intervals.

The linked official 2024-12-27 price-limit announcement is retained in full. It concerns priceLimitRatioX/Y
and trading price limits, not historical tick/qty/minimum/precision interval coverage.
Public instruments GETs for both symbols and the public announcements index return upstream CloudFront
HTTP 403 (geographic restriction). The announcement website/search are separately reachable.
The public web.archive.org CDX attempt is blocked at proxy CONNECT (403 / curl exit 56).
Access restrictions were not bypassed.

## Why Gate A fails

Required tuple: tick_size, price_precision, qty_step, quantity_precision, minimum_qty, contract_type,
linear_perpetual identity, base_asset, quote_asset, effective_from/effective_to. No recovered source proves
this entire tuple on a non-trivial historical interval, together with applicable historical known time.
Tick changes alone do not supply qty step/minimum/precision applicability. Present values cannot fill gaps.
A complete search of this current index cannot prove that deleted/unindexed changes never occurred;
absence of another change notice is not unchanged-period proof.

Repo field/path search, historical manifests, immutable project copies, client/models and synthetic fixtures
supply no authoritative historical instrument snapshot. Searches project paths/hashes only, never monetary
outcomes or legacy SOURCE truth. Negative findings are scoped to these saved/reachable sources; this is not
proof that suitable metadata does not exist elsewhere.

The next required input is authoritative production snapshots or a complete effective-dated parameter record
proving all required fields and known/applicable periods. A partial interval is acceptable when fully proven;
no minimum arbitrary duration, no current-value interpolation, no assumption of unchanged filters.

## Preserved evidence state and STOP boundary

Stage B/C/D/E/F/G/H were not run after Gate A failed. No annotation unit map, Evidence v3 freeze,
second financial preregistration or financial result is created. Annotation units: NOT_RUN, not a measured zero.
The four counts below are inherited unchanged from the frozen v2 funnel, not a new completion run:
RAW 176365; QUALITATIVE_REQUIRED 131099; remaining UNKNOWN partition 45266;
EVIDENCE_COMPLETE 0 / SOURCE_DECISION_READY (SOURCE ALLOW) 0. All 176365 retain critical metadata UNKNOWN.
Necessary objective primitives passing is not complete SOURCE validity. Blocker breakdown remains in
STAGE_A_STOP_STATUS.json with explicit inherited provenance. Old880 is not re-evaluated; prior frozen
102 inactive / 3 qualitative-required / 775 unknown remain preserved, without outcome diagnostics.

Strategy v1/v1.1, U1–U6, N11, active branches, M15/H1/H4/D1, FIRST_TEST_ONLY, stop/FTA/WAIT semantics,
v2 adapter, first result, baseline and audit are unchanged. This recovery namespace is not Evidence v3.
No financial history run, P&L computation, execution, LIVE/private API or production integration.
""")
    (output / REPLAY_FILES[3]).write_text("""# Reproducibility

From repository root, use /workspace/crypto-bot-venv/bin/python.
Offline report generation from saved provenance: python scripts/audit_original_v1_1_metadata_recovery_v2.py --build.
Existing outputs are protected. Fresh offline replay: python scripts/audit_original_v1_1_metadata_recovery_v2.py --replay-output /tmp/metadata_stage_a_replay.
Hash-check frozen delivery, parents and dataset: python scripts/audit_original_v1_1_metadata_recovery_v2.py --resume-existing.
QA and seal: --validate followed by --seal. Neither imports financial accounting nor runs a financial backtest.

Source collection scripts are retained. Initial collector expects complete official Git clones at
/tmp/bybit_metadata_recovery_docs and /tmp/bybit_metadata_recovery_pybit; both remotes and pinned heads are
in provenance/HISTORICAL_METADATA_SEARCH_RECEIPT_v2.json. Use a separate checkout/namespace for any future
collection: sealed namespace cannot be overwritten. Announcement collector uses public search POSTs only,
with schema pinned to the saved public frontend JS. All raw bodies, requests, literal content, commit history,
query counts and partial manual assessment are retained. Transport response cookies are redacted; original
header digests are preserved in the initial search receipt. Report replay consumes saved inputs, not today's web.

Full regression tests include inherited synthetic accounting unit fixtures; this is not financial history execution.
The manifest seals the STOP evidence and its scripts/tests/QA logs; it is not an Evidence v3 financial eligibility freeze.
""")
    return status


def check_parent():
    if digest(PARENT / "freeze_manifest.json") != PARENT_SHA:
        raise ValueError("Pinned Evidence v2 manifest changed")
    verify_freeze(PARENT)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", PARENT_COMMIT, "HEAD"],
        cwd=ROOT,
        check=True,
    )


def validate():
    if (DEST / "recovery_manifest.json").exists():
        raise ValueError("Sealed delivery; use --resume-existing")
    check_parent()
    validate_provenance()
    metadata, status = read(DEST / REPLAY_FILES[0]), read(DEST / REPLAY_FILES[1])
    validate_stop_map(metadata)
    validate_status(status)
    # Reconstruct report bytes from saved inputs; compare all delivery report outputs.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="metadata_stage_a_") as temporary:
        replay = Path(temporary) / "replay"
        build(replay)
        equality = {name: digest(DEST / name) for name in REPLAY_FILES}
        if any(digest(replay / name) != digest(DEST / name) for name in REPLAY_FILES):
            raise ValueError("Offline replay changed")
    logs = {
        name: (DEST / "qa" / (name + ".log")).read_text()
        for name in ("full_unittest", "ruff", "compile", "mypy", "frozen_parent_resume")
    }
    match = re.search(r"Ran (\d+) tests[^\n]*\n\nOK(?:\n|$)", logs["full_unittest"])
    if (
        not match
        or int(match[1]) < 753
        or "FAILED (" in logs["full_unittest"]
        or "skipped=" in logs["full_unittest"]
    ):
        raise ValueError("Regression test gate failed")
    if (
        "All checks passed!" not in logs["ruff"]
        or logs["compile"].strip()
        or "Success: no issues found" not in logs["mypy"]
        or "VERIFIED_RESUME v1.1" not in logs["frozen_parent_resume"]
    ):
        raise ValueError("Required QA failed")
    receipt = {
        "status": "PASS",
        "scope": "Stage A STOP evidence; no new financial result acceptance",
        "full_tests": int(match[1]),
        "frozen_v2_manifest_sha256": PARENT_SHA,
        "strategy_v1_v1_1_first_result_v2_dataset_hashes": "PASS",
        "baseline_source_audit_invariance": "PASS (frozen v1.1 verified resume)",
        "source_registry_causality_canonical_ID_prefix_future_mutation_BACKTEST_SHADOW_parity": "PASS (unchanged frozen code + full regression; no new historical annotation)",
        "metadata_effective_period_correctness": "PASS (complete UNKNOWN map; no partial observation admitted)",
        "no_outcome_leakage": "PASS (metadata-only sources; parent result/baseline bytes hashed, no outcome selection)",
        "replay_files": equality,
        "financial_identity": "NOT_APPLICABLE_SECOND_FINANCIAL_BACKTEST_NOT_RUN",
        "code_sha256": {name: digest(ROOT / name) for name in CODE},
        "qa_log_sha256": {name: digest(DEST / "qa" / (name + ".log")) for name in logs},
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "trade_entry_allowed": False,
    }
    save(DEST / "QA_RECEIPT.json", receipt)
    (DEST / "QA_REPORT.md").write_text(f"""# Stage A QA

PASS. {receipt["full_tests"]} regression tests, zero failures/skips; new Stage A safety/provenance checks included.
Ruff on all new scripts/tests, compileall src/scripts/tests, mypy src: PASS.
Frozen v1/v1.1/v2 and first-result artifact hashes, exact dataset hashes, baseline/Source Audit archive invariance: PASS.
Completed-candle/known_at, prefix/future mutation, canonical IDs, source registry consistency, BACKTEST/SHADOW:
covered by unchanged frozen artifacts and full tests; no new historical SOURCE labels or events were generated.
Effective period coverage and UNKNOWN→no frozen metadata admission: PASS. Exact-symbol notice identification: PASS.
All four report outputs replay byte-identically offline. Source files/literal hashes validated.
No monetary outcomes read into metadata proof; inherited result/baseline verified by hashes only.
Financial identity/intrabar fills/second result acceptance: NOT_APPLICABLE, because Gate A STOP.
SECOND_FINANCIAL_BACKTEST_RAN=FALSE. trade_entry_allowed=false. No LIVE/private API or production integration.
""")
    print(
        "METADATA_STAGE_A_QA_PASS",
        receipt["full_tests"],
        "tests; offline replay 4/4; finance NOT_RUN",
    )


def artifacts():
    return {
        str(p.relative_to(ROOT)): digest(p)
        for p in DEST.rglob("*")
        if p.is_file() and p != DEST / "recovery_manifest.json"
    } | {name: digest(ROOT / name) for name in CODE}


def seal():
    path = DEST / "recovery_manifest.json"
    if path.exists():
        raise ValueError("Existing seal preserved")
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    if branch != "medium-term-source-research":
        raise ValueError("Research branch required")
    receipt = read(DEST / "QA_RECEIPT.json")
    if receipt["status"] != "PASS":
        raise ValueError("QA must pass")
    for name, expected in receipt["code_sha256"].items():
        verified_file(name, expected)
    for name, expected in receipt["qa_log_sha256"].items():
        if digest(DEST / "qa" / (name + ".log")) != expected:
            raise ValueError("QA log changed")
    validate_stop_map(read(DEST / REPLAY_FILES[0]))
    validate_status(read(DEST / REPLAY_FILES[1]))
    payload = artifacts()
    save(
        path,
        {
            "name": "ORIGINAL_v1_1_STAGE_A_METADATA_RECOVERY_v2",
            "status": "STOP_STAGE_A_GATE_A",
            "STOP_REASON": STOP_REASON,
            "parent_evidence_v2_commit": PARENT_COMMIT,
            "parent_evidence_v2_manifest_sha256": PARENT_SHA,
            "strategy_commit": "43e9d7addcd427650ff856dd1fa99f78ee5c06f7",
            "artifacts": dict(sorted(payload.items())),
            "QA": "PASS",
            "QA_tests": receipt["full_tests"],
            "Evidence_v3_freeze_created": False,
            "SECOND_FINANCIAL_BACKTEST_RAN": False,
            "trade_entry_allowed": False,
        },
    )
    print(
        "STOP_STAGE_A_GATE_A", len(payload), "artifacts; manifest SHA256", digest(path)
    )


def resume():
    manifest = read(DEST / "recovery_manifest.json")
    if (
        manifest["status"] != "STOP_STAGE_A_GATE_A"
        or manifest["SECOND_FINANCIAL_BACKTEST_RAN"] is not False
    ):
        raise ValueError("Unsafe manifest")
    if set(artifacts()) != set(manifest["artifacts"]):
        raise ValueError("Sealed namespace membership changed")
    for name, expected in manifest["artifacts"].items():
        verified_file(name, expected)
    check_parent()
    validate_provenance()
    validate_stop_map(read(DEST / REPLAY_FILES[0]))
    validate_status(read(DEST / REPLAY_FILES[1]))
    print(
        "VERIFIED_RESUME STAGE_A_STOP",
        len(manifest["artifacts"]),
        "artifacts; no financial computation",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--replay-output", type=Path)
    group.add_argument("--validate", action="store_true")
    group.add_argument("--seal", action="store_true")
    group.add_argument("--resume-existing", action="store_true")
    args = parser.parse_args()
    if args.build:
        build(DEST)
    elif args.replay_output:
        build(args.replay_output)
    elif args.validate:
        validate()
    elif args.seal:
        seal()
    else:
        resume()


if __name__ == "__main__":
    main()
