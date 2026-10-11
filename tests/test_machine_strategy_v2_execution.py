"""Independent event-order and normalized cost accounting contracts."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from machine_strategy_v2_execution import execute, stats
from test_original_v1_1_evidence_adapter_v2 import bars


def case(direction="LONG"):
    return {
        "case_id": "case",
        "symbol": "BTCUSDT",
        "branch": "OB",
        "setup_tf": 60,
        "direction": direction,
        "decision_at": 0,
        "order_expires_at": 3600,
        "confirmation_known_at": 0,
        "FTA_known_at": 0,
        "theoretical_entry": "10",
        "fixed_initial_stop": "9" if direction == "LONG" else "11",
        "theoretical_target": "12" if direction == "LONG" else "8",
        "entry_poi_id": "poi",
        "stop_anchor": "9.5",
        "trade_entry_allowed": False,
    }


class MachineExecutionTests(unittest.TestCase):
    def run_case(self, values, c=None):
        return execute(c or case(), {15: bars(values, tf=15)})

    def test_open_fill_then_single_target(self):
        r = self.run_case([(10, 12, 9.5, 11)])
        self.assertEqual(r["status"], "CLOSED")
        self.assertTrue(r["WIN"])
        self.assertEqual(r["exit_reason"], "STRUCTURAL_FTA")

    def test_dual_hit_never_ordered_arbitrarily(self):
        r = self.run_case([(10, 13, 8, 11)])
        self.assertEqual(r["status"], "WAIT_INTRABAR_ORDER")
        self.assertIsNone(r["Net_R"])

    def test_wick_fill_and_target_can_precede_entry(self):
        r = self.run_case([(11, 13, 9.5, 10)])
        self.assertEqual(r["status"], "WAIT_INTRABAR_ORDER")

    def test_wick_fill_stop_only_is_ordered_crossing(self):
        r = self.run_case([(11, 11.5, 8, 10)])
        self.assertEqual(r["exit_reason"], "FIXED_INITIAL_STOP")
        self.assertTrue(r["LOSS"])

    def test_gap_beyond_stop_before_fill_rejects(self):
        r = self.run_case([(8, 10, 7, 9)])
        self.assertEqual(r["status"], "GAP_INVALIDATED_BEFORE_FILL")
        self.assertFalse(r["filled"])

    def test_open_gap_price_improvement_theoretical(self):
        r = self.run_case([(9.5, 10, 9.2, 9.7), (9.7, 12.5, 9.2, 12)])
        self.assertEqual(r["fill_price"], "9.5")
        self.assertEqual(r["initial_price_risk"], "0.5")

    def test_post_fill_stop_gap_at_open(self):
        r = self.run_case([(10, 11, 9.5, 10), (8, 9, 7, 8)])
        self.assertEqual(r["exit_reason"], "STOP_GAP_OPEN")
        self.assertEqual(r["exit_price"], "8")

    def test_short_symmetric_accounting(self):
        r = self.run_case([(10, 10.5, 7.5, 8)], case("SHORT"))
        self.assertTrue(r["WIN"])
        self.assertEqual(r["Gross_R"], "2")

    def test_unfilled_order_expires(self):
        r = self.run_case([(11, 11.5, 10.5, 11)] * 5)
        self.assertEqual(r["status"], "UNFILLED_EXPIRED")
        self.assertFalse(r["filled"])

    def test_filled_EOF_not_forced_close(self):
        r = self.run_case([(10, 11, 9.5, 10)])
        self.assertEqual(r["status"], "OPEN_CENSORED_EOF")
        self.assertIsNone(r["Net_R"])

    def test_unfilled_EOF_is_order_censored(self):
        r = self.run_case([(11, 11.5, 10.5, 11)])
        self.assertEqual(r["status"], "ORDER_CENSORED_EOF")

    def test_SFP_body_exit_only_native_close(self):
        c = case()
        c["branch"] = "SFP"
        r = self.run_case(
            [
                (10, 11, 9.4, 9.6),
                (9.6, 10, 9.3, 9.4),
                (9.4, 10, 9.2, 9.3),
                (9.3, 10, 9.1, 9.2),
            ],
            c,
        )
        self.assertEqual(r["exit_reason"], "SFP_PATTERN_BODY_INVALIDATION")
        self.assertEqual(r["exit_at"], 3600)

    def test_funding_unknown_not_zero(self):
        r = self.run_case([(10, 12, 9.5, 11)])
        self.assertIsNone(r["Funding_R"])
        self.assertIn("EXCLUDED", r["funding_treatment"])

    def test_cost_identity_and_sensitivity(self):
        r = self.run_case([(10, 12, 9.5, 11)])
        s = stats([r])
        high = stats([r], cost_multiplier="2")
        self.assertAlmostEqual(
            s["Gross_R"] - s["Fees_R"] - s["Slippage_R"], s["Net_R_ex_funding"]
        )
        self.assertLess(high["Net_R_ex_funding"], s["Net_R_ex_funding"])

    def test_unknown_rows_not_WIN_LOSS_sample(self):
        r = self.run_case([(10, 13, 8, 11)])
        s = stats([r])
        self.assertEqual(s["CLOSED"], 0)
        self.assertIsNone(s["WR_percent"])
        self.assertEqual(s["intrabar_unresolved"], 1)

    def test_invalid_frozen_geometry_rejected(self):
        c = case()
        c["fixed_initial_stop"] = "11"
        with self.assertRaises(ValueError):
            self.run_case([(10, 12, 9.5, 11)], c)

    def test_future_evidence_rejected(self):
        c = case()
        c["FTA_known_at"] = 1
        with self.assertRaises(ValueError):
            self.run_case([(10, 12, 9.5, 11)], c)

    def test_actual_event_future_suffix_does_not_change_closed_trade(self):
        first = self.run_case([(10, 12, 9.5, 11)])
        extended = self.run_case([(10, 12, 9.5, 11), (100, 110, 90, 100)])
        self.assertEqual(first, extended)
