from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

from crypto_bot.analysis_report import write_structure_transition_csv, write_trend_state_csv
from crypto_bot.data.bybit import BybitPublicClient
from crypto_bot.data.qa import audit_klines
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import MarketAnalysisError, TrendState, analyze_market
from crypto_bot.strategy.structure_stability import compare_bos_suffix


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase-1.4.12 structure-only lifecycle audit: compare recent BOS from full loaded "
            "history against an isolated recent suffix and export BROKEN-transition diagnostics."
        )
    )
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--intervals", nargs="+", default=["5", "15", "60", "240"])
    parser.add_argument("--data-root", default="data/history/bybit")
    parser.add_argument("--report-root", default="data/reports/phase1_4_14/structure_lifecycle_audit")
    parser.add_argument("--suffix-days", type=int, default=60)
    parser.add_argument(
        "--stabilization-days",
        type=int,
        default=7,
        help="QA guard excluded from the left edge of isolated suffix analysis; TECHNICAL QA parameter.",
    )
    args = parser.parse_args()
    if args.suffix_days <= 0:
        parser.error("--suffix-days must be positive")
    if args.stabilization_days < 0 or args.stabilization_days >= args.suffix_days:
        parser.error("--stabilization-days must be >=0 and < --suffix-days")

    ok = True
    for raw_symbol in args.symbols:
        symbol = raw_symbol.upper()
        for interval in args.intervals:
            try:
                interval_ms = BybitPublicClient.interval_ms(interval)
            except ValueError as exc:
                print(f"ERROR {symbol} {interval}: {exc}", file=sys.stderr)
                ok = False
                continue
            path = Path(args.data_root) / symbol / f"{interval}.csv"
            if not path.exists():
                print(f"MISSING {path}")
                ok = False
                continue
            rows = read_klines_csv(path)
            qa = audit_klines(rows, interval_ms)
            if not rows or not qa.is_healthy:
                print(f"BLOCKED {symbol} {interval}: rows={len(rows)} healthy={qa.is_healthy}")
                ok = False
                continue
            candles = [row.to_strategy_candle(interval_ms) for row in rows]
            end = candles[-1].close_time
            suffix_start = end - timedelta(days=args.suffix_days)
            suffix = [c for c in candles if c.open_time >= suffix_start]
            if len(suffix) < 3:
                print(f"BLOCKED {symbol} {interval}: suffix has fewer than 3 candles")
                ok = False
                continue
            try:
                full_report = analyze_market(candles, timeframe_minutes=interval_ms // 60_000)
                suffix_report = analyze_market(suffix, timeframe_minutes=interval_ms // 60_000)
            except MarketAnalysisError as exc:
                print(f"ANALYSIS ERROR {symbol} {interval}: {exc}")
                ok = False
                continue
            compare_start = suffix[0].open_time + timedelta(days=args.stabilization_days)
            stability = compare_bos_suffix(full_report, suffix_report, compare_start=compare_start)
            out = Path(args.report_root) / symbol / interval
            out.mkdir(parents=True, exist_ok=True)
            write_trend_state_csv(full_report, out / "full_state_segments.csv")
            write_trend_state_csv(suffix_report, out / "suffix_state_segments.csv")
            write_structure_transition_csv(full_report, out / "full_structure_transitions.csv")
            write_structure_transition_csv(suffix_report, out / "suffix_structure_transitions.csv")
            payload = {
                "symbol": symbol,
                "interval": interval,
                "loaded_candles": len(candles),
                "suffix_candles": len(suffix),
                "suffix_days": args.suffix_days,
                "stabilization_days": args.stabilization_days,
                "compare_start": compare_start.isoformat(),
                "full_state_counts": full_report.state_candle_counts(),
                "suffix_state_counts": suffix_report.state_candle_counts(),
                "full_longest_broken": full_report.longest_state_run(TrendState.BROKEN),
                "suffix_longest_broken": suffix_report.longest_state_run(TrendState.BROKEN),
                "full_transition_count": len(full_report.structure_transition_diagnostics),
                "suffix_transition_count": len(suffix_report.structure_transition_diagnostics),
                "full_unresolved_transition_count": sum(
                    1 for x in full_report.structure_transition_diagnostics if x.resolved_trend is None
                ),
                "suffix_unresolved_transition_count": sum(
                    1 for x in suffix_report.structure_transition_diagnostics if x.resolved_trend is None
                ),
                "bos_suffix_stability": {
                    "full_count": stability.full_count,
                    "suffix_count": stability.suffix_count,
                    "exact_overlap_count": stability.exact_overlap_count,
                    "full_only_count": stability.full_only_count,
                    "suffix_only_count": stability.suffix_only_count,
                    "exact_jaccard": stability.exact_jaccard,
                },
                "qa_note": (
                    "No pass threshold is hard-coded. Prepending older history may change the isolated suffix left edge; "
                    "the stabilization guard reduces that boundary effect. This report is diagnostic, not a trading rule."
                ),
            }
            (out / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                f"[{symbol} {interval}] full BOS={stability.full_count}, suffix BOS={stability.suffix_count}, "
                f"overlap={stability.exact_overlap_count}, jaccard={stability.exact_jaccard:.3f}; "
                f"full longest BROKEN={payload['full_longest_broken']}, unresolved={payload['full_unresolved_transition_count']}"
            )
            print(f"  output: {out / 'summary.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
