from __future__ import annotations

import unittest
from decimal import Decimal

from original_v1_1_financial_data import Bar
from source_strategy_v1_ob_breaker_resolver import resolve_breaker_from_ob, resolve_ob_formation


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


def raw_ob():
    return {
        "id": "ob-long",
        "kind": "OB",
        "known_at": 3800,
        "completed_at": 3800,
        "tf": 15,
        "source_validated": False,
        "payload": {
            "level_id": "low-95",
            "direction": "LONG",
            "source_bar_start": 2000,
            "engulf_bar_start": 2900,
            "low": "90",
            "high": "102",
            "body_low": "94",
            "body_high": "100",
        },
    }


def fvg(identifier, direction, known_at, starts, low, high):
    return {
        "id": identifier,
        "kind": "FVG",
        "known_at": known_at,
        "completed_at": known_at,
        "tf": 15,
        "source_validated": True,
        "payload": {
            "direction": direction,
            "bar_starts": starts,
            "low": str(low),
            "high": str(high),
        },
    }


def base_index():
    source = b(2000, 100, 102, 90, 94)
    impulse = b(2900, 94, 109, 93, 108)
    bos = b(3800, 108, 113, 106, 111)
    objects = [
        sw("low-95", "LOW", 95, 1000),
        sw("high-110", "HIGH", 110, 1500),
        raw_ob(),
        fvg("fvg-ob", "LONG", 3800, [2000, 2900, 3800], 102.5, 103),
    ]
    return FakeIndex([source, impulse, bos], objects)


class TestSourceStrategyV1ObBreakerResolver(unittest.TestCase):
    def test_ob_source_formation_requires_raid_body_imbalance_and_structure_update(self):
        result = resolve_ob_formation(base_index(), "ob-long", 4700)
        self.assertEqual(result["state"], "SOURCE_FORMATION_READY")
        self.assertEqual(result["branch"], "OB_CONSERVATIVE")
        self.assertEqual(result["raid_level_id"], "low-95")
        self.assertEqual(result["imbalance_id"], "fvg-ob")
        self.assertIn("TN_OB_BODY_001", result["technical_normalization_ids"])
        self.assertFalse(result["trade_entry_allowed"])

    def test_ob_body_wick_normalization_is_separate_from_source_fail(self):
        index = base_index()
        index.bars[0] = b(2000, 96, 110, 90, 95)
        result = resolve_ob_formation(index, "ob-long", 4700)
        self.assertEqual(result["state"], "NORMALIZATION_FAIL")
        self.assertEqual(result["technical_normalization_id"], "TN_OB_BODY_001")

    def test_ob_without_following_imbalance_remains_unknown(self):
        index = base_index()
        index.by_id.pop("fvg-ob")
        result = resolve_ob_formation(index, "ob-long", 4700)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_OB_FOLLOWING_IMBALANCE")

    def test_breaker_rejects_partial_ob_parent(self):
        formation = resolve_ob_formation(base_index(), "ob-long", 4700)
        result = resolve_breaker_from_ob(base_index(), formation, 6000, whole_impulse=None)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_SOURCE_VALID_OB")

    def test_breaker_requires_whole_impulse_evidence(self):
        index = base_index()
        formation = resolve_ob_formation(index, "ob-long", 4700)
        full_ob = {**formation, "state": "SOURCE_CHAIN_READY"}
        result = resolve_breaker_from_ob(index, full_ob, 6000)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_BREAKER_WHOLE_IMPULSE")

    def test_breaker_uses_full_source_ob_and_impulse_extreme(self):
        index = base_index()
        formation = resolve_ob_formation(index, "ob-long", 4700)
        full_ob = {**formation, "state": "SOURCE_CHAIN_READY"}
        break_bar = b(4700, 100, 104, 80, 85)
        index.bars.append(break_bar)
        index.by_id["fvg-break"] = fvg("fvg-break", "SHORT", 5600, [4700], 88, 90)
        whole = {
            "source_validated": True,
            "value": True,
            "known_at": 5600,
            "interval_start": 4700,
            "interval_end": 5600,
            "low": "80",
            "high": "104",
            "evidence": "source-causal whole impulse",
        }
        result = resolve_breaker_from_ob(index, full_ob, 5600, whole_impulse=whole)
        self.assertEqual(result["state"], "SOURCE_FORMATION_READY")
        self.assertEqual(result["branch"], "BREAKER")
        self.assertEqual(result["direction"], "SHORT")
        self.assertEqual(D(result["stop_anchor"]["price"]), D("104"))
        self.assertFalse(result["trade_entry_allowed"])


if __name__ == "__main__":
    unittest.main()
