"""Negative integrity and engine-isolation tests; no historical finance."""

import importlib
import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import check_machine_strategy_v4_1_conformance as field_checker
import verify_machine_strategy_v4_1_implementation_v1 as verifier
from check_machine_strategy_v4_1_source_replay import FinancialImportTrap, trap


class FreezeTests(unittest.TestCase):
    def test_final_field_report_cannot_upgrade_single_product_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "SOURCE_PREFIX_REPLAY_RECEIPT.json").write_text(
                json.dumps(
                    {
                        "source_only_causality": "PASS",
                        "historical_position_evaluations": 0,
                        "historical_financial_authorized": False,
                        "trade_entry_allowed": False,
                        "products": {"BTC-USDT-SWAP": {}},
                    }
                )
            )
            with (
                patch.object(field_checker, "DEST", root),
                self.assertRaisesRegex(ValueError, "SOURCE_PRODUCT_GAP"),
            ):
                field_checker.check()

    def test_partial_field_report_requires_external_progress_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "SOURCE_REPLAY_PROGRESS.json").write_text("{}")
            with (
                patch.object(field_checker, "DEST", root),
                self.assertRaisesRegex(ValueError, "EXTERNAL_PROGRESS_PIN_MISMATCH"),
            ):
                field_checker.check(partial=True, expected_progress_sha256="0" * 64)

    def test_pin_verification_rejects_changed_bytes_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "proof.json"
            path.write_text("sealed")
            pins = {"proof.json": sha256(path.read_bytes()).hexdigest()}
            verifier.verify_pins(pins, root)
            path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "PIN_CHANGED"):
                verifier.verify_pins(pins, root)
            with self.assertRaisesRegex(ValueError, "UNSAFE_PIN_PATH"):
                verifier.verify_pins({"../outside": "0" * 64}, root)

    def test_resume_requires_external_manifest_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("{}")
            with patch.object(verifier, "MANIFEST", path):
                for pin in (None, "", "0" * 64):
                    with self.assertRaisesRegex(
                        ValueError, "EXTERNAL_IMPLEMENTATION_PIN"
                    ):
                        verifier.resume(pin)

    def test_self_consistent_ready_with_financial_flag_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "decision": verifier.READY,
                        "complete_implementation_freeze": True,
                        "implementation_ready": True,
                        "historical_financial_authorized": True,
                        "historical_position_evaluations": 0,
                        "trade_entry_allowed": False,
                        "PAPER": False,
                        "LIVE": False,
                    }
                )
            )
            with (
                patch.object(verifier, "MANIFEST", path),
                self.assertRaisesRegex(ValueError, "FROZEN_SAFETY_DRIFT"),
            ):
                verifier.resume(sha256(path.read_bytes()).hexdigest())

    def test_ready_label_cannot_mask_incomplete_source_evidence(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_NOT_PASS"):
            verifier.check_source({"source_only_causality": "PENDING"})

    def test_production_replay_traps_position_call_before_its_body(self):
        executed = []

        def _drive_case():
            executed.append(True)

        old = sys.getprofile()
        sys.setprofile(trap)
        try:
            with self.assertRaisesRegex(RuntimeError, "POSITION_ENGINE_FORBIDDEN"):
                _drive_case()
        finally:
            sys.setprofile(old)
        self.assertEqual(executed, [])

    def test_financial_runner_import_is_actively_denied(self):
        guard = FinancialImportTrap()
        # Remove/reinstate any synthetic-test import without reexecuting it.
        name = "machine_strategy_v4_1_guarded_runner"
        prior = sys.modules.pop(name, None)
        sys.meta_path.insert(0, guard)
        try:
            with self.assertRaisesRegex(
                RuntimeError, "FINANCIAL_RUNNER_IMPORT_FORBIDDEN"
            ):
                importlib.import_module(name)
        finally:
            sys.meta_path.remove(guard)
            if prior is not None:
                sys.modules[name] = prior


if __name__ == "__main__":
    unittest.main()
