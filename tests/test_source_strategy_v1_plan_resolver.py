from __future__ import annotations

import unittest
from decimal import Decimal

from original_v1_1_financial_data import Bar
from source_strategy_v1_plan_resolver import assemble_source_plan, atr_sma14_from_pattern


D = Decimal


class FakeIndex:
    def __init__(self, bars=(), objects=()):
        self.bars = list(bars)
        self.by_id = {obj["id"]: obj for obj in objects}


def b(start, o, h, l, c):
    return Bar(start, start + 900, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def poi(identifier, direction, low, high, known_at=1000, tf=60):
    return {
        "id": identifier,
        "kind": "OB",
        "tf": tf,
        "known_at": known_at,
        "completed_at": known_at,
        "source_validated": True,
        "payload": {"direction": direction, "low": str(low), "high": str(high)},
        "evidence": "source target",
    }


class TestSourceStrategyV1PlanResolver(unittest.TestCase):
    def test_stb_plan_adds_nearest_fta_without_execution(self):
        chain = {
            "state": "SOURCE_CHAIN_READY",
            "branch": "STB_BTS",
            "direction": "LONG",
            "setup_tf": 60,
            "decision_at": 2000,
            "stb_id": "stb",
            "entry": {"price": "100"},
            "stop_anchor": {"kind": "MANIPULATION_RAID_EXTREME", "price": "95"},
            "user_resolution_ids": ["U2", "U3"],
        }
        indexes = {60: FakeIndex(objects=[poi("near", "SHORT", 110, 115), poi("far", "SHORT", 125, 130)])}
        plan = assemble_source_plan(chain, indexes)
        self.assertEqual(plan["state"], "SOURCE_PLAN_READY_PRE_VENUE")
        self.assertEqual(plan["entry"]["price_pre_tick"], "100")
        self.assertEqual(plan["target"]["price"], "110")
        self.assertFalse(plan["financial_outcomes_generated"])
        self.assertFalse(plan["trade_entry_allowed"])

    def test_range_uses_frozen_range_target_not_generic_fta(self):
        chain = {
            "state": "SOURCE_CHAIN_READY",
            "branch": "RANGE_CONSERVATIVE",
            "direction": "LONG",
            "setup_tf": 15,
            "decision_at": 2000,
            "range_id": "r",
            "entry": {"price": "90"},
            "stop_anchor": {"kind": "DEVIATION_INVALIDATION_EXTREME", "price": "85"},
            "target_plan": {"kind": "RANGE_80_20_SAME_ZONE", "opposite_boundary": "110", "allocation": ["0.80", "0.20"]},
            "user_resolution_ids": ["U1", "U2", "U3"],
        }
        plan = assemble_source_plan(chain, {})
        self.assertEqual(plan["state"], "SOURCE_PLAN_READY_PRE_VENUE")
        self.assertEqual(plan["target"]["price_pre_tick"], "110")
        self.assertEqual(plan["target_inventory_id"], None)

    def test_missing_fta_stays_unknown(self):
        chain = {
            "state": "SOURCE_CHAIN_READY",
            "branch": "STB_BTS",
            "direction": "SHORT",
            "setup_tf": 60,
            "decision_at": 2000,
            "stb_id": "stb",
            "entry": {"price": "100"},
            "stop_anchor": {"kind": "MANIPULATION_RAID_EXTREME", "price": "105"},
            "user_resolution_ids": ["U2", "U3"],
        }
        plan = assemble_source_plan(chain, {})
        self.assertEqual(plan["state"], "UNKNOWN")
        self.assertEqual(plan["reason"], "WAIT_CONTEXTUAL_FTA")

    def test_atr14_uses_15_contiguous_bars_and_14_true_ranges(self):
        bars = []
        for i in range(15):
            start = i * 900
            bars.append(b(start, 100, 102, 98, 100))
        index = FakeIndex(bars=bars)
        atr = atr_sma14_from_pattern(index, 14 * 900)
        self.assertEqual(atr, D("4"))

    def test_sfp_plan_uses_atr_stop_from_pattern_extreme(self):
        bars = [b(i * 900, 100, 102, 98, 100) for i in range(14)]
        bars.append(b(14 * 900, 100, 103, 95, 101))
        sfp = {
            "id": "sfp",
            "kind": "SFP",
            "tf": 60,
            "known_at": 14 * 900 + 900,
            "source_validated": True,
            "payload": {"direction": "LONG", "bar_start": 14 * 900, "low": "95", "high": "103"},
        }
        parent = FakeIndex(bars=bars, objects=[sfp])
        chain = {
            "state": "SOURCE_CHAIN_READY",
            "branch": "SFP",
            "direction": "LONG",
            "setup_tf": 60,
            "decision_at": 20000,
            "sfp_id": "sfp",
            "entry_poi": {"kind": "FVG", "low": "100", "high": "101"},
            "user_resolution_ids": ["U3", "U4"],
        }
        indexes = {60: FakeIndex(objects=[poi("target", "SHORT", 110, 115, known_at=18000)])}
        plan = assemble_source_plan(chain, indexes, parent_index=parent)
        self.assertEqual(plan["state"], "SOURCE_PLAN_READY_PRE_VENUE")
        self.assertEqual(plan["entry"]["price_pre_tick"], "101")
        self.assertEqual(D(plan["stop"]["pattern_extreme"]), D("95"))
        self.assertLess(D(plan["stop"]["price"]), D("95"))

    def test_nonprotective_stop_is_rejected(self):
        chain = {
            "state": "SOURCE_CHAIN_READY",
            "branch": "STB_BTS",
            "direction": "LONG",
            "setup_tf": 60,
            "decision_at": 2000,
            "stb_id": "x",
            "entry": {"price": "100"},
            "stop_anchor": {"price": "101"},
        }
        result = assemble_source_plan(chain, {})
        self.assertEqual(result["state"], "OBJECTIVE_FAIL")
        self.assertEqual(result["reason"], "STOP_NOT_PROTECTIVE")


if __name__ == "__main__":
    unittest.main()
