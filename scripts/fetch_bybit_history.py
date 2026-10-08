from __future__ import annotations

import argparse
import os
import sys
import time
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
    parser = argparse.ArgumentParser(description="Download and audit public Bybit historical candles.")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--interval", default="1", help="Bybit interval, e.g. 1, 5, 15, 60, 240, D")
    parser.add_argument("--days", type=int, default=2, help="Number of recent calendar days to request")
    parser.add_argument("--base-url", default=os.getenv("BYBIT_BASE_URL", "https://api.bybit.com"))
    parser.add_argument("--output", default="data/history/bybit")
    args = parser.parse_args()

    if args.days <= 0:
        parser.error("--days must be positive")

    client = BybitPublicClient(base_url=args.base_url)
    try:
        interval_ms = client.interval_ms(args.interval)
        end_ms = client.get_server_time_ms()
    except (BybitAPIError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    start_ms = end_ms - args.days * 24 * 60 * 60 * 1000

    overall_ok = True
    for symbol in args.symbols:
        print(f"\n[{symbol}] downloading {args.interval}m-equivalent candles...")
        try:
            info = client.get_instrument_info(symbol)
            if info.status != "Trading":
                raise BybitAPIError(f"{symbol.upper()} is not in Trading status: {info.status}")
            if not info.is_usdt_linear_perpetual:
                raise BybitAPIError(
                    f"{symbol.upper()} is not a USDT linear perpetual "
                    f"(contractType={info.contract_type!r}, quote={info.quote_coin!r}, settle={info.settle_coin!r})"
                )
            symbol_start = max(start_ms, info.launch_time_ms or start_ms)
            if symbol_start > end_ms:
                raise BybitAPIError(f"{symbol.upper()} launch time is after the requested end time")
            fetch = client.fetch_klines(
                symbol=symbol,
                interval=args.interval,
                start_ms=symbol_start,
                end_ms=end_ms,
            )
        except (BybitAPIError, ValueError) as exc:
            print(f"ERROR: {exc}")
            overall_ok = False
            continue

        qa = audit_klines(fetch.candles, interval_ms)
        coverage = audit_coverage(fetch, interval_ms)
        out_path = Path(args.output) / symbol.upper() / f"{args.interval}.csv"
        write_klines_csv(fetch.candles, out_path)

        print(f"  status:              {info.status}")
        print(f"  contract type:       {info.contract_type}")
        print(f"  launch:              {iso_utc(info.launch_time_ms)}")
        print(f"  candles saved:       {len(fetch.candles)}")
        print(f"  expected closed:     {coverage.expected_count}")
        print(f"  coverage:            {coverage.completeness_pct:.4f}%")
        print(f"  QA gaps:             {qa.gap_count}")
        print(f"  QA duplicates:       {qa.duplicate_count}")
        print(f"  QA out-of-order:     {qa.out_of_order_count}")
        print(f"  QA misaligned:       {qa.misaligned_count}")
        print(f"  QA metadata:         {qa.metadata_mismatch_count}")
        print(f"  output:              {out_path}")
        if not qa.is_healthy or coverage.missing_count:
            overall_ok = False
            print("  RESULT: REVIEW REQUIRED")
        else:
            print("  RESULT: OK")

    return 0 if overall_ok else 2


if __name__ == "__main__":
    sys.exit(main())
