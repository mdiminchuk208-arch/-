from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from crypto_bot.strategy.pure_source_branch_registry_v2 import (
    GeometryStatus,
    load_source_branch_registry,
    parse_source_branch_registry,
    source_branch_registry_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "pure_source_branch_registry_v2.json"


class PureSourceBranchRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.registry = load_source_branch_registry(CONFIG)

    def test_registry_is_fail_closed_and_non_ranked(self):
        registry = self.registry
        self.assertFalse(registry.trade_entry_allowed)
        self.assertFalse(registry.financial_backtest_allowed)
        self.assertEqual(registry.project_policy_applied, ())
        self.assertEqual(
            registry.selection_policy,
            "NO_PRECEDENCE_NO_RANKING_NO_OUTCOME_SELECTION",
        )
        self.assertGreaterEqual(len(registry.families), 7)
        for family in registry.families:
            self.assertGreaterEqual(len(family.alternatives), 2)

    def test_exact_source_branch_is_not_trade_eligibility(self):
        midpoint = self.registry.alternative("STB_BTS_MIDPOINT_0_5")
        self.assertTrue(midpoint.is_exact_choice)
        self.assertFalse(midpoint.needs_additional_resolution)
        self.assertEqual(midpoint.exact_value, 0.5)
        self.assertFalse(self.registry.trade_entry_allowed)

        atr14 = self.registry.alternative("SFP_ATR_STANDARD_14")
        self.assertTrue(atr14.is_exact_choice)
        self.assertEqual(atr14.exact_value, 14)
        self.assertFalse(self.registry.trade_entry_allowed)

    def test_bounded_and_relative_branches_preserve_unresolved_geometry(self):
        inside = self.registry.alternative("OB_DIRECT_INSIDE_ZONE")
        self.assertEqual(inside.geometry_status, GeometryStatus.BOUNDED_ZONE_NO_EXACT_QUOTE)
        self.assertTrue(inside.needs_additional_resolution)
        self.assertIn("EXACT_INSIDE_OB_QUOTE_UNSPECIFIED", inside.unresolved)

        stop = self.registry.alternative("OB_STOP_BEYOND_ZONE_EXTREME")
        self.assertEqual(stop.geometry_status, GeometryStatus.RELATIVE_ANCHOR_NO_EXACT_BUFFER)
        self.assertTrue(stop.needs_additional_resolution)

    def test_fta_full_and_partial_are_both_preserved_without_precedence(self):
        full = self.registry.alternative("FTA_FULL_FIXATION")
        partial = self.registry.alternative("FTA_PARTIAL_FIXATION")
        self.assertEqual(full.exact_value, 1.0)
        self.assertTrue(full.is_exact_choice)
        self.assertIsNone(partial.exact_value)
        self.assertTrue(partial.needs_additional_resolution)
        self.assertIn("PARTIAL_FRACTION_UNSPECIFIED", partial.unresolved)
        self.assertEqual(full.family_id, partial.family_id)

    def test_outcome_or_ranking_metadata_is_rejected(self):
        for field, value in (
            ("rank", 1),
            ("score", 99),
            ("win_rate", 0.9),
            ("profit_factor", 2.0),
            ("pnl", 1000),
            ("preferred", True),
        ):
            raw = deepcopy(self.raw)
            raw["families"][0]["alternatives"][0][field] = value
            with self.assertRaisesRegex(ValueError, "forbidden outcome/ranking metadata"):
                parse_source_branch_registry(raw)

    def test_project_policy_and_execution_permission_are_rejected(self):
        raw = deepcopy(self.raw)
        raw["project_policy_applied"] = ["ANTI_SCALP"]
        with self.assertRaisesRegex(ValueError, "PROJECT policy"):
            parse_source_branch_registry(raw)

        raw = deepcopy(self.raw)
        raw["trade_entry_allowed"] = True
        with self.assertRaisesRegex(ValueError, "fail closed"):
            parse_source_branch_registry(raw)

        raw = deepcopy(self.raw)
        raw["financial_backtest_allowed"] = True
        with self.assertRaisesRegex(ValueError, "does not authorize financial backtesting"):
            parse_source_branch_registry(raw)

    def test_registry_fingerprint_is_independent_of_family_and_alternative_order(self):
        first = parse_source_branch_registry(self.raw)
        raw = deepcopy(self.raw)
        raw["families"].reverse()
        for family in raw["families"]:
            family["alternatives"].reverse()
        second = parse_source_branch_registry(raw)
        self.assertEqual(first, second)
        self.assertEqual(
            source_branch_registry_fingerprint(first),
            source_branch_registry_fingerprint(second),
        )

    def test_unknown_family_and_alternative_fail_explicitly(self):
        with self.assertRaises(KeyError):
            self.registry.alternatives("DOES_NOT_EXIST")
        with self.assertRaises(KeyError):
            self.registry.alternative("DOES_NOT_EXIST")


if __name__ == "__main__":
    unittest.main()
