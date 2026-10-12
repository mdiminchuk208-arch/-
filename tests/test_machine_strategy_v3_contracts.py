"""Synthetic, non-financial contract tests for the pre-outcome v3 design."""

import unittest
from decimal import Decimal

from scripts.machine_strategy_v3_contracts import (
    ContractReject,
    ContractWait,
    admit_context,
    cash_stop_identity,
    censor_eof,
    completed_atr14,
    first_test,
    holding_duration_bounds,
    proven_tick_epoch,
    raw_family_prices,
    require_known_at,
    reserve_idea,
)
from scripts.machine_strategy_v3_contracts import (
    executable_plan as _executable_plan,
)
from scripts.machine_strategy_v3_contracts import (
    frame_state as _frame_state,
)
from scripts.machine_strategy_v3_contracts import (
    observe_m15_bar as _observe_m15_bar,
)

D = Decimal


def epoch(tick="0.1", **overrides):
    # Synthetic proof-shaped fixture; no historical metadata is asserted.
    return {
        "id": "e1",
        "symbol": "BTCUSDT",
        "contract_type": "USDT_LINEAR_PERPETUAL",
        "effective_from": 0,
        "effective_until": 1000,
        "known_at": 0,
        "source_known_at": 0,
        "effective_proof_known_at": 0,
        "source_sha256": "a" * 64,
        "verified": True,
        "tick": tick,
        **overrides,
    }


def leg(ident, direction, origin, endpoint, known_at):
    return {
        "id": ident,
        "direction": direction,
        "origin": origin,
        "endpoint": endpoint,
        "known_at": known_at,
        "end_swing_at": known_at - 1,
    }


def bar(start, *, opening="101", high="103", low="99", close=None):
    return {
        "start": start,
        "end": start + 900,
        "open": opening,
        "high": high,
        "low": low,
        "close": opening if close is None else close,
    }


def executable_plan(*, raw, targets, zone_low, zone_high, epoch, decision_at):
    return _executable_plan(
        raw={"known_at": 0, **raw},
        targets=targets,
        zone_low=zone_low,
        zone_high=zone_high,
        epochs=[epoch],
        symbol="BTCUSDT",
        contract_type="USDT_LINEAR_PERPETUAL",
        decision_at=decision_at,
    )


def observe_m15_bar(order, candle):
    order = {
        "symbol": "BTCUSDT",
        "contract_type": "USDT_LINEAR_PERPETUAL",
        "tick_epoch_id": "e1",
        **order,
    }
    return _observe_m15_bar(order, candle, [epoch(effective_until=10000)])


def frame_state(**kwargs):
    return _frame_state(latest_close_known_at=30, **kwargs)


class MetadataAndCausalityTests(unittest.TestCase):
    def test_unique_known_verified_epoch_and_edges(self):
        e = epoch()
        self.assertEqual(
            proven_tick_epoch([e], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 0, 100)["id"],
            "e1",
        )
        self.assertEqual(
            proven_tick_epoch([e], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 999, 100)["id"],
            "e1",
        )
        for epochs, at, decision in [
            ([], 1, 100),
            ([e], 1000, 1000),
            ([e, {**e, "id": "e2"}], 1, 100),
            ([{**e, "known_at": 101}], 1, 100),
            ([{**e, "verified": False}], 1, 100),
        ]:
            with (
                self.subTest(epochs=epochs, at=at),
                self.assertRaisesRegex(ContractWait, "TICK_METADATA"),
            ):
                proven_tick_epoch(
                    epochs, "BTCUSDT", "USDT_LINEAR_PERPETUAL", at, decision
                )
        with self.assertRaises(ContractWait):
            proven_tick_epoch([e], "BTCUSDT", "SPOT", 1, 100)

    def test_epoch_proof_cannot_be_missing_malformed_or_future(self):
        original = epoch()
        variants = [
            {key: value for key, value in original.items() if key != "source_sha256"},
            {**original, "source_sha256": "short"},
            {**original, "source_sha256": "0" * 64},
            {**original, "source_known_at": 101},
            {**original, "effective_proof_known_at": 101},
            {**original, "tick": "0"},
            {**original, "contract_type": "SPOT"},
            {**original, "verified": "false"},
            {**original, "source_known_at": "unknown"},
            {**original, "effective_until": "unknown"},
            {**original, "tick": "unknown"},
        ]
        for candidate in variants:
            with (
                self.subTest(candidate=candidate),
                self.assertRaisesRegex(ContractWait, "TICK_METADATA"),
            ):
                proven_tick_epoch(
                    [candidate], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100
                )

    def test_epoch_times_reject_fraction_bool_nan_and_malformed_catalogue(self):
        original = epoch(effective_until=1000)
        for candidate in [
            {**original, "source_known_at": 100.9},
            {**original, "source_known_at": True},
            {**original, "effective_proof_known_at": float("nan")},
            {**original, "effective_from": 0.5},
            {**original, "effective_until": False},
        ]:
            with (
                self.subTest(candidate=candidate),
                self.assertRaisesRegex(ContractWait, "WAIT_HISTORICAL_TICK_METADATA"),
            ):
                proven_tick_epoch(
                    [candidate], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100
                )
        malformed_future_record = {**original, "id": "future", "effective_from": "bad"}
        with self.assertRaisesRegex(ContractWait, "WAIT_HISTORICAL_TICK_METADATA"):
            proven_tick_epoch(
                [original, malformed_future_record],
                "BTCUSDT",
                "USDT_LINEAR_PERPETUAL",
                1,
                100,
            )
        for bad_at, bad_decision in [(True, 100), (1.5, 100), (1, False), (1, 100.9)]:
            with (
                self.subTest(at=bad_at, decision=bad_decision),
                self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"),
            ):
                proven_tick_epoch(
                    [original], "BTCUSDT", "USDT_LINEAR_PERPETUAL", bad_at, bad_decision
                )

    def test_future_epoch_append_and_mutation_preserve_past_selection(self):
        old = epoch(effective_until=1000)
        future = epoch(
            id="future",
            known_at=200,
            effective_from=1000,
            effective_until=2000,
            source_known_at=200,
            effective_proof_known_at=200,
        )
        baseline = proven_tick_epoch([old], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100)
        self.assertEqual(
            proven_tick_epoch(
                [old, future], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100
            ),
            baseline,
        )
        mutated_future = {
            **future,
            "tick": "nonsense",
            "source_sha256": "bad",
            "effective_from": "unknown",
        }
        self.assertEqual(
            proven_tick_epoch(
                [old, mutated_future], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100
            ),
            baseline,
        )
        available_noncovering = {
            **future,
            "known_at": 0,
            "source_known_at": 200,
            "source_sha256": "bad",
        }
        self.assertEqual(
            proven_tick_epoch(
                [old, available_noncovering], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100
            ),
            baseline,
        )
        bad_availability = {**future, "known_at": 100.9}
        with self.assertRaisesRegex(ContractWait, "WAIT_HISTORICAL_TICK_METADATA"):
            proven_tick_epoch(
                [old, bad_availability], "BTCUSDT", "USDT_LINEAR_PERPETUAL", 1, 100
            )

    def test_recursive_input_validation_rejects_outcomes_and_nested_future(self):
        require_known_at(
            {"known_at": 10, "nested": [{"known_at": 9, "end_swing_at": 8}]}, 10
        )
        for payload, reason in [
            ({"known_at": 10, "nested": [{"known_at": 11}]}, "FUTURE_KNOWN_AT"),
            (
                {"known_at": 10, "nested": [{"known_at": 9, "end_swing_at": 10}]},
                "FUTURE_SWING_CENTER",
            ),
            (
                {"known_at": 10, "nested": [{"known_at": 9, "Net_R": "20"}]},
                "OUTCOME_INPUT_FIELD",
            ),
            ({"known_at": 10, "PnL": 1}, "OUTCOME_INPUT_FIELD"),
        ]:
            with (
                self.subTest(payload=payload),
                self.assertRaisesRegex(ContractReject, reason),
            ):
                require_known_at(payload, 10)

    def test_nested_known_and_swing_times_require_json_integers(self):
        for payload in [
            {"known_at": 10, "nested": [{"known_at": 10.9}]},
            {"known_at": 10, "nested": [{"known_at": True}]},
            {"known_at": 10, "nested": [{"known_at": 9, "end_swing_at": 9.5}]},
            {"known_at": 10, "nested": [{"known_at": 9, "end_swing_at": float("nan")}]},
            {"known_at": 10, "nested": [{"known_at": 9, "consumed_at": 9.5}]},
        ]:
            with (
                self.subTest(payload=payload),
                self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"),
            ):
                require_known_at(payload, 10)

    def test_known_at_and_swing_center_are_causal(self):
        require_known_at({"known_at": 10, "end_swing_at": 9}, 10)
        with self.assertRaisesRegex(ContractReject, "FUTURE_KNOWN_AT"):
            require_known_at({"known_at": 11}, 10)
        with self.assertRaisesRegex(ContractReject, "FUTURE_SWING_CENTER"):
            require_known_at({"known_at": 10, "end_swing_at": 11}, 10)
        with self.assertRaisesRegex(ContractReject, "FUTURE_STATE_CLOSE"):
            _frame_state(
                current=None,
                previous=None,
                range_event=None,
                latest_close=100,
                latest_close_known_at=31,
                decision_at=30,
            )


class StateTests(unittest.TestCase):
    def test_trend_transition_range_uncertain_mirror(self):
        for direction, previous, current, close, rlow, rhigh in [
            (
                "LONG",
                leg("p", "LONG", 90, 110, 10),
                leg("c", "LONG", 100, 120, 20),
                115,
                105,
                120,
            ),
            (
                "SHORT",
                leg("p", "SHORT", 110, 90, 10),
                leg("c", "SHORT", 100, 80, 20),
                85,
                80,
                95,
            ),
        ]:
            trend = frame_state(
                current=current,
                previous=previous,
                range_event=None,
                latest_close=close,
                decision_at=30,
            )
            self.assertEqual(
                trend["state"], "TREND_UP" if direction == "LONG" else "TREND_DOWN"
            )
            transition = frame_state(
                current=current,
                previous=None,
                range_event=None,
                latest_close=close,
                decision_at=30,
            )
            self.assertTrue(transition["state"].startswith("TRANSITION"))
            range_event = {
                "id": "r",
                "context_id": "c",
                "low": rlow,
                "high": rhigh,
                "known_at": 21,
                "eq_reacted_at": 22,
            }
            ranged = frame_state(
                current=current,
                previous=previous,
                range_event=range_event,
                latest_close=close,
                decision_at=30,
            )
            self.assertEqual(ranged["state"], "RANGE")
            invalidated = frame_state(
                current=current,
                previous=previous,
                range_event={**range_event, "invalidated_at": 25},
                latest_close=close,
                decision_at=30,
            )
            self.assertNotEqual(invalidated["state"], "RANGE")
            with self.assertRaisesRegex(ContractReject, "FUTURE_RANGE_INVALIDATION"):
                frame_state(
                    current=current,
                    previous=previous,
                    range_event={**range_event, "invalidated_at": 31},
                    latest_close=close,
                    decision_at=30,
                )
            invalid_close = 99 if direction == "LONG" else 101
            self.assertEqual(
                frame_state(
                    current=current,
                    previous=previous,
                    range_event=None,
                    latest_close=invalid_close,
                    decision_at=30,
                )["state"],
                "UNCERTAIN",
            )
        self.assertEqual(
            frame_state(
                current=None,
                previous=None,
                range_event=None,
                latest_close=100,
                decision_at=30,
            )["state"],
            "UNCERTAIN",
        )

    def test_state_cannot_use_structure_after_latest_close(self):
        current = leg("c", "LONG", 100, 120, 31)
        with self.assertRaisesRegex(ContractReject, "FUTURE_STATE_STRUCTURE"):
            _frame_state(
                current=current,
                previous=None,
                range_event=None,
                latest_close=110,
                latest_close_known_at=30,
                decision_at=40,
            )
        self.assertEqual(
            frame_state(
                current={**leg("c", "LONG", 100, 120, 20), "invalidated_at": 25},
                previous=None,
                range_event=None,
                latest_close=110,
                decision_at=30,
            )["state"],
            "UNCERTAIN",
        )
        self.assertEqual(
            frame_state(
                current=None,
                previous=None,
                range_event=None,
                latest_close=100,
                decision_at=30,
            )["known_at"],
            30,
        )

    def test_protected_equality_is_live_range_boundary_equality_retires(self):
        current = leg("c", "LONG", 100, 120, 20)
        self.assertNotEqual(
            frame_state(
                current=current,
                previous=None,
                range_event=None,
                latest_close=100,
                decision_at=30,
            )["state"],
            "UNCERTAIN",
        )
        r = {
            "id": "r",
            "context_id": "c",
            "low": 105,
            "high": 120,
            "known_at": 21,
            "eq_reacted_at": 22,
        }
        with self.assertRaisesRegex(ContractReject, "MISSING_RANGE_INVALIDATION"):
            frame_state(
                current=current,
                previous=None,
                range_event=r,
                latest_close=105,
                decision_at=30,
            )
        retired = frame_state(
            current=current,
            previous=None,
            range_event={**r, "invalidated_at": 30},
            latest_close=105,
            decision_at=30,
        )
        self.assertNotEqual(retired["state"], "RANGE")

    def test_h4_range_requires_live_matching_object(self):
        states = {
            "H1": {"state": "TRANSITION_UP", "direction": "LONG", "known_at": 30},
            "H4": {
                "state": "RANGE",
                "direction": "LONG",
                "known_at": 30,
                "context_id": "c",
                "range_id": "r",
            },
            "D1": {"state": "TREND_DOWN", "direction": "SHORT", "known_at": 30},
        }
        kwargs = {
            "states": states,
            "direction": "LONG",
            "formation_bar": {"start": 10, "end": 20, "low": 105, "high": 110},
            "m15_confirmation": {"known_at": 25, "direction": "LONG"},
            "parent_pois": [],
            "decision_at": 30,
        }
        valid = {
            "id": "r",
            "context_id": "c",
            "known_at": 5,
            "eq_reacted_at": 6,
            "low": 105,
            "high": 120,
        }
        for candidate in [
            {**valid, "id": "other"},
            {**valid, "invalidated_at": 7},
            {**valid, "eq_reacted_at": 11},
        ]:
            with (
                self.subTest(candidate=candidate),
                self.assertRaisesRegex(ContractWait, "H4_RANGE_OBJECT"),
            ):
                admit_context(**kwargs, h4_range=candidate)

    def test_aligned_opposite_higher_trends_wait_symmetrically(self):
        for direction, opposite_state in [
            ("LONG", "TREND_DOWN"),
            ("SHORT", "TREND_UP"),
        ]:
            h1 = "TRANSITION_UP" if direction == "LONG" else "TRANSITION_DOWN"
            opposite_direction = "SHORT" if direction == "LONG" else "LONG"
            states = {
                "H1": {"state": h1, "direction": direction, "known_at": 30},
                "H4": {
                    "state": opposite_state,
                    "direction": opposite_direction,
                    "known_at": 30,
                },
                "D1": {
                    "state": opposite_state,
                    "direction": opposite_direction,
                    "known_at": 30,
                },
            }
            with (
                self.subTest(direction=direction),
                self.assertRaisesRegex(ContractWait, "H4_D1_TREND_DIRECTION"),
            ):
                admit_context(
                    states=states,
                    direction=direction,
                    formation_bar={"start": 10, "end": 20, "low": 90, "high": 110},
                    m15_confirmation={"known_at": 25, "direction": direction},
                    parent_pois=[
                        {
                            "id": "p",
                            "tf": "H4",
                            "direction": direction,
                            "known_at": 5,
                            "low": 95,
                            "high": 105,
                            "confirmed": True,
                            "consumed_at": None,
                        }
                    ],
                    decision_at=30,
                )

    def test_total_h4_d1_state_table_both_directions(self):
        labels = ("RANGE", "TREND_UP", "TREND_DOWN", "TRANSITION_UP", "TRANSITION_DOWN")
        for direction in ("LONG", "SHORT"):
            own = "TREND_UP" if direction == "LONG" else "TREND_DOWN"
            opposite = "TREND_DOWN" if direction == "LONG" else "TREND_UP"
            h1 = "TRANSITION_UP" if direction == "LONG" else "TRANSITION_DOWN"
            for h4_label in labels:
                for d1_label in labels:

                    def state(label, range_direction=direction):
                        state_direction = (
                            "LONG"
                            if label.endswith("UP")
                            else "SHORT"
                            if label.endswith("DOWN")
                            else range_direction
                        )
                        return {
                            "state": label,
                            "direction": state_direction,
                            "known_at": 30,
                            "context_id": "c",
                            "range_id": "r",
                        }

                    states = {
                        "H1": state(h1),
                        "H4": state(h4_label),
                        "D1": state(d1_label),
                    }
                    poi = {
                        "id": "p",
                        "tf": "H4",
                        "direction": direction,
                        "known_at": 5,
                        "low": 95,
                        "high": 105,
                        "confirmed": True,
                        "consumed_at": None,
                    }
                    kwargs = {
                        "states": states,
                        "direction": direction,
                        "formation_bar": {
                            "start": 10,
                            "end": 20,
                            "low": 95,
                            "high": 105,
                        },
                        "m15_confirmation": {"known_at": 25, "direction": direction},
                        "parent_pois": [poi],
                        "decision_at": 30,
                        "h4_range": {
                            "id": "r",
                            "context_id": "c",
                            "known_at": 5,
                            "eq_reacted_at": 6,
                            "low": 95,
                            "high": 105,
                        },
                    }
                    with self.subTest(direction=direction, h4=h4_label, d1=d1_label):
                        if h4_label == "RANGE":
                            expected = "RANGE_CONTEXT"
                        elif h4_label == d1_label == own:
                            expected = "TREND_CONTEXT"
                        elif h4_label == d1_label == opposite:
                            with self.assertRaisesRegex(
                                ContractWait, "H4_D1_TREND_DIRECTION"
                            ):
                                admit_context(**kwargs)
                            continue
                        else:
                            expected = "MIXED_OR_TRANSITION_CONTEXT"
                        self.assertEqual(admit_context(**kwargs)["context"], expected)
        valid_states = {
            "H1": {"state": "TRANSITION_UP", "direction": "LONG", "known_at": 30},
            "H4": {
                "state": "TREND_UP",
                "direction": "LONG",
                "known_at": 30,
                "context_id": "h4",
            },
            "D1": {
                "state": "TREND_UP",
                "direction": "LONG",
                "known_at": 30,
                "context_id": "d1",
            },
        }
        for tf in valid_states:
            uncertain = {
                **valid_states,
                tf: {"state": "UNCERTAIN", "direction": None, "known_at": 30},
            }
            with (
                self.subTest(uncertain=tf),
                self.assertRaisesRegex(ContractWait, "NO_CONFIRMED_STATE"),
            ):
                admit_context(
                    states=uncertain,
                    direction="LONG",
                    formation_bar={"start": 10, "end": 20, "low": 95, "high": 105},
                    m15_confirmation={"known_at": 25, "direction": "LONG"},
                    parent_pois=[],
                    decision_at=30,
                )

    def test_context_precedence_and_symmetry(self):
        confirm = {"known_at": 25, "direction": "LONG"}
        formation = {"start": 10, "end": 20, "low": 105, "high": 110}
        states = {
            "H1": {"state": "TRANSITION_UP", "direction": "LONG", "known_at": 30},
            "H4": {
                "state": "RANGE",
                "direction": "LONG",
                "range_id": "r",
                "context_id": "c",
                "known_at": 30,
            },
            "D1": {"state": "TREND_DOWN", "direction": "SHORT", "known_at": 30},
        }
        r = {
            "id": "r",
            "context_id": "c",
            "known_at": 5,
            "eq_reacted_at": 6,
            "low": 105,
            "high": 120,
        }
        self.assertEqual(
            admit_context(
                states=states,
                direction="LONG",
                formation_bar=formation,
                m15_confirmation=confirm,
                parent_pois=[],
                decision_at=30,
                h4_range=r,
            )["context"],
            "RANGE_CONTEXT",
        )
        states["H4"] = {
            "state": "TREND_UP",
            "direction": "LONG",
            "context_id": "h4",
            "known_at": 30,
        }
        states["D1"] = {
            "state": "TREND_UP",
            "direction": "LONG",
            "context_id": "d1",
            "known_at": 30,
        }
        self.assertEqual(
            admit_context(
                states=states,
                direction="LONG",
                formation_bar=formation,
                m15_confirmation=confirm,
                parent_pois=[],
                decision_at=30,
            )["context"],
            "TREND_CONTEXT",
        )
        states["D1"] = {"state": "TREND_DOWN", "direction": "SHORT", "known_at": 30}
        poi = {
            "id": "p",
            "tf": "D1",
            "direction": "LONG",
            "known_at": 9,
            "low": 106,
            "high": 108,
            "confirmed": True,
            "consumed_at": None,
        }
        self.assertEqual(
            admit_context(
                states=states,
                direction="LONG",
                formation_bar=formation,
                m15_confirmation=confirm,
                parent_pois=[poi],
                decision_at=30,
            )["context"],
            "MIXED_OR_TRANSITION_CONTEXT",
        )
        with self.assertRaises(ContractWait):
            admit_context(
                states=states,
                direction="LONG",
                formation_bar=formation,
                m15_confirmation=confirm,
                parent_pois=[{**poi, "known_at": 11}],
                decision_at=30,
            )
        mirrored = {
            "H1": {"state": "TRANSITION_DOWN", "direction": "SHORT", "known_at": 30},
            "H4": {
                "state": "TREND_DOWN",
                "direction": "SHORT",
                "context_id": "h4",
                "known_at": 30,
            },
            "D1": {
                "state": "TREND_DOWN",
                "direction": "SHORT",
                "context_id": "d1",
                "known_at": 30,
            },
        }
        self.assertEqual(
            admit_context(
                states=mirrored,
                direction="SHORT",
                formation_bar={"start": 10, "end": 20, "low": 90, "high": 95},
                m15_confirmation={"known_at": 25, "direction": "SHORT"},
                parent_pois=[],
                decision_at=30,
            )["context"],
            "TREND_CONTEXT",
        )
        with self.assertRaisesRegex(ContractReject, "INCONSISTENT_STATE"):
            admit_context(
                states={**mirrored, "H4": {**mirrored["H4"], "direction": "LONG"}},
                direction="SHORT",
                formation_bar={"start": 10, "end": 20, "low": 90, "high": 95},
                m15_confirmation={"known_at": 25, "direction": "SHORT"},
                parent_pois=[],
                decision_at=30,
            )


class PriceAndCostTests(unittest.TestCase):
    def test_atr_uses_exact_completed_prefix(self):
        bars = [
            {
                "start": i * 3600,
                "end": (i + 1) * 3600,
                "open": 100,
                "high": 102,
                "low": 98,
                "close": 100,
            }
            for i in range(15)
        ]
        self.assertEqual(completed_atr14(bars, 15 * 3600, 3600, 15 * 3600), D(4))
        with self.assertRaises(ContractWait):
            completed_atr14(bars, 13 * 3600, 3600, 13 * 3600)
        # Mutating a suffix after the cutoff cannot change the frozen prefix result.
        mutated_suffix = bars + [
            {
                "start": 15 * 3600,
                "end": 16 * 3600,
                "open": 1,
                "high": 100000,
                "low": 1,
                "close": 1,
            }
        ]
        self.assertEqual(
            completed_atr14(mutated_suffix, 15 * 3600, 3600, 15 * 3600), D(4)
        )
        self.assertEqual(
            completed_atr14(mutated_suffix, 16 * 3600, 3600, 15 * 3600), D(4)
        )
        with self.assertRaisesRegex(ContractWait, "ATR14_PATTERN_BAR"):
            completed_atr14(bars, 16 * 3600, 3600, 16 * 3600)

    def test_atr_rejects_invalid_candles_gaps_and_tf(self):
        bars = [
            {
                "start": i * 3600,
                "end": (i + 1) * 3600,
                "open": 100,
                "high": 102,
                "low": 98,
                "close": 100,
            }
            for i in range(15)
        ]
        for changed, reason in [
            ({**bars[-1], "low": -1}, "INVALID_ATR_BAR"),
            ({**bars[-1], "close": 103}, "INVALID_ATR_BAR"),
            (
                {
                    **bars[-1],
                    "start": bars[-1]["start"] + 3600,
                    "end": bars[-1]["end"] + 3600,
                },
                "ATR_NONCONTIGUOUS_PREFIX",
            ),
        ]:
            with (
                self.subTest(changed=changed),
                self.assertRaisesRegex(ContractReject, reason),
            ):
                completed_atr14(
                    bars[:-1] + [changed], 16 * 3600, 3600, int(changed["end"])
                )
        with self.assertRaisesRegex(ContractReject, "ATR_NATIVE_TF"):
            completed_atr14(bars, 15 * 3600, 900, 15 * 3600)

    def test_all_families_raw_price_contracts_both_directions(self):
        for family in ("SFP", "OB", "BREAKER", "STB", "RANGE"):
            for direction in ("LONG", "SHORT"):
                with self.subTest(family=family, direction=direction):
                    raw = raw_family_prices(
                        family=family,
                        direction=direction,
                        zone_low=99,
                        zone_high=101,
                        stop_anchor=98 if direction == "LONG" else 102,
                        atr14=2 if family == "SFP" else None,
                    )
                    self.assertEqual(raw["family"], family)
                    if direction == "LONG":
                        self.assertLess(raw["raw_stop_boundary"], raw["raw_entry"])
                    else:
                        self.assertGreater(raw["raw_stop_boundary"], raw["raw_entry"])
                    if family == "SFP":
                        self.assertEqual(
                            raw["raw_stop_boundary"],
                            D(96 if direction == "LONG" else 104),
                        )
                    if family == "STB":
                        self.assertEqual(raw["raw_entry"], D(100))

    def test_strict_grid_nearest_target_and_cash_stop_identity(self):
        raw = {"direction": "LONG", "raw_entry": D("100"), "raw_stop_boundary": D("99")}
        p = executable_plan(
            raw=raw,
            targets=[
                {"id": "far", "price": 110, "known_at": 1},
                {"id": "near", "price": 105, "known_at": 1},
            ],
            zone_low=99,
            zone_high=100,
            epoch=epoch(),
            decision_at=10,
        )
        self.assertEqual(
            (p["entry"], p["stop"], p["target"]), (D(100), D("98.9"), D("104.9"))
        )
        self.assertEqual(p["nearest_fta_id"], "near")
        stop = cash_stop_identity(p["entry"], p["stop"], p["stop"], "LONG")
        self.assertEqual(stop["modeled_cash_stop_R"], D(-1))
        self.assertEqual(
            stop["modeled_gross_cash"]
            - stop["modeled_fee_cash"]
            - stop["modeled_slippage_cash"],
            stop["modeled_net_cash"],
        )
        self.assertLess(
            abs(
                stop["modeled_gross_R"]
                - stop["modeled_fee_R"]
                - stop["modeled_slippage_R"]
                - stop["modeled_cash_stop_R"]
            ),
            D("1e-24"),
        )
        self.assertEqual(p["raw_price_risk_D"], D("1.1"))
        self.assertEqual(p["raw_price_risk_ticks"], D(11))
        self.assertEqual(
            p["stop_cost_share_of_unit"] + p["raw_price_risk_D"] / p["cash_stop_unit"],
            D(1),
        )
        self.assertGreater(p["modeled_target_cash_margin"], 0)
        with self.assertRaisesRegex(ContractReject, "UNECONOMIC_NEAREST_FTA"):
            executable_plan(
                raw=raw,
                targets=[
                    {"id": "near", "price": D("100.2"), "known_at": 1},
                    {"id": "far", "price": 110, "known_at": 1},
                ],
                zone_low=99,
                zone_high=100,
                epoch=epoch(),
                decision_at=10,
            )

    def test_reflection_and_positive_price_tick_scaling(self):
        long = executable_plan(
            raw={"direction": "LONG", "raw_entry": 100, "raw_stop_boundary": 99},
            targets=[{"id": "f", "price": 105, "known_at": 1}],
            zone_low=99,
            zone_high=100,
            epoch=epoch(),
            decision_at=10,
        )
        short = executable_plan(
            raw={"direction": "SHORT", "raw_entry": 100, "raw_stop_boundary": 101},
            targets=[{"id": "f", "price": 95, "known_at": 1}],
            zone_low=100,
            zone_high=101,
            epoch=epoch(),
            decision_at=10,
        )
        self.assertEqual(short["entry"], 200 - long["entry"])
        self.assertEqual(short["stop"], 200 - long["stop"])
        self.assertEqual(short["target"], 200 - long["target"])
        self.assertNotEqual(short["cash_stop_unit"], long["cash_stop_unit"])
        scaled = executable_plan(
            raw={"direction": "LONG", "raw_entry": 1000, "raw_stop_boundary": 990},
            targets=[{"id": "f", "price": 1050, "known_at": 1}],
            zone_low=990,
            zone_high=1000,
            epoch=epoch(tick="1"),
            decision_at=10,
        )
        self.assertEqual(scaled["cash_stop_unit"], 10 * long["cash_stop_unit"])
        self.assertEqual(scaled["raw_price_risk_ticks"], long["raw_price_risk_ticks"])
        self.assertEqual(
            scaled["target_move_to_cost_ratio"], long["target_move_to_cost_ratio"]
        )

    def test_tiny_structural_stop_retains_cost_diagnostics(self):
        plan = executable_plan(
            raw={
                "direction": "LONG",
                "raw_entry": 100,
                "raw_stop_boundary": D("99.99"),
            },
            targets=[{"id": "t", "price": 105, "known_at": 1}],
            zone_low=99,
            zone_high=100,
            epoch=epoch(tick="0.01"),
            decision_at=10,
        )
        self.assertEqual(plan["raw_price_risk_ticks"], D(2))
        self.assertGreater(plan["stop_cost_share_of_unit"], D("0.8"))
        self.assertGreater(plan["entry_notional_per_cash_stop_unit"], 100)

    def test_coincident_nearest_fta_ids_are_all_recorded(self):
        plan = executable_plan(
            raw={"direction": "LONG", "raw_entry": 100, "raw_stop_boundary": 99},
            targets=[
                {"id": "z", "price": 105, "known_at": 1},
                {"id": "a", "price": 105, "known_at": 1},
                {"id": "far", "price": 110, "known_at": 1},
            ],
            zone_low=99,
            zone_high=100,
            epoch=epoch(),
            decision_at=10,
        )
        self.assertEqual(plan["nearest_fta_id"], "a")
        self.assertEqual(plan["coincident_fta_ids"], ("a", "z"))
        self.assertEqual(plan["tick_evidence_scope"], "GRID_REPRESENTABILITY_ONLY")

    def test_rounded_entry_outside_zone_and_stop_collision(self):
        with self.assertRaisesRegex(ContractReject, "ENTRY_OUTSIDE_ZONE"):
            executable_plan(
                raw={
                    "direction": "LONG",
                    "raw_entry": D("100.01"),
                    "raw_stop_boundary": 99,
                },
                targets=[{"id": "t", "price": 105, "known_at": 1}],
                zone_low=D("100.01"),
                zone_high=D("100.02"),
                epoch=epoch(tick="0.1"),
                decision_at=10,
            )
        with self.assertRaisesRegex(ContractReject, "STOP_GEOMETRY"):
            executable_plan(
                raw={
                    "direction": "LONG",
                    "raw_entry": 100,
                    "raw_stop_boundary": D("100.1"),
                },
                targets=[{"id": "t", "price": 105, "known_at": 1}],
                zone_low=99,
                zone_high=100,
                epoch=epoch(tick="0.1"),
                decision_at=10,
            )

    def test_rounding_collision_and_future_fta(self):
        raw = {"direction": "LONG", "raw_entry": D("100"), "raw_stop_boundary": D("99")}
        with self.assertRaisesRegex(ContractReject, "ROUNDING_COLLISION"):
            executable_plan(
                raw=raw,
                targets=[{"id": "x", "price": D("100.1"), "known_at": 1}],
                zone_low=99,
                zone_high=100,
                epoch=epoch(),
                decision_at=10,
            )
        with self.assertRaisesRegex(ContractReject, "FUTURE_KNOWN_AT"):
            executable_plan(
                raw=raw,
                targets=[{"id": "x", "price": 105, "known_at": 11}],
                zone_low=99,
                zone_high=100,
                epoch=epoch(),
                decision_at=10,
            )
        with self.assertRaisesRegex(ContractReject, "ENTRY_IN_OPPOSING_POI"):
            executable_plan(
                raw=raw,
                targets=[
                    {
                        "id": "z",
                        "price": 105,
                        "zone_low": 99,
                        "zone_high": 101,
                        "known_at": 1,
                    }
                ],
                zone_low=99,
                zone_high=100,
                epoch=epoch(),
                decision_at=10,
            )


class LifecycleTests(unittest.TestCase):
    def test_first_test_and_duplicate_reservation(self):
        poi = {"id": "p", "known_at": 10, "low": 99, "high": 101, "consumed_at": None}
        untouched = first_test(
            poi,
            {"start": 10, "end": 11, "open": 100, "low": 99, "high": 101},
            eligibility_at=11,
        )
        self.assertIsNone(untouched["consumed_at"])
        touched = first_test(
            poi,
            {"start": 11, "end": 12, "open": 102, "low": 99, "high": 102},
            eligibility_at=11,
        )
        self.assertEqual(touched["consumed_at"], 12)
        self.assertEqual(touched["first_touch_time_bounds"], (11, 12))
        self.assertEqual(touched["first_touch_observed_at"], 12)
        open_touch = first_test(
            poi,
            {"start": 11, "end": 12, "open": 100, "low": 99, "high": 101},
            eligibility_at=11,
        )
        self.assertEqual(open_touch["first_touch_time_bounds"], (11, 11))
        self.assertEqual(
            first_test(
                touched,
                {"start": 12, "end": 13, "open": 100, "low": 99, "high": 101},
                eligibility_at=11,
            )["first_touch_time_bounds"],
            (11, 12),
        )
        reserved = reserve_idea({}, "physical", "p")
        with self.assertRaises(ContractReject):
            reserve_idea(reserved, "physical", "new")
        with self.assertRaises(ContractReject):
            reserve_idea(reserved, "new", "p")

    def test_intrabar_wait_bounds_open_ordering_and_gap(self):
        order = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
        }
        wick = observe_m15_bar(order, bar(0, opening=101, high=106, low=99))
        self.assertEqual(wick["status"], "WAIT_INTRABAR_ORDER")
        self.assertEqual(wick["event_time_bounds"], (0, 900))
        wick_stop = observe_m15_bar(order, bar(0, opening=101, high=103, low=97))
        self.assertEqual(wick_stop["status"], "WAIT_INTRABAR_ORDER")
        open_fill = observe_m15_bar(order, bar(0, opening=100, high=103, low=97))
        self.assertEqual(open_fill["status"], "EXIT_OBSERVED")
        self.assertEqual(open_fill["fill_price"], D(100))
        self.assertEqual(open_fill["event_time_bounds"], (0, 900))
        self.assertEqual(
            open_fill["price_evidence_tag"], "MODELED_STOP_TRIGGER_PLUS_SLIPPAGE"
        )
        gap = observe_m15_bar(order, bar(0, opening=106, high=107, low=105))
        self.assertEqual(gap["status"], "GAP_INVALIDATED_BEFORE_FILL")
        filled = observe_m15_bar(order, bar(0, opening=101, high=103, low=99))
        self.assertEqual(filled["status"], "FILLED")
        self.assertEqual(filled["fill_time_bounds"], (0, 900))
        self.assertEqual(
            filled["fill_price_evidence_tag"], "TOUCH_IMPLIES_FULL_LIMIT_FILL_AT_E"
        )
        later = observe_m15_bar(filled, bar(900, opening=97, high=99, low=96))
        self.assertEqual(
            (later["status"], later["exit_price"], later["event_time_bounds"]),
            ("EXIT_OBSERVED", D(97), (900, 900)),
        )
        self.assertNotIn("Net_R", later)
        self.assertEqual(later["price_evidence_tag"], "OBSERVED_BAR_OPEN")
        self.assertEqual(
            observe_m15_bar({**order, "last_observed_end": 3600}, bar(3600))["status"],
            "UNFILLED_EXPIRED",
        )
        with self.assertRaises(ContractReject):
            observe_m15_bar({**order, "decision_at": 100}, bar(0))

    def test_short_intrabar_reflection(self):
        order = {
            "status": "PENDING",
            "direction": "SHORT",
            "entry": 100,
            "stop": 102,
            "target": 95,
            "decision_at": 0,
            "expires_at": 3600,
        }
        wick = observe_m15_bar(order, bar(0, opening=99, high=101, low=94))
        self.assertEqual(wick["status"], "WAIT_INTRABAR_ORDER")
        open_fill = observe_m15_bar(order, bar(0, opening=100, high=103, low=97))
        self.assertEqual(
            (open_fill["status"], open_fill["exit_reason"]),
            ("EXIT_OBSERVED", "FIXED_INITIAL_STOP"),
        )

    def test_active_order_requires_epoch_for_entire_observed_bar(self):
        order = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
            "symbol": "BTCUSDT",
            "contract_type": "USDT_LINEAR_PERPETUAL",
            "tick_epoch_id": "e1",
        }
        with self.assertRaisesRegex(ContractWait, "TICK_METADATA"):
            _observe_m15_bar(order, bar(0), [epoch(effective_until=450)])
        with self.assertRaisesRegex(ContractWait, "TICK_METADATA"):
            _observe_m15_bar(order, bar(0), [epoch(), epoch(id="e2")])

    def test_expiry_is_known_without_future_tick_proof(self):
        order = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
            "symbol": "BTCUSDT",
            "contract_type": "USDT_LINEAR_PERPETUAL",
            "tick_epoch_id": "e1",
            "last_observed_end": 3600,
        }
        self.assertEqual(
            _observe_m15_bar(order, bar(3600), [])["status"], "UNFILLED_EXPIRED"
        )

    def test_missing_interior_m15_bar_waits_including_at_expiry(self):
        order = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
        }
        with self.assertRaisesRegex(ContractWait, "WAIT_DATA_GAP"):
            observe_m15_bar(order, bar(900))
        with self.assertRaisesRegex(ContractWait, "WAIT_DATA_GAP"):
            observe_m15_bar(order, bar(3600))
        first = observe_m15_bar(order, bar(0, opening=102, high=103, low=101))
        self.assertEqual(first["last_observed_end"], 900)
        with self.assertRaisesRegex(ContractReject, "NONMONOTONIC_M15_BAR"):
            observe_m15_bar(first, bar(0))
        with self.assertRaisesRegex(ContractWait, "WAIT_DATA_GAP"):
            censor_eof(first, 3600)

    def test_holding_duration_remains_interval(self):
        bounds = holding_duration_bounds((0, 900), (900, 1800))
        self.assertEqual(
            bounds,
            {"minimum_seconds": 0, "maximum_seconds": 1800, "exact_seconds": None},
        )
        self.assertEqual(
            holding_duration_bounds((0, 0), (900, 900))["exact_seconds"], 900
        )

    def test_m15_alignment_ohlc_and_tick_grid_are_strict(self):
        order = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
        }
        for candle in [
            {**bar(0), "end": 901},
            {**bar(0), "start": 1, "end": 901},
            {**bar(0), "close": 104},
            {**bar(0), "low": 0},
        ]:
            with self.subTest(candle=candle), self.assertRaises(ContractReject):
                observe_m15_bar(order, candle)
        with self.assertRaisesRegex(ContractWait, "TICK_METADATA"):
            observe_m15_bar(order, {**bar(0), "high": D("103.05")})

    def test_sfp_native_close_invalidation_after_wick_checks(self):
        order = {
            "status": "FILLED",
            "branch": "SFP",
            "direction": "LONG",
            "entry": 100,
            "stop": 95,
            "target": 110,
            "decision_at": 0,
            "expires_at": 3600,
            "setup_tf_seconds": 3600,
            "stop_anchor": 99,
            "last_observed_end": 2700,
        }
        quiet = bar(2700, opening=100, high=101, low=98, close=98)
        observed = observe_m15_bar(order, quiet)
        self.assertEqual(
            (observed["exit_reason"], observed["event_time_bounds"]),
            ("SFP_PATTERN_BODY_INVALIDATION", (3600, 3600)),
        )
        self.assertEqual(observed["price_evidence_tag"], "OBSERVED_NATIVE_CLOSE")
        stopped = observe_m15_bar(order, {**quiet, "low": 94})
        self.assertEqual(stopped["exit_reason"], "FIXED_INITIAL_STOP")
        with self.assertRaisesRegex(ContractReject, "MISSING_SFP_NATIVE_INVALIDATION"):
            observe_m15_bar(
                {key: value for key, value in order.items() if key != "stop_anchor"},
                quiet,
            )

    def test_eof_censor_preserves_unknown_exit(self):
        base = {
            "status": "PENDING",
            "decision_at": 0,
            "expires_at": 3600,
            "last_observed_end": 1800,
        }
        self.assertEqual(censor_eof(base, 1800)["status"], "ORDER_CENSORED_EOF")
        self.assertEqual(
            censor_eof({**base, "last_observed_end": 3600}, 3600)["status"],
            "UNFILLED_EXPIRED",
        )
        opened = censor_eof({**base, "status": "FILLED"}, 1800)
        self.assertEqual(opened["status"], "OPEN_CENSORED_EOF")
        self.assertNotIn("exit_price", opened)

    def test_long_short_reflection_event_statuses(self):
        long = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
        }
        short = {**long, "direction": "SHORT", "stop": 102, "target": 95}
        long_cases = [
            bar(0, opening=101, high=103, low=99),
            bar(0, opening=101, high=106, low=99),
            bar(0, opening=101, high=103, low=97),
            bar(0, opening=100, high=106, low=99),
            bar(0, opening=106, high=107, low=105),
        ]
        expected = [
            "FILLED",
            "WAIT_INTRABAR_ORDER",
            "WAIT_INTRABAR_ORDER",
            "EXIT_OBSERVED",
            "GAP_INVALIDATED_BEFORE_FILL",
        ]
        for candle, status in zip(long_cases, expected):
            reflected = {
                "start": candle["start"],
                "end": candle["end"],
                "open": 200 - D(candle["open"]),
                "high": 200 - D(candle["low"]),
                "low": 200 - D(candle["high"]),
                "close": 200 - D(candle["close"]),
            }
            with self.subTest(status=status):
                self.assertEqual(observe_m15_bar(long, candle)["status"], status)
                self.assertEqual(observe_m15_bar(short, reflected)["status"], status)


class TimestampIntegrityTests(unittest.TestCase):
    def test_observation_rejects_fractional_bool_and_nan_times(self):
        order = {
            "status": "PENDING",
            "direction": "LONG",
            "entry": 100,
            "stop": 98,
            "target": 105,
            "decision_at": 0,
            "expires_at": 3600,
        }
        cases = [
            (order, {**bar(0), "start": 0.5}),
            (order, {**bar(0), "end": True}),
            (order, {**bar(0), "end": float("nan")}),
            ({**order, "decision_at": 0.5}, bar(0)),
            ({**order, "decision_at": False}, bar(0)),
            ({**order, "expires_at": 3600.9}, bar(0)),
            ({**order, "last_observed_end": True}, bar(0)),
        ]
        for candidate_order, candle in cases:
            with (
                self.subTest(order=candidate_order, bar=candle),
                self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"),
            ):
                observe_m15_bar(candidate_order, candle)

    def test_other_public_causal_times_are_exact(self):
        with self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"):
            frame_state(
                current=None,
                previous=None,
                range_event=None,
                latest_close=100,
                decision_at=30.5,
            )
        with self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"):
            _frame_state(
                current=None,
                previous=None,
                range_event=None,
                latest_close=100,
                latest_close_known_at=True,
                decision_at=30,
            )
        with self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"):
            completed_atr14([], True, 3600, 0)
        with self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"):
            first_test(
                {"known_at": 0, "low": 1, "high": 2},
                {"start": 0, "end": 1, "open": 1, "low": 1, "high": 2},
                eligibility_at=0.5,
            )
        with self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"):
            holding_duration_bounds((0, True), (1, 2))
        with self.assertRaisesRegex(ContractReject, "REJECT_NONINTEGER_TIMESTAMP"):
            censor_eof(
                {"status": "PENDING", "decision_at": 0, "expires_at": 3600},
                observed_through=0.5,
            )


if __name__ == "__main__":
    unittest.main()
