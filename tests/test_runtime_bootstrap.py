import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.models import HistoricalFetch, MarketCandle
from crypto_bot.data.pipeline import persist_audited_dataset
from crypto_bot.runtime.bootstrap import bootstrap_live_mtf_from_verified_datasets
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer, MtfSeriesSpec, SQLiteMtfCandleStore


def candle(ts: int, *, interval: str, symbol: str = "BTC-USDT-SWAP") -> MarketCandle:
    return MarketCandle(
        exchange="OKX",
        symbol=symbol,
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


def persist(tmp: str, *, interval: str, interval_ms: int, rows, symbol="BTC-USDT-SWAP"):
    fetch = HistoricalFetch(
        exchange="OKX",
        symbol=symbol,
        interval=interval,
        requested_start_ms=rows[0].open_time_ms,
        requested_end_ms=rows[-1].open_time_ms,
        server_time_ms=rows[-1].open_time_ms + interval_ms,
        candles=tuple(rows),
    )
    return persist_audited_dataset(
        fetch,
        interval_ms=interval_ms,
        output_root=tmp,
        source="TEST_VERIFIED_BOOTSTRAP",
    )


class RuntimeBootstrapTests(unittest.TestCase):
    def make_buffer(self, tmp):
        return LiveMtfBuffer(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            specs=(
                MtfSeriesSpec("5", 300_000, min_bars=2),
                MtfSeriesSpec("15", 900_000, min_bars=1),
            ),
            store=SQLiteMtfCandleStore(Path(tmp) / "runtime.sqlite3"),
        )

    def test_verified_datasets_seed_live_buffer_and_are_restart_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "history"
            five = persist(
                str(data_root),
                interval="5",
                interval_ms=300_000,
                rows=[candle(0, interval="5"), candle(300_000, interval="5")],
            )
            fifteen = persist(
                str(data_root),
                interval="15",
                interval_ms=900_000,
                rows=[candle(0, interval="15")],
            )
            datasets = (
                (five.csv_path, five.manifest_path),
                (fifteen.csv_path, fifteen.manifest_path),
            )
            buffer = self.make_buffer(tmp)
            first = bootstrap_live_mtf_from_verified_datasets(buffer, datasets)
            self.assertTrue(first.ready)
            self.assertEqual(first.inserted_count, 3)
            self.assertEqual(first.duplicate_count, 0)
            self.assertEqual(first.series_counts, (("5", 2), ("15", 1)))

            restarted = self.make_buffer(tmp)
            second = bootstrap_live_mtf_from_verified_datasets(restarted, datasets)
            self.assertTrue(second.ready)
            self.assertEqual(second.inserted_count, 0)
            self.assertEqual(second.duplicate_count, 3)

    def test_missing_configured_timeframe_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            five = persist(
                str(Path(tmp) / "history"),
                interval="5",
                interval_ms=300_000,
                rows=[candle(0, interval="5"), candle(300_000, interval="5")],
            )
            buffer = self.make_buffer(tmp)
            with self.assertRaisesRegex(ValueError, "missing configured timeframes"):
                bootstrap_live_mtf_from_verified_datasets(
                    buffer,
                    ((five.csv_path, five.manifest_path),),
                )

    def test_wrong_symbol_fails_before_live_state_is_seeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrong = persist(
                str(Path(tmp) / "history"),
                interval="5",
                interval_ms=300_000,
                rows=[
                    candle(0, interval="5", symbol="ETH-USDT-SWAP"),
                    candle(300_000, interval="5", symbol="ETH-USDT-SWAP"),
                ],
                symbol="ETH-USDT-SWAP",
            )
            buffer = self.make_buffer(tmp)
            with self.assertRaisesRegex(ValueError, "identity"):
                bootstrap_live_mtf_from_verified_datasets(
                    buffer,
                    ((wrong.csv_path, wrong.manifest_path),),
                    require_all_configured_timeframes=False,
                )
            self.assertEqual(buffer.status().counts, (("5", 0), ("15", 0)))


if __name__ == "__main__":
    unittest.main()
