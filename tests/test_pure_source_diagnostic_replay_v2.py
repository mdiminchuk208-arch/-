from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta

from test_pure_source_object_provider_v2 import BASE
from test_pure_source_setup_provider_v2 import setup_data

from crypto_bot.strategy.pure_source_diagnostic_replay_v2 import (
    BASELINE_IDENTIFIABILITY,
    build_source_diagnostic_artifact,
    verify_source_diagnostic_artifact,
    verify_source_diagnostic_resume,
)


class SourceDiagnosticReplayTests(unittest.TestCase):
    def test_end_to_end_diagnostic_artifact_preserves_fail_closed_boundary(self):
        artifact = build_source_diagnostic_artifact(setup_data())
        self.assertEqual(artifact.baseline_identifiability, BASELINE_IDENTIFIABILITY)
        self.assertFalse(artifact.trade_entry_allowed)
        self.assertFalse(artifact.financial_run)
        self.assertEqual(artifact.source_ready_setup_count, 0)
        self.assertEqual(artifact.execution_ready_observation_count, 0)
        self.assertGreater(artifact.execution_plan_count, 0)
        self.assertEqual(artifact.receipt_count, artifact.evidence_batch_count)
        self.assertTrue(verify_source_diagnostic_artifact(artifact))

        execution_reasons = {
            row.reason
            for row in artifact.unresolved
            if row.layer == "EXECUTION"
        }
        self.assertTrue(
            {
                "SFP_ENTRY_QUOTE_WITHIN_NEW_POI_UNRESOLVED",
                "WAIT_SFP_ATR_EVIDENCE",
                "WAIT_FIRST_TROUBLE_AREA",
            }.issubset(execution_reasons)
        )

    def test_input_order_is_deterministic(self):
        lower, higher = setup_data()
        forward = build_source_diagnostic_artifact((lower, higher))
        reverse = build_source_diagnostic_artifact((higher, lower))
        self.assertEqual(forward, reverse)

    def test_future_mutation_changes_dataset_identity_not_causal_prefix(self):
        cutoff = BASE + timedelta(minutes=45)
        initial = build_source_diagnostic_artifact(setup_data(), through=cutoff)
        mutated = build_source_diagnostic_artifact(
            setup_data(invalidation=True, extra_poi=True), through=cutoff
        )

        # The immutable full-dataset manifest must expose the changed future
        # suffix. Hiding that difference would make artifact reuse unsafe.
        self.assertNotEqual(initial.dataset_sha256, mutated.dataset_sha256)
        self.assertNotEqual(initial.artifact_sha256, mutated.artifact_sha256)

        # Causal computation through the cutoff must remain bit-for-bit stable.
        self.assertEqual(initial.first_decision_at, mutated.first_decision_at)
        self.assertEqual(initial.last_decision_at, mutated.last_decision_at)
        self.assertEqual(initial.receipt_count, mutated.receipt_count)
        self.assertEqual(initial.evidence_batch_count, mutated.evidence_batch_count)
        self.assertEqual(initial.receipt_chain_sha256, mutated.receipt_chain_sha256)
        self.assertEqual(initial.evidence_chain_sha256, mutated.evidence_chain_sha256)
        self.assertEqual(initial.final_runtime_sha256, mutated.final_runtime_sha256)
        self.assertEqual(initial.causal_object_count, mutated.causal_object_count)
        self.assertEqual(initial.setup_count, mutated.setup_count)
        self.assertEqual(initial.execution_plan_count, mutated.execution_plan_count)
        self.assertEqual(initial.source_ready_setup_count, mutated.source_ready_setup_count)
        self.assertEqual(
            initial.execution_ready_observation_count,
            mutated.execution_ready_observation_count,
        )
        self.assertEqual(initial.unresolved, mutated.unresolved)
        self.assertEqual(initial.trade_entry_allowed, mutated.trade_entry_allowed)
        self.assertEqual(initial.financial_run, mutated.financial_run)

    def test_fingerprint_detects_tampering(self):
        artifact = build_source_diagnostic_artifact(setup_data())
        changed = replace(artifact, receipt_chain_sha256="0" * 64)
        self.assertFalse(verify_source_diagnostic_artifact(changed))

    def test_verified_repeat_matches_exact_artifact(self):
        artifact = build_source_diagnostic_artifact(setup_data())
        verification = verify_source_diagnostic_resume(artifact, setup_data())
        self.assertTrue(verification.verified)
        self.assertEqual(verification.reason, "EXACT_DIAGNOSTIC_REPLAY_MATCH")
        self.assertEqual(
            verification.existing_artifact_sha256,
            verification.repeated_artifact_sha256,
        )

    def test_resume_rejects_different_dataset(self):
        artifact = build_source_diagnostic_artifact(setup_data())
        verification = verify_source_diagnostic_resume(
            artifact, setup_data(invalidation=True, extra_poi=True)
        )
        self.assertFalse(verification.verified)
        self.assertEqual(verification.reason, "DATASET_SHA256_MISMATCH")


if __name__ == "__main__":
    unittest.main()
