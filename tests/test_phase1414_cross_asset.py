from __future__ import annotations

import json
import unittest


class Phase1414CrossAssetTests(unittest.TestCase):
    def test_registry_contains_cross_asset_harness_policy(self):
        with open('config/source_rules.json', encoding='utf-8') as fh:
            payload = json.load(fh)
        self.assertEqual(payload['registry_version'], 'phase1.4.16-0.4.16')
        by_id = {row['rule_id']: row for row in payload['rules']}
        self.assertEqual(by_id['PHASE1414_CROSS_ASSET_BASKET_POLICY_001']['kind'], 'TECHNICAL_NORMALIZATION')
        self.assertEqual(by_id['PHASE1414_CROSS_ASSET_INVARIANT_GATE_001']['kind'], 'TECHNICAL_NORMALIZATION')

    def test_phase1414_harness_policy_remains_historical_registry_evidence(self):
        with open('config/source_rules.json', encoding='utf-8') as fh:
            payload = json.load(fh)
        by_id = {row['rule_id']: row for row in payload['rules']}
        self.assertIn('PHASE1414_CROSS_ASSET_BASKET_POLICY_001', by_id)
        self.assertIn('PHASE1414_CROSS_ASSET_INVARIANT_GATE_001', by_id)


if __name__ == '__main__':
    unittest.main()
