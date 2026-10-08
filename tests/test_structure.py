import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.structure import confirmed_swings, bearish_bos, bullish_bos


def c(i, o, h, l, cl, closed=True):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, closed)


class StructureTests(unittest.TestCase):
    def test_swing_high(self):
        candles = [c(0, 9, 10, 8, 9), c(1, 10, 12, 9, 11), c(2, 10, 11, 9, 10)]
        swings = confirmed_swings(candles)
        self.assertEqual([(s.index, s.kind, s.price) for s in swings], [(1, "high", 12)])

    def test_swing_low(self):
        candles = [c(0, 11, 12, 10, 11), c(1, 10, 11, 8, 9), c(2, 10, 12, 9, 11)]
        swings = confirmed_swings(candles)
        self.assertEqual([(s.index, s.kind, s.price) for s in swings], [(1, "low", 8)])

    def test_no_swing_until_right_candle_closed(self):
        candles = [c(0, 9, 10, 8, 9), c(1, 10, 12, 9, 11), c(2, 10, 11, 9, 10, closed=False)]
        self.assertEqual(confirmed_swings(candles), [])


    def test_no_swing_if_center_candle_is_not_closed(self):
        candles = [c(0, 9, 10, 8, 9), c(1, 10, 12, 9, 11, closed=False), c(2, 10, 11, 9, 10)]
        self.assertEqual(confirmed_swings(candles), [])

    def test_bos_close_not_wick(self):
        self.assertTrue(bullish_bos(101, 100))
        self.assertFalse(bullish_bos(99.5, 100))
        self.assertTrue(bearish_bos(99, 100))
        self.assertFalse(bearish_bos(100.5, 100))

    def test_candle_rejects_naive_timestamps(self):
        naive = datetime(2026, 1, 1)
        with self.assertRaises(ValueError):
            Candle(naive, naive + timedelta(minutes=1), 10, 11, 9, 10, True)


if __name__ == "__main__":
    unittest.main()
