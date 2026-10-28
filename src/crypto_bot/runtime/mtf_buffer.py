from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from crypto_bot.data.models import MarketCandle
from crypto_bot.strategy.pure_source_replay_v2 import ReplaySeries


@dataclass(frozen=True)
class MtfSeriesSpec:
    timeframe: str
    interval_ms: int
    min_bars: int = 1

    def __post_init__(self) -> None:
        if not self.timeframe:
            raise ValueError("timeframe must be non-empty")
        if self.interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        if self.min_bars <= 0:
            raise ValueError("min_bars must be positive")


@dataclass(frozen=True)
class MtfBufferStatus:
    exchange: str
    symbol: str
    ready: bool
    counts: tuple[tuple[str, int], ...]
    missing_timeframes: tuple[str, ...]


class SQLiteMtfCandleStore:
    """Durable idempotent closed-candle store for live/restart-safe MTF state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mtf_candles (
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    open_time_ms INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume_base REAL,
                    turnover_quote REAL,
                    is_closed INTEGER NOT NULL,
                    PRIMARY KEY(exchange, symbol, interval, open_time_ms)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mtf_series "
                "ON mtf_candles(exchange, symbol, interval, open_time_ms)"
            )

    @staticmethod
    def _row_tuple(candle: MarketCandle) -> tuple[object, ...]:
        return (
            candle.exchange.upper(),
            candle.symbol.upper(),
            candle.interval,
            candle.open_time_ms,
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume_base,
            candle.turnover_quote,
            1 if candle.is_closed else 0,
        )

    @staticmethod
    def _row_to_candle(row: sqlite3.Row) -> MarketCandle:
        return MarketCandle(
            exchange=row["exchange"],
            symbol=row["symbol"],
            interval=row["interval"],
            open_time_ms=int(row["open_time_ms"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume_base=(float(row["volume_base"]) if row["volume_base"] is not None else None),
            turnover_quote=(
                float(row["turnover_quote"]) if row["turnover_quote"] is not None else None
            ),
            is_closed=bool(row["is_closed"]),
        )

    def get(
        self,
        *,
        exchange: str,
        symbol: str,
        interval: str,
        open_time_ms: int,
    ) -> MarketCandle | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT exchange,symbol,interval,open_time_ms,open,high,low,close,
                       volume_base,turnover_quote,is_closed
                FROM mtf_candles
                WHERE exchange=? AND symbol=? AND interval=? AND open_time_ms=?
                """,
                (exchange.upper(), symbol.upper(), interval, int(open_time_ms)),
            ).fetchone()
        return self._row_to_candle(row) if row is not None else None

    def put(self, candle: MarketCandle) -> bool:
        if not candle.is_closed:
            raise ValueError("MTF store accepts closed candles only")
        existing = self.get(
            exchange=candle.exchange,
            symbol=candle.symbol,
            interval=candle.interval,
            open_time_ms=candle.open_time_ms,
        )
        if existing is not None:
            if existing != candle:
                raise ValueError(
                    "closed candle mutation detected for existing exchange/symbol/interval/open_time"
                )
            return False

        values = self._row_tuple(candle)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mtf_candles(
                    exchange,symbol,interval,open_time_ms,open,high,low,close,
                    volume_base,turnover_quote,is_closed
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                values,
            )
        return True

    def load_series(
        self,
        *,
        exchange: str,
        symbol: str,
        interval: str,
        limit: int | None = None,
    ) -> tuple[MarketCandle, ...]:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be positive when supplied")
        sql = (
            "SELECT exchange,symbol,interval,open_time_ms,open,high,low,close,"
            "volume_base,turnover_quote,is_closed FROM mtf_candles "
            "WHERE exchange=? AND symbol=? AND interval=? ORDER BY open_time_ms"
        )
        params: list[object] = [exchange.upper(), symbol.upper(), interval]
        if limit is not None:
            sql = (
                "SELECT * FROM ("
                "SELECT exchange,symbol,interval,open_time_ms,open,high,low,close,"
                "volume_base,turnover_quote,is_closed FROM mtf_candles "
                "WHERE exchange=? AND symbol=? AND interval=? "
                "ORDER BY open_time_ms DESC LIMIT ?"
                ") ORDER BY open_time_ms"
            )
            params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return tuple(self._row_to_candle(row) for row in rows)


class LiveMtfBuffer:
    """Strict MTF closed-candle accumulator with replay-compatible snapshots.

    The canonical path intentionally does not truncate old history. An arbitrary
    rolling lookback could alter SOURCE object discovery and would therefore be
    an unclassified strategy parameter. A future bounded horizon must be added
    only when its SOURCE/PROJECT classification is explicit.
    """

    def __init__(
        self,
        *,
        exchange: str,
        symbol: str,
        specs: Iterable[MtfSeriesSpec],
        store: SQLiteMtfCandleStore,
    ) -> None:
        self.exchange = exchange.upper()
        self.symbol = symbol.upper()
        self.store = store
        spec_rows = tuple(specs)
        if not spec_rows:
            raise ValueError("at least one MTF series spec is required")
        if len({row.timeframe for row in spec_rows}) != len(spec_rows):
            raise ValueError("duplicate MTF timeframe spec")
        self.specs = {row.timeframe: row for row in spec_rows}

    def ingest(self, candle: MarketCandle) -> bool:
        if candle.exchange.upper() != self.exchange or candle.symbol.upper() != self.symbol:
            raise ValueError("MTF candle identity does not match buffer identity")
        if not candle.is_closed:
            raise ValueError("live MTF buffer accepts closed candles only")
        try:
            spec = self.specs[candle.interval]
        except KeyError as exc:
            raise ValueError(f"unconfigured MTF interval: {candle.interval}") from exc
        if candle.open_time_ms % spec.interval_ms != 0:
            raise ValueError("MTF candle open time is not aligned to configured interval")

        exact = self.store.get(
            exchange=self.exchange,
            symbol=self.symbol,
            interval=candle.interval,
            open_time_ms=candle.open_time_ms,
        )
        if exact is not None:
            if exact != candle:
                raise ValueError(
                    "closed candle mutation detected for existing exchange/symbol/interval/open_time"
                )
            return False

        existing = self.store.load_series(
            exchange=self.exchange,
            symbol=self.symbol,
            interval=candle.interval,
            limit=1,
        )
        if existing:
            latest = existing[-1]
            if candle.open_time_ms < latest.open_time_ms:
                raise ValueError("out-of-order live MTF candle")
            if candle.open_time_ms > latest.open_time_ms + spec.interval_ms:
                raise ValueError("live MTF continuity gap detected")
        return self.store.put(candle)

    def status(self) -> MtfBufferStatus:
        counts: list[tuple[str, int]] = []
        missing: list[str] = []
        for timeframe, spec in sorted(self.specs.items(), key=lambda item: item[1].interval_ms):
            rows = self.store.load_series(
                exchange=self.exchange,
                symbol=self.symbol,
                interval=timeframe,
            )
            counts.append((timeframe, len(rows)))
            if len(rows) < spec.min_bars:
                missing.append(timeframe)
        return MtfBufferStatus(
            exchange=self.exchange,
            symbol=self.symbol,
            ready=not missing,
            counts=tuple(counts),
            missing_timeframes=tuple(missing),
        )

    def replay_series(self, *, require_ready: bool = True) -> tuple[ReplaySeries, ...]:
        status = self.status()
        if require_ready and not status.ready:
            raise ValueError(
                "MTF buffer is not ready: " + ",".join(status.missing_timeframes)
            )
        output: list[ReplaySeries] = []
        for timeframe, spec in sorted(self.specs.items(), key=lambda item: item[1].interval_ms):
            rows = self.store.load_series(
                exchange=self.exchange,
                symbol=self.symbol,
                interval=timeframe,
            )
            if not rows:
                continue
            previous = rows[0].open_time_ms
            for row in rows[1:]:
                if row.open_time_ms != previous + spec.interval_ms:
                    raise ValueError(f"stored MTF continuity gap in {timeframe}")
                previous = row.open_time_ms
            output.append(
                ReplaySeries(
                    timeframe=timeframe,
                    interval_ms=spec.interval_ms,
                    candles=rows,
                )
            )
        return tuple(output)
