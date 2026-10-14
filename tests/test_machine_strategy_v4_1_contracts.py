from __future__ import annotations

from decimal import Decimal, localcontext
import unittest

from machine_strategy_v4_1_contracts import (
    V41Reject,
    SelectedPoiState,
    canonical_decimal,
    latch_eligibility,
    ledger_decimal,
    native_contact,
    payoff_equality_passes,
    physical_identity,
    register_emission,
    selected_poi_identity,
    transport_design_value_to_ledger,
)


class TestMachineStrategyV41Contracts(unittest.TestCase):
    def base(self, **overrides):
        values = dict(
            formation_id="formation-A",
            source_parent_id="parent-A",
            selected_poi_id="poi-A",
            selected_poi_kind="RANGE_BOUNDARY",
            selected_poi_native_tf=60,
            formation_known_at=1_000,
            reaction_required_at=1_900,
        )
        values.update(overrides)
        return SelectedPoiState(**values)

    def test_identity_canonicalization_is_stable(self):
        self.assertEqual(canonical_decimal(Decimal("1.2300")), "1.23")
        self.assertEqual(canonical_decimal(Decimal("0E-10")), "0")
        self.assertEqual(
            physical_identity("X", Decimal("1.2300"), "A"),
            physical_identity("X", Decimal("1.23"), "A"),
        )

    def test_stb_body_is_distinct_from_parent(self):
        selected = selected_poi_identity(
            family="STB",
            formation_id="f",
            body_low=Decimal("99.0"),
            body_high=Decimal("101.0"),
        )
        self.assertNotEqual(selected, "parent-ob")

    def test_breaker_and_range_generated_handles_are_deterministic(self):
        breaker_a = selected_poi_identity(
            family="BREAKER",
            source_parent_id="ob-parent",
            breaker_formation_known_at=2_000,
            direction="LONG",
        )
        breaker_b = selected_poi_identity(
            family="BREAKER",
            source_parent_id="ob-parent",
            breaker_formation_known_at=2_000,
            direction="LONG",
        )
        self.assertEqual(breaker_a, breaker_b)
        range_a = selected_poi_identity(
            family="RANGE",
            range_id="r1",
            direction="SHORT",
            boundary_price=Decimal("100.00"),
        )
        range_b = selected_poi_identity(
            family="RANGE",
            range_id="r1",
            direction="SHORT",
            boundary_price=Decimal("100"),
        )
        self.assertEqual(range_a, range_b)

    def test_first_admissible_eligibility_is_monotonic(self):
        state = self.base()
        latched = latch_eligibility(
            state,
            cutoff=2_000,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        later = latch_eligibility(
            latched,
            cutoff=2_100,
            origin_conf_id="conf-B",
            origin_conf_known_at=2_050,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        self.assertEqual(later.origin_conf_id, "conf-A")
        self.assertEqual(later.eligibility_at, 2_000)

    def test_partial_native_interval_cannot_consume(self):
        state = latch_eligibility(
            self.base(),
            cutoff=2_000,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        result = native_contact(
            state,
            native_bar_open=1_800,
            native_bar_close=2_100,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        self.assertIsNone(result.consumed_at)

    def test_contact_is_published_at_native_close(self):
        state = latch_eligibility(
            self.base(),
            cutoff=2_000,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        result = native_contact(
            state,
            native_bar_open=2_000,
            native_bar_close=2_300,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        self.assertEqual(result.consumed_at, 2_300)

    def test_required_range_reaction_is_exempt_then_next_contact_consumes(self):
        state = latch_eligibility(
            self.base(),
            cutoff=2_000,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        exempt = native_contact(
            state,
            native_bar_open=2_000,
            native_bar_close=2_300,
            intersects=True,
            native_context_admissible_at_open=True,
            is_required_reaction_contact=True,
        )
        self.assertIsNone(exempt.consumed_at)
        self.assertEqual(exempt.required_reaction_exempt_contact_at, 2_300)
        consumed = native_contact(
            exempt,
            native_bar_open=2_300,
            native_bar_close=2_600,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        self.assertEqual(consumed.consumed_at, 2_600)

    def test_pre_emission_consumption_rejects(self):
        consumed = self.base(
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            eligibility_at=2_000,
            consumed_at=2_300,
        )
        with self.assertRaisesRegex(V41Reject, "REJECT_SELECTED_POI_PRECONSUMED"):
            register_emission(
                consumed,
                emission_decision_at=2_300,
                proposal_selected_conf_id="conf-B",
            )

    def test_proposal_conf_does_not_rebase_origin(self):
        state = self.base(
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            eligibility_at=2_000,
        )
        emitted = register_emission(
            state,
            emission_decision_at=2_200,
            proposal_selected_conf_id="conf-B",
        )
        self.assertEqual(emitted.origin_conf_id, "conf-A")
        self.assertEqual(emitted.proposal_selected_conf_id, "conf-B")

    def test_decimal50_transport_is_not_recomputed_at_decimal80(self):
        with localcontext() as ctx:
            ctx.prec = 50
            third = Decimal(1) / Decimal(3)
        serialized, parsed80 = transport_design_value_to_ledger(third)
        self.assertEqual(parsed80, ledger_decimal(serialized))
        self.assertEqual(serialized, canonical_decimal(third))

    def test_payoff_equality_passes(self):
        self.assertTrue(payoff_equality_passes(Decimal("1"), Decimal("1")))
        self.assertFalse(payoff_equality_passes(Decimal("0.999"), Decimal("1")))

    def test_float_is_never_canonical_design_input(self):
        with self.assertRaises(V41Reject):
            canonical_decimal(1.5)


if __name__ == "__main__":
    unittest.main()
