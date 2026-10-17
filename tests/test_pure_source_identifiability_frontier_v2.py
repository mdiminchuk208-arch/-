from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "pure_source_identifiability_frontier_v2.json"


class PureSourceIdentifiabilityFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frontier = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_fail_closed_baseline_flags(self):
        cfg = self.frontier
        self.assertEqual(cfg["baseline_identifiability"], "NOT_IDENTIFIABLE")
        self.assertFalse(cfg["trade_entry_allowed"])
        self.assertFalse(cfg["financial_backtest_allowed"])
        self.assertFalse(cfg["paper_allowed"])
        self.assertFalse(cfg["live_allowed"])
        self.assertFalse(cfg["private_api_allowed"])

    def test_stage16_does_not_add_source_or_project_rules(self):
        self.assertEqual(self.frontier["source_rule_changes"], [])
        self.assertEqual(self.frontier["project_policy_applied"], [])
        authority = self.frontier["authority"]
        self.assertFalse(authority["historical_engine_is_source_truth"])
        self.assertFalse(authority["historical_pnl_can_resolve_source_ambiguity"])

    def test_blocker_classes_are_explicit_and_nonempty(self):
        expected = {
            "MISSING_SOURCE_QUALITATIVE_PROVENANCE",
            "SOURCE_PERMITTED_VARIANTS_NO_PRECEDENCE",
            "SOURCE_GEOMETRY_UNSPECIFIED",
            "SOURCE_EXIT_ALLOCATION_UNSPECIFIED",
            "SOURCE_CONTEXT_OR_IDENTITY_UNSPECIFIED",
        }
        blockers = self.frontier["blocker_classes"]
        self.assertEqual({row["class"] for row in blockers}, expected)
        for row in blockers:
            self.assertTrue(row["items"])
            self.assertTrue(row["resolution_mode"])
            self.assertTrue(row["forbidden_shortcut"])

    def test_explicit_source_variants_are_enumerated_not_ranked(self):
        row = next(
            item
            for item in self.frontier["blocker_classes"]
            if item["class"] == "SOURCE_PERMITTED_VARIANTS_NO_PRECEDENCE"
        )
        self.assertEqual(
            row["resolution_mode"],
            "ENUMERATE_AS_SEPARATE_SOURCE_BRANCHES_WITHOUT_RANKING",
        )
        forbidden = row["forbidden_shortcut"].lower()
        for token in ("pnl", "win rate", "pf", "expectancy", "score"):
            self.assertIn(token, forbidden)

    def test_source_priority_is_frozen(self):
        self.assertEqual(
            self.frontier["authority"]["source_priority"],
            [
                "Методичка",
                "SW5",
                "SW9",
                "SW11",
                "SW12",
                "SW22",
                "other confirmed ORIGINAL SOURCE materials",
                "SOURCE Rule Registry",
            ],
        )

    def test_project_overlays_are_not_allowed_as_next_work(self):
        prohibited = " ".join(self.frontier["prohibited_next_work"]).lower()
        self.assertIn("project_overlay", prohibited)
        self.assertIn("paper", prohibited)
        self.assertIn("live", prohibited)
        self.assertIn("private", prohibited)


if __name__ == "__main__":
    unittest.main()
