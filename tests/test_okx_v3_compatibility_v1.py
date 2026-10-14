"""Only registered toy execution; no historical financial input/evaluation."""

import json
import random
import sys
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import machine_strategy_v3_contracts as core
import machine_strategy_v3_historical_adapter as original
import okx_v3_compatibility_binding_v1 as binding
import okx_v3_compatibility_runner_v1 as runner


class CompatibilityTests(unittest.TestCase):
    def test_campaign_requires_explicit_supported_READY_one_shot_scope(self):
        for header in (
            "STRATEGY_AUTONOMY_TO_PLATFORM_RECONNECT",
            "OKX Compatibility Implementation + READY Review",
        ):
            self.assertTrue(
                runner.campaign_permits_historical(
                    "# Current Campaign — " + header + "\nREADY authorizes one-shot"
                )
            )
        for task in (
            "",
            "# Other\nREADY one-shot",
            "# Current Campaign — OKX Compatibility Implementation + READY Review\nWAIT",
        ):
            self.assertFalse(runner.campaign_permits_historical(task))

    def test_ETH_quantity_identity_cash_and_signed_funding_symmetry(self):
        long = runner.run_registered_toy("LONG_ETH")
        short = runner.run_registered_toy("SHORT_ETH")
        for case in (long, short):
            self.assertEqual(case["product"], "ETH-USDT-SWAP")
            self.assertEqual(case["strategy_symbol_alias"], "ETHUSDT")
            self.assertEqual(case["status"], "CLOSED")
            self.assertEqual(
                Decimal(case["all_scenarios"][2]["quantity_base"]), Decimal("0.7")
            )
            for s in case["all_scenarios"]:
                a = s["columns"]["base"]
                q, entry, exit_price = (
                    Decimal(s[k]) for k in ("quantity_base", "fill_price", "exit_price")
                )
                self.assertEqual(
                    Decimal(a["fees_cash"]), Decimal(".0006") * q * (entry + exit_price)
                )
        self.assertLess(
            Decimal(long["all_scenarios"][0]["columns"]["base"]["funding_cash"]), 0
        )
        self.assertEqual(
            Decimal(short["all_scenarios"][0]["columns"]["base"]["funding_cash"]), 0
        )

    def test_checkpoint_rejects_changed_bytes_and_membership(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(runner, "OUT", Path(tmp)),
        ):
            path = runner.OUT / "cases.jsonl"
            path.write_text('{"case_id":"same","value":1}\n')
            h = runner.checkpoint_run()
            runner.verify_run_checkpoint(h)
            path.write_text('{"case_id":"same","value":2}\n')
            with self.assertRaisesRegex(runner.FinancialBlocked, "BYTES_CHANGED"):
                runner.verify_run_checkpoint(h)
            h = runner.checkpoint_run()
            (runner.OUT / "extra").write_text("extra")
            with self.assertRaisesRegex(runner.FinancialBlocked, "NAMESPACE_CHANGED"):
                runner.verify_run_checkpoint(h)

    def test_checkpoint_requires_external_pin(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(runner, "OUT", Path(tmp)),
        ):
            runner.checkpoint_run()
            with self.assertRaises(runner.FinancialBlocked):
                runner.verify_run_checkpoint(None)

    def test_nonempty_causal_prefix_future_mutation_and_exclusive_end(self):
        from test_machine_strategy_v3_readiness_conformance import bars

        values = [
            (100, 102, 99, 100),
            (100, 101, 95, 99),
            (99, 103, 98, 100),
            (100, 101, 94, 98),
            (98, 102, 93, 101),
        ]
        native_values = []
        for o, h, lo, c in values:
            native_values.extend(
                [
                    (o, h, lo, o),
                    (o, o, o, o),
                    (o, o, o, o),
                    (o, max(o, c), min(o, c), c),
                ]
            )
        native_values.extend([(100, 100, 100, 100)] * (96 - len(native_values)))
        native = bars(native_values)
        changed = native + bars([(100, 300, 10, 250)] * 4, start=86400)
        a, _ = original.derive_market(native)
        b, _ = original.derive_market(changed)
        first = binding.CompatibilityAdapter("BTC-USDT-SWAP", a, 0, 86400)
        second = binding.CompatibilityAdapter("BTC-USDT-SWAP", b, 0, 86400)
        x = first.catalog(cutoff=18000)
        y = second.catalog(cutoff=18000)
        self.assertEqual(x, y)
        self.assertGreater(len(x[1]["raw_native_formations"]), 0)
        self.assertGreater(
            sum(v for k, v in x[1]["counts"].items() if k.startswith("RAW_")), 0
        )
        exclusive = binding.CompatibilityAdapter("BTC-USDT-SWAP", a, 0, 18000)
        orders, audit = exclusive.catalog()
        self.assertEqual(audit["known_through"], 14400)
        self.assertTrue(all(o["decision_at"] < 18000 for o in orders))

    def test_exact_nine_cartesian_grids_and_no_fake_epochs(self):
        for product in binding.PRODUCT_ALIAS:
            rows = binding.scenarios(product)
            self.assertEqual(len(rows), 9)
            self.assertEqual(len({r["id"] for r in rows}), 9)
            self.assertTrue(all("verified" not in r for r in rows))
            self.assertTrue(
                all(r["classification"].startswith("SYNTHETIC") for r in rows)
            )
        self.assertEqual(
            [binding.scenarios("BTC-USDT-SWAP")[i]["tick"] for i in (0, 3, 6)],
            ["0.1", "0.5", "2.0"],
        )

    def test_signal_method_same_bytecode_and_inherited_run(self):
        self.assertIs(
            binding.CompatibilityAdapter.plan_pending.__code__,
            original.HistoricalAdapter.plan_pending.__code__,
        )
        self.assertIs(
            binding.CompatibilityAdapter.run.__code__,
            original.HistoricalAdapter.run.__code__,
        )

    def test_emitted_candidate_target_reservation_prefix_and_conflict_audit(self):
        from original_v1_1_financial_data import Bar

        rng = random.Random(7701)
        price = Decimal(10000)
        native = []
        for i in range(96 * 60):
            close = price * Decimal(str(1 + rng.uniform(-0.004, 0.004)))
            high = max(price, close) * Decimal(str(1 + rng.uniform(0.0001, 0.003)))
            low = min(price, close) * Decimal(str(1 - rng.uniform(0.0001, 0.003)))
            native.append(Bar(i * 900, (i + 1) * 900, price, high, low, close))
            price = close
        cutoff = 50 * 86400
        future = [
            replace(
                b,
                open=Decimal(100),
                high=Decimal(99999),
                low=Decimal(1),
                close=Decimal(888),
            )
            if b.start >= cutoff
            else b
            for b in native
        ]
        prefix_market, _ = original.derive_market(
            [b for b in native if b.end <= cutoff]
        )
        full_market, _ = original.derive_market(native)
        changed_market, _ = original.derive_market(future)

        def adapter(market):
            return binding.CompatibilityAdapter(
                "BTC-USDT-SWAP", market, 0, native[-1].end
            )

        a = adapter(prefix_market).catalog(cutoff)
        b = adapter(full_market).catalog(cutoff)
        c = adapter(changed_market).catalog(cutoff)
        self.assertGreater(len(a[0]), 0)
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertTrue(a[1]["reservation_audit"])
        for order in a[0]:
            self.assertLessEqual(order["confirmation_known_at"], order["decision_at"])
            self.assertTrue(
                all(
                    t["known_at"] <= order["decision_at"]
                    for t in order["all_FTA_inventory"]
                )
            )
        conflicted = adapter(full_market)
        first = a[0][0]
        conflicted.registry = {"physical": (first["physical_idea_id"],), "pois": ()}
        orders, audit = conflicted.catalog(cutoff)
        recorded = [
            r for r in audit["reservation_audit"] if r["reason"].startswith("REJECT")
        ]
        self.assertTrue(recorded)
        self.assertTrue(
            any(
                p["case_id"] == first["base_signal_case_id"]
                for r in recorded
                for p in r["proposals"]
            )
        )
        self.assertNotIn(first["case_id"], {o["case_id"] for o in orders})

    def test_fake_verified_epoch_rejected(self):
        grid = {**binding.scenarios("BTC-USDT-SWAP")[0], "verified": True}
        with self.assertRaises(core.ContractReject):
            binding.modeled_grid([grid], "BTCUSDT", core.CONTRACT_TYPE, 0, 0)

    def test_price_lattice_changes_do_not_round_observations(self):
        self.assertIsNot(binding._model_observer, core.observe_m15_bar)
        case = runner.run_registered_toy("LONG")
        self.assertEqual(case["status"], "CLOSED")
        self.assertTrue(all(r["fill_price"] == "100" for r in case["all_scenarios"]))
        # Native opening 101 is off the P20 synthetic grid of 2; it remains usable.
        self.assertEqual(case["all_scenarios"][6]["entry"], "100")

    def test_all_scenarios_preserved_and_minimum_cash_selected(self):
        case = runner.run_registered_toy("LONG")
        for column in ("base", "doubled"):
            expected = min(
                case["all_scenarios"],
                key=lambda s: (
                    Decimal(s["columns"][column]["net_cash"]),
                    s["scenario_id"],
                ),
            )
            self.assertEqual(
                case["adverse"][column]["scenario_id"], expected["scenario_id"]
            )
            self.assertEqual(
                case["adverse"][column]["net_cash"],
                expected["columns"][column]["net_cash"],
            )

    def test_constant_reference_R_denominator_and_floor_size(self):
        case = runner.run_registered_toy("LONG")
        units = {s["fixed_R_unit"] for s in case["all_scenarios"]}
        self.assertEqual(len(units), 1)
        self.assertEqual(case["all_scenarios"][2]["quantity_base"], "0.9800")
        for s in case["all_scenarios"]:
            self.assertGreater(Decimal(s["quantity_base"]), 0)
            self.assertLessEqual(Decimal(s["quantity_base"]), 1)

    def test_doubled_cost_same_path_and_funding(self):
        case = runner.run_registered_toy("LONG")
        for state in case["all_scenarios"]:
            a, b = state["columns"]["base"], state["columns"]["doubled"]
            for field in ("gross_cash", "funding_cash"):
                self.assertEqual(a[field], b[field])
            self.assertEqual(Decimal(b["fees_cash"]), 2 * Decimal(a["fees_cash"]))
            self.assertEqual(
                Decimal(b["slippage_cash"]), 2 * Decimal(a["slippage_cash"])
            )

    def test_positive_funding_long_debit_short_uncertain_credit_excluded(self):
        long = runner.run_registered_toy("LONG")["all_scenarios"][0]
        short = runner.run_registered_toy("SHORT")["all_scenarios"][0]
        self.assertLess(Decimal(long["columns"]["base"]["funding_cash"]), 0)
        self.assertEqual(Decimal(short["columns"]["base"]["funding_cash"]), 0)

    def test_negative_funding_mirrors_payer(self):
        long = runner.run_registered_toy("LONG_NEGATIVE_FUNDING")["all_scenarios"][0]
        short = runner.run_registered_toy("SHORT_NEGATIVE_FUNDING")["all_scenarios"][0]
        self.assertEqual(Decimal(long["columns"]["base"]["funding_cash"]), 0)
        self.assertLess(Decimal(short["columns"]["base"]["funding_cash"]), 0)

    def test_funding_witness_order_is_coherent(self):
        case = runner.run_registered_toy("LONG")
        for s in case["all_scenarios"]:
            w = s["funding_timing_witness"]
            self.assertLessEqual(
                tuple(w["model_fill_event_slot"]), tuple(w["model_exit_event_slot"])
            )
            for t in w["settlements_included"]:
                self.assertLess(tuple(w["model_fill_event_slot"]), (t, 0))
                self.assertLess((t, 0), tuple(w["model_exit_event_slot"]))

    def test_intrabar_unknown_is_not_converted_to_closed(self):
        case = runner.run_registered_toy("LONG_INTRABAR")
        self.assertEqual(case["status"], "COMPATIBILITY_DISAGREEMENT")
        self.assertTrue(
            all(s["status"] == "WAIT_INTRABAR_ORDER" for s in case["all_scenarios"])
        )
        self.assertEqual(case["adverse"], {})

    def test_unfilled_EOF_not_counted_as_closed(self):
        case = runner.run_registered_toy("LONG_UNFILLED")
        self.assertEqual(case["status"], "ALL_SCENARIOS_NO_FILL")
        self.assertEqual(len(case["all_scenarios"]), 9)

    def test_eligibility_disagreement_retains_diagnostic_closed_losses_or_wins(self):
        case = runner.run_registered_toy("LONG_ELIGIBILITY_DISAGREEMENT")
        self.assertEqual(case["status"], "COMPATIBILITY_DISAGREEMENT")
        self.assertEqual(len(case["all_scenarios"]), 9)
        self.assertTrue(case["closed_values_diagnostic_only"])
        self.assertTrue(case["adverse"])
        self.assertTrue(
            any(s["status"] == "SCENARIO_INELIGIBLE" for s in case["all_scenarios"])
        )

    def test_qualification_STOP_dominates_subset_metrics(self):
        summary = runner.run_registered_toy_summary("LONG_ELIGIBILITY_DISAGREEMENT")
        self.assertEqual(summary["decision"], "MACHINE_STRATEGY_V3_QUALIFICATION_STOP")
        self.assertEqual(summary["base"]["CLOSED"], 0)

    def test_one_toy_win_does_not_relax_sample_threshold(self):
        summary = runner.run_registered_toy_summary("LONG")
        self.assertEqual(summary["decision"], "MACHINE_STRATEGY_V3_QUALIFIED_FAIL")
        self.assertIn("CLOSED", summary["numeric_failures"])

    def test_NO_capability_blocks_before_source_or_output(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(runner, "OUT", Path(tmp) / "out"),
            patch.object(runner, "market_inputs") as loader,
        ):
            with self.assertRaises(runner.FinancialBlocked):
                runner.run_once(None)
            loader.assert_not_called()
            self.assertFalse(runner.OUT.exists())

    def test_forged_capability_is_not_issued(self):
        forged = runner.Capability(runner._MARKER, "0" * 64, binding.POLICY_COMMIT)
        with self.assertRaises(runner.FinancialBlocked):
            runner.check(forged)

    def test_all_financial_kernels_fail_without_scope(self):
        for function, args in [
            (runner._drive_case, ({}, [], [])),
            (runner._closed_cash, ({}, [])),
            (runner._funding_min, ({}, [], Decimal(1))),
            (runner._stats, ([], "base")),
            (runner._qualification, ([],)),
            (runner._adverse_case, ({}, [])),
        ]:
            with (
                self.subTest(function=function.__name__),
                self.assertRaises(runner.FinancialBlocked),
            ):
                function(*args)

    def test_registered_name_does_not_allow_custom_history(self):
        order, native, funding = runner.toy_fixture("LONG")
        changed = [replace(native[0], high=Decimal(999)), native[1]]
        with (
            runner._evaluation_scope(fixture="LONG"),
            self.assertRaises(runner.FinancialBlocked),
        ):
            runner._drive_case(order, changed, funding)

    def test_fixture_scope_cannot_accept_arbitrary_closed_state_or_metrics(self):
        with runner._evaluation_scope(fixture="LONG"):
            with self.assertRaises(runner.FinancialBlocked):
                runner._closed_cash({"exit_price": "999"}, [])
            with self.assertRaises(runner.FinancialBlocked):
                runner._stats([{"status": "CLOSED", "case_id": "historical"}], "base")

    def test_unknown_toy_is_rejected(self):
        with self.assertRaises(runner.FinancialBlocked):
            runner.run_registered_toy("BTC_history")

    def test_toy_replay_byte_identical(self):
        for name in runner.TOY_NAMES:
            a = json.dumps(runner.run_registered_toy(name), sort_keys=True)
            b = json.dumps(runner.run_registered_toy(name), sort_keys=True)
            self.assertEqual(
                sha256(a.encode()).hexdigest(), sha256(b.encode()).hexdigest()
            )

    def test_ready_authorization_missing_external_pin_rejected(self):
        with self.assertRaises(runner.FinancialBlocked):
            runner.authorize(None, None)

    def test_frozen_qualification_targets_match_stage_A(self):
        pre, _ = binding.read_policy()
        old = json.loads(
            (binding.ROOT / pre["parent_stage_A"]["preregistration_path"]).read_text()
        )
        self.assertEqual(pre["qualification_unchanged"], old["qualification"])


if __name__ == "__main__":
    unittest.main()
