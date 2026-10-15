"""Implementation regressions from independent engineering counterexamples."""

import unittest
from decimal import ROUND_UP, Decimal, localcontext
from types import SimpleNamespace

from machine_strategy_v4_1_contracts import (
    SelectedPoiState,
    V41Reject,
    V41Wait,
    ledger_decimal,
    native_contact,
)
from machine_strategy_v4_1_funding_guard import (
    SyntheticFundingCapability,
    adverse_funding_witness,
    synthetic_capability,
)
from machine_strategy_v4_1_guarded_runner import (
    FinancialBlocked,
    evaluate_fixture,
    evaluate_historical_catalog,
    fixture,
)
from machine_strategy_v4_1_historical_adapter import V41HistoricalAdapter, serial
from machine_strategy_v4_1_selected_poi_inventory import SelectedPoiInventory
from machine_strategy_v4_1_synthetic_source_bridge import ClosedSourceBridge
from machine_strategy_v4_readiness_core import V4Wait


class Regressions(unittest.TestCase):
    def test_shared_refined_physical_id_has_two_parent_associations(self):
        inv = SelectedPoiInventory()
        kwargs = {
            "family": "OB",
            "source_parent_id": "p1",
            "native_tf": 15,
            "formation_known_at": 0,
            "reaction_required_at": 900,
            "existing_id": "zone",
            "zone_born_at": 1800,
            "origin_bos_id": "BOS",
            "expected_origin_conf_id": "CONF",
            "expected_origin_conf_known_at": 2700,
        }
        inv.register(formation_id="f1", **kwargs)
        kwargs["source_parent_id"] = "p2"
        kwargs["formation_known_at"] = 900
        inv.register(formation_id="f2", **kwargs)
        self.assertEqual(len(inv), 1)
        self.assertEqual(len(inv.snapshot()["candidate_associations"]["zone"]), 2)
        with self.assertRaisesRegex(V41Wait, "LOWER_BOUND"):
            inv.latch_m15(
                "zone",
                cutoff=900,
                origin_conf_id="CONF",
                origin_conf_known_at=2700,
                family_prerequisites_complete=True,
                m4_gate_admissible=True,
                completed_context_admissible=True,
                formation_id="f1",
            )
        with self.assertRaisesRegex(V41Reject, "UNRELATED_REFINED"):
            inv.latch_m15(
                "zone",
                cutoff=2700,
                origin_conf_id="OTHER",
                origin_conf_known_at=2700,
                family_prerequisites_complete=True,
                m4_gate_admissible=True,
                completed_context_admissible=True,
                formation_id="f1",
            )
        inv.latch_m15(
            "zone",
            cutoff=2700,
            origin_conf_id="CONF",
            origin_conf_known_at=2700,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
            formation_id="f2",
        )
        owner = inv.state("zone")
        self.assertEqual(
            (
                owner["formation_id"],
                owner["source_parent_id"],
                owner["formation_known_at"],
            ),
            ("f2", "p2", 900),
        )
        inv.emit_h1_proposal(
            "zone",
            emission_decision_at=3600,
            proposal_selected_conf_id="LATEST",
            formation_id="f1",
        )
        self.assertEqual(inv.state("zone")["formation_id"], "f2")
        self.assertEqual(inv.state("zone")["source_parent_id"], "p2")
        self.assertEqual(inv.snapshot()["events"][-1]["formation_id"], "f1")
        with self.assertRaisesRegex(V41Reject, "ALREADY_RESERVED"):
            inv.emit_h1_proposal(
                "zone",
                emission_decision_at=4500,
                proposal_selected_conf_id="NEW",
                formation_id="f2",
            )

    def test_refined_inventory_exists_during_context_wait_and_latches_old_origin(self):
        source = object.__new__(V41HistoricalAdapter)
        source.inventory = SelectedPoiInventory()
        source.meta, source.contact_active = {}, set()
        bos_a = {"id": "BOS_A", "known_at": 900, "direction": "LONG"}
        conf_a = {
            "id": "CONF_A",
            "confirmation_id": "confirmation_A",
            "bos_id": "BOS_A",
            "known_at": 1800,
            "direction": "LONG",
        }
        frame = SimpleNamespace(
            bos=[bos_a],
            bos_times=[900],
            bos_by_id={"BOS_A": bos_a},
            confirmations=[conf_a],
            confirm_times=[1800],
            confirmed_bos={"BOS_A": 1800},
        )
        source.frames = {15: frame}
        zone = {
            "id": "refined_A",
            "kind": "OB",
            "origin_bos_id": "BOS_A",
            "born_at": 1800,
            "low": Decimal("100.00"),
            "high": Decimal("101.00"),
        }
        source.zones_by_bos = {"BOS_A": [zone]}
        item = {
            "branch": "OB",
            "direction": "LONG",
            "formation_id": "formation",
            "formation_at": 0,
            "reaction_at": None,
            "setup_tf": 60,
            "zone": {"id": "parent", "low": Decimal(99), "high": Decimal(102)},
        }
        source._reaction = lambda item, at: item.update(reaction_at=900)

        def wait_context(*args):
            raise V4Wait("WAIT_NO_HTF_CONTEXT")

        source._context = wait_context
        with self.assertRaisesRegex(V4Wait, "NO_HTF_CONTEXT"):
            source.prepare(item, 2700, True)
        state = source.inventory.state("refined_A")
        self.assertIsNone(state["eligibility_at"])
        self.assertEqual(state["origin_conf_id"], "confirmation_A")
        self.assertEqual(state["origin_conf_known_at"], 1800)
        self.assertEqual(state["reaction_required_at"], 900)
        self.assertEqual(state["expected_origin_conf_id"], "confirmation_A")
        self.assertEqual(source.inventory.snapshot()["events"][0]["known_at"], 1800)
        source._context = lambda *args: ({"known_at": 2700}, {})
        source.prepare(item, 2700, True)
        source.inventory.observe_native_bar(
            "refined_A",
            native_bar_open=2700,
            native_bar_close=3600,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        with self.assertRaisesRegex(V41Reject, "PRECONSUMED"):
            source.prepare(item, 3600, False)
        # Fresh inventory isolates context-WAIT -> later CONF admissible latch.
        source.inventory = SelectedPoiInventory()
        source._register(item, zone)
        bos_b = {"id": "BOS_B", "known_at": 2700, "direction": "LONG"}
        conf_b = {
            "id": "CONF_B",
            "confirmation_id": "confirmation_B",
            "bos_id": "BOS_B",
            "known_at": 3600,
            "direction": "LONG",
        }
        frame.bos.append(bos_b)
        frame.bos_times.append(2700)
        frame.bos_by_id["BOS_B"] = bos_b
        frame.confirmations.append(conf_b)
        frame.confirm_times.append(3600)
        frame.confirmed_bos["BOS_B"] = 3600
        source._context = lambda *args: ({"known_at": 3600}, {})
        source.prepare(item, 3600, True)
        state = source.inventory.state("refined_A")
        self.assertEqual(
            (state["eligibility_at"], state["origin_conf_id"]), (3600, "confirmation_A")
        )
        source.inventory.observe_native_bar(
            "refined_A",
            native_bar_open=3600,
            native_bar_close=4500,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        # Latest-BOS proposal eligibility stays independent of the physical clock.
        with self.assertRaisesRegex(V41Wait, "ORIGIN_BOUND"):
            source.prepare(item, 3600, False)
        self.assertEqual(
            serial({"price": Decimal("100.00"), "nested": [Decimal("0.0100")]}),
            {"price": "100", "nested": ["0.01"]},
        )

    def test_completed_reaction_is_published_even_when_context_waits(self):
        inv = SelectedPoiInventory()
        kwargs = {
            "family": "RANGE",
            "formation_id": "f",
            "source_parent_id": "range",
            "native_tf": 240,
            "formation_known_at": 0,
            "reaction_required_at": None,
            "direction": "LONG",
            "range_id": "r",
            "boundary_price": "100",
        }
        state = inv.register(**kwargs)
        kwargs["reaction_required_at"] = 14400
        inv.register(**kwargs)
        state = inv.state(state.selected_poi_id)
        self.assertEqual(state["reaction_required_at"], 14400)
        self.assertIsNone(state["eligibility_at"])

    def test_h4_real_adapter_bridge_all_families_and_directions(self):
        for side in ("long", "short"):
            for family in ("sfp", "ob", "stb", "breaker", "range"):
                for mode in ("midbar", "no_fill", "context_late"):
                    with self.subTest(side=side, family=family, mode=mode):
                        result = evaluate_fixture(f"{side}_{family}_h4_{mode}")
                        self.assertEqual(len(result["scenario_states"]), 9)
                        for state in result["scenario_states"]:
                            bridge = state["source_bridge_receipt"]
                            selected = bridge["selected_state"]
                            self.assertEqual(selected["reserved_at"], 32400)
                            self.assertTrue(bridge["actual_adapter_lifecycle_flags"])
                            self.assertTrue(
                                all(
                                    t["flags"]["known_at"] <= t["open"]
                                    for t in bridge["M15_OPEN_flag_trace"]
                                )
                            )
                            if mode == "no_fill":
                                self.assertEqual(state["status"], "RETIRED_PENDING")
                                self.assertEqual(
                                    state["observed_at"],
                                    34200 if family in ("ob", "sfp") else 43200,
                                )
                            else:
                                self.assertEqual(state["status"], "CLOSED")
                                self.assertEqual(
                                    tuple(state["fill_time_bounds"]), (33300, 34200)
                                )
                            if mode == "context_late" and family not in ("ob", "sfp"):
                                self.assertIsNone(selected["consumed_at"])
                            else:
                                self.assertEqual(
                                    selected["consumed_at"],
                                    34200 if family in ("ob", "sfp") else 43200,
                                )

    def test_equal_cutoff_contact_precedes_reservation_in_actual_adapter_bridge(self):
        for side in ("long", "short"):
            for family in ("sfp", "ob", "stb", "breaker", "range"):
                order, bars, _, _ = fixture(f"{side}_{family}_h4_equal_cutoff")
                with self.assertRaisesRegex(V41Reject, "PRECONSUMED"):
                    ClosedSourceBridge(order, bars)

    def test_exemption_flag_cannot_erase_subsequent_contact(self):
        state = SelectedPoiState(
            "f",
            "p",
            "id",
            "RANGE_BOUNDARY",
            60,
            0,
            reaction_required_at=3600,
            eligibility_at=4500,
        )
        result = native_contact(
            state,
            native_bar_open=7200,
            native_bar_close=10800,
            intersects=True,
            native_context_admissible_at_open=True,
            is_required_reaction_contact=True,
        )
        self.assertEqual(result.consumed_at, 10800)
        with self.assertRaisesRegex(V41Reject, "NATIVE_BAR_INTERVAL"):
            native_contact(
                state,
                native_bar_open=7200,
                native_bar_close=7500,
                intersects=True,
                native_context_admissible_at_open=True,
            )

    def test_registered_funding_name_never_licenses_arbitrary_input(self):
        cap = synthetic_capability("LONG_POSITIVE_FUNDING")
        with self.assertRaisesRegex(V41Reject, "UNREGISTERED_SYNTHETIC_FUNDING_INPUT"):
            adverse_funding_witness(
                cap,
                direction="LONG",
                fill_time_bounds=(100, 100),
                exit_time_bounds=(300, 300),
                settlements=[(200, "0.5", "1000000")],
                quantity_base="1",
            )
        with self.assertRaisesRegex(V41Reject, "NO_REGISTERED"):
            adverse_funding_witness(
                SyntheticFundingCapability(object(), "LONG_POSITIVE_FUNDING"),
                direction="LONG",
                fill_time_bounds=(100, 100),
                exit_time_bounds=(300, 300),
                settlements=[(200, "0.001", "100")],
                quantity_base="1",
            )

    def test_ledger_transport_rejects_noncanonical_strings(self):
        for value in ["1E-4", "1.00", "-0", "NaN"]:
            with self.assertRaises(V41Reject):
                ledger_decimal(value)
        self.assertEqual(ledger_decimal("0.0001"), Decimal("0.0001"))

    def test_runner_scope_is_independent_of_ambient_decimal_context(self):
        names = ["long_ob_target", "short_funding", "long_stb_h4_midbar"]
        expected = [evaluate_fixture(name) for name in names]
        with localcontext() as ctx:
            ctx.prec = 6
            ctx.rounding = ROUND_UP
            self.assertEqual([evaluate_fixture(name) for name in names], expected)

    def test_registered_nine_scenario_runner_is_mirrored_and_history_closed(self):
        for family in ["sfp", "ob", "stb", "breaker", "range"]:
            for side in ["long", "short"]:
                result = evaluate_fixture(f"{side}_{family}_target")
                self.assertEqual(len(result["scenario_states"]), 9)
                self.assertTrue(
                    all(s["status"] == "CLOSED" for s in result["scenario_states"])
                )
                for s in result["scenario_states"]:
                    self.assertEqual(s["version"], "MACHINE_STRATEGY_v4.1")
                    self.assertIsInstance(s["canonical_design_transport"]["entry"], str)
        with self.assertRaises(FinancialBlocked):
            evaluate_historical_catalog([])
        with self.assertRaises(FinancialBlocked):
            evaluate_fixture("user-history")


if __name__ == "__main__":
    unittest.main()
