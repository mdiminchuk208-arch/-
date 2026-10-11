"""New economic admission filters never choose thresholds or geometry by outcomes."""

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_machine_strategy_improvement_design import configuration
from run_machine_strategy_research import version_cases


def item(entry=100, stop=98, target=102):
    return {
        "case_id": "stable-case",
        "decision_at": 1000,
        "theoretical_entry": str(entry),
        "fixed_initial_stop": str(stop),
        "theoretical_target": str(target),
        "trade_entry_allowed": False,
    }


class ImprovementTests(unittest.TestCase):
    def apply(self, version, c):
        with patch(
            "run_machine_strategy_research.read", return_value=configuration(version)
        ):
            return version_cases(version, [c])

    def test_cost_budget_pre_entry(self):
        included, excluded = self.apply("v2.1", item(target=100.1))
        self.assertFalse(included)
        self.assertEqual(
            excluded[0]["reasons"], ["REJECTED_SCALP_POOR_EDGE_COST_RATIO"]
        )

    def test_large_structural_potential_passes_cost(self):
        included, excluded = self.apply("v2.1", item())
        self.assertEqual(len(included), 1)
        self.assertFalse(excluded)

    def test_v22_risk_symmetry_not_farther_target(self):
        included, excluded = self.apply("v2.2", item(stop=95, target=102))
        self.assertFalse(included)
        self.assertIn("REJECTED_STRUCTURAL_TARGET_INSIDE_ONE_R", excluded[0]["reasons"])

    def test_one_R_equality_allowed(self):
        self.assertEqual(len(self.apply("v2.2", item())[0]), 1)

    def test_frozen_prices_unchanged(self):
        c = item()
        before = copy.deepcopy(c)
        included, _ = self.apply("v2.1", c)
        self.assertEqual(c, before)
        self.assertEqual(included[0]["fixed_initial_stop"], c["fixed_initial_stop"])
        self.assertEqual(included[0]["theoretical_target"], c["theoretical_target"])
        self.assertEqual(included[0]["base_v2_case_id"], c["case_id"])

    def test_holding_and_outcomes_not_admission_variables(self):
        for version in ("v2.1", "v2.2"):
            r = configuration(version)
            self.assertFalse(r["holding_duration_used_for_admission"])
            self.assertFalse(r["outcome_labels_used_for_admission"])
            self.assertFalse(r["TP_percent_fixed"])
            self.assertFalse(r["trade_entry_allowed"])

    def test_no_unbounded_versions(self):
        with self.assertRaises(ValueError):
            configuration("v2.3")

    def test_cost_and_structural_thresholds_fixed(self):
        self.assertEqual(configuration("v2.1")["minimum_edge_cost_ratio"], 5)
        self.assertEqual(configuration("v2.2")["minimum_structural_R"], 1)

    def test_source_rule_never_promoted(self):
        self.assertEqual(
            configuration("v2.1")["classification"], "MACHINE_RULE_PRE_BACKTEST"
        )
        self.assertFalse(configuration("v2.2")["base_geometry_changed"])
