"""Registered synthetic design witnesses; no historical bars or financial cases."""

import ast
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from dataclasses import replace
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/machine_strategy_v4_1_design_reference.py"
spec = importlib.util.spec_from_file_location("v41_reference", SOURCE)
ref = importlib.util.module_from_spec(spec)
import sys

sys.modules[spec.name] = ref
spec.loader.exec_module(ref)
D = Decimal
DEST = ROOT / "docs/machine_strategy_v4_1_design_v1"


def poi(family="STB", direction="LONG", tf=None, **updates):
    values = {
        "family": family,
        "direction": direction,
        "native_tf": tf or (15 if family in ("SFP", "OB") else 60),
        "formation_id": "formation",
        "parent_id": "parent",
        "formation_at": 0,
        "reaction_at": 0,
        "conf_at": 0,
        "born_at": 0,
        "conf_id": "own-conf",
        "low": D("99"),
        "high": D("101"),
    }
    if family == "RANGE":
        values["low"] = values["high"] = D("100")
    values.update(updates)
    return ref.POI(**values)


def context(at=0, ok=True):
    return {"kind": "CONTEXT", "at": at, "admissible": ok}


def emit(at):
    return {"kind": "EMIT", "at": at}


def execution(start, fill=True):
    return {
        "kind": "EXECUTION",
        "at": start + 900,
        "start": start,
        "modeled_fill": fill,
    }


def contact(p, start, low="99", high="101", native=True, known=None):
    return {
        "kind": "CONTACT",
        "at": start + p.native_tf * 60,
        "start": start,
        "low": low,
        "high": high,
        "native_context_at_open": native,
        "native_context_known_at": start if known is None else known,
    }


def reflected(event):
    e = dict(event)
    if e["kind"] == "CONTACT":
        e["low"], e["high"] = (
            ref.canonical(200 - D(e["high"])),
            ref.canonical(200 - D(e["low"])),
        )
    return e


class DesignWitnesses(unittest.TestCase):
    def all_pairs(self):
        for family in ref.FAMILIES:
            for direction in ref.DIRECTIONS:
                yield poi(family, direction)

    def test_SFP_PREEMISSION_CONTACT(self):
        for direction in ref.DIRECTIONS:
            p = poi("SFP", direction)
            result = ref.replay(p, [context(), contact(p, 0), emit(3600)], 3600)
            self.assertEqual(result["trace"][-1][2], "REJECT_SELECTED_POI_PRECONSUMED")

    def test_OB_PARENT_VS_REFINED(self):
        for direction in ref.DIRECTIONS:
            p = poi("OB", direction)
            parent = contact(p, 0, low="97", high="98")
            events = [context(), parent, emit(1800)]
            self.assertEqual(ref.replay(p, events, 1800)["status"], "PENDING")
            self.assertEqual(
                ref.replay(p, events + [contact(p, 1800)], 2700)["status"],
                "RETIRED_CONTACT",
            )

    def test_STB_BODY_VS_PARENT(self):
        for direction in ref.DIRECTIONS:
            p = poi("STB", direction)
            e = contact(p, 0, low="97", high="98")
            if direction == "SHORT":
                e = reflected(e)
            result = ref.replay(p, [context(), e, emit(3600)], 3600)
            self.assertIsNone(result["consumed_at"])
            self.assertEqual(result["status"], "PENDING")
            result = ref.replay(p, [context(), e, emit(3600), contact(p, 3600)], 7200)
            self.assertEqual(result["status"], "RETIRED_CONTACT")
            self.assertNotEqual(p.selected_id, p.parent_id)

    def test_BREAKER_PRECREATION_CONTACT(self):
        for direction in ref.DIRECTIONS:
            p = poi(
                "BREAKER",
                direction,
                formation_at=3600,
                reaction_at=3600,
                conf_at=4500,
                born_at=3600,
            )
            events = [context(), contact(p, 0), emit(7200)]
            result = ref.replay(p, events, 7200)
            self.assertEqual(result["status"], "PENDING")
            self.assertIsNone(result["consumed_at"])
            result = ref.replay(p, events + [contact(p, 7200)], 10800)
            self.assertEqual(result["status"], "RETIRED_CONTACT")

    def test_RANGE_REQUIRED_REACTION_EXEMPT(self):
        for direction in ref.DIRECTIONS:
            p = poi("RANGE", direction, reaction_at=3600, conf_at=4500)
            events = [context(), contact(p, 0), emit(7200)]
            self.assertEqual(ref.replay(p, events, 7200)["status"], "PENDING")
            self.assertEqual(
                ref.replay(p, events + [contact(p, 7200)], 10800)["status"],
                "RETIRED_CONTACT",
            )

    def test_ACTIVE_ORDER_SAME_BAR_FILL(self):
        for p in self.all_pairs():
            with self.subTest(family=p.family, direction=p.direction):
                events = [context(), emit(0), execution(0), contact(p, 0)]
                self.assertEqual(
                    ref.replay(p, events, p.native_tf * 60)["status"], "FILLED_WITNESS"
                )

    def test_PENDING_CONTACT_NO_FILL(self):
        for p in self.all_pairs():
            events = [context(), emit(0), execution(0, False), contact(p, 0)]
            self.assertEqual(
                ref.replay(p, events, p.native_tf * 60)["status"], "RETIRED_CONTACT"
            )

    def test_CONTEXT_LATE_ENABLE(self):
        for p in self.all_pairs():
            n = p.native_tf * 60
            events = [context(0, False), contact(p, 0), context(n, True), emit(n)]
            result = ref.replay(p, events, n)
            self.assertEqual(result["eligibility_at"], n)
            self.assertIsNone(result["consumed_at"])
            self.assertEqual(result["status"], "PENDING")
            self.assertEqual(
                ref.replay(p, events + [contact(p, n)], 2 * n)["status"],
                "RETIRED_CONTACT",
            )

    def test_DEADLINE_BOUNDARY(self):
        for p in self.all_pairs():
            for cutoff in (57600, 58500):
                self.assertEqual(
                    ref.replay(p, [context(), emit(cutoff)], cutoff)["trace"][-1][2],
                    "EXPIRED_PENDING",
                )
            events = [context(), emit(56700), execution(57600)]
            self.assertEqual(ref.replay(p, events, 58500)["status"], "EXPIRED_PENDING")
            self.assertEqual(
                ref.replay(p, [context(), emit(56700), execution(56700)], 57600)[
                    "status"
                ],
                "FILLED_WITNESS",
            )

    def test_H4_MIDBAR_EMISSION_FILL(self):
        for family in ("STB", "BREAKER", "RANGE"):
            for direction in ref.DIRECTIONS:
                p = poi(
                    family,
                    direction,
                    tf=240,
                    formation_at=28800,
                    reaction_at=28800,
                    conf_at=28800,
                    born_at=28800,
                )
                events = [
                    context(28800),
                    emit(32400),
                    execution(33300),
                    {"kind": "EXPOSURE_ENDED", "at": 36000},
                    emit(36000),
                    contact(p, 28800),
                ]
                result = ref.replay(p, events, 43200)
                self.assertEqual(result["filled_at"], 33300)
                self.assertEqual(result["status"], "FILLED_WITNESS")
                self.assertEqual(result["consumed_at"], 43200)
                self.assertIn(
                    (36000, "EMIT", "REJECT_ALREADY_RESERVED"), result["trace"]
                )
                # Hand exposure marker carries no exit price, cash or financial outcome.
                self.assertEqual(result["reserved_at"], 32400)
                self.assertFalse(result["exposure_active"])

    def test_CONTACT_EQUALS_EMISSION(self):
        for p in self.all_pairs():
            events = [context(), emit(p.native_tf * 60), contact(p, 0)]
            result = ref.replay(p, events, p.native_tf * 60)
            self.assertEqual(result["trace"][-1][2], "REJECT_SELECTED_POI_PRECONSUMED")
            self.assertIsNone(result["reserved_at"])

    def test_NATIVE_CONTEXT_OPEN_PROOF(self):
        for p in self.all_pairs():
            result = ref.replay(
                p,
                [context(), contact(p, 0, native=False), emit(p.native_tf * 60)],
                p.native_tf * 60,
            )
            self.assertEqual(result["status"], "PENDING")
            with self.assertRaisesRegex(ValueError, "FUTURE_NATIVE_CONTEXT_PROOF"):
                ref.replay(p, [context(), contact(p, 0, known=900)], p.native_tf * 60)

    def test_OWNERSHIP_MONOTONIC(self):
        for p in self.all_pairs():
            n = p.native_tf * 60
            events = [
                context(),
                contact(p, 0),
                context(n, False),
                context(n + 900),
                emit(n + 900),
            ]
            result = ref.replay(p, events, n + 900)
            self.assertEqual(result["eligibility_at"], 0)
            self.assertEqual(result["consumed_at"], n)
            self.assertEqual(result["trace"][-1][2], "REJECT_SELECTED_POI_PRECONSUMED")
            events = [
                context(),
                emit(0),
                context(900, False),
                context(1800),
                emit(1800),
            ]
            result = ref.replay(p, events, 1800)
            self.assertEqual(result["status"], "RETIRED_CONTEXT")
            self.assertEqual(result["trace"][-1][2], "REJECT_ALREADY_RESERVED")

    def test_PREPROPOSAL_CONF_AB_LATCH(self):
        for family in ("STB", "BREAKER", "RANGE"):
            for direction in ref.DIRECTIONS:
                p = poi(
                    family,
                    direction,
                    formation_at=28800,
                    reaction_at=28800,
                    conf_at=32400,
                    born_at=28800,
                    conf_id="A",
                )
                events = [
                    context(28800),
                    contact(p, 32400),
                    {"kind": "PROPOSAL_CONF", "at": 39600, "id": "B"},
                    emit(43200),
                ]
                result = ref.replay(p, events, 43200)
                self.assertEqual(result["eligibility_at"], 32400)
                self.assertEqual(result["origin_conf_id"], "A")
                self.assertEqual(result["proposal_selected_conf_id"], "B")
                self.assertEqual(result["consumed_at"], 36000)
                self.assertEqual(
                    result["trace"][-1][2], "REJECT_SELECTED_POI_PRECONSUMED"
                )

    def test_MIDBAR_ELIGIBILITY_NO_BACKDATE(self):
        for family in ("STB", "BREAKER", "RANGE"):
            for direction in ref.DIRECTIONS:
                p = poi(family, direction, tf=240, conf_at=900)
                events = [context(), contact(p, 0), emit(14400)]
                result = ref.replay(p, events, 14400)
                self.assertEqual(result["eligibility_at"], 900)
                self.assertIsNone(result["consumed_at"])
                self.assertEqual(result["status"], "PENDING")
                result = ref.replay(p, events + [contact(p, 14400)], 28800)
                self.assertEqual(result["status"], "RETIRED_CONTACT")
                prefix = ref.replay(p, events, 0)
                self.assertIsNone(prefix["origin_conf_id"])
                self.assertIsNone(prefix["eligibility_at"])

    def test_DECIMAL_ONE_THIRD(self):
        text = ref.design_third()
        number = ref.ledger_boundary(text)
        self.assertEqual(ref.canonical(number), text)
        with localcontext() as ctx:
            ctx.prec = 80
            ctx.rounding = ROUND_HALF_EVEN
            self.assertNotEqual(number, D(1) / D(3))

    def test_DECIMAL_PAYOFF_EQUALITY(self):
        for direction in ref.DIRECTIONS:
            unit, planned = ref.planned_equal(direction)
            self.assertEqual(unit, planned)
            self.assertEqual(ref.ledger_boundary(unit), ref.ledger_boundary(planned))

    def test_LOT_FLOOR_PRECISION_BOUNDARY(self):
        base = D("1." + "0" * 50 + "1")
        lot = D(1)
        text = ref.design_quantity(base, lot)
        self.assertEqual(text, "1")
        self.assertEqual(ref.ledger_boundary(text), D(1))
        with localcontext() as ctx:
            ctx.prec = 80
            ctx.rounding = ROUND_HALF_EVEN
            self.assertEqual(
                (D(1) / base).to_integral_value(rounding=ROUND_FLOOR), D(0)
            )

    def test_prefix_future_mutation_and_deterministic_replay(self):
        for p in self.all_pairs():
            n = p.native_tf * 60
            events = [
                context(),
                emit(0),
                execution(0, False),
                contact(p, 0),
                context(2 * n, False),
            ]
            mutated = copy.deepcopy(events)
            for e in mutated:
                if e["at"] > 900:
                    if e["kind"] == "CONTACT":
                        e["low"], e["high"] = "500", "501"
                    elif e["kind"] == "CONTEXT":
                        e["admissible"] = True
            expected = ref.replay(p, [e for e in events if e["at"] <= 900], 900)
            self.assertEqual(ref.replay(p, events, 900), expected)
            self.assertEqual(ref.replay(p, mutated, 900), expected)
            self.assertEqual(
                ref.replay(p, list(reversed(events)), 2 * n),
                ref.replay(p, events, 2 * n),
            )

    def test_canonical_identity_and_input_guard(self):
        p = poi()
        self.assertEqual(
            p.selected_id, replace(p, low=D("99.000"), high=D("101.00")).selected_id
        )
        self.assertNotEqual(p.selected_id, replace(p, formation_id="other").selected_id)
        self.assertEqual(ref.canonical(D("-0")), "0")
        self.assertEqual(ref.canonical(D("1E-7")), "0.0000001")
        for value in (0.1, D("NaN"), D("Infinity")):
            with self.assertRaises(ValueError):
                ref.canonical(value)
        for value in ("1E-7", "1.00", "-0"):
            with self.assertRaises(ValueError):
                ref.ledger_boundary(value)
        with self.assertRaises(ValueError):
            poi(formation_at=True)

    def test_reference_imports_are_only_stdlib(self):
        allowed = {"__future__", "hashlib", "json", "dataclasses", "decimal"}
        tree = ast.parse(SOURCE.read_text())
        imported = {
            n.module.split(".")[0]
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
        } | {
            a.name.split(".")[0]
            for n in ast.walk(tree)
            if isinstance(n, ast.Import)
            for a in n.names
        }
        self.assertLessEqual(imported, allowed)
        self.assertNotIn("evaluate_historical_catalog", SOURCE.read_text())

    def test_frozen_pin_tamper_and_unsafe_path_rejected(self):
        vspec = importlib.util.spec_from_file_location(
            "v41_verify", ROOT / "scripts/verify_machine_strategy_v4_1_design_v1.py"
        )
        verifier = importlib.util.module_from_spec(vspec)
        vspec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "input.json"
            file.write_text("{}")
            pin = {"input.json": hashlib.sha256(file.read_bytes()).hexdigest()}
            verifier.verify_pins(pin, root)
            file.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, "PIN_CHANGED"):
                verifier.verify_pins(pin, root)
            with self.assertRaisesRegex(ValueError, "UNSAFE_PIN_PATH"):
                verifier.verify_pins(
                    {str(file): hashlib.sha256(file.read_bytes()).hexdigest()}, root
                )

    def test_fake_design_manifest_cannot_escalate_authority(self):
        vspec = importlib.util.spec_from_file_location(
            "v41_verify", ROOT / "scripts/verify_machine_strategy_v4_1_design_v1.py"
        )
        verifier = importlib.util.module_from_spec(vspec)
        vspec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "manifest.json"
            file.write_text(
                json.dumps(
                    {
                        "decision": verifier.PASS,
                        "historical_financial_authorized": True,
                        "implementation_ready": False,
                        "complete_implementation_freeze": False,
                        "PAPER": False,
                        "LIVE": False,
                        "trade_entry_allowed": False,
                        "version": verifier.VERSION,
                    }
                )
            )
            with patch.object(verifier, "MANIFEST", file):
                with self.assertRaisesRegex(
                    ValueError, "EXTERNAL_MANIFEST_PIN_MISMATCH"
                ):
                    verifier.resume("0" * 64)
                with self.assertRaisesRegex(ValueError, "DESIGN_AUTHORITY_ESCALATION"):
                    verifier.resume(hashlib.sha256(file.read_bytes()).hexdigest())

    def test_all_registered_witnesses_have_executed_test_methods(self):
        registry = json.loads((DEST / "SYNTHETIC_WITNESS_REGISTRY.json").read_text())
        for w in registry["witnesses"]:
            self.assertTrue(hasattr(self, "test_" + w["id"]), w["id"])
        self.assertFalse(registry["financial_data_allowed"])


if __name__ == "__main__":
    unittest.main()
