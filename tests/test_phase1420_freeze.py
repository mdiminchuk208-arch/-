import unittest
from pathlib import Path

import crypto_bot
from crypto_bot.strategy.order_block import derive_qualified_order_block_geometry
from crypto_bot.strategy.trade_plan import OTE_DEEP, OTE_SHALLOW, select_first_opposing_poi_fta


class Phase1420FreezeTests(unittest.TestCase):
    def test_version_is_0420_everywhere(self):
        self.assertEqual(crypto_bot.__version__, "0.4.20")
        pyproject=Path("pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = "0.4.20"', pyproject)

    def test_trade_plan_surface_is_frozen(self):
        self.assertEqual(OTE_SHALLOW, 0.705)
        self.assertEqual(OTE_DEEP, 0.79)
        self.assertTrue(callable(derive_qualified_order_block_geometry))
        self.assertTrue(callable(select_first_opposing_poi_fta))

    def test_ob_poi_automation_remains_fail_closed(self):
        source=Path("src/crypto_bot/strategy/mtf_sfp.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("SOURCE_OB_POI_AUTOMATION_NOT_IMPLEMENTED"), 2)
        self.assertNotIn("SOURCE_SL_TARGET_SELECTION_NOT_IMPLEMENTED", source)
        self.assertNotIn("trade_entry_allowed=True", source)
