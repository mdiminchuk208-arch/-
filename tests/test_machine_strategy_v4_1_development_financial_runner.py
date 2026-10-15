from __future__ import annotations

import tempfile
import unittest
from decimal import ROUND_UP, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

import audit_machine_strategy_v4_1_development_financial_v1 as auditor
import run_machine_strategy_v4_1_development_financial_v1 as runner
from machine_strategy_v4_1_execution_binding import all_scenario_plans
from machine_strategy_v4_1_guarded_runner import fixture
from machine_strategy_v4_1_synthetic_source_bridge import ClosedSourceBridge


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
        funding = [(900, Decimal("0.001"), Decimal(105))]
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
                    "funding_cash": Decimal(0),
                    "funding_R": Decimal(0),
                },
                "doubled": {
                    "net_cash": value - 1,
                    "net_R": value - 1,
                    "gross_cash": value + 1,
                    "gross_R": value + 1,
                    "fees_cash": Decimal(1),
                    "fees_R": Decimal(1),
                    "slippage_cash": Decimal(1),
                    "slippage_R": Decimal(1),
                    "funding_cash": Decimal(0),
                    "funding_R": Decimal(0),
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
        self.assertEqual(Decimal(case["adverse"]["base"]["net_cash"]), Decimal(1))
        self.assertEqual(Decimal(case["adverse"]["doubled"]["net_cash"]), Decimal(0))

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


class V41PreRunIntegrityTests(unittest.TestCase):
    def test_authorization_verifies_transitive_implementation_pins(self):
        with (
            patch(
                "verify_machine_strategy_v4_1_implementation_v1.resume",
                side_effect=ValueError("PIN_CHANGED"),
            ) as verify,
            patch.object(runner, "market_inputs") as data,
        ):
            with self.assertRaisesRegex(ValueError, "PIN_CHANGED"):
                runner._run()
            verify.assert_called_once_with(runner.IMPLEMENTATION_MANIFEST_SHA256)
            data.assert_not_called()

    def test_authorization_does_not_accept_caller_context(self):
        with self.assertRaises(TypeError):
            runner._authorization(True)
        with self.assertRaises(TypeError):
            runner._authorization(manifest_path="arbitrary.json")

    def test_existing_output_or_started_reservation_blocks_before_data(self):
        for name in (*runner.FINAL_FILES, "RUN_STARTED.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                out = Path(directory)
                (out / name).write_text("existing")
                with (
                    patch.object(runner, "OUT", out),
                    patch.object(runner, "market_inputs") as data,
                ):
                    with self.assertRaisesRegex(
                        runner.FinancialGateBlocked, "ONE_SHOT_OUTPUT_ALREADY_EXISTS"
                    ):
                        runner._run()
                    data.assert_not_called()

    def test_atomic_reservation_refuses_concurrent_second_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / "RUN_STARTED.json").write_text("reserved")
            with (
                patch.object(runner, "OUT", out),
                patch.object(runner, "_authorization", return_value={}),
                patch.object(runner, "market_inputs") as data,
            ):
                with self.assertRaises(FileExistsError):
                    runner._run()
                data.assert_not_called()

    def test_unresolved_plan_retains_unknown_state(self):
        state = runner._scenario_state(
            {},
            {
                "scenario_id": "P01_Q001",
                "status": "UNRESOLVED",
                "reason": "DATA_UNKNOWN",
            },
            {},
        )
        self.assertEqual(state["status"], "UNRESOLVED")

    def test_deadline_and_structural_retirement_are_distinct(self):
        state = {"status": "PENDING"}
        self.assertEqual(
            runner._retire_pending(state, {"known_at": 57600, "deadline": True})[
                "status"
            ],
            "UNFILLED_EXPIRED",
        )
        self.assertEqual(
            runner._retire_pending(
                state, {"known_at": 57600, "structural_break": True}
            )["status"],
            "UNFILLED_RETIRED",
        )

    def _registered_source(self, name, eof_at=None):
        order, bars, funding, _ = fixture(name)
        if eof_at is not None:
            bars = [bar for bar in bars if bar["end"] <= eof_at]
        order = runner._jsonable(order)
        order["scenario_plans"] = all_scenario_plans(
            order, completed_close=order["decision_close"]
        )
        order.setdefault("context", {"origin_id": "registered-completed-seed"})
        order.setdefault("nearest_fta_id", "fixture-fta")
        for key in ("entry", "stop", "target"):
            order.setdefault(key, order["scenario_plans"][0][key])
        bridge = ClosedSourceBridge(order, bars)
        source = bridge.source
        source.catalog = lambda cutoff=None: ([order], {})
        return order, bridge.native, funding, source

    def _drive(self, order, native, funding, source):
        with patch.object(runner, "V41HistoricalAdapter", return_value=source):
            return runner._drive_decision_group(
                order["product"], {15: native}, funding, [order], 0, native[-1].end
            )[order["case_id"]]

    def test_actual_source_h4_midbar_driver_long_short(self):
        for direction in ("long", "short"):
            with self.subTest(direction=direction):
                order, native, funding, source = self._registered_source(
                    direction + "_stb_h4_midbar"
                )
                states = self._drive(order, native, funding, source)
                self.assertEqual(len(states), 9)
                self.assertEqual(states[0]["status"], "CLOSED")
                self.assertEqual(states[0]["fill_time_bounds"], (33300, 34200))
                self.assertEqual(
                    source.inventory.state(order["entry_poi_id"])["reserved_at"], 32400
                )

    def test_actual_source_final_close_contact_retires_before_eof(self):
        order, native, funding, source = self._registered_source(
            "long_stb_h4_no_fill", 43200
        )
        states = self._drive(order, native, funding, source)
        self.assertEqual(states[0]["status"], "UNFILLED_RETIRED")
        self.assertEqual(states[0]["observed_at"], 43200)
        self.assertIn("poi_consumed", states[0]["retirement_reasons"])

    def test_driver_gap_retains_unknown(self):
        order, native, funding, source = self._registered_source("long_stb_h4_midbar")
        native = [bar for bar in native if bar.start != 33300]
        states = self._drive(order, native, funding, source)
        self.assertEqual(states[0]["status"], "UNKNOWN_DATA_GAP")

    def test_driver_deadline_before_observer(self):
        order, native, funding, source = self._registered_source("long_stb_h4_midbar")
        source.lifecycle_flags = lambda order, at, scenario: {
            "known_at": at,
            "deadline": at >= 32400,
        }
        with patch.object(runner, "_model_observer") as observer:
            states = self._drive(order, native, funding, source)
            observer.assert_not_called()
        self.assertEqual(states[0]["status"], "UNFILLED_EXPIRED")

    def test_observer_wait_is_preserved_without_aborting_run(self):
        order, native, funding, source = self._registered_source("long_stb_h4_midbar")
        with patch.object(
            runner,
            "_model_observer",
            side_effect=runner.core.ContractWait("WAIT_HISTORICAL_TICK_METADATA"),
        ):
            states = self._drive(order, native, funding, source)
        self.assertEqual(states[0]["status"], "UNRESOLVED")

    def test_ambient_context_cannot_change_driver_or_auditor(self):
        first = self._registered_source("long_stb_h4_midbar")
        expected = runner._jsonable(self._drive(*first))
        second = self._registered_source("long_stb_h4_midbar")
        with localcontext() as context:
            context.prec = 6
            context.rounding = ROUND_UP
            actual = runner._jsonable(self._drive(*second))
        self.assertEqual(actual, expected)
        order = first[0]
        case = runner._adverse_case(order, expected)
        arithmetic = auditor._verify_case_arithmetic(
            {order["case_id"]: order}, [case], {order["product"]: []}
        )
        self.assertGreater(arithmetic["closed_arithmetic_checks"], 0)
        self.assertEqual(
            runner._group_stats([case], "base")["net_R"],
            auditor._serialize(auditor._stats([case], "base"))["net_R"],
        )

    def test_auditor_rejects_adverse_value_tamper(self):
        order, native, funding, source = self._registered_source("long_stb_h4_midbar")
        case = runner._adverse_case(order, self._drive(order, native, funding, source))
        case["adverse"]["base"]["net_cash"] = "99999"
        with self.assertRaisesRegex(
            auditor.AuditStop, "ADVERSE_SELECTION_OR_VALUES_CHANGED"
        ):
            auditor._verify_case_arithmetic({order["case_id"]: order}, [case])

    def test_independent_signed_funding_witness_matches_exact_ledger(self):
        for direction in ("LONG", "SHORT"):
            state = {
                "direction": direction,
                "quantity_base": "0.33333333333333333333333333333333333333333333333333",
                "fill_price": "100",
                "exit_price": "110",
                "fixed_R_unit": "3",
                "fill_time_bounds": [0, 900],
                "event_time_bounds": [1800, 2700],
            }
            rows = [
                (900, Decimal("0.001"), Decimal(105)),
                (1800, Decimal("-0.002"), Decimal(108)),
            ]
            cash = runner._jsonable(runner._closed_cash(state, rows))
            actual, witness = auditor._funding_witness(state, rows)
            self.assertEqual(actual, Decimal(cash["columns"]["base"]["funding_cash"]))
            self.assertEqual(witness, cash["funding_timing_witness"])


if __name__ == "__main__":
    unittest.main()
