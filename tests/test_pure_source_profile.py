import unittest
from crypto_bot.strategy.profile import PROJECT_POLICY_IDS, PURE_SOURCE_CONFIG, PolicyClass, ProjectPolicyContaminationError, StrategyProfile, StrategyRuntimeConfig
class PureSourceProfileTests(unittest.TestCase):
    def test_pure_source_disables_all_project_switches(self):
        cfg=PURE_SOURCE_CONFIG; self.assertEqual(cfg.strategy_profile,StrategyProfile.PURE_SOURCE); self.assertFalse(cfg.trade_entry_allowed); self.assertFalse(cfg.project_admission_enabled); self.assertFalse(cfg.project_exits_enabled); self.assertFalse(cfg.project_risk_overlays_enabled); self.assertFalse(cfg.project_ranking_scoring_enabled)
    def test_each_known_project_policy_is_rejected(self):
        for policy_id in PROJECT_POLICY_IDS:
            with self.subTest(policy_id=policy_id):
                with self.assertRaises(ProjectPolicyContaminationError): PURE_SOURCE_CONFIG.assert_policy_allowed(policy_id,PolicyClass.PROJECT_POLICY)
    def test_source_and_normalization_policies_are_allowed(self):
        cfg=PURE_SOURCE_CONFIG.record_policy("SRC_SW5_BOS_BODY_CLOSE",PolicyClass.SOURCE_RULE).record_policy("TN_RIGHT_CANDLE_CLOSED",PolicyClass.TECHNICAL_NORMALIZATION); self.assertIn("SRC_SW5_BOS_BODY_CLOSE",cfg.applied_policy_ids); self.assertIn("TN_RIGHT_CANDLE_CLOSED",cfg.applied_policy_ids)
    def test_pure_source_rejects_enabled_project_switch(self):
        for kwargs in ({"project_admission_enabled":True},{"project_exits_enabled":True},{"project_risk_overlays_enabled":True},{"project_ranking_scoring_enabled":True}):
            with self.assertRaises(ProjectPolicyContaminationError): StrategyRuntimeConfig(**kwargs)
    def test_live_entry_can_never_be_enabled(self):
        with self.assertRaises(ValueError): StrategyRuntimeConfig(trade_entry_allowed=True)
if __name__=="__main__": unittest.main()
