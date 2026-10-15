from __future__ import annotations

import unittest
from decimal import Decimal

from original_v1_1_financial_data import Bar
from source_strategy_v1_ob_entry_resolver import resolve_ob_entry_chain


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


def fvg():
    return {
        "id": "new-poi",
        "kind": "FVG",
        "known_at": 8000,
        "completed_at": 8000,
        "tf": 15,
        "source_validated": True,
        "payload": {"direction": "LONG", "low": "101", "high": "102", "bar_starts": [6900, 7800, 8700]},
    }


def formation(setup_tf=60):
    return {
        "state": "SOURCE_FORMATION_READY",
        "branch": "OB_CONSERVATIVE",
        "direction": "LONG",
        "setup_tf": setup_tf,
        "decision_at": 3000,
        "ob_id": "ob-long",
        "zone": {"low": "90", "high": "100", "body_low": "94", "body_high": "99"},
        "source_extreme": "88",
        "technical_normalization_ids": ["TN_OB_BODY_001"],
        "trade_entry_allowed": False,
    }


def valid_m15(include_poi=True):
    objects = [
        sw("h1", "HIGH", 110, 3500),
        sw("l1", "LOW", 105, 4000),
        sw("h2", "HIGH", 108, 4500),
        sw("l2", "LOW", 102, 5000),
    ]
    if include_poi:
        objects.append(fvg())
    reaction = b(6000, 103, 104, 95, 101)
    bos = b(6900, 105, 110, 104, 109)
    return FakeIndex([reaction, bos], objects)


class TestSourceStrategyV1ObEntryResolver(unittest.TestCase):
    def test_full_ob_chain_requires_corrective_structure_reaction_bos_and_new_poi(self):
        result = resolve_ob_entry_chain(formation(), valid_m15(), 9000)
        self.assertEqual(result["state"], "SOURCE_CHAIN_READY")
        self.assertEqual(result["m15_bos_id"] is not None, True)
        self.assertEqual(result["entry_poi_id"], "new-poi")
        self.assertEqual(D(result["stop_anchor"]["price"]), D("88"))
        self.assertIn("TN_OB_APPROACH_001", result["technical_normalization_ids"])
        self.assertIn("TN_OB_REACTION_001", result["technical_normalization_ids"])
        self.assertFalse(result["trade_entry_allowed"])

    def test_m15_ob_needing_lower_refinement_is_wait_not_reject(self):
        result = resolve_ob_entry_chain(formation(setup_tf=15), valid_m15(), 9000)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_NO_AVAILABLE_LOWER_TF")

    def test_no_corrective_structure_is_normalization_fail(self):
        m15 = valid_m15()
        m15.by_id = {"new-poi": m15.by_id["new-poi"]}
        result = resolve_ob_entry_chain(formation(), m15, 9000)
        self.assertEqual(result["state"], "NORMALIZATION_FAIL")
        self.assertEqual(result["reason"], "OB_SMOOTH_STRUCTURAL_APPROACH_FAIL")

    def test_missing_new_poi_stays_unknown(self):
        result = resolve_ob_entry_chain(formation(), valid_m15(include_poi=False), 9000)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_NEW_POI_AFTER_BOS")


if __name__ == "__main__":
    unittest.main()
