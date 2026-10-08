from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from crypto_bot.analysis_report import write_event_csv, write_summary_json, write_sweep_episode_csv, write_trend_state_csv
from crypto_bot.data.bybit import BybitPublicClient
from crypto_bot.data.qa import audit_klines
from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import MarketAnalysisError, TrendState, analyze_market


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze downloaded Bybit candles with Phase-1.3 causal structure/liquidity logic.")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--interval", default="1")
    parser.add_argument("--data-root", default="data/history/bybit")
    parser.add_argument("--report-root", default="data/reports/phase1_3")
    parser.add_argument("--show-last", type=int, default=12, help="Print the last N detected events for each symbol.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        interval_ms = BybitPublicClient.interval_ms(args.interval)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    overall_ok = True
    for raw_symbol in args.symbols:
        symbol = raw_symbol.upper()
        csv_path = Path(args.data_root) / symbol / f"{args.interval}.csv"
        print(f"\n[{symbol}] reading {csv_path}")
        if not csv_path.exists():
            print("  RESULT: MISSING CSV — run fetch_bybit_history.py first")
            overall_ok = False
            continue

        candles = read_klines_csv(csv_path)
        qa = audit_klines(candles, interval_ms)
        print(f"  rows:              {len(candles)}")
        print(f"  QA healthy:        {qa.is_healthy}")
        print(f"  QA gaps:           {qa.gap_count}")
        print(f"  QA duplicates:     {qa.duplicate_count}")
        print(f"  QA out-of-order:   {qa.out_of_order_count}")
        print(f"  QA unfinished:     {qa.unfinished_count}")
        print(f"  QA misaligned:     {qa.misaligned_count}")
        if not qa.is_healthy:
            print("  ANALYSIS BLOCKED: market strategy is not run on unhealthy data")
            overall_ok = False
            continue

        strategy_candles = [c.to_strategy_candle(interval_ms) for c in candles]
        try:
            report = analyze_market(strategy_candles, timeframe_minutes=max(1, interval_ms // 60_000))
        except MarketAnalysisError as exc:
            print(f"  ANALYSIS ERROR: {exc}")
            overall_ok = False
            continue

        counts = Counter(event.kind.value for event in report.events)
        print(f"  structural levels: {len(report.levels)}")
        print(f"  sweep episodes:    {len(report.sweep_episodes)}")
        print(f"  events:            {len(report.events)}")
        print(f"  final trend:       {report.final_trend.value}")
        state_counts = report.state_candle_counts()
        print(
            "  trend states:      "
            + ", ".join(f"{key}={value}" for key, value in state_counts.items())
            + f"; longest BROKEN={report.longest_state_run(TrendState.BROKEN)} candles"
        )
        print(f"  SFP TF preference: {report.sfp_timeframe_preference}")
        if report.sfp_timeframe_preference == "SOURCE_VALID_BELOW_PREFERRED_H1":
            print("    NOTE: the source allows SFP on any timeframe but explicitly prefers H1 and above for SFP search.")
            print("    NOTE: these are SFP formations, not trade entries; LTF BOS is still required afterwards.")
        for key, value in sorted(counts.items()):
            print(f"    {key:<30} {value}")

        print(f"  BOS policy:         {report.structure_policy}")
        print(f"  OB auto-validation: {report.order_block_readiness.status}")
        for reason in report.order_block_readiness.blocking_reasons:
            print(f"    - {reason}")

        last_n = max(0, args.show_last)
        print(f"  last {last_n} events:")
        recent_events = report.events[-last_n:] if last_n else ()
        for event in recent_events:
            print(
                f"    {event.event_time.isoformat()} | {event.kind.value:<28} "
                f"price={event.price:g} level={event.level_price:g} id={event.level_id}"
                f" episode={event.episode_id if event.episode_id is not None else '-'}"
            )

        report_dir = Path(args.report_root) / symbol / args.interval
        events_path = write_event_csv(report, report_dir / "events.csv")
        episodes_path = write_sweep_episode_csv(report, report_dir / "sweep_episodes.csv")
        state_path = write_trend_state_csv(report, report_dir / "trend_state_segments.csv")
        summary_path = write_summary_json(report, report_dir / "summary.json")
        print(f"  events output:      {events_path}")
        print(f"  episodes output:    {episodes_path}")
        print(f"  state audit output: {state_path}")
        print(f"  summary output:     {summary_path}")
        print("  RESULT: OK")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
