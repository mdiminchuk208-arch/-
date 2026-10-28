from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from crypto_bot.common.models import Candle
from crypto_bot.data.bridge import to_canonical_candle
from crypto_bot.data.live_feed import ClosedCandlePollFeed


class CausalClockRuntime(Protocol):
    def observe_candles(self, candles: Sequence[Candle], *, decision_at: datetime) -> None: ...


@dataclass(frozen=True)
class DriverResult:
    bootstrapped: bool
    processed_count: int
    last_decision_at: datetime | None


class ClosedCandleRuntimeDriver:
    """Crash-safe bridge from a public closed-candle feed to a causal runtime.

    The driver commits a feed cursor only *after* the runtime accepts the
    corresponding canonical candle. It does not manufacture SOURCE evidence,
    setups or execution plans; it advances only the causal observation clock.
    """

    def __init__(
        self,
        *,
        feed: ClosedCandlePollFeed,
        runtime: CausalClockRuntime,
        interval_ms: int,
    ) -> None:
        if interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        self.feed = feed
        self.runtime = runtime
        self.interval_ms = interval_ms

    def run_once(self) -> DriverResult:
        batch = self.feed.poll()
        last_decision_at: datetime | None = None
        processed = 0

        for market_candle in batch.candles:
            canonical = to_canonical_candle(market_candle, interval_ms=self.interval_ms)
            self.runtime.observe_candles((canonical,), decision_at=canonical.close_time)
            # Commit only after downstream success. A crash/exception before this
            # point leaves the candle pending for the next process run.
            self.feed.commit(market_candle)
            processed += 1
            last_decision_at = canonical.close_time

        return DriverResult(
            bootstrapped=batch.bootstrapped,
            processed_count=processed,
            last_decision_at=last_decision_at,
        )
