"""Integrity/causality tests; no financial or strategy evaluation."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from okx_qualification_data_v1 import (
    STEP,
    DataInvalid,
    page_url,
    parse_page,
    validate_continuity,
)


def candle(at, confirm="1"):
    return [str(at), "100", "102", "99", "101", "1", "0.01", "1", confirm]


def page(rows):
    return json.dumps({"code": "0", "data": rows}).encode()


class DataTests(unittest.TestCase):
    def test_exact_decimal_and_chronological_sort(self):
        rows = parse_page(page([candle(2 * STEP), candle(STEP)]), 3 * STEP)
        self.assertEqual([r[0] for r in rows], [str(STEP), str(2 * STEP)])
        self.assertEqual(rows[0][1], "100")

    def test_completed_only(self):
        with self.assertRaises(DataInvalid):
            parse_page(page([candle(STEP, "0")]), 2 * STEP)

    def test_future_and_cursor_equality_rejected(self):
        with self.assertRaises(DataInvalid):
            parse_page(page([candle(2 * STEP)]), 2 * STEP)

    def test_grid_and_duplicate_rejected(self):
        for rows in [[candle(STEP + 1)], [candle(STEP), candle(STEP)]]:
            with self.assertRaises(DataInvalid):
                parse_page(page(rows), 3 * STEP)

    def test_bad_prices_nonfinite_and_volume(self):
        for column, value in [(1, "NaN"), (2, "98"), (3, "0"), (5, "-1")]:
            row = candle(STEP)
            row[column] = value
            with self.assertRaises(DataInvalid):
                parse_page(page([row]), 2 * STEP)

    def test_application_error_not_success(self):
        with self.assertRaises(DataInvalid):
            parse_page(b'{"code":"50011","data":[]}', 2 * STEP)

    def test_full_grid_and_edges(self):
        rows = [candle(0), candle(STEP), candle(2 * STEP), candle(3 * STEP)]
        self.assertEqual(validate_continuity(rows, STEP, 3 * STEP), rows[1:3])

    def test_interior_gap_not_interpolated(self):
        with self.assertRaisesRegex(DataInvalid, "CONTINUITY_GAP"):
            validate_continuity([candle(STEP), candle(3 * STEP)], STEP, 4 * STEP)

    def test_duplicate_pages_rejected(self):
        with self.assertRaises(DataInvalid):
            validate_continuity([candle(STEP), candle(STEP)], STEP, 2 * STEP)

    def test_prefix_unaffected_by_future_mutation(self):
        prefix = [candle(STEP), candle(2 * STEP)]
        extended = prefix + [candle(3 * STEP)]
        extended[-1][1:5] = ["999", "999", "999", "999"]
        self.assertEqual(
            validate_continuity(prefix, STEP, 3 * STEP),
            validate_continuity(extended, STEP, 3 * STEP),
        )

    def test_only_official_public_route_and_products(self):
        self.assertTrue(
            page_url("BTC-USDT-SWAP", STEP).startswith(
                "https://www.okx.com/api/v5/market/history-candles?"
            )
        )
        for name in ["BTCUSDT", "../private", "ETH-USD-SWAP"]:
            with self.assertRaises(DataInvalid):
                page_url(name, STEP)


if __name__ == "__main__":
    unittest.main()
