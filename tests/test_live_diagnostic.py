import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.models import MarketCandle
from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.runtime.live_diagnostic import (
    LIVE_DIAGNOSTIC_EVENT_TYPE,
    LiveDiagnosticStatus,
    LivePureSourceDiagnosticRunner,
)
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer, MtfSeriesSpec, SQLiteMtfCandleStore


def candle(ts: int, *, interval: str, interval_ms: int) -> MarketCandle:
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


class LiveDiagnosticTests(unittest.TestCase):
    def make(self, tmp):
        buffer = LiveMtfBuffer(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            specs=(
                MtfSeriesSpec("5", 300_000, min_bars=1),
                MtfSeriesSpec("15", 900_000, min_bars=1),
            ),
            store=SQLiteMtfCandleStore(Path(tmp) / "mtf.sqlite3"),
        )
        outbox = SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3")
        return buffer, outbox, LivePureSourceDiagnosticRunner(buffer=buffer, outbox=outbox)

    def test_not_ready_buffer_emits_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, runner = self.make(tmp)
            buffer.ingest(candle(0, interval="5", interval_ms=300_000))
            result = runner.run_once()
            self.assertEqual(result.status, LiveDiagnosticStatus.WAIT_MTF_HISTORY)
            self.assertFalse(result.published)
            self.assertFalse(result.trade_entry_allowed)
            self.assertEqual(outbox.pending(), ())

    def test_ready_buffer_publishes_fail_closed_diagnostic_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, runner = self.make(tmp)
            buffer.ingest(candle(0, interval="5", interval_ms=300_000))
            buffer.ingest(candle(0, interval="15", interval_ms=900_000))

            first = runner.run_once()
            self.assertEqual(first.status, LiveDiagnosticStatus.DIAGNOSTIC_READY)
            self.assertTrue(first.published)
            self.assertFalse(first.trade_entry_allowed)
            self.assertIsNotNone(first.artifact_sha256)
            rows = outbox.pending()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].event_type, LIVE_DIAGNOSTIC_EVENT_TYPE)
            self.assertFalse(rows[0].payload["artifact"]["trade_entry_allowed"])
            self.assertFalse(rows[0].payload["artifact"]["financial_run"])

            second = runner.run_once()
            self.assertFalse(second.published)
            self.assertEqual(second.artifact_sha256, first.artifact_sha256)
            self.assertEqual(len(outbox.pending()), 1)

    def test_new_closed_prefix_produces_new_diagnostic_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, runner = self.make(tmp)
            buffer.ingest(candle(0, interval="5", interval_ms=300_000))
            buffer.ingest(candle(0, interval="15", interval_ms=900_000))
            first = runner.run_once()

            buffer.ingest(candle(300_000, interval="5", interval_ms=300_000))
            second = runner.run_once()
            self.assertTrue(second.published)
            self.assertNotEqual(second.artifact_sha256, first.artifact_sha256)
            self.assertEqual(len(outbox.pending()), 2)

    def test_restart_reuses_durable_buffer_and_outbox_without_duplicate_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, runner = self.make(tmp)
            buffer.ingest(candle(0, interval="5", interval_ms=300_000))
            buffer.ingest(candle(0, interval="15", interval_ms=900_000))
            first = runner.run_once()
            self.assertTrue(first.published)

            restarted_buffer = LiveMtfBuffer(
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                specs=(
                    MtfSeriesSpec("5", 300_000, min_bars=1),
                    MtfSeriesSpec("15", 900_000, min_bars=1),
                ),
                store=SQLiteMtfCandleStore(Path(tmp) / "mtf.sqlite3"),
            )
            restarted = LivePureSourceDiagnosticRunner(
                buffer=restarted_buffer,
                outbox=SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3"),
            )
            second = restarted.run_once()
            self.assertFalse(second.published)
            self.assertEqual(second.artifact_sha256, first.artifact_sha256)


if __name__ == "__main__":
    unittest.main()
