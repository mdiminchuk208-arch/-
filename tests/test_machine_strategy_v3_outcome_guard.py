"""Negative historical guard and nonfinancial evidence-boundary tests."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import machine_strategy_v3_guarded_runner as runner
from original_v1_1_financial_data import END, ROOT, START


class OutcomeGuardTests(unittest.TestCase):
    def test_metadata_change_and_data_gap_preserve_unknown_existing_exposure(self):
        for name, status, reason in (
            (
                "filled_epoch_change",
                "UNRESOLVED_METADATA",
                "WAIT_HISTORICAL_TICK_METADATA",
            ),
            ("filled_data_gap", "UNRESOLVED_DATA_GAP", "WAIT_DATA_GAP"),
        ):
            event = runner.run_registered_fixture(name)
            self.assertEqual(event["status"], status)
            self.assertEqual(event["status_before_uncertainty"], "FILLED")
            self.assertEqual(event["uncertainty_reason"], reason)
            self.assertEqual(event["observed_through"], 900)
            self.assertNotIn("exit_price", event)
            self.assertNotIn("amounts", event)

    def test_no_entry_point_can_load_history_during_readiness(self):
        capability = runner._Authorization(
            runner._MARKER,
            ROOT / "docs/machine_strategy_v3_design/freeze_manifest.json",
            "f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0",
            ROOT / "missing_auth.json",
            "a" * 64,
        )
        before = runner.COUNTERS["historical_outcome_evaluations"]
        with (
            patch.object(
                runner, "load_primary", side_effect=AssertionError("History loaded")
            ),
            patch.object(
                runner,
                "observe_m15_bar",
                side_effect=AssertionError("Historical exit called"),
            ),
            patch.object(
                runner,
                "cash_stop_identity",
                side_effect=AssertionError("Historical accounting called"),
            ),
        ):
            for call in (
                lambda: runner.run_historical("BTCUSDT", [], capability),
                lambda: runner._drive_order({}, [], [], capability=capability),
                lambda: runner._closed_record({}, capability),
            ):
                with self.assertRaisesRegex(
                    runner.HistoricalOutcomeBlocked, "IMPLEMENTATION_READINESS_FORBIDS"
                ):
                    call()
        self.assertEqual(before, runner.COUNTERS["historical_outcome_evaluations"])

    def test_registered_fixture_rejects_changed_bars_order_and_epoch(self):
        order, bars, epochs = runner._fixture_inputs("open_stop")
        altered = replace(bars[0], close=bars[0].close + 1)
        attempts = (
            ({**order, "symbol": "BTCUSDT"}, bars, epochs),
            (order, [altered], epochs),
            (order, bars, [{**epochs[0], "tick": "0.01"}]),
        )
        with patch.object(
            runner,
            "observe_m15_bar",
            side_effect=AssertionError("Unregistered exit called"),
        ):
            for o, b, e in attempts:
                with self.assertRaisesRegex(
                    runner.HistoricalOutcomeBlocked, "INPUTS_DO_NOT_MATCH"
                ):
                    runner._drive_order(o, b, e, fixture_name="open_stop")

    def test_no_caller_supplied_fixture_switch(self):
        with self.assertRaisesRegex(
            runner.HistoricalOutcomeBlocked, "UNKNOWN_INTERNAL_SYNTHETIC"
        ):
            runner.run_registered_fixture("historical")
        with self.assertRaises(TypeError):
            runner.run_registered_fixture("open_stop", bars=[])

    def test_empty_tick_evidence_remains_coverage_stop(self):
        with self.assertRaisesRegex(
            runner.HistoricalOutcomeBlocked, "HISTORICAL_TICK_COVERAGE_GAP"
        ):
            runner.validate_historical_epochs("BTCUSDT", [], {"artifacts": {}})

    def test_tick_source_authentication_and_continuity_required(self):
        name = "docs/machine_strategy_v3_design/MACHINE_STRATEGY_V3_SPEC.json"
        digest = sha256((ROOT / name).read_bytes()).hexdigest()
        # Deliberately labeled nonfinancial metadata fixture; never supplied to a
        # historical runner or published as exchange evidence.
        epoch = {
            "id": "SYNTHETIC_METADATA_FIXTURE",
            "symbol": "BTCUSDT",
            "contract_type": "USDT_LINEAR_PERPETUAL",
            "verified": True,
            "tick": "0.1",
            "effective_from": START,
            "effective_until": END,
            "known_at": START,
            "source_known_at": START,
            "effective_proof_known_at": START,
            "source_path": name,
            "source_sha256": digest,
            "effective_proof_path": name,
            "effective_proof_sha256": digest,
            "interval_verification_status": "VERIFIED_COMPLETE_INTERVAL",
        }
        manifest = {"artifacts": {name: digest}}
        runner.validate_historical_epochs("BTCUSDT", [epoch], manifest)
        for field, value, reason in (
            ("source_sha256", "a" * 64, "NOT_MANIFEST_PINNED"),
            ("effective_proof_path", "../outside", "NOT_MANIFEST_PINNED"),
            ("interval_verification_status", "UNVERIFIED", "CONTINUITY_NOT_VERIFIED"),
            ("effective_from", START + 1, "COVERAGE_GAP"),
            ("effective_until", END - 1, "COVERAGE_GAP"),
        ):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(runner.HistoricalOutcomeBlocked, reason),
            ):
                runner.validate_historical_epochs(
                    "BTCUSDT", [{**epoch, field: value}], manifest
                )


if __name__ == "__main__":
    unittest.main()
