"""Nonfinancial Stage-A evidence verification and immutable STOP sealing."""

from __future__ import annotations

import argparse
import csv
import io
import json
from decimal import Decimal
from hashlib import sha256
from urllib.parse import urlparse
from zipfile import ZipFile

from okx_qualification_data_v1 import (
    DEST,
    PRODUCTS,
    ROOT,
    compact,
    millis,
    retained_pages,
    save,
    validate_continuity,
)
from okx_v3_input_bridge_v1 import aggregate, load_native

PREREG_SHA = "74d161d04dc5634859b1e6e1b8fa07d60281c86fde7b4a02d0bced15f3c93988"
CODE = [
    "scripts/okx_qualification_data_v1.py",
    "scripts/okx_v3_input_bridge_v1.py",
    "scripts/verify_okx_stage_a_v1.py",
    "tests/test_okx_qualification_data_v1.py",
    "tests/test_okx_v3_input_bridge_v1.py",
    "tests/test_verify_okx_stage_a_v1.py",
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_receipts():
    receipts = list((DEST / "evidence").rglob("*.receipt.json"))
    for file in receipts:
        r = json.loads(file.read_text())
        raw = ROOT / r["raw_path"]
        if not raw.resolve().is_relative_to(DEST / "evidence"):
            raise ValueError("SOURCE_PATH_OUTSIDE_STAGE_A")
        if digest(raw) != r["raw_sha256"] or len(raw.read_bytes()) != r.get(
            "body_bytes", r.get("raw_bytes")
        ):
            raise ValueError("SOURCE_HASH_OR_LENGTH_CHANGED")
        url = urlparse(r.get("url", r.get("requested_url")))
        if url.scheme != "https" or not (
            url.hostname == "okx.com" or (url.hostname or "").endswith(".okx.com")
        ):
            raise ValueError("OFFICIAL_OKX_SOURCE_REQUIRED")
        if r.get("request_auth") or r.get("request_cookies") or r.get("private_API"):
            raise ValueError("NO_PRIVATE_OR_ACCOUNT_SESSION_ALLOWED")
        if (
            r["method"] == "POST"
            and url.path != "/priapi/v5/broker/public/trade-data/download-link"
        ):
            raise ValueError("ONLY_PUBLIC_ARCHIVE_METADATA_POST_ALLOWED")
        if r["method"] not in ("GET", "POST"):
            raise ValueError("UNSUPPORTED_EVIDENCE_METHOD")
    return len(receipts)


def funding(product, start, end):
    folder = DEST / "evidence/cost_funding"
    path = folder / (
        product.replace("-", "_")
        + "_funding_development_prereg_20241013_20261013exclusive.csv"
    )
    rows = list(csv.DictReader(io.StringIO(path.read_text())))
    sources = {}
    times = []
    for row in rows:
        at, rate = int(row["funding_time_utc_ms"]), Decimal(row["funding_rate"])
        if (
            row["instrument_name"] != product
            or not rate.is_finite()
            or not start <= at < end
        ):
            raise ValueError("FUNDING_IDENTITY_RATE_OR_PERIOD")
        source = folder / row["source_body"]
        if not source.resolve().is_relative_to(folder):
            raise ValueError("FUNDING_SOURCE_PATH")
        if source not in sources:
            if source.suffix == ".zip":
                with ZipFile(source) as z:
                    if (
                        len(z.infolist()) != 1
                        or z.infolist()[0].file_size > 2 * 1024 * 1024
                    ):
                        raise ValueError("FUNDING_ARCHIVE_SIZE_OR_MEMBERS")
                    raw_rows = csv.DictReader(
                        io.StringIO(z.read(z.namelist()[0]).decode())
                    )
                    sources[source] = {
                        (r["instrument_name"], int(r["funding_time"])): Decimal(
                            r["funding_rate"]
                        )
                        for r in raw_rows
                    }
            else:
                d = json.loads(source.read_text())
                if d["code"] != "0":
                    raise ValueError("FUNDING_API_CODE")
                sources[source] = {
                    (r["instId"], int(r["fundingTime"])): Decimal(r["realizedRate"])
                    for r in d["data"]
                }
        if sources[source].get((product, at)) != rate:
            raise ValueError("FUNDING_NORMALIZATION_NOT_SOURCE_MATCHED")
        times.append(at)
    # This validates the actual observed archive schedule; never fills missing rates.
    if times != list(range(start, end, 8 * 3600000)):
        raise ValueError("FUNDING_SETTLEMENT_GRID_GAP_OR_DUPLICATE")
    return {
        "rows": len(rows),
        "source_matched": True,
        "gaps": 0,
        "series_sha256": digest(path),
        "historical_observed_interval_hours": 8,
        "future_interval_not_assumed": True,
        "cash_valuation_model_not_implemented": True,
    }


def prepare():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_STAGE_FREEZE_PRESERVED")
    prereg_path = DEST / "STAGE_A_PREREGISTRATION.json"
    if digest(prereg_path) != PREREG_SHA:
        raise ValueError("PREREGISTRATION_CHANGED")
    spec = json.loads(prereg_path.read_text())
    for name, expected in spec["protected_code_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("FROZEN_STRATEGY_CODE_CHANGED")
    receipt_count = source_receipts()
    start, end = millis(spec["warmup_start"]), millis(spec["end_exclusive"])
    data = {}
    for product in PRODUCTS:
        pages, cursor = retained_pages(
            DEST / "evidence/candles" / product, product, end
        )
        rows = validate_continuity(pages, start, end)
        report = json.loads((DEST / f"checkpoints/{product}.json").read_text())
        rebuilt = "".join(compact(row) for row in rows).encode()
        if sha256(rebuilt).hexdigest() != report["content_sha256"] or cursor > start:
            raise ValueError("NATIVE_REPLAY_OR_COVERAGE_CHANGED")
        bars = load_native(product)
        tf = {}
        for seconds in (3600, 14400, 86400):
            derived, omitted = aggregate(bars, seconds)
            if omitted:
                raise ValueError("INCOMPLETE_DERIVED_GROUP")
            tf[str(seconds)] = {
                "bars": len(derived),
                "omitted_groups": 0,
                "content_sha256": sha256(
                    compact([b.observed(seconds // 60) for b in derived]).encode()
                ).hexdigest(),
            }
        data[product] = {
            "native_M15_bars": len(bars),
            "gaps": 0,
            "native_replay_identical": True,
            "derived": tf,
            "funding": funding(product, millis(spec["development_start"]), end),
        }
    result = {
        "decision": "MACHINE_STRATEGY_V3_QUALIFICATION_STOP",
        "stage": "A",
        "source_receipts_verified": receipt_count,
        "data": data,
        "frozen_strategy_code_unchanged": True,
        "qualification_WR_target": "0.70",
        "blockers": [
            "NO_VERIFIED_HISTORICAL_OKX_TICK_LOT_FILTER_EPOCHS",
            "ORDINARY_ACCOUNT_APPLICABLE_OKX_API_SWAP_FEE_UNKNOWN",
            "EXACT_FROZEN_V3_OUTCOME_RUNNER_REMAINS_BYBIT_BOUND_AND_EX_FUNDING",
        ],
        "conservative_epoch_fabrication_forbidden": True,
        "financial_outcome_evaluations": 0,
        "Stage_B_authorized": False,
        "strategy_not_financially_failed_or_qualified": True,
        "historical_actual_API_latency_not_proved": True,
        "PAPER": False,
        "LIVE": False,
        "trade_entry_allowed": False,
    }
    save(DEST / "STAGE_A_READINESS.json", result)
    return result


def freeze_stop():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_STAGE_FREEZE_PRESERVED")
    status = json.loads((DEST / "STAGE_A_READINESS.json").read_text())
    qa = json.loads((DEST / "QA_RECEIPT.json").read_text())
    if (
        status["Stage_B_authorized"]
        or status["decision"] != "MACHINE_STRATEGY_V3_QUALIFICATION_STOP"
        or qa["status"] != "PASS"
    ):
        raise ValueError("ONLY_QA_VERIFIED_NONFINANCIAL_STOP_CAN_BE_SEALED")
    if (
        "FINAL_STAGE_A_STOP_REVIEW_PASS"
        not in (DEST / "INDEPENDENT_REVIEW.md").read_text()
    ):
        raise ValueError("INDEPENDENT_REVIEW_REQUIRED")
    for n, h in qa["pinned_bytes"].items():
        if digest(ROOT / n) != h:
            raise ValueError("POST_QA_CHANGE")
    files = [p for p in DEST.rglob("*") if p.is_file()]
    if any("__pycache__" in p.parts or p.suffix == ".pyc" for p in files):
        raise ValueError("NAMESPACE_CACHE_FORBIDDEN")
    artifacts = {str(p.relative_to(ROOT)): digest(p) for p in files}
    artifacts.update({p: digest(ROOT / p) for p in CODE})
    artifacts.update(
        json.loads((DEST / "STAGE_A_PREREGISTRATION.json").read_text())[
            "protected_code_sha256"
        ]
    )
    parent = ROOT / "docs/exchange_selection_audit_v1/freeze_manifest.json"
    if (
        digest(parent)
        != json.loads((DEST / "STAGE_A_PREREGISTRATION.json").read_text())[
            "parent_exchange_manifest_sha256"
        ]
    ):
        raise ValueError("PARENT_FREEZE_CHANGED")
    artifacts[str(parent.relative_to(ROOT))] = digest(parent)
    artifacts.update(json.loads(parent.read_text())["artifacts"])
    save(
        DEST / "freeze_manifest.json",
        {
            "stage": "OKX_V3_QUALIFICATION_STAGE_A_v1",
            "decision": status["decision"],
            "artifacts": artifacts,
            "preregistration_sha256": PREREG_SHA,
            "financial_authorized": False,
            "PAPER": False,
            "LIVE": False,
            "trade_entry_allowed": False,
        },
    )
    return digest(DEST / "freeze_manifest.json")


def resume(expected):
    path = DEST / "freeze_manifest.json"
    if not expected or digest(path) != expected:
        raise ValueError("EXTERNALLY_PINNED_MANIFEST_REQUIRED")
    m = json.loads(path.read_text())
    names = {
        str(p.relative_to(ROOT)) for p in DEST.rglob("*") if p.is_file() and p != path
    }
    if names != {
        n for n in m["artifacts"] if n.startswith(str(DEST.relative_to(ROOT)) + "/")
    }:
        raise ValueError("FROZEN_NAMESPACE_MEMBERSHIP_CHANGED")
    for n, h in m["artifacts"].items():
        if digest(ROOT / n) != h:
            raise ValueError("FROZEN_BYTES_CHANGED")
    return {"manifest_sha256": expected, "decision": m["decision"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--freeze-stop", action="store_true")
    action.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    value = (
        prepare()
        if args.prepare
        else freeze_stop()
        if args.freeze_stop
        else resume(args.expected_manifest_sha256)
    )
    print(json.dumps(value, sort_keys=True))
