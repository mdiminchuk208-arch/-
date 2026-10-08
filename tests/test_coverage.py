import unittest

from crypto_bot.data.coverage import audit_coverage
from crypto_bot.data.models import HistoricalFetch, MarketCandle


def candle(t):
    return MarketCandle("BYBIT", "BTCUSDT", "1", t, 100, 101, 99, 100.5, 1, 100, True)


class CoverageTests(unittest.TestCase):
    def test_coverage_excludes_current_unclosed_slot(self):
        fetch = HistoricalFetch(
            exchange="BYBIT",
            symbol="BTCUSDT",
            interval="1",
            requested_start_ms=0,
            requested_end_ms=180_000,
            server_time_ms=180_000,
            candles=(candle(0), candle(60_000), candle(120_000)),
        )
        report = audit_coverage(fetch, 60_000)
        self.assertEqual(report.expected_count, 3)
        self.assertEqual(report.actual_count, 3)
        self.assertEqual(report.completeness_pct, 100.0)

    def test_missing_candle_reduces_completeness(self):
        fetch = HistoricalFetch(
            exchange="BYBIT",
            symbol="BTCUSDT",
            interval="1",
            requested_start_ms=0,
            requested_end_ms=120_000,
            server_time_ms=180_000,
            candles=(candle(0), candle(120_000)),
        )
        report = audit_coverage(fetch, 60_000)
        self.assertEqual(report.expected_count, 3)
        self.assertEqual(report.missing_count, 1)
        self.assertAlmostEqual(report.completeness_pct, 66.6666666667)


if __name__ == "__main__":
    unittest.main()

class CoverageBoundaryTests(unittest.TestCase):
    def test_boundary_shortfall_is_distinct_from_internal_gap(self):
        fetch = HistoricalFetch(
            exchange="BYBIT",
            symbol="BTCUSDT",
            interval="1",
            requested_start_ms=0,
            requested_end_ms=180_000,
            server_time_ms=240_000,
            candles=(candle(60_000), candle(120_000), candle(180_000)),
        )
        report = audit_coverage(fetch, 60_000)
        self.assertEqual(report.missing_count, 1)
        self.assertEqual(report.leading_missing_count, 1)
        self.assertEqual(report.internal_missing_count, 0)
        self.assertEqual(report.trailing_missing_count, 0)
        self.assertEqual(report.coverage_status, "BOUNDARY_SHORTFALL")

    def test_internal_missing_slot_is_classified_internal(self):
        fetch = HistoricalFetch(
            exchange="BYBIT",
            symbol="BTCUSDT",
            interval="1",
            requested_start_ms=0,
            requested_end_ms=180_000,
            server_time_ms=240_000,
            candles=(candle(0), candle(60_000), candle(180_000)),
        )
        report = audit_coverage(fetch, 60_000)
        self.assertEqual(report.missing_count, 1)
        self.assertEqual(report.internal_missing_count, 1)
        self.assertTrue(report.has_internal_gap)
        self.assertEqual(report.coverage_status, "INTERNAL_GAP")
