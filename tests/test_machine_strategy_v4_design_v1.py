"""Synthetic design reference checks, not a strategy implementation or backtest."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_design_v1"
spec = importlib.util.spec_from_file_location(
    "design_verifier", ROOT / "scripts/verify_machine_strategy_v4_design_v1.py"
)
assert spec and spec.loader
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
D = Decimal


def read(name):
    return json.loads((DEST / name).read_text())


def prices(raw, anchor, fta, tick, direction):
    """Exact toy lattice oracle used only with synthetic prices."""
    floor = lambda p: (p / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
    ceil = lambda p: (p / tick).to_integral_value(rounding=ROUND_CEILING) * tick
    if direction == "LONG":
        return floor(raw), ceil(anchor) - tick, ceil(fta) - tick
    return ceil(raw), floor(anchor) + tick, floor(fta) + tick


def approach(direction, reaction, cutoff, events, *, invalid_at=None, gap=False):
    """Known-at fixture interpreter; no discovery or historical data access."""
    if gap:
        return "WAIT_REQUIRED_CAUSAL_EVIDENCE"
    if invalid_at is not None and invalid_at <= cutoff:
        return "APPROACH_INVALID"
    seen = [e for e in events if reaction < e[0] <= cutoff]
    confirms = [e for e in seen if e[1] == "CONF" and e[2] == direction]
    if not confirms:
        return "WAIT_REFINEMENT_BOS_CONF"
    selected = max(confirms, key=lambda e: (e[0], e[3]))
    opposing = [e for e in seen if e[2] != direction]
    if any(e[0] == selected[0] for e in opposing):
        return "WAIT_DUAL_OPPOSING_EVENT"
    if any(e[0] > selected[0] for e in opposing):
        return "WAIT_RECONFIRMATION"
    return "APPROACH_CORRECTIVE" if opposing else "APPROACH_CLEAN"


def completed_target(mark, raw, target, direction):
    return mark >= min(raw, target) if direction == "LONG" else mark <= max(raw, target)


def alive_at_open(formation, opening, emission, retirement_known_at=None):
    return emission <= opening < formation + 57600 and (
        retirement_known_at is None or retirement_known_at > opening
    )


def contact_trace(*, contact_known_at, start, end, fill=True, already_filled=False):
    """Synthetic pending ownership ordering; no cash ledger or historical runner."""
    if already_filled:
        return "EXPOSURE_KEEPS_INHERITED_EXITS"
    if contact_known_at is not None and contact_known_at <= start:
        return "RETIRED_BEFORE_OPEN"
    if fill:
        return "FILLED_CURRENT_BAR"
    return "RETIRE_AFTER_EXECUTION" if contact_known_at == end else "PENDING"


class V4DesignTests(unittest.TestCase):
    def test_complete_contract_schema_and_pins(self):
        self.assertEqual(verifier.check_design()["new_trade_evaluations"], 0)

    def test_tampered_or_missing_pin_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "input.json"
            p.write_text("original")
            pins = {"input.json": verifier.digest(p)}
            verifier.verify_pins(pins, root)
            p.write_text("mutated")
            with self.assertRaises(ValueError):
                verifier.verify_pins(pins, root)
            p.unlink()
            with self.assertRaises(ValueError):
                verifier.verify_pins(pins, root)

    def test_unsafe_and_empty_pin_maps_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                verifier.verify_pins({}, Path(tmp))
            with self.assertRaises(ValueError):
                verifier.verify_pins({"../outside": "0" * 64}, Path(tmp))

    def test_external_manifest_digest_rejects_unfrozen_or_mismatched(self):
        # No fixture can cause this test to freeze the real design.
        with tempfile.TemporaryDirectory() as tmp:
            original = verifier.DEST
            verifier.DEST = Path(tmp)
            try:
                (Path(tmp) / "DESIGN_FREEZE_MANIFEST.json").write_text("{}")
                with self.assertRaises(ValueError):
                    verifier.resume("0" * 64)
            finally:
                verifier.DEST = original

    def test_all_five_native_families_have_distinct_anchors(self):
        families = read("ENTRY_EXIT_CONTRACT.json")["families"]
        self.assertEqual(set(families), {"SFP", "OB", "BREAKER", "STB", "RANGE"})
        for f in families.values():
            self.assertEqual(f["formation_tf_minutes"], [60, 240])
            self.assertFalse(f["anchor_equality_breaks"])
            self.assertEqual(
                f["structural_break_comparison"],
                {
                    "LONG": "close < structural_anchor",
                    "SHORT": "close > structural_anchor",
                },
            )
        self.assertIn("unbuffered", families["SFP"]["structural_anchor"])
        self.assertIn("ATR14", families["SFP"]["protective_boundary"])
        self.assertIn("source native range", families["RANGE"]["additional_retirement"])

    def test_clean_and_corrective_are_mirrored(self):
        for direction, opposite in [("LONG", "SHORT"), ("SHORT", "LONG")]:
            clean = [(20, "CONF", direction, "a")]
            corrective = [(15, "BOS", opposite, "b"), *clean]
            self.assertEqual(approach(direction, 10, 30, clean), "APPROACH_CLEAN")
            self.assertEqual(
                approach(direction, 10, 30, corrective), "APPROACH_CORRECTIVE"
            )

    def test_later_opposite_requires_fresh_confirmation(self):
        for direction, opposite in [("LONG", "SHORT"), ("SHORT", "LONG")]:
            events = [(20, "CONF", direction, "a"), (25, "BOS", opposite, "b")]
            self.assertEqual(approach(direction, 10, 30, events), "WAIT_RECONFIRMATION")
            events.append((28, "CONF", direction, "c"))
            self.assertEqual(approach(direction, 10, 30, events), "APPROACH_CORRECTIVE")

    def test_dual_event_cannot_be_selected_by_id(self):
        for direction, opposite in [("LONG", "SHORT"), ("SHORT", "LONG")]:
            events = [(20, "CONF", direction, "z"), (20, "CONF", opposite, "a")]
            self.assertEqual(
                approach(direction, 10, 30, events), "WAIT_DUAL_OPPOSING_EVENT"
            )

    def test_missing_confirmation_and_gap_wait_not_terminal_reject(self):
        self.assertEqual(approach("LONG", 10, 30, []), "WAIT_REFINEMENT_BOS_CONF")
        self.assertEqual(
            approach("LONG", 10, 30, [], gap=True), "WAIT_REQUIRED_CAUSAL_EVIDENCE"
        )

    def test_positive_structural_invalidation_is_permanent(self):
        events = [(28, "CONF", "LONG", "a")]
        self.assertEqual(
            approach("LONG", 10, 30, events, invalid_at=25), "APPROACH_INVALID"
        )
        self.assertEqual(
            approach("LONG", 10, 30, events, invalid_at=31), "APPROACH_CLEAN"
        )

    def test_future_mutation_does_not_change_approach_prefix(self):
        before = [(20, "CONF", "LONG", "a"), (10, "BOS", "SHORT", "reaction_boundary")]
        future = [(31, "CONF", "SHORT", "x"), (40, "BOS", "SHORT", "y")]
        self.assertEqual(
            approach("LONG", 10, 30, before), approach("LONG", 10, 30, before + future)
        )

    def test_all_family_zone_types_and_tick_envelopes(self):
        for family, record in read("ENTRY_EXIT_CONTRACT.json")["families"].items():
            self.assertIn("entry_zone", record, family)
            for tick in [D("0.01"), D("0.05"), D("0.20")]:
                for direction in ["LONG", "SHORT"]:
                    low, high = D("100.013"), D("100.077")
                    if family == "RANGE":
                        low = high = D("100.013")
                    raw = (
                        (low + high) / 2
                        if family == "STB"
                        else high
                        if direction == "LONG"
                        else low
                    )
                    entry, _, _ = prices(raw, D("95"), D("105"), tick, direction)
                    self.assertTrue(low - tick <= entry <= high + tick)

    def test_strict_outward_stop_and_inward_target_at_grid_equality(self):
        self.assertEqual(
            prices(D("100"), D("99"), D("102"), D("0.1"), "LONG"),
            (D("100"), D("98.9"), D("101.9")),
        )
        self.assertEqual(
            prices(D("100"), D("101"), D("98"), D("0.1"), "SHORT"),
            (D("100"), D("101.1"), D("98.1")),
        )

    def test_no_source_envelope_or_historical_epoch_promotion(self):
        registry = read("RULE_REGISTRY.json")["rules"]
        zone = next(r for r in registry if r["rule_id"] == "M4_EXECUTABLE_ZONE")
        self.assertEqual(zone["classification"], "TECHNICAL_NORMALIZATION")
        self.assertFalse(zone["source_selector_equivalence"])
        self.assertIn(
            "without raw structural POI contact",
            read("EXECUTION_CONTRACT.json")["POI_ownership"]["outside_POI_contact"],
        )

    def test_nearest_fta_between_raw_and_rounded_entry_cannot_be_skipped(self):
        for direction, raw, reference, targets, expected in [
            ("LONG", D("100.05"), D("100.0"), [D("100.03"), D("102")], D("100.03")),
            ("SHORT", D("100.05"), D("100.1"), [D("100.07"), D("98")], D("100.07")),
        ]:
            sign = 1 if direction == "LONG" else -1
            nearest = min(
                (sign * (t - reference), str(t), t)
                for t in targets
                if sign * (t - reference) > 0
            )[2]
            self.assertEqual(nearest, expected)
            self.assertLess(sign * (expected - raw), 0)
        self.assertIn(
            "reference-grid rounded",
            read("ENTRY_EXIT_CONTRACT.json")["FTA"]["selector"],
        )

    def test_inward_target_completion_before_reservation_mirrors(self):
        self.assertTrue(completed_target(D("100.02"), D("100.05"), D("100"), "LONG"))
        self.assertTrue(completed_target(D("99.98"), D("99.95"), D("100"), "SHORT"))
        self.assertFalse(completed_target(D("99.99"), D("100.05"), D("100"), "LONG"))
        self.assertFalse(completed_target(D("100.01"), D("99.95"), D("100"), "SHORT"))
        self.assertIn(
            "before reservation",
            read("ENTRY_EXIT_CONTRACT.json")["FTA"]["pre_emission_executable_check"],
        )

    def test_target_equality_is_completed(self):
        for direction in ["LONG", "SHORT"]:
            self.assertTrue(completed_target(D("100"), D("100"), D("100"), direction))

    def test_parent_deadline_anchored_not_reset_by_emission(self):
        self.assertTrue(alive_at_open(0, 56700, 3600))
        self.assertFalse(alive_at_open(0, 57600, 3600))
        self.assertFalse(alive_at_open(0, 57600, 57600))
        self.assertFalse(alive_at_open(0, 60000, 54000))

    def test_close_observation_cannot_pre_cancel_its_own_bar(self):
        self.assertEqual(
            contact_trace(contact_known_at=900, start=0, end=900), "FILLED_CURRENT_BAR"
        )
        self.assertEqual(
            contact_trace(contact_known_at=900, start=0, end=900, fill=False),
            "RETIRE_AFTER_EXECUTION",
        )
        self.assertEqual(
            contact_trace(contact_known_at=0, start=0, end=900), "RETIRED_BEFORE_OPEN"
        )

    def test_filled_positions_do_not_gain_new_context_exit(self):
        self.assertEqual(
            contact_trace(contact_known_at=0, start=0, end=900, already_filled=True),
            "EXPOSURE_KEEPS_INHERITED_EXITS",
        )
        self.assertFalse(
            read("ENTRY_EXIT_CONTRACT.json")["exits"][
                "filled_context_or_POI_change_is_exit"
            ]
        )

    def test_outside_structural_POI_contact_can_fill_only_explicit_model(self):
        # LONG E=100 below structural low=100.05, OPEN=99.99 still above S=99.
        entry, stop, _ = prices(D("100.05"), D("99.05"), D("103"), D("0.1"), "LONG")
        self.assertTrue(stop < D("99.99") <= entry < D("100.05"))
        self.assertEqual(
            contact_trace(contact_known_at=None, start=0, end=900), "FILLED_CURRENT_BAR"
        )

    def test_doubled_cost_payoff_equality_and_mirror_threshold(self):
        with localcontext() as ctx:
            ctx.prec = 50
            for direction, stop in [("LONG", D("99")), ("SHORT", D("101"))]:
                sign, entry, c = (
                    (D(1) if direction == "LONG" else D(-1)),
                    D("100"),
                    D("0.0008"),
                )
                # Scale to produce an exactly finite equality fixture, no epsilon.
                scale = abs(sign - 2 * c)
                entry, stop = entry * scale, stop * scale
                k = sign * (entry - stop) + c * (entry + stop)
                target = (k + (sign + 2 * c) * entry) / (sign - 2 * c)
                numerator = sign * (target - entry) - 2 * c * (entry + target)
                self.assertEqual(numerator, k)
                for delta in [D("-0.01"), D(0), D("0.01")]:
                    altered = target + sign * delta
                    passes = sign * (altered - entry) - 2 * c * (entry + altered) >= k
                    self.assertEqual(passes, delta >= 0)
        self.assertIn(
            "equality passing", read("EXECUTION_CONTRACT.json")["payoff"]["admit"]
        )

    def test_quantity_cancels_planned_parity_but_not_fixed_U_reporting(self):
        entry, stop, target = D("100"), D("99"), D("102")
        k = entry - stop + D("0.0008") * (entry + stop)
        n = target - entry - D("0.0016") * (entry + target)
        for q in [D(1), D("0.7"), D("0.98")]:
            self.assertEqual((q * n) / (q * k), n / k)
            self.assertEqual(q * n / k, q * (n / k))
        self.assertIn(
            "no multiplication by Q_s",
            read("EXECUTION_CONTRACT.json")["payoff"]["qualification_U"],
        )

    def test_full_roundtrip_cost_and_edge_ratio_not_fixed_percentage_TP(self):
        entry, target = D("100"), D("102")
        fee = D("0.0006") * (entry + target)
        slip = D("0.0002") * (entry + target)
        self.assertEqual(fee + slip, D("0.0008") * (entry + target))
        self.assertGreater((target - entry) / (fee + slip), 1)
        exits = read("ENTRY_EXIT_CONTRACT.json")["exits"]
        self.assertFalse(exits["partial_TP_ladder"])
        self.assertFalse(exits["breakeven"])
        self.assertTrue(exits["original_canonical_TP_40_30_30_SL_cost_BE_untouched"])

    def test_all_scenarios_and_unchanged_qualification(self):
        parent = json.loads(
            (
                ROOT
                / "docs/machine_strategy_v3_okx_compatibility_v1/QUANTIZATION_STRESS_POLICY.json"
            ).read_text()
        )
        self.assertEqual(
            read("EXECUTION_CONTRACT.json")["compatibility"]["all_scenarios"],
            parent["scenario_generation"]["scenario_ids_in_order"],
        )
        self.assertEqual(
            read("V4_PREREGISTRATION.json")["qualification"], verifier.QUALIFICATION
        )

    def test_telemetry_has_no_decision_input_allowlist_or_outcome_readback(self):
        telemetry = read("TELEMETRY_SCHEMA.json")
        self.assertNotIn("decision_input_allowlist", telemetry)
        self.assertEqual(
            len(telemetry["telemetry_emission_field_allowlist"]),
            len(set(telemetry["telemetry_emission_field_allowlist"])),
        )
        self.assertTrue(telemetry["observer_only"])
        self.assertTrue(
            telemetry["causality"]["telemetry_readback_into_strategy_forbidden"]
        )
        forbidden = {
            "WIN",
            "LOSS",
            "net_PnL",
            "future_funding",
            "MFE",
            "MAE",
            "holding_time",
        }
        self.assertFalse(
            forbidden & set(telemetry["telemetry_emission_field_allowlist"])
        )
        mutated = copy.deepcopy(telemetry)
        mutated["future_outcome"] = "loss"
        self.assertEqual(
            mutated["telemetry_emission_field_allowlist"],
            telemetry["telemetry_emission_field_allowlist"],
        )
        self.assertIn(
            "Excluded from Anti-Scalp rejected",
            telemetry["anti_scalp_reason_mapping"]["NO_HTF_CONTEXT"],
        )

    def test_preserved_source_ambiguities_and_no_source_promotion(self):
        inherited = read("INHERITED_INPUTS_AND_SOURCE_CITATIONS.json")
        self.assertFalse(inherited["source_validated"])
        self.assertGreaterEqual(len(inherited["retained_material_source_variants"]), 6)
        self.assertFalse(
            read("SOURCE_CONFLICT_REGISTRY.json")["source_conflicts_resolved_by_PnL"]
        )
        for r in read("RULE_REGISTRY.json")["rules"]:
            self.assertFalse(r["historical_PnL_selection"])
            self.assertNotEqual(r["classification"], "SOURCE_RULE")

    def test_funding_interval_witness_semantics_are_inherited_and_pinned(self):
        treatment = read("ENTRY_EXIT_CONTRACT.json")["exits"]["funding"]
        self.assertIn("coherent fill/exit interval witnesses", treatment)
        self.assertIn("-1/+1", treatment)
        self.assertIn("settlement-close proxy", treatment)
        self.assertNotIn("start <settlement<=exit", treatment)
        pins = read("INHERITED_INPUTS_AND_SOURCE_CITATIONS.json")[
            "inherited_input_sha256"
        ]
        for name in [
            "scripts/okx_v3_compatibility_runner_v1.py",
            "docs/machine_strategy_v3_okx_compatibility_v1/COST_FUNDING_BINDING.json",
            "docs/machine_strategy_v3_okx_compatibility_v1/CAUSALITY_REPORT.md",
        ]:
            self.assertEqual(verifier.digest(ROOT / name), pins[name])


if __name__ == "__main__":
    unittest.main()
