"""Cross-asset causal robustness audit for the production SOURCE_CONSERVATIVE path.

This script is QA only. It never creates an entry, order, profitability threshold or
new source rule. It validates the same production structure/SFP/MTF invariants across
a broader symbol basket before Entry Engine work.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from crypto_bot import __version__ as PACKAGE_VERSION

from crypto_bot.data.qa import audit_klines
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.cross_asset_validation import (
    DEFAULT_CROSS_ASSET_BASKET,
    REQUIRED_TIMEFRAMES,
    SymbolRobustnessChecks,
    decide_cross_asset_gate,
    normalize_symbols,
)
from crypto_bot.strategy.market_analysis import (
    MarketEventKind,
    StructureAnalysisMode,
    TrendState,
    analyze_market,
)
from crypto_bot.strategy.mtf_sfp import link_sfp_formations_to_ltf_bos
from crypto_bot.strategy.recovery_ablation import plain
from crypto_bot.strategy.structure_stability import compare_bos_suffix


BOS_KINDS = {
    MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
    MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
}
SFP_KINDS = {
    MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED,
    MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED,
}
PAIRS = ((60, 5), (240, 15))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plain(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def input_record(path: Path, rows, qa, span_days: float) -> dict:
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(rows),
        "start_open_time_ms": rows[0].open_time_ms if rows else None,
        "end_open_time_ms": rows[-1].open_time_ms if rows else None,
        "span_days": span_days,
        "qa": asdict(qa),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_CROSS_ASSET_BASKET))
    parser.add_argument("--data-root", type=Path, default=Path("data/history/bybit"))
    parser.add_argument("--report-root", type=Path, default=Path("data/reports/phase1_4_16/cross_asset_240d"))
    parser.add_argument("--evaluation-days", type=int, default=240)
    parser.add_argument("--suffix-days", type=int, default=60)
    parser.add_argument("--stabilization-days", type=int, default=30)
    parser.add_argument("--analysis-warmup-days", type=int, default=0, help="Extra history loaded before the evaluation window; QA only, not a trading parameter.")
    parser.add_argument(
        "--diagnostic-recovery",
        action="store_true",
        help="Also run TECHNICAL_RECOVERY structure diagnostics. This never affects the gate decision.",
    )
    args = parser.parse_args()
    if args.evaluation_days <= 0 or args.suffix_days <= 0 or args.stabilization_days < 0 or args.analysis_warmup_days < 0:
        parser.error("evaluation/suffix days must be positive; stabilization/warmup days cannot be negative")
    if args.suffix_days >= args.evaluation_days:
        parser.error("--suffix-days must be smaller than --evaluation-days")

    symbols = normalize_symbols(args.symbols)
    required_basket = DEFAULT_CROSS_ASSET_BASKET
    root = Path(__file__).resolve().parents[1]
    report_root = args.report_root
    report_root.mkdir(parents=True, exist_ok=True)

    loaded: dict[str, dict[int, list]] = {}
    input_manifests: dict[str, dict] = {}
    preflight_errors: dict[str, list[str]] = {}
    symbol_common_ends = []

    for symbol in symbols:
        loaded[symbol] = {}
        input_manifests[symbol] = {}
        preflight_errors[symbol] = []
        for tf in REQUIRED_TIMEFRAMES:
            path = args.data_root / symbol / f"{tf}.csv"
            if not path.exists():
                preflight_errors[symbol].append(f"missing input: {path}")
                continue
            rows = read_klines_csv(path)
            if not rows:
                preflight_errors[symbol].append(f"empty input: {path}")
                continue
            qa = audit_klines(rows, tf * 60_000)
            identity_ok = all(r.symbol == symbol and r.interval == str(tf) and r.exchange == "BYBIT" for r in rows)
            if not qa.is_healthy:
                preflight_errors[symbol].append(f"unhealthy data: {path}")
            if not identity_ok:
                preflight_errors[symbol].append(f"incorrect series identity: {path}")
            candles = [r.to_strategy_candle(tf * 60_000) for r in rows]
            span_days = (candles[-1].close_time - candles[0].open_time).total_seconds() / 86400
            minimum_span = args.evaluation_days - tf / 1440
            if span_days < minimum_span:
                preflight_errors[symbol].append(
                    f"insufficient span for {args.evaluation_days}d evaluation: {path} ({span_days:.6f}d)"
                )
            loaded[symbol][tf] = candles
            input_manifests[symbol][str(tf)] = input_record(path, rows, qa, span_days)
        if len(loaded[symbol]) == len(REQUIRED_TIMEFRAMES):
            symbol_common_ends.append(min(candles[-1].close_time for candles in loaded[symbol].values()))

    runnable_symbols = tuple(symbol for symbol in symbols if not preflight_errors[symbol] and len(loaded[symbol]) == 4)
    if not runnable_symbols:
        payload = {
            "version": PACKAGE_VERSION,
            "gate": asdict(decide_cross_asset_gate({}, required_basket=required_basket)),
            "preflight_errors": preflight_errors,
            "inputs": input_manifests,
            "checks_passed": False,
        }
        write_json(report_root / "summary.json", payload)
        print("No symbol has a complete healthy 5/15/60/240 dataset; cross-asset gate remains OPEN.")
        return 2

    # All compared symbols use one common UTC end so the basket is evaluated over the same market regime.
    global_end = min(
        min(loaded[symbol][tf][-1].close_time for tf in REQUIRED_TIMEFRAMES)
        for symbol in runnable_symbols
    )
    evaluation_start = global_end - timedelta(days=args.evaluation_days)
    suffix_start = global_end - timedelta(days=args.suffix_days)
    compare_start = suffix_start + timedelta(days=args.stabilization_days)
    analysis_start = evaluation_start - timedelta(days=args.analysis_warmup_days)

    checks: dict[str, SymbolRobustnessChecks] = {}
    symbol_summaries: dict[str, dict] = {}
    matrix_rows: list[dict] = []

    for symbol in runnable_symbols:
        reports = {}
        tf_summary = {}
        source_recovery_free = True
        suffix_exact = True
        trade_safe = True
        mtf_runtime_passed = True
        print(f"{symbol}: SOURCE_CONSERVATIVE structure audit", flush=True)
        for tf in REQUIRED_TIMEFRAMES:
            cs = [c for c in loaded[symbol][tf] if c.open_time >= analysis_start and c.close_time <= global_end]
            full = analyze_market(cs, timeframe_minutes=tf, analysis_mode=StructureAnalysisMode.SOURCE_CONSERVATIVE)
            reports[tf] = full
            suffix = [c for c in cs if c.open_time >= suffix_start]
            if not suffix:
                raise ValueError(f"empty suffix for {symbol} {tf}")
            short = analyze_market(suffix, timeframe_minutes=tf, analysis_mode=StructureAnalysisMode.SOURCE_CONSERVATIVE)
            stability = compare_bos_suffix(full, short, compare_start=compare_start)
            exact = stability.full_only_count == 0 and stability.suffix_only_count == 0 and stability.exact_jaccard == 1.0
            suffix_exact &= exact
            source_recovery_free &= not any(e.recovery_transition_ids for e in full.events)
            source_recovery_free &= not any(
                t.resolution_mode == "SAME_DIRECTION_POST_BOS_RECOVERY" for t in full.structure_transition_diagnostics
            )
            bos_count = sum(e.kind in BOS_KINDS and e.event_time >= evaluation_start for e in full.events)
            sfp_count = sum(e.kind in SFP_KINDS and e.event_time >= evaluation_start for e in full.events)
            info = {
                "bos_count_evaluation": bos_count,
                "structural_sfp_count_evaluation": sfp_count,
                "state_candle_counts": full.state_candle_counts(),
                "longest_broken_run": full.longest_state_run(TrendState.BROKEN),
                "transition_resolution_modes": dict(Counter(t.resolution_mode for t in full.structure_transition_diagnostics)),
                "suffix_stability": asdict(stability),
                "suffix_exact": exact,
            }
            if args.diagnostic_recovery:
                tech = analyze_market(cs, timeframe_minutes=tf, analysis_mode=StructureAnalysisMode.TECHNICAL_RECOVERY)
                info["diagnostic_recovery"] = {
                    "bos_count_evaluation": sum(e.kind in BOS_KINDS and e.event_time >= evaluation_start for e in tech.events),
                    "structural_sfp_count_evaluation": sum(e.kind in SFP_KINDS and e.event_time >= evaluation_start for e in tech.events),
                    "recovery_transition_count": sum(
                        t.resolution_mode == "SAME_DIRECTION_POST_BOS_RECOVERY" for t in tech.structure_transition_diagnostics
                    ),
                }
            tf_summary[str(tf)] = info

        pair_summary = {}
        for htf, ltf in PAIRS:
            try:
                mtf = link_sfp_formations_to_ltf_bos(
                    reports[htf],
                    reports[ltf],
                    htf_minutes=htf,
                    ltf_minutes=ltf,
                    max_wait_ltf_bars=None,
                    max_wait_minutes=None,
                    candidate_not_before=evaluation_start,
                    ltf_observation_start=loaded[symbol][ltf][0].open_time,
                    ltf_observation_end=global_end,
                )
                candidate_trade_flags = [c.trade_entry_allowed for c in mtf.candidates]
                opportunity_trade_flags = [o.trade_entry_allowed for o in mtf.opportunities]
                safe = not any(candidate_trade_flags) and not any(opportunity_trade_flags)
                trade_safe &= safe
                pair_summary[f"{htf}_to_{ltf}"] = {
                    "candidate_count": len(mtf.candidates),
                    "confirmed_context_count": mtf.confirmed_count,
                    "unique_ltf_bos_count": mtf.unique_ltf_bos_count,
                    "opportunity_count": len(mtf.opportunities),
                    "trade_entry_safety_passed": safe,
                    "validation_scope": "STRUCTURAL_SWING_SFP_ONLY_RANGE_GATES_SEPARATE",
                    "entry_engine_blocking_reasons": mtf.entry_engine_blocking_reasons,
                }
            except Exception as exc:  # report the symbol as failed instead of silently skipping it
                mtf_runtime_passed = False
                pair_summary[f"{htf}_to_{ltf}"] = {"runtime_error": f"{type(exc).__name__}: {exc}"}

        check = SymbolRobustnessChecks(
            symbol=symbol,
            data_qa_passed=True,
            evaluation_span_passed=True,
            source_recovery_free=source_recovery_free,
            suffix_stability_exact=suffix_exact,
            trade_entry_safety_passed=trade_safe,
            mtf_runtime_passed=mtf_runtime_passed,
        )
        checks[symbol] = check
        symbol_summaries[symbol] = {
            "checks": asdict(check),
            "passed": check.passed,
            "timeframes": tf_summary,
            "mtf": pair_summary,
        }
        for tf_label, row in tf_summary.items():
            matrix_rows.append(
                {
                    "symbol": symbol,
                    "timeframe": tf_label,
                    "bos_count_evaluation": row["bos_count_evaluation"],
                    "structural_sfp_count_evaluation": row["structural_sfp_count_evaluation"],
                    "longest_broken_run": row["longest_broken_run"],
                    "suffix_exact": row["suffix_exact"],
                }
            )
        write_json(report_root / symbol / "summary.json", symbol_summaries[symbol])

    gate = decide_cross_asset_gate(checks, required_basket=required_basket)
    code_hashes = {}
    tracked = sorted((root / "src").rglob("*.py")) + [Path(__file__).resolve(), root / "config/source_rules.json", root / "pyproject.toml"]
    for path in tracked:
        code_hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()

    payload = {
        "version": PACKAGE_VERSION,
        "analysis_mode": StructureAnalysisMode.SOURCE_CONSERVATIVE.value,
        "evaluation_days": args.evaluation_days,
        "suffix_days": args.suffix_days,
        "stabilization_days": args.stabilization_days,
        "analysis_warmup_days": args.analysis_warmup_days,
        "global_evaluation_start": evaluation_start,
        "global_evaluation_end": global_end,
        "required_basket": required_basket,
        "requested_symbols": symbols,
        "runnable_symbols": runnable_symbols,
        "preflight_errors": preflight_errors,
        "inputs": input_manifests,
        "code_hashes": code_hashes,
        "gate": asdict(gate),
        "checks_passed": gate.gate_closed,
        "interpretation": (
            "Pass/fail uses only data/causality/provenance/runtime/safety invariants. BOS/SFP/opportunity counts are "
            "diagnostic and are not profitability or trading-quality thresholds. Range normalization gates remain separate."
        ),
        "symbols": symbol_summaries,
    }
    write_json(report_root / "summary.json", payload)

    with (report_root / "cross_asset_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "symbol",
            "timeframe",
            "bos_count_evaluation",
            "structural_sfp_count_evaluation",
            "longest_broken_run",
            "suffix_exact",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(matrix_rows)

    print(f"Cross-asset gate closed: {gate.gate_closed}")
    if gate.missing_required_symbols:
        print("Missing required symbols: " + ", ".join(gate.missing_required_symbols))
    if gate.failed_symbols:
        print("Failed symbols: " + ", ".join(gate.failed_symbols))
    return 0 if gate.gate_closed else 3


if __name__ == "__main__":
    raise SystemExit(main())
