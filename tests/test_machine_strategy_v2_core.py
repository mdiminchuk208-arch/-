"""Synthetic machine decisions: source boundary, causality and branch contracts."""

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from machine_strategy_v2_core import (
    BRANCHES,
    PARAMETERS,
    PRIORITY,
    Frame,
    build_cohort,
    epsilon,
    ident,
    liquidity_inventory,
    plan_case,
    serial,
)
from test_original_v1_1_evidence_adapter_v2 import bars

D = Decimal
VALUES = [
    (10, 11, 8, 10),
    (10, 12, 7, 10),
    (10, 11, 8, 10),
    (10, 14, 9, 13),
    (13, 15, 10, 14),
    (14, 14.5, 10, 13),
    (13, 14, 11, 13),
]


def fixture(branch="STB", direction="LONG"):
    c = {
        "id": "h1",
        "bos_id": "bos",
        "confirmation_id": "conf",
        "known_at": 100,
        "direction": direction,
        "protected_id": "low",
        "end_swing_id": "high",
        "protected_price": D(6),
        "low": D(6),
        "high": D(20),
        "EQ": D(13),
        "OTE": [D(9), D(10)],
    }
    z = {
        "id": "entry-poi",
        "direction": direction,
        "low": D(10),
        "high": D(11),
        "born_at": 110,
        "consumed_at": None,
        "contextual_at_birth": True,
        "origin_bos_id": "m-bos",
        "kind": "FVG",
    }
    pool = {
        "id": "pool",
        "known_at": 90,
        "payload": {
            "side": "HIGH" if direction == "LONG" else "LOW",
            "price": "18" if direction == "LONG" else "8",
            "swing_id": "unprotected",
        },
    }
    frames = {
        tf: SimpleNamespace(
            context=copy.deepcopy(c), pools={}, candidates_zones=lambda *a, **kw: []
        )
        for tf in (60, 240, 1440)
    }
    frames[60].pools = {"pool": pool}
    conf = {**c, "id": "m-conf", "bos_id": "m-bos", "known_at": 150}
    bos = {"id": "m-bos", "known_at": 130, "direction": direction}
    frames[15] = SimpleNamespace(
        confirmations=[conf],
        confirm_times=[150],
        bos=[bos],
        bos_times=[130],
        bos_by_id={"m-bos": bos},
        candidates_zones=lambda *a, **kw: [z],
    )
    pending = {
        "branch": branch,
        "direction": direction,
        "zone": z if branch not in ("SFP", "OB") else {**z, "low": D(9), "high": D(12)},
        "reaction_at": 120,
        "formation_at": 110,
        "formation_id": "formation",
        "setup_tf": 60,
        "formation_bar": bars([(10, 12, 9, 11)])[0],
        "extreme": D(9) if direction == "LONG" else D(12),
        "atr": D(1),
        "range": {"id": "range", "low": D(10), "high": D(16), "known_at": 100},
    }
    return pending, frames


class MachineCoreTests(unittest.TestCase):
    def test_strict_swing_right_close_and_prefix(self):
        full = Frame("BTCUSDT", 60, bars(VALUES))
        prefix = Frame("BTCUSDT", 60, bars(VALUES[:3]))
        full.advance(10799)
        self.assertIsNone(full.latest["LOW"])
        full.advance(10800)
        prefix.advance(10800)
        self.assertEqual(full.latest, prefix.latest)

    def test_context_conf_comes_after_BOS(self):
        f = Frame("BTCUSDT", 60, bars(VALUES))
        f.advance(21600)
        self.assertIsNotNone(f.context)
        self.assertLess(
            f.bos_by_id[f.context["bos_id"]]["known_at"], f.context["known_at"]
        )
        self.assertEqual(f.context["protected_price"], D(7))

    def test_future_mutation_cannot_change_context(self):
        a = Frame("BTCUSDT", 60, bars(VALUES))
        b = Frame("BTCUSDT", 60, bars(VALUES[:6] + [(100, 101, 90, 100)]))
        a.advance(21600)
        b.advance(21600)
        self.assertEqual(serial(a.context), serial(b.context))

    def test_backward_cutoff_rejected(self):
        f = Frame("BTCUSDT", 60, bars(VALUES))
        f.advance(21600)
        with self.assertRaises(ValueError):
            f.advance(18000)

    def test_equal_swings_not_selected(self):
        f = Frame("BTCUSDT", 60, bars([(10, 12, 8, 10)] * 5))
        f.advance(18000)
        self.assertIsNone(f.context)
        self.assertFalse(f.bos)

    def test_wick_is_not_BOS(self):
        f = Frame("BTCUSDT", 60, bars(VALUES[:3] + [(10, 20, 9, 11)]))
        f.advance(14400)
        self.assertFalse(f.bos)

    def test_context_invalidates_by_body_loss(self):
        f = Frame("BTCUSDT", 60, bars(VALUES[:6] + [(8, 9, 5, 6)]))
        f.advance(25200)
        self.assertIsNone(f.context)

    def test_all_five_branches_have_complete_positive_plan(self):
        for branch in BRANCHES:
            pending, frames = fixture(branch)
            case, reason = plan_case("BTCUSDT", pending, frames, 200, set())
            with self.subTest(branch=branch):
                self.assertEqual(reason, "ALLOWED_MACHINE_SETUP")
                self.assertIsNotNone(case)
                self.assertFalse(case["source_validated"])
                self.assertFalse(case["trade_entry_allowed"])
                self.assertTrue(case["fixed_stop"])
                self.assertFalse(case["BE_enabled"])

    def test_short_stop_and_target_geometry(self):
        pending, frames = fixture(direction="SHORT")
        case, _ = plan_case("BTCUSDT", pending, frames, 200, set())
        self.assertLess(D(case["theoretical_target"]), D(case["theoretical_entry"]))
        self.assertGreater(D(case["fixed_initial_stop"]), D(case["theoretical_entry"]))

    def test_no_context_is_named_observational_WAIT(self):
        pending, frames = fixture()
        frames[240].context = None
        self.assertEqual(
            plan_case("BTCUSDT", pending, frames, 200, set())[1],
            "WAIT_NO_CONFIRMED_CONTEXT",
        )

    def test_D1_disagreement_not_universal_alignment(self):
        pending, frames = fixture()
        frames[1440].context["direction"] = "SHORT"
        self.assertIsNotNone(plan_case("BTCUSDT", pending, frames, 200, set())[0])

    def test_H4_countertrend_requires_higher_POI(self):
        pending, frames = fixture()
        frames[240].context["direction"] = "SHORT"
        self.assertEqual(
            plan_case("BTCUSDT", pending, frames, 200, set())[1],
            "WAIT_COUNTERTREND_ORIGIN_POI",
        )

    def test_no_refinement_confirmation_no_entry(self):
        pending, frames = fixture()
        frames[15].confirmations = []
        self.assertEqual(
            plan_case("BTCUSDT", pending, frames, 200, set())[1],
            "WAIT_REFINEMENT_BOS_CONF",
        )

    def test_consumed_POI_rejected(self):
        pending, frames = fixture()
        pending["zone"]["consumed_at"] = 190
        self.assertEqual(
            plan_case("BTCUSDT", pending, frames, 200, set())[1],
            "REJECT_CONSUMED_OR_ALREADY_ORDERED_POI",
        )

    def test_duplicate_entry_POI_not_reordered(self):
        pending, frames = fixture()
        self.assertIsNone(plan_case("BTCUSDT", pending, frames, 200, {"entry-poi"})[0])

    def test_FTA_absence_WAIT(self):
        pending, frames = fixture()
        frames[60].pools = {}
        self.assertEqual(
            plan_case("BTCUSDT", pending, frames, 200, set())[1], "WAIT_NO_CAUSAL_FTA"
        )

    def test_future_FTA_rejected(self):
        pending, frames = fixture()
        frames[60].pools["pool"]["known_at"] = 201
        with self.assertRaises(ValueError):
            plan_case("BTCUSDT", pending, frames, 200, set())

    def test_canonical_physical_identity_branch_independent(self):
        a, fa = fixture("STB")
        b, fb = fixture("BREAKER")
        ca, _ = plan_case("BTCUSDT", a, fa, 200, set())
        cb, _ = plan_case("BTCUSDT", b, fb, 200, set())
        self.assertEqual(ca["physical_idea_id"], cb["physical_idea_id"])

    def test_fixed_priority_unique(self):
        self.assertEqual(len(set(PRIORITY.values())), 5)
        self.assertEqual(min(PRIORITY, key=PRIORITY.get), "BREAKER")

    def test_OTE_EQ_and_ATR_not_fitted(self):
        self.assertEqual(PARAMETERS["OTE"], ["0.705", "0.79"])
        self.assertEqual(PARAMETERS["EQ"], "0.5")
        self.assertEqual(PARAMETERS["ATR"], 14)

    def test_epsilon_explicitly_theoretical(self):
        self.assertEqual(epsilon(D(100)), D("0.00000100"))

    def test_liquidity_roles_are_total_and_not_standalone_trigger(self):
        _pending, frames = fixture()
        pools = liquidity_inventory(frames, frames[60].context, "LONG", D(10), D(9))
        self.assertEqual(pools[0]["role"], "TARGET_FUEL")
        self.assertIn(pools[0]["scope"], ("INTERNAL", "EXTERNAL"))

    def test_serialization_and_identity_stable(self):
        self.assertEqual(
            ident("test", serial({"p": D("1.1")})), ident("test", {"p": "1.1"})
        )

    def test_live_rejected_before_data_access(self):
        with self.assertRaises(ValueError):
            build_cohort("BTCUSDT", {}, mode="LIVE")

    def test_gap_data_rejected(self):
        b = bars(VALUES)
        with self.assertRaises(ValueError):
            Frame("BTCUSDT", 60, [b[0], b[2]])
