"""Audit input isolation, accounting detection and descriptive tail contracts."""

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_machine_strategy_failure_v1 import (
    assert_causal,
    extremes,
    geometry,
    metrics,
    quantiles,
    timing_issue,
    verify_accounting,
    verify_chronology,
    verify_partitions,
)
from machine_strategy_v2_execution import execute
from test_machine_strategy_v2_execution import case
from test_original_v1_1_evidence_adapter_v2 import bars


def frozen_case(direction="LONG"):
    c = case(direction)
    c.update(
        branch="SFP",
        context_relation="TREND",
        PD_at_entry="DISCOUNT",
        OTE_at_entry=False,
        FTA_kind="STRUCTURAL_LIQUIDITY",
        known_at=0,
        formation_at=0,
        poi_born_at=0,
        selected_impulse={"known_at": 0},
    )
    return c


class FailureAuditTests(unittest.TestCase):
    def test_planned_geometry_uses_plan_not_improved_fill(self):
        c = frozen_case()
        g = geometry(c)
        self.assertEqual(Decimal(g["planned_target_R"]), 2)
        r = execute(c, {15: bars([(9.5, 10, 9.2, 9.7), (9.7, 12.5, 9.2, 12)], tf=15)})
        self.assertEqual(r["initial_price_risk"], "0.5")
        self.assertEqual(g, geometry(c))

    def test_preentry_outcome_contamination_rejected(self):
        for key in (
            "Net_R",
            "Fees_R",
            "filled",
            "hold_hours",
            "initial_price_risk",
            "WIN",
            "mfe",
            "exit_reason",
            "exit_time_bounds",
            "fill_time_bounds",
            "fill_observation_at",
            "known_entry_fee_R",
            "known_entry_slippage_R",
            "censored_at",
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                geometry({**frozen_case(), key: 1})

    def test_nested_future_known_at_rejected(self):
        c = frozen_case()
        c["liquidity_inventory"] = [{"known_at": 1}]
        with self.assertRaises(ValueError):
            geometry(c)

    def test_unsafe_entry_flag_rejected(self):
        with self.assertRaises(ValueError):
            geometry({**frozen_case(), "trade_entry_allowed": True})

    def test_future_impulse_end_swing_rejected(self):
        c = frozen_case()
        c["selected_impulse"]["end_swing_at"] = 1
        with self.assertRaises(ValueError):
            geometry(c)

    def test_consumed_preentry_case_rejected(self):
        with self.assertRaises(ValueError):
            geometry({**frozen_case(), "consumed_at": 0})

    def test_invalid_plan_or_direction_rejected(self):
        for replacement in (
            {"fixed_initial_stop": "11"},
            {"direction": "FLAT"},
            {"theoretical_target": "9"},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                geometry({**frozen_case(), **replacement})

    def test_accounting_detects_corrupted_net(self):
        c = frozen_case()
        r = execute(c, {15: bars([(10, 12, 9.5, 11)], tf=15)})
        verify_accounting(r)
        with self.assertRaises(ValueError):
            verify_accounting({**r, "Net_R": str(Decimal(r["Net_R"]) + 1)})

    def test_accounting_detects_direction_sign_corruption(self):
        c = frozen_case()
        r = execute(c, {15: bars([(10, 12, 9.5, 11)], tf=15)})
        with self.assertRaises(ValueError):
            verify_accounting({**r, "direction": "SHORT"})

    def test_unresolved_not_imputed_zero(self):
        r = execute(frozen_case(), {15: bars([(10, 13, 8, 11)], tf=15)})
        verify_accounting(r)
        with self.assertRaises(ValueError):
            verify_accounting({**r, "Net_R": "0"})

    def test_funding_unknown_cannot_be_changed_to_zero(self):
        r = execute(frozen_case(), {15: bars([(10, 12, 9.5, 11)], tf=15)})
        with self.assertRaises(ValueError):
            verify_accounting({**r, "Funding_R": "0"})

    def test_unresolved_funding_unknown_cannot_be_zero(self):
        r = execute(frozen_case(), {15: bars([(10, 13, 8, 11)], tf=15)})
        with self.assertRaises(ValueError):
            verify_accounting({**r, "Funding_R": "0"})

    def test_saved_execution_order_rejects_reversed_observations(self):
        r = execute(frozen_case(), {15: bars([(10, 12, 9.5, 11)], tf=15)})
        verify_chronology(r)
        for replacement in (
            {"fill_at": -1},
            {"fill_observation_at": -1},
            {"consumed_at": -1},
            {"exit_at": -1},
            {"exit_known_at": -1},
            {"closed": False},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                verify_chronology({**r, **replacement})

    def test_saved_partitions_reject_missing_filled_case(self):
        r = execute(frozen_case(), {15: bars([(10, 12, 9.5, 11)], tf=15)})
        counts = {
            "cases": 1,
            "orders": 1,
            "filled": 1,
            "CLOSED": 1,
            "status_counts": {"CLOSED": 1},
        }
        verify_partitions([r], [r], [r], counts)
        with self.assertRaises(ValueError):
            verify_partitions([r], [], [r], counts)

    def test_saved_counts_reject_status_or_cohort_drift(self):
        r = execute(frozen_case(), {15: bars([(10, 12, 9.5, 11)], tf=15)})
        counts = {
            "cases": 1,
            "orders": 1,
            "filled": 1,
            "CLOSED": 1,
            "status_counts": {"CLOSED": 1},
        }
        for replacement in (
            {"cases": 2},
            {"status_counts": {"WAIT_INTRABAR_ORDER": 1}},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                verify_partitions([r], [r], [r], {**counts, **replacement})

    def test_descriptive_tail_does_not_modify_cohort(self):
        c = frozen_case()
        r = execute(c, {15: bars([(10, 12, 9.5, 11)], tf=15)})
        before = copy.deepcopy(r)
        e = extremes([r], {c["case_id"]: geometry(c)})
        self.assertEqual(
            e["LONG"]["leave_one_extreme_out_diagnostic"]["without_best_R"], 0
        )
        self.assertEqual(r, before)

    def test_unresolved_is_excluded_from_closed_metrics(self):
        c = frozen_case()
        r = execute(c, {15: bars([(10, 13, 8, 11)], tf=15)})
        m = metrics([r], {c["case_id"]: geometry(c)})
        self.assertEqual((m["FILLED"], m["CLOSED"]), (1, 0))
        self.assertIsNone(m["Expectancy_R"])

    def test_same_bar_time_bounds_issue_is_exposed(self):
        c = case()
        r = execute(c, {15: bars([(11, 11.5, 8, 10)], tf=15)})
        self.assertTrue(timing_issue(r))
        self.assertEqual(r["exit_time_bounds"], [900, 900])
        self.assertEqual(r["fill_time_bounds"], [0, 900])

    def test_linear_quantiles_even_sample(self):
        self.assertEqual(quantiles([1, 3])["median"], 2)
        self.assertIsNone(quantiles([]))

    def test_local_saved_case_projection_determinism(self):
        before = frozen_case()
        after = {**frozen_case(), "case_id": "future", "decision_at": 900}
        prefix = [geometry(c) for c in [before, after] if c["decision_at"] <= 0]
        mutated = {**after, "theoretical_target": "100"}
        self.assertEqual(
            prefix, [geometry(c) for c in [before, mutated] if c["decision_at"] <= 0]
        )
        assert_causal(before, 0)


if __name__ == "__main__":
    unittest.main()
