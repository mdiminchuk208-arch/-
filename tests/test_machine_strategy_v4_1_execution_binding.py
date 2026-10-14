from __future__ import annotations

import unittest

from machine_strategy_v4_1_execution_binding import all_scenario_plans


class TestV41ExecutionBinding(unittest.TestCase):
    def order(self, *, direction="LONG"):
        if direction == "LONG":
            raw_entry = "100"
            boundary = "90"
            fta = "130"
            zone = {"low": "99.5", "high": "100.5"}
            completed = "95"
        else:
            raw_entry = "100"
            boundary = "110"
            fta = "70"
            zone = {"low": "99.5", "high": "100.5"}
            completed = "105"
        return (
            {
                "version": "MACHINE_STRATEGY_v4.1",
                "product": "BTC-USDT-SWAP",
                "case_id": f"synthetic-{direction.lower()}",
                "direction": direction,
                "raw_entry": raw_entry,
                "protective_boundary": boundary,
                "raw_fta_price": fta,
                "structural_entry_zone": zone,
                "nearest_fta_id": "fta-1",
                "fixed_R_unit": "10.152",
            },
            completed,
        )

    def test_retains_all_nine_scenarios_long(self):
        order, completed = self.order(direction="LONG")
        plans = all_scenario_plans(order, completed_close=completed)
        self.assertEqual(len(plans), 9)
        self.assertEqual(plans[0]["scenario_id"], "P01_Q001")
        self.assertEqual(len({row["scenario_id"] for row in plans}), 9)
        self.assertTrue(all(row["trade_entry_allowed"] is False for row in plans))

    def test_retains_all_nine_scenarios_short(self):
        order, completed = self.order(direction="SHORT")
        plans = all_scenario_plans(order, completed_close=completed)
        self.assertEqual(len(plans), 9)
        self.assertEqual(plans[0]["scenario_id"], "P01_Q001")
        self.assertEqual(len({row["scenario_id"] for row in plans}), 9)

    def test_completed_fta_is_retained_as_ineligible_not_dropped(self):
        order, _ = self.order(direction="LONG")
        plans = all_scenario_plans(order, completed_close="130")
        self.assertEqual(len(plans), 9)
        self.assertTrue(all(row["status"] == "INELIGIBLE" for row in plans))
        self.assertTrue(all(row["reason"] == "FTA_ALREADY_COMPLETED" for row in plans))

    def test_design_values_are_serialized_strings_for_ledger_transport(self):
        order, completed = self.order(direction="LONG")
        plans = all_scenario_plans(order, completed_close=completed)
        eligible = [row for row in plans if row["status"] == "ELIGIBLE_PENDING"]
        self.assertTrue(eligible)
        row = eligible[0]
        for key in ("entry", "stop", "target", "quantity_contracts", "quantity_base"):
            self.assertIsInstance(row[key], str)
        for key in ("planned_stop_unit", "net_target_doubled", "ratio"):
            self.assertIsInstance(row["planned_payoff"][key], str)
        self.assertEqual(row["decimal_scope"], "DESIGN_PRECISION_50_HALF_EVEN")
        self.assertFalse(row["ledger_recompute_geometry_allowed"])

    def test_wrong_version_cannot_enter_scenario_path(self):
        order, completed = self.order(direction="LONG")
        order["version"] = "MACHINE_STRATEGY_v4"
        plans = all_scenario_plans(order, completed_close=completed)
        self.assertEqual(len(plans), 9)
        self.assertTrue(all(row["status"] == "INELIGIBLE" for row in plans))
        self.assertTrue(all(row["reason"] == "REJECT_V4_1_ORDER_VERSION" for row in plans))


if __name__ == "__main__":
    unittest.main()
