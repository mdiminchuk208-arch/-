import json
import unittest
from pathlib import Path

import crypto_bot


class Phase1416RangeGeometryTests(unittest.TestCase):
    def test_version_and_registry(self):
        self.assertEqual(crypto_bot.__version__, "0.4.20")
        payload = json.loads(Path("config/source_rules.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["registry_version"], "phase1.4.21-0.4.21")
        ids = [r["rule_id"] for r in payload["rules"]]
        self.assertIn("RANGE_DIRECTIONAL_GEOMETRY_001", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_entry_engine_remains_blocked(self):
        source = Path("src/crypto_bot/strategy/mtf_sfp.py").read_text(encoding="utf-8")
        self.assertNotIn("RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED", source)
        self.assertNotIn("RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED", source)
        self.assertNotIn("RANGE_RETIREMENT_REDRAW_LIFECYCLE_NOT_FORMALIZED", source)
        self.assertIn("SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED", source)


if __name__ == "__main__":
    unittest.main()
