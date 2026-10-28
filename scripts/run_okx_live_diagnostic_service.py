from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from crypto_bot.data.live_feed import ClosedCandlePollFeed, DurableCandleCursor
from crypto_bot.data.okx import OKX_MAINNET, OKXAPIError, OKXPublicClient
from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.runtime.bootstrap import bootstrap_live_mtf_from_verified_datasets
from crypto_bot.runtime.health import RuntimeHealthPolicy
from crypto_bot.runtime.health_store import write_runtime_health_file
from crypto_bot.runtime.live_diagnostic import LivePureSourceDiagnosticRunner
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer, MtfSeriesSpec, SQLiteMtfCandleStore
from crypto_bot.runtime.service import LiveDiagnosticService


DEFAULT_INTERVALS = ("5", "15", "60", "240", "D")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _print_event(kind: str, payload: Any) -> None:
    body = {
        "kind": kind,
        "payload": _jsonable(
            asdict(payload) if hasattr(payload, "__dataclass_fields__") else payload
        ),
    }
    print(json.dumps(body, sort_keys=True, ensure_ascii=False), flush=True)


def _dataset_paths(
    data_root: Path,
    symbol: str,
    intervals: list[str],
) -> tuple[tuple[Path, Path], ...]:
    result: list[tuple[Path, Path]] = []
    for interval in intervals:
        csv_path = data_root / "okx" / symbol / f"{interval}.csv"
        manifest_path = csv_path.with_suffix(".manifest.json")
        if not csv_path.exists() or not manifest_path.exists():
            raise FileNotFoundError(
                f"missing verified bootstrap dataset for {symbol} {interval}: "
                f"{csv_path} / {manifest_path}"
            )
        result.append((csv_path, manifest_path))
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the fail-closed OKX public-data PURE SOURCE diagnostic service. "
            "This process has no private exchange API and cannot place orders."
        )
    )
    parser.add_argument("--symbol", default="BTC-USDT-SWAP")
    parser.add_argument("--intervals", nargs="+", default=list(DEFAULT_INTERVALS))
    parser.add_argument("--data-root", default="data/history")
    parser.add_argument("--state-root", default="data/runtime")
    parser.add_argument("--health-file", default=None)
    parser.add_argument("--base-url", default=OKX_MAINNET)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument(
        "--stale-intervals",
        type=float,
        default=3.0,
        help="Operational health threshold as a multiple of each candle interval.",
    )
    parser.add_argument("--max-pending-outbox", type=int, default=5000)
    parser.add_argument("--page-limit", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be positive")
    if args.stale_intervals <= 0:
        parser.error("--stale-intervals must be positive")
    if args.max_pending_outbox < 0:
        parser.error("--max-pending-outbox cannot be negative")
    if not 1 <= args.page_limit <= 300:
        parser.error("--page-limit must be within [1, 300]")

    symbol = args.symbol.upper()
    client = OKXPublicClient(base_url=args.base_url)
    try:
        specs = tuple(
            MtfSeriesSpec(interval, client.interval_ms(interval), min_bars=1)
            for interval in args.intervals
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    symbol_state = Path(args.state_root) / "okx" / symbol
    symbol_state.mkdir(parents=True, exist_ok=True)
    health_path = Path(args.health_file) if args.health_file else symbol_state / "health.json"

    buffer = LiveMtfBuffer(
        exchange="OKX",
        symbol=symbol,
        specs=specs,
        store=SQLiteMtfCandleStore(symbol_state / "mtf.sqlite3"),
    )

    try:
        bootstrap = bootstrap_live_mtf_from_verified_datasets(
            buffer,
            _dataset_paths(Path(args.data_root), symbol, list(args.intervals)),
        )
    except (ValueError, OSError) as exc:
        print(f"ERROR: bootstrap failed: {exc}", file=sys.stderr)
        return 2
    _print_event("bootstrap", bootstrap)

    cursor = DurableCandleCursor(symbol_state / "cursors.json")
    feeds = {
        spec.timeframe: ClosedCandlePollFeed(
            client=client,
            exchange="OKX",
            symbol=symbol,
            interval=spec.timeframe,
            interval_ms=spec.interval_ms,
            cursor=cursor,
            page_limit=args.page_limit,
        )
        for spec in specs
    }
    outbox = SQLiteEngineOutbox(symbol_state / "engine_outbox.sqlite3")
    diagnostic = LivePureSourceDiagnosticRunner(buffer=buffer, outbox=outbox)
    stale_after = {
        spec.timeframe: max(120, int(spec.interval_ms / 1000 * args.stale_intervals))
        for spec in specs
    }
    health_policy = RuntimeHealthPolicy(
        stale_after_seconds=stale_after,
        max_pending_outbox=args.max_pending_outbox,
    )
    service = LiveDiagnosticService(
        buffer=buffer,
        feeds=feeds,
        diagnostic_runner=diagnostic,
        health_policy=health_policy,
    )

    while True:
        try:
            observed_at = datetime.fromtimestamp(
                client.get_server_time_ms() / 1000,
                tz=timezone.utc,
            )
            cycle = service.run_cycle(observed_at=observed_at)
            write_runtime_health_file(cycle.health, health_path)
        except (OKXAPIError, ValueError, OSError) as exc:
            print(
                json.dumps(
                    {
                        "kind": "fatal_cycle_error",
                        "error": str(exc),
                        "health_file": str(health_path),
                        "trade_entry_allowed": False,
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                file=sys.stderr,
                flush=True,
            )
            # Do not overwrite the last successful health receipt. Its age will
            # exceed the external health-check threshold and fail naturally.
            return 2

        _print_event("cycle", cycle)
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
