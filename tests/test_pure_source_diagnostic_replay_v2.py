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

    def test_prefix_artifact_is_unchanged_by_later_future_mutation(self):
        cutoff = BASE + timedelta(minutes=45)
        initial = build_source_diagnostic_artifact(setup_data(), through=cutoff)
        mutated = build_source_diagnostic_artifact(
            setup_data(invalidation=True, extra_poi=True), through=cutoff
        )
        self.assertEqual(initial, mutated)

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
