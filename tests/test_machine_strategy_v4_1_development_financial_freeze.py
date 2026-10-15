from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_machine_strategy_v4_1_development_financial_v1 as seal


class FinancialSealIntegrityTests(unittest.TestCase):
    def test_missing_external_checkpoint_pin_cannot_resume(self):
        with self.assertRaisesRegex(ValueError, "EXTERNAL_CHECKPOINT_PIN_REQUIRED"):
            seal.checkpoint(None)

    def test_parent_manifest_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "parent.json"
            path.write_text("{}")
            with (
                patch.object(seal, "PARENT", path),
                self.assertRaisesRegex(
                    ValueError, "EXTERNAL_IMPLEMENTATION_PIN_CHANGED"
                ),
            ):
                seal.parent_pins()

    def test_valid_complete_checkpoint_and_missing_member(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "results"
            out.mkdir()
            for name in seal.FILES:
                (out / name).write_text("exact frozen bytes")
            data = {
                "historical_run_count": 1,
                "artifacts_sha256": {
                    name: seal.digest(out / name) for name in seal.FILES
                },
            }
            path = out / "RUN_CHECKPOINT.json"
            path.write_text(json.dumps(data))
            with patch.object(seal, "ROOT", root), patch.object(seal, "OUT", out):
                self.assertEqual(seal.checkpoint(seal.digest(path)), data)
                del data["artifacts_sha256"]["RUN_RECEIPT.json"]
                path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, "INCOMPLETE_CHECKPOINT"):
                    seal.checkpoint(seal.digest(path))

    def test_changed_payload_cannot_pass_external_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "results"
            out.mkdir()
            for name in seal.FILES:
                (out / name).write_text("first")
            data = {
                "historical_run_count": 1,
                "artifacts_sha256": {
                    name: seal.digest(out / name) for name in seal.FILES
                },
            }
            path = out / "RUN_CHECKPOINT.json"
            path.write_text(json.dumps(data))
            pin = seal.digest(path)
            (out / "FINANCIAL_RESULT.json").write_text("changed")
            with (
                patch.object(seal, "ROOT", root),
                patch.object(seal, "OUT", out),
                self.assertRaisesRegex(ValueError, "PIN_CHANGED"),
            ):
                seal.checkpoint(pin)

    def test_arbitrary_external_path_pin_rejected(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "UNSAFE_PIN_PATH"),
        ):
            seal.verify_pins({"../outside": "0" * 64}, Path(directory))

    def test_empty_pin_inventory_rejected(self):
        with self.assertRaisesRegex(ValueError, "EMPTY_PINS"):
            seal.verify_pins({})

    def test_runner_auditor_disagreement_never_becomes_pass(self):
        with self.assertRaisesRegex(
            ValueError, "PASS_WITHOUT_CONCORDANT_QUALIFICATION"
        ):
            seal.decision_allowed(seal.PASS, seal.STOP, seal.PASS)
        seal.decision_allowed(seal.PASS, seal.STOP, seal.STOP)

    def test_unknown_decision_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_DECISION"):
            seal.decision_allowed(seal.PASS, seal.PASS, "READY")

    def test_one_shot_count_must_remain_one(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            path = out / "RUN_CHECKPOINT.json"
            path.write_text(json.dumps({"historical_run_count": 2}))
            with (
                patch.object(seal, "OUT", out),
                self.assertRaisesRegex(ValueError, "RUN_COUNT_DRIFT"),
            ):
                seal.checkpoint(seal.digest(path))

    def test_result_manifest_cannot_resume_without_external_pin(self):
        with self.assertRaisesRegex(
            ValueError, "EXTERNAL_RESULT_MANIFEST_PIN_MISMATCH"
        ):
            seal.resume(None)

    def test_actual_pre_outcome_qa_has_complete_committed_evidence(self):
        pins = seal.pre_run_qa(seal.read("PRE_RUN_QA_RECEIPT.json"))
        self.assertEqual(len(pins), 11)

    def test_empty_or_arbitrary_qa_evidence_rejected(self):
        original = seal.read("PRE_RUN_QA_RECEIPT.json")
        for field, value in (
            ("commands", []),
            ("tested_sha256", {"unrelated": "0" * 64}),
            ("log_sha256", {}),
        ):
            bad = copy.deepcopy(original)
            bad[field] = value
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ValueError, "INCOMPLETE_PRE_RUN_QA"),
            ):
                seal.pre_run_qa(bad)

    def test_review_must_cover_exact_outcome_and_previous_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outcome").write_text("exact")
            (root / "previous").write_text("first actual review")
            anchors = {
                name: seal.digest(root / name) for name in ("outcome", "previous")
            }
            receipt = {
                "role": "COST_FUNDING_AUDITOR",
                "sequence": 2,
                "review_completed": True,
                "previous_review_sha256": anchors["previous"],
                "reviewed_sha256": dict(anchors),
            }
            with patch.object(seal, "ROOT", root):
                seal.review_receipt(
                    receipt, "COST_FUNDING_AUDITOR", 2, anchors, anchors["previous"]
                )
                for field, value, error in (
                    (
                        "reviewed_sha256",
                        {"previous": anchors["previous"]},
                        "INCOMPLETE_REVIEW_ANCHORS",
                    ),
                    ("previous_review_sha256", None, "REVIEW_CHAIN_CHANGED"),
                    ("role", "BACKTEST_REVIEWER", "REVIEW_ROLE_SEQUENCE"),
                    ("sequence", 1, "REVIEW_ROLE_SEQUENCE"),
                ):
                    bad = dict(receipt)
                    bad[field] = value
                    with (
                        self.subTest(field=field),
                        self.assertRaisesRegex(ValueError, error),
                    ):
                        seal.review_receipt(
                            bad, "COST_FUNDING_AUDITOR", 2, anchors, anchors["previous"]
                        )

    def test_audit_checks_cannot_be_empty_partial_or_truthy_nonboolean(self):
        audit = {
            "decision": seal.PASS,
            "runner_reported_decision": seal.PASS,
            "checks": dict.fromkeys(seal.AUDIT_CHECKS, True),
        }
        seal.audit_integrity(audit, seal.PASS)
        for checks in (
            {},
            {"closed_trades_min": True},
            dict.fromkeys(seal.AUDIT_CHECKS, 1),
        ):
            with (
                self.subTest(checks=checks),
                self.assertRaisesRegex(ValueError, "INCOMPLETE_AUDIT_CHECKS"),
            ):
                seal.audit_integrity({**audit, "checks": checks}, seal.PASS)
        with self.assertRaisesRegex(ValueError, "AUDIT_RUNNER_DRIFT"):
            seal.audit_integrity(audit, seal.STOP)
        audit["checks"]["closed_trades_min"] = False
        with self.assertRaisesRegex(ValueError, "AUDIT_DECISION_INCOHERENT"):
            seal.audit_integrity(audit, seal.PASS)

    def test_final_decision_must_match_review_and_exact_checkpoint(self):
        checked = {
            "runner_decision": seal.PASS,
            "auditor_decision": seal.PASS,
            "critical_blockers": [],
        }
        decision = {
            **checked,
            "decision": seal.PASS,
            "stop_reasons": [],
            "checkpoint_sha256": "a" * 64,
        }
        self.assertEqual(
            seal.final_decision(decision, {"decision": seal.PASS}, checked, "a" * 64),
            seal.PASS,
        )
        for field, value in (
            ("decision", seal.STOP),
            ("runner_decision", seal.STOP),
            ("checkpoint_sha256", "b" * 64),
        ):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ValueError, "FINAL_DECISION_INCOHERENT"),
            ):
                seal.final_decision(
                    {**decision, field: value},
                    {"decision": seal.PASS},
                    checked,
                    "a" * 64,
                )
        with self.assertRaisesRegex(ValueError, "CRITICAL_REVIEW_BLOCKER"):
            seal.final_decision(
                decision,
                {"decision": seal.PASS},
                {**checked, "critical_blockers": ["unresolved"]},
                "a" * 64,
            )
        with self.assertRaisesRegex(ValueError, "PASS_WITH_STOP_REASONS"):
            seal.final_decision(
                {**decision, "stop_reasons": ["unresolved"]},
                {"decision": seal.PASS},
                checked,
                "a" * 64,
            )

    def test_stop_requires_specific_recorded_reason(self):
        checked = {
            "runner_decision": seal.STOP,
            "auditor_decision": seal.STOP,
            "critical_blockers": [],
        }
        decision = {
            **checked,
            "decision": seal.STOP,
            "stop_reasons": [],
            "checkpoint_sha256": "a" * 64,
        }
        with self.assertRaisesRegex(ValueError, "EXACT_STOP_REASONS_REQUIRED"):
            seal.final_decision(decision, {"decision": seal.STOP}, checked, "a" * 64)
        self.assertEqual(
            seal.final_decision(
                {**decision, "stop_reasons": ["closed_trades_min"]},
                {"decision": seal.STOP},
                checked,
                "a" * 64,
            ),
            seal.STOP,
        )

    def test_resume_rejects_unpinned_added_namespace_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "out"
            out.mkdir()
            final = out / "FINAL_DECISION.json"
            final.write_text(json.dumps({"decision": seal.STOP}))
            manifest = out / "RESULT_FREEZE_MANIFEST.json"
            data = {
                "decision": seal.STOP,
                "historical_run_count": 1,
                "trade_entry_allowed": False,
                "PAPER": False,
                "LIVE": False,
                "private_exchange_api_allowed": False,
                "further_historical_financial_runs_authorized": False,
                "artifact_sha256": {"out/FINAL_DECISION.json": seal.digest(final)},
            }
            manifest.write_text(json.dumps(data))
            with (
                patch.object(seal, "ROOT", root),
                patch.object(seal, "OUT", out),
                patch.object(seal, "MANIFEST", manifest),
            ):
                self.assertTrue(seal.resume(seal.digest(manifest))["verified_resume"])
                (out / "new_unpinned_result.json").write_text("tampering")
                with self.assertRaisesRegex(
                    ValueError, "FROZEN_NAMESPACE_MEMBERSHIP_CHANGED"
                ):
                    seal.resume(seal.digest(manifest))


if __name__ == "__main__":
    unittest.main()
