"""Source readiness/causal completion independent of unknown execution metadata."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from original_strategy_executable_profile_v1 import ACTIVE, evaluate, load_tree
from original_v1_1_evidence_completion_v3 import (
    COMMON,
    CompletionIndex,
    annotation_signature,
    annotation_unit,
    normalize_object,
    questions_for,
)
from original_v1_1_objective_geometry_v2 import ConsumedRegistry, object_record
from original_v1_1_source_plan_geometry_v3 import (
    READY,
    assess_source,
    source_entry,
    source_stop,
    source_target,
    unique_source_objects,
)
from test_original_strategy_spec_v1_1 import record, synthetic_case
from test_original_v1_1_evidence_adapter_v2 import bars


def complete(branch="OB_CONSERVATIVE", side="LONG"):
    c = synthetic_case(branch, side)
    c["instrument_metadata"] = None
    c["tick_size"] = None
    for q in questions_for(branch):
        c["facts"][q] = record(value=True)
    c["source_context"] = c["identity_evidence"]["context"]
    c["source_context_inventory"] = record(value=True)
    c["branch_conflict_resolution"] = record(value=True)
    c["bos"].update(id="bos-1", kind="BOS")
    c["entry_poi"]["confirmation_id"] = "bos-1"
    c["source_parent_ob"] = record(id="parent-ob", kind="OB")
    c["source_selected_range"] = record(id="selected-range", kind="range")
    c["source_formation"] = record(
        id="formation-1",
        kind="breaker"
        if branch == "BREAKER"
        else "STB"
        if branch == "STB_BTS"
        else "formation",
        payload={"prior_OB_id": "parent-ob", "range_id": "selected-range"},
    )
    c["source_confirmation"] = record(
        id="confirmation-1",
        kind="confirmation",
        known_at=54000,
        completed_at=54000,
        payload={
            "formation_id": "formation-1",
            "structure_id": "protected-structure",
            "range_id": "selected-range",
            "deviation_id": "formation-1",
            "event": "range_boundary_return_retest",
        },
    )
    c["source_stop_clearance"] = record(
        value=True, expression_id=source_stop(c)["expression_id"]
    )
    return c


def annotation_row(candidate="a", proven=False):
    return {
        "candidate_id": candidate,
        "symbol": "SYNTHETIC",
        "direction": "LONG",
        "branch": "OB_CONSERVATIVE",
        "setup_tf": 60,
        "decision_at": 60000,
        "canonical_source_context": {
            "physical_idea_id": "physical" if proven else None,
            "setup_id": "setup" if proven else None,
            "source_object_ids": ["source-poi"],
        },
        "relevant_object_ids": ["source-poi"],
        "required_questions": ["smooth_approach"],
        "source_stop_anchor": {"source_extreme": "95"},
        "source_fta_inventory": {
            "prefixes": {"60": {"objects": 3, "decision_cutoff": 60000}}
        },
        "source_confirmation": {"branch": "OB_CONSERVATIVE"},
        "raw_first_test_observations": [],
    }


class SourcePlanTests(unittest.TestCase):
    def test_each_branch_both_directions_ready_without_metadata(self):
        for branch in ACTIVE:
            for side in ("LONG", "SHORT"):
                with self.subTest(branch=branch, side=side):
                    c = complete(branch, side)
                    result = assess_source(c, required_qualitative=COMMON)
                    self.assertEqual(result["status"], READY, result["source_gaps"])
                    self.assertEqual(result["SOURCE_ALLOW"], 0)
                    self.assertEqual(result["SOURCE_DECISION_READY_FOR_FINANCE"], 0)
                    self.assertFalse(result["trade_entry_allowed"])
                    self.assertEqual(
                        evaluate(c)["status"], "WAIT_UNRESOLVED_INSTRUMENT_METADATA"
                    )

    def test_no_early_metadata_gate(self):
        c = complete()
        c["facts"]["smooth_approach"]["value"] = False
        self.assertEqual(assess_source(c)["status"], "QUALITATIVE_FAIL")

    def test_causal_unknown_not_fail(self):
        c = complete()
        c["facts"]["smooth_approach"]["known_at"] = 60001
        self.assertEqual(assess_source(c)["status"], "QUALITATIVE_UNKNOWN")

    def test_naked_boolean_not_source_proof(self):
        c = complete()
        c["facts"]["smooth_approach"] = {"value": True}
        self.assertEqual(assess_source(c)["status"], "QUALITATIVE_UNKNOWN")

    def test_coverage_wait_before_qualitative_fail(self):
        c = complete()
        c["setup_tf"] = 15
        c["facts"]["smooth_approach"]["value"] = False
        result = assess_source(c)
        self.assertEqual(result["status"], "WAIT_NO_AVAILABLE_LOWER_TF")
        self.assertIn("WAIT_NO_AVAILABLE_LOWER_TF", result["source_gaps"])

    def test_sfp_geometry_fail_before_coverage_wait(self):
        c = complete("SFP")
        c["setup_tf"] = 15
        c["sfp"]["raid"]["low"] = "100"
        self.assertEqual(assess_source(c)["status"], "OBJECTIVE_SOURCE_FAIL")

    def test_unknown_protected_endpoints_blocks_ready(self):
        c = complete()
        del c["facts"]["protected_endpoints"]
        self.assertEqual(
            assess_source(c, required_qualitative=COMMON)["status"],
            "QUALITATIVE_UNKNOWN",
        )

    def test_no_context_id_alias(self):
        c = complete()
        c["source_context"] = record(id="different")
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_metadata_and_tick_do_not_change_source_geometry(self):
        c = complete()
        a = assess_source(c)
        c["tick_size"] = "500"
        c["instrument_metadata"] = record(tick_size="500")
        self.assertEqual(a, assess_source(c))

    def test_beyond_extreme_symbolic_not_fake_tick(self):
        s = source_stop(complete())
        self.assertEqual(s["unrounded_reference"], "95")
        self.assertEqual(s["construction"], "STRICTLY_BEYOND_SOURCE_EXTREME")
        self.assertEqual(s["tick_rounded_stop_price"], "BLOCKED_EXECUTION_METADATA")

    def test_sfp_causal_atr_not_tick(self):
        s = source_stop(complete("SFP"))
        self.assertEqual(s["normalization_ids"], ["N11_ATR_SMA14"])
        self.assertIsNotNone(s["atr_sma14"])

    def test_nonunique_stop_unknown(self):
        c = complete()
        c["stop_anchor"]["unique"] = False
        self.assertIsNone(source_stop(c))
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_future_atr_unknown(self):
        c = complete("SFP")
        c["atr_bars"][0]["known_at"] = 60001
        self.assertIsNone(source_stop(c))

    def test_midpoint_stb_and_proximal_ob(self):
        self.assertEqual(
            source_entry(complete("STB_BTS"))["unrounded_reference"], "100"
        )
        self.assertEqual(source_entry(complete())["unrounded_reference"], "101")

    def test_nearest_fta_all_timeframes(self):
        c = complete()
        target, gap = source_target(c, source_entry(c))
        self.assertIsNone(gap)
        self.assertEqual(target["poi_id"], "near-m15")

    def test_fta_tie_unknown(self):
        c = complete()
        c["contextual_pois"].append(
            {**c["contextual_pois"][0], "id": "materially-other"}
        )
        self.assertEqual(source_target(c, source_entry(c))[1], "UNKNOWN_FTA_NONUNIQUE")

    def test_unknown_inventory_not_empty_complete(self):
        c = complete()
        c["contextual_poi_inventory"]["complete_for_known_prefix"] = False
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_future_fta_mutation_irrelevant(self):
        c = complete()
        a = assess_source(c)
        c["contextual_pois"].append(
            record(
                id="future",
                known_at=60001,
                completed_at=60001,
                low="102",
                high="103",
                contextual=True,
                opposing=True,
            )
        )
        self.assertEqual(a, assess_source(c))
        c["contextual_pois"][-1]["low"] = "-90000"
        self.assertEqual(a, assess_source(c))

    def test_range_fractions_source_not_project_tp(self):
        c = complete("RANGE_CONSERVATIVE")
        t, _ = source_target(c, source_entry(c))
        self.assertEqual(t["fractions_same_zone"], ["0.8", "0.2"])

    def test_range_optional_farther_fta_preserves_boundary_semantics(self):
        c = complete("RANGE_CONSERVATIVE")
        c["range_exit"]["source_exit_poi"] = c["contextual_pois"][-1]
        t, gap = source_target(c, source_entry(c))
        self.assertIsNone(gap)
        self.assertIn("MIN", t["symbolic_target"])

    def test_adverse_wait_sweep_not_fail(self):
        c = complete()
        c["liquidity"][0]["role"] = "ADVERSE"
        r = assess_source(c)
        self.assertEqual(r["status"], "OTHER_SOURCE_WAIT")
        self.assertIn("WAIT_SWEEP", r["source_gaps"])

    def test_unknown_liquidity_never_pass(self):
        c = complete()
        c["liquidity"][0]["role"] = "UNKNOWN"
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_first_test_unknown_never_ready(self):
        c = complete()
        c["zone_first_test"]["value"] = None
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_clearance_bound_to_source_expression(self):
        c = complete()
        c["source_stop_clearance"]["expression_id"] = "unrelated"
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_refinement_must_link_confirmed_bos(self):
        c = complete()
        c["entry_poi"]["confirmation_id"] = "raw-cross"
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_breaker_requires_source_parent_ob(self):
        c = complete("BREAKER")
        c["source_parent_ob"]["source_validated"] = False
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_range_retest_parent_not_interchangeable(self):
        c = complete("RANGE_RETURN_CHOCH")
        c["source_confirmation"]["payload"]["range_id"] = "other-range"
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_stb_requires_structure_confirmation(self):
        c = complete("STB_BTS")
        del c["source_confirmation"]["payload"]["structure_id"]
        self.assertEqual(assess_source(c)["status"], "OTHER_SOURCE_WAIT")

    def test_mode_parity(self):
        for b in ACTIVE:
            c = complete(b)
            a = assess_source(c)
            c["mode"] = "SHADOW"
            self.assertEqual(a, assess_source(c))

    def test_live_forbidden(self):
        c = complete()
        c["mode"] = "LIVE"
        with self.assertRaises(ValueError):
            assess_source(c)

    def test_outcomes_forbidden(self):
        c = complete()
        c["nested"] = {"win_rate": 0.8}
        with self.assertRaises(ValueError):
            assess_source(c)

    def test_policy_injection_rejected(self):
        t = copy.deepcopy(load_tree())
        t["source_nodes"][0]["rule_id"] = "P_ANTI_SCALP"
        c = complete(t["source_nodes"][0]["branch_id"])
        with self.assertRaisesRegex(ValueError, "Non-source"):
            assess_source(c, tree=t)

    def test_multiple_contexts_not_arbitrarily_selected(self):
        objects = [record(id="a"), record(id="b")]
        self.assertEqual(
            unique_source_objects(objects, at=60000, reason="UNKNOWN_CONTEXT")[1],
            "UNKNOWN_CONTEXT_NONUNIQUE",
        )


class CompletionObjectTests(unittest.TestCase):
    def setUp(self):
        self.bars = bars(
            [
                (10, 11, 8, 10),
                (10, 12, 7, 10),
                (10, 11, 8, 10),
                (10, 13, 9, 12),
                (12, 12.5, 9, 11),
                (11, 12, 6, 6.5),
            ]
        )
        self.index = CompletionIndex("BTCUSDT", 60, self.bars)

    def test_prefix_reconstruction(self):
        at = self.bars[3].end
        short = CompletionIndex("BTCUSDT", 60, self.bars[:4])
        self.assertEqual(short.prefix(at), self.index.prefix(at))
        self.assertEqual(
            short.ordered, [o for o in self.index.ordered if o["known_at"] <= at]
        )

    def test_future_mutation(self):
        at = self.bars[3].end
        changed = self.bars[:4] + bars(
            [(500, 900, 400, 700), (700, 800, 500, 600)], start=at
        )
        other = CompletionIndex("BTCUSDT", 60, changed)
        self.assertEqual(other.prefix(at), self.index.prefix(at))

    def test_raw_cross_not_bos(self):
        crosses = [o for o in self.index.ordered if o["kind"] == "raw_body_cross"]
        self.assertTrue(crosses)
        self.assertTrue(
            all(
                o["payload"]["BOS_or_CONF_source_role"] == "UNKNOWN"
                and not o["source_validated"]
                for o in crosses
            )
        )

    def test_touch_cutoff_completed_only(self):
        touch = self.index.touch.first(10800, 8, 10, 14400)
        self.assertEqual(touch["known_at"], 14400)
        self.assertIsNone(self.index.touch.first(10800, 8, 10, 14399))
        self.assertEqual(touch["source_eligible_test"], "UNKNOWN")

    def test_parent_ids_known_and_canonical(self):
        for o in self.index.ordered:
            self.assertEqual(o["canonical_id"], o["id"])
            self.assertTrue(
                all(
                    self.index.objects[p]["known_at"] <= o["known_at"]
                    for p in o["parent_ids"]
                )
            )

    def test_parent_future_rejected(self):
        parent = object_record(
            "swing", "BTCUSDT", 60, 10000, {"price": "10"}, ["S_STRUCTURE"]
        )
        child = object_record(
            "raw_body_cross", "BTCUSDT", 60, 9999, {"level_id": parent["id"]}, ["S_BOS"]
        )
        with self.assertRaises(ValueError):
            normalize_object(child, parent_objects={parent["id"]: parent})

    def test_first_test_idempotence(self):
        r = ConsumedRegistry()
        a = r.test("poi", "event", 100, eligible=True, ordered=True)
        self.assertEqual(a, r.test("poi", "event", 100, eligible=True, ordered=True))
        self.assertEqual(
            r.test("poi", "other", 101, eligible=True, ordered=True)["state"],
            "CONSUMED",
        )

    def test_unknown_eligibility_not_consumed(self):
        r = ConsumedRegistry()
        r.test("poi", "raw-touch", 100, eligible=None, ordered=False)
        self.assertEqual(
            r.test("poi", "valid", 101, eligible=True, ordered=True)["state"],
            "FIRST_TEST",
        )


class AnnotationEquivalenceTests(unittest.TestCase):
    def test_null_identity_not_equivalence(self):
        a, b = annotation_row("a"), annotation_row("b")
        self.assertNotEqual(annotation_signature(a), annotation_signature(b))
        with self.assertRaises(ValueError):
            annotation_unit([a, b])

    def test_proven_identical_context_safe_to_group(self):
        unit = annotation_unit([annotation_row("a", True), annotation_row("b", True)])
        self.assertEqual(unit["candidate_ids"], ["a", "b"])

    def test_each_material_difference_separates(self):
        for field, value in [
            ("decision_at", 60001),
            ("direction", "SHORT"),
            ("branch", "SFP"),
            ("required_questions", ["higher_poi"]),
            ("relevant_object_ids", ["other"]),
        ]:
            a, b = annotation_row("a", True), annotation_row("b", True)
            b[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                annotation_unit([a, b])

    def test_question_source_citation_required(self):
        a = annotation_row()
        a["required_questions"] = ["invented_question"]
        with self.assertRaises(ValueError):
            annotation_unit([a])

    def test_label_or_outcome_cannot_be_identity_input(self):
        a = annotation_row()
        a["outcome"] = "WIN"
        with self.assertRaises(ValueError):
            annotation_signature(a)

    def test_expanded_questions_all_have_frozen_citations(self):
        from original_v1_1_evidence_adapter_v2 import QUALITATIVE
        from original_v1_1_evidence_completion_v3 import ADDED_QUESTIONS

        for b in ACTIVE:
            for q in questions_for(b):
                self.assertTrue(QUALITATIVE.get(q, ADDED_QUESTIONS.get(q)))


class BlindedMaterializerTests(unittest.TestCase):
    def view(self, directory, *, cutoff=10800):
        from original_strategy_executable_profile_v1 import digest
        from original_v1_1_financial_data import write_rows

        index = CompletionIndex(
            "BTCUSDT",
            60,
            bars([(10, 11, 8, 10), (10, 12, 7, 10), (10, 11, 8, 10), (10, 13, 9, 12)]),
        )
        objects = directory / "objects.jsonl.gz"
        candles = directory / "candles.jsonl.gz"
        write_rows(objects, index.ordered)
        write_rows(candles, (b.observed(60) for b in index.bars))
        view = index.prefix(cutoff)
        view["objects_file"] = str(objects)
        view["blinded_candles_file"] = str(candles)
        return {
            "annotation_unit_id": digest(["fixture", cutoff]),
            "decision_cutoff": cutoff,
            "blinded_prefixes": {"60": view},
            "trade_entry_allowed": False,
        }

    def test_materialized_actual_prefix_excludes_future(self):
        import tempfile

        from materialize_original_v1_1_evidence_completion_v3 import materialize

        with tempfile.TemporaryDirectory() as temp:
            unit = self.view(Path(temp))
            result = materialize(unit)
            self.assertEqual(len(result["completed_candles"]["60"]), 3)
            self.assertTrue(
                all(o["known_at"] <= 10800 for o in result["causal_objects"]["60"])
            )
            self.assertFalse(result["future_candles_exposed"])

    def test_materializer_rejects_forged_prefix_hash(self):
        import tempfile

        from materialize_original_v1_1_evidence_completion_v3 import materialize

        with tempfile.TemporaryDirectory() as temp:
            unit = self.view(Path(temp))
            unit["blinded_prefixes"]["60"]["object_prefix_sha256"] = "f" * 64
            with self.assertRaises(ValueError):
                materialize(unit)

    def test_materializer_rejects_different_cutoff(self):
        import tempfile

        from materialize_original_v1_1_evidence_completion_v3 import materialize

        with tempfile.TemporaryDirectory() as temp:
            unit = self.view(Path(temp))
            unit["decision_cutoff"] += 1
            with self.assertRaises(ValueError):
                materialize(unit)

    def test_materializer_rejects_forged_count(self):
        import tempfile

        from materialize_original_v1_1_evidence_completion_v3 import materialize

        with tempfile.TemporaryDirectory() as temp:
            unit = self.view(Path(temp))
            unit["blinded_prefixes"]["60"]["completed_candles"] = 4
            with self.assertRaises(ValueError):
                materialize(unit)

    def test_incomplete_native_bar_never_rendered(self):
        import tempfile

        from materialize_original_v1_1_evidence_completion_v3 import materialize

        with tempfile.TemporaryDirectory() as temp:
            unit = self.view(Path(temp), cutoff=10799)
            result = materialize(unit)
            self.assertEqual(len(result["completed_candles"]["60"]), 2)

    def test_unit_outcome_leak_rejected(self):
        import tempfile

        from materialize_original_v1_1_evidence_completion_v3 import materialize

        with tempfile.TemporaryDirectory() as temp:
            unit = self.view(Path(temp))
            unit["baseline_result"] = "old label"
            with self.assertRaises(ValueError):
                materialize(unit)

    def test_all_unit_source_citations_are_frozen_source(self):
        from original_v1_1_evidence_adapter_v2 import QUALITATIVE
        from original_v1_1_evidence_completion_v3 import ADDED_QUESTIONS
        from original_v1_1_source_plan_geometry_v3 import source_categories

        for branch in ACTIVE:
            for q in questions_for(branch):
                for rule in QUALITATIVE.get(q, ADDED_QUESTIONS.get(q)):
                    self.assertEqual(source_categories()[rule], "SOURCE_RULE")


if __name__ == "__main__":
    unittest.main()
