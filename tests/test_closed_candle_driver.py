import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.live_feed import ClosedCandlePollFeed, DurableCandleCursor
from crypto_bot.data.models import MarketCandle
from crypto_bot.runtime.closed_candle_driver import ClosedCandleRuntimeDriver


def candle(ts: int) -> MarketCandle:
    return MarketCandle(
        exchange="OKX",
        symbol="BTC-USDT-SWAP",
        interval="1",
        open_time_ms=ts,
        open=100.0,
        high=102.0,
        low=99.0,
        close=101.0,
        volume_base=1.0,
        turnover_quote=100.0,
        is_closed=True,
    )


class Page:
    def __init__(self, rows):
        self.candles = tuple(rows)


class FakeClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = 0

    def get_kline_page(self, **kwargs):
        index = min(self.calls, len(self.pages) - 1)
        self.calls += 1
        return Page(self.pages[index])


class FakeRuntime:
    def __init__(self, fail_on_call=None):
        self.calls = []
        self.fail_on_call = fail_on_call

    def observe_candles(self, candles, *, decision_at):
        next_index = len(self.calls) + 1
        if self.fail_on_call == next_index:
            raise RuntimeError("injected runtime failure")
        self.calls.append((tuple(candles), decision_at))


class ClosedCandleDriverTests(unittest.TestCase):
    def make_feed(self, tmp, pages):
        return ClosedCandlePollFeed(
            client=FakeClient(pages),
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="1",
            cursor=DurableCandleCursor(Path(tmp) / "cursor.json"),
        )

    def test_bootstrap_does_not_advance_runtime_with_old_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = FakeRuntime()
            feed = self.make_feed(tmp, [[candle(60_000), candle(120_000)]])
            result = ClosedCandleRuntimeDriver(feed=feed, runtime=runtime, interval_ms=60_000).run_once()
            self.assertTrue(result.bootstrapped)
            self.assertEqual(result.processed_count, 0)
            self.assertEqual(runtime.calls, [])
            self.assertEqual(feed.cursor.get(feed.key), 120_000)

    def test_new_candle_is_observed_then_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = FakeRuntime()
            feed = self.make_feed(tmp, [[candle(60_000)], [candle(60_000), candle(120_000)]])
            driver = ClosedCandleRuntimeDriver(feed=feed, runtime=runtime, interval_ms=60_000)
            driver.run_once()
            result = driver.run_once()
            self.assertEqual(result.processed_count, 1)
            self.assertEqual(len(runtime.calls), 1)
            self.assertEqual(feed.cursor.get(feed.key), 120_000)
            self.assertEqual(runtime.calls[0][0][0].close_time, result.last_decision_at)

    def test_runtime_failure_does_not_commit_failed_candle(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed = self.make_feed(tmp, [[candle(60_000)], [candle(60_000), candle(120_000)]])
            bootstrap_runtime = FakeRuntime()
            bootstrap = ClosedCandleRuntimeDriver(feed=feed, runtime=bootstrap_runtime, interval_ms=60_000)
            bootstrap.run_once()

            failing = ClosedCandleRuntimeDriver(feed=feed, runtime=FakeRuntime(fail_on_call=1), interval_ms=60_000)
            with self.assertRaises(RuntimeError):
                failing.run_once()
            self.assertEqual(feed.cursor.get(feed.key), 60_000)

            # A restarted runtime sees the same uncommitted candle again.
            feed.client = FakeClient([[candle(60_000), candle(120_000)]])
            recovered_runtime = FakeRuntime()
            recovered = ClosedCandleRuntimeDriver(feed=feed, runtime=recovered_runtime, interval_ms=60_000)
            result = recovered.run_once()
            self.assertEqual(result.processed_count, 1)
            self.assertEqual(feed.cursor.get(feed.key), 120_000)

    def test_multiple_pending_candles_commit_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = FakeRuntime()
            feed = self.make_feed(tmp, [
                [candle(60_000)],
                [candle(60_000), candle(120_000), candle(180_000)],
            ])
            driver = ClosedCandleRuntimeDriver(feed=feed, runtime=runtime, interval_ms=60_000)
            driver.run_once()
            result = driver.run_once()
            self.assertEqual(result.processed_count, 2)
            self.assertEqual(feed.cursor.get(feed.key), 180_000)
            self.assertEqual(len(runtime.calls), 2)


if __name__ == "__main__":
    unittest.main()
