from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.structure_stability import compare_bos_suffix


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def c(i: int, o: float, h: float, l: float, cl: float) -> Candle:
    return Candle(
        open_time=BASE + timedelta(minutes=i),
        close_time=BASE + timedelta(minutes=i + 1),
        open=o,
        high=h,
        low=l,
        close=cl,
        is_closed=True,
    )


class StructureStabilityTests(unittest.TestCase):
    def test_identical_report_has_perfect_bos_overlap(self):
        candles = [
            c(0, 10, 11, 9.5, 10.2),
            c(1, 10.2, 10.5, 8, 9),
            c(2, 9, 11, 8.5, 10.4),
            c(3, 10.4, 12, 9, 11.3),
            c(4, 11.3, 11.5, 9.5, 10.2),
            c(5, 10.2, 11, 9, 9.6),
            c(6, 9.6, 12, 9.3, 11.2),
            c(7, 11.2, 13, 10, 12.6),
            c(8, 12.6, 12.7, 10.5, 11.6),
            c(9, 11.6, 11.9, 8.5, 8.8),
        ]
        report = analyze_market(candles)
        result = compare_bos_suffix(report, report, compare_start=BASE)
        self.assertEqual(result.full_count, result.suffix_count)
        self.assertEqual(result.full_only_count, 0)
        self.assertEqual(result.suffix_only_count, 0)
        self.assertEqual(result.exact_jaccard, 1.0)

    def test_compare_start_excludes_earlier_bos(self):
        candles = [
            c(0, 10, 11, 9.5, 10.2),
            c(1, 10.2, 10.5, 8, 9),
            c(2, 9, 11, 8.5, 10.4),
            c(3, 10.4, 12, 9, 11.3),
            c(4, 11.3, 11.5, 9.5, 10.2),
            c(5, 10.2, 11, 9, 9.6),
            c(6, 9.6, 12, 9.3, 11.2),
            c(7, 11.2, 13, 10, 12.6),
            c(8, 12.6, 12.7, 10.5, 11.6),
            c(9, 11.6, 11.9, 8.5, 8.8),
        ]
        report = analyze_market(candles)
        result = compare_bos_suffix(report, report, compare_start=BASE + timedelta(minutes=11))
        self.assertEqual(result.full_count, 0)
        self.assertEqual(result.suffix_count, 0)
        self.assertEqual(result.exact_jaccard, 1.0)


if __name__ == "__main__":
    unittest.main()
