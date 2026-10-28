from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from crypto_bot.data.models import MarketCandle


LIVE_CURSOR_SCHEMA = "crypto-bot.live-candle-cursor.v1"


class ClosedCandleClient(Protocol):
    def get_kline_page(
        self,
        *,
        symbol: str,
        interval: str,
        after_ms: int | None = None,
        before_ms: int | None = None,
        limit: int = 300,
        closed_only: bool = True,
    ): ...


@dataclass(frozen=True)
class FeedKey:
    exchange: str
    symbol: str
    interval: str

    @property
    def storage_key(self) -> str:
        return f"{self.exchange.upper()}|{self.symbol.upper()}|{self.interval}"


@dataclass(frozen=True)
class PollBatch:
    key: FeedKey
    candles: tuple[MarketCandle, ...]
    bootstrapped: bool
    cursor_before: int | None


class DurableCandleCursor:
    """Small atomic JSON cursor store for public closed-candle feeds."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._values = self._load()

    def _load(self) -> dict[str, int]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema") != LIVE_CURSOR_SCHEMA:
            raise ValueError(f"unsupported live cursor schema: {payload.get('schema')!r}")
        values = payload.get("cursors")
        if not isinstance(values, dict):
            raise ValueError("live cursor file must contain an object named cursors")
        parsed: dict[str, int] = {}
        for key, value in values.items():
            timestamp = int(value)
            if timestamp < 0:
                raise ValueError("live cursor timestamps cannot be negative")
            parsed[str(key)] = timestamp
        return parsed

    def get(self, key: FeedKey) -> int | None:
        return self._values.get(key.storage_key)

    def commit(self, key: FeedKey, open_time_ms: int) -> None:
        open_time_ms = int(open_time_ms)
        if open_time_ms < 0:
            raise ValueError("open_time_ms cannot be negative")
        current = self.get(key)
        if current is not None and open_time_ms < current:
            raise ValueError("cursor cannot move backwards")
        if current == open_time_ms:
            return
        self._values[key.storage_key] = open_time_ms
        self._write_atomic()

    def _write_atomic(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": LIVE_CURSOR_SCHEMA,
            "cursors": dict(sorted(self._values.items())),
        }
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


class ClosedCandlePollFeed:
    """Fail-safe closed-candle polling feed with explicit commit semantics.

    The first observation is a *baseline*, not a historical signal. When no
    durable cursor exists, the feed records the newest closed candle and emits
    nothing. This prevents process startup from reinterpreting old history as
    fresh live information.

    On subsequent polls, returned candles are not committed automatically.
    Call ``commit`` only after downstream processing succeeds. That lets a
    restart replay an uncommitted candle instead of losing it.
    """

    def __init__(
        self,
        *,
        client: ClosedCandleClient,
        exchange: str,
        symbol: str,
        interval: str,
        cursor: DurableCandleCursor,
        page_limit: int = 50,
    ) -> None:
        if page_limit <= 0:
            raise ValueError("page_limit must be positive")
        self.client = client
        self.key = FeedKey(exchange=exchange, symbol=symbol, interval=interval)
        self.cursor = cursor
        self.page_limit = page_limit

    def poll(self) -> PollBatch:
        current = self.cursor.get(self.key)
        page = self.client.get_kline_page(
            symbol=self.key.symbol,
            interval=self.key.interval,
            limit=self.page_limit,
            closed_only=True,
        )
        candles = tuple(
            sorted(
                (
                    candle
                    for candle in page.candles
                    if candle.exchange.upper() == self.key.exchange.upper()
                    and candle.symbol.upper() == self.key.symbol.upper()
                    and candle.interval == self.key.interval
                    and candle.is_closed
                ),
                key=lambda candle: candle.open_time_ms,
            )
        )

        if current is None:
            if candles:
                self.cursor.commit(self.key, candles[-1].open_time_ms)
            return PollBatch(
                key=self.key,
                candles=(),
                bootstrapped=True,
                cursor_before=None,
            )

        pending = tuple(candle for candle in candles if candle.open_time_ms > current)
        return PollBatch(
            key=self.key,
            candles=pending,
            bootstrapped=False,
            cursor_before=current,
        )

    def commit(self, candle: MarketCandle) -> None:
        if candle.exchange.upper() != self.key.exchange.upper():
            raise ValueError("cannot commit candle from a different exchange")
        if candle.symbol.upper() != self.key.symbol.upper() or candle.interval != self.key.interval:
            raise ValueError("cannot commit candle from a different feed identity")
        if not candle.is_closed:
            raise ValueError("cannot commit an unfinished candle")
        current = self.cursor.get(self.key)
        if current is not None and candle.open_time_ms <= current:
            if candle.open_time_ms == current:
                return
            raise ValueError("cannot commit a candle older than the durable cursor")
        self.cursor.commit(self.key, candle.open_time_ms)
