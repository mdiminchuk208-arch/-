from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from crypto_bot.data.bybit import BybitAPIError, BybitPublicClient
from crypto_bot.data.coverage import audit_coverage
from crypto_bot.data.qa import audit_klines
from crypto_bot.data.storage import write_klines_csv


def iso_utc(ms: int | None) -> str:
    if ms is None:
        return "n/a"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public Bybit candles for Phase-1.4 multi-timeframe SFP analysis.")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument(
        "--intervals",
        nargs="+",
        default=["5", "15", "60", "240"],
        help="Bybit fixed intervals. Defaults are experiment conveniences, not source-mandated HTF/LTF mappings.",
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default=os.getenv("BYBIT_BASE_URL", "https://api.bybit.com"))
    parser.add_argument("--output", default="data/history/bybit")
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be positive")

    client = BybitPublicClient(base_url=args.base_url)
    try:
        end_ms = client.get_server_time_ms()
        interval_ms_map = {interval: client.interval_ms(interval) for interval in args.intervals}
    except (BybitAPIError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    start_ms = end_ms - args.days * 24 * 60 * 60 * 1000

    overall_ok = True
    for raw_symbol in args.symbols:
        symbol = raw_symbol.upper()
        try:
            info = client.get_instrument_info(symbol)
            if info.status != "Trading":
                raise BybitAPIError(f"{symbol} is not in Trading status: {info.status}")
            if not info.is_usdt_linear_perpetual:
                raise BybitAPIError(f"{symbol} is not a crypto USDT linear perpetual supported by this phase")
        except (BybitAPIError, ValueError) as exc:
            print(f"\n[{symbol}] ERROR: {exc}")
            overall_ok = False
            continue

        symbol_start = max(start_ms, info.launch_time_ms or start_ms)
        print(f"\n[{symbol}] launch={iso_utc(info.launch_time_ms)}")
        for interval in args.intervals:
            interval_ms = interval_ms_map[interval]
            print(f"  interval {interval}: downloading...")
            try:
                fetch = client.fetch_klines(
                    symbol=symbol,
                    interval=interval,
                    start_ms=symbol_start,
                    end_ms=end_ms,
                )
            except (BybitAPIError, ValueError) as exc:
                print(f"    ERROR: {exc}")
                overall_ok = False
                continue
            qa = audit_klines(fetch.candles, interval_ms)
            coverage = audit_coverage(fetch, interval_ms)
            out_path = Path(args.output) / symbol / f"{interval}.csv"
            write_klines_csv(fetch.candles, out_path)
            print(f"    candles:    {len(fetch.candles)}")
            print(f"    coverage:   {coverage.completeness_pct:.4f}%")
            print(f"    coverage status: {coverage.coverage_status}")
            if coverage.missing_count:
                print(
                    "    missing slots: "
                    f"total={coverage.missing_count} leading={coverage.leading_missing_count} "
                    f"internal={coverage.internal_missing_count} trailing={coverage.trailing_missing_count}"
                )
                preview = coverage.missing_open_times_ms[:5]
                if preview:
                    print("    missing UTC opens: " + ", ".join(iso_utc(x) for x in preview))
                if coverage.boundary_missing_count and not coverage.internal_missing_count:
                    print("    coverage note: rows are internally continuous; shortfall is at requested-window boundary.")
            print(f"    QA healthy: {qa.is_healthy}")
            print(f"    output:     {out_path}")
            if not qa.is_healthy or coverage.missing_count:
                overall_ok = False
                print("    RESULT: REVIEW REQUIRED")
            else:
                print("    RESULT: OK")
    return 0 if overall_ok else 2


if __name__ == "__main__":
    sys.exit(main())
