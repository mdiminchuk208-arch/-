import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.manifest import read_dataset_manifest
from crypto_bot.data.models import HistoricalFetch, MarketCandle
from crypto_bot.data.pipeline import persist_audited_dataset
from crypto_bot.data.storage import read_klines_csv


def candle(ts: int, close: float = 101.0, *, closed: bool = True) -> MarketCandle:
    return MarketCandle(
        exchange="OKX",
        symbol="BTC-USDT-SWAP",
        interval="1",
        open_time_ms=ts,
        open=100.0,
        high=max(102.0, close),
        low=min(99.0, close),
        close=close,
        volume_base=1.0,
        turnover_quote=100.0,
        is_closed=closed,
    )


class DataPipelineTests(unittest.TestCase):
    def test_healthy_dataset_writes_csv_manifest_and_identity(self):
        fetch = HistoricalFetch(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="1",
            requested_start_ms=60_000,
            requested_end_ms=180_000,
            server_time_ms=240_000,
            candles=(candle(60_000), candle(120_000), candle(180_000)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = persist_audited_dataset(
                fetch,
                interval_ms=60_000,
                output_root=tmp,
                source="OKX_V5_HISTORY_CANDLES",
            )
            self.assertTrue(result.is_healthy)
            self.assertTrue(result.csv_path.exists())
            self.assertTrue(result.manifest_path.exists())
            self.assertEqual(
                result.csv_path,
                Path(tmp) / "okx" / "BTC-USDT-SWAP" / "1.csv",
            )
            restored_rows = read_klines_csv(result.csv_path)
            restored_manifest = read_dataset_manifest(result.manifest_path)
        self.assertEqual(restored_rows, list(fetch.candles))
        self.assertEqual(restored_manifest, result.manifest)
        self.assertEqual(restored_manifest.row_count, 3)
        self.assertTrue(restored_manifest.closed_only)

    def test_internal_gap_persists_for_diagnostics_but_is_not_healthy(self):
        fetch = HistoricalFetch(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="1",
            requested_start_ms=60_000,
            requested_end_ms=180_000,
            server_time_ms=240_000,
            candles=(candle(60_000), candle(180_000)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = persist_audited_dataset(
                fetch,
                interval_ms=60_000,
                output_root=tmp,
                source="OKX_V5_HISTORY_CANDLES",
            )
            self.assertFalse(result.is_healthy)
            self.assertTrue(result.csv_path.exists())
            self.assertTrue(result.manifest_path.exists())
        self.assertEqual(result.qa.gap_count, 1)
        self.assertEqual(result.coverage.internal_missing_count, 1)

    def test_unfinished_dataset_is_not_healthy(self):
        fetch = HistoricalFetch(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="1",
            requested_start_ms=60_000,
            requested_end_ms=60_000,
            server_time_ms=180_000,
            candles=(candle(60_000, closed=False),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = persist_audited_dataset(
                fetch,
                interval_ms=60_000,
                output_root=tmp,
                source="TEST",
            )
        self.assertFalse(result.is_healthy)
        self.assertFalse(result.manifest.closed_only)

    def test_empty_dataset_is_rejected(self):
        fetch = HistoricalFetch(
            exchange="OKX",
            symbol="BTC-USDT-SWAP",
            interval="1",
            requested_start_ms=60_000,
            requested_end_ms=60_000,
            server_time_ms=180_000,
            candles=(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                persist_audited_dataset(
                    fetch,
                    interval_ms=60_000,
                    output_root=tmp,
                    source="TEST",
                )


if __name__ == "__main__":
    unittest.main()
