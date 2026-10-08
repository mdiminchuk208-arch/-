from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from crypto_bot.data.models import MarketCandle

spec = spec_from_file_location('research_import', Path(__file__).resolve().parents[1] / 'scripts/import_public_research_data.py')
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)


def candle(index):
    return MarketCandle('BINANCE', 'BTCUSDT', '5', index * 300000,
                        10 + index, 12 + index, 9 + index, 11 + index, index + 1)


class ResearchDataImportTests(unittest.TestCase):
    def test_gap_or_partial_bin_is_never_interpolated(self):
        rows, rejected = module.aggregate([candle(i) for i in (0, 2, 3, 4, 5, 6)], 5, 15)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].open_time_ms, 900000)
        self.assertEqual((rows[0].open, rows[0].high, rows[0].low, rows[0].close, rows[0].volume_base),
                         (13, 17, 12, 16, 15))
        self.assertEqual([r['source_rows'] for r in rejected], [2, 1])

    def test_duplicates_and_disaggregation_are_rejected(self):
        with self.assertRaises(ValueError):
            module.aggregate([candle(0), candle(0)], 5, 15)
        with self.assertRaises(ValueError):
            module.aggregate([candle(0)], 15, 5)

    def test_gzip_is_reproducible_and_records_logical_sha(self):
        with TemporaryDirectory() as directory:
            a, b = Path(directory) / 'a.csv.gz', Path(directory) / 'b.csv.gz'
            rows = [candle(0), candle(1)]
            left, right = module.write_compressed(rows, a), module.write_compressed(rows, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(left['csv_sha256'], right['csv_sha256'])
            self.assertEqual(left['gaps'], {})


if __name__ == '__main__':
    unittest.main()
