from __future__ import annotations

import unittest
from decimal import Decimal

from source_strategy_v1_core import (
    Bar,
    LiquidityLevel,
    Pivot,
    RawSfpCandidate,
    SourceSemanticError,
    assert_nonfinancial_record,
    detect_bos,
    detect_imbalances,
    detect_range_deviations,
    exact_equal_liquidity,
    label_pivots,
    ote_levels,
    range_boundary,
    raw_sfp_candidates,
    strict_three_bar_pivots,
    structure_state,
)


D = Decimal


def bar(start, o, h, l, c, tf=15):
    return Bar(start, start + tf * 60, D(str(o)), D(str(h)), D(str(l)), D(str(c)), tf)


def pivot(identifier, side, price, known_at, label=None, tf=15):
    return Pivot(
        id=identifier,
        side=side,
        price=D(str(price)),
        source_bar_start=known_at - 2 * tf * 60,
        source_bar_end=known_at - tf * 60,
        known_at=known_at,
        timeframe_minutes=tf,
        label=label,
    )


class TestSourceStrategyV1Core(unittest.TestCase):
    def test_strict_pivot_is_not_known_until_right_bar_closes(self):
        bars = [
            bar(0, 7, 10, 4, 7),
            bar(900, 7, 12, 6, 8),
            bar(1800, 8, 11, 5, 6),
        ]
        self.assertEqual(strict_three_bar_pivots(bars, 2699), [])
        pivots = strict_three_bar_pivots(bars, 2700)
        highs = [p for p in pivots if p.side == "HIGH"]
        self.assertEqual(len(highs), 1)
        self.assertEqual(highs[0].price, D("12"))
        self.assertEqual(highs[0].known_at, 2700)

    def test_structure_labels_bullish_hh_hl(self):
        raw = [
            pivot("h1", "HIGH", 10, 1000),
            pivot("l1", "LOW", 5, 1100),
            pivot("h2", "HIGH", 12, 1200),
            pivot("l2", "LOW", 6, 1300),
        ]
        labeled = label_pivots(raw)
        state = structure_state(labeled, 1300)
        self.assertEqual(state.latest_high_label, "HH")
        self.assertEqual(state.latest_low_label, "HL")
        self.assertEqual(state.trend, "BULLISH")

    def test_equal_structure_stays_unknown(self):
        raw = [
            pivot("h1", "HIGH", 10, 1000),
            pivot("l1", "LOW", 5, 1100),
            pivot("h2", "HIGH", 10, 1200),
            pivot("l2", "LOW", 6, 1300),
        ]
        state = structure_state(label_pivots(raw), 1300)
        self.assertEqual(state.latest_high_label, "EQUAL_HIGH")
        self.assertEqual(state.trend, "UNKNOWN")

    def test_bos_uses_completed_close_not_wick(self):
        pivots = [
            pivot("h1", "HIGH", 10, 1000),
            pivot("l1", "LOW", 5, 1100),
            pivot("h2", "HIGH", 12, 1200, "HH"),
            pivot("l2", "LOW", 6, 1300, "HL"),
        ]
        wick_only = Bar(2000, 2900, D("7"), D("8"), D("5"), D("6.5"), 15)
        close_break = Bar(2900, 3800, D("6.5"), D("7"), D("4.5"), D("5.5"), 15)
        self.assertEqual(detect_bos([wick_only], pivots, 2900), [])
        events = detect_bos([wick_only, close_break], pivots, 3800)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].direction, "BEARISH")
        self.assertEqual(events[0].broken_pivot_id, "l2")

    def test_wick_gap_imbalance_has_no_hidden_size_threshold(self):
        bars = [
            bar(0, 8, 10, 7, 9),
            bar(900, 9, 11, 8, 10),
            bar(1800, 10.2, 11.2, 10.01, 11),
        ]
        result = detect_imbalances(bars, 2700)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].direction, "BULLISH")
        self.assertEqual(result[0].zone_low, D("10"))
        self.assertEqual(result[0].zone_high, D("10.01"))
        self.assertIn("UNKNOWN_IMPULSE_STRENGTH", result[0].unresolved)

    def test_exact_equal_liquidity_does_not_invent_tolerance(self):
        pivots = [
            pivot("h1", "HIGH", 100, 1000),
            pivot("h2", "HIGH", 100, 2000),
            pivot("h3", "HIGH", 100.01, 3000),
        ]
        levels = exact_equal_liquidity(pivots)
        self.assertEqual(len(levels), 1)
        self.assertEqual(levels[0].kind, "EXACT_EQH")
        self.assertEqual(levels[0].source_ids, ("h1", "h2"))
        self.assertIn("UNKNOWN_EQH_EQL_TOLERANCE", levels[0].unresolved)

    def test_ote_source_levels_are_exact_given_explicit_anchors(self):
        levels = ote_levels(0, 100)
        self.assertEqual(levels["0.5"], "50")
        self.assertEqual(levels["0.62"], "62")
        self.assertEqual(levels["0.705"], "70.5")
        self.assertEqual(levels["0.79"], "79")

    def test_raw_sfp_preserves_unresolved_source_semantics(self):
        level = LiquidityLevel(
            id="level-100",
            kind="SWING_HIGH",
            price=D("100"),
            known_at=0,
            timeframe_minutes=15,
            source_ids=("h1",),
        )
        sweep = Bar(900, 1800, D("99"), D("105"), D("98"), D("99"), 15)
        candidates = raw_sfp_candidates([sweep], [level], 1800)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.direction, "SHORT")
        self.assertEqual(candidate.state, "UNKNOWN_SOURCE_SEMANTICS")
        self.assertIn("UNKNOWN_SFP_EXACT_THREE_CANDLE_GEOMETRY", candidate.unresolved)
        self.assertFalse(hasattr(candidate, "pnl"))

    def test_future_level_cannot_create_past_sfp(self):
        level = LiquidityLevel(
            id="future-level",
            kind="SWING_HIGH",
            price=D("100"),
            known_at=2000,
            timeframe_minutes=15,
            source_ids=("future",),
        )
        sweep = Bar(900, 1800, D("99"), D("105"), D("98"), D("99"), 15)
        self.assertEqual(raw_sfp_candidates([sweep], [level], 1800), [])

    def test_range_deviation_is_evidence_not_trade(self):
        low = pivot("low", "LOW", 90, 1000)
        high = pivot("high", "HIGH", 110, 1100)
        rng = range_boundary(low, high)
        above = Bar(2000, 2900, D("105"), D("115"), D("102"), D("108"), 15)
        deviations = detect_range_deviations([above], rng, 2900)
        self.assertEqual(len(deviations), 1)
        self.assertEqual(deviations[0].direction, "ABOVE")
        self.assertEqual(rng.state, "UNKNOWN_SOURCE_SEMANTICS")

    def test_financial_fields_are_forbidden_in_stage_2(self):
        candidate = RawSfpCandidate(
            id="x",
            direction="LONG",
            level_id="l",
            level_price=D("1"),
            sweep_bar_start=0,
            known_at=900,
            timeframe_minutes=15,
        )
        assert_nonfinancial_record(candidate)
        with self.assertRaisesRegex(SourceSemanticError, "FINANCIAL_FIELD_FORBIDDEN"):
            assert_nonfinancial_record({"pnl": "10"})

    def test_bar_validation_rejects_impossible_ohlc(self):
        with self.assertRaises(SourceSemanticError):
            Bar(0, 900, D("20"), D("10"), D("5"), D("7"), 15)


if __name__ == "__main__":
    unittest.main()
