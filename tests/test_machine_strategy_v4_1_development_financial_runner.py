from __future__ import annotations

import copy
import unittest
from decimal import Decimal

import run_machine_strategy_v4_1_development_financial_v1 as runner


class V41DevelopmentFinancialRunnerTests(unittest.TestCase):
    def test_trade_entry_never_enabled(self):
        self.assertFalse(runner.TRADE_ENTRY_ALLOWED)

    def test_pending_retirement_is_terminal_before_fill(self):
        state = {"status": "PENDING", "scenario_id": "P01_Q001"}
        retired = runner._retire_pending(
            state,
            {
                "known_at": 100,
                "structural_break": True,
                "source_retired": False,
                "context_invalid": False,
                "poi_consumed": False,
                "refinement_stale": False,
                "target_completed": False,
                "deadline": False,
                "data_integrity_stop": False,
            },
        )
        self.assertEqual(retired["status"], "UNFILLED_RETIRED")
        self.assertIn("structural_break", retired["retirement_reasons"])

    def test_data_gap_retirement_is_unknown_not_no_fill(self):
        state = {"status": "PENDING", "scenario_id": "P01_Q001"}
        retired = runner._retire_pending(
            state,
            {"known_at": 100, "data_integrity_stop": True},
        )
        self.assertEqual(retired["status"], "UNKNOWN_DATA_GAP")

    def test_closed_cash_keeps_funding_signed_and_doubled_cost_worse(self):
        state = {
            "direction": "LONG",
            "quantity_base": "1",
            "fill_price": "100",
            "exit_price": "110",
            "fixed_R_unit": "10",
            "fill_time_bounds": (0, 0),
            "event_time_bounds": (1800, 1800),
        }
        funding = [(900, Decimal("0.001"), Decimal("105"))]
        result = runner._closed_cash(state, funding)
        base = result["columns"]["base"]
        doubled = result["columns"]["doubled"]
        self.assertLess(base["funding_cash"], 0)
        self.assertLess(base["net_cash"], base["gross_cash"])
        self.assertLess(doubled["net_cash"], base["net_cash"])

    def _closed_state(self, scenario_id: str, net: str):
        value = Decimal(net)
        return {
            "scenario_id": scenario_id,
            "status": "CLOSED",
            "observed_at": 1000,
            "event_time_bounds": (900, 1000),
            "holding_time_bounds": {
                "minimum_seconds": 100,
                "maximum_seconds": 100,
                "exact_seconds": 100,
            },
            "exit_reason": "STRUCTURAL_FTA",
            "columns": {
                "base": {
                    "net_cash": value,
                    "net_R": value,
                    "gross_cash": value + 1,
                    "gross_R": value + 1,
                    "fees_cash": Decimal("0.5"),
                    "fees_R": Decimal("0.5"),
                    "slippage_cash": Decimal("0.5"),
                    "slippage_R": Decimal("0.5"),
                    "funding_cash": Decimal("0"),
                    "funding_R": Decimal("0"),
                },
                "doubled": {
                    "net_cash": value - 1,
                    "net_R": value - 1,
                    "gross_cash": value + 1,
                    "gross_R": value + 1,
                    "fees_cash": Decimal("1"),
                    "fees_R": Decimal("1"),
                    "slippage_cash": Decimal("1"),
                    "slippage_R": Decimal("1"),
                    "funding_cash": Decimal("0"),
                    "funding_R": Decimal("0"),
                },
            },
        }

    def test_all_nine_closed_uses_worst_cash_per_column(self):
        ids = [grid["id"] for grid in runner.scenarios("BTC-USDT-SWAP")]
        states = [self._closed_state(sid, str(i + 1)) for i, sid in enumerate(ids)]
        order = {
            "case_id": "case",
            "product": "BTC-USDT-SWAP",
            "direction": "LONG",
            "branch": "OB",
            "setup_tf": 60,
            "decision_at": 0,
            "context": {"origin_id": "ctx"},
            "entry": "100",
            "stop": "90",
            "target": "110",
            "fixed_R_unit": "10",
            "nearest_fta_id": "fta",
        }
        case = runner._adverse_case(order, states)
        self.assertEqual(case["status"], "CLOSED")
        self.assertEqual(Decimal(case["adverse"]["base"]["net_cash"]), Decimal("1"))
        self.assertEqual(Decimal(case["adverse"]["doubled"]["net_cash"]), Decimal("0"))

    def test_disagreement_is_never_promoted_to_closed(self):
        ids = [grid["id"] for grid in runner.scenarios("BTC-USDT-SWAP")]
        states = [self._closed_state(sid, "1") for sid in ids]
        states[-1] = {
            "scenario_id": ids[-1],
            "status": "SCENARIO_INELIGIBLE",
            "reason": "SYNTHETIC",
        }
        order = {
            "case_id": "case",
            "product": "BTC-USDT-SWAP",
            "direction": "LONG",
            "branch": "OB",
            "setup_tf": 60,
            "decision_at": 0,
            "context": {"origin_id": "ctx"},
            "entry": "100",
            "stop": "90",
            "target": "110",
            "fixed_R_unit": "10",
            "nearest_fta_id": "fta",
        }
        case = runner._adverse_case(order, states)
        self.assertEqual(case["status"], "COMPATIBILITY_DISAGREEMENT")
        self.assertTrue(case["closed_values_diagnostic_only"])

    def test_empty_case_set_cannot_pass_qualification(self):
        prereg = {
            "qualification": {
                "closed_trades_min": 200,
                "win_rate_min": "0.70",
                "profit_factor_min": "1.20",
                "doubled_cost_profit_factor_min": "1.00",
                "max_drawdown_R_max": "20",
                "max_consecutive_net_losses_max": 10,
                "wilson_95pct_win_rate_lower_bound_min": "0.60",
                "each_coin_direction_closed_min": 30,
                "largest_calendar_quarter_profit_share_max": "0.50",
                "largest_coin_profit_share_max": "0.80",
                "filled_unknown_exit_max": 0,
            }
        }
        result = runner._qualification([], prereg)
        self.assertEqual(
            result["decision"],
            "MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP",
        )


if __name__ == "__main__":
    unittest.main()
