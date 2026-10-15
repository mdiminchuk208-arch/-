from __future__ import annotations

import unittest
from decimal import Decimal

from original_v1_1_financial_data import Bar
from source_strategy_v1_stb_resolver import resolve_stb_chain
from source_strategy_v1_structure_resolver import first_directional_bos, latest_source_structure


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


def long_swings():
    return [
        sw("l1", "LOW", 90, 1000),
        sw("h1", "HIGH", 100, 1200),
        sw("l2", "LOW", 95, 1400),
        sw("h2", "HIGH", 110, 1600),
    ]


def raw_stb():
    return {
        "id": "stb-1",
        "kind": "STB",
        "symbol": "BTCUSDT",
        "tf": 15,
        "known_at": 3800,
        "completed_at": 3800,
        "source_validated": False,
        "payload": {
            "level_id": "l2",
            "direction": "LONG",
            "source_bar_start": 2000,
            "engulf_bar_start": 2900,
            "low": "90",
            "high": "102",
            "body_low": "94",
            "body_high": "100",
            "engulf_low": "89",
            "engulf_high": "112"
        },
    }


class TestSourceStrategyV1StbResolver(unittest.TestCase):
    def valid_index(self, with_bos=True):
        source = b(2000, 100, 102, 90, 94)
        engulf = b(2900, 94, 112, 89, 108)
        later = b(3800, 108, 113, 107, 111 if with_bos else 109)
        return FakeIndex([source, engulf, later], [*long_swings(), raw_stb()])

    def test_structure_is_resolved_directly_from_source_swings(self):
        structure = latest_source_structure(self.valid_index(), 2000)
        self.assertIsNotNone(structure)
        self.assertEqual(structure["payload"]["direction"], "LONG")
        self.assertEqual(structure["payload"]["protected_endpoint_id"], "l2")

    def test_directional_bos_uses_close_not_wick(self):
        index = self.valid_index(with_bos=True)
        bos = first_directional_bos(index, "LONG", 3800, 4700)
        self.assertIsNotNone(bos)
        self.assertEqual(bos["payload"]["broken_swing_id"], "h2")
        self.assertEqual(bos["known_at"], 4700)

    def test_stb_chain_resolves_source_rules_and_midpoint_entry(self):
        result = resolve_stb_chain(self.valid_index(), "stb-1", 4700)
        self.assertEqual(result["state"], "SOURCE_CHAIN_READY")
        self.assertEqual(result["branch"], "STB_BTS")
        self.assertEqual(result["direction"], "LONG")
        self.assertEqual(result["entry"]["kind"], "STB_MIDPOINT")
        self.assertEqual(D(result["entry"]["price"]), D("96"))
        self.assertEqual(D(result["stop_anchor"]["price"]), D("90"))
        self.assertFalse(result["trade_entry_allowed"])

    def test_missing_bos_stays_unknown(self):
        result = resolve_stb_chain(self.valid_index(with_bos=False), "stb-1", 4700)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_STB_BOS_OR_CONFIRMATION")

    def test_missing_structure_stays_unknown(self):
        index = self.valid_index()
        index.by_id = {key: value for key, value in index.by_id.items() if key in {"l2", "stb-1"}}
        result = resolve_stb_chain(index, "stb-1", 4700)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_STB_MARKET_STRUCTURE")

    def test_raid_or_engulf_failure_is_source_fail(self):
        index = self.valid_index()
        bad_source = b(2000, 100, 102, 96, 98)
        index.bars[0] = bad_source
        result = resolve_stb_chain(index, "stb-1", 4700)
        self.assertEqual(result["state"], "OBJECTIVE_FAIL")
        self.assertEqual(result["reason"], "STB_RAID_OR_FULL_ENGULF_FAIL")


if __name__ == "__main__":
    unittest.main()
