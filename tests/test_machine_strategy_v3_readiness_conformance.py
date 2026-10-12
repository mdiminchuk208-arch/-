"""Synthetic, pre-entry conformance checks for the frozen v3 adapter.

This module never reads historical market files or computes trade outcomes.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from machine_strategy_v2_core import Frame, serial
from machine_strategy_v3_contracts import (
    ContractReject,
    ContractWait,
    completed_atr14,
    first_test,
    raw_family_prices,
    reserve_idea,
)
from machine_strategy_v3_guarded_runner import (
    COUNTERS,
    HistoricalOutcomeBlocked,
    authorize_later,
    run_historical,
    run_registered_fixture,
)
from machine_strategy_v3_historical_adapter import (
    HistoricalAdapter,
    HistoricalFrame,
    derive_market,
    inventories,
)
from original_v1_1_financial_data import Bar

D = Decimal


def bars(values: list[tuple], tf: int = 15, start: int = 0) -> list[Bar]:
    return [
        Bar(
            start + i * tf * 60,
            start + (i + 1) * tf * 60,
            *(D(str(value)) for value in row),
        )
        for i, row in enumerate(values)
    ]


def mirrored(values: list[tuple], pivot: int = 1000) -> list[tuple]:
    return [
        (pivot - opening, pivot - low, pivot - high, pivot - close)
        for opening, high, low, close in values
    ]


def synthetic_epoch() -> dict:
    return {
        "id": "synthetic-tick",
        "symbol": "BTCUSDT",
        "contract_type": "USDT_LINEAR_PERPETUAL",
        "tick": "0.1",
        "verified": True,
        "known_at": 0,
        "source_known_at": 0,
        "effective_proof_known_at": 0,
        "effective_from": 0,
        "effective_until": 1000000,
        "source_sha256": "1" * 64,
    }


def pending_fixture(branch: str, direction: str) -> tuple[HistoricalAdapter, dict]:
    """Supply complete synthetic frame evidence directly to plan_pending."""
    short = direction == "SHORT"
    old_low, old_high = (80, 120)
    context = {
        "id": "h1-context",
        "direction": direction,
        "low": D(old_low),
        "high": D(old_high),
        "EQ": D(100),
        "OTE": [D(95), D(105)],
    }

    def frame(tf: int):
        state = {
            "state": "TREND_DOWN" if short else "TREND_UP",
            "direction": direction,
            "context_id": f"context-{tf}",
            "known_at": 14400,
        }
        pool = {
            "id": f"pool-{tf}",
            "known_at": 10800,
            "payload": {
                "side": "LOW" if short else "HIGH",
                "price": "85" if short else "115",
            },
        }
        return SimpleNamespace(
            state=lambda _at: dict(state),
            context=context,
            pools={pool["id"]: pool} if tf == 60 else {},
            candidates_zones=lambda _direction: [],
            confirmed_bos={},
            zones={},
            retired_ranges={},
            range_record=lambda: None,
        )

    original = {"id": "origin", "low": D(98), "high": D(102), "born_at": 7200}
    refinement = {
        "id": "refined-poi",
        "kind": "OB",
        "direction": direction,
        "low": D(100 if short else 99),
        "high": D(101 if short else 100),
        "born_at": 10800,
        "origin_bos_id": "m15-bos",
        "consumed_at": None,
    }
    confirmation = {
        "id": "m15-conf",
        "bos_id": "m15-bos",
        "known_at": 14400,
        "direction": direction,
    }
    bos = {"id": "m15-bos", "known_at": 10800, "direction": direction}
    m15 = SimpleNamespace(
        confirmations=[confirmation],
        bos=[bos],
        bos_by_id={bos["id"]: bos},
        candidates_zones=lambda candidate: (
            [refinement] if candidate == direction else []
        ),
    )
    adapter = HistoricalAdapter.__new__(HistoricalAdapter)
    adapter.symbol = "BTCUSDT"
    adapter.epochs = [synthetic_epoch()]
    adapter.registry = {"physical": (), "pois": ()}
    adapter.frames = {15: m15, 60: frame(60), 240: frame(240), 1440: frame(1440)}
    zone = dict(original)
    if branch == "STB" or branch == "BREAKER":
        zone.update(low=D(99), high=D(101))
    elif branch == "RANGE":
        zone.update(low=D(100), high=D(100))
    formation_bar = Bar(3600, 7200, D(100), D(103), D(97), D(100))
    item = {
        "branch": branch,
        "direction": direction,
        "setup_tf": 60,
        "formation_id": "formation",
        "formation_at": 7200,
        "formation_bar": formation_bar,
        "reaction_at": 10800,
        "zone": zone,
        "extreme": D(105 if short else 95),
        "atr": D(1),
        "range": {
            "id": "native-range",
            "known_at": 3600,
            "low": D(80 if short else 100),
            "high": D(100 if short else 120),
        },
    }
    return adapter, item


def flat_run_adapter() -> HistoricalAdapter:
    native = bars([(100, 100, 100, 100)] * 96)
    market, _ = derive_market(native)
    return HistoricalAdapter(
        "BTCUSDT", market, [], evaluation_start=0, evaluation_end=86400
    )


def inject_pending_at(
    adapter: HistoricalAdapter, formation_at: int, key: tuple[str, str], pending: dict
) -> None:
    original_discover = adapter.discover

    def discover(at: int) -> None:
        original_discover(at)
        if at == formation_at:
            adapter.pending[key] = copy.deepcopy(pending)

    adapter.discover = discover


class FrozenPrimitiveConformance(unittest.TestCase):
    """Adapter expectations pinned to existing M2/M3 machine contracts."""

    def test_all_29_inherited_rules_and_explicit_override_markers(self) -> None:
        provenance = json.loads(
            (ROOT / "docs/machine_strategy_v3_design/RULE_PROVENANCE.json").read_text()
        )
        inherited = provenance["inherited_rules"]
        self.assertEqual(len(inherited), 29)
        self.assertEqual(
            {rule["rule_id"] for rule in inherited if rule["overridden"]},
            {
                "M2_TF",
                "M2_CONTEXT",
                "M2_HTF",
                "M2_FIRST_TEST",
                "M2_IDENTITIES",
                "M2_ENTRY",
                "M2_STOP",
                "M2_FTA",
                "M2_RANGE_EXIT",
                "M2_INTRABAR",
            },
        )

    def test_strict_swing_and_bos_use_completed_prefix(self) -> None:
        values = [
            (10, 11, 8, 10),
            (10, 12, 7, 10),
            (10, 11, 8, 10),
            (10, 14, 9, 13),
            (13, 15, 10, 14),
            (14, 14.5, 10, 13),
            (13, 14, 11, 13),
        ]
        full = Frame("BTCUSDT", 60, bars(values, 60))
        mutated = Frame("BTCUSDT", 60, bars(values[:6] + [(100, 101, 90, 100)], 60))
        full.advance(21600)
        mutated.advance(21600)
        self.assertEqual(serial(full.context), serial(mutated.context))
        self.assertEqual(full.context["protected_price"], D(7))
        self.assertLess(
            full.bos_by_id[full.context["bos_id"]]["known_at"],
            full.context["known_at"],
        )
        reflected = Frame("BTCUSDT", 60, bars(mirrored(values), 60))
        reflected.advance(21600)
        self.assertEqual(reflected.context["direction"], "SHORT")

    def test_sfp_atr_pinned_to_pattern_end_with_previous_close(self) -> None:
        values = [(100, 102, 99, 101)] * 15
        native = bars(values, 60)
        payload = [
            {
                "start": candle.start,
                "end": candle.end,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
            }
            for candle in native
        ]
        pattern_end = native[-1].end
        atr = completed_atr14(payload, pattern_end, 3600, pattern_end)
        appended = copy.deepcopy(payload)
        appended.append(
            {
                "start": pattern_end,
                "end": pattern_end + 3600,
                "open": D(101),
                "high": D(500),
                "low": D(1),
                "close": D(101),
            }
        )
        self.assertEqual(
            completed_atr14(appended, pattern_end + 3600, 3600, pattern_end), atr
        )
        raw = raw_family_prices(
            family="SFP",
            direction="LONG",
            zone_low=99,
            zone_high=101,
            stop_anchor=98,
            atr14=atr,
        )
        self.assertEqual(raw["raw_stop_boundary"], D(98) - atr)
        with self.assertRaisesRegex(ContractWait, "WAIT_ATR14_PREFIX"):
            completed_atr14(payload[:14], pattern_end, 3600, pattern_end)

    def test_first_eligible_native_touch_has_occurrence_bounds(self) -> None:
        poi = {"id": "native", "known_at": 3600, "low": 99, "high": 101}
        opening = {"start": 7200, "end": 10800, "open": 100, "high": 102, "low": 98}
        wick = {**opening, "open": 102}
        before = first_test(poi, opening, eligibility_at=10800)
        self.assertNotIn("consumed_at", before)
        open_test = first_test(poi, opening, eligibility_at=7200)
        self.assertEqual(open_test["first_touch_time_bounds"], (7200, 7200))
        self.assertEqual(open_test["consumed_at"], 10800)
        wick_test = first_test(poi, wick, eligibility_at=7200)
        self.assertEqual(wick_test["first_touch_time_bounds"], (7200, 10800))
        self.assertEqual(first_test(open_test, wick, eligibility_at=7200), open_test)


class HistoricalAdapterConformance(unittest.TestCase):
    def test_adapter_prefix_equal_when_future_ohlc_mutates(self) -> None:
        h1_values = [
            (100, 102, 99, 100),
            (100, 101, 95, 99),
            (99, 103, 98, 100),
            (100, 101, 94, 98),
            (98, 102, 93, 101),
        ]
        native_values = []
        for opening, high, low, close in h1_values:
            native_values.extend(
                [
                    (opening, high, low, opening),
                    (opening, opening, opening, opening),
                    (opening, opening, opening, opening),
                    (opening, max(opening, close), min(opening, close), close),
                ]
            )
        native_values.extend([(100, 100, 100, 100)] * (96 - len(native_values)))
        original = bars(native_values)
        altered = original + bars([(100, 300, 10, 250)] * 4, start=86400)
        first_market, _ = derive_market(original)
        second_market, _ = derive_market(altered)
        first = HistoricalAdapter(
            "BTCUSDT", first_market, [], evaluation_start=0, evaluation_end=86400
        )
        second = HistoricalAdapter(
            "BTCUSDT", second_market, [], evaluation_start=0, evaluation_end=86400
        )
        first_orders, first_receipt = first.run(cutoff=18000)
        second_orders, second_receipt = second.run(cutoff=18000)
        self.assertEqual(first_orders, second_orders)
        self.assertEqual(first_receipt, second_receipt)
        self.assertGreater(
            sum(v for k, v in first_receipt["counts"].items() if k.startswith("RAW_")),
            0,
        )

    def test_refinement_negative_contracts_for_all_families(self) -> None:
        for branch in ("SFP", "OB", "BREAKER", "STB", "RANGE"):
            with self.subTest(branch=branch, gate="missing_confirm"):
                adapter, item = pending_fixture(branch, "LONG")
                adapter.frames[15].confirmations = []
                with self.assertRaisesRegex(ContractWait, "WAIT_REFINEMENT_BOS_CONF"):
                    adapter.plan_pending(item, 18000)
            with self.subTest(branch=branch, gate="reverse_bos"):
                adapter, item = pending_fixture(branch, "LONG")
                adapter.frames[15].bos.append(
                    {"id": "reverse", "known_at": 12600, "direction": "SHORT"}
                )
                with self.assertRaisesRegex(
                    ContractReject, "REJECT_NON_SMOOTH_STRUCTURAL_APPROACH"
                ):
                    adapter.plan_pending(item, 18000)
            with self.subTest(branch=branch, gate="consumed_poi"):
                adapter, item = pending_fixture(branch, "LONG")
                item["zone"]["consumed_at"] = 12600
                if branch in ("SFP", "OB"):
                    adapter.frames[15].candidates_zones = lambda _direction: []
                    with self.assertRaisesRegex(
                        ContractWait, "WAIT_ORIGIN_BOUND_REFINEMENT_POI"
                    ):
                        adapter.plan_pending(item, 18000)
                else:
                    with self.assertRaisesRegex(
                        ContractReject, "REJECT_CONSUMED_OR_RESERVED_POI"
                    ):
                        adapter.plan_pending(item, 18000)

    def test_sfp_next_native_open_available_only_at_native_close(self) -> None:
        for setup_tf, formation_at, before, available in (
            (60, 3600, 3600, 7200),
            (240, 14400, 18000, 28800),
        ):
            with self.subTest(setup_tf=setup_tf):
                key = (f"manual-{setup_tf}", "SFP")
                pending = {
                    "branch": "SFP",
                    "direction": "LONG",
                    "formation_id": key[0],
                    "formation_at": formation_at,
                    "formation_bar": Bar(
                        0, formation_at, D(100), D(100), D(100), D(100)
                    ),
                    "setup_tf": setup_tf,
                    "expiry": formation_at + 57600,
                    "reaction_at": formation_at,
                    "next_open_required": True,
                    "level": D(99),
                }

                def awaiting_refinement(_item: dict, _at: int) -> None:
                    raise ContractWait("WAIT_REFINEMENT_BOS_CONF")

                adapter = flat_run_adapter()
                inject_pending_at(adapter, formation_at, key, pending)
                adapter.plan_pending = awaiting_refinement
                adapter.run(cutoff=before)
                self.assertTrue(adapter.pending[key]["next_open_required"])
                # `run` is one forward pass; replay from a fresh adapter for a later cut.
                ready = flat_run_adapter()
                inject_pending_at(ready, formation_at, key, pending)
                ready.plan_pending = awaiting_refinement
                ready.run(cutoff=available)
                evidence = ready.pending[key]["next_open_evidence"]
                self.assertEqual(evidence["actual_at"], formation_at)
                self.assertEqual(evidence["known_at"], available)
                self.assertFalse(ready.pending[key]["next_open_required"])
        rejected = flat_run_adapter()
        equal_pending = {
            "branch": "SFP",
            "direction": "LONG",
            "formation_id": "equal-open",
            "formation_at": 3600,
            "formation_bar": Bar(0, 3600, D(100), D(100), D(100), D(100)),
            "setup_tf": 60,
            "expiry": 61200,
            "reaction_at": 3600,
            "next_open_required": True,
            "level": D(100),
        }
        inject_pending_at(rejected, 3600, ("equal-open", "SFP"), equal_pending)
        _, report = rejected.run(cutoff=7200)
        self.assertEqual(report["diagnostics"][0]["reason"], "REJECT_SFP_NEXT_OPEN")

    def test_ob_and_range_native_reaction_wait_for_later_completed_bar(self) -> None:
        for branch in ("OB", "RANGE"):
            with self.subTest(branch=branch):
                adapter = flat_run_adapter()
                key = (f"native-{branch}", branch)
                pending = {
                    "branch": branch,
                    "direction": "LONG",
                    "formation_id": key[0],
                    "formation_at": 3600,
                    "formation_bar": Bar(0, 3600, D(100), D(100), D(100), D(100)),
                    "setup_tf": 60,
                    "expiry": 61200,
                    "reaction_at": None,
                    "next_open_required": False,
                    "zone": {"id": "reaction", "low": D(100), "high": D(100)},
                    "range": {"low": D(90), "high": D(110)},
                }
                inject_pending_at(adapter, 3600, key, pending)

                def awaiting_refinement(_item: dict, _at: int) -> None:
                    raise ContractWait("WAIT_REFINEMENT_BOS_CONF")

                adapter.plan_pending = awaiting_refinement
                adapter.run(cutoff=3600)
                self.assertIsNone(adapter.pending[key]["reaction_at"])
                later = flat_run_adapter()
                inject_pending_at(later, 3600, key, pending)
                later.plan_pending = awaiting_refinement
                later.run(cutoff=7200)
                self.assertEqual(later.pending[key]["reaction_at"], 7200)
                missed = flat_run_adapter()
                no_contact = copy.deepcopy(pending)
                no_contact["zone"] = {
                    "id": "outside",
                    "low": D(90),
                    "high": D(91),
                }
                inject_pending_at(missed, 3600, key, no_contact)
                missed.run(cutoff=7200)
                self.assertIsNone(missed.pending[key]["reaction_at"])

    def test_breaker_raw_parent_contextual_birth_and_full_interval_extreme(
        self,
    ) -> None:
        for direction, values in (
            ("LONG", [(100, 102, 98, 100), (100, 104, 97, 103)]),
            ("SHORT", mirrored([(100, 102, 98, 100), (100, 104, 97, 103)], 200)),
        ):
            with self.subTest(direction=direction):
                frame = HistoricalFrame("BTCUSDT", 60, bars(values, 60))
                frame.advance(3600)
                parent_direction = "SHORT" if direction == "LONG" else "LONG"
                frame.zones["parent-ob"] = {
                    "id": "parent-ob",
                    "kind": "OB",
                    "direction": parent_direction,
                    "low": D(98),
                    "high": D(102),
                    "born_at": 3600,
                    "contextual_at_birth": True,
                    "consumed_at": None,
                    "raw": {"payload": {"body_low": "99", "body_high": "101"}},
                }
                frame.advance(7200)
                adapter = HistoricalAdapter.__new__(HistoricalAdapter)
                adapter.frames = {60: frame, 240: SimpleNamespace(cursor=0)}
                adapter.pending = {}
                adapter.broken_obs = set()
                adapter.seen_ranges = set()
                adapter.start = 0
                adapter.counts = Counter()
                adapter.discover(7200)
                formed = [
                    p for p in adapter.pending.values() if p["branch"] == "BREAKER"
                ]
                self.assertEqual(len(formed), 1)
                item = formed[0]
                self.assertEqual(item["zone"]["low"], D(99))
                self.assertEqual(item["zone"]["high"], D(101))
                self.assertEqual(item["extreme"], D(97 if direction == "LONG" else 103))
                self.assertEqual(item["formation_at"], 7200)
                self.assertIn("parent-ob", adapter.broken_obs)

    def test_range_raw_deviation_reclaim_is_native_and_mirrored(self) -> None:
        for direction, values in (
            ("LONG", [(100, 105, 95, 100), (100, 105, 89, 100)]),
            ("SHORT", mirrored([(100, 105, 95, 100), (100, 105, 89, 100)], 200)),
        ):
            with self.subTest(direction=direction):
                frame = HistoricalFrame("BTCUSDT", 60, bars(values, 60))
                frame.advance(3600)
                frame.context = {
                    "id": "leg",
                    "direction": direction,
                    "known_at": 3600,
                    "protected_price": D(80 if direction == "LONG" else 120),
                    "end_swing_at": 0,
                    "low": D(80),
                    "high": D(120),
                }
                frame.range = {
                    "id": "native-range",
                    "known_at": 3600,
                    "low": D(90),
                    "high": D(110),
                    "EQ": D(100),
                    "context_id": "leg",
                }
                frame.range_mid_reacted = True
                frame.range_reactions["native-range"] = 3600
                frame.advance(7200)
                adapter = HistoricalAdapter.__new__(HistoricalAdapter)
                adapter.frames = {60: frame, 240: SimpleNamespace(cursor=0)}
                adapter.pending = {}
                adapter.broken_obs = set()
                adapter.seen_ranges = set()
                adapter.start = 0
                adapter.counts = Counter()
                adapter.discover(7200)
                formed = [p for p in adapter.pending.values() if p["branch"] == "RANGE"]
                self.assertEqual(len(formed), 1)
                self.assertEqual(formed[0]["direction"], direction)
                self.assertEqual(formed[0]["range"]["id"], "native-range")
                self.assertEqual(formed[0]["reaction_at"], None)

    def test_raw_sfp_ob_stb_formations_are_mirrored_and_strict(self) -> None:
        long = [
            (100, 102, 99, 100),
            (100, 101, 95, 99),
            (99, 103, 98, 100),
            (100, 101, 94, 98),
            (98, 102, 93, 101),
        ]
        for direction, values in (("LONG", long), ("SHORT", mirrored(long, 200))):
            with self.subTest(direction=direction):
                frame = HistoricalFrame("BTCUSDT", 60, bars(values, 60))
                frame.advance(3 * 3600)
                self.assertTrue(any(o["kind"] == "swing" for o in frame.new_events))
                frame.advance(4 * 3600)
                self.assertTrue(
                    any(
                        o["kind"] == "SFP" and o["payload"]["direction"] == direction
                        for o in frame.new_events
                    )
                )
                frame.advance(5 * 3600)
                for family in ("OB", "STB"):
                    self.assertTrue(
                        any(
                            o["kind"] == family
                            and o["payload"]["direction"] == direction
                            for o in frame.new_events
                        )
                    )
        equal_raid = long[:3] + [(100, 101, 95, 98)]
        frame = HistoricalFrame("BTCUSDT", 60, bars(equal_raid, 60))
        frame.advance(4 * 3600)
        self.assertFalse(any(o["kind"] == "SFP" for o in frame.new_events))

    def test_sfp_missing_required_atr_prefix_is_named_wait(self) -> None:
        values = [
            (100, 102, 99, 100),
            (100, 101, 95, 99),
            (99, 103, 98, 100),
            (100, 101, 94, 98),
        ]
        frame = HistoricalFrame("BTCUSDT", 60, bars(values, 60))
        frame.advance(4 * 3600)
        self.assertTrue(any(o["kind"] == "SFP" for o in frame.new_events))
        adapter = HistoricalAdapter.__new__(HistoricalAdapter)
        adapter.frames = {60: frame, 240: SimpleNamespace(cursor=0)}
        adapter.pending = {}
        adapter.broken_obs = set()
        adapter.seen_ranges = set()
        adapter.start = 0
        adapter.counts = Counter()
        adapter.discover(4 * 3600)
        self.assertGreater(adapter.counts["WAIT_ATR14_PREFIX"], 0)
        self.assertFalse(any(p["branch"] == "SFP" for p in adapter.pending.values()))

    def test_native_range_eq_lock_boundary_retirement_and_no_reactivation(self) -> None:
        series = bars(
            [
                (100, 105, 95, 100),
                (100, 102, 98, 100),
                (100, 106, 96, 101),
                (101, 112, 99, 110),
                (100, 106, 96, 101),
            ],
            60,
        )
        frame = HistoricalFrame("BTCUSDT", 60, series)
        frame.advance(3600)
        frame.context = {
            "id": "leg",
            "direction": "LONG",
            "known_at": 3600,
            "protected_price": D(80),
            "end_swing_at": 0,
            "low": D(80),
            "high": D(120),
        }
        frame.range = {
            "id": "fixed-range",
            "known_at": 3600,
            "low": D(90),
            "high": D(110),
            "EQ": D(100),
            "context_id": "leg",
        }
        frame.range_mid_reacted = False
        frame.advance(7200)
        self.assertEqual(frame.range_record()["eq_reacted_at"], 7200)
        frame.advance(10800)
        self.assertEqual(frame.range["id"], "fixed-range")
        frame.advance(14400)
        self.assertEqual(frame.retired_ranges["fixed-range"], 14400)
        self.assertNotEqual(
            frame.range_record()["id"] if frame.range_record() else None,
            "fixed-range",
        )
        frame.advance(18000)
        self.assertNotIn("fixed-range", {r["id"] for r in [frame.range] if r})

    def test_protected_origin_body_loss_is_strict_and_mirrored(self) -> None:
        for direction, values, protected in (
            (
                "LONG",
                [(100, 101, 99, 100), (100, 101, 98, 99), (99, 100, 97, 97)],
                D(99),
            ),
            (
                "SHORT",
                mirrored(
                    [(100, 101, 99, 100), (100, 101, 98, 99), (99, 100, 97, 97)], 200
                ),
                D(101),
            ),
        ):
            with self.subTest(direction=direction):
                frame = HistoricalFrame("BTCUSDT", 60, bars(values, 60))
                frame.advance(3600)
                frame.context = {
                    "id": "protected",
                    "direction": direction,
                    "known_at": 3600,
                    "protected_price": protected,
                }
                frame.advance(7200)
                self.assertIsNotNone(frame.context)
                frame.advance(10800)
                self.assertIsNone(frame.context)
                self.assertEqual(frame.state(10800)["state"], "UNCERTAIN")

    def test_simultaneous_opposing_confirmations_are_uncertain(self) -> None:
        frame = HistoricalFrame("BTCUSDT", 60, bars([(100, 101, 99, 100)], 60))
        frame.advance(3600)
        frame.confirmations = [
            {"id": "long-confirm", "direction": "LONG", "known_at": 3600},
            {"id": "short-confirm", "direction": "SHORT", "known_at": 3600},
        ]
        self.assertEqual(frame.state(3600)["state"], "UNCERTAIN")

    def test_physical_bucket_and_poi_reservation_never_reenter(self) -> None:
        first = reserve_idea({"physical": (), "pois": ()}, "same-time-LONG", "poi-1")
        with self.assertRaisesRegex(ContractReject, "REJECT_DUPLICATE_PHYSICAL_OR_POI"):
            reserve_idea(first, "same-time-LONG", "poi-2")
        with self.assertRaisesRegex(ContractReject, "REJECT_DUPLICATE_PHYSICAL_OR_POI"):
            reserve_idea(first, "later-time-LONG", "poi-1")
        opposite = reserve_idea(first, "same-time-SHORT", "poi-3")
        self.assertEqual(len(opposite["physical"]), 2)

    def test_opposing_contextual_zone_containing_entry_rejects(self) -> None:
        for direction in ("LONG", "SHORT"):
            with self.subTest(direction=direction):
                adapter, item = pending_fixture("STB", direction)
                opposite = "SHORT" if direction == "LONG" else "LONG"
                zone = {
                    "id": "opposing-zone",
                    "kind": "FVG",
                    "direction": opposite,
                    "low": D(99),
                    "high": D(101),
                    "born_at": 7200,
                    "origin_bos_id": "opposite-bos",
                    "consumed_at": None,
                }
                frame = adapter.frames[240]
                frame.confirmed_bos["opposite-bos"] = 10800
                frame.candidates_zones = (
                    lambda candidate, zone=zone, opposite=opposite: (
                        [zone] if candidate == opposite else []
                    )
                )
                with self.assertRaisesRegex(
                    ContractReject, "REJECT_ENTRY_IN_OPPOSING_POI"
                ):
                    adapter.plan_pending(item, 18000)

    def test_h4_range_uses_formation_bar_boundary_contact(self) -> None:
        for direction in ("LONG", "SHORT"):
            with self.subTest(direction=direction):
                adapter, item = pending_fixture("STB", direction)
                h4 = adapter.frames[240]
                h4_state = {
                    "state": "RANGE",
                    "direction": direction,
                    "context_id": "context-240",
                    "range_id": "h4-range",
                    "known_at": 14400,
                }
                h4_range = {
                    "id": "h4-range",
                    "context_id": "context-240",
                    "known_at": 0,
                    "eq_reacted_at": 3600,
                    "invalidated_at": None,
                    "low": D(98 if direction == "LONG" else 80),
                    "high": D(120 if direction == "LONG" else 102),
                }
                h4.state = lambda _at, state=h4_state: dict(state)
                h4.range_record = lambda record=h4_range: dict(record)
                self.assertEqual(
                    adapter.plan_pending(item, 18000)["context"]["context"],
                    "RANGE_CONTEXT",
                )
                h4_range["low" if direction == "LONG" else "high"] = D(
                    90 if direction == "LONG" else 110
                )
                with self.assertRaisesRegex(
                    ContractWait, "WAIT_RANGE_BOUNDARY_FORMATION"
                ):
                    adapter.plan_pending(item, 18000)

    def test_transition_context_requires_formation_open_parent_poi(self) -> None:
        adapter, item = pending_fixture("STB", "LONG")
        h4 = adapter.frames[240]
        h4.state = lambda _at: {
            "state": "TRANSITION_UP",
            "direction": "LONG",
            "context_id": "context-240",
            "known_at": 14400,
        }
        with self.assertRaisesRegex(ContractWait, "WAIT_TRANSITION_ORIGIN_POI"):
            adapter.plan_pending(item, 18000)
        parent = {
            "id": "known-parent",
            "kind": "OB",
            "direction": "LONG",
            "low": D(98),
            "high": D(102),
            "born_at": 0,
            "origin_bos_id": "h4-origin-bos",
            "consumed_at": None,
        }
        h4.confirmed_bos[parent["origin_bos_id"]] = 3600
        h4.candidates_zones = lambda candidate: [parent] if candidate == "LONG" else []
        order = adapter.plan_pending(item, 18000)
        self.assertEqual(order["context"]["context"], "MIXED_OR_TRANSITION_CONTEXT")
        h4.confirmed_bos[parent["origin_bos_id"]] = 3601
        with self.assertRaisesRegex(ContractWait, "WAIT_TRANSITION_ORIGIN_POI"):
            adapter.plan_pending(item, 18000)

    def test_complete_m15_groups_derive_4_16_96_utc_bars(self) -> None:
        values = [(100, 101 + i % 4, 99 - i % 3, 100 + i % 2) for i in range(96)]
        m15 = bars(values)
        market, receipt = derive_market(m15)
        self.assertEqual(
            [len(market[tf]) for tf in (15, 60, 240, 1440)], [96, 24, 6, 1]
        )
        for tf, width in ((60, 4), (240, 16), (1440, 96)):
            first = market[tf][0]
            self.assertEqual(first.start, 0)
            self.assertEqual(first.end, tf * 60)
            self.assertEqual(first.open, m15[0].open)
            self.assertEqual(first.close, m15[width - 1].close)
            self.assertEqual(first.high, max(b.high for b in m15[:width]))
            self.assertEqual(first.low, min(b.low for b in m15[:width]))
            self.assertEqual(receipt[str(tf)]["excluded_incomplete_groups"], [])
        extended, _ = derive_market(m15 + bars([(100, 110, 90, 101)], start=86400))
        self.assertEqual(extended[1440], market[1440])

    def test_missing_or_duplicate_native_bar_never_aggregates(self) -> None:
        series = bars([(100, 101, 99, 100)] * 96)
        for malformed in (
            series[:4] + series[5:],
            series[:5] + [series[4]] + series[5:],
        ):
            with self.subTest(size=len(malformed)), self.assertRaises(ContractWait):
                derive_market(malformed)

    def test_all_five_families_mirror_pre_entry_price_and_lineage(self) -> None:
        for branch in ("SFP", "OB", "BREAKER", "STB", "RANGE"):
            for direction in ("LONG", "SHORT"):
                with self.subTest(branch=branch, direction=direction):
                    adapter, item = pending_fixture(branch, direction)
                    order = adapter.plan_pending(item, 18000)
                    self.assertEqual(order["branch"], branch)
                    self.assertEqual(order["direction"], direction)
                    self.assertEqual(order["confirmation_id"], "m15-conf")
                    self.assertEqual(order["context"]["context"], "TREND_CONTEXT")
                    self.assertEqual(
                        order["entry_poi_id"],
                        "refined-poi" if branch in ("SFP", "OB") else "origin",
                    )
                    self.assertFalse(order["source_validated"])
                    self.assertFalse(order["trade_entry_allowed"])
                    self.assertEqual(order["status"], "PENDING")
                    self.assertEqual(order["expires_at"], 21600)
                    self.assertEqual(order["stop_anchor"], str(item["extreme"]))
                    entry, stop, target = (
                        D(order[k]) for k in ("entry", "stop", "target")
                    )
                    if direction == "LONG":
                        self.assertLess(stop, entry)
                        self.assertLess(entry, target)
                    else:
                        self.assertLess(target, entry)
                        self.assertLess(entry, stop)
                    if branch == "SFP":
                        self.assertEqual(
                            D(order["raw_stop_boundary"]),
                            item["extreme"] + (D(1) if direction == "SHORT" else -D(1)),
                        )

    def test_reaction_close_bos_equality_is_inherited(self) -> None:
        adapter, item = pending_fixture("STB", "LONG")
        self.assertEqual(
            adapter.frames[15].bos_by_id["m15-bos"]["known_at"],
            item["reaction_at"],
        )
        self.assertEqual(
            adapter.plan_pending(item, 18000)["confirmation_id"], "m15-conf"
        )
        adapter.frames[15].bos_by_id["m15-bos"]["known_at"] -= 1
        with self.assertRaisesRegex(ContractWait, "WAIT_REFINEMENT_BOS_CONF"):
            adapter.plan_pending(item, 18000)

    def test_missing_metadata_and_retired_source_range_block_orders(self) -> None:
        adapter, item = pending_fixture("RANGE", "LONG")
        adapter.epochs = []
        with self.assertRaisesRegex(ContractWait, "WAIT_HISTORICAL_TICK_METADATA"):
            adapter.plan_pending(item, 18000)
        adapter.epochs = [synthetic_epoch()]
        adapter.frames[60].retired_ranges[item["range"]["id"]] = 17000
        with self.assertRaisesRegex(ContractReject, "REJECT_RETIRED_SOURCE_RANGE"):
            adapter.plan_pending(item, 18000)

    def test_complete_inventory_nearest_ties_and_internal_adverse(self) -> None:
        adapter, item = pending_fixture("STB", "LONG")
        frames = adapter.frames
        twin = {
            "id": "coincident-pool",
            "known_at": 10800,
            "payload": {"side": "HIGH", "price": "115"},
        }
        frames[240].pools[twin["id"]] = twin
        order = adapter.plan_pending(item, 18000)
        self.assertEqual(len(order["coincident_fta_ids"]), 2)
        self.assertEqual(
            sorted(order["coincident_fta_ids"]),
            sorted(["pool-60", "coincident-pool"]),
        )
        self.assertEqual(len(order["all_FTA_inventory"]), 2)
        adverse = {
            "id": "internal-adverse",
            "known_at": 10800,
            "payload": {"side": "LOW", "price": "90"},
        }
        frames[60].pools[adverse["id"]] = adverse
        with self.assertRaisesRegex(
            ContractReject, "REJECT_INTERNAL_ADVERSE_POOL_BEYOND_STOP"
        ):
            adapter.plan_pending(item, 18000)
        targets, liquidity = inventories(
            frames, "LONG", D(100), D(94), frames[60].context
        )
        self.assertEqual(len(targets), 2)
        self.assertTrue(
            next(p for p in liquidity if p["id"] == adverse["id"])["adverse"]
        )

    def test_nearest_pool_between_raw_and_rounded_entry_is_not_omitted(self) -> None:
        adapter, item = pending_fixture("STB", "LONG")
        item["zone"].update(low=D("100.0"), high=D("100.1"))
        adapter.frames[60].pools["near-rounded-entry"] = {
            "id": "near-rounded-entry",
            "known_at": 10800,
            "payload": {"side": "HIGH", "price": "100.02"},
        }
        with self.assertRaisesRegex(ContractReject, "REJECT_ROUNDING_COLLISION"):
            adapter.plan_pending(item, 18000)

    def test_native_first_test_consumption_is_recorded_at_close(self) -> None:
        series = bars([(100, 101, 99, 100)] * 2, 60)
        frame = HistoricalFrame("BTCUSDT", 60, series)
        frame.advance(3600)
        zone = {
            "id": "eligible-native-poi",
            "kind": "OB",
            "direction": "LONG",
            "low": D(99),
            "high": D(101),
            "born_at": 3600,
            "origin_bos_id": "bos",
            "consumed_at": None,
        }
        frame.zones[zone["id"]] = zone
        frame.active_zones.add(zone["id"])
        frame.confirmed_bos["bos"] = 3600
        frame.context = {
            "id": "context",
            "direction": "LONG",
            "known_at": 3600,
            "protected_price": D(90),
        }
        frame.advance(7200)
        touched = frame.zones[zone["id"]]
        self.assertEqual(touched["consumed_at"], 7200)
        self.assertEqual(touched["first_touch_time_bounds"], (3600, 3600))
        self.assertEqual(touched["first_touch_observed_at"], 7200)


class GuardedRunnerConformance(unittest.TestCase):
    def test_historical_callable_fails_closed_before_data_access(self) -> None:
        before = dict(COUNTERS)
        with self.assertRaisesRegex(
            HistoricalOutcomeBlocked,
            "IMPLEMENTATION_READINESS_FORBIDS_HISTORICAL_OUTCOMES",
        ):
            run_historical("BTCUSDT", [], None)
        self.assertEqual(
            COUNTERS["historical_outcome_evaluations"],
            before["historical_outcome_evaluations"],
        )
        with self.assertRaisesRegex(
            HistoricalOutcomeBlocked,
            "IMPLEMENTATION_READINESS_FORBIDS_HISTORICAL_OUTCOMES",
        ):
            authorize_later(ROOT / "unused-fixture-authorization.json")

    def test_registered_synthetic_event_paths_return_no_financial_fields(self) -> None:
        expected = {
            "open_stop": "EXIT_OBSERVED",
            "wick_ambiguous": "WAIT_INTRABAR_ORDER",
            "prefill_target_gap": "GAP_INVALIDATED_BEFORE_FILL",
            "filled_then_stop_gap": "EXIT_OBSERVED",
            "filled_eof": "OPEN_CENSORED_EOF",
            "unfilled_eof": "ORDER_CENSORED_EOF",
            "dual_touch": "WAIT_INTRABAR_ORDER",
        }
        for recipe, status in expected.items():
            with self.subTest(recipe=recipe):
                event = run_registered_fixture(recipe)
                self.assertEqual(event["status"], status)
                self.assertFalse(event["trade_entry_allowed"])
                self.assertFalse(
                    {"amounts", "financial_outcome", "modeled_cash_stop_R"} & set(event)
                )
        with self.assertRaisesRegex(
            HistoricalOutcomeBlocked, "UNKNOWN_INTERNAL_SYNTHETIC_FIXTURE"
        ):
            run_registered_fixture("caller-provided-history")


if __name__ == "__main__":
    unittest.main()
