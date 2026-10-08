import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.sfp import detect_sfp


def c(i, o, h, l, cl):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, True)


class SFPTests(unittest.TestCase):
    def test_valid_bearish_sfp(self):
        res = detect_sfp(c(0, 99, 102, 98, 99.5), c(1, 99.4, 100, 97, 98), 100, "high")
        self.assertTrue(res.valid)
        self.assertEqual(res.direction, Direction.SHORT)

    def test_invalid_if_sweep_candle_closes_outside(self):
        res = detect_sfp(c(0, 99, 102, 98, 101), c(1, 99.4, 100, 97, 98), 100, "high")
        self.assertFalse(res.valid)

    def test_invalid_if_next_candle_opens_outside(self):
        res = detect_sfp(c(0, 99, 102, 98, 99.5), c(1, 100.5, 101, 98, 99), 100, "high")
        self.assertFalse(res.valid)

    def test_valid_bullish_sfp(self):
        res = detect_sfp(c(0, 101, 102, 98, 100.5), c(1, 100.6, 103, 100.2, 102), 100, "low")
        self.assertTrue(res.valid)
        self.assertEqual(res.direction, Direction.LONG)

    def test_rejects_non_chronological_next_candle(self):
        sweep = c(1, 99, 102, 98, 99.5)
        earlier = c(0, 99.4, 100, 97, 98)
        res = detect_sfp(sweep, earlier, 100, "high")
        self.assertFalse(res.valid)

    def test_rejects_nonpositive_liquidity_level(self):
        with self.assertRaises(ValueError):
            detect_sfp(c(0, 99, 102, 98, 99.5), c(1, 99.4, 100, 97, 98), 0, "high")


if __name__ == "__main__":
    unittest.main()
