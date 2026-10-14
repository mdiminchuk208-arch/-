"""Registered synthetic execution and checkpoint guard tests. No historical outcomes."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import machine_strategy_v3_contracts as inherited
import machine_strategy_v4_guarded_runner as runner
from machine_strategy_v4_lifecycle import SourceLifecycle
from machine_strategy_v4_readiness_core import GateTelemetry, V4Reject, V4Wait


class V4RunnerTests(unittest.TestCase):
    def test_all_families_both_directions_use_nine_registered_states(self):
        for direction in ("long", "short"):
            for family in ("sfp", "ob", "breaker", "stb", "range"):
                with self.subTest(direction=direction, family=family):
                    result = runner.evaluate_fixture(f"{direction}_{family}_target")
                    self.assertEqual(result["status"], "CLOSED")
                    self.assertEqual(len(result["scenario_states"]), 9)
                    self.assertFalse(result["trade_entry_allowed"])
                    for state in result["scenario_states"]:
                        self.assertEqual(state["fixed_R_unit"], result["fixed_R_unit"])
                        self.assertEqual(
                            state["columns"]["base"]["gross_cash"],
                            state["columns"]["doubled"]["gross_cash"],
                        )

    def test_funding_signed_minimum_preserves_same_timestamp_witness(self):
        for direction in ("long", "short"):
            result = runner.evaluate_fixture(f"{direction}_funding")
            for state in result["scenario_states"]:
                expected = -Decimal("0.1") * state["quantity_base"]
                self.assertEqual(state["columns"]["base"]["funding_cash"], expected)
                self.assertEqual(
                    state["columns"]["base"]["funding_cash"],
                    state["columns"]["doubled"]["funding_cash"],
                )
                witness = state["funding_timing_witness"]
                self.assertLessEqual(
                    witness["model_fill_event_slot"], witness["model_exit_event_slot"]
                )

    def test_native_sfp_body_exit_is_mirrored(self):
        for direction in ("long", "short"):
            result = runner.evaluate_fixture(f"{direction}_sfp_body")
            self.assertTrue(
                all(
                    s["exit_reason"] == "SFP_PATTERN_BODY_INVALIDATION"
                    for s in result["scenario_states"]
                )
            )

    def test_current_close_cannot_cancel_same_bar_fill_or_create_context_exit(self):
        result = runner.evaluate_fixture("long_postfill_context")
        self.assertEqual(result["status"], "CLOSED")
        self.assertTrue(
            all(s["exit_reason"] == "STRUCTURAL_FTA" for s in result["scenario_states"])
        )

    def test_pending_contact_retires_without_imputed_cash(self):
        result = runner.evaluate_fixture("long_pending_retire")
        self.assertEqual(result["status"], "NO_FILL")
        for state in result["scenario_states"]:
            self.assertEqual(state["status"], "RETIRED_PENDING")
            self.assertNotIn("columns", state)

    def test_gap_invalidates_before_pending_contact(self):
        result = runner.evaluate_fixture("long_gap")
        self.assertTrue(
            all(
                s["status"] == "GAP_INVALIDATED_BEFORE_FILL"
                for s in result["scenario_states"]
            )
        )

    def test_wick_ambiguity_never_imputes_closed(self):
        result = runner.evaluate_fixture("long_wick_ambiguity")
        self.assertTrue(result["qualification_stop"])
        self.assertTrue(
            all(
                s["status"] == "WAIT_INTRABAR_ORDER" and "columns" not in s
                for s in result["scenario_states"]
            )
        )

    def test_data_gap_keeps_fill_evidence_unknown(self):
        result = runner.evaluate_fixture("long_data_gap")
        self.assertTrue(result["qualification_stop"])
        for state in result["scenario_states"]:
            self.assertEqual(state["status"], "UNKNOWN_DATA_GAP")
            self.assertIn("fill_price", state)
            self.assertNotIn("columns", state)

    def test_pending_eof_is_not_closed_or_cash_zero(self):
        result = runner.evaluate_fixture("long_pending_eof")
        self.assertTrue(
            all(
                s["status"] == "ORDER_CENSORED_EOF" and "columns" not in s
                for s in result["scenario_states"]
            )
        )

    def test_parent_deadline_equality_does_not_fill(self):
        result = runner.evaluate_fixture("long_deadline")
        self.assertTrue(
            all(
                s["status"] == "UNFILLED_EXPIRED" and "fill_price" not in s
                for s in result["scenario_states"]
            )
        )

    def test_closed_nonce_cannot_be_fabricated_from_context_dictionary(self):
        token = runner._ACTIVE.set({"marker": object(), "allowed_inputs": {"anything"}})
        try:
            with self.assertRaisesRegex(
                runner.FinancialBlocked, "NO_AUTHORIZED_V4_SCOPE"
            ):
                runner._drive_case({}, [], [], None)
        finally:
            runner._ACTIVE.reset(token)

    def test_registered_nonce_cannot_accept_arbitrary_prices(self):
        nonce = runner._fixture_issue("long_ob_target")
        token = runner._ACTIVE.set(nonce)
        try:
            order, bars, rows, _ = runner.fixture("long_ob_target")
            bars[0]["open"] = "99999"
            with self.assertRaisesRegex(
                runner.FinancialBlocked, "INPUTS_NOT_REGISTERED"
            ):
                runner._drive_case(order, bars, rows, None)
        finally:
            runner._ACTIVE.reset(token)
            runner._fixture_revoke(nonce)

    def test_unregistered_fixture_and_direct_cash_block_before_calculation(self):
        with self.assertRaises(runner.FinancialBlocked):
            runner.evaluate_fixture("arbitrary-history")
        with self.assertRaises(runner.FinancialBlocked):
            runner._cash({}, [])
        with self.assertRaises(runner.FinancialBlocked):
            runner._funding_min({}, [])

    def test_self_consistent_authorization_file_never_enables_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "authorization.json"
            p.write_text(
                '{"decision":"MACHINE_STRATEGY_V4_FIRST_FINANCIAL_AUTHORIZED"}'
            )
            with self.assertRaisesRegex(
                runner.FinancialBlocked, "HISTORICAL_FINANCIAL_GATE_NOT_AUTHORIZED"
            ):
                runner.evaluate_historical_catalog(
                    [],
                    {},
                    [],
                    implementation_manifest_sha256="0" * 64,
                    authorization_path=p,
                    authorization_sha256=runner.fingerprint(p.read_text()),
                )

    def test_repeating_R_uses_exact_inherited_ledger_precision(self):
        state = runner.evaluate_fixture("long_ob_target")["scenario_states"][0]
        self.assertGreater(len(str(state["columns"]["base"]["net_R"])), 50)
        self.assertEqual(
            state["columns"]["base"]["net_R"],
            runner.evaluate_fixture("long_ob_target")["scenario_states"][0]["columns"][
                "base"
            ]["net_R"],
        )

    def test_source_consumption_clock_gap_changes_synthetic_disposition(self):
        zone = {"low": "100", "high": "101", "known_at": 3600, "consumed_at": None}
        native = {
            "start": 3600,
            "end": 7200,
            "open": "100",
            "high": "102",
            "low": "98",
            "close": "101",
        }
        origin_eligible = inherited.first_test(zone, native, eligibility_at=3600)
        later_refinement_eligible = inherited.first_test(
            zone, native, eligibility_at=9000
        )
        self.assertEqual(origin_eligible["consumed_at"], 7200)
        self.assertIsNone(later_refinement_eligible["consumed_at"])
        # This diagnoses a missing frozen policy, never chooses a profitable clock.
        for family in ("STB", "BREAKER", "RANGE"):
            with self.assertRaisesRegex(
                V4Wait, "WAIT_VERSIONED_SELECTED_POI_FIRST_TEST_CONTRACT"
            ):
                SourceLifecycle(
                    {
                        "branch": family,
                        "first_test_mapping_status": "UNRESOLVED_FROZEN_DESIGN",
                    },
                    {},
                )

    def test_telemetry_snapshot_is_detached_and_future_or_nested_outcome_fails(self):
        sink = GateTelemetry("f", "p", "SFP", "LONG", 0)
        item = {"gate": "context", "status": "PASS", "evaluated_at": 900}
        sink.emit(item)
        item["status"] = "LOSS"
        snapshot = sink.snapshot()
        snapshot["events"][0]["event_type"] = "LOSS"
        self.assertNotEqual(sink.snapshot()["events"][0]["event_type"], "LOSS")
        with self.assertRaises(V4Reject):
            sink.emit(
                {"gate": "a", "status": "PASS", "evaluated_at": 900, "x": {"pnl": "1"}}
            )
        with self.assertRaises(V4Reject):
            sink.emit(
                {
                    "gate_name": "a",
                    "event_type": "PASS",
                    "known_at": 901,
                    "decision_cutoff": 900,
                }
            )


if __name__ == "__main__":
    unittest.main()
