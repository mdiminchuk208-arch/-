from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from crypto_bot.common.models import Candle
from crypto_bot.data.models import MarketCandle


TECHNICAL_NORMALIZATION_ID = "TN_MARKET_CANDLE_TO_CANONICAL_UTC_V1"


def to_canonical_candle(candle: MarketCandle, *, interval_ms: int) -> Candle:
    """Convert exchange-normalized market data to the Strategy Engine candle.

    This function performs timestamp/shape normalization only. It does not
    detect structure, infer SOURCE objects or change trade eligibility.
    """
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")
    if not candle.is_closed:
        raise ValueError("canonical Strategy Engine candles must be closed")
    if candle.open_time_ms % interval_ms != 0:
        raise ValueError("market candle open time is not aligned to interval")

    open_time = datetime.fromtimestamp(candle.open_time_ms / 1000, tz=timezone.utc)
    close_time = open_time + timedelta(milliseconds=interval_ms)
    return Candle(
        open_time=open_time,
        close_time=close_time,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        is_closed=True,
    )


def to_canonical_series(
    candles: Iterable[MarketCandle],
    *,
    interval_ms: int,
    require_contiguous: bool = True,
) -> tuple[Candle, ...]:
    rows = sorted(candles, key=lambda item: item.open_time_ms)
    if not rows:
        return ()

    identity = (rows[0].exchange, rows[0].symbol, rows[0].interval)
    previous_open: int | None = None
    seen: set[int] = set()
    output: list[Candle] = []
    for row in rows:
        if (row.exchange, row.symbol, row.interval) != identity:
            raise ValueError("canonical series cannot mix exchange/symbol/interval identities")
        if row.open_time_ms in seen:
            raise ValueError("canonical series cannot contain duplicate open times")
        if previous_open is not None and require_contiguous and row.open_time_ms != previous_open + interval_ms:
            raise ValueError("canonical series must be contiguous")
        output.append(to_canonical_candle(row, interval_ms=interval_ms))
        seen.add(row.open_time_ms)
        previous_open = row.open_time_ms
    return tuple(output)
