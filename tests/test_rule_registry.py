import json
import unittest
from pathlib import Path


class RuleRegistryTests(unittest.TestCase):
    def load_rules(self):
        root = Path(__file__).resolve().parents[1]
        return json.loads((root / "config" / "source_rules.json").read_text(encoding="utf-8"))["rules"]

    def test_registry_has_unique_ids_and_valid_kinds(self):
        rules = self.load_rules()
        ids = [r["rule_id"] for r in rules]
        self.assertEqual(len(ids), len(set(ids)))
        allowed = {"SOURCE_RULE", "TECHNICAL_NORMALIZATION", "BACKTEST_PARAMETER"}
        self.assertTrue(all(r["kind"] in allowed for r in rules))

    def test_source_rules_have_provenance(self):
        for rule in self.load_rules():
            if rule["kind"] == "SOURCE_RULE":
                self.assertTrue(rule.get("source"), rule["rule_id"])
                self.assertTrue(rule.get("page") or rule.get("pages"), rule["rule_id"])

    def test_range_boundary_clarity_preserves_both_source_statements(self):
        rules = {r["rule_id"]: r for r in self.load_rules()}
        self.assertIn("RANGE_UNCLEAR_BOUNDARIES_SKIP_001", rules)
        self.assertIn("RANGE_BOUNDARIES_MAY_BE_NONCRISP_001", rules)
        self.assertEqual(rules["RANGE_UNCLEAR_BOUNDARIES_SKIP_001"]["kind"], "SOURCE_RULE")
        self.assertEqual(rules["RANGE_BOUNDARIES_MAY_BE_NONCRISP_001"]["kind"], "SOURCE_RULE")
        self.assertNotEqual(
            rules["RANGE_UNCLEAR_BOUNDARIES_SKIP_001"]["source"],
            rules["RANGE_BOUNDARIES_MAY_BE_NONCRISP_001"]["source"],
        )

    def test_phase148_structure_lifecycle_preserves_source_and_supersedes_locking_normalization(self):
        rules = {r["rule_id"]: r for r in self.load_rules()}
        self.assertEqual(rules["MS_POST_BOS_OPPOSITE_STRUCTURE_001"]["kind"], "SOURCE_RULE")
        self.assertEqual(rules["MS_BOS_TREND_CHANGE_001"]["kind"], "SOURCE_RULE")
        self.assertEqual(rules["MS_PHASE148_STRUCTURE_LIFECYCLE_001"]["kind"], "TECHNICAL_NORMALIZATION")
        self.assertEqual(rules["MS_PHASE13_POST_BOS_CONF_001"].get("status"), "SUPERSEDED")
        self.assertEqual(
            rules["MS_PHASE13_POST_BOS_CONF_001"].get("superseded_by"),
            "MS_PHASE148_STRUCTURE_LIFECYCLE_001",
        )

    def test_phase1411_structure_ordering_and_live_key_rules_are_explicit_normalizations(self):
        rules = {r["rule_id"]: r for r in self.load_rules()}
        for rule_id in (
            "MS_PHASE1411_INTERLEAVED_SWING_ORDER_001",
            "MS_PHASE1411_TRANSITION_AUDIT_CAUSAL_IDS_001",
            "MS_PHASE1411_LOCAL_EXPECTED_CONF_001",
            "MS_PHASE1411_LIVE_KEY_UPDATE_001",
        ):
            self.assertIn(rule_id, rules)
            self.assertEqual(rules[rule_id]["kind"], "TECHNICAL_NORMALIZATION")



if __name__ == "__main__":
    unittest.main()
