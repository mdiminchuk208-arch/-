"""Offline execution-minimum provenance review; no financial or exchange API runner."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from audit_original_v1_1_metadata_recovery_v2 import (
    END,
    START,
    validate_provenance,
)
from original_v1_1_financial_data import ROOT, checksum, save
from original_v1_1_staged_research_common import (
    read,
    seal,
    validate_qa,
    verify_originals,
    verify_stage,
)

DEST = ROOT / "docs/original_v1_1_execution_metadata_v3"
EVIDENCE = ROOT / "docs/original_v1_1_evidence_completion_v4"
RECOVERY = ROOT / "docs/original_v1_1_metadata_recovery_v2"
EVIDENCE_SHA = "ab55a6f99cc6acdd3cc55be23b21f14e8d9fe7768896dc8b521478dca4acde6b"
EVIDENCE_COMMIT = "3d4aa7e6bda90974538bdf66b9d1d703e1aad605"
ANNOTATION_COMMIT = "601f4330c9321fcebe000f63dbafef349b4eb4c9"
CODE = [
    "scripts/original_v1_1_execution_metadata_v3.py",
    "tests/test_original_v1_1_execution_metadata_v3.py",
]
FILES = [
    "EXECUTION_FIELD_REQUIREMENTS.json",
    "PRIMARY_METADATA_SOURCE_REVIEW.json",
    "VERIFIED_PRICE_EXECUTION_INTERVALS.json",
    "VERIFIED_QTY_EXECUTION_INTERVALS.json",
    "NORMALIZED_R_ELIGIBLE_INTERVALS.json",
    "UNKNOWN_INTERVALS.json",
    "METADATA_GATE_STATUS.json",
    "MASTER_STAGE_GATE_REPORT.json",
    "PARENT_INVARIANCE.json",
    "provenance/ETHUSDT_official_notice.text.txt",
    "provenance/BTCUSDT_official_notice.text.txt",
]
PRICE_FIELDS = (
    "tick_size",
    "effective_tick_periods",
    "contract_identity",
    "contract_type",
    "linear_perpetual",
)
SIZE_FIELDS = ("qty_step", "minimum_qty", "quantity_precision")
DESCRIPTIVE_FIELDS = ("base_asset", "quote_asset", "price_precision")
MODE = "NORMALIZED_R_BACKTEST_WITHOUT_EXCHANGE_QTY_EXECUTION"


def field_requirements():
    return {
        "accounting_mode": MODE,
        "status": "ELIGIBILITY_CONTRACT_ONLY_NOT_FINANCIAL_PREREGISTRATION",
        "fields": {
            **{
                f: {
                    "classification": "PRICE_EXECUTION_CRITICAL",
                    "normalized_R": "REQUIRED",
                    "exchange_execution": "REQUIRED",
                }
                for f in PRICE_FIELDS
            },
            **{
                f: {
                    "classification": "SIZE_EXECUTION_CRITICAL",
                    "normalized_R": "NOT_REQUIRED_FOR_THIS_ACCOUNTING_VIEW",
                    "exchange_execution": "REQUIRED",
                }
                for f in SIZE_FIELDS
            },
            **{
                f: {
                    "classification": "DESCRIPTIVE",
                    "normalized_R": "NOT_REQUIRED_FOR_THIS_ACCOUNTING_VIEW",
                    "exchange_execution": "REQUIRED_BY_UNCHANGED_FROZEN_ADAPTER",
                }
                for f in DESCRIPTIVE_FIELDS
            },
        },
        "quantity_omission_proof": "For an explicitly linear contract, gross price PnL=q*direction*(exit-entry) and initial price risk=q*abs(entry-stop). With proportional fees and proportional price slippage, every monetary term and denominator scales with q>0, so q cancels in R. This does not prove an executable exchange lot, actual monetary account PnL, fee tier or funding cost. No fixed monetary charges may be silently omitted.",
        "price_tick_requirement": "Entry/stop/FTA source prices and historical tick rounding must be deterministic. No candle-decimal inference, dummy tick, current-API backdating or fabricated effective periods.",
        "descriptive_omission_limits": "Exact symbol/contract identity and linearity remain REQUIRED. Base/quote names do not affect dimensionless R; no currency-valued PnL claim. Separate display price_precision is redundant only when an exact verified Decimal tick defines the price lattice. No quantity values are imputed.",
        "source_price_requirement": "Stage 4 source-complete entry, fixed stop and contextual FTA/Range prices, branch/first-test/chronology proof required for each case; interval eligibility alone never admits a case.",
        "funding_and_costs": "Not calculated here. A Stage 5 preregistration must specify proportional cost/funding conventions and unknown-cost treatment before any financial outcome.",
        "frozen_metadata_adapter_modified": False,
        "trade_entry_allowed": False,
    }


def interval_eligible(record, *, accounting=MODE):
    """Explicit proof contract, separate from the frozen nine-field adapter."""
    if accounting not in (MODE, "EXCHANGE_SIZE_EXECUTION"):
        raise ValueError("Unknown accounting view")
    a, b = record.get("effective_from"), record.get("effective_to")
    known = record.get("historical_known_at")
    if not (
        type(a) is int
        and type(b) is int
        and type(known) is int
        and a < b
        and known <= a
    ):
        return False
    proof = record.get("proof", {})
    if not all(
        proof.get(k) is True
        for k in (
            "historical_version_verified",
            "effective_period_verified",
            "exact_contract_verified",
            "price_filter_verified",
        )
    ):
        return False
    values = record.get("values", {}) or {}
    if (
        any(values.get(f) is None for f in PRICE_FIELDS)
        or values["linear_perpetual"] is not True
        or values["contract_identity"] != record.get("symbol")
        or values["contract_type"] != "USDT Perpetual"
        or values["effective_tick_periods"] != [a, b]
    ):
        return False
    from decimal import Decimal, InvalidOperation

    try:
        tick = Decimal(str(values["tick_size"]))
        if not tick.is_finite() or tick <= 0:
            return False
    except InvalidOperation:
        return False
    return accounting != "EXCHANGE_SIZE_EXECUTION" or (
        proof.get("quantity_filter_verified") is True
        and all(values.get(f) is not None for f in SIZE_FIELDS + DESCRIPTIVE_FIELDS)
    )


def literal_detail(path):
    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        path.read_text(),
        re.DOTALL,
    )
    if not match:
        raise ValueError("Missing official notice structured body")
    detail = json.loads(match[1])["props"]["pageProps"].get("articleDetail", {})
    pieces = []

    def gather(value):
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                pieces.append(value["text"])
            for key, child in value.items():
                if key != "text":
                    gather(child)
        elif isinstance(value, list):
            for child in value:
                gather(child)

    gather(detail.get("content", {}))
    return detail, "\n".join(pieces) + "\n"


def review_sources(output):
    _, documents, notices, partial = validate_provenance()
    receipt = read(DEST / "provenance/TARGETED_RETRIEVAL_RECEIPT.json")
    if (
        receipt["broad_metadata_search_repeated"]
        or receipt["third_party_API_called"]
        or not receipt["proxy_and_TLS_preserved"]
    ):
        raise ValueError("Unexpected retrieval method")
    requests = {r["symbol"]: r for r in receipt["requests"]}
    results = []
    for old in partial["partial_source_observations"]:
        fresh = requests[old["symbol"]]
        if (
            fresh["url"] != old["source_url"]
            or fresh["http_status"] != "200"
            or fresh["exit_code"] != 0
            or fresh["private_API"]
            or fresh["exchange_secrets_sent"]
        ):
            raise ValueError("Targeted primary notice receipt mismatch")
        for key in ("body", "headers"):
            if checksum(ROOT / fresh[key + "_file"]) != fresh[key + "_sha256"]:
                raise ValueError("Retrieved provenance hash changed")
        detail, literal = literal_detail(ROOT / fresh["body_file"])
        same = literal == (ROOT / old["literal_text_file"]).read_text()
        if (
            not same
            or detail.get("title") != old["article_title"]
            or detail.get("date") != old["page_published_date"]
        ):
            raise ValueError("Changed primary notice needs a new source review")
        target = output / "provenance" / (old["symbol"] + "_official_notice.text.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(literal)
        results.append(
            {
                "symbol": old["symbol"],
                "source_url": old["source_url"],
                "previous_literal_sha256": old["literal_text_sha256"],
                "current_literal_sha256": checksum(target),
                "literal_body_unchanged": same,
                "title": detail["title"],
                "page_claimed_publication": detail["date"],
                "title_date": old["title_claimed_date"],
                "announced_effective_date": old["body_claimed_date"],
                "announced_tick_before": old["tick_size_before"],
                "announced_tick_after": old["tick_size_after"],
                "contract_type_literal": old["contract_type_literal"],
                "date_interpretation": "Publication/title and announced effective date may legitimately differ. The difference alone is not evidence that the change is false. Neither publication nor title date is substituted for actual filter effectiveness.",
                "verified_historical_version_at_publication": False,
                "verified_implemented_filter_period": False,
                "verified_quantity_period": False,
                "historical_known_at": None,
                "assessment": "CURRENT_OFFICIAL_ANNOUNCEMENT_OF_CHANGE_ONLY",
                "blocker": "No contemporaneously versioned historical filter observation or immutable announcement version; no bounded implemented tick period. Current page body is observed in 2026 and cannot be backdated to scoring history.",
                "missing_size_fields_irrelevant_to_normalized_R": list(SIZE_FIELDS),
                "admitted_interval": False,
            }
        )
    if len(results) != 2:
        raise ValueError("Missing exact-symbol notice")
    return {
        "saved_official_parameter_articles_reviewed": len(notices["articles"]),
        "saved_official_documentation_examples_reviewed": len(documents),
        "exact_symbol_tick_notices": results,
        "rejected_substring": "NEIROETHUSDT is not ETHUSDT",
        "documentation_examples": "Five existing official dated examples are documentation payloads, not contemporaneously observed production filter epochs. No historical values admitted.",
        "scope_of_search": "Existing complete saved provenance reused; only two targeted official public GETs. No archive/current API/broad search repetition.",
        "trade_entry_allowed": False,
    }


def build(output):
    if (output / "METADATA_GATE_STATUS.json").exists():
        raise ValueError("Existing outputs preserved")
    parents = verify_originals()
    parents["evidence_v4"] = verify_stage(EVIDENCE, expected_sha=EVIDENCE_SHA)
    output.mkdir(parents=True, exist_ok=True)
    review = review_sources(output)
    requirements = field_requirements()
    save(output / FILES[0], requirements)
    save(output / FILES[1], review)
    for name in FILES[2:5]:
        save(
            output / name,
            {
                "scope": [START, END],
                "interval_convention": "[effective_from,effective_to)",
                "records": [],
                "verified_intervals": 0,
                "trade_entry_allowed": False,
            },
        )
    unknown = {
        "scope": [START, END],
        "scope_UTC": ["2023-01-01 00:00:00 UTC", "2025-12-05 23:30:00 UTC inclusive"],
        "records": [],
    }
    for symbol in ("BTCUSDT", "ETHUSDT"):
        row = {
            "symbol": symbol,
            "effective_from": START,
            "effective_to": END,
            "status": "UNKNOWN",
            "historical_known_at": None,
            "values": None,
            "PRICE_EXECUTION_CRITICAL": "UNKNOWN_PERIOD_PROOF",
            "SIZE_EXECUTION_CRITICAL": "UNKNOWN_FOR_EXCHANGE_EXECUTION",
            "normalized_R_size_fields": "NOT_REQUIRED_FOR_THIS_ACCOUNTING_VIEW",
            "missing_normalized_R_price_fields": list(PRICE_FIELDS),
            "proof": {
                "historical_version_verified": False,
                "effective_period_verified": False,
                "exact_contract_verified": False,
                "price_filter_verified": False,
            },
            "reason": "Partial announced tick changes and descriptive contract labels do not establish causally versioned implemented filter intervals. Removing quantity requirements leaves price tick/period proof unresolved.",
            "trade_entry_allowed": False,
        }
        if interval_eligible(row) or interval_eligible(
            row, accounting="EXCHANGE_SIZE_EXECUTION"
        ):
            raise ValueError("Unknown interval incorrectly admitted")
        unknown["records"].append(row)
    save(output / FILES[5], unknown)
    status = {
        "VERIFIED_PRICE_EXECUTION_INTERVALS": 0,
        "VERIFIED_QTY_EXECUTION_INTERVALS": 0,
        "NORMALIZED_R_ELIGIBLE_INTERVALS": 0,
        "UNKNOWN_SYMBOL_INTERVALS": 2,
        "HISTORICAL_METADATA_VERIFIED": False,
        "GATE_3": "STOP_NO_CAUSALLY_VERIFIED_PRICE_TICK_INTERVAL",
        "normalized_R_mode_authorized_for_future_preregistration": True,
        "accounting_mode_preregistered": False,
        "exchange_realistic_sizing_claim": False,
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "trade_entry_allowed": False,
    }
    save(output / FILES[6], status)
    source = read(EVIDENCE / "SOURCE_EVIDENCE_COMPLETION_FUNNEL.json")
    if source["SOURCE_READY_EXCEPT_EXECUTION_METADATA"] != 0:
        raise ValueError(
            "Positive source cohort requires a new dependent gate assessment"
        )
    stages = [
        {
            "stage": 1,
            "status": "FROZEN_QUALITATIVE_UNKNOWN",
            "commit": ANNOTATION_COMMIT,
            "manifest_sha256": read(EVIDENCE / "freeze_manifest.json")["parent"][
                "annotation_manifest_sha256"
            ],
            "candidates": 131099,
            "annotations": 2186597,
            "next_gate": "SOURCE_COMPLETION_REQUIRED",
        },
        {
            "stage": 2,
            "status": source["GATE_2"],
            "commit": EVIDENCE_COMMIT,
            "manifest_sha256": EVIDENCE_SHA,
            "RAW_PROPOSALS": source["RAW_PROPOSALS"],
            "QUALITATIVE_UNKNOWN": source["QUALITATIVE_UNKNOWN"],
            "WAIT_NO_AVAILABLE_LOWER_TF": source["WAIT_NO_AVAILABLE_LOWER_TF"],
            "SOURCE_READY_EXCEPT_EXECUTION_METADATA": 0,
            "next_gate": "SOURCE_READY_GT_0",
        },
        {
            "stage": 3,
            "status": status["GATE_3"],
            "commit": None,
            "commit_resolution": "Containing git commit of this namespace freeze_manifest.json",
            "manifest_sha256": None,
            "manifest_resolution": "SHA256 of this namespace freeze_manifest.json, computed externally after seal to avoid self-reference",
            "VERIFIED_PRICE_EXECUTION_INTERVALS": 0,
            "NORMALIZED_R_ELIGIBLE_INTERVALS": 0,
            "next_gate": "CAUSALLY_VERIFIED_PRICE_TICK_INTERVAL_REQUIRED",
        },
    ]
    names = (
        "FINAL_SOURCE_ALLOW_ASSEMBLY",
        "PRE_OUTCOME_FINANCIAL_FREEZE",
        "SECOND_FINANCIAL_BACKTEST",
        "ROBUSTNESS_STABILITY",
        "PROJECT_OVERLAYS_DIAGNOSTIC",
        "PAPER_TRADING_READINESS",
    )
    stages.extend(
        {
            "stage": i,
            "name": name,
            "status": "BLOCKED_NOT_RUN",
            "commit": None,
            "manifest_sha256": None,
            "next_gate": "SOURCE_AND_PRICE_EXECUTION_GATES_REQUIRED",
        }
        for i, name in enumerate(names, 4)
    )
    save(
        output / FILES[7],
        {
            "stages": stages,
            "latest_source_ready": 0,
            "FINAL_SOURCE_ALLOW_CASES": 0,
            "final_source_allow_cohort_frozen": False,
            "zero_allow_basis": "Empty source-ready set implies empty possible intersection; Stage 4 was not run or frozen.",
            "SECOND_FINANCIAL_BACKTEST_RAN": False,
            "financial_metrics": None,
            "robustness_verdict": "NOT_AVAILABLE_NO_SECOND_FINANCIAL_RESULT",
            "project_overlays": "BLOCKED_NOT_RUN",
            "PAPER_TRADING_READY": False,
            "paper_readiness_assessed_as_completed_stage": False,
            "paper_readiness_reason": "No second financial result or qualified 200 CLOSED/30-day virtual record established by this workflow; no paper launch authorized.",
            "STOP_REASONS": [source["GATE_2"], status["GATE_3"]],
            "source_blocker": "No unique source-validated context/protected endpoints/contextual entry/FTA/first-test and physical/setup identity; material qualitative predicates UNKNOWN. No numeric/discretionary selector invented.",
            "metadata_blocker": "Historical implemented tick epochs and causal version availability unverified even with quantity omitted for normalized R.",
            "future_progress_requires": [
                "Causally blinded source attestations for material relations, with exact canonical IDs and source citations; a new annotation/evidence freeze",
                "Contemporaneous or immutably versioned exact-contract price filter epoch proof; separate metadata freeze",
            ],
            "trade_entry_allowed": False,
        },
    )
    save(output / FILES[8], parents)
    print("EXECUTION_METADATA_V3_COMPLETE", status["GATE_3"], flush=True)


def validate(replay):
    verify_stage(EVIDENCE, expected_sha=EVIDENCE_SHA)
    qa = validate_qa(DEST, CODE, replay, FILES, minimum_tests=866)
    (DEST / "QA_REPORT.md").write_text(f"""# Execution metadata v3 QA

PASS: {qa["tests"]} inherited/new tests; {len(FILES)} deterministic outputs byte-identical.
All 72 saved primary derivative notices and 5 official documentation examples hash-verified. Two targeted public official notices retain complete bodies/headers/UTC receipt; literal bodies match prior provenance.
Publication/title versus announced effectiveness are separated. No 2026 observation is backdated, no candle-decimal tick inference, no fabricated implementation epochs or dummy quantity values.
Normalized R quantity omission explicitly classified with linear proportional-cost algebra; historical tick/contract/epoch proof remains mandatory. This is an eligibility contract, not a financial preregistration or financial run.
Full scope covered by two UNKNOWN symbol intervals; neither accounting mode admits them. Regression tests exercise positive proof contracts and missing/future/invalid evidence rejection.
Inherited candle/known_at/prefix mutation/canonical identity/source registry and BACKTEST/SHADOW tests pass. Immutable strategy/evidence/recovery/first result/dataset/baseline/audit hashes verified.
Dependent stages 4–9 BLOCKED_NOT_RUN. No financial metrics fabricated; PAPER_TRADING_READY=false. No LIVE/private API. trade_entry_allowed=false.
""")
    print("EXECUTION_METADATA_V3_QA_PASS", qa["tests"], flush=True)


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
        verify_stage(EVIDENCE, expected_sha=EVIDENCE_SHA)
        verify_originals()
        print("VERIFIED_RESUME EXECUTION_METADATA_v3")
    elif args.seal:
        seal(
            DEST,
            CODE,
            name="HISTORICAL_EXECUTION_METADATA_v3",
            parent={
                "evidence_v4_manifest_sha256": EVIDENCE_SHA,
                "recovery_manifest_sha256": checksum(
                    RECOVERY / "recovery_manifest.json"
                ),
            },
            status=read(DEST / FILES[6])["GATE_3"],
        )
    elif args.validate_replay:
        validate(args.validate_replay)
    else:
        build(args.replay_output or DEST)


if __name__ == "__main__":
    main()
