import tempfile
import unittest
from pathlib import Path

from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import read_klines_csv, write_klines_csv


class StorageTests(unittest.TestCase):
    def test_csv_round_trip(self):
        candles = [
            MarketCandle("BYBIT", "BTCUSDT", "1", 60_000, 100, 102, 99, 101, 1.5, 151.5, True),
            MarketCandle("BYBIT", "BTCUSDT", "1", 0, 99, 101, 98, 100, 2.0, 200.0, True),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = write_klines_csv(candles, Path(tmp) / "btc.csv")
            loaded = read_klines_csv(path)
        self.assertEqual([c.open_time_ms for c in loaded], [0, 60_000])
        self.assertEqual(loaded[1].volume_base, 1.5)


if __name__ == "__main__":
    unittest.main()
