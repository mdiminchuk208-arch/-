import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from crypto_bot.data.manifest import (
    DATASET_MANIFEST_SCHEMA,
    build_dataset_manifest,
    candle_content_sha256,
    read_dataset_manifest,
    write_dataset_manifest,
)
from crypto_bot.data.models import MarketCandle


def candle(ts, close=101.0, *, symbol="BTC-USDT-SWAP", closed=True):
    return MarketCandle(
        exchange="OKX",
        symbol=symbol,
        interval="1",
        open_time_ms=ts,
        open=100.0,
        high=max(102.0, close),
        low=min(99.0, close),
        close=close,
        volume_base=1.25,
        turnover_quote=125.0,
        is_closed=closed,
    )


class DatasetManifestTests(unittest.TestCase):
    def test_manifest_is_order_independent_for_same_chronological_series(self):
        rows = [candle(60_000), candle(120_000, 102.0)]
        left = build_dataset_manifest(rows, interval_ms=60_000, source="OKX_V5_HISTORY_CANDLES")
        right = build_dataset_manifest(list(reversed(rows)), interval_ms=60_000, source="OKX_V5_HISTORY_CANDLES")
        self.assertEqual(left.dataset_id, right.dataset_id)
        self.assertEqual(left.content_sha256, right.content_sha256)
        self.assertEqual(left.schema, DATASET_MANIFEST_SCHEMA)
        self.assertEqual(left.row_count, 2)
        self.assertTrue(left.closed_only)

    def test_content_change_changes_dataset_identity(self):
        rows = [candle(60_000), candle(120_000, 102.0)]
        # Keep the mutation inside the original candle's valid OHLC envelope so
        # this test isolates dataset identity rather than model validation.
        changed = [rows[0], replace(rows[1], close=101.5)]
        left = build_dataset_manifest(rows, interval_ms=60_000, source="OKX_V5_HISTORY_CANDLES")
        right = build_dataset_manifest(changed, interval_ms=60_000, source="OKX_V5_HISTORY_CANDLES")
        self.assertNotEqual(left.content_sha256, right.content_sha256)
        self.assertNotEqual(left.dataset_id, right.dataset_id)

    def test_source_and_requested_window_are_part_of_dataset_identity(self):
        rows = [candle(60_000)]
        left = build_dataset_manifest(
            rows,
            interval_ms=60_000,
            source="OKX_V5_HISTORY_CANDLES",
            requested_start_ms=60_000,
            requested_end_ms=120_000,
        )
        right = build_dataset_manifest(
            rows,
            interval_ms=60_000,
            source="OKX_V5_HISTORY_CANDLES",
            requested_start_ms=0,
            requested_end_ms=120_000,
        )
        self.assertNotEqual(left.dataset_id, right.dataset_id)
        self.assertEqual(left.content_sha256, right.content_sha256)

    def test_unfinished_candle_is_visible_in_manifest(self):
        manifest = build_dataset_manifest(
            [candle(60_000, closed=False)],
            interval_ms=60_000,
            source="TEST",
        )
        self.assertFalse(manifest.closed_only)

    def test_mixed_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            build_dataset_manifest(
                [candle(60_000), candle(120_000, symbol="ETH-USDT-SWAP")],
                interval_ms=60_000,
                source="TEST",
            )

    def test_empty_series_is_rejected(self):
        with self.assertRaises(ValueError):
            build_dataset_manifest([], interval_ms=60_000, source="TEST")

    def test_manifest_round_trip(self):
        manifest = build_dataset_manifest(
            [candle(60_000), candle(120_000, 102.0)],
            interval_ms=60_000,
            source="OKX_V5_HISTORY_CANDLES",
            requested_start_ms=60_000,
            requested_end_ms=120_000,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            write_dataset_manifest(manifest, path)
            restored = read_dataset_manifest(path)
        self.assertEqual(restored, manifest)

    def test_candle_hash_preserves_duplicate_rows_instead_of_deduplicating(self):
        one = [candle(60_000)]
        duplicate = [candle(60_000), candle(60_000)]
        self.assertNotEqual(candle_content_sha256(one), candle_content_sha256(duplicate))


if __name__ == "__main__":
    unittest.main()
