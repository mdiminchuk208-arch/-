"""Paired execution/plan symmetry tests, without any historical re-execution."""

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from machine_strategy_v2_core import epsilon, plan_case
from machine_strategy_v2_execution import FEE, SLIPPAGE, execute
from test_machine_strategy_v2_core import fixture
from test_machine_strategy_v2_execution import case
from test_original_v1_1_evidence_adapter_v2 import bars

D = Decimal
REFLECTION_CONSTANT = D(30)
SCENARIOS = {
    "open_target": [(10, 12, 9.5, 11)],
    "wick_stop": [(11, 11.5, 8, 10)],
    "dual_hit": [(10, 13, 8, 11)],
    "wick_target_ambiguity": [(11, 13, 9.5, 10)],
    "prefill_stop_gap": [(8, 10, 7, 9)],
    "prefill_target_gap": [(13, 14, 11, 12)],
    "open_improvement": [(9.5, 10, 9.2, 9.7), (9.7, 12.5, 9.2, 12)],
    "postfill_stop_gap": [(10, 11, 9.5, 10), (8, 9, 7, 8)],
    "postfill_target_gap": [(10, 11, 9.5, 10), (13, 14, 12.5, 13)],
    "expiry": [(11, 11.5, 10.5, 11)] * 5,
    "order_censored": [(11, 11.5, 10.5, 11)],
    "filled_censored": [(10, 11, 9.5, 10)],
    "SFP_body": [
        (10, 11, 9.4, 9.6),
        (9.6, 10, 9.3, 9.4),
        (9.4, 10, 9.2, 9.3),
        (9.3, 10, 9.1, 9.2),
    ],
}


def reflected_values(values, constant=REFLECTION_CONSTANT):
    return [
        (
            constant - D(str(o)),
            constant - D(str(lo)),
            constant - D(str(hi)),
            constant - D(str(c)),
        )
        for o, hi, lo, c in values
    ]


def reflected_case(original, constant=REFLECTION_CONSTANT):
    c = copy.deepcopy(original)
    c["direction"] = "SHORT"
    for key in (
        "theoretical_entry",
        "fixed_initial_stop",
        "theoretical_target",
        "stop_anchor",
    ):
        c[key] = str(constant - D(c[key]))
    return c


class FailureSymmetryTests(unittest.TestCase):
    def test_reflected_execution_events_and_gross(self):
        for name, values in SCENARIOS.items():
            with self.subTest(scenario=name):
                c = case()
                if name == "SFP_body":
                    c["branch"] = "SFP"
                long = execute(c, {15: bars(values, tf=15)})
                short = execute(
                    reflected_case(c), {15: bars(reflected_values(values), tf=15)}
                )
                for key in (
                    "status",
                    "filled",
                    "closed",
                    "fill_at",
                    "exit_at",
                    "exit_reason",
                    "hold_hours",
                    "fill_time_bounds",
                    "exit_time_bounds",
                ):
                    self.assertEqual(long.get(key), short.get(key), (name, key))
                if long["filled"]:
                    self.assertEqual(D(long["fill_price"]) + D(short["fill_price"]), 30)
                    self.assertEqual(
                        D(long["initial_price_risk"]), D(short["initial_price_risk"])
                    )
                if long["closed"]:
                    self.assertEqual(D(long["exit_price"]) + D(short["exit_price"]), 30)
                    self.assertEqual(D(long["Gross_R"]), D(short["Gross_R"]))
                    for fee_key, rate in (("Fees_R", FEE), ("Slippage_R", SLIPPAGE)):
                        expected = (
                            rate
                            * (D(short["fill_price"]) + D(short["exit_price"]))
                            / D(short["initial_price_risk"])
                        )
                        self.assertEqual(D(short[fee_key]), expected)
                    self.assertEqual(
                        D(short["Net_R"]),
                        D(short["Gross_R"])
                        - D(short["Fees_R"])
                        - D(short["Slippage_R"]),
                    )

    def test_price_scaling_preserves_all_normalized_values(self):
        for name, values in SCENARIOS.items():
            with self.subTest(scenario=name):
                c = case()
                if name == "SFP_body":
                    c["branch"] = "SFP"
                before = execute(c, {15: bars(values, tf=15)})
                scaled = copy.deepcopy(c)
                for key in (
                    "theoretical_entry",
                    "fixed_initial_stop",
                    "theoretical_target",
                    "stop_anchor",
                ):
                    scaled[key] = str(D(c[key]) * 10)
                after = execute(
                    scaled,
                    {
                        15: bars(
                            [tuple(D(str(p)) * 10 for p in row) for row in values],
                            tf=15,
                        )
                    },
                )
                for key in ("status", "Gross_R", "Fees_R", "Slippage_R", "Net_R"):
                    self.assertEqual(before[key], after[key], (name, key))

    def test_reflection_cost_difference_is_price_based(self):
        long = execute(case(), {15: bars(SCENARIOS["open_target"], tf=15)})
        short = execute(
            reflected_case(case()),
            {15: bars(reflected_values(SCENARIOS["open_target"]), tf=15)},
        )
        self.assertEqual(D(long["Gross_R"]), D(short["Gross_R"]))
        self.assertNotEqual(D(long["Net_R"]), D(short["Net_R"]))

    def test_all_five_branches_mirror_with_explicit_relative_epsilon(self):
        for branch in ("SFP", "OB", "STB", "BREAKER", "RANGE"):
            with self.subTest(branch=branch):
                pending, frames = fixture(branch)
                long, long_reason = plan_case("BTCUSDT", pending, frames, 180, set())
                self.assertIsNotNone(long, long_reason)
                short_pending = copy.deepcopy(pending)
                short_pending["direction"] = "SHORT"
                short_pending["extreme"] = D(30) - pending["extreme"]
                for key in ("zone", "range"):
                    short_pending[key]["low"] = D(30) - pending[key]["high"]
                    short_pending[key]["high"] = D(30) - pending[key]["low"]
                    if "direction" in short_pending[key]:
                        short_pending[key]["direction"] = "SHORT"
                short_pending["formation_bar"] = bars(
                    reflected_values([(10, 12, 9, 11)])
                )[0]
                for tf in (60, 240, 1440):
                    context = frames[tf].context
                    old_low, old_high = context["low"], context["high"]
                    context.update(
                        direction="SHORT",
                        low=D(30) - old_high,
                        high=D(30) - old_low,
                        EQ=D(30) - context["EQ"],
                        protected_price=D(30) - context["protected_price"],
                        OTE=sorted(D(30) - x for x in context["OTE"]),
                    )
                pool = frames[60].pools["pool"]["payload"]
                pool.update(side="LOW", price=str(D(30) - D(pool["price"])))
                refinement_zone = frames[15].candidates_zones()[0]
                low, high = refinement_zone["low"], refinement_zone["high"]
                refinement_zone.update(
                    direction="SHORT", low=D(30) - high, high=D(30) - low
                )
                frames[15].confirmations[0]["direction"] = "SHORT"
                frames[15].bos[0]["direction"] = "SHORT"
                short, short_reason = plan_case(
                    "BTCUSDT", short_pending, frames, 180, set()
                )
                self.assertIsNotNone(short, short_reason)
                self.assertEqual(
                    D(long["theoretical_entry"]) + D(short["theoretical_entry"]), 30
                )
                expected_stop_sum = (
                    D(30)
                    if branch == "SFP"
                    else D(30)
                    + epsilon(short_pending["extreme"])
                    - epsilon(pending["extreme"])
                )
                self.assertEqual(
                    D(long["fixed_initial_stop"]) + D(short["fixed_initial_stop"]),
                    expected_stop_sum,
                )
                self.assertEqual(long["FTA_kind"], short["FTA_kind"])
                expected_target_sum = D(30)
                if branch == "RANGE":
                    expected_target_sum += epsilon(
                        short_pending["range"]["low"]
                    ) - epsilon(pending["range"]["high"])
                self.assertEqual(
                    D(long["theoretical_target"]) + D(short["theoretical_target"]),
                    expected_target_sum,
                )


if __name__ == "__main__":
    unittest.main()
