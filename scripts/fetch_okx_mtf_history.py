from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from crypto_bot.data.okx import OKXAPIError, OKXPublicClient
from crypto_bot.data.pipeline import persist_audited_dataset


SOURCE_NAME = "OKX_V5_HISTORY_CANDLES"
DEFAULT_INTERVALS = ("5", "15", "60", "240", "D")
DEFAULT_SYMBOLS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP")


def iso_utc(ms: int | None) -> str:
    if ms is None:
        return "n/a"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download, audit and fingerprint public OKX multi-timeframe historical candles."
    )
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument(
        "--intervals",
        nargs="+",
        default=list(DEFAULT_INTERVALS),
        help="Canonical repo intervals. Default: 5 15 60 240 D (OKX D maps to 1Dutc).",
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default=os.getenv("OKX_BASE_URL", "https://www.okx.com"))
    parser.add_argument("--output-root", default="data/history")
    args = parser.parse_args()

    if args.days <= 0:
        parser.error("--days must be positive")

    client = OKXPublicClient(base_url=args.base_url)
    try:
        end_ms = client.get_server_time_ms()
        interval_ms_map = {interval: client.interval_ms(interval) for interval in args.intervals}
    except (OKXAPIError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    requested_start_ms = end_ms - args.days * 24 * 60 * 60 * 1000
    overall_ok = True

    for raw_symbol in args.symbols:
        symbol = raw_symbol.upper()
        try:
            info = client.get_instrument_info(symbol)
            if info.status.lower() != "live":
                raise OKXAPIError(f"{symbol} is not in OKX live state: {info.status}")
            if not info.is_usdt_linear_perpetual:
                raise OKXAPIError(
                    f"{symbol} is not a USDT linear perpetual "
                    f"(contractType={info.contract_type!r}, quote={info.quote_coin!r}, settle={info.settle_coin!r})"
                )
        except (OKXAPIError, ValueError) as exc:
            print(f"\n[{symbol}] ERROR: {exc}")
            overall_ok = False
            continue

        symbol_start_ms = max(requested_start_ms, info.launch_time_ms or requested_start_ms)
        if symbol_start_ms > end_ms:
            print(f"\n[{symbol}] ERROR: launch time is after the requested end time")
            overall_ok = False
            continue

        print(f"\n[{symbol}] OKX state={info.status} launch={iso_utc(info.launch_time_ms)}")
        for interval in args.intervals:
            interval_ms = interval_ms_map[interval]
            print(f"  interval {interval}: downloading public closed candles...")
            try:
                fetch = client.fetch_klines(
                    symbol=symbol,
                    interval=interval,
                    start_ms=symbol_start_ms,
                    end_ms=end_ms,
                    closed_only=True,
                )
                persisted = persist_audited_dataset(
                    fetch,
                    interval_ms=interval_ms,
                    output_root=args.output_root,
                    source=SOURCE_NAME,
                )
            except (OKXAPIError, ValueError, OSError) as exc:
                print(f"    ERROR: {exc}")
                overall_ok = False
                continue

            qa = persisted.qa
            coverage = persisted.coverage
            print(f"    candles:         {persisted.manifest.row_count}")
            print(f"    first UTC open:  {iso_utc(persisted.manifest.first_open_time_ms)}")
            print(f"    last UTC open:   {iso_utc(persisted.manifest.last_open_time_ms)}")
            print(f"    coverage:        {coverage.completeness_pct:.4f}% ({coverage.coverage_status})")
            print(f"    QA healthy:      {qa.is_healthy}")
            print(f"    dataset_id:      {persisted.manifest.dataset_id}")
            print(f"    content_sha256:  {persisted.manifest.content_sha256}")
            print(f"    CSV:             {persisted.csv_path}")
            print(f"    manifest:        {persisted.manifest_path}")
            if coverage.missing_count:
                print(
                    "    missing slots:    "
                    f"total={coverage.missing_count} leading={coverage.leading_missing_count} "
                    f"internal={coverage.internal_missing_count} trailing={coverage.trailing_missing_count}"
                )
            if not persisted.is_healthy:
                overall_ok = False
                print("    RESULT: REVIEW REQUIRED — dataset must not enter deterministic replay")
            else:
                print("    RESULT: OK — dataset is eligible for deterministic replay input")

    return 0 if overall_ok else 2


if __name__ == "__main__":
    sys.exit(main())
