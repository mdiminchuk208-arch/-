from __future__ import annotations

import inspect
import json
import unittest

import crypto_bot
from crypto_bot.strategy.mtf_sfp import link_sfp_formations_to_ltf_bos


class Phase1415FreezeTests(unittest.TestCase):
    def test_version_and_registry_are_1415(self):
        self.assertEqual(crypto_bot.__version__, "0.4.20")
        with open("config/source_rules.json", encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["registry_version"], "phase1.4.16-0.4.16")
        by_id = {row["rule_id"]: row for row in payload["rules"]}
        self.assertEqual(by_id["PHASE1415_CROSS_ASSET_GATE_FREEZE_001"]["kind"], "TECHNICAL_NORMALIZATION")
        self.assertEqual(by_id["PHASE1415_RANGE_BOUNDARY_NO_REACTIVATION_001"]["kind"], "TECHNICAL_NORMALIZATION")

    def test_cross_asset_runtime_blocker_is_closed_but_range_and_entry_gates_remain(self):
        source = inspect.getsource(link_sfp_formations_to_ltf_bos)
        self.assertNotIn("CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED", source)
        self.assertNotIn("RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED", source)
        self.assertNotIn("RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED", source)
        self.assertNotIn("RANGE_RETIREMENT_REDRAW_LIFECYCLE_NOT_FORMALIZED", source)
        self.assertIn("SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED", source)
        self.assertIn("SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED", source)

    def test_cross_asset_validated_defaults_are_frozen(self):
        with open("scripts/analyze_cross_asset_robustness.py", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn('parser.add_argument("--evaluation-days", type=int, default=240)', source)
        self.assertIn('parser.add_argument("--suffix-days", type=int, default=60)', source)
        self.assertIn('parser.add_argument("--stabilization-days", type=int, default=30)', source)
        self.assertIn('parser.add_argument("--analysis-warmup-days", type=int, default=0', source)


if __name__ == "__main__":
    unittest.main()
