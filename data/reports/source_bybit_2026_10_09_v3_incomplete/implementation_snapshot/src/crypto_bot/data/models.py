from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Iterable

from crypto_bot.common.models import Candle


@dataclass(frozen=True)
class MarketCandle:
    exchange: str
    symbol: str
    interval: str
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume_base: float | None = None
    turnover_quote: float | None = None
    is_closed: bool = True

    def __post_init__(self) -> None:
        if self.open_time_ms < 0:
            raise ValueError("open_time_ms must be non-negative")
        if not all(isfinite(v) for v in (self.open, self.high, self.low, self.close)):
            raise ValueError("OHLC values must be finite")
        if self.low > self.high:
            raise ValueError("low cannot exceed high")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open must be within [low, high]")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close must be within [low, high]")
        if self.volume_base is not None and (not isfinite(self.volume_base) or self.volume_base < 0):
            raise ValueError("volume_base must be finite and non-negative")
        if self.turnover_quote is not None and (not isfinite(self.turnover_quote) or self.turnover_quote < 0):
            raise ValueError("turnover_quote must be finite and non-negative")

    def to_strategy_candle(self, interval_ms: int) -> Candle:
        open_time = datetime.fromtimestamp(self.open_time_ms / 1000, tz=timezone.utc)
        close_time = datetime.fromtimestamp((self.open_time_ms + interval_ms) / 1000, tz=timezone.utc)
        return Candle(
            open_time=open_time,
            close_time=close_time,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            is_closed=self.is_closed,
        )


@dataclass(frozen=True)
class InstrumentInfo:
    exchange: str
    symbol: str
    contract_type: str
    symbol_type: str
    market_region: str
    base_coin: str
    quote_coin: str
    settle_coin: str
    status: str
    launch_time_ms: int | None
    delivery_time_ms: int | None
    tick_size: float | None
    qty_step: float | None
    min_order_qty: float | None
    max_order_qty: float | None
    max_market_order_qty: float | None
    min_notional_value: float | None
    funding_interval_min: int | None
    max_leverage: float | None

    @property
    def is_usdt_linear_perpetual(self) -> bool:
        # Bybit documents marketRegion as TradFi-specific and symbolType as a region/type
        # classifier. Requiring both to be empty is intentionally conservative for this
        # crypto-only project; a future new crypto symbolType must be reviewed explicitly.
        return (
            self.contract_type == "LinearPerpetual"
            and self.symbol_type == ""
            and self.market_region == ""
            and self.quote_coin == "USDT"
            and self.settle_coin == "USDT"
        )


@dataclass(frozen=True)
class HistoricalFetch:
    exchange: str
    symbol: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    server_time_ms: int
    candles: tuple[MarketCandle, ...]

    @classmethod
    def from_iterable(
        cls,
        *,
        exchange: str,
        symbol: str,
        interval: str,
        requested_start_ms: int,
        requested_end_ms: int,
        server_time_ms: int,
        candles: Iterable[MarketCandle],
    ) -> "HistoricalFetch":
        return cls(
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            requested_start_ms=requested_start_ms,
            requested_end_ms=requested_end_ms,
            server_time_ms=server_time_ms,
            candles=tuple(candles),
        )
