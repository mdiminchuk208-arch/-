import unittest
from datetime import datetime, timezone

from crypto_bot.data.bridge import TECHNICAL_NORMALIZATION_ID, to_canonical_candle, to_canonical_series
from crypto_bot.data.models import MarketCandle


def market(ts: int, *, symbol="BTC-USDT-SWAP", interval="1", closed=True) -> MarketCandle:
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
        is_closed=closed,
    )


class DataBridgeTests(unittest.TestCase):
    def test_market_candle_converts_to_utc_strategy_candle(self):
        row = to_canonical_candle(market(60_000), interval_ms=60_000)
        self.assertEqual(row.open_time, datetime(1970, 1, 1, 0, 1, tzinfo=timezone.utc))
        self.assertEqual(row.close_time, datetime(1970, 1, 1, 0, 2, tzinfo=timezone.utc))
        self.assertTrue(row.is_closed)
        self.assertEqual(row.close, 101.0)
        self.assertEqual(TECHNICAL_NORMALIZATION_ID, "TN_MARKET_CANDLE_TO_CANONICAL_UTC_V1")

    def test_unfinished_or_misaligned_candle_is_rejected(self):
        with self.assertRaises(ValueError):
            to_canonical_candle(market(60_000, closed=False), interval_ms=60_000)
        with self.assertRaises(ValueError):
            to_canonical_candle(market(60_001), interval_ms=60_000)

    def test_series_requires_single_identity_no_duplicates_and_contiguity(self):
        self.assertEqual(
            len(to_canonical_series([market(60_000), market(120_000)], interval_ms=60_000)),
            2,
        )
        with self.assertRaises(ValueError):
            to_canonical_series([market(60_000), market(60_000)], interval_ms=60_000)
        with self.assertRaises(ValueError):
            to_canonical_series([market(60_000), market(180_000)], interval_ms=60_000)
        with self.assertRaises(ValueError):
            to_canonical_series(
                [market(60_000), market(120_000, symbol="ETH-USDT-SWAP")],
                interval_ms=60_000,
            )

    def test_noncontiguous_series_can_be_requested_only_for_diagnostics(self):
        rows = to_canonical_series(
            [market(60_000), market(180_000)],
            interval_ms=60_000,
            require_contiguous=False,
        )
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
