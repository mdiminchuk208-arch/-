"""Independent causal view/annotation sufficiency contracts, no outcomes."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from original_strategy_executable_profile_v1 import digest
from original_v1_1_blinded_annotation_v1 import (
    KnownPrefix,
    annotation,
    citations,
    validate_annotation,
)
from original_v1_1_evidence_completion_v3 import CompletionIndex
from test_original_v1_1_evidence_adapter_v2 import bars


def fixture(question="market_context"):
    unit = {
        "candidate_ids": ["candidate-a"],
        "annotation_unit_id": "unit-a",
        "decision_cutoff": 10800,
        "required_questions": [
            {"concept": question, "source_rule_ids": ["S_STRUCTURE"]}
        ],
    }
    view = {
        "causal_inventory": {
            "60": {
                "last_completed_at": 10800,
                "source_contextual_witness_counts": {},
                "source_primitive_counts": {"swing": 2},
            }
        },
        "visible_related_objects": [],
        "trade_entry_allowed": False,
    }
    return unit, view


class BlindedAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.sources = citations()

    def test_strict_source_underdetermination_unknown(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        self.assertEqual(r["answer"], "UNKNOWN")
        self.assertFalse(r["source_validated"])
        self.assertEqual(r["unknown_reason"], "UNKNOWN_SOURCE_CONTEXT_SELECTION")
        validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_no_claim_human_review(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        self.assertFalse(r["annotator_provenance"]["claimed_human_chart_review"])

    def test_geometry_not_protected_importance(self):
        unit, view = fixture("protected_endpoints")
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        self.assertEqual(r["answer"], "UNKNOWN")

    def test_new_witness_not_ignored_or_auto_passed(self):
        unit, view = fixture()
        view["causal_inventory"]["60"]["source_contextual_witness_counts"] = {
            "source_context": 1
        }
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        self.assertEqual(r["unknown_reason"], "UNKNOWN_UNREVIEWED_CONTEXTUAL_RELATION")

    def test_future_view_forbidden(self):
        unit, view = fixture()
        view["causal_inventory"]["60"]["last_completed_at"] = 10801
        with self.assertRaises(ValueError):
            annotation(unit, unit["required_questions"][0], view, self.sources)

    def test_nonsource_citation_forbidden(self):
        unit, view = fixture()
        unit["required_questions"][0]["source_rule_ids"] = ["U1"]
        with self.assertRaises(ValueError):
            annotation(unit, unit["required_questions"][0], view, self.sources)

    def test_uncited_question_forbidden(self):
        unit, view = fixture()
        unit["required_questions"][0]["source_rule_ids"] = []
        with self.assertRaises(ValueError):
            annotation(unit, unit["required_questions"][0], view, self.sources)

    def test_unknown_question_not_silently_annotated(self):
        unit, view = fixture("invented_numeric_gate")
        with self.assertRaises(ValueError):
            annotation(unit, unit["required_questions"][0], view, self.sources)

    def test_future_annotation_time_forbidden(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        r["known_at"] = 10801
        with self.assertRaises(ValueError):
            validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_candidate_alias_cannot_reuse_annotation(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        r["candidate_id"] = "another"
        with self.assertRaises(ValueError):
            validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_view_mutation_cannot_reuse_provenance(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        view["visible_related_objects"] = ["changed"]
        with self.assertRaises(ValueError):
            validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_unknown_needs_reason(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        r["unknown_reason"] = ""
        with self.assertRaises(ValueError):
            validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_pass_without_witness_rejected(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        r["answer"] = "PASS"
        with self.assertRaises(ValueError):
            validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_unknown_cannot_set_source_validated(self):
        unit, view = fixture()
        r = annotation(unit, unit["required_questions"][0], view, self.sources)
        r["source_validated"] = True
        with self.assertRaises(ValueError):
            validate_annotation(r, unit=unit, view=view, citation_index=self.sources)

    def test_outcome_input_forbidden(self):
        unit, view = fixture()
        view["outcome"] = "WIN"
        with self.assertRaises(ValueError):
            annotation(unit, unit["required_questions"][0], view, self.sources)

    def test_annotation_mode_independent(self):
        unit, view = fixture()
        a = annotation(unit, unit["required_questions"][0], view, self.sources)
        self.assertEqual(
            a, annotation(unit, unit["required_questions"][0], view, self.sources)
        )

    def test_citations_have_actual_primary_text_hash_and_pages(self):
        for source in self.sources.values():
            self.assertEqual(source["category"], "SOURCE_RULE")
            self.assertTrue(source["primary_passages"])
            for p in source["primary_passages"]:
                self.assertTrue(p["literal_passage"])
                self.assertEqual(len(p["source_sha256"]), 64)
                self.assertTrue(p["page_or_paragraph"])


class KnownPrefixTests(unittest.TestCase):
    def setUp(self):
        self.bars = bars(
            [(10, 11, 8, 10), (10, 12, 7, 10), (10, 11, 8, 10), (10, 13, 9, 12)]
        )
        self.index = CompletionIndex("BTCUSDT", 60, self.bars)

    def cursor(self, index=None):
        i = index or self.index
        return KnownPrefix(i.ordered, (b.observed(60) for b in i.bars))

    def test_actual_prefix_counts_and_hash(self):
        result = self.cursor().verify(self.index.prefix(10800))
        self.assertEqual(result["completed_candles"], 3)
        self.assertEqual(result["last_completed_at"], 10800)

    def test_future_object_not_exposed(self):
        c = self.cursor()
        c.verify(self.index.prefix(10800))
        self.assertTrue(all(o["known_at"] <= 10800 for o in c.objects.values()))

    def test_prefix_reconstruction_identity(self):
        c = self.cursor()
        other = CompletionIndex("BTCUSDT", 60, self.bars[:3])
        self.assertEqual(
            c.verify(self.index.prefix(10800)),
            self.cursor(other).verify(other.prefix(10800)),
        )

    def test_future_mutation_preserves_annotation_inventory(self):
        changed = CompletionIndex(
            "BTCUSDT", 60, self.bars[:3] + bars([(500, 900, 400, 700)], start=10800)
        )
        self.assertEqual(
            self.cursor().verify(self.index.prefix(10800)),
            self.cursor(changed).verify(changed.prefix(10800)),
        )

    def test_backward_causality_rejected(self):
        c = self.cursor()
        c.advance(10800)
        with self.assertRaises(ValueError):
            c.advance(10799)

    def test_incomplete_native_bar_excluded(self):
        c = self.cursor()
        result = c.verify(self.index.prefix(10799))
        self.assertEqual(result["completed_candles"], 2)

    def test_forged_prefix_hash_rejected(self):
        view = copy.deepcopy(self.index.prefix(10800))
        view["object_prefix_sha256"] = digest(["forged"])
        with self.assertRaises(ValueError):
            self.cursor().verify(view)

    def test_forged_count_rejected(self):
        view = copy.deepcopy(self.index.prefix(10800))
        view["completed_candles"] = 4
        with self.assertRaises(ValueError):
            self.cursor().verify(view)

    def test_repeated_cutoff_idempotent(self):
        c = self.cursor()
        a = c.verify(self.index.prefix(10800))
        self.assertEqual(a, c.verify(self.index.prefix(10800)))


if __name__ == "__main__":
    unittest.main()
