import csv
import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.models import HistoricalFetch, MarketCandle
from crypto_bot.data.pipeline import persist_audited_dataset
from crypto_bot.data.verify import require_replay_eligible_dataset, verify_persisted_dataset


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


def healthy_fetch() -> HistoricalFetch:
    return HistoricalFetch(
        exchange="OKX",
        symbol="BTC-USDT-SWAP",
        interval="1",
        requested_start_ms=60_000,
        requested_end_ms=180_000,
        server_time_ms=240_000,
        candles=(candle(60_000), candle(120_000), candle(180_000)),
    )


class DatasetVerifyTests(unittest.TestCase):
    def test_persisted_healthy_dataset_is_replay_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            persisted = persist_audited_dataset(
                healthy_fetch(),
                interval_ms=60_000,
                output_root=tmp,
                source="OKX_V5_HISTORY_CANDLES",
            )
            verified = require_replay_eligible_dataset(
                persisted.csv_path,
                persisted.manifest_path,
            )
        self.assertTrue(verified.is_replay_eligible)
        self.assertTrue(verified.hash_matches)
        self.assertTrue(verified.identity_matches)
        self.assertTrue(verified.row_count_matches)
        self.assertTrue(verified.bounds_match)

    def test_content_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            persisted = persist_audited_dataset(
                healthy_fetch(),
                interval_ms=60_000,
                output_root=tmp,
                source="OKX_V5_HISTORY_CANDLES",
            )
            with persisted.csv_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["close"] = "101.5"
            with persisted.csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            result = verify_persisted_dataset(persisted.csv_path, persisted.manifest_path)
            self.assertFalse(result.hash_matches)
            self.assertFalse(result.is_replay_eligible)
            with self.assertRaisesRegex(ValueError, "CONTENT_HASH_MISMATCH"):
                require_replay_eligible_dataset(persisted.csv_path, persisted.manifest_path)

    def test_gap_fails_replay_gate_even_when_manifest_matches_the_gapped_file(self):
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
            persisted = persist_audited_dataset(
                fetch,
                interval_ms=60_000,
                output_root=tmp,
                source="OKX_V5_HISTORY_CANDLES",
            )
            result = verify_persisted_dataset(persisted.csv_path, persisted.manifest_path)
            self.assertTrue(result.hash_matches)
            self.assertFalse(result.is_replay_eligible)
            with self.assertRaisesRegex(ValueError, "DATA_QUALITY_FAILED"):
                require_replay_eligible_dataset(persisted.csv_path, persisted.manifest_path)

    def test_unfinished_manifest_fails_closed(self):
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
            persisted = persist_audited_dataset(
                fetch,
                interval_ms=60_000,
                output_root=tmp,
                source="TEST",
            )
            with self.assertRaisesRegex(ValueError, "MANIFEST_NOT_CLOSED_ONLY"):
                require_replay_eligible_dataset(persisted.csv_path, persisted.manifest_path)


if __name__ == "__main__":
    unittest.main()
