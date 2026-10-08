import unittest

from crypto_bot.strategy.order_block import OrderBlockEvidence, assess_order_block


class OrderBlockTests(unittest.TestCase):
    def valid_evidence(self, **changes):
        data = dict(
            liquidity_swept=True,
            aggressive_impulse=True,
            engulfs_previous_candle=True,
            bos_confirmed=True,
            in_htf_poi=True,
            in_structural_impulse=True,
            aligned_with_trend=True,
            imbalance_present=True,
            test_number=1,
            ltf_reaction_confirmed=False,
        )
        data.update(changes)
        return OrderBlockEvidence(**data)

    def test_valid_ob_with_imb_is_a_quality(self):
        a = assess_order_block(self.valid_evidence())
        self.assertTrue(a.formation_valid)
        self.assertTrue(a.trade_eligible)
        self.assertEqual(a.quality, "A")

    def test_ob_without_imb_remains_formation_compatible_but_not_trade_eligible(self):
        a = assess_order_block(self.valid_evidence(imbalance_present=False))
        self.assertTrue(a.formation_valid)
        self.assertFalse(a.trade_eligible)
        self.assertEqual(a.quality, "IMB_UNRESOLVED")
        self.assertIn("imb_hard_vs_soft_rule_unresolved", a.reasons)

    def test_ob_without_bos_is_invalid(self):
        a = assess_order_block(self.valid_evidence(bos_confirmed=False))
        self.assertFalse(a.formation_valid)
        self.assertFalse(a.trade_eligible)
        self.assertIn("bos_confirmed", a.reasons)

    def test_second_test_does_not_invalidate_formation(self):
        a = assess_order_block(self.valid_evidence(test_number=2))
        self.assertTrue(a.formation_valid)
        self.assertFalse(a.trade_eligible)
        self.assertIn("repeat_test_requires_ltf_reaction", a.reasons)

    def test_second_test_can_be_eligible_after_ltf_reaction(self):
        a = assess_order_block(self.valid_evidence(test_number=2, ltf_reaction_confirmed=True))
        self.assertTrue(a.formation_valid)
        self.assertTrue(a.trade_eligible)

    def test_invalid_test_number(self):
        with self.assertRaises(ValueError):
            assess_order_block(self.valid_evidence(test_number=0))


if __name__ == "__main__":
    unittest.main()
