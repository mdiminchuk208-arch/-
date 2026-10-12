"""Freeze implementation evidence without running historical v3 outcomes."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from machine_strategy_research_io import original_invariance, verify_machine
from machine_strategy_v3_guarded_runner import (
    COUNTERS,
    HistoricalOutcomeBlocked,
    _closed_record,
    _drive_order,
    authorize_later,
    run_historical,
    run_registered_fixture,
)
from machine_strategy_v3_historical_adapter import (
    FAMILIES,
    HistoricalAdapter,
    derive_market,
    identity,
    load_primary,
)
from original_v1_1_financial_data import END, ROOT, START, WARMUP, Bar, checksum, save

DEST = ROOT / "docs/machine_strategy_v3_implementation_readiness"
START_HEAD = "c6b7340809046df01dab1091e02bc111022c702a"
INTEGRATED_POLICY_HEAD = "ed86bd3b03ffcc1a4f31b3eb82651751e389ff2a"
DESIGN_SHA = "f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0"
AUDIT_SHA = "9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201"
DECISION = "V3_IMPLEMENTATION_FROZEN_FINANCIAL_STOP"
CODE = [
    "scripts/machine_strategy_v3_historical_adapter.py",
    "scripts/machine_strategy_v3_guarded_runner.py",
    "scripts/build_machine_strategy_v3_implementation_readiness.py",
    "tests/test_machine_strategy_v3_readiness_conformance.py",
    "tests/test_machine_strategy_v3_outcome_guard.py",
]
DATA_OUTPUTS = [
    "HISTORICAL_ADAPTER_SPEC.json",
    "HISTORICAL_ADAPTER_COVERAGE.json",
    "TICK_EPOCHS.json",
    "DATA_GRID_AUTHENTICITY.json",
    "DATA_CONTINUITY_REPORT.json",
    "OUTCOME_GUARD_QA.json",
    "OOS_READINESS.json",
    "CAUSALITY_QA.json",
    "FROZEN_INPUT_VERIFICATION.json",
]


def utc(at):
    return datetime.fromtimestamp(at, UTC).isoformat()


def frozen_inputs():
    original_invariance()
    result = {
        "design": verify_machine(ROOT / "docs/machine_strategy_v3_design", DESIGN_SHA),
        "audit": verify_machine(
            ROOT / "docs/machine_strategy_failure_audit_v1", AUDIT_SHA
        ),
    }
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", INTEGRATED_POLICY_HEAD], cwd=ROOT, text=True
    ).splitlines()
    allowed = {"agent_control/STATUS.md", "agent_control/CURRENT_STATE.md", *CODE}
    if any(
        name not in allowed and not name.startswith(str(DEST.relative_to(ROOT)) + "/")
        for name in changed
    ):
        raise ValueError("Unexpected tracked change outside readiness scope")
    return {
        "status": "PASS",
        "start_head": START_HEAD,
        "integrated_policy_head": INTEGRATED_POLICY_HEAD,
        "original_invariance": "PASS",
        **result,
    }


def static_admission_scan():
    forbidden = {
        "gross_r",
        "net_r",
        "fees_r",
        "slippage_r",
        "pnl",
        "win",
        "loss",
        "mfe",
        "mae",
        "equity",
        "drawdown",
        "exit_price",
        "fill_price",
        "exit_reason",
        "outcome",
        "financial_outcome",
        "holding_time_bounds",
    }
    path = ROOT / CODE[0]
    tree = ast.parse(path.read_text())
    keys = {
        node.value.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    imports = [
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    ]
    if keys & forbidden or any(
        "runner" in name or "result" in name for name in imports if name
    ):
        raise ValueError("Outcome dependency in historical admission")
    return {
        "status": "PASS",
        "adapter_sha256": checksum(path),
        "forbidden_columns": sorted(forbidden),
        "forbidden_columns_read": [],
        "runner_imported_by_adapter": False,
        "scope": "Direct adapter AST plus separately pinned/reviewed primitive dependencies",
    }


def check_known_at(value, cutoff):
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                (
                    key.endswith("known_at")
                    or key
                    in {"born_at", "formation_at", "consumed_at", "eq_reacted_at"}
                )
                and item is not None
                and (type(item) is not int or item > cutoff)
            ):
                raise ValueError("Future known-at: " + key)
            check_known_at(item, cutoff)
    elif isinstance(value, (list, tuple)):
        for item in value:
            check_known_at(item, cutoff)


def historical_prefix_qa(symbol, m15):
    # Only raw, causal pre-entry events/states; epochs remain empty and exits are
    # never called. Full future index construction is intentionally challenged.
    cutoff = START + 7 * 86400
    prefix = [b for b in m15 if b.end <= cutoff]
    changed_future = [
        b
        if b.end <= cutoff
        else Bar(
            b.start,
            b.end,
            *(
                getattr(b, k) * Decimal("1.013")
                for k in ("open", "high", "low", "close")
            ),
        )
        for b in m15
    ]
    hashes = []
    decisions = None
    for name, bars in (
        ("prefix", prefix),
        ("full_future", m15),
        ("mutated_future", changed_future),
    ):
        market, _ = derive_market(bars)
        orders, state = HistoricalAdapter(symbol, market, []).run(cutoff)
        check_known_at(orders, cutoff)
        check_known_at(state["frame_snapshot"], cutoff)
        if orders:
            raise ValueError("Unverified ticks admitted a historical order")
        hashes.append(
            {
                "scenario": name,
                "pre_entry_digest": identity("historical_prefix", orders, state),
            }
        )
        decisions = state["known_through"]
    if len({h["pre_entry_digest"] for h in hashes}) != 1:
        raise ValueError("Historical prefix/future-mutation mismatch")
    return {
        "status": "PASS",
        "symbol": symbol,
        "cutoff": cutoff,
        "cutoff_UTC": utc(cutoff),
        "decision_known_through": decisions,
        "scenarios": hashes,
        "historical_position_evaluations": 0,
        "financial_fields_observed": False,
        "verified_tick_epochs_supplied": 0,
        "scope": "Actual complete warmup + first seven development days; full 2022-2025 future index and future-OHLC mutation; all-family positive path tested separately on synthetic fixtures",
    }


def guard_qa():
    blocked = []
    for name, call in (
        ("public_history", lambda: run_historical("BTCUSDT", [])),
        ("direct_kernel", lambda: _drive_order({}, [], [])),
        ("direct_accounting", lambda: _closed_record({})),
        (
            "current_phase_authorization",
            lambda: authorize_later(ROOT / "nonexistent_authorization.json"),
        ),
        ("forged_fixture", lambda: _drive_order({}, [], [], fixture_name="open_stop")),
    ):
        try:
            call()
        except HistoricalOutcomeBlocked as exc:
            blocked.append({"probe": name, "reason": str(exc)})
        else:
            raise ValueError("Historical guard bypass: " + name)
    fixtures = {
        n: run_registered_fixture(n)
        for n in (
            "open_stop",
            "wick_ambiguous",
            "prefill_target_gap",
            "filled_then_stop_gap",
            "filled_eof",
            "unfilled_eof",
            "dual_touch",
            "filled_epoch_change",
            "filled_data_gap",
        )
    }
    if COUNTERS["historical_outcome_evaluations"] != 0:
        raise ValueError("Historical outcome evaluation detected")
    return {
        "status": "PASS",
        "blocked_probes": blocked,
        "synthetic_event_receipts": fixtures,
        "counters": dict(COUNTERS),
        "historical_outcomes_run_or_viewed": False,
        "trade_entry_allowed": False,
        "guard_limits": "Process-local capability checks enforce ordinary entry paths, not hostile Python monkeypatching; NEXT_TASK phase and committed READY/auth/evidence revalidated at every historical kernel/accounting entry.",
    }


def tick_records():
    records = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        records.append(
            {
                "symbol": symbol,
                "contract_type": "USDT_LINEAR_PERPETUAL",
                "valid_from": WARMUP,
                "valid_to": END,
                "interval_end_exclusive": True,
                "tick_size": None,
                "effective_at": None,
                "known_at": None,
                "source_url_or_archive_id": None,
                "source_hash": None,
                "evidence_class": "UNPROVEN_COMPLETE_INTERVAL",
                "verification_status": "UNVERIFIED",
                "notes": "Dated change notices are evidence leads, not proof of all active epochs, pre-effective publication and unchanged continuity; no later setting/decimal backfill.",
            }
        )
    return {
        "status": "STOP_NO_VERIFIED_HISTORICAL_TICK_EPOCHS",
        "intervals": records,
        "verified_core_epochs": [],
        "development_start": START,
        "development_end_exclusive": END,
        "verified_development_coverage_seconds": {"BTCUSDT": 0, "ETHUSDT": 0},
        "notice_claims_not_executable_epochs": [
            {
                "symbol": "ETHUSDT",
                "title_date": "2023-01-06",
                "page_date": "2023-01-06T07:03:06",
                "publication_timezone_verified": False,
                "body_effective_at_UTC": "2023-01-17T08:00:00+00:00",
                "before_tick": "0.05",
                "after_tick": "0.01",
                "archive_capture_at_UTC": "2023-02-05T04:10:38+00:00",
                "retrieval_receipt": "evidence/eth_tick_notice_arquivo_receipt.json",
                "source_hash": checksum(
                    DEST / "evidence/eth_tick_notice_arquivo_20230205.html"
                ),
                "effective_publication_discrepancy": "Archive capture follows stated effective time; pre-effective known_at and applied/unchanged interval not proven.",
            },
            {
                "symbol": "BTCUSDT",
                "title_date": "2023-02-08",
                "page_date": "2023-02-07T11:02:47",
                "publication_timezone_verified": False,
                "body_effective_at_UTC": "2023-02-10T08:00:00+00:00",
                "before_tick": "0.5",
                "after_tick": "0.1",
                "archive_capture_at_UTC": None,
                "retrieval_receipt": "evidence/btc_current_notice.receipt.json",
                "source_hash": checksum(DEST / "evidence/btc_current_notice.body"),
                "effective_publication_discrepancy": "Current notice title and page date differ; no contemporary capture/complete continuity proof.",
            },
        ],
        "trade_entry_allowed": False,
    }


def prepare(dest=DEST):
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("Frozen readiness preserved; use --resume-existing")
    dest.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(
        (
            ROOT / "docs/machine_strategy_v3_design/DATA_EXPOSURE_INVENTORY.json"
        ).read_text()
    )
    data, prefixes = [], []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        bars, source = load_primary(symbol)
        _, aggregation = derive_market(bars)
        if bars[0].start != WARMUP or bars[-1].end != END:
            raise ValueError("Canonical primary interval incomplete")
        data.append(
            {
                **source,
                "UTC_M15_grid": "PASS",
                "missing_bars": 0,
                "duplicate_bars": 0,
                "interpolation": False,
                "development_first_open": START,
                "development_end_exclusive": END,
                "warmup_first_open": WARMUP,
                "development_M15_bars": sum(b.start >= START for b in bars),
                "derivations": aggregation,
                "price_tick_grid_verdict": "UNVERIFIED_NO_HISTORICAL_EPOCHS",
            }
        )
        prefixes.append(historical_prefix_qa(symbol, bars))
    aliases = [
        r
        for r in inventory["series"]
        if r["symbol"] in {"BTCUSDT", "ETHUSDT"} and r["exchange"] == "BYBIT"
    ]
    outputs = {
        "HISTORICAL_ADAPTER_SPEC.json": {
            "strategy_version": "MACHINE_STRATEGY_v3",
            "frozen_design_manifest_sha256": DESIGN_SHA,
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "families": list(FAMILIES),
            "primary": "Pinned native M15 representation only; complete UTC 4/16/96 groups derive H1/H4/D1; no fallback/interpolation",
            "decision_clock": "Completed H1 close; D1,H4,H1,M15 release order",
            "adapter_entry_point": "HistoricalAdapter.run",
            "outcome_entry_point": "run_historical (separate authorized committed READY freeze only)",
            "new_rule_selection": False,
            "trade_entry_allowed": False,
            "operational_clarifications": [
                "Frozen M15 CONF must be later than reaction; linked BOS may equal reaction according to frozen inherited code.",
                "H4 range boundary uses nominated formation_bar; native Range later reaction independently required.",
                "EQ-confirmed range fixed until retirement; old ID never reactivates, new correction may form a new ID.",
                "Canonical END is data availability end 2025-12-05T23:30Z exclusive; old END+1 inclusive label does not add a missing bar.",
                "All profit-side FTA candidates retained before passive entry rounding; nearest selection uses executable E.",
            ],
        },
        "HISTORICAL_ADAPTER_COVERAGE.json": {
            "implementation": "FULL_PRE_ENTRY_ADAPTER_AND_GUARDED_LATER_RUNNER",
            "families": {
                name: {
                    "native_TF": [60, 240],
                    "directions": ["LONG", "SHORT"],
                    "positive_conformance": "SYNTHETIC_MIRRORED",
                    "historical_outcome_execution": False,
                }
                for name in FAMILIES
            },
            "required_surfaces": [
                "causal states",
                "POI/FTA/pools",
                "ATR at formation",
                "native next-open/reaction known_at",
                "first eligible test",
                "physical/POI reservation",
                "tick WAIT",
                "structural entry/stop/target",
                "cost-inclusive modeled feasibility",
                "order lifecycle",
                "gap invalidation",
                "intrabar ambiguity",
                "EOF censor",
                "risk/accounting identity",
            ],
            "historical_positive_executable_coverage": "STOP_UNVERIFIED_TICKS",
            "historical_prefix_checks": prefixes,
            "trade_entry_allowed": False,
        },
        "TICK_EPOCHS.json": tick_records(),
        "DATA_GRID_AUTHENTICITY.json": {
            "timestamp_OHLC_source_hash_verdict": "PASS_PINNED_LOCAL_REPRESENTATIONS",
            "historical_exchange_price_grid_verdict": "UNVERIFIED",
            "independent_exchange_authenticity": "NOT_ESTABLISHED_BEYOND_FROZEN_PUBLIC_SOURCE_PROVENANCE",
            "sources": data,
            "alias_overlap_inventory": [
                {
                    k: r.get(k, False) if k == "raw_source_alias" else r[k]
                    for k in (
                        "path",
                        "stored_sha256",
                        "underlying_series_id",
                        "raw_source_alias",
                        "timeframe_minutes",
                        "exposure",
                    )
                }
                for r in aliases
            ],
            "aliases_as_independent_evidence": False,
            "independently_stored_H1_H4_used": False,
        },
        "DATA_CONTINUITY_REPORT.json": {
            "status": "PASS_LOCAL_DECLARED_CANONICAL_INTERVAL",
            "period_end_policy": "Exclusive availability end, no fabricated final M15/H1/H4/D1 bar",
            "sources": data,
            "warmup": [WARMUP, START],
            "development": [START, END],
            "gap_behavior": "WAIT_DATA_GRID_OR_CONTINUITY; no interpolation or overlap fallback",
            "tick_STOP_map": tick_records()["intervals"],
        },
        "OUTCOME_GUARD_QA.json": guard_qa(),
        "CAUSALITY_QA.json": {
            "status": "PASS",
            "static_admission": static_admission_scan(),
            "historical_prefix_future_mutation": prefixes,
            "known_at_validation": "PASS",
            "historical_outcomes_observed": False,
        },
        "OOS_READINESS.json": oos_readiness(inventory),
        "FROZEN_INPUT_VERIFICATION.json": frozen_inputs(),
    }
    for name, value in outputs.items():
        save(dest / name, value)
    return {name: checksum(dest / name) for name in DATA_OUTPUTS}


def oos_readiness(inventory):
    # Illustrative minimum post-freeze day only, NOT an OOS registration.
    anchor = 1791849600  # 2026-10-13T00:00Z
    begin = anchor - 365 * 86400
    coverage = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        intervals = sorted(
            (
                max(begin, r["first_open_ms"] // 1000),
                min(anchor, r["last_open_ms"] // 1000 + 900),
            )
            for r in inventory["series"]
            if r["exchange"] == "BYBIT"
            and r["symbol"] == symbol
            and r["timeframe_minutes"] == 15
            and not r["raw_source_alias"]
        )
        cursor, gaps = begin, []
        for start, end in intervals:
            if end <= begin or start >= anchor:
                continue
            if start > cursor:
                gaps.append({"from": cursor, "to": start, "end_exclusive": True})
            cursor = max(cursor, end)
        if cursor < anchor:
            gaps.append({"from": cursor, "to": anchor, "end_exclusive": True})
        coverage.append(
            {
                "symbol": symbol,
                "illustrative_warmup": [begin, anchor],
                "missing_local_intervals": gaps,
                "continuous_365_day_warmup_verified": not gaps,
            }
        )
    return {
        "status": "STOP_NO_PRISTINE_OOS",
        "local_exposure": "ALL_92_SERIES_EXPOSED_DEVELOPMENT; old2026TEST not pristine",
        "illustrative_anchor_UTC": utc(anchor),
        "anchor_is_registration": False,
        "warmup": coverage,
        "public_gap_acquisition": "BLOCKED_HTTP_403_BOTH_SYMBOLS; immutable receipts retained",
        "metadata": "STOP_NO_VERIFIED_HISTORICAL_TICK_EPOCHS",
        "acquisition_procedure": "Unauthenticated GET /v5/market/kline category=linear interval=15, paginate exact start/end, hash raw responses, normalize only closed UTC bars, enforce native identity/duplicate/gap/OHLC checks; archive instruments/dated changes independently. Do not use private API or interpolate.",
        "prospective_signals_positions_outcomes_generated": False,
        "can_claim_pristine_OOS": False,
        "separate_append_only_registration": "Required after complete implementation freeze: exact first UTC D1 OPEN strictly later than max(freeze commit time, registration commit time), BTC/ETH, 365-day evaluation + independently verified 365-day pre-start warmup; no early outcome peeking",
        "registration_ready": False,
        "trade_entry_allowed": False,
    }


def freeze():
    path = DEST / "freeze_manifest.json"
    if path.exists():
        raise ValueError("Frozen readiness preserved; use --resume-existing")
    if any("__pycache__" in p.parts or p.suffix == ".pyc" for p in DEST.rglob("*")):
        raise ValueError("Rebuildable bytecode must be outside the immutable namespace")
    frozen_inputs()
    qa = json.loads((DEST / "QA_RECEIPT.json").read_text())
    if (
        qa["status"] != "PASS"
        or qa["tests"] < 1027
        or qa["historical_outcome_evaluations"] != 0
    ):
        raise ValueError("Full gate QA not PASS")
    for name, digest in {**qa["code_sha256"], **qa["qa_log_sha256"]}.items():
        if checksum(ROOT / name) != digest:
            raise ValueError("QA-frozen bytes changed: " + name)
    for role in (
        "strategy_explorer",
        "execution_auditor",
        "strategy_designer",
        "backtest_reviewer",
    ):
        if (
            "IMPLEMENTATION_REVIEW_PASS"
            not in (DEST / "reviews" / (role + ".md")).read_text()
        ):
            raise ValueError("Independent implementation review not PASS: " + role)
    guard = json.loads((DEST / "OUTCOME_GUARD_QA.json").read_text())
    if guard["counters"]["historical_outcome_evaluations"] != 0:
        raise ValueError("Historical outcome violation")
    artifacts = {
        str(p.relative_to(ROOT)): checksum(p) for p in DEST.rglob("*") if p.is_file()
    }
    artifacts.update({name: checksum(ROOT / name) for name in CODE})
    for parent in ("machine_strategy_v3_design", "machine_strategy_failure_audit_v1"):
        manifest = ROOT / "docs" / parent / "freeze_manifest.json"
        artifacts[str(manifest.relative_to(ROOT))] = checksum(manifest)
        artifacts.update(json.loads(manifest.read_text())["artifacts"])
    save(
        path,
        {
            "stage": "MACHINE_STRATEGY_v3_IMPLEMENTATION_READINESS",
            "version": 1,
            "decision": DECISION,
            "status": "IMPLEMENTATION_QA_PASS_FINANCIAL_METADATA_STOP",
            "start_head": START_HEAD,
            "integrated_policy_head": INTEGRATED_POLICY_HEAD,
            "task_at_freeze_sha256": checksum(ROOT / "agent_control/NEXT_TASK.md"),
            "artifacts": dict(sorted(artifacts.items())),
            "QA_tests": qa["tests"],
            "outcomes_computed": False,
            "historical_outcome_evaluations": 0,
            "trade_entry_allowed": False,
            "LIVE_enabled": False,
            "PAPER_enabled": False,
            "OOS_status": "STOP_NO_PRISTINE_OOS",
            "blockers": [
                "NO_VERIFIED_HISTORICAL_TICK_EPOCHS",
                "HISTORICAL_EXCHANGE_PRICE_GRID_UNVERIFIED",
            ],
            "affected_symbols": ["BTCUSDT", "ETHUSDT"],
            "affected_development_interval": [START, END],
            "affected_warmup_interval": [WARMUP, START],
        },
    )
    return verify_machine(DEST)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--output", type=Path, default=DEST)
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    if args.resume_existing:
        if not args.expected_manifest_sha256:
            raise ValueError("Resume requires externally pinned manifest digest")
        result = verify_machine(DEST, args.expected_manifest_sha256)
    elif args.freeze:
        result = freeze()
    else:
        result = prepare(args.output)
    print(
        json.dumps(
            {
                "status": "VERIFIED_RESUME"
                if args.resume_existing
                else "PASS_NONFINANCIAL_INFRASTRUCTURE",
                "receipt": result,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
