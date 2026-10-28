import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.data.models import MarketCandle
from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.runtime.health import (
    RuntimeHealthPolicy,
    RuntimeHealthState,
    evaluate_runtime_health,
)
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer, MtfSeriesSpec, SQLiteMtfCandleStore


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


class RuntimeHealthTests(unittest.TestCase):
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
        policy = RuntimeHealthPolicy(
            stale_after_seconds={"5": 600, "15": 1_800},
            max_pending_outbox=10,
        )
        return buffer, outbox, policy

    def test_starting_until_all_mtf_history_is_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, policy = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            snapshot = evaluate_runtime_health(
                buffer=buffer,
                outbox=outbox,
                policy=policy,
                observed_at=datetime.fromtimestamp(300, tz=UTC),
                diagnostic_pipeline_available=True,
            )
            self.assertEqual(snapshot.state, RuntimeHealthState.STARTING)
            self.assertIn("MTF_HISTORY_NOT_READY", snapshot.reasons)
            self.assertIn("MTF_MISSING_15", snapshot.reasons)
            self.assertFalse(snapshot.trade_entry_allowed)

    def test_fresh_ready_runtime_is_healthy_diagnostic_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, policy = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            buffer.ingest(candle(0, interval="15"))
            snapshot = evaluate_runtime_health(
                buffer=buffer,
                outbox=outbox,
                policy=policy,
                observed_at=datetime.fromtimestamp(900, tz=UTC),
                diagnostic_pipeline_available=True,
            )
            self.assertEqual(snapshot.state, RuntimeHealthState.HEALTHY_DIAGNOSTIC)
            self.assertEqual(snapshot.reasons, ())
            self.assertTrue(snapshot.mtf_ready)
            self.assertFalse(snapshot.trade_entry_allowed)

    def test_stale_any_timeframe_enters_safe_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, policy = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            buffer.ingest(candle(0, interval="15"))
            snapshot = evaluate_runtime_health(
                buffer=buffer,
                outbox=outbox,
                policy=policy,
                observed_at=datetime.fromtimestamp(3_000, tz=UTC),
                diagnostic_pipeline_available=True,
            )
            self.assertEqual(snapshot.state, RuntimeHealthState.SAFE_MODE)
            self.assertIn("5", snapshot.stale_timeframes)
            self.assertIn("MARKET_DATA_STALE_5", snapshot.reasons)
            self.assertFalse(snapshot.trade_entry_allowed)

    def test_outbox_backlog_degrades_but_does_not_change_execution_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, _ = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            buffer.ingest(candle(0, interval="15"))
            outbox.enqueue(
                event_id="evt-1",
                event_type="test",
                payload={"v": 1},
                created_at=datetime.fromtimestamp(800, tz=UTC),
            )
            policy = RuntimeHealthPolicy(
                stale_after_seconds={"5": 600, "15": 1_800},
                max_pending_outbox=0,
            )
            snapshot = evaluate_runtime_health(
                buffer=buffer,
                outbox=outbox,
                policy=policy,
                observed_at=datetime.fromtimestamp(900, tz=UTC),
                diagnostic_pipeline_available=True,
            )
            self.assertEqual(snapshot.state, RuntimeHealthState.DEGRADED)
            self.assertIn("ENGINE_OUTBOX_BACKLOG", snapshot.reasons)
            self.assertFalse(snapshot.trade_entry_allowed)

    def test_diagnostic_unavailable_is_degraded_when_market_data_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, policy = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            buffer.ingest(candle(0, interval="15"))
            snapshot = evaluate_runtime_health(
                buffer=buffer,
                outbox=outbox,
                policy=policy,
                observed_at=datetime.fromtimestamp(900, tz=UTC),
                diagnostic_pipeline_available=False,
            )
            self.assertEqual(snapshot.state, RuntimeHealthState.DEGRADED)
            self.assertIn("DIAGNOSTIC_PIPELINE_UNAVAILABLE", snapshot.reasons)

    def test_health_policy_must_match_configured_timeframes_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, _ = self.make(tmp)
            bad = RuntimeHealthPolicy(stale_after_seconds={"5": 600}, max_pending_outbox=10)
            with self.assertRaisesRegex(ValueError, "exactly match"):
                evaluate_runtime_health(
                    buffer=buffer,
                    outbox=outbox,
                    policy=bad,
                    observed_at=datetime.fromtimestamp(900, tz=UTC),
                    diagnostic_pipeline_available=True,
                )

    def test_naive_health_clock_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer, outbox, policy = self.make(tmp)
            with self.assertRaises(ValueError):
                evaluate_runtime_health(
                    buffer=buffer,
                    outbox=outbox,
                    policy=policy,
                    observed_at=datetime(2026, 10, 28, 10, 0),
                    diagnostic_pipeline_available=True,
                )


if __name__ == "__main__":
    unittest.main()
