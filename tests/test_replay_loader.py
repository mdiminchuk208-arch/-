import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.models import HistoricalFetch, MarketCandle
from crypto_bot.data.pipeline import persist_audited_dataset
from crypto_bot.data.replay_loader import load_verified_mtf_replay_series, load_verified_replay_series


def candle(ts: int, *, interval="1", symbol="BTC-USDT-SWAP") -> MarketCandle:
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


def persist(tmp, *, interval="1", interval_ms=60_000, symbol="BTC-USDT-SWAP"):
    fetch = HistoricalFetch(
        exchange="OKX",
        symbol=symbol,
        interval=interval,
        requested_start_ms=interval_ms,
        requested_end_ms=interval_ms * 3,
        server_time_ms=interval_ms * 4,
        candles=tuple(
            candle(interval_ms * index, interval=interval, symbol=symbol)
            for index in (1, 2, 3)
        ),
    )
    return persist_audited_dataset(
        fetch,
        interval_ms=interval_ms,
        output_root=tmp,
        source="TEST",
    )


class ReplayLoaderTests(unittest.TestCase):
    def test_verified_dataset_loads_as_existing_stage10_replay_series(self):
        with tempfile.TemporaryDirectory() as tmp:
            persisted = persist(tmp)
            loaded = load_verified_replay_series(persisted.csv_path, persisted.manifest_path)
        self.assertEqual(str(loaded.series.timeframe), "1")
        self.assertEqual(loaded.series.interval_ms, 60_000)
        self.assertEqual(len(loaded.series.candles), 3)
        self.assertTrue(loaded.verification.is_replay_eligible)

    def test_tampered_dataset_never_reaches_replay_series(self):
        with tempfile.TemporaryDirectory() as tmp:
            persisted = persist(tmp)
            text = persisted.csv_path.read_text(encoding="utf-8")
            persisted.csv_path.write_text(text.replace("101.0", "101.5", 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CONTENT_HASH_MISMATCH"):
                load_verified_replay_series(persisted.csv_path, persisted.manifest_path)

    def test_mtf_loader_sorts_by_interval_and_requires_one_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = persist(tmp, interval="1", interval_ms=60_000)
            five = persist(tmp, interval="5", interval_ms=300_000)
            loaded = load_verified_mtf_replay_series([
                (five.csv_path, five.manifest_path),
                (one.csv_path, one.manifest_path),
            ])
            self.assertEqual([item.series.interval_ms for item in loaded], [60_000, 300_000])

            eth = persist(tmp, interval="15", interval_ms=900_000, symbol="ETH-USDT-SWAP")
            with self.assertRaisesRegex(ValueError, "same exchange and symbol"):
                load_verified_mtf_replay_series([
                    (one.csv_path, one.manifest_path),
                    (eth.csv_path, eth.manifest_path),
                ])

    def test_duplicate_mtf_interval_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = persist(Path(tmp) / "a")
            second = persist(Path(tmp) / "b")
            with self.assertRaisesRegex(ValueError, "duplicate MTF replay interval"):
                load_verified_mtf_replay_series([
                    (first.csv_path, first.manifest_path),
                    (second.csv_path, second.manifest_path),
                ])


if __name__ == "__main__":
    unittest.main()
