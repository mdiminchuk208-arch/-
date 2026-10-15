from __future__ import annotations

import unittest
from decimal import Decimal

from original_v1_1_financial_data import Bar
from source_strategy_v1_sfp_resolver import (
    first_m15_bos_after_sfp,
    first_new_source_poi,
    first_pattern_invalidation,
    next_native_open_confirmation,
    resolve_sfp_chain,
    validate_raw_sfp,
)


D = Decimal


class FakeIndex:
    def __init__(self, bars, objects):
        self.bars = bars
        self.by_id = {obj["id"]: obj for obj in objects}


def b(start, end, o, h, l, c):
    return Bar(start, end, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def swing(identifier="swing-100", side="LOW", price="100", known_at=3000, tf=60):
    return {
        "id": identifier,
        "kind": "swing",
        "known_at": known_at,
        "completed_at": known_at,
        "tf": tf,
        "source_validated": True,
        "payload": {"side": side, "price": price},
    }


def sfp(identifier="sfp-long", tf=60):
    return {
        "id": identifier,
        "kind": "SFP",
        "known_at": 7200,
        "completed_at": 7200,
        "tf": tf,
        "source_validated": False,
        "source_rule_ids": ["S_SFP_FORMATION"],
        "payload": {
            "level_id": "swing-100",
            "price": "100",
            "direction": "LONG",
            "bar_start": 3600,
            "low": "95",
            "high": "103",
            "close": "102",
        },
    }


def m15_high():
    return {
        "id": "m15-high",
        "kind": "swing",
        "known_at": 7000,
        "completed_at": 7000,
        "tf": 15,
        "source_validated": True,
        "payload": {"side": "HIGH", "price": "104"},
    }


def fvg(known_at=9000):
    return {
        "id": "fvg-long",
        "kind": "FVG",
        "known_at": known_at,
        "completed_at": known_at,
        "tf": 15,
        "source_validated": True,
        "payload": {"direction": "LONG", "low": "103", "high": "104"},
    }


class TestSourceStrategyV1SfpResolver(unittest.TestCase):
    def parent(self, next_close="102", sfp_tf=60):
        formation = b(3600, 7200, 101, 103, 95, 102)
        next_bar = b(7200, 10800, 101, 103, 94 if next_close == "94" else 99, next_close)
        objects = [swing(tf=sfp_tf), sfp(tf=sfp_tf)]
        return FakeIndex([formation, next_bar], objects)

    def m15(self, with_poi=True, bos_close="104.5", bos_start=7200):
        bos_bar = b(bos_start, bos_start + 900, 102, 105, 101, bos_close)
        objects = [m15_high()]
        if with_poi:
            objects.append(fvg(max(9000, bos_start + 900)))
        return FakeIndex([bos_bar], objects)

    def test_literal_sfp_is_validated_from_sweep_and_reclaim(self):
        parent = self.parent()
        result = validate_raw_sfp(parent, parent.by_id["sfp-long"], 10800)
        self.assertIsNotNone(result)
        self.assertTrue(result["source_validated"])
        self.assertTrue(result["context"]["liquidity_context"])
        self.assertTrue(result["context"]["meaningful_for_this_setup"])

    def test_next_open_confirmation_is_causal(self):
        parent = self.parent()
        validated = validate_raw_sfp(parent, parent.by_id["sfp-long"], 10800)
        self.assertIsNotNone(validated)
        confirmation = next_native_open_confirmation(parent, validated, 10800)
        self.assertTrue(confirmation["passed"])
        self.assertEqual(confirmation["actual_open_time"], 7200)
        self.assertEqual(confirmation["known_at"], 10800)

    def test_m15_bos_uses_preexisting_opposite_swing(self):
        parent = self.parent()
        validated = validate_raw_sfp(parent, parent.by_id["sfp-long"], 10800)
        bos = first_m15_bos_after_sfp(self.m15(), validated, 10800)
        self.assertIsNotNone(bos)
        self.assertEqual(bos["protected_swing_id"], "m15-high")
        self.assertEqual(bos["direction"], "LONG")

    def test_first_new_poi_is_selected_without_future_ranking(self):
        parent = self.parent()
        validated = validate_raw_sfp(parent, parent.by_id["sfp-long"], 10800)
        m15 = self.m15()
        bos = first_m15_bos_after_sfp(m15, validated, 10800)
        poi, reason = first_new_source_poi(m15, bos, "LONG", 10800)
        self.assertIsNone(reason)
        self.assertEqual(poi["id"], "fvg-long")

    def test_full_source_chain_ready_without_financial_fields(self):
        result = resolve_sfp_chain(self.parent(), self.m15(), "sfp-long", 10800)
        self.assertEqual(result["state"], "SOURCE_CHAIN_READY")
        self.assertEqual(result["branch"], "SFP")
        self.assertEqual(result["m15_bos_id"].startswith(""), True)
        self.assertEqual(result["entry_poi_id"], "fvg-long")
        self.assertFalse(result["trade_entry_allowed"])
        for forbidden in ("pnl", "win", "loss", "profit_factor", "fees"):
            self.assertNotIn(forbidden, result)

    def test_pattern_close_beyond_extreme_invalidates_before_late_bos(self):
        parent = self.parent(next_close="94")
        validated = validate_raw_sfp(parent, parent.by_id["sfp-long"], 12000)
        invalidation = first_pattern_invalidation(parent, validated, 12000)
        self.assertIsNotNone(invalidation)
        late_m15 = self.m15(bos_start=10800)
        self.assertIsNone(first_m15_bos_after_sfp(late_m15, validated, 12000, invalidation))
        result = resolve_sfp_chain(parent, late_m15, "sfp-long", 12000)
        self.assertEqual(result["state"], "OBJECTIVE_FAIL")
        self.assertEqual(result["reason"], "SFP_INVALIDATED_BEFORE_M15_BOS")

    def test_missing_new_poi_stays_unknown_not_fail(self):
        result = resolve_sfp_chain(self.parent(), self.m15(with_poi=False), "sfp-long", 10800)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_NEW_POI_AFTER_BOS")

    def test_m15_sfp_lower_tf_gap_is_coverage_wait_not_source_reject(self):
        parent = self.parent(sfp_tf=15)
        result = resolve_sfp_chain(parent, self.m15(), "sfp-long", 10800)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "WAIT_NO_AVAILABLE_LOWER_TF")

    def test_outcome_field_is_rejected(self):
        parent = self.parent()
        parent.by_id["sfp-long"]["outcome"] = "WIN"
        with self.assertRaisesRegex(ValueError, "FINANCIAL_OR_OUTCOME_FIELD_FORBIDDEN"):
            validate_raw_sfp(parent, parent.by_id["sfp-long"], 10800)


if __name__ == "__main__":
    unittest.main()
