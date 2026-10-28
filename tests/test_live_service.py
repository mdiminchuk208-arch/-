import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from crypto_bot.data.live_feed import ClosedCandlePollFeed, DurableCandleCursor
from crypto_bot.data.models import MarketCandle
from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.runtime.health import RuntimeHealthPolicy, RuntimeHealthState
from crypto_bot.runtime.live_diagnostic import LivePureSourceDiagnosticRunner
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer, MtfSeriesSpec, SQLiteMtfCandleStore
from crypto_bot.runtime.service import LiveDiagnosticService


UTC = timezone.utc


def candle(ts: int, *, interval: str) -> MarketCandle:
    return MarketCandle(
        exchange="OKX",
        symbol="BTC-USDT-SWAP",
        interval=interval,
        open_time_ms=ts,
        open=100.0,
        high=102.0,
        low=99.0,
        close=101.0,
        volume_base=1.0,
        turnover_quote=100.0,
        is_closed=True,
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


class LiveServiceTests(unittest.TestCase):
    def make(self, tmp, *, seed_5=(0,), seed_15=(0,), cursor=None, pages_5=None, pages_15=None):
        buffer = LiveMtfBuffer(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            specs=(
                MtfSeriesSpec("5", 300_000, min_bars=1),
                MtfSeriesSpec("15", 900_000, min_bars=1),
            ),
            store=SQLiteMtfCandleStore(Path(tmp) / "mtf.sqlite3"),
        )
        for ts in seed_5:
            buffer.ingest(candle(ts, interval="5"))
        for ts in seed_15:
            buffer.ingest(candle(ts, interval="15"))

        cursor = cursor or DurableCandleCursor(Path(tmp) / "cursor.json")
        feed5 = ClosedCandlePollFeed(
            client=FakeClient(pages_5 or [[candle(0, interval="5"), candle(300_000, interval="5")]]),
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="5",
            interval_ms=300_000,
            cursor=cursor,
        )
        feed15 = ClosedCandlePollFeed(
            client=FakeClient(pages_15 or [[candle(0, interval="15")]]),
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="15",
            interval_ms=900_000,
            cursor=cursor,
        )
        outbox = SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3")
        diagnostic = LivePureSourceDiagnosticRunner(buffer=buffer, outbox=outbox)
        health_policy = RuntimeHealthPolicy(
            stale_after_seconds={"5": 600, "15": 1_800},
            max_pending_outbox=10,
        )
        service = LiveDiagnosticService(
            buffer=buffer,
            feeds={"5": feed5, "15": feed15},
            diagnostic_runner=diagnostic,
            health_policy=health_policy,
        )
        return buffer, cursor, outbox, service

    def test_cycle_reconciles_empty_cursor_to_verified_buffer_then_catches_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, cursor, outbox, service = self.make(tmp)
            result = service.run_cycle(observed_at=datetime.fromtimestamp(900, tz=UTC))
            self.assertEqual(result.inserted_candles, 1)
            self.assertEqual(result.duplicate_candles, 0)
            self.assertIsNotNone(result.diagnostic)
            self.assertFalse(result.trade_entry_allowed)
            self.assertEqual(result.health.state, RuntimeHealthState.HEALTHY_DIAGNOSTIC)
            self.assertEqual([row.open_time_ms for row in buffer.replay_series()[0].candles], [0, 300_000])
            self.assertEqual(cursor.get(service.feeds["5"].key), 300_000)
            self.assertEqual(cursor.get(service.feeds["15"].key), 0)
            self.assertEqual(len(outbox.pending()), 1)

    def test_second_unchanged_cycle_does_not_recompute_or_duplicate_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, outbox, service = self.make(tmp)
            first = service.run_cycle(observed_at=datetime.fromtimestamp(900, tz=UTC))
            second = service.run_cycle(observed_at=datetime.fromtimestamp(901, tz=UTC))
            self.assertIsNotNone(first.diagnostic)
            self.assertIsNone(second.diagnostic)
            self.assertEqual(second.inserted_candles, 0)
            self.assertEqual(len(outbox.pending()), 1)

    def test_cursor_lag_replays_exact_stored_candle_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            buffer, _, _, service = self.make(
                tmp,
                seed_5=(0, 300_000),
                seed_15=(0,),
                cursor=cursor,
                pages_5=[[candle(0, interval="5"), candle(300_000, interval="5")]],
            )
            cursor.commit(service.feeds["5"].key, 0)
            cursor.commit(service.feeds["15"].key, 0)
            result = service.run_cycle(observed_at=datetime.fromtimestamp(900, tz=UTC))
            self.assertEqual(result.inserted_candles, 0)
            self.assertEqual(result.duplicate_candles, 1)
            self.assertEqual(cursor.get(service.feeds["5"].key), 300_000)
            self.assertEqual(len(buffer.replay_series()[0].candles), 2)

    def test_cursor_ahead_of_durable_mtf_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            _, _, _, service = self.make(tmp, cursor=cursor)
            cursor.commit(service.feeds["5"].key, 600_000)
            with self.assertRaisesRegex(ValueError, "ahead of live MTF state"):
                service.run_cycle(observed_at=datetime.fromtimestamp(900, tz=UTC))

    def test_service_requires_exact_feed_and_interval_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer = LiveMtfBuffer(
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                specs=(MtfSeriesSpec("5", 300_000),),
                store=SQLiteMtfCandleStore(Path(tmp) / "mtf.sqlite3"),
            )
            cursor = DurableCandleCursor(Path(tmp) / "cursor.json")
            bad_feed = ClosedCandlePollFeed(
                client=FakeClient([[]]),
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                interval="5",
                interval_ms=60_000,
                cursor=cursor,
            )
            diagnostic = LivePureSourceDiagnosticRunner(
                buffer=buffer,
                outbox=SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3"),
            )
            policy = RuntimeHealthPolicy(stale_after_seconds={"5": 600}, max_pending_outbox=10)
            with self.assertRaisesRegex(ValueError, "interval_ms"):
                LiveDiagnosticService(
                    buffer=buffer,
                    feeds={"5": bad_feed},
                    diagnostic_runner=diagnostic,
                    health_policy=policy,
                )


if __name__ == "__main__":
    unittest.main()
