from __future__ import annotations

import unittest
from decimal import Decimal

from original_v1_1_financial_data import Bar
from source_strategy_v1_range_resolver import resolve_range_chain


D = Decimal


class FakeIndex:
    symbol = "BTCUSDT"
    tf = 15

    def __init__(self, bars, objects):
        self.bars = bars
        self.by_id = {obj["id"]: obj for obj in objects}


def b(start, o, h, l, c):
    return Bar(start, start + 900, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def sw(identifier, side, price, known_at):
    return {
        "id": identifier,
        "kind": "swing",
        "known_at": known_at,
        "completed_at": known_at,
        "tf": 15,
        "source_validated": True,
        "payload": {"side": side, "price": str(price)},
    }


def rng():
    return {
        "id": "range-1",
        "kind": "range",
        "known_at": 1800,
        "completed_at": 1800,
        "tf": 15,
        "source_validated": False,
        "payload": {
            "low": "90",
            "high": "110",
            "low_swing_id": "low-90",
            "high_swing_id": "high-110",
            "source_selected": False,
        },
    }


def valid_index(with_retest=True):
    midpoint = b(1800, 98, 102, 97, 101)
    deviation = b(2700, 96, 98, 85, 92)
    choch = b(3600, 101, 106, 99, 105)
    bars = [midpoint, deviation, choch]
    if with_retest:
        bars.append(b(4500, 96, 98, 89, 93))
    objects = [
        sw("low-90", "LOW", 90, 900),
        sw("high-110", "HIGH", 110, 1800),
        sw("local-high-104", "HIGH", 104, 2600),
        rng(),
    ]
    return FakeIndex(bars, objects)


class TestSourceStrategyV1RangeResolver(unittest.TestCase):
    def test_range_chain_resolves_deviation_choch_and_retest(self):
        result = resolve_range_chain(valid_index(), "range-1", 5400)
        self.assertEqual(result["state"], "SOURCE_CHAIN_READY")
        self.assertEqual(result["branch"], "RANGE_CONSERVATIVE")
        self.assertEqual(result["direction"], "LONG")
        self.assertEqual(D(result["entry"]["price"]), D("90"))
        self.assertEqual(D(result["stop_anchor"]["price"]), D("85"))
        self.assertEqual(D(result["target_plan"]["opposite_boundary"]), D("110"))
        self.assertEqual(result["target_plan"]["allocation"], ["0.80", "0.20"])
        self.assertFalse(result["trade_entry_allowed"])

    def test_missing_midpoint_reaction_stays_unknown(self):
        index = valid_index()
        index.bars[0] = b(1800, 92, 95, 91, 94)
        result = resolve_range_chain(index, "range-1", 5400)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_RANGE_MIDPOINT_REACTION")

    def test_missing_retest_stays_unknown(self):
        result = resolve_range_chain(valid_index(with_retest=False), "range-1", 5400)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_RANGE_RECLAIM_RETEST")

    def test_internal_trending_structure_is_source_fail(self):
        index = valid_index()
        index.by_id.update(
            {
                "in-low1": sw("in-low1", "LOW", 94, 1900),
                "in-high1": sw("in-high1", "HIGH", 100, 2100),
                "in-low2": sw("in-low2", "LOW", 96, 2300),
                "in-high2": sw("in-high2", "HIGH", 103, 2500),
            }
        )
        result = resolve_range_chain(index, "range-1", 5400)
        self.assertEqual(result["state"], "OBJECTIVE_FAIL")
        self.assertEqual(result["reason"], "RANGE_INTERNAL_TREND_STRUCTURE")

    def test_both_side_deviation_same_bar_stays_unknown(self):
        index = valid_index()
        index.bars[1] = b(2700, 100, 115, 85, 100)
        result = resolve_range_chain(index, "range-1", 5400)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_RANGE_BOTH_SIDE_DEVIATION")


if __name__ == "__main__":
    unittest.main()
