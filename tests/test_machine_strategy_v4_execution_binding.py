import unittest

from machine_strategy_v4_execution_binding import all_scenario_plans


class V4ExecutionBindingTests(unittest.TestCase):
    def test_all_nine_scenarios_are_retained(self):
        order = {
            "version": "MACHINE_STRATEGY_v4",
            "product": "BTC-USDT-SWAP",
            "case_id": "synthetic-case",
            "direction": "LONG",
            "raw_entry": "100",
            "protective_boundary": "90",
            "raw_fta_price": "130",
            "structural_entry_zone": {"low": "99.5", "high": "100.5"},
        }
        plans = all_scenario_plans(order, completed_close="95")
        self.assertEqual(len(plans), 9)
        self.assertEqual(plans[0]["scenario_id"], "P01_Q001")
        self.assertEqual(len({plan["scenario_id"] for plan in plans}), 9)
        self.assertTrue(all(plan["trade_entry_allowed"] is False for plan in plans))

    def test_completed_target_does_not_disappear_case(self):
        order = {
            "version": "MACHINE_STRATEGY_v4",
            "product": "BTC-USDT-SWAP",
            "case_id": "synthetic-case",
            "direction": "LONG",
            "raw_entry": "100",
            "protective_boundary": "90",
            "raw_fta_price": "130",
            "structural_entry_zone": {"low": "99.5", "high": "100.5"},
        }
        plans = all_scenario_plans(order, completed_close="130")
        self.assertEqual(len(plans), 9)
        self.assertTrue(all(plan["status"] == "INELIGIBLE" for plan in plans))
        self.assertTrue(all(plan["reason"] == "FTA_ALREADY_COMPLETED" for plan in plans))


if __name__ == "__main__":
    unittest.main()
