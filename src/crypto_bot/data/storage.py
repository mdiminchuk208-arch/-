from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from crypto_bot.data.models import MarketCandle


CSV_FIELDS = [
    "exchange",
    "symbol",
    "interval",
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume_base",
    "turnover_quote",
    "is_closed",
]


def write_klines_csv(candles: Iterable[MarketCandle], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(candles, key=lambda candle: candle.open_time_ms)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for c in rows:
            writer.writerow(
                {
                    "exchange": c.exchange,
                    "symbol": c.symbol,
                    "interval": c.interval,
                    "open_time_ms": c.open_time_ms,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume_base": "" if c.volume_base is None else c.volume_base,
                    "turnover_quote": "" if c.turnover_quote is None else c.turnover_quote,
                    "is_closed": "1" if c.is_closed else "0",
                }
            )
    return destination


def read_klines_csv(path: str | Path) -> list[MarketCandle]:
    source = Path(path)
    out: list[MarketCandle] = []
    with source.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            out.append(
                MarketCandle(
                    exchange=row["exchange"],
                    symbol=row["symbol"],
                    interval=row["interval"],
                    open_time_ms=int(row["open_time_ms"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume_base=float(row["volume_base"]) if row["volume_base"] else None,
                    turnover_quote=float(row["turnover_quote"]) if row["turnover_quote"] else None,
                    is_closed=row["is_closed"] == "1",
                )
            )
    return out
