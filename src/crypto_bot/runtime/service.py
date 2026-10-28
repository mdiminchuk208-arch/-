from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from crypto_bot.data.live_feed import ClosedCandlePollFeed
from crypto_bot.runtime.health import (
    RuntimeHealthPolicy,
    RuntimeHealthSnapshot,
    evaluate_runtime_health,
)
from crypto_bot.runtime.live_diagnostic import (
    LiveDiagnosticResult,
    LivePureSourceDiagnosticRunner,
)
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer


@dataclass(frozen=True)
class LiveServiceCycleResult:
    observed_at: str
    inserted_candles: int
    duplicate_candles: int
    bootstrapped_feeds: tuple[str, ...]
    diagnostic: LiveDiagnosticResult | None
    health: RuntimeHealthSnapshot
    trade_entry_allowed: bool


class LiveDiagnosticService:
    """One deterministic 24/7 service cycle for public-data diagnostics.

    Flow:
        cursor reconciliation -> poll/catch-up -> durable MTF ingest ->
        fail-closed PURE SOURCE diagnostic -> outbox -> health snapshot.

    The service never calls a private exchange endpoint and never grants
    financial execution permission.
    """

    def __init__(
        self,
        *,
        buffer: LiveMtfBuffer,
        feeds: Mapping[str, ClosedCandlePollFeed],
        diagnostic_runner: LivePureSourceDiagnosticRunner,
        health_policy: RuntimeHealthPolicy,
    ) -> None:
        self.buffer = buffer
        self.feeds = dict(feeds)
        self.diagnostic_runner = diagnostic_runner
        self.health_policy = health_policy
        self._first_cycle = True
        self._validate_contracts()

    def _validate_contracts(self) -> None:
        configured = set(self.buffer.specs)
        supplied = set(self.feeds)
        if supplied != configured:
            raise ValueError(
                "live feeds must exactly match MTF buffer timeframes "
                f"(missing={sorted(configured - supplied)}, extra={sorted(supplied - configured)})"
            )
        if self.diagnostic_runner.buffer is not self.buffer:
            raise ValueError("diagnostic runner must consume the same live MTF buffer")
        if set(self.health_policy.stale_after_seconds) != configured:
            raise ValueError("health policy must exactly match live MTF timeframes")

        for timeframe, spec in self.buffer.specs.items():
            feed = self.feeds[timeframe]
            if feed.key.exchange.upper() != self.buffer.exchange:
                raise ValueError(f"feed exchange mismatch for {timeframe}")
            if feed.key.symbol.upper() != self.buffer.symbol:
                raise ValueError(f"feed symbol mismatch for {timeframe}")
            if feed.key.interval != timeframe:
                raise ValueError(f"feed interval mismatch for {timeframe}")
            if feed.interval_ms != spec.interval_ms:
                raise ValueError(
                    f"feed {timeframe} must configure interval_ms={spec.interval_ms} for gap-safe catch-up"
                )

    def _reconcile_cursor(self, timeframe: str) -> None:
        feed = self.feeds[timeframe]
        rows = self.buffer.store.load_series(
            exchange=self.buffer.exchange,
            symbol=self.buffer.symbol,
            interval=timeframe,
            limit=1,
        )
        cursor_value = feed.cursor.get(feed.key)
        if not rows:
            if cursor_value is not None:
                raise ValueError(
                    f"durable cursor for {timeframe} exists but live MTF state is empty"
                )
            return

        latest_buffer = rows[-1].open_time_ms
        if cursor_value is None:
            # Verified/durable MTF state is the safe handoff point. Polling then
            # catches up every bar from here to the current exchange head.
            feed.cursor.commit(feed.key, latest_buffer)
            return
        if cursor_value > latest_buffer:
            raise ValueError(
                f"durable cursor for {timeframe} is ahead of live MTF state"
            )
        # cursor < latest_buffer is allowed. At-least-once catch-up will replay
        # exact stored candles idempotently before advancing the cursor.

    def run_cycle(self, *, observed_at: datetime) -> LiveServiceCycleResult:
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")

        inserted = 0
        duplicates = 0
        bootstrapped: list[str] = []

        for timeframe, spec in sorted(
            self.buffer.specs.items(), key=lambda item: item[1].interval_ms
        ):
            self._reconcile_cursor(timeframe)
            feed = self.feeds[timeframe]
            batch = feed.poll()
            if batch.bootstrapped:
                bootstrapped.append(timeframe)
            for candle in batch.candles:
                if self.buffer.ingest(candle):
                    inserted += 1
                else:
                    duplicates += 1
                # Commit only after durable MTF acceptance/idempotent match.
                feed.commit(candle)

        diagnostic: LiveDiagnosticResult | None = None
        status = self.buffer.status()
        if status.ready and (self._first_cycle or inserted > 0):
            diagnostic = self.diagnostic_runner.run_once()

        self._first_cycle = False
        health = evaluate_runtime_health(
            buffer=self.buffer,
            outbox=self.diagnostic_runner.outbox,
            policy=self.health_policy,
            observed_at=observed_at,
            diagnostic_pipeline_available=True,
        )
        return LiveServiceCycleResult(
            observed_at=observed_at.isoformat(),
            inserted_candles=inserted,
            duplicate_candles=duplicates,
            bootstrapped_feeds=tuple(bootstrapped),
            diagnostic=diagnostic,
            health=health,
            trade_entry_allowed=False,
        )
