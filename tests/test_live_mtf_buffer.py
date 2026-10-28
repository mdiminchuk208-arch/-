import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.models import MarketCandle
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer, MtfSeriesSpec, SQLiteMtfCandleStore


def candle(ts: int, *, interval="5", symbol="BTC-USDT-SWAP", close=101.0, closed=True):
    return MarketCandle(
        exchange="OKX",
        symbol=symbol,
        interval=interval,
        open_time_ms=ts,
        open=100.0,
        high=max(102.0, close),
        low=min(99.0, close),
        close=close,
        volume_base=1.0,
        turnover_quote=100.0,
        is_closed=closed,
    )


class LiveMtfBufferTests(unittest.TestCase):
    def make(self, tmp):
        store = SQLiteMtfCandleStore(Path(tmp) / "mtf.sqlite3")
        buffer = LiveMtfBuffer(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            specs=(
                MtfSeriesSpec("5", 300_000, min_bars=2, max_bars=3),
                MtfSeriesSpec("15", 900_000, min_bars=1, max_bars=2),
            ),
            store=store,
        )
        return store, buffer

    def test_readiness_tracks_each_configured_timeframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, buffer = self.make(tmp)
            self.assertFalse(buffer.status().ready)
            buffer.ingest(candle(0, interval="5"))
            buffer.ingest(candle(300_000, interval="5"))
            self.assertFalse(buffer.status().ready)
            buffer.ingest(candle(0, interval="15"))
            status = buffer.status()
            self.assertTrue(status.ready)
            self.assertEqual(status.counts, (("5", 2), ("15", 1)))

    def test_exact_duplicate_is_idempotent_but_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, buffer = self.make(tmp)
            row = candle(0, interval="5")
            self.assertTrue(buffer.ingest(row))
            self.assertFalse(buffer.ingest(row))
            with self.assertRaisesRegex(ValueError, "mutation"):
                buffer.ingest(candle(0, interval="5", close=101.5))

    def test_gap_out_of_order_unfinished_and_wrong_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, buffer = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            with self.assertRaisesRegex(ValueError, "continuity gap"):
                buffer.ingest(candle(600_000, interval="5"))
            with self.assertRaisesRegex(ValueError, "out-of-order"):
                buffer.ingest(candle(-300_000, interval="5"))
            with self.assertRaisesRegex(ValueError, "closed candles only"):
                buffer.ingest(candle(300_000, interval="5", closed=False))
            with self.assertRaisesRegex(ValueError, "identity"):
                buffer.ingest(candle(300_000, interval="5", symbol="ETH-USDT-SWAP"))

    def test_unconfigured_and_misaligned_interval_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, buffer = self.make(tmp)
            with self.assertRaisesRegex(ValueError, "unconfigured"):
                buffer.ingest(candle(0, interval="60"))
            with self.assertRaisesRegex(ValueError, "not aligned"):
                buffer.ingest(candle(1, interval="5"))

    def test_replay_snapshot_is_sorted_bounded_and_restart_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, buffer = self.make(tmp)
            for ts in (0, 300_000, 600_000, 900_000):
                buffer.ingest(candle(ts, interval="5"))
            buffer.ingest(candle(0, interval="15"))
            series = buffer.replay_series()
            self.assertEqual([item.timeframe for item in series], ["5", "15"])
            self.assertEqual([row.open_time_ms for row in series[0].candles], [300_000, 600_000, 900_000])

            restarted = LiveMtfBuffer(
                exchange="OKX",
                symbol="BTC-USDT-SWAP",
                specs=(
                    MtfSeriesSpec("5", 300_000, min_bars=2, max_bars=3),
                    MtfSeriesSpec("15", 900_000, min_bars=1, max_bars=2),
                ),
                store=SQLiteMtfCandleStore(store.path),
            )
            self.assertTrue(restarted.status().ready)
            self.assertEqual(
                [row.open_time_ms for row in restarted.replay_series()[0].candles],
                [300_000, 600_000, 900_000],
            )

    def test_replay_snapshot_requires_readiness_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, buffer = self.make(tmp)
            buffer.ingest(candle(0, interval="5"))
            with self.assertRaisesRegex(ValueError, "not ready"):
                buffer.replay_series()
            partial = buffer.replay_series(require_ready=False)
            self.assertEqual(len(partial), 1)


if __name__ == "__main__":
    unittest.main()
