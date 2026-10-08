from __future__ import annotations

import json
import unittest

from crypto_bot.strategy.global_opportunity import PRODUCTION_GLOBAL_CLUSTER_WINDOW_MINUTES
from crypto_bot.strategy.market_analysis import StructureAnalysisMode, analyze_market


class Phase1413FreezeTests(unittest.TestCase):
    def test_production_analysis_default_is_source_conservative(self):
        self.assertEqual(analyze_market([]).analysis_mode, StructureAnalysisMode.SOURCE_CONSERVATIVE)

    def test_production_global_cluster_window_is_exact_timestamp(self):
        self.assertEqual(PRODUCTION_GLOBAL_CLUSTER_WINDOW_MINUTES, 0)

    def test_registry_contains_freeze_and_cross_asset_gate(self):
        with open("config/source_rules.json", encoding="utf-8") as fh:
            payload = json.load(fh)
        by_id = {row["rule_id"]: row for row in payload["rules"]}
        self.assertEqual(payload["registry_version"], "phase1.4.16-0.4.16")
        self.assertEqual(by_id["MS_PHASE1413_PRODUCTION_MODE_FREEZE_001"]["kind"], "TECHNICAL_NORMALIZATION")
        self.assertEqual(by_id["MTF_PHASE1413_GLOBAL_CLUSTER_FREEZE_001"]["kind"], "TECHNICAL_NORMALIZATION")
        self.assertEqual(by_id["PHASE1413_CROSS_ASSET_ROBUSTNESS_GATE_001"]["kind"], "TECHNICAL_NORMALIZATION")


if __name__ == "__main__":
    unittest.main()
