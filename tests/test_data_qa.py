import unittest

from crypto_bot.data.models import MarketCandle
from crypto_bot.data.qa import DataIssueKind, audit_klines


def candle(t, *, closed=True):
    return MarketCandle("BYBIT", "BTCUSDT", "1", t, 100, 101, 99, 100.5, 1, 100, closed)


class DataQATests(unittest.TestCase):
    def test_healthy_series(self):
        report = audit_klines([candle(0), candle(60_000), candle(120_000)], 60_000)
        self.assertTrue(report.is_healthy)
        self.assertEqual(report.gap_count, 0)

    def test_gap_is_counted_by_missing_candles(self):
        report = audit_klines([candle(0), candle(180_000)], 60_000)
        self.assertEqual(report.gap_count, 2)
        self.assertTrue(any(i.kind == DataIssueKind.GAP for i in report.issues))

    def test_misaligned_timestamp_is_flagged(self):
        report = audit_klines([candle(1_000)], 60_000)
        self.assertEqual(report.misaligned_count, 1)
        self.assertTrue(any(i.kind == DataIssueKind.MISALIGNED_TIMESTAMP for i in report.issues))

    def test_duplicate_out_of_order_and_unfinished_are_flagged(self):
        report = audit_klines([candle(60_000), candle(0), candle(0, closed=False)], 60_000)
        self.assertEqual(report.duplicate_count, 1)
        self.assertEqual(report.out_of_order_count, 1)
        self.assertEqual(report.unfinished_count, 1)
        self.assertFalse(report.is_healthy)

    def test_mixed_symbol_metadata_is_flagged(self):
        a = candle(0)
        b = MarketCandle(
            exchange=a.exchange, symbol="ETHUSDT", interval=a.interval,
            open_time_ms=a.open_time_ms + 60_000, open=100, high=101, low=99, close=100,
            volume_base=1, turnover_quote=100, is_closed=True,
        )
        report = audit_klines([a, b], 60_000)
        self.assertEqual(report.metadata_mismatch_count, 1)
        self.assertFalse(report.is_healthy)


if __name__ == "__main__":
    unittest.main()
