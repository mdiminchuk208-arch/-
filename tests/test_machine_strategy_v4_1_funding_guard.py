from __future__ import annotations

import unittest

from machine_strategy_v4_1_contracts import V41Reject
from machine_strategy_v4_1_funding_guard import (
    adverse_funding_witness,
    assert_historical_funding_blocked,
    synthetic_capability,
)


class TestV41FundingGuard(unittest.TestCase):
    def test_unregistered_fixture_is_rejected(self):
        with self.assertRaisesRegex(V41Reject, "UNREGISTERED_SYNTHETIC_FUNDING_FIXTURE"):
            synthetic_capability("NOT_REGISTERED")

    def test_long_positive_funding_uses_adverse_negative_cash(self):
        cap = synthetic_capability("LONG_POSITIVE_FUNDING")
        result = adverse_funding_witness(
            cap,
            direction="LONG",
            fill_time_bounds=(100, 100),
            exit_time_bounds=(300, 300),
            settlements=[(200, "0.001", "100")],
            quantity_base="1",
        )
        self.assertEqual(result["funding_cash"], "-0.100")
        self.assertEqual(result["settlements_included"], [200])
        self.assertFalse(result["historical_source_used"])

    def test_short_positive_funding_never_forces_favorable_credit(self):
        cap = synthetic_capability("SHORT_POSITIVE_FUNDING")
        result = adverse_funding_witness(
            cap,
            direction="SHORT",
            fill_time_bounds=(200, 200),
            exit_time_bounds=(300, 300),
            settlements=[(200, "0.001", "100")],
            quantity_base="1",
        )
        # The coherent witness may place the modeled fill after the same-timestamp
        # settlement, avoiding a favorable funding credit under adverse selection.
        self.assertEqual(result["funding_cash"], "0")
        self.assertEqual(result["settlements_included"], [])

    def test_same_timestamp_boundary_uses_explicit_slot_order(self):
        cap = synthetic_capability("SAME_TIMESTAMP_BOUNDARY")
        result = adverse_funding_witness(
            cap,
            direction="LONG",
            fill_time_bounds=(200, 200),
            exit_time_bounds=(300, 300),
            settlements=[(200, "0.001", "100"), (300, "0.001", "100")],
            quantity_base="1",
        )
        self.assertIn(result["model_fill_event_slot"][1], (-1, 1))
        self.assertIn(result["model_exit_event_slot"][1], (-1, 1))
        self.assertEqual(result["precision"], 80)

    def test_historical_funding_is_unconditionally_blocked_in_readiness(self):
        with self.assertRaisesRegex(V41Reject, "HISTORICAL_V4_1_FUNDING_NOT_AUTHORIZED"):
            assert_historical_funding_blocked()


if __name__ == "__main__":
    unittest.main()
