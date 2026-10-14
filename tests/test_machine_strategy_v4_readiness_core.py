import unittest
from decimal import Decimal

from machine_strategy_v4_readiness_core import (
    GateTelemetry,
    V4Reject,
    V4Wait,
    classify_approach,
    executable_plan,
    pending_alive,
    planned_payoff_gate,
    target_lifecycle_ok,
)


class V4ReadinessCoreTests(unittest.TestCase):
    def test_clean_and_corrective_are_symmetric(self):
        clean = classify_approach(
            direction="LONG",
            reaction_at=10,
            selected_conf={"id": "c", "known_at": 20, "direction": "LONG"},
            opposing_events=[],
            decision_at=30,
            data_complete=True,
            structurally_retired=False,
        )
        self.assertEqual(clean["state"], "APPROACH_CLEAN")
        corrective = classify_approach(
            direction="SHORT",
            reaction_at=10,
            selected_conf={"id": "c", "known_at": 25, "direction": "SHORT"},
            opposing_events=[{"id": "x", "known_at": 20}],
            decision_at=30,
            data_complete=True,
            structurally_retired=False,
        )
        self.assertEqual(corrective["state"], "APPROACH_CORRECTIVE")

    def test_later_opposite_waits(self):
        with self.assertRaisesRegex(V4Wait, "WAIT_RECONFIRMATION"):
            classify_approach(
                direction="LONG",
                reaction_at=10,
                selected_conf={"id": "c", "known_at": 20, "direction": "LONG"},
                opposing_events=[{"id": "x", "known_at": 21}],
                decision_at=30,
                data_complete=True,
                structurally_retired=False,
            )

    def test_completed_fta_mirror(self):
        with self.assertRaisesRegex(V4Reject, "FTA_ALREADY_COMPLETED"):
            target_lifecycle_ok(
                direction="LONG",
                completed_close="110",
                raw_fta="110",
                inward_target="109",
            )
        with self.assertRaisesRegex(V4Reject, "FTA_ALREADY_COMPLETED"):
            target_lifecycle_ok(
                direction="SHORT",
                completed_close="90",
                raw_fta="90",
                inward_target="91",
            )

    def test_zero_width_range_gets_one_grid_envelope(self):
        plan = executable_plan(
            direction="LONG",
            raw_entry="100",
            protective_boundary="98",
            raw_fta="104",
            structural_low="100",
            structural_high="100",
            tick="1",
        )
        self.assertEqual(plan["entry"], Decimal(100))
        self.assertEqual(plan["exec_low"], Decimal(99))
        self.assertEqual(plan["exec_high"], Decimal(101))

    def test_payoff_gate_pass_and_fail(self):
        result = planned_payoff_gate(
            direction="LONG", entry="100", stop="98", target="103"
        )
        self.assertGreaterEqual(result["ratio"], Decimal(1))
        with self.assertRaisesRegex(V4Reject, "REJECT_INSUFFICIENT_STRUCTURAL_PAYOFF"):
            planned_payoff_gate(direction="LONG", entry="100", stop="98", target="101")

    def test_half_open_parent_deadline(self):
        self.assertTrue(
            pending_alive(
                formation_known_at=100,
                bar_open_at=100 + 57599,
                lifecycle_flags={},
            )
        )
        self.assertFalse(
            pending_alive(
                formation_known_at=100,
                bar_open_at=100 + 57600,
                lifecycle_flags={},
            )
        )

    def test_telemetry_blocks_outcome_fields(self):
        telemetry = GateTelemetry("f", "p", "SFP", "LONG", 100)
        telemetry.emit({"gate": "context", "evaluated_at": 200, "status": "PASS"})
        with self.assertRaisesRegex(V4Reject, "REJECT_OUTCOME_FIELD_IN_TELEMETRY"):
            telemetry.emit(
                {"gate": "x", "evaluated_at": 201, "status": "PASS", "pnl": "1"}
            )


if __name__ == "__main__":
    unittest.main()
