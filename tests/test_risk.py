import unittest

from crypto_bot.strategy.risk import position_quantity_simple, source_aligned_risk_fraction


class RiskTests(unittest.TestCase):
    def test_source_aligned_range(self):
        self.assertTrue(source_aligned_risk_fraction(0.0025))
        self.assertTrue(source_aligned_risk_fraction(0.02))
        self.assertFalse(source_aligned_risk_fraction(0.03))

    def test_simple_position_quantity(self):
        # $100 equity, 1% risk = $1; entry 100, stop 99 -> $1 loss per unit -> qty 1.
        self.assertAlmostEqual(
            position_quantity_simple(equity=100, risk_fraction=0.01, entry_price=100, stop_price=99),
            1.0,
        )

    def test_phase1_sizing_rejects_experimental_risk_by_default(self):
        with self.assertRaises(ValueError):
            position_quantity_simple(equity=100, risk_fraction=0.03, entry_price=100, stop_price=99)

    def test_generic_experiment_can_explicitly_disable_source_guard(self):
        self.assertAlmostEqual(
            position_quantity_simple(
                equity=100,
                risk_fraction=0.03,
                entry_price=100,
                stop_price=99,
                enforce_source_range=False,
            ),
            3.0,
        )

    def test_nonfinite_risk_inputs_are_rejected(self):
        self.assertFalse(source_aligned_risk_fraction(float("nan")))
        with self.assertRaises(ValueError):
            position_quantity_simple(equity=100, risk_fraction=0.01, entry_price=float("inf"), stop_price=99)


if __name__ == "__main__":
    unittest.main()
