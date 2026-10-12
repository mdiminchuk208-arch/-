"""Freeze v3 design and nonfinancial contracts; never build historical trade outcomes."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from audit_machine_strategy_failure_v1 import verify_inputs
from machine_strategy_research_io import qa_stage, verify_machine
from original_v1_1_financial_data import ROOT, checksum, save

DEST = ROOT / "docs/machine_strategy_v3_design"
AUDIT_SHA = "9dd7cd7a26ac503c350501a8967c7fed450888aed349542f5592162e993d1201"
START_COMMIT = "d7ac9872594bec5775fc75045877a7e54e0d9911"
CODE = [
    "scripts/build_machine_strategy_v3_design.py",
    "scripts/machine_strategy_v3_contracts.py",
    "tests/test_machine_strategy_v3_contracts.py",
]
GENERATED = [
    "MACHINE_STRATEGY_V3_SPEC.md",
    "MACHINE_STRATEGY_V3_SPEC.json",
    "CAUSAL_HYPOTHESES.md",
    "RULE_PROVENANCE.json",
    "DIRECTION_AND_REGIME_SPEC.json",
    "RISK_NORMALIZATION_SPEC.json",
    "ENTRY_TARGET_EXECUTION_SPEC.json",
    "SETUP_FAMILY_SPEC.json",
    "DATA_EXPOSURE_INVENTORY.json",
    "VALIDATION_PROTOCOL.md",
    "VALIDATION_PROTOCOL.json",
    "FROZEN_INPUT_VERIFICATION.json",
]
EVIDENCE = [
    "docs/machine_strategy_v2_design/MACHINE_RULE_REGISTRY.csv",
    "docs/machine_strategy_v2_design/SOURCE_CITATIONS.json",
    "docs/machine_strategy_v2_pre_outcome/DATASET_VERIFICATION.json",
    "docs/original_v1_1_execution_metadata_v3/METADATA_EVIDENCE_REPORT.md",
    "docs/original_v1_1_metadata_recovery_v2/HISTORICAL_METADATA_EVIDENCE_REPORT.md",
    "data/reports/source_validation_qa_2026_10_09/dataset_integrity.json",
    "data/reports/robustness_research/bybit_dataset_manifest.json",
    "data/reports/robustness_research/binance_dataset_manifest.json",
    "data/reports/robustness_research/bybit_temporal_split.json",
    "data/reports/robustness_research/binance_temporal_split.json",
    "data/reports/strategy_v2_2026_10_10/split.json",
    "data/reports/strategy_v2_2026_10_10/strategy_v2_final_leakage_audit.json",
    "data/reports/source_bybit_2026_10_09_final/run_lock.json",
    "data/reports/source_pdf_native_bybit_2026_10_09/run_lock.json",
    "data/reports/source_permitted_physical_bybit_2026_10_10/run_lock.json",
    "data/reports/medium_term_2026_10_10/causal_final/native_bybit_2026/run_lock.json",
]


def read(path):
    return json.loads((ROOT / path).read_text())


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, UTC).isoformat()


def frozen_inputs():
    parent = verify_inputs()
    audit = verify_machine(ROOT / "docs/machine_strategy_failure_audit_v1", AUDIT_SHA)
    changes = subprocess.check_output(
        ["git", "diff", "--name-status", START_COMMIT, "--"], cwd=ROOT, text=True
    )
    for line in changes.splitlines():
        kind, name = line.split("\t", 1)
        if kind != "A" and name not in (
            "agent_control/STATUS.md",
            "agent_control/CURRENT_STATE.md",
        ):
            raise ValueError("Pre-existing file changed: " + name)
    return {
        "status": "PASS",
        "frozen_machine_inputs": parent,
        "failure_audit": audit,
        "source_and_exposure_evidence_sha256": {
            n: checksum(ROOT / n) for n in EVIDENCE
        },
        "financial_run": False,
        "trade_entry_allowed": False,
    }


def exposure_inventory():
    """Read only dataset timestamps/counts/hashes, not strategy outcomes or price features."""
    integrity = read(EVIDENCE[5])
    expected = {
        r["path"]: r.get("stored_sha256", r.get("sha256"))
        for r in integrity["public_series"] + integrity["native_bybit_series"]
    }
    public = {}
    for name in EVIDENCE[6:8]:
        public.update({r["path"]: r for r in read(name)["series"]})
    records = []
    paths = sorted(
        p
        for p in (ROOT / "data/history").rglob("*")
        if p.is_file() and (p.name.endswith(".csv") or p.name.endswith(".gz"))
    )
    for p in paths:
        rel = str(p.relative_to(ROOT))
        opener = gzip.open if p.suffix == ".gz" else open
        digest = sha256()
        n, first, last = 0, None, None
        with opener(p, "rb") as stream:
            header = stream.readline()
            digest.update(header)
            columns = header.decode().strip().split(",")
            index = (
                columns.index("open_time_ms")
                if "open_time_ms" in columns
                else columns.index("timestamp")
            )
            for line in stream:
                digest.update(line)
                if not line.strip():
                    continue
                stamp = int(line.split(b",", index + 1)[index])
                first = stamp if first is None else min(first, stamp)
                last = stamp if last is None else max(last, stamp)
                n += 1
        stored = checksum(p)
        if rel in expected and stored != expected[rel]:
            raise ValueError("Pinned history changed: " + rel)
        raw = "source_raw" in p.parts
        native = "public_research" not in p.parts
        if raw:
            symbol = "BTCUSDT" if "btc" in p.name.lower() else "ETHUSDT"
            tf = int(p.name.split("_")[1].split(".")[0]) if ".csv" in p.name else 15
        else:
            symbol, tf = p.parent.name, int(p.name.split(".")[0])
        exchange = "BINANCE" if "binance_mirror" in p.parts else "BYBIT"
        underlying = (
            f"{exchange}:{'NATIVE_2026' if native else 'PUBLIC_MIRROR'}:{symbol}:{tf}"
        )
        row = {
            "path": rel,
            "stored_sha256": stored,
            "csv_content_sha256": digest.hexdigest(),
            "underlying_series_id": underlying,
            "raw_source_alias": raw,
            "exchange": exchange,
            "symbol": symbol,
            "timeframe_minutes": tf,
            "candles": n,
            "first_open_ms": first,
            "last_open_ms": last,
            "start": iso(first),
            "end_exclusive": iso(last + tf * 60000),
            "exposure": "EXPOSED_DEVELOPMENT",
            "pristine_OOS": False,
            "prior_uses": [
                "source_research",
                "medium_term",
                "old_2026_fitted_development",
            ]
            if native
            else ["old_robustness"],
            "prior_use_evidence": (
                [EVIDENCE[5], EVIDENCE[10], EVIDENCE[11], *EVIDENCE[12:16]]
                if native
                else [EVIDENCE[5], EVIDENCE[7], EVIDENCE[9]]
                if exchange == "BINANCE"
                else [EVIDENCE[5], EVIDENCE[6], EVIDENCE[8], EVIDENCE[2]]
            ),
            "representation_policy": "Overlapping raw/normalized source representations have distinct hashes and can differ in OHLCV or initial partial rows; shared underlying periods remain exposed."
            if raw
            else "Canonical normalized series",
        }
        if exchange == "BYBIT" and not native:
            row["prior_uses"] += ["Original", "v2_v2.1_v2.2", "failure_audit"]
        if rel in public:
            row["original_provenance"] = public[rel]["provenance"]
            if digest.hexdigest() != public[rel]["csv_sha256"]:
                raise ValueError("CSV content hash mismatch: " + rel)
        records.append(row)
    for p in sorted((ROOT / "data/reports").rglob("derived_D1.jsonl.gz")):
        with gzip.open(p, "rt") as stream:
            times = [
                (json.loads(line)["open_time"], json.loads(line)["close_time"])
                for line in stream
            ]
        native = "native_bybit_2026" in p.parts
        records.append(
            {
                "path": str(p.relative_to(ROOT)),
                "stored_sha256": checksum(p),
                "underlying_series_id": f"BYBIT:{'NATIVE_2026' if native else 'PUBLIC_MIRROR'}:{p.parent.name}:1440",
                "exchange": "BYBIT",
                "symbol": p.parent.name,
                "timeframe_minutes": 1440,
                "candles": len(times),
                "start": min(x[0] for x in times),
                "end_exclusive": max(x[1] for x in times),
                "derived_from_tf": 15,
                "exposure": "EXPOSED_DEVELOPMENT",
                "pristine_OOS": False,
                "prior_uses": ["medium_term", "source_research"]
                + ([] if native else ["Original", "v2_v2.1_v2.2", "failure_audit"]),
                "prior_use_evidence": [EVIDENCE[2], EVIDENCE[15]],
            }
        )
    canonical = [
        r
        for r in records
        if not r.get("raw_source_alias") and r["timeframe_minutes"] != 1440
    ]
    if (
        len(canonical) != 74
        or sum(
            r["candles"]
            for r in canonical
            if "NATIVE_2026" in r["underlying_series_id"]
        )
        != 993575
    ):
        raise ValueError("Exposure inventory coverage mismatch")
    return {
        "classification_policy": "Conservative whole-file exposure; overlapping raw/normalized representations and aggregates are not new OOS, even when OHLCV/content hashes differ. Unknown external availability is not pristine proof.",
        "series": records,
        "physical_series_and_aliases": len(records),
        "canonical_native_public_series": 74,
        "development_machine_interval": read(EVIDENCE[2]),
        "old_2026_split_evidence": {
            "path": EVIDENCE[10],
            "sha256": checksum(ROOT / EVIDENCE[10]),
            "provenance": read(EVIDENCE[10])["provenance"],
            "recorded_split": read(EVIDENCE[10]),
        },
        "available_pristine_OOS": [],
        "OOS_verdict": "STOP_NO_PRISTINE_OOS",
        "upstream_advertised_dates_are_not_local_or_pristine_proof": True,
        "price_features_computed": False,
        "v3_cases_built": False,
        "v3_outcomes_read": False,
        "trade_entry_allowed": False,
    }


def architecture():
    direction = {
        "rule_id": "M3_STATE",
        "clock": "Completed H1 CLOSE; advance D1,H4,H1,M15 at equal cutoff in that order; no incomplete bars.",
        "per_TF_priority": ["UNCERTAIN", "RANGE", "TREND", "TRANSITION"],
        "uncertain": "Missing/invalid active CONF leg, dual opposing CONF at same known_at, or incomplete/gapped required prefix => UNCERTAIN.",
        "range": "Active correction-to-impulse-end fixed range, completed EQ contact and inside CLOSE, latest CLOSE strictly inside boundaries, no later CONF superseding range. CLOSE at or outside either boundary retires range permanently; wick alone does not. Re-entry inside cannot reactivate a retired range.",
        "trend": "Current and immediately previous confirmed legs same sign, both protected origin and endpoint strictly advance in that sign. Completed CLOSE strictly beyond protected origin invalidates (LONG below/SHORT above); equality or wick alone does not. Two legs is a machine structure convention, not a fitted lookback.",
        "transition": "Valid active last CONF exists; neither RANGE nor strict two-leg TREND holds. Label its last direction; no predictive future label.",
        "context_priority": [
            "ANY_HTF_UNCERTAIN_WAIT",
            "H4_RANGE",
            "H4_D1_ALIGNED_TREND",
            "TRANSITION_ORIGIN_POI",
        ],
        "context_names": {
            "range": "RANGE_CONTEXT",
            "aligned_trend": "TREND_CONTEXT",
            "mixed_or_transition": "MIXED_OR_TRANSITION_CONTEXT",
        },
        "H4_range": "H1 current leg and M15 confirmation match proposed direction; formation/retest intersects correct fixed H4 boundary. H4 RANGE takes priority over D1 trend, which is still recorded and must be valid.",
        "trend_admission": "If H4 and D1 are the same TREND_UP or TREND_DOWN, only that direction may enter with H1/M15 matching. Opposite candidate WAIT_H4_D1_TREND_DIRECTION; cannot fall through to transition via a POI. No directional exemption.",
        "transition_admission": "Only non-RANGE, non-aligned-trend combinations (opposite H4/D1 trends, trend+transition, or two transitions) use transition-origin POI gate: H1 leg/M15 match candidate; same-direction unconsumed confirmed H4/D1 POI intersects formation, known by formation OPEN. Candidate may oppose one HTF direction under this explicit machine convention. Otherwise WAIT.",
        "all_states_machine_not_source_equivalence": True,
        "LONG_SHORT_mirrored": True,
    }
    risk = {
        "rule_id": "M3_RISK",
        "prices": "Decimal positive quote/base; zero-origin verified tick lattice; reject NaN/Infinity.",
        "structural_boundary": "Immutable branch extreme; SFP adds outward SMA14 true range including completed pattern bar and preceding CLOSE. 14 is inherited machine normalization, not source-mandated or re-tuned.",
        "ATR": "TR=max(H-L,abs(H-prev_close),abs(L-prev_close)); arithmetic mean exactly14 contiguous native-TF TRs ending exactly at pattern_end<=decision. Store immutable ATR at formation; later completed bars cannot drift it. Missing pattern bar/previous close/history => WAIT; no additional ATR risk floor.",
        "rounding": "LONG entry=floor(raw/t)*t, SHORT entry=ceil(raw/t)*t, still inside POI. Stop first grid price strictly outside immutable boundary, once only; no epsilon. Target first grid price strictly inside nearest FTA, never farther.",
        "tick_requirement": "symbol + USDT_LINEAR_PERPETUAL contract + literal verified=true + source/effective proof publication known_at <= decision + effective_from <= decision < effective_until; no overlaps; unknown/changed epoch WAIT. Future adapter must independently hash archived source bytes against source_sha256 and prove interval coverage/publication provenance; the pure core only validates schema/digest syntax, not evidence authenticity.",
        "cost_model": {
            "entry_fee": "0.0006",
            "exit_fee": "0.0006",
            "entry_slippage": "0.0002",
            "exit_slippage": "0.0002",
            "status": "PREREGISTERED_MODEL_NOT_HISTORICAL_ACTUAL",
        },
        "sign": "d=+1 LONG/-1 SHORT",
        "cost": "C(F,P)=(f_e+s_e)*F+(f_x+s_x)*P",
        "cash_stop_unit": "K=d*(F-S)+C(F,S), recomputed at modeled actual fill; strictly positive",
        "gross": "d*(P-F)/K",
        "fees": "(f_e*F+f_x*P)/K",
        "slippage": "(s_e*F+s_x*P)/K",
        "net": "gross-fees-slippage; MODELED_CASH_STOP_R_EX_FUNDING",
        "funding": None,
        "non_gap_stop_identity": "Net_cash_R(S)=-1 exactly; stop gaps can exceed -1",
        "mandatory_raw_diagnostics": [
            "raw_price_risk_D",
            "raw_price_risk_bps",
            "raw_price_risk_ticks",
            "cash_stop_unit",
            "modeled_stop_cost_cash",
            "stop_cost_share_of_unit",
            "entry_notional_per_cash_stop_unit",
            "target_move_D",
            "target_cost_cash",
            "target_move_to_cost_ratio",
        ],
        "price_risk_R_comparable_to_v2": False,
        "portfolio_leverage_safety_claim": False,
        "minimum_risk": "Verified positive tick separation and positive cost-inclusive K; no fitted min ATR/R/percentage hurdle. This normalizes arithmetic, not execution realism or positive expectancy.",
    }
    execution = {
        "rule_id": "M3_EXEC",
        "entry_order": "RESTING_LIMIT_ONLY",
        "expiry_seconds": 3600,
        "pending_expiry_seconds": 57600,
        "expiry_provenance": "Inherited16H1pending/1H1order machine convention; no outcome tuning",
        "fill_price_policy": "CONSERVATIVE_LIMIT_PRICE_NO_OPEN_IMPROVEMENT: F=rounded E for any modeled limit touch. Retain actual modeled fill field; economics recheck uses F.",
        "before_fill": "Activate only bar OPEN>=decision; expire before OPEN>=expires. OPEN at/beyond stop/target invalidates before testing entry.",
        "target_inventory": "All completed contextual unconsumed opposing OB/STB/FVG on H1/H4/D1, unswept profit-side strict-swing pools, plus range far-boundary cap. Entry inside opposite POI rejects. Do not use a success score.",
        "target_priority": "Nearest signed forward raw distance, then canonical ID; retain coincident IDs. Round inward only after selecting nearest; collapsed/unprofitable target rejects without trying farther objects.",
        "economics": "M=d*(T-E)>C(E,T) strict; edge_cost_ratio=M/C(E,T)>1 is algebraic model-feasibility, not signal edge or calibrated margin.",
        "adverse_liquidity": "Inherited contextual internal adverse pool lying beyond structural stop rejects; mirrored completion is MACHINE_RULE_PRE_OUTCOME, not source-proven SHORT algorithm.",
        "entry_bar_ambiguity": "Any wick-only fill plus stop OR target touch => WAIT_INTRABAR_ORDER. OPEN fill: dual touch WAIT; single stop/target touch has interval bounds. No within-bar continuity assumption.",
        "postfill": "OPEN stop/target gaps execute before wick tests; dual wick touch WAIT; otherwise single touch interval. SFP body invalidation only native completed close, after wick processing.",
        "metadata_change": "Missing/changed active epoch before an order event => WAIT_HISTORICAL_TICK_METADATA, no new fill or inferred amendment; existing exposure flagged censored/unknown, never invented flat exit.",
        "time_evidence": "OPEN occurrences [start,start]; wick occurrences [start,end]; observations at completed end. Exit bounds independent of fill observation. Holding duration interval [max(0,exit_low-fill_high),exit_high-fill_low], never realized zero from observation equality.",
        "unresolved": "Keep entry information but exit/PnL/WIN/LOSS unknown; no imputed zeros. EOF order/open censoring distinct.",
        "identity": "physical is intentionally the directional bucket (symbol,formation_at,direction): same-time same-direction native formations share a bucket with fixed sibling/TF/ID priority; opposite directions have separate buckets. POI separately reserved at order emission. First eligible OHLC contact consumes at bar.end, occurrence bounds [start,end] or [start,start] if OPEN inside zone; never timestamp wick contact at OPEN. No old bucket/POI retry after loss/expiry/gap; later independent formation/CONF required.",
        "bar_coverage": "Adapter must advance every contiguous aligned900second bar from decision through active lifetime; last_observed_end is explicit. Missing interior bar=>WAIT_DATA_GAP; EOF/expiry never imply unfilled when coverage is incomplete.",
        "fill_assumptions": "TOUCH_IMPLIES_FULL_LIMIT_FILL_AT_E and target touch full modeled exit; wick stop MODELED_STOP_TRIGGER_PLUS_SLIPPAGE, not observed exact fill. Grid proof alone does not prove queue, spread, latency, tick order, partial fill, or within-bar gap behavior. No within-bar continuity assumption establishes ordering; modeled trigger prices still need declared execution assumptions.",
        "adapter_input_contract": {
            "formation": "symbol/branch/direction/nativeTF60or240/formation_at/native bar OHLC+open/end/geometry IDs; raw geometry and reaction/refinement known_at<=decision; M15 alone cannot originate idea. SFP original_pattern_extreme maps to order.stop_anchor for body invalidation; distinct raw_stop_boundary=original_pattern_extreme plus/minus immutable pattern-end ATR then one outward tick for protective stop. Never pass the buffered boundary as body stop_anchor",
            "state": "Every active leg current/previous ids, protected origin, endpoint, direction, known_at/end_swing_at; retired/body-broken leg flags; range fixed boundaries, context_id, EQ reaction and invalidation timestamps. Completed simultaneous TF changes visible at same H1 cutoff",
            "POI": "id,tf,kind,direction,low/high,born_at,origin_bos_id,origin_CONF_known_at,contextual_at_birth,consumed_at/first_touch_bounds. Eligibility starts at first bar OPEN after origin CONF and matching active native context. Native first touch consumes even absent order",
            "FTA_eligibility": "Decision-time complete H1/H4/D1 inventory: unswept HIGH pools forward LONG/LOW forward SHORT plus confirmed-contextual unconsumed opposite OB/STB/FVG proximal edges. Zone enclosing entry rejects; known_at<=decision. Range far boundary additional cap. Adapter must attach id/kind/tf/known_at/price, optional zone_low/high; preserve all nearest-price IDs and auditable inventory digest",
            "adverse_pool": "From same complete inventory: internal to active H1 impulse, wrong-side liquidity beyond structural stop (LOW below stop for LONG, HIGH above stop for SHORT) => inherited mirrored adverse rejection; no source-proven SHORT claim",
            "adapter_status": "Required full historical raw-event/state/inventory adapter is absent in this gate; pure core only checks supplied causal contract fields, not completeness of historical discovery. Missing mandatory geometry/eligibility evidence WAIT, never assume source-valid",
        },
        "sibling_priority": ["BREAKER", "STB", "SFP", "OB", "RANGE"],
        "TF_priority": [240, 60],
        "PAPER_enabled": False,
        "LIVE_enabled": False,
        "trade_entry_allowed": False,
    }
    families = {
        "SFP": "Completed H1/H4 strict-swing raid/reclaim; next native OPEN reclaimed, usable only at its CLOSE; later M15 BOS/CONF; new origin-bound OB/FVG wholly inside pattern; proximal edge; pattern extreme±causal ATR14; native body invalidation exit.",
        "OB": "Raw raid/opposing candle/full engulf; later reaction; M15 BOS/CONF; new origin-bound OB/FVG inside raw OB; proximal edge; raw full extreme boundary.",
        "BREAKER": "Contextual-at-birth OB; later opposite body break beyond full extreme; M15 opposite BOS/CONF with no intervening reverse BOS; body-zone retest; parent-birth-through-break extreme boundary.",
        "STB": "Raw manipulation raid/engulf; later matching M15 BOS/CONF; manipulation body midpoint; full manipulation extreme boundary.",
        "RANGE": "Confirmed impulse plus interior correction; EQ contact/inside CLOSE; first deviation/reclaim then later boundary contact/inside CLOSE; M15 BOS/CONF; boundary entry; deviation extreme; far-boundary FTA cap.",
    }
    family = {
        "rule_id": "M3_FAMILIES",
        "all_families_retained": list(families),
        "contracts": families,
        "formation_timeframes": [60, 240],
        "decision_tf": 60,
        "refinement_tf": 15,
        "formation_refinement_inheritance": "Frozen M2 raw geometry/BOS/CONF/first-test selectors except explicit M3 overrides; no source-valid equivalence",
        "shared_smoothness": "No opposite M15 BOS between reaction and selected CONF; qualitative smoothness is a machine convention.",
        "refinement_priority": "OB before FVG; latest causal birth then canonical ID; formation/zone IDs and rejected siblings retained",
        "range_parent_mapping": "Use range on native setup TF. If global H4 RANGE governs admission, local formation must intersect its corresponding boundary; do not silently replace native source range geometry.",
        "exits": "Full nearest rounded FTA, all families; Range optional20% breakout is unresolved source choice, represented by full same-zone machine exit. No partial ladder or BE, no fixed percentages; Original canonical exits untouched.",
        "source_validated": False,
        "decision_branch_selection_based_on_PnL": False,
    }
    return direction, risk, execution, family


def validation_protocol():
    return {
        "rule_id": "M3_VALIDATION",
        "development": {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "exchange": "BYBIT",
            "warmup_start": "2022-01-01T00:00:00+00:00",
            "interval": ["2023-01-01T00:00:00+00:00", "2025-12-05T23:30:00+00:00"],
            "status": "EXPOSED_NOT_OOS",
        },
        "robustness": {
            "calendar_partitions": [2023, 2024, 2025],
            "cross_classifications": [
                "symbol",
                "direction",
                "family",
                "setup_tf",
                "causal_market_state",
            ],
            "cost_multipliers": ["0.5", "1", "2"],
            "independence_claim": False,
            "threshold_selection": False,
            "partition_boundary": "Exclude decisions or observation intervals crossing partition boundaries; censored/unresolved shown separately, not assigned zero",
        },
        "available_untouched_OOS": None,
        "current_OOS_gate": "STOP_NO_PRISTINE_OOS",
        "prospective_OOS": {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "exchange": "BYBIT",
            "contract": "USDT_LINEAR_PERPETUAL",
            "TFs": [15, 60, 240, 1440],
            "start_rule": "Provisional plan only: first UTC D1 OPEN strictly after MAX(complete implementation pre-outcome freeze commit committer timestamp, append-only OOS registration commit committer timestamp). This contract-core design freeze alone cannot start the OOS clock. Register complete code/spec/data/protocol hashes and resolved start/end before first observation; missed preregistration/embargo => STOP, no post-outcome window shift",
            "end_rule": "start plus365 UTC days, exclusive",
            "window_reason": "Fixed four-season calendar evaluation commitment before outcomes, not an entry parameter",
            "acquisition": "Public completed M15 bars; derive contiguous UTC H1/H4/D1; no privateAPI/orders; metadata epoch announcements archived with publication known_at",
            "embargo": "Before locked end, no candidate signals, positions, trade labels or equity read, including inference from raw prices. Raw access only logged integrity-only script/role with no strategy-state access: hash/continuity/metadata checks. No interim optimization, early stopping, extension or relabeling after outcome",
            "warmup": "Exactly365 days pre-start completed bars for state warmup; no pre-start orders/outcomes. Prefix-only state reset/reservation ledger at OOS start",
            "warmup_current_state": "UNAVAILABLE_CONTIGUOUS: local Bybit public ends2025-12-05, native starts2026-01-25 and ends2026-09-22. Public gap filling needs independent evidence before registration; no interpolation/pretended ready prefix",
            "training_leakage": "No overlapping underlying OOS candles in development; hashes/copies/content periods checked; no carried development order or position",
            "readiness": "UNESTABLISHED_FUTURE_PLAN_NOT_EXISTING_PRISTINE_DATA",
            "missing_data": "No interpolation; gaps/instrument/metadata ambiguity => WAIT and unqualified-OOS report; do not shift window post hoc",
        },
        "qualification": "After separate authorization: fixed-spec development financial run, robustness, then locked untouched OOS; positive net ex-funding/PF>1 across declared model and stress reported, dependence-aware uncertainty and concentration disclosed. No production on reused TEST or subgroup alone; funding/actual execution evidence required for exchange-realism claim.",
        "implementation_scope": "NONFINANCIAL_CONTRACT_CORE; historical family-event adapter/full case runner not implemented in this gate",
        "first_v3_financial_backtest_ready": False,
        "first_financial_STOP_reasons": [
            "HISTORICAL_EVENT_ADAPTER_NOT_IMPLEMENTED",
            "NO_VERIFIED_HISTORICAL_TICK_EPOCHS",
        ],
        "production_candidate": None,
        "PAPER_enabled": False,
        "LIVE_enabled": False,
        "trade_entry_allowed": False,
    }


def build(output):
    output = Path(output).resolve()
    if (
        any((output / n).exists() for n in GENERATED)
        or (output / "freeze_manifest.json").exists()
    ):
        raise ValueError(
            "Existing design preserved; fresh output or --resume-existing required"
        )
    inputs = frozen_inputs()
    inventory = exposure_inventory()
    direction, risk, execution, family = architecture()
    validation = validation_protocol()
    components = {
        "DIRECTION_AND_REGIME_SPEC.json": direction,
        "RISK_NORMALIZATION_SPEC.json": risk,
        "ENTRY_TARGET_EXECUTION_SPEC.json": execution,
        "SETUP_FAMILY_SPEC.json": family,
    }
    overrides = {
        "M2_TF",
        "M2_CONTEXT",
        "M2_HTF",
        "M2_ENTRY",
        "M2_STOP",
        "M2_FTA",
        "M2_RANGE_EXIT",
        "M2_IDENTITIES",
        "M2_INTRABAR",
        "M2_FIRST_TEST",
    }
    with (ROOT / EVIDENCE[0]).open() as stream:
        inherited = [
            dict(
                r,
                classification="MACHINE_RULE_PRE_OUTCOME",
                original_classification=r["classification"],
                inherited_from=EVIDENCE[0],
                overridden=r["rule_id"] in overrides,
            )
            for r in csv.DictReader(stream)
        ]
    sources = read(EVIDENCE[1])
    source_refs = {
        "M3_STATE": ["S_STRUCTURE", "S_CONF", "S_RANGE_FORMATION", "S_FLOW"],
        "M3_RISK": ["S_SFP_STOP", "S_STOP_FIXED", "S_SL_OFF_POOL"],
        "M3_EXEC": ["S_FTA", "S_OB_FIRST_TEST", "S_PLAN"],
        "M3_FAMILIES": [
            "S_SFP_FORMATION",
            "S_OB_FORMATION",
            "S_BREAKER_FORMATION",
            "S_STB_FORMATION",
            "S_RANGE_FORMATION",
        ],
        "M3_VALIDATION": [],
    }
    rules = [
        {
            "rule_id": item["rule_id"],
            "classification": "MACHINE_RULE_PRE_OUTCOME",
            "normative_definition": item,
            "source_references": source_refs[item["rule_id"]],
            "source_concept_not_selector_equivalence": True,
            "causal_fields": "completed features/known_at <= decision; no outcome columns",
            "PnL_tuning": False,
            "numerical_rationale": "Inherited conventions or exact grid/price/cost arithmetic; new two-leg state is strict HH+HL/LH+LL geometry, not an outcome search",
        }
        for item in (*components.values(), validation)
    ]
    rules += [
        {
            "rule_id": "M3_TICK_WAIT",
            "classification": "UNRESOLVED_WAIT_RULE",
            "definition": risk["tick_requirement"],
            "reason": "No verified historical tick epochs in frozen metadata evidence",
        },
        {
            "rule_id": "M3_COST_FEASIBILITY",
            "classification": "EXECUTION_SAFETY_RULE",
            "definition": execution["economics"],
            "reason": "Strictly positive declared target net; not positive expectancy",
        },
        {
            "rule_id": "M3_INTRABAR_WAIT",
            "classification": "UNRESOLVED_WAIT_RULE",
            "definition": execution["entry_bar_ambiguity"],
            "reason": "OHLC lacks tick-order evidence; no continuity inference",
        },
        {
            "rule_id": "M3_SOURCE_CONCEPTS",
            "classification": "SOURCE_DERIVED",
            "definition": "Source supports structural direction/first FTA/stop/family concepts only; no machine selector promoted",
            "references": EVIDENCE[1],
            "source_validated": False,
        },
    ]
    registry = {
        "rules": rules,
        "inherited_rules": inherited,
        "source_citations": sources,
        "source_registry_sha256": checksum(ROOT / EVIDENCE[1]),
        "forbidden_justification": "historically profitable subgroup",
        "source_validated": False,
    }
    spec = {
        "version": "MACHINE_STRATEGY_v3",
        "status": "PRE_OUTCOME_DESIGN_ONLY",
        "components": components,
        "validation": validation,
        "rule_registry": "RULE_PROVENANCE.json",
        "failure_audit_sha256": AUDIT_SHA,
        "implementation": {
            "code": CODE,
            "scope": validation["implementation_scope"],
            "historical_case_adapter_implemented": False,
        },
        "financial_result": "UNKNOWN_NOT_RUN",
        "outcome_parameters_selected": False,
        "base": "Independent modeled cases; no portfolio/sizing/leverage/correlation/fallback overlay",
        "trade_entry_allowed": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, item in components.items():
        save(output / name, item)
    save(output / "MACHINE_STRATEGY_V3_SPEC.json", spec)
    save(output / "RULE_PROVENANCE.json", registry)
    save(output / "DATA_EXPOSURE_INVENTORY.json", inventory)
    save(output / "VALIDATION_PROTOCOL.json", validation)
    save(output / "FROZEN_INPUT_VERIFICATION.json", inputs)
    lines = [
        "# MACHINE_STRATEGY_v3 pre-outcome specification",
        "",
        "A separate machine architecture; Original and frozen v2.x unchanged. No financial outcome computed. trade_entry_allowed=false; PAPER/LIVE off.",
        "",
        "Normative definitions are the component JSON objects and their fully listed provenance registry. Inherited M2 definitions are reproduced verbatim with override markers, pinned to immutable source; new selectors are machine conventions, never SOURCE_RULE promotions.",
        "",
    ]
    for name, component in components.items():
        lines += [
            "## " + name,
            "",
            "```json",
            json.dumps(component, indent=2),
            "```",
            "",
        ]
    lines += [
        "## Implementation and readiness",
        "",
        validation["implementation_scope"],
        "",
        "Synthetic contracts validate causality/price geometry/execution observations. No historical v3 case adapter or financial runner is created here; its future implementation needs a separately frozen pre-outcome commit and QA. Historical tick evidence remains absent. Current first financial gate: STOP; current independent OOS gate: STOP_NO_PRISTINE_OOS. No production candidate.",
    ]
    (output / "MACHINE_STRATEGY_V3_SPEC.md").write_text("\n".join(lines) + "\n")
    (output / "CAUSAL_HYPOTHESES.md").write_text(
        "# Causal hypotheses, not demonstrated edge\n\nH1: Completed protected-origin/endpoint progression can represent directional auction state symmetrically, beyond context IDs alone. H4 interior range precedence and transition-origin POI are explicit hypotheses, not ranked historical subgroups.\n\nH2: Stop-loss plus declared transaction cost is a finite per-unit cash-risk basis without moving structural invalidation. Tiny raw stops and implied notional remain visible; normalized cash R does not solve execution, leverage or portfolio risk.\n\nH3: A nearest causal obstacle must support strictly positive modeled target net before entry; rejecting an algebraically negative opportunity is economic feasibility, not proof of positive expectancy. Do not skip the obstacle to improve RR.\n\nH4: Conservative intrabar WAIT and independently recorded occurrence bounds avoid invented elapsed duration.\n\nAll five families and both directions remain; no thresholds, symbols, years or branches were selected by financial ranking. Historical audit is development exposure. New hypotheses remain unvalidated until separate frozen testing and genuinely independent evaluation.\n"
    )
    (output / "VALIDATION_PROTOCOL.md").write_text(
        "# Validation and exposure protocol\n\n```json\n"
        + json.dumps(validation, indent=2)
        + "\n```\n\nAll local native/public/derived histories and source aliases are inventoried by hashes, underlying series, timestamps and prior research use. Renaming TEST, recompressing or aggregating candles does not restore independence. The future registration resolves the frozen-commit UTC boundary before its first observation. A changed implementation gets a new freeze and new OOS window; it must not reuse this window as untouched after any result inspection.\n"
    )
    print(
        "V3_DESIGN_BUILT",
        output,
        "exposed_physical_files",
        len(inventory["series"]),
        "financial_NOT_RUN",
        flush=True,
    )


def seal(replay):
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("Existing v3 freeze preserved")
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != "machine-v3-research"
    ):
        raise ValueError("Research branch required")
    review = read(
        str((DEST / "independent_review/FINAL_REVIEW.json").relative_to(ROOT))
    )
    if review.get("status") != "PASS" or review.get("reviewer") != "backtest_reviewer":
        raise ValueError("Independent final PASS required")
    if review.get("code_sha256") != {n: checksum(ROOT / n) for n in CODE}:
        raise ValueError("Code changed after independent review")
    if review.get("generated_sha256") != {n: checksum(DEST / n) for n in GENERATED}:
        raise ValueError("Generated design changed after review")
    for role in (
        "strategy_explorer",
        "strategy_designer",
        "execution_auditor",
        "backtest_reviewer",
    ):
        if not (DEST / "independent_review" / (role + ".md")).is_file():
            raise ValueError("Missing actual role report: " + role)
    qa = qa_stage(DEST, CODE, Path(replay).resolve(), GENERATED, minimum_tests=964)
    commands = read(str((DEST / "qa/COMMAND_RECEIPT.json").relative_to(ROOT)))
    if commands["code_sha256"] != qa["code_sha256"] or commands["status"] != "PASS":
        raise ValueError("Code/QA execution receipt mismatch")
    inputs = frozen_inputs()
    if read(str((DEST / "FROZEN_INPUT_VERIFICATION.json").relative_to(ROOT))) != inputs:
        raise ValueError("Frozen inputs changed after generation")
    (DEST / "QA_REPORT.md").write_text(
        f"# V3 nonfinancial QA\n\nPASS: {qa['tests']} full inherited/new tests; {len(GENERATED)} design outputs byte-identical under fresh replay. Lint/type/compile/Original resume PASS. Frozen audit, all14 machine namespaces, Original/source/baseline invariance PASS. All4 roles contributed; final independent PASS required and retained.\n\nNew synthetic tests cover completed-prefix/future mutation, known-at/outcome rejection, structural state, all5family price projections (full raw-event adapter deferred), tick/price/cost units, mirrored predicates and transform-aware symmetry, metadata gaps, limit gaps, intrabar uncertainty, and duplicate reservation. No historical v3 cohort or aggregate financial metrics were produced.\n\nImplementation is a nonfinancial contract core, not a historical event adapter or qualified executable exchange system. First financial gate STOP for missing adapter/historical tick epochs; OOS STOP for absent pristine data, with prospective registration fixed. trade_entry_allowed=false; PAPER/LIVE off.\n"
    )
    artifacts = {
        str(p.relative_to(ROOT)): checksum(p) for p in DEST.rglob("*") if p.is_file()
    }
    artifacts.update({n: checksum(ROOT / n) for n in CODE})
    protected = dict(inputs["source_and_exposure_evidence_sha256"])
    inventory = read(str((DEST / "DATA_EXPOSURE_INVENTORY.json").relative_to(ROOT)))
    for row in inventory["series"]:
        protected[row["path"]] = row["stored_sha256"]
    for source in read(EVIDENCE[1]).values():
        for passage in source.get("primary_passages", []):
            protected[passage["source_document"]] = passage["source_sha256"]
    for name in (
        "scripts/machine_strategy_v2_core.py",
        "scripts/original_v1_1_objective_geometry_v2.py",
    ):
        protected[name] = checksum(ROOT / name)
    for name, expected in protected.items():
        if checksum(ROOT / name) != expected:
            raise ValueError("Frozen dataset/source byte mismatch: " + name)
    artifacts.update(protected)
    save(
        DEST / "freeze_manifest.json",
        {
            "stage": "design",
            "version": "MACHINE_STRATEGY_v3",
            "status": "FROZEN_PRE_OUTCOME",
            "parents": {inputs["failure_audit"]["path"]: AUDIT_SHA},
            "artifacts": dict(sorted(artifacts.items())),
            "QA_tests": qa["tests"],
            "financial_result": "UNKNOWN_NOT_RUN",
            "outcomes_computed": False,
            "v3_cases_built": False,
            "first_financial_backtest_ready": False,
            "trade_entry_allowed": False,
            "LIVE_enabled": False,
            "PAPER_enabled": False,
        },
    )
    print("FROZEN_V3_DESIGN", checksum(DEST / "freeze_manifest.json"), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEST)
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--resume-existing", action="store_true")
    args = parser.parse_args()
    if args.resume_existing:
        frozen_inputs()
        print("VERIFIED_V3_DESIGN_RESUME", verify_machine(DEST))
    elif args.seal:
        seal(args.seal)
    else:
        build(args.output)


if __name__ == "__main__":
    main()
