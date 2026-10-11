"""Frozen annotation joins preserve causal source blockers independently of metadata."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from original_v1_1_evidence_completion_v4 import assemble, source_complete


def fixture():
    base = {
        "candidate_id": "case-a",
        "decision_at": 3600,
        "branch": "SFP",
        "setup_tf": 60,
        "required_questions": ["market_context", "source_entry_poi"],
        "source_gaps": ["UNKNOWN_CANONICAL_SOURCE_CONTEXT"],
        "objective_fail_reasons": [],
        "qualitative_fail": [],
        "source_identity": None,
        "source_component_counts": {},
        "metadata_verified": False,
    }
    summary = {
        "view": {
            "candidate_id": "case-a",
            "visible_cutoff": 3600,
            "view_sha256": "frozen-view",
        },
        "answers": {q: "UNKNOWN" for q in base["required_questions"]},
        "records": 2,
    }
    return base, summary


class EvidenceCompletionV4Tests(unittest.TestCase):
    def test_unknown_is_not_failure(self):
        r = assemble(*fixture())
        self.assertEqual(r["status"], "QUALITATIVE_UNKNOWN")
        self.assertEqual(r["qualitative_fail"], [])
        self.assertFalse(r["evidence_complete"])

    def test_metadata_resolution_does_not_close_source(self):
        base, summary = fixture()
        a = assemble(base, summary)
        base["metadata_verified"] = True
        b = assemble(base, summary)
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(b["SOURCE_ALLOW"], 0)

    def test_unknown_gaps_include_all_material_questions(self):
        r = assemble(*fixture())
        self.assertIn("source_entry_poi", r["source_gaps"])
        self.assertIn("UNKNOWN_CANONICAL_SOURCE_CONTEXT", r["source_gaps"])

    def test_lower_tf_wait_is_preserved(self):
        base, _ = fixture()
        base["setup_tf"] = 15
        self.assertEqual(assemble(base, None)["status"], "WAIT_NO_AVAILABLE_LOWER_TF")

    def test_objective_fail_has_precedence(self):
        base, summary = fixture()
        base["objective_fail_reasons"] = ["invalid_source_geometry"]
        self.assertEqual(assemble(base, summary)["status"], "OBJECTIVE_SOURCE_FAIL")

    def test_labels_cannot_create_source_witnesses(self):
        for answer in ("PASS", "FAIL", "TRUE"):
            with self.subTest(answer=answer):
                base, summary = fixture()
                summary["answers"]["market_context"] = answer
                with self.assertRaises(ValueError):
                    assemble(base, summary)

    def test_candidate_alias_rejected(self):
        base, summary = fixture()
        summary["view"]["candidate_id"] = "case-b"
        with self.assertRaises(ValueError):
            assemble(base, summary)

    def test_later_annotation_cutoff_rejected(self):
        base, summary = fixture()
        summary["view"]["visible_cutoff"] += 60
        with self.assertRaises(ValueError):
            assemble(base, summary)

    def test_incomplete_or_extra_question_set_rejected(self):
        for questions in (
            {},
            {"market_context": "UNKNOWN"},
            {
                "market_context": "UNKNOWN",
                "source_entry_poi": "UNKNOWN",
                "extra": "UNKNOWN",
            },
        ):
            base, summary = fixture()
            summary["answers"] = questions
            with self.assertRaises(ValueError):
                assemble(base, summary)

    def test_outcome_input_rejected(self):
        base, summary = fixture()
        base["net_pnl"] = "1"
        with self.assertRaises(ValueError):
            assemble(base, summary)

    def test_shadow_backtest_identical(self):
        base, summary = fixture()
        self.assertEqual(
            assemble(base, summary), assemble(base, summary, mode="SHADOW")
        )

    def test_live_rejected(self):
        with self.assertRaises(ValueError):
            assemble(*fixture(), mode="LIVE")

    def test_inputs_immutable_and_replay_identical(self):
        base, summary = fixture()
        before = copy.deepcopy((base, summary))
        first = assemble(base, summary)
        self.assertEqual(before, (base, summary))
        self.assertEqual(first, assemble(base, summary))

    def test_identity_label_does_not_close_critical_geometry(self):
        base, _ = fixture()
        base["source_identity"] = {"physical_id": "p", "setup_id": "s"}
        base["canonical_source_context"] = {
            "physical_idea_id": "p",
            "setup_id": "s",
            "canonical_source_context": "SOURCE_CONTEXT_COMPLETE",
        }
        self.assertFalse(source_complete(base))

    def test_source_geometry_and_anchor_preserved(self):
        base, summary = fixture()
        base["source_stop_anchor"] = {"kind": "SFP_PATTERN_EXTREME", "known_at": 2700}
        self.assertEqual(
            assemble(base, summary)["source_stop_anchor"], base["source_stop_anchor"]
        )

    def test_future_geometry_cannot_complete_source(self):
        base, _ = fixture()
        base.update(
            {
                "source_identity": {"physical_id": "p", "setup_id": "s"},
                "canonical_source_context": {
                    "physical_idea_id": "p",
                    "setup_id": "s",
                    "canonical_source_context": "SOURCE_CONTEXT_COMPLETE",
                },
                "source_entry_geometry": {"known_at": 3601},
            }
        )
        self.assertFalse(source_complete(base))

    def test_no_entry_authorization(self):
        r = assemble(*fixture())
        self.assertFalse(r["trade_entry_allowed"])
        self.assertEqual(r["SOURCE_DECISION_READY_FOR_FINANCE"], 0)
