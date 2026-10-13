"""Venue architecture evidence synthesis, never strategy/account execution."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from exchange_selection_math import (
    NOTIONALS,
    as_ratio,
    band_score,
    display,
    evidence_points,
    exact,
    fee_scenarios,
    liquidity_summary,
    lot_grid_impact,
    rank,
    shifted_weights,
    weighted_score,
)

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/exchange_selection_audit_v1"
PREREG_SHA = "ab7add22e1ab5efd543499729c431e03fda1fd6f213063c94bbbf6614e9ce699"
PREREG_COMMIT = "055bcc2"
PARENT_SHA = "b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d"
PARENT = ROOT / "docs/machine_strategy_v3_prospective_readiness"
CODE = [
    "scripts/exchange_selection_math.py",
    "scripts/exchange_selection_public_capture.py",
    "scripts/build_exchange_selection_audit_v1.py",
    "tests/test_exchange_selection_audit_v1.py",
    ".github/workflows/exchange-public-venue-probes.yml",
]
OUTPUTS = [
    "CANDIDATE_UNIVERSE.json",
    "OFFICIAL_FEE_EVIDENCE.json",
    "NORMALIZED_FEE_MATRIX.json",
    "FUNDING_CAPABILITY_MATRIX.json",
    "PUBLIC_DATA_CAPABILITY_MATRIX.json",
    "PUBLIC_ENDPOINT_PROBES.json",
    "LIQUIDITY_SPREAD_SLIPPAGE.json",
    "EXECUTION_CAPABILITY_MATRIX.json",
    "METADATA_PROVENANCE_MATRIX.json",
    "RESEARCH_VENUE_SCORES.json",
    "EXECUTION_VENUE_SCORES.json",
    "SENSITIVITY_ANALYSIS.json",
    "REJECTED_VENUES.json",
    "VENUE_ROLE_DECISIONS.json",
    "CI_BOOK_NORMALIZATION.json",
    "SOURCE_HASH_VERIFICATION.json",
    "FROZEN_INPUT_VERIFICATION.json",
    "LOT_GRID_VWAP.json",
]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(), parse_float=Decimal)


def save(path, value):
    Path(path).write_text(
        json.dumps(value, sort_keys=True, indent=2, default=str) + "\n"
    )


def first(item, names):
    return next((item[k] for k in names if k in item), None)


def raw_path(receipt_path, receipt):
    name = first(receipt, ("raw_file", "raw_path", "body_file", "body_path"))
    if type(name) is not str:
        raise ValueError("RAW_BODY_PATH_REQUIRED")
    p = Path(receipt_path)
    candidates = [p.parent / name, ROOT / name, DEST / name]
    # Scoped documented relocation from interrupted worker's temporary directory.
    venue = next(
        (
            s
            for s in p.parts
            if s in read(DEST / "SCORING_PREREGISTRATION.json")["candidate_venues"]
        ),
        None,
    )
    if venue:
        candidates.extend(
            [
                DEST / "evidence" / venue / name,
                DEST / "evidence" / venue / "raw" / Path(name).name,
            ]
        )
    valid = [
        c.resolve()
        for c in candidates
        if c.resolve().is_relative_to(DEST / "evidence") and c.is_file()
    ]
    if not valid:
        raise ValueError("RAW_BODY_OUTSIDE_EVIDENCE_OR_MISSING")
    expected = first(receipt, ("raw_sha256", "body_sha256", "sha256"))
    for c in valid:
        if digest(c) == expected:
            return c
    raise ValueError("RAW_BODY_HASH_MISMATCH")


def source_verification():
    result = []
    prereg_time = int(
        subprocess.check_output(
            ["git", "show", "-s", "--format=%ct", PREREG_COMMIT], cwd=ROOT
        )
    )
    for p in sorted((DEST / "evidence").rglob("*.receipt.json")):
        r = read(p)
        body = raw_path(p, r)
        size = first(
            r, ("raw_bytes", "body_bytes", "bytes", "raw_length", "raw_byte_count")
        )
        if size is not None and body.stat().st_size != size:
            raise ValueError("RAW_BYTE_LENGTH_CHANGED")
        begin = first(
            r,
            (
                "request_started_at",
                "request_started_at_utc",
                "request_utc",
                "request_start_utc",
                "started_utc",
            ),
        )
        end = first(
            r,
            (
                "response_completed_at",
                "retrieval_utc",
                "response_utc",
                "request_end_utc",
                "completed_utc",
                "completion_utc",
            ),
        )
        if begin is None or end is None:
            raise ValueError("EXPLICIT_REQUEST_RETRIEVAL_REQUIRED")
        a, b = datetime.fromisoformat(begin), datetime.fromisoformat(end)
        if (
            a.tzinfo is None
            or b.tzinfo is None
            or b < a
            or a.timestamp() <= prereg_time
        ):
            raise ValueError("PRECOLLECTION_OR_REVERSED_CHRONOLOGY")
        if any(
            k.lower()
            in {"authorization", "proxy-authorization", "cookie", "set-cookie"}
            for k in r.get("headers", {})
        ):
            raise ValueError("SENSITIVE_RECEIPT_HEADER")
        result.append(
            {
                "receipt": str(p.relative_to(ROOT)),
                "body": str(body.relative_to(ROOT)),
                "sha256": digest(body),
                "http_status": first(r, ("http_status", "status")),
                "latency_ms": r.get("latency_ms"),
                "url": r.get("url"),
                "request_time": begin,
                "retrieval_time": end,
                "environment": "GITHUB_HOSTED_CI" if "ci" in p.parts else "CODEX_CLOUD",
            }
        )
    return result


def verify_parent():
    manifest = PARENT / "freeze_manifest.json"
    if digest(manifest) != PARENT_SHA:
        raise ValueError("FROZEN_PARENT_MANIFEST_CHANGED")
    m = read(manifest)
    prefix = str(PARENT.relative_to(ROOT)) + "/"
    names = {
        str(p.relative_to(ROOT))
        for p in PARENT.rglob("*")
        if p.is_file() and p != manifest
    }
    if names != {p for p in m["artifacts"] if p.startswith(prefix)}:
        raise ValueError("FROZEN_PARENT_MEMBERSHIP_CHANGED")
    for name, h in m["artifacts"].items():
        if digest(ROOT / name) != h:
            raise ValueError("FROZEN_PARENT_BYTES_CHANGED: " + name)
    return {
        "parent_manifest_sha256": PARENT_SHA,
        "artifact_hashes_verified": len(m["artifacts"]),
        "financial_content_parsed": False,
    }


def time_from_book(value, fallback, unit):
    if value is None:
        return fallback
    v = exact(str(value))
    divisor = {"seconds": 1, "milliseconds": 1000, "nanoseconds": 1000000000}.get(unit)
    if divisor is None:
        raise ValueError("DOCUMENTED_TIMESTAMP_UNIT_REQUIRED")
    v /= divisor
    whole = v.numerator // v.denominator
    return (
        datetime(1970, 1, 1, tzinfo=UTC)
        + timedelta(seconds=whole, microseconds=int((v - whole) * 1000000))
    ).isoformat()


def ci_books(facts):
    summary = read(DEST / "evidence/ci/PROBE_SUMMARY.json")
    result: dict[str, dict[str, list[dict]]] = {
        v: {"BTC": [], "ETH": []} for v in facts
    }
    rejected = []
    for r in summary["probes"]:
        name = r["source_kind"]
        if not name.startswith("book_") or r["http_status"] != 200 or r["truncated"]:
            continue
        venue = r["venue"]
        symbol = name.split("_")[1]
        path = DEST / "evidence/ci" / venue / r["raw_file"]
        if (
            venue not in facts
            or symbol not in {"BTC", "ETH"}
            or not path.resolve().is_relative_to(DEST / "evidence/ci")
        ):
            raise ValueError("CI_SOURCE_OUTSIDE_PUBLIC_EVIDENCE")
        if digest(path) != r["raw_sha256"]:
            raise ValueError("CI_BODY_CHANGED")
        data = read(path)
        multiplier = Fraction(1)
        stamp = None
        try:
            if venue == "okx":
                if data["code"] != "0":
                    raise ValueError("API_FAILURE")
                d = data["data"][0]
                f = facts[venue]["products"][symbol]
                multiplier = exact(f["ctVal"]) * exact(f["ctMult"])
                bids, asks = d["bids"], d["asks"]
                stamp = d.get("ts")
            elif venue == "hyperliquid":
                if data["coin"] != symbol:
                    raise ValueError("WRONG_BOOK_INSTRUMENT")
                bids = [(x["px"], x["sz"]) for x in data["levels"][0]]
                asks = [(x["px"], x["sz"]) for x in data["levels"][1]]
                stamp = data["time"]
            elif venue == "gate":
                bids = [(x["p"], x["s"]) for x in data["bids"]]
                asks = [(x["p"], x["s"]) for x in data["asks"]]
                multiplier = exact(
                    facts[venue]["products"][symbol]["contract_multiplier"]
                )
                stamp = data.get("current")
            elif venue in {"blofin", "bitget", "kucoin_futures"}:
                valid = {"blofin": "0", "bitget": "00000", "kucoin_futures": "200000"}[
                    venue
                ]
                if str(data["code"]) != valid:
                    raise ValueError("API_FAILURE")
                d = data["data"]
                if isinstance(d, list):
                    d = d[0]
                bids, asks = d["bids"], d["asks"]
                stamp = d.get("ts", d.get("timestamp", d.get("time")))
                if venue in {"blofin", "kucoin_futures"}:
                    multiplier = exact(
                        facts[venue]["products"][symbol]["multiplier_base_per_contract"]
                    )
            elif venue == "mexc":
                if data["success"] is not True:
                    raise ValueError("API_FAILURE")
                d = data["data"]
                bids, asks = d["bids"], d["asks"]
                stamp = d.get("timestamp")
                multiplier = exact(
                    facts[venue]["products"][symbol]["contract_size_base"]
                )
            elif venue == "kraken_futures":
                if data["result"] != "success":
                    raise ValueError("API_FAILURE")
                d = data["orderBook"]
                bids, asks = d["bids"], d["asks"]
            elif venue == "deribit":
                d = data["result"]
                if d["instrument_name"] != facts[venue]["products"][symbol]["symbol"]:
                    raise ValueError("WRONG_BOOK_INSTRUMENT")
                bids, asks = d["bids"], d["asks"]
                stamp = d.get("timestamp")
            else:
                raise ValueError("UNSUPPORTED_CI_BOOK")
            local = facts[venue]["books"][symbol]
            if not local:
                raise ValueError("NO_DOCUMENTED_UNITS")
            normalized = {
                "bids": [[str(x[0]), display(exact(x[1]) * multiplier)] for x in bids],
                "asks": [[str(x[0]), display(exact(x[1]) * multiplier)] for x in asks],
                "source_id": "evidence/ci/"
                + venue
                + "/"
                + Path(r["receipt_file"]).name,
                "time_utc": time_from_book(
                    stamp,
                    r["response_completed_at"],
                    "nanoseconds"
                    if venue == "kucoin_futures"
                    else "seconds"
                    if venue == "gate"
                    else "milliseconds",
                ),
                "units_proof_id": local[0]["units_proof_id"],
                "environment": "GITHUB_HOSTED_CI",
                "unit_confidence_inherited_not_inferred": True,
            }
            result[venue][symbol].append(normalized)
        except (KeyError, IndexError, ValueError) as exc:
            rejected.append(
                {
                    "venue": venue,
                    "symbol": symbol,
                    "source_id": r["receipt_file"],
                    "reason": str(exc),
                }
            )
    return {
        "books": result,
        "rejected": rejected,
        "all_retained_valid_books_used": True,
        "same_unit_proof_limits_as_local": True,
    }


def row_scores(venue, a, fees, liquid, policy):
    research = {k: evidence_points(v) for k, v in a["research"].items()}
    execution = {k: evidence_points(v) for k, v in a["execution"].items()}
    if a["fee_base_confirmed"] is True and (
        fees.get("maker_rate") is None or fees.get("taker_rate") is None
    ):
        raise ValueError("CONFIRMED_FEE_REQUIRES_ACTUAL_RATES")
    avg = as_ratio(liquid["mean_impact_rational"]) if liquid["scoring_usable"] else None
    execution["liquidity"] = band_score(
        avg,
        policy["liquidity_scoring"]["bands_upper_inclusive_bps"],
        policy["liquidity_scoring"]["scores"],
    )
    cost = (
        2 * exact(fees["taker_rate"]) * 10000 + 2 * avg
        if avg is not None and a["fee_base_confirmed"] is True
        else None
    )
    execution["cost"] = band_score(
        cost,
        policy["cost_scoring"]["bands_upper_inclusive_bps"],
        policy["cost_scoring"]["scores"],
    )
    result = []
    for kind, points, gates in (
        ("research", research, a["hard_research"]),
        ("execution", execution, a["hard_execution"]),
    ):
        evidence_points(gates)
        score = weighted_score(points, policy[kind + "_weights"])
        result.append(
            {
                "venue": venue,
                "points": points,
                "score": display(score),
                "score_rational": [str(score.numerator), str(score.denominator)],
                "eligible": all(g["confirmed"] is True for g in gates),
                "hard_gate_failures": [g for g in gates if g["confirmed"] is not True],
                "all_in_cost_bps": display(cost)
                if kind == "execution" and cost is not None
                else None,
            }
        )
    return result


def selection(research, execution):
    r = [x for x in rank(research) if x["eligible"]]
    e = [x for x in rank(execution) if x["eligible"]]
    return {
        "PRIMARY_RESEARCH_VALIDATION_VENUE": r[0]["venue"] if r else None,
        "PRIMARY_EXECUTION_VENUE": e[0]["venue"] if e else None,
        "SECONDARY_EXECUTION_VENUE": e[1]["venue"] if len(e) > 1 else None,
        "REFERENCE_BENCHMARK_VENUE": r[1]["venue"] if len(r) > 1 else None,
        "decision": "EXCHANGE_SELECTION_AUDIT_FROZEN_PASS"
        if r and e
        else "EXCHANGE_SELECTION_AUDIT_FROZEN_STOP",
        "actual_account_eligibility_verified": False,
        "historical_backtest_ready": False,
        "OOS_registered_or_started": False,
        "LIVE_enabled": False,
        "PAPER_enabled": False,
        "trade_entry_allowed": False,
    }


def base_lot(venue, facts, symbol):
    """Use only explicit current source fields; unsupported semantics stay null."""
    meta = facts["metadata"].get("current_filters")
    if not meta or not meta.get(symbol):
        return None
    f = meta[symbol]
    if venue == "okx":
        return exact(f["lotSz"]) * exact(f["ctVal"]) * exact(f["ctMult"])
    if venue in {"blofin", "kucoin_futures"}:
        return exact(f["lot_contracts"]) * exact(f["multiplier_base"])
    if venue == "hyperliquid":
        return Fraction(1, 10 ** f["szDecimals"])
    if venue == "deribit":
        return exact(f["contract_size_base"])
    if venue == "mexc":
        return exact(f["volume_unit_contracts"]) * exact(f["contract_size_base"])
    if venue == "gate" and f.get("enable_decimal") is False:
        return exact(f["quanto_multiplier"])
    return None


def prepare(output=DEST):
    output = Path(output)
    if (output / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_FREEZE_PRESERVED")
    output.mkdir(parents=True, exist_ok=True)
    if digest(DEST / "SCORING_PREREGISTRATION.json") != PREREG_SHA:
        raise ValueError("PREREGISTRATION_CHANGED")
    committed = subprocess.check_output(
        [
            "git",
            "show",
            PREREG_COMMIT
            + ":docs/exchange_selection_audit_v1/SCORING_PREREGISTRATION.json",
        ],
        cwd=ROOT,
    )
    if sha256(committed).hexdigest() != PREREG_SHA:
        raise ValueError("PREREG_COMMIT_CHANGED")
    policy = read(DEST / "SCORING_PREREGISTRATION.json")
    sources = source_verification()
    parents = verify_parent()
    facts = {
        v: read(DEST / "evidence" / v / "FACTS.json")
        for v in policy["candidate_venues"]
    }
    assessments = read(DEST / "reviews/SCORING_ASSESSMENTS.json")["venues"]
    ci = ci_books(facts)
    books = {
        v: {
            s: facts[v].get("books", {}).get(s, []) + ci["books"][v][s]
            for s in ("BTC", "ETH")
        }
        for v in facts
    }
    liquids = {
        v: liquidity_summary(
            books[v], units_confirmed=assessments[v]["book_units_confirmed"]
        )
        for v in facts
    }
    fees = {
        v: fee_scenarios(facts[v]["fees"]["maker_rate"], facts[v]["fees"]["taker_rate"])
        if assessments[v]["fee_base_confirmed"] is True
        else fee_scenarios(None, None)
        for v in facts
    }
    researches, executions = [], []
    for v in facts:
        r, e = row_scores(v, assessments[v], facts[v]["fees"], liquids[v], policy)
        researches.append(r)
        executions.append(e)
    decision = selection(researches, executions)
    sensitivity = {
        "base_roles": decision,
        "cost_weight_shifts": [],
        "remove_snapshot": [],
        "promotions": "Already excluded in all primary/sensitivity fee matrices; no guaranteed discount used",
        "unknown_depth": [],
    }
    for shift in (-5, 5):
        weights = shifted_weights(policy["execution_weights"], shift)
        rows = []
        for e in executions:
            score = weighted_score(e["points"], weights)
            rows.append(
                {
                    **e,
                    "score": display(score),
                    "score_rational": [str(score.numerator), str(score.denominator)],
                }
            )
        sensitivity["cost_weight_shifts"].append(
            {
                "shift": shift,
                "weights": {k: display(v) for k, v in weights.items()},
                "roles": selection(researches, rows),
                "ranking": rank(rows),
            }
        )
    for venue in facts:
        for symbol in books[venue]:
            for b in books[venue][symbol]:
                altered = liquidity_summary(
                    books[venue],
                    units_confirmed=assessments[venue]["book_units_confirmed"],
                    remove_source=b["source_id"],
                )
                _, e = row_scores(
                    venue, assessments[venue], facts[venue]["fees"], altered, policy
                )
                rows = [e if old["venue"] == venue else old for old in executions]
                sensitivity["remove_snapshot"].append(
                    {
                        "venue": venue,
                        "source_removed": b["source_id"],
                        "scoring_usable_after_removal": altered["scoring_usable"],
                        "roles": selection(researches, rows),
                    }
                )
    # Conservative historical-depth scenario: old exact actual sample is unchanged;
    # documentary-only depth receives zero and cannot satisfy the hard gate.
    for r in researches:
        depth_actual = assessments[r["venue"]]["hard_research"][2]["confirmed"] is True
        points = {
            **r["points"],
            "history": r["points"]["history"] if depth_actual else 0,
        }
        score = weighted_score(points, policy["research_weights"])
        sensitivity["unknown_depth"].append(
            {
                **r,
                "points": points,
                "score": display(score),
                "score_rational": [str(score.numerator), str(score.denominator)],
            }
        )
    sensitivity["unknown_depth_roles"] = selection(
        sensitivity["unknown_depth"], executions
    )
    sensitivity["primary_execution_changed_under_snapshot_removal"] = any(
        x["roles"]["PRIMARY_EXECUTION_VENUE"] != decision["PRIMARY_EXECUTION_VENUE"]
        for x in sensitivity["remove_snapshot"]
    )
    lot_checks: dict[str, dict[str, list[dict]]] = {}
    for venue, venue_facts in facts.items():
        lot_checks[venue] = {}
        for symbol in ("BTC", "ETH"):
            lot = (
                base_lot(venue, venue_facts, symbol)
                if assessments[venue]["book_units_confirmed"] is True
                else None
            )
            lot_checks[venue][symbol] = [
                {
                    "source_id": b["source_id"],
                    "checks": {
                        n: {
                            side: lot_grid_impact(b, n, side, lot)
                            for side in ("BUY", "SELL")
                        }
                        for n in NOTIONALS
                    },
                }
                for b in books[venue][symbol]
            ]
    outputs = {
        "CANDIDATE_UNIVERSE.json": {
            "venues": policy["candidate_venues"],
            "products": {v: facts[v]["products"] for v in facts},
            "preregistration_sha256": PREREG_SHA,
        },
        "OFFICIAL_FEE_EVIDENCE.json": {v: facts[v]["fees"] for v in facts},
        "NORMALIZED_FEE_MATRIX.json": {
            "venues": fees,
            "BTC_ETH_same_published_fee_class": True,
            "USD_notional_assumes_quote_unit_at_par": True,
            "funding_spread_slippage_separate": True,
        },
        "FUNDING_CAPABILITY_MATRIX.json": {v: facts[v]["funding"] for v in facts},
        "PUBLIC_DATA_CAPABILITY_MATRIX.json": {
            v: {
                "facts": facts[v]["data"],
                "hard_research": assessments[v]["hard_research"],
                "two_year_sample_is_not_continuity": True,
            }
            for v in facts
        },
        "PUBLIC_ENDPOINT_PROBES.json": {
            "responses": sources,
            "ci_run": read(DEST / "evidence/ci/WORKFLOW_RUN_RECEIPT.json"),
            "no_alternative_geographic_routing": True,
            "cloud_inherited_egress_transport_only": True,
        },
        "LIQUIDITY_SPREAD_SLIPPAGE.json": {
            "venues": liquids,
            "all_five_notionals": NOTIONALS,
            "snapshot_estimates_not_future_execution_guarantees": True,
            "queue_lot_and_future_exit_model_requires_compatibility_gate": True,
        },
        "EXECUTION_CAPABILITY_MATRIX.json": {
            v: {
                "facts": facts[v]["execution"],
                "hard_execution": assessments[v]["hard_execution"],
                "account_jurisdiction_requires_later_user_check": True,
            }
            for v in facts
        },
        "METADATA_PROVENANCE_MATRIX.json": {
            v: {
                "facts": facts[v]["metadata"],
                "historical_epochs_verified": False,
                "prospective_only_no_backdating": True,
            }
            for v in facts
        },
        "RESEARCH_VENUE_SCORES.json": {
            "weights": policy["research_weights"],
            "ranking": rank(researches),
            "score_probability_claimed": False,
        },
        "EXECUTION_VENUE_SCORES.json": {
            "weights": policy["execution_weights"],
            "ranking": rank(executions),
            "future_architecture_only": True,
        },
        "SENSITIVITY_ANALYSIS.json": sensitivity,
        "REJECTED_VENUES.json": {
            v: {
                "research_reasons": next(
                    r["hard_gate_failures"] for r in researches if r["venue"] == v
                ),
                "execution_reasons": next(
                    r["hard_gate_failures"] for r in executions if r["venue"] == v
                ),
                "other_limitations": facts[v].get("limitations", []),
            }
            for v in facts
        },
        "VENUE_ROLE_DECISIONS.json": decision,
        "CI_BOOK_NORMALIZATION.json": ci,
        "SOURCE_HASH_VERIFICATION.json": {
            "raw_receipts_verified": len(sources),
            "status": "PASS",
            "sensitive_headers_retained": False,
            "preregistration_precedes_every_retained_request": True,
        },
        "FROZEN_INPUT_VERIFICATION.json": parents,
        "LOT_GRID_VWAP.json": {
            "venues": lot_checks,
            "preregistered_ranking_replaced": False,
            "scope": "Documented current-lot quantity models only; metadata continuity, exact price-grid rounding, minimum order checks and actual fill tests require compatibility gate",
        },
    }
    for name, value in outputs.items():
        save(output / name, value)
    return {name: digest(output / name) for name in OUTPUTS}


def seal():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("EXISTING_FREEZE_PRESERVED")
    qa = read(DEST / "QA_RECEIPT.json")
    roles = read(DEST / "VENUE_ROLE_DECISIONS.json")
    if qa["status"] != "PASS":
        raise ValueError("NEW_AUDIT_QA_REQUIRED")
    marker = (
        "FINAL_REVIEW_PASS_FOR_EXCHANGE_SELECTION"
        if roles["decision"].endswith("PASS")
        else "FINAL_REVIEW_PASS_FOR_EXCHANGE_STOP"
    )
    if marker not in (DEST / "reviews/final_independent_reviewer.md").read_text():
        raise ValueError("INDEPENDENT_SEAL_REQUIRED")
    for maps in (qa["code_sha256"], qa["log_sha256"], qa["replay_sha256"]):
        for name, h in maps.items():
            if digest(ROOT / name) != h:
                raise ValueError("POST_QA_BYTES_CHANGED")
    verify_parent()
    paths = [p for p in DEST.rglob("*") if p.is_file()]
    if any("__pycache__" in p.parts or p.suffix == ".pyc" for p in paths):
        raise ValueError("NAMESPACE_CACHES_FORBIDDEN")
    artifacts = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    artifacts.update({p: digest(ROOT / p) for p in CODE})
    artifacts[str((PARENT / "freeze_manifest.json").relative_to(ROOT))] = PARENT_SHA
    artifacts.update(read(PARENT / "freeze_manifest.json")["artifacts"])
    save(
        DEST / "freeze_manifest.json",
        {
            "stage": "EXCHANGE_SELECTION_AUDIT_v1",
            "decision": roles["decision"],
            "roles": roles,
            "artifacts": dict(sorted(artifacts.items())),
            "preregistered_scoring_sha256": PREREG_SHA,
            "strategy_rules_changed": False,
            "historical_financial_authorized": False,
            "OOS_clock_started": False,
            "LIVE_enabled": False,
            "PAPER_enabled": False,
            "trade_entry_allowed": False,
        },
    )
    return digest(DEST / "freeze_manifest.json")


def verify_existing(expected):
    if not expected or digest(DEST / "freeze_manifest.json") != expected:
        raise ValueError("PINNED_MANIFEST_REQUIRED")
    m = read(DEST / "freeze_manifest.json")
    prefix = str(DEST.relative_to(ROOT)) + "/"
    names = {
        str(p.relative_to(ROOT))
        for p in DEST.rglob("*")
        if p.is_file() and p.name != "freeze_manifest.json"
    }
    if names != {p for p in m["artifacts"] if p.startswith(prefix)}:
        raise ValueError("NAMESPACE_MEMBERSHIP_CHANGED")
    for name, h in m["artifacts"].items():
        if digest(ROOT / name) != h:
            raise ValueError("FROZEN_ARTIFACT_CHANGED")
    return {"manifest_sha256": expected, "decision": m["decision"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    a = p.add_mutually_exclusive_group(required=True)
    a.add_argument("--prepare", action="store_true")
    a.add_argument("--freeze", action="store_true")
    a.add_argument("--resume-existing", action="store_true")
    p.add_argument("--output", type=Path, default=DEST)
    p.add_argument("--expected-manifest-sha256")
    args = p.parse_args()
    result = (
        prepare(args.output)
        if args.prepare
        else seal()
        if args.freeze
        else verify_existing(args.expected_manifest_sha256)
    )
    print(
        json.dumps({"result": result, "strategy_or_orders_run": False}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
