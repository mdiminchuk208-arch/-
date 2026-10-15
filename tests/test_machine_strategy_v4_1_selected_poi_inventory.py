from __future__ import annotations

import unittest
from decimal import Decimal

from machine_strategy_v4_1_contracts import V41Reject, V41Wait
from machine_strategy_v4_1_selected_poi_inventory import SelectedPoiInventory


class TestSelectedPoiInventory(unittest.TestCase):
    def test_range_required_reaction_exempt_then_consumed(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="RANGE",
            formation_id="f",
            source_parent_id="r",
            native_tf=60,
            formation_known_at=0,
            reaction_required_at=3600,
            direction="LONG",
            range_id="r",
            boundary_price="100",
        )
        exempt = inventory.observe_native_bar(
            state.selected_poi_id,
            native_bar_open=0,
            native_bar_close=3600,
            intersects=True,
            native_context_admissible_at_open=True,
            is_required_reaction_contact=True,
        )
        self.assertIsNone(exempt.consumed_at)
        inventory.latch_m15(
            state.selected_poi_id,
            cutoff=4500,
            origin_conf_id="A",
            origin_conf_known_at=4500,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        consumed = inventory.observe_native_bar(
            state.selected_poi_id,
            native_bar_open=7200,
            native_bar_close=10800,
            intersects=True,
            native_context_admissible_at_open=True,
            is_required_reaction_contact=True,
        )
        self.assertEqual(consumed.consumed_at, 10800)

    def test_reaction_can_latch_after_physical_registration_but_not_reset(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="RANGE",
            formation_id="range-late-reaction",
            source_parent_id="range-parent",
            native_tf=60,
            formation_known_at=1_000,
            reaction_required_at=None,
            direction="LONG",
            range_id="range-2",
            boundary_price=Decimal(101),
        )
        reacted = inventory.set_reaction_required_at(
            state.selected_poi_id, known_at=1_900
        )
        self.assertEqual(reacted.reaction_required_at, 1_900)
        same = inventory.set_reaction_required_at(state.selected_poi_id, known_at=1_900)
        self.assertEqual(same.reaction_required_at, 1_900)
        with self.assertRaisesRegex(V41Reject, "REJECT_REACTION_TIMESTAMP_RESET"):
            inventory.set_reaction_required_at(state.selected_poi_id, known_at=2_000)

    def test_late_reaction_is_part_of_eligibility_lower_bound(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="SFP",
            formation_id="sfp-late-reaction",
            source_parent_id="sfp-parent",
            native_tf=15,
            formation_known_at=1_000,
            reaction_required_at=None,
            existing_id="refined-poi-late",
            zone_born_at=1500,
            origin_bos_id="bos-A",
            expected_origin_conf_id="conf-A",
            expected_origin_conf_known_at=1700,
        )
        inventory.set_reaction_required_at(state.selected_poi_id, known_at=1_900)
        with self.assertRaisesRegex(V41Wait, "WAIT_POI_ELIGIBILITY_LOWER_BOUND"):
            inventory.latch_m15(
                state.selected_poi_id,
                cutoff=1_800,
                origin_conf_id="conf-A",
                origin_conf_known_at=1_700,
                family_prerequisites_complete=True,
                m4_gate_admissible=True,
                completed_context_admissible=True,
            )

    def test_preproposal_origin_latch_cannot_be_rebased_by_later_conf(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="STB",
            formation_id="stb-formation",
            source_parent_id="stb-parent",
            native_tf=60,
            formation_known_at=1_000,
            reaction_required_at=1_000,
            body_low=Decimal(99),
            body_high=Decimal(101),
        )
        latched = inventory.latch_m15(
            state.selected_poi_id,
            cutoff=1_500,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_450,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        again = inventory.latch_m15(
            state.selected_poi_id,
            cutoff=1_800,
            origin_conf_id="conf-B",
            origin_conf_known_at=1_750,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        self.assertEqual(latched.origin_conf_id, "conf-A")
        self.assertEqual(again.origin_conf_id, "conf-A")
        emitted = inventory.emit_h1_proposal(
            state.selected_poi_id,
            emission_decision_at=2_000,
            proposal_selected_conf_id="conf-B",
        )
        self.assertEqual(emitted.origin_conf_id, "conf-A")
        self.assertEqual(emitted.proposal_selected_conf_id, "conf-B")

    def test_native_bar_open_before_eligibility_is_wholly_ineligible(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="BREAKER",
            formation_id="breaker-formation",
            source_parent_id="parent-ob",
            native_tf=240,
            formation_known_at=1_000,
            reaction_required_at=1_000,
            breaker_formation_known_at=1_000,
            direction="SHORT",
        )
        inventory.latch_m15(
            state.selected_poi_id,
            cutoff=2_000,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_950,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        unchanged = inventory.observe_native_bar(
            state.selected_poi_id,
            native_bar_open=1_000,
            native_bar_close=15400,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        self.assertIsNone(unchanged.consumed_at)

    def test_equal_cutoff_consumption_rejects_emission(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="OB",
            formation_id="ob-formation",
            source_parent_id="ob-parent",
            native_tf=15,
            formation_known_at=1_000,
            reaction_required_at=1_200,
            existing_id="refined-poi",
            zone_born_at=1000,
            origin_bos_id="bos-A",
            expected_origin_conf_id="conf-A",
            expected_origin_conf_known_at=1450,
        )
        inventory.latch_m15(
            state.selected_poi_id,
            cutoff=1_500,
            origin_conf_id="conf-A",
            origin_conf_known_at=1_450,
            family_prerequisites_complete=True,
            m4_gate_admissible=True,
            completed_context_admissible=True,
        )
        inventory.observe_native_bar(
            state.selected_poi_id,
            native_bar_open=1_500,
            native_bar_close=2400,
            intersects=True,
            native_context_admissible_at_open=True,
        )
        with self.assertRaisesRegex(V41Reject, "REJECT_SELECTED_POI_PRECONSUMED"):
            inventory.emit_h1_proposal(
                state.selected_poi_id,
                emission_decision_at=2_400,
                proposal_selected_conf_id="conf-A",
            )

    def test_waiting_context_does_not_create_false_eligibility(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="SFP",
            formation_id="sfp-formation",
            source_parent_id="sfp-parent",
            native_tf=15,
            formation_known_at=1_000,
            reaction_required_at=1_200,
            existing_id="sfp-refined-poi",
            zone_born_at=1000,
            origin_bos_id="bos-A",
            expected_origin_conf_id="conf-A",
            expected_origin_conf_known_at=1450,
        )
        with self.assertRaisesRegex(V41Wait, "WAIT_CONTEXT_FOR_POI_ELIGIBILITY"):
            inventory.latch_m15(
                state.selected_poi_id,
                cutoff=1_500,
                origin_conf_id="conf-A",
                origin_conf_known_at=1_450,
                family_prerequisites_complete=True,
                m4_gate_admissible=True,
                completed_context_admissible=False,
            )
        snapshot = inventory.snapshot()
        self.assertIsNone(snapshot["states"][state.selected_poi_id]["eligibility_at"])
        self.assertFalse(snapshot["financial_metrics_generated"])
        self.assertEqual(snapshot["historical_position_evaluations"], 0)
        self.assertFalse(snapshot["trade_entry_allowed"])

    def test_deadline_blocks_late_eligibility_and_emission(self):
        inventory = SelectedPoiInventory()
        state = inventory.register(
            family="STB",
            formation_id="stb-deadline",
            source_parent_id="stb-parent",
            native_tf=60,
            formation_known_at=1_000,
            reaction_required_at=1_000,
            body_low=Decimal(99),
            body_high=Decimal(101),
        )
        with self.assertRaisesRegex(V41Reject, "EXPIRED_PENDING"):
            inventory.latch_m15(
                state.selected_poi_id,
                cutoff=1_000 + 57_600,
                origin_conf_id="conf-A",
                origin_conf_known_at=1_500,
                family_prerequisites_complete=True,
                m4_gate_admissible=True,
                completed_context_admissible=True,
            )


if __name__ == "__main__":
    unittest.main()
