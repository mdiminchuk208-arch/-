import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from crypto_bot.data.live_feed import ClosedCandlePollFeed, DurableCandleCursor, FeedKey
from crypto_bot.data.models import MarketCandle


def candle(ts: int, *, closed: bool = True) -> MarketCandle:
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
        is_closed=closed,
    )


@dataclass(frozen=True)
class Page:
    candles: tuple[MarketCandle, ...]


class FakeClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = 0

    def get_kline_page(self, **kwargs):
        index = min(self.calls, len(self.pages) - 1)
        self.calls += 1
        return Page(tuple(self.pages[index]))


class LiveFeedTests(unittest.TestCase):
    def test_first_poll_baselines_latest_closed_candle_without_emitting_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            feed = ClosedCandlePollFeed(
                client=FakeClient([[candle(60_000), candle(120_000)]]),
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="1",
                cursor=cursor,
            )
            batch = feed.poll()
            self.assertTrue(batch.bootstrapped)
            self.assertEqual(batch.candles, ())
            self.assertEqual(cursor.get(feed.key), 120_000)

    def test_next_poll_returns_only_new_closed_candles_and_requires_explicit_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            client = FakeClient([
                [candle(60_000), candle(120_000)],
                [candle(120_000), candle(180_000), candle(240_000)],
            ])
            feed = ClosedCandlePollFeed(
                client=client,
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="1",
                cursor=cursor,
            )
            feed.poll()
            batch = feed.poll()
            self.assertEqual([c.open_time_ms for c in batch.candles], [180_000, 240_000])
            self.assertEqual(cursor.get(feed.key), 120_000)
            feed.commit(batch.candles[0])
            self.assertEqual(cursor.get(feed.key), 180_000)
            feed.commit(batch.candles[1])
            self.assertEqual(cursor.get(feed.key), 240_000)

    def test_uncommitted_candle_is_replayed_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cursor.json"
            first_cursor = DurableCandleCursor(path)
            first_feed = ClosedCandlePollFeed(
                client=FakeClient([[candle(60_000)]]),
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="1",
                cursor=first_cursor,
            )
            first_feed.poll()

            # Process sees 120k but crashes before commit.
            first_feed.client = FakeClient([[candle(60_000), candle(120_000)]])
            batch = first_feed.poll()
            self.assertEqual([c.open_time_ms for c in batch.candles], [120_000])

            restarted = ClosedCandlePollFeed(
                client=FakeClient([[candle(60_000), candle(120_000)]]),
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="1",
                cursor=DurableCandleCursor(path),
            )
            replayed = restarted.poll()
            self.assertEqual([c.open_time_ms for c in replayed.candles], [120_000])

    def test_committed_cursor_survives_restart_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cursor.json"
            cursor = DurableCandleCursor(path)
            key = FeedKey("OKX", "BTC-USDT-SWAP", "1")
            cursor.commit(key, 120_000)
            cursor.commit(key, 120_000)
            restored = DurableCandleCursor(path)
            self.assertEqual(restored.get(key), 120_000)
            with self.assertRaises(ValueError):
                restored.commit(key, 60_000)

    def test_identity_and_closed_state_are_enforced_on_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            feed = ClosedCandlePollFeed(
                client=FakeClient([[]]),
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="1",
                cursor=cursor,
            )
            with self.assertRaises(ValueError):
                feed.commit(candle(60_000, closed=False))
            wrong = MarketCandle(
                exchange="OKX",
                symbol="ETH-USDT-SWAP",
                interval="1",
                open_time_ms=60_000,
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume_base=1.0,
                turnover_quote=100.0,
                is_closed=True,
            )
            with self.assertRaises(ValueError):
                feed.commit(wrong)

    def test_poll_ignores_unfinished_or_mismatched_rows(self):
        mismatched = MarketCandle(
            exchange="OKX",
            symbol="ETH-USDT-SWAP",
            interval="1",
            open_time_ms=180_000,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume_base=1.0,
            turnover_quote=100.0,
            is_closed=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            key = FeedKey("OKX", "BTC-USDT-SWAP", "1")
            cursor.commit(key, 60_000)
            feed = ClosedCandlePollFeed(
                client=FakeClient([[candle(120_000, closed=False), mismatched, candle(240_000)]]),
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="1",
                cursor=cursor,
            )
            batch = feed.poll()
            self.assertEqual([c.open_time_ms for c in batch.candles], [240_000])


if __name__ == "__main__":
    unittest.main()
