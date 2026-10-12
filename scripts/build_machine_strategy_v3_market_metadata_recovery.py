"""Evidence-only tick recovery: no order, strategy or outcome engine imports."""

from __future__ import annotations

import argparse
import ast
import csv
import gzip
import json
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v3_market_metadata_recovery"
START_HEAD = "50c9fb3010fbf43264f2a6ae18cfd8815a76bad2"
WARMUP, START, END = 1640995200, 1672531200, 1764977400
CONTRACT = "USDT_LINEAR_PERPETUAL"
OLD_DOC_ASSESSMENT = "docs/original_v1_1_metadata_recovery_v2/provenance/OFFICIAL_DOCUMENT_EXAMPLE_ASSESSMENT.json"
DECISION = "V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP"
PARENTS = {
    "docs/machine_strategy_v3_design": "f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0",
    "docs/machine_strategy_v3_implementation_readiness": "d5eb8bd912a0b290679b30969dfa5e8015c4212c07b3263f42c9ca4a34d3a018",
    "docs/machine_strategy_failure_audit_v1": "9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201",
}
CODE = [
    "scripts/build_machine_strategy_v3_market_metadata_recovery.py",
    "scripts/collect_machine_strategy_v3_metadata_evidence.py",
    "tests/test_machine_strategy_v3_market_metadata_recovery.py",
]
OUTPUTS = [
    "EVIDENCE_SEARCH_LOG.json",
    "SOURCE_INVENTORY.json",
    "BTCUSDT_TICK_EPOCHS.json",
    "ETHUSDT_TICK_EPOCHS.json",
    "EPOCH_COVERAGE_MAP.json",
    "PRICE_GRID_COMPATIBILITY.json",
    "PROVENANCE_TIMELINE.json",
    "UNRESOLVED_INTERVALS.json",
    "FROZEN_INPUT_VERIFICATION.json",
    "STATIC_OUTCOME_ISOLATION.json",
    "CROSS_SOURCE_CONTRADICTIONS.json",
]


class PriceRow(TypedDict):
    start: int
    end: int
    open: str
    high: str
    low: str
    close: str


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")


def exact_time(value):
    if type(value) is not int:
        raise ValueError("EXACT_INTEGER_TIMESTAMP_REQUIRED")
    return value


def utc(value):
    return datetime.fromtimestamp(exact_time(value), UTC).isoformat()


def iso_seconds(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("UNPROVEN_TIMEZONE")
    delta = dt.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (
        Decimal(delta.days * 86400 + delta.seconds)
        + Decimal(delta.microseconds) / 1000000
    )


def on_grid(value, tick):
    if type(value) not in (str, Decimal, int) or type(tick) not in (str, Decimal, int):
        raise ValueError("EXACT_DECIMAL_STRING_OR_INTEGER_REQUIRED")
    p, t = Decimal(value), Decimal(tick)
    if not p.is_finite() or not t.is_finite() or p <= 0 or t <= 0:
        raise ValueError("FINITE_POSITIVE_PRICE_AND_TICK_REQUIRED")
    pn, pd = p.as_integer_ratio()
    tn, td = t.as_integer_ratio()
    return (pn * td) % (pd * tn) == 0


def validate_epochs(epochs, symbol, begin=WARMUP, end=END):
    """Validate affirmatively reviewed proof, never derive it from alignment."""
    exact_time(begin)
    exact_time(end)
    if begin >= end:
        raise ValueError("INVALID_COVERAGE_INTERVAL")
    ordered = sorted(epochs, key=lambda e: e["valid_from"])
    previous_end = None
    for epoch in ordered:
        a, b = exact_time(epoch["valid_from"]), exact_time(epoch["valid_to"])
        if not begin <= a < b <= end or previous_end is not None and a < previous_end:
            raise ValueError("OVERLAPPING_OR_INVALID_EPOCH")
        previous_end = b
        if epoch["symbol"] != symbol or epoch["contract_type"] != CONTRACT:
            raise ValueError("WRONG_SYMBOL_OR_CONTRACT")
        if epoch["verification_status"] == "VERIFIED":
            tick = Decimal(epoch["tick_size"])
            if not tick.is_finite() or tick <= 0:
                raise ValueError("INVALID_TICK")
            known = exact_time(epoch["known_at"])
            effective = exact_time(epoch["effective_at"])
            if known > a or effective > a:
                raise ValueError("RETROACTIVE_EPOCH_KNOWLEDGE")
            for field in (
                "source_bytes_verified",
                "effective_application_proven",
                "complete_interval_continuity_proven",
                "independent_provenance_review_pass",
            ):
                if epoch.get(field) is not True:
                    raise ValueError("INSUFFICIENT_AFFIRMATIVE_INTERVAL_PROOF")
            if not epoch.get("evidence_ids"):
                raise ValueError("MISSING_EVIDENCE")
        elif epoch["verification_status"] != "UNVERIFIED":
            raise ValueError("UNKNOWN_VERIFICATION_STATUS")
    return ordered


def coverage(epochs, symbol, begin, end):
    # Clip a validated whole-scope map to warmup/development separately.
    if not WARMUP <= exact_time(begin) < exact_time(end) <= END:
        raise ValueError("INVALID_COVERAGE_INTERVAL")
    ordered = validate_epochs(epochs, symbol)
    cursor, verified, unresolved = begin, 0, []
    for epoch in ordered:
        a, b = max(begin, epoch["valid_from"]), min(end, epoch["valid_to"])
        if a >= b:
            continue
        if cursor < a:
            unresolved.append({"valid_from": cursor, "valid_to": a})
        if epoch["verification_status"] == "VERIFIED":
            verified += b - a
        else:
            unresolved.append({"valid_from": a, "valid_to": b})
        cursor = b
    if cursor < end:
        unresolved.append({"valid_from": cursor, "valid_to": end})
    # Merge adjacent unknowns, yielding minimal exact unresolved intervals.
    merged: list[dict[str, int]] = []
    for gap in unresolved:
        if merged and merged[-1]["valid_to"] == gap["valid_from"]:
            merged[-1]["valid_to"] = gap["valid_to"]
        else:
            merged.append(dict(gap))
    total = end - begin
    return {
        "symbol": symbol,
        "valid_from": begin,
        "valid_to": end,
        "end_exclusive": True,
        "total_seconds": total,
        "verified_seconds": verified,
        "verified_percent": str(
            (Decimal(verified) * 100 / total).quantize(Decimal("0.000001"))
        ),
        "complete_verified": verified == total,
        "unresolved_intervals": merged,
    }


def unknown_epoch(symbol):
    return {
        "symbol": symbol,
        "contract_type": CONTRACT,
        "valid_from": WARMUP,
        "valid_to": END,
        "tick_size": None,
        "effective_at": None,
        "known_at": None,
        "verification_status": "UNVERIFIED",
        "evidence_ids": [],
        "reason": "NO_COMPLETE_CAUSALLY_KNOWN_EXECUTABLE_INTERVAL_PROOF",
    }


def primary(symbol):
    parent = ROOT / "docs/machine_strategy_v3_implementation_readiness"
    expected = next(
        r
        for r in read(parent / "DATA_GRID_AUTHENTICITY.json")["sources"]
        if r["symbol"] == symbol
    )
    path = ROOT / expected["path"]
    if digest(path) != expected["sha256"]:
        raise ValueError("FROZEN_DATA_HASH_CHANGED")
    rows: list[PriceRow] = []
    with gzip.open(path, "rt") as stream:
        for row in csv.DictReader(stream):
            ms = int(row["open_time_ms"])
            if ms % 1000:
                raise ValueError("SUBSECOND_SOURCE_BAR")
            at = ms // 1000
            if not WARMUP <= at < END:
                continue
            if (
                row["symbol"] != symbol
                or row["exchange"] != "BYBIT"
                or row["interval"] != "15"
                or row["is_closed"] != "1"
            ):
                raise ValueError("SOURCE_IDENTITY_MISMATCH")
            if at % 900 or at + 900 > END or rows and at != rows[-1]["start"] + 900:
                raise ValueError("SOURCE_CONTINUITY_MISMATCH")
            prices = {key: row[key] for key in ("open", "high", "low", "close")}
            values = {key: Decimal(value) for key, value in prices.items()}
            if (
                not all(v.is_finite() and v > 0 for v in values.values())
                or not values["low"]
                <= min(values["open"], values["close"])
                <= max(values["open"], values["close"])
                <= values["high"]
            ):
                raise ValueError("INVALID_RAW_OHLC")
            rows.append(
                {
                    "start": at,
                    "end": at + 900,
                    "open": prices["open"],
                    "high": prices["high"],
                    "low": prices["low"],
                    "close": prices["close"],
                }
            )
    if not rows or rows[0]["start"] != WARMUP or rows[-1]["end"] != END:
        raise ValueError("FROZEN_SCOPE_INCOMPLETE")
    return rows, {
        key: expected[key] for key in ("path", "sha256", "symbol", "contract_type")
    }


def grid_check(rows, tick, begin, end):
    checked, violations, cells = 0, [], 0
    for row in rows:
        if not begin <= row["start"] < end:
            continue
        if row["end"] > end:
            raise ValueError("BAR_SPANS_EPOCH_CHANGE_NO_UNIQUE_GRID")
        checked += 1
        bad = [k for k in ("open", "high", "low", "close") if not on_grid(row[k], tick)]
        if bad:
            cells += len(bad)
            violations.append(
                {
                    "bar_start": row["start"],
                    "bar_end": row["end"],
                    "bar_start_UTC": utc(row["start"]),
                    "fields": {k: row[k] for k in bad},
                }
            )
    return {
        "tick_size": tick,
        "valid_from": begin,
        "valid_to": end,
        "bars_checked": checked,
        "off_grid_bars": len(violations),
        "off_grid_cells": cells,
        "violations": violations,
        "arithmetic": "Exact integer ratios of Decimal strings; no context rounding/float tolerance",
        "OHLC_modified": False,
    }


def receipt_inventory():
    receipts = []
    for path in sorted((DEST / "evidence").rglob("*.receipt.json")):
        receipt = read(path)
        headers = receipt.get("headers", receipt.get("response_headers", {}))
        if any(
            k.lower() in {"cookie", "set-cookie", "authorization", "x-api-key"}
            for k in headers
        ):
            raise ValueError("SENSITIVE_RESPONSE_HEADERS_FORBIDDEN")
        body = receipt.get("body_path", receipt.get("body_file"))
        if body is None:
            body = str(
                path.with_name(path.name.replace(".receipt.json", ".body")).relative_to(
                    ROOT
                )
            )
        source = ROOT / body
        if not source.is_file():
            source = path.parent / body
        if not source.resolve().is_relative_to((DEST / "evidence").resolve()):
            raise ValueError("EVIDENCE_PATH_OUTSIDE_METADATA_NAMESPACE")
        expected = receipt.get("body_sha256", receipt.get("sha256"))
        if not source.is_file() or expected is None or digest(source) != expected:
            raise ValueError("EVIDENCE_RECEIPT_HASH_MISMATCH: " + str(path))
        body = str(source.relative_to(ROOT))
        at = receipt.get(
            "retrieved_at",
            receipt.get("retrieved_at_utc", receipt.get("retrieval_time")),
        )
        if at is not None:
            iso_seconds(at)
        receipts.append(
            {
                "receipt_path": str(path.relative_to(ROOT)),
                "receipt_sha256": digest(path),
                "body_path": body,
                "body_sha256": expected,
                "retrieved_at": at,
                "url": receipt.get(
                    "url", receipt.get("request_url", receipt.get("requested_url"))
                ),
                "source_class": receipt.get(
                    "source_class", "RESEARCH_SEARCH_OR_CAPTURE"
                ),
                "http_status": receipt.get("http_status", receipt.get("status")),
                "error_class": receipt.get("error_class", receipt.get("error")),
                "search_result_is_epoch_proof": False,
            }
        )
    return receipts


def sources():
    supplied = DEST / "evidence/tick_research/SOURCE_CANDIDATES.json"
    if not supplied.exists():
        raise ValueError("Lead researcher source inventory required")
    result = read(supplied)
    entries = result["sources"] if isinstance(result, dict) else result
    normalized = []
    for item in entries:
        raw = supplied.parent / item["raw_body_path"]
        if not raw.resolve().is_relative_to((DEST / "evidence").resolve()):
            raise ValueError("SOURCE_PATH_OUTSIDE_METADATA_NAMESPACE")
        if digest(raw) != item["raw_sha256"]:
            raise ValueError("SOURCE_INVENTORY_BYTES_CHANGED")
        normalized.append(
            {
                **item,
                "raw_body_path": str(raw.relative_to(ROOT)),
                "receipt_path": str(
                    (supplied.parent / item["receipt_path"]).relative_to(ROOT)
                ),
                "publication_time": item.get("advertised_publication_at_utc"),
                "publication_time_status": "ISSUER_ASSERTION_OR_FIXTURE_NOT_INDEPENDENT_CAPTURE",
                "effective_at": item.get("advertised_effective_at_utc"),
                "archive_capture_time": item.get("archive_capture_at_utc"),
                "retrieved_at": item["retrieved_at_utc"],
                "exchange_capture_time": item.get("exchange_capture_at_utc"),
                "known_at": item.get("independently_proven_publication_at_utc"),
                "git_author_time": item.get("git_author_at_utc"),
                "git_committer_time": item.get("git_committer_at_utc"),
            }
        )
    for path in sorted((DEST / "evidence/root_search").glob("*.receipt.json")):
        r = read(path)
        label = r["id"]
        if not label.startswith(
            ("official_doc_raw_", "arquivo_production_api_", "arquivo_notice_")
        ):
            continue
        archive = (
            "2024-05-24T02:31:34Z"
            if label == "arquivo_production_api_20240524"
            else "2023-02-05T04:07:38Z"
            if label == "arquivo_notice_20230131"
            else None
        )
        normalized.append(
            {
                "id": label,
                "symbols": [],
                "contract_identity": None,
                "source_class": r["source_class"],
                "original_url": r["url"],
                "raw_body_path": r["body_path"],
                "raw_sha256": r["body_sha256"],
                "receipt_path": str(path.relative_to(ROOT)),
                "publication_time": None,
                "publication_time_status": "NOT_PROVEN",
                "effective_at": None,
                "archive_capture_time": archive,
                "retrieved_at": r["retrieved_at"],
                "exchange_capture_time": None,
                "known_at": None,
                "verification_status": "CONTEXT_ONLY_NOT_EXECUTABLE_EPOCH",
                "proves": "Retained official documentation example or archived HTTP response with explicit provenance",
                "does_not_prove": "No complete instrument epoch; documentation revisions are not production captures; HTTP200 archive API payload has Illegal category/empty list; Jan31 table lacks exact BTCUSDT/ETHUSDT per source-content inspection",
            }
        )
    return normalized


def isolation():
    tree = ast.parse((ROOT / CODE[0]).read_text())
    imports = [
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    ]
    read_keys = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    forbidden = {
        "net_r",
        "gross_r",
        "pnl",
        "win",
        "loss",
        "exit_price",
        "equity",
        "mfe",
        "mae",
    }
    if read_keys & forbidden:
        raise ValueError("OUTCOME_COLUMN_READ")
    if any(
        name
        and any(
            word in name
            for word in (
                "strategy_v3_contracts",
                "historical_adapter",
                "guarded_runner",
                "financial_data",
            )
        )
        for name in imports
    ):
        raise ValueError("OUTCOME_OR_STRATEGY_IMPORT")
    return {
        "status": "PASS",
        "imports": imports,
        "data_read_allowlist": [
            "pinned BTC/ETH raw OHLC CSV",
            "metadata evidence receipts/pages",
            "source inventory",
            "frozen manifests and metadata continuity receipt",
        ],
        "CSV_columns_used": [
            "open_time_ms",
            "symbol",
            "exchange",
            "interval",
            "is_closed",
            "open",
            "high",
            "low",
            "close",
        ],
        "strategy_admission_or_outcome_engine_imported": False,
        "outcome_column_subscript_reads": [],
        "collector_scope": "Separate public-only endpoint/host audit plus receipt URL inventory and private-endpoint negative fixtures; not inferred solely from builder imports",
        "historical_v3_outcomes_read_or_generated": False,
        "builder_sha256": digest(ROOT / CODE[0]),
    }


def frozen_inputs():
    # Hash-only invariant verification never uses protected outcome content in
    # evidence decisions. The namespace verifier also checks exact membership.
    from machine_strategy_research_io import verify_machine

    result = {
        name: verify_machine(ROOT / name, value) for name, value in PARENTS.items()
    }
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", START_HEAD], cwd=ROOT, text=True
    ).splitlines()
    allowed = {*CODE, "agent_control/STATUS.md", "agent_control/CURRENT_STATE.md"}
    prefix = str(DEST.relative_to(ROOT)) + "/"
    if any(name not in allowed and not name.startswith(prefix) for name in changed):
        raise ValueError("FROZEN_OR_UNEXPECTED_FILE_CHANGE")
    return {
        "status": "PASS",
        "start_head": START_HEAD,
        "parents": result,
        "decision_reads_are_metadata_only": True,
    }


def prepare(dest=DEST):
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("Immutable recovery preserved; use --resume-existing")
    dest.mkdir(parents=True, exist_ok=True)
    receipts, inventory = receipt_inventory(), sources()
    maps, grid, epoch_output = {}, {}, {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        epochs = [unknown_epoch(symbol)]
        validate_epochs(epochs, symbol)
        maps[symbol] = {
            name: coverage(epochs, symbol, a, b)
            for name, a, b in (
                ("warmup", WARMUP, START),
                ("development", START, END),
                ("full", WARMUP, END),
            )
        }
        epoch_output[symbol] = {
            "symbol": symbol,
            "contract_type": CONTRACT,
            "epochs": epochs,
            "verified_core_epochs": [],
            "candidate_epoch_promotion": False,
            "source_ids": [
                s.get("id", s.get("source_id"))
                for s in inventory
                if symbol in s.get("symbols", [s.get("symbol")])
            ],
            "shorter_fully_proven_interval": None,
        }
        rows, source = primary(symbol)
        change, before, after = (
            (1676016000, "0.5", "0.1")
            if symbol == "BTCUSDT"
            else (1673942400, "0.05", "0.01")
        )
        checks = [
            grid_check(rows, before, WARMUP, START),
            grid_check(rows, before, START, change),
            grid_check(rows, after, change, END),
        ]
        epoch_output[symbol]["candidate_intervals"] = [
            {
                "valid_from": WARMUP,
                "valid_to": change,
                "tick_size": before,
                "effective_at": None,
                "known_at": None,
                "verification_status": "UNVERIFIED",
                "end_exclusive": True,
                "status_basis": "HYPOTHETICAL_NOTICE_CONSISTENCY_WINDOW; actual start/application/continuity unknown; not counted as coverage",
            },
            {
                "valid_from": change,
                "valid_to": END,
                "tick_size": after,
                "effective_at": change,
                "known_at": None,
                "verification_status": "UNVERIFIED",
                "end_exclusive": True,
                "status_basis": "Advertised boundary only; actual application/causal knowledge/continuity to end unknown; not counted as coverage",
            },
        ]
        grid[symbol] = {
            "source": source,
            "VERIFIED_epochs_checked": 0,
            "VERIFIED_price_grid_status": "STOP_NO_VERIFIED_EPOCHS",
            "non_authoritative_notice_consistency": checks,
            "candidate_status": "UNVERIFIED_NOTICE_CLAIM_HYPOTHETICAL_WINDOW",
            "conditional_contradictions": "Raw OHLC vs assumed old grid until advertised effective time; cannot infer actual boundary or fix prices from these rows",
            "alignment_is_epoch_proof": False,
        }
    timeline = []
    for source in inventory:
        timeline.append(
            {
                key: source.get(key)
                for key in (
                    "id",
                    "source_id",
                    "symbols",
                    "symbol",
                    "source_class",
                    "title_date",
                    "page_date",
                    "publication_time",
                    "publication_time_status",
                    "effective_at",
                    "archive_capture_time",
                    "retrieved_at",
                    "exchange_capture_time",
                    "known_at",
                    "git_author_time",
                    "git_committer_time",
                )
            }
        )
    output = {
        "EVIDENCE_SEARCH_LOG.json": {
            "search_receipts": receipts,
            "requests_retained": len(receipts),
            "bounded_scope": "Official notices/indexes, official Git examples, API/archive indexes and captures, reputable third-party instrument metadata/fixtures; all recorded URLs/statuses/hashes",
            "miss_or_error_proves_absence": False,
            "duplicate_queries_are_independent_evidence": False,
        },
        "SOURCE_INVENTORY.json": {
            "sources": inventory,
            "receipt_hashes_verified": len(receipts),
            "auto_verified_epoch_promotion": False,
        },
        "BTCUSDT_TICK_EPOCHS.json": epoch_output["BTCUSDT"],
        "ETHUSDT_TICK_EPOCHS.json": epoch_output["ETHUSDT"],
        "EPOCH_COVERAGE_MAP.json": {
            "symbols": maps,
            "warmup": [WARMUP, START],
            "development": [START, END],
            "readiness_requires_exact_complete_coverage_both_symbols": True,
            "readiness": False,
        },
        "PRICE_GRID_COMPATIBILITY.json": {
            "symbols": grid,
            "VERIFIED_epoch_conflicts": None,
            "notice_candidate_off_grid_bars_total": sum(
                c["off_grid_bars"]
                for g in grid.values()
                for c in g["non_authoritative_notice_consistency"]
            ),
            "prices_rounded_or_changed": False,
        },
        "PROVENANCE_TIMELINE.json": {
            "sources": timeline,
            "publication_effective_archive_retrieval_separate": True,
            "self_asserted_date_promoted_to_proven_known_at": False,
        },
        "UNRESOLVED_INTERVALS.json": {
            "primary_state": DECISION,
            "symbols": {
                symbol: maps[symbol]["full"]["unresolved_intervals"] for symbol in maps
            },
            "unresolved_UTC": {
                symbol: [
                    {"from": utc(g["valid_from"]), "to_exclusive": utc(g["valid_to"])}
                    for g in maps[symbol]["full"]["unresolved_intervals"]
                ]
                for symbol in maps
            },
            "strongest_gap": "No complete causal production-filter/applicability/continuity chain; candidate boundary conflicts remain",
            "shorter_fully_proven_interval": None,
            "development_truncation_authorized": False,
            "prospective_only_collection": {
                "assessment": "POINT_IN_TIME_CAPTURE_POSSIBLE_IF_PUBLIC_ACCESS_READY; CONTINUOUS_EPOCH_PROOF_NOT_YET_ESTABLISHED",
                "activated": False,
                "procedure": "Separate clean append-only registration; unauthenticated linear instruments-info raw bytes and request/response/server timestamps, symbol/contract/tick and filter fields, independent trusted capture/hash chain plus official change/applicability evidence. Preserve uncertain inter-capture intervals; no sample alignment or no-change assumption. No signals/orders/OOS outcome access.",
                "validation_protocol_changed": False,
            },
            "trade_entry_allowed": False,
        },
        "FROZEN_INPUT_VERIFICATION.json": frozen_inputs(),
        "STATIC_OUTCOME_ISOLATION.json": isolation(),
    }
    examples = read(ROOT / OLD_DOC_ASSESSMENT)
    for example in examples:
        if digest(ROOT / example["file"]) != example["document_sha256"]:
            raise ValueError("FROZEN_DOCUMENT_EXAMPLE_HASH_CHANGED")
    stale = next(e for e in examples if e["version"] == "end_2023")
    output["CROSS_SOURCE_CONTRADICTIONS.json"] = {
        "actual_exchange_epoch_conflict_proven": False,
        "conditional_notice_vs_OHLC": {
            symbol: [
                check
                for check in g["non_authoritative_notice_consistency"]
                if check["off_grid_bars"]
            ]
            for symbol, g in grid.items()
        },
        "documentation_vs_fixture_context_check": {
            "official_document_example": stale,
            "third_party_fixture_sources": [
                s["id"] for s in inventory if s["id"].startswith("ccxt_bybit_")
            ],
            "assessment": "Official end-2023 documentation still contains BTC tick0.50 with early-2023 embedded server-time example, whereas later CCXT fixtures contain0.10. Treating Git revision/fixture date as production filter capture creates a false conflict; both are context-only and may be stale. Neither proves an active interval.",
            "revision_time_equals_exchange_capture": False,
        },
        "old_assessment_path": OLD_DOC_ASSESSMENT,
        "old_assessment_sha256": digest(ROOT / OLD_DOC_ASSESSMENT),
        "source_prices_or_epoch_boundaries_changed": False,
    }
    for name, value in output.items():
        save(dest / name, value)
    return {name: digest(dest / name) for name in OUTPUTS}


def seal():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("Existing recovery freeze preserved")
    frozen_inputs()
    qa = read(DEST / "QA_RECEIPT.json")
    if qa["status"] != "PASS" or qa["tests"] < 1034:
        raise ValueError("FULL_QA_REQUIRED")
    review = (DEST / "reviews/final_independent_reviewer.md").read_text()
    if "FINAL_REVIEW_PASS_FOR_FINANCIAL_STOP" not in review:
        raise ValueError("FINAL_INDEPENDENT_REVIEW_REQUIRED")
    for name, value in {
        **qa["code_sha256"],
        **qa["qa_log_sha256"],
        **qa["replay_sha256"],
    }.items():
        if digest(ROOT / name) != value:
            raise ValueError("POST_QA_BYTES_CHANGED: " + name)
    paths = [p for p in DEST.rglob("*") if p.is_file()]
    if any("__pycache__" in p.parts or p.suffix == ".pyc" for p in paths):
        raise ValueError("BUILD_CACHES_OUTSIDE_IMMUTABLE_NAMESPACE_REQUIRED")
    artifacts = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    artifacts.update({name: digest(ROOT / name) for name in CODE})
    for name, value in PARENTS.items():
        path = ROOT / name / "freeze_manifest.json"
        artifacts[str(path.relative_to(ROOT))] = value
        artifacts.update(read(path)["artifacts"])
    artifacts[OLD_DOC_ASSESSMENT] = digest(ROOT / OLD_DOC_ASSESSMENT)
    for example in read(ROOT / OLD_DOC_ASSESSMENT):
        artifacts[example["file"]] = example["document_sha256"]
    save(
        DEST / "freeze_manifest.json",
        {
            "stage": "MACHINE_STRATEGY_v3_MARKET_METADATA_RECOVERY",
            "version": 1,
            "decision": DECISION,
            "artifacts": dict(sorted(artifacts.items())),
            "QA_tests": qa["tests"],
            "historical_v3_outcomes_generated_or_viewed": False,
            "verified_tick_coverage": {"BTCUSDT": "0%", "ETHUSDT": "0%"},
            "unresolved_interval": [WARMUP, END],
            "financial_authorization_ready": False,
            "trade_entry_allowed": False,
            "LIVE_enabled": False,
            "PAPER_enabled": False,
        },
    )
    return digest(DEST / "freeze_manifest.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--output", type=Path, default=DEST)
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    if args.prepare:
        result = prepare(args.output)
    elif args.freeze:
        result = seal()
    else:
        if not args.expected_manifest_sha256:
            raise ValueError("Externally pinned manifest SHA required")
        from machine_strategy_research_io import verify_machine

        result = verify_machine(DEST, args.expected_manifest_sha256)
    print(
        json.dumps({"status": "PASS_METADATA_ONLY", "receipt": result}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
