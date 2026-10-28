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

    With ``interval_ms`` configured, a resumed feed paginates backwards from the
    latest page until it reaches the durable cursor and verifies that every
    expected closed bar is present. This avoids silently skipping candles after
    a long process outage.
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
        interval_ms: int | None = None,
        max_backfill_pages: int = 10_000,
    ) -> None:
        if page_limit <= 0:
            raise ValueError("page_limit must be positive")
        if interval_ms is not None and interval_ms <= 0:
            raise ValueError("interval_ms must be positive when supplied")
        if max_backfill_pages <= 0:
            raise ValueError("max_backfill_pages must be positive")
        self.client = client
        self.key = FeedKey(exchange=exchange, symbol=symbol, interval=interval)
        self.cursor = cursor
        self.page_limit = page_limit
        self.interval_ms = interval_ms
        self.max_backfill_pages = max_backfill_pages

    def _page(self, *, after_ms: int | None = None) -> tuple[MarketCandle, ...]:
        page = self.client.get_kline_page(
            symbol=self.key.symbol,
            interval=self.key.interval,
            after_ms=after_ms,
            limit=self.page_limit,
            closed_only=True,
        )
        return tuple(
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

    @staticmethod
    def _merge_candles(
        target: dict[int, MarketCandle],
        rows: tuple[MarketCandle, ...],
    ) -> None:
        for candle in rows:
            previous = target.get(candle.open_time_ms)
            if previous is not None and previous != candle:
                raise ValueError("conflicting closed candle across polling pages")
            target[candle.open_time_ms] = candle

    def poll(self) -> PollBatch:
        current = self.cursor.get(self.key)
        latest = self._page()

        if current is None:
            if latest:
                self.cursor.commit(self.key, latest[-1].open_time_ms)
            return PollBatch(
                key=self.key,
                candles=(),
                bootstrapped=True,
                cursor_before=None,
            )

        by_open: dict[int, MarketCandle] = {}
        self._merge_candles(by_open, latest)

        if self.interval_ms is not None and latest:
            earliest = latest[0].open_time_ms
            pages = 1
            while earliest > current + self.interval_ms:
                if pages >= self.max_backfill_pages:
                    raise ValueError("max_backfill_pages reached before durable cursor")
                older = self._page(after_ms=earliest)
                pages += 1
                if not older:
                    break
                older_earliest = older[0].open_time_ms
                if older_earliest >= earliest:
                    raise ValueError("poll pagination did not move backwards")
                self._merge_candles(by_open, older)
                earliest = older_earliest

        pending = tuple(
            by_open[key]
            for key in sorted(by_open)
            if key > current
        )

        if self.interval_ms is not None and pending:
            expected = current + self.interval_ms
            for candle in pending:
                if candle.open_time_ms != expected:
                    raise ValueError(
                        "closed-candle catch-up gap detected: "
                        f"expected {expected}, got {candle.open_time_ms}"
                    )
                expected += self.interval_ms

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
