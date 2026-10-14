"""Synthetic evidence-boundary tests; no strategy or trade re-evaluation."""

import sys
import unittest
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_okx_v3_failure_audit_v1 as audit
from okx_v3_input_bridge_v1 import NativeBar


def bar(start, opening, high, low, close):
    return NativeBar(
        start,
        start + 900,
        *(D(str(x)) for x in (opening, high, low, close)),
        "BTC-USDT-SWAP",
    )


class FailureDiagnosticTests(unittest.TestCase):
    def test_price_envelope_mirrors_direction_and_is_not_a_trade(self):
        native = [bar(0, 100, 115, 92, 101)]
        self.assertEqual(
            audit.price_excursion(native, 100, "LONG"),
            {"favorable_D": D(15), "adverse_D": D(8)},
        )
        self.assertEqual(
            audit.price_excursion(native, 100, "SHORT"),
            {"favorable_D": D(8), "adverse_D": D(15)},
        )

    def test_exact_OPEN_exit_excludes_later_exit_bar_extremes(self):
        native = [bar(0, 100, 105, 95, 100), bar(900, 110, 999, 1, 100)]
        state = {
            "fill_time_bounds": [0, 0],
            "event_time_bounds": [900, 900],
            "fill_price": "100",
            "exit_price": "110",
            "direction": "LONG",
        }
        result = audit.exposure_excursion_bounds(native, state)
        self.assertEqual(result["upper_D"], {"favorable_D": "10", "adverse_D": "5"})
        self.assertEqual(result["possible_overlap_bars"], 1)

    def test_wick_boundaries_do_not_invent_exact_ordered_excursions(self):
        native = [
            bar(0, 101, 140, 80, 100),
            bar(900, 100, 110, 90, 100),
            bar(1800, 100, 130, 70, 101),
        ]
        state = {
            "fill_time_bounds": [0, 900],
            "event_time_bounds": [1800, 2700],
            "fill_price": "100",
            "exit_price": "105",
            "direction": "LONG",
        }
        result = audit.exposure_excursion_bounds(native, state)
        self.assertEqual(result["lower_D"], {"favorable_D": "10", "adverse_D": "10"})
        self.assertEqual(result["upper_D"], {"favorable_D": "40", "adverse_D": "30"})
        self.assertTrue(result["intrabar_exact_extrema_unknown"])

    def test_future_after_exit_cannot_change_excursion_bounds(self):
        native = [bar(0, 100, 105, 95, 100)]
        state = {
            "fill_time_bounds": [0, 0],
            "event_time_bounds": [900, 900],
            "fill_price": "100",
            "exit_price": "104",
            "direction": "LONG",
        }
        self.assertEqual(
            audit.exposure_excursion_bounds(native, state),
            audit.exposure_excursion_bounds(
                native + [bar(900, 104, 99999, 1, 300)], state
            ),
        )

    def test_cancellation_OPEN_does_not_admit_post_cancel_wicks(self):
        native = [bar(0, 110, 112, 109, 110)] + [
            bar(i * 900, 110, 112, 109, 110) for i in range(1, 5)
        ]
        order = {
            "decision_at": 900,
            "formation_at": 0,
            "expires_at": 4500,
            "direction": "LONG",
            "product": "BTC-USDT-SWAP",
            "branch": "RANGE",
            "setup_tf": 60,
            "context": "RANGE_CONTEXT",
        }
        state = {
            "scenario_id": "synthetic",
            "status": "GAP_INVALIDATED_BEFORE_FILL",
            "entry": "100",
            "stop": "90",
            "target": "105",
            "observed_at": 900,
        }
        case = {"case_id": "synthetic", "all_scenarios": [state]}
        a = audit.no_fill(order, case, native, [b.start for b in native], {})
        changed = [native[0], replace(native[1], high=D(999), low=D(1)), *native[2:]]
        b = audit.no_fill(order, case, changed, [b.start for b in changed], {})
        self.assertEqual(
            a["all_scenarios"][0]["active_order_price_envelope_D"],
            b["all_scenarios"][0]["active_order_price_envelope_D"],
        )
        self.assertNotEqual(
            a["all_scenarios"][0]["full_expiry_window_price_envelope_D"],
            b["all_scenarios"][0]["full_expiry_window_price_envelope_D"],
        )
        self.assertTrue(
            b["all_scenarios"][0]["full_window_includes_post_cancellation_prices"]
        )

    def test_decision_geometry_ATR_and_mark_ignore_future_bars(self):
        native = [bar(i * 900, 100, 102, 98, 100) for i in range(20)]
        at = 15 * 900
        order = {
            "decision_at": at,
            "entry": "99",
            "stop": "95",
            "target": "110",
            "fixed_R_unit": "4.1552",
            "direction": "LONG",
            "branch": "SFP",
            "formation_id": "origin",
            "formation_at": 3600,
            "confirmation_known_at": at,
            "expires_at": at + 3600,
            "target_move_to_cost_ratio": "65",
            "modeled_target_cash_margin": "10.8328",
            "stop_cost_share_of_unit": ".037",
        }
        raw = {"origin": {"atr": "2", "reaction_at": 7200}}
        changed = [
            replace(b, high=D(9999), low=D(1)) if b.start > at else b for b in native
        ]

        def geometry(bars):
            return audit.decision_geometry(
                order,
                bars,
                [b.start for b in bars],
                [b.end for b in bars],
                bars,
                [b.end for b in bars],
                raw,
            )

        self.assertEqual(geometry(native), geometry(changed))
        self.assertEqual(
            geometry(native)["diagnostic_completed_native_TF_SMA14_TR"], "4"
        )

    def test_raw_origin_partition_detects_duplicate_or_missing_disposition(self):
        raw = [
            {
                "formation_id": key,
                "formation_at": 0,
                "discovered_at": 0,
                "expiry": 57600,
                "direction": "LONG",
                "branch": branch,
                "setup_tf": 60,
            }
            for key, branch in [("a", "SFP"), ("b", "STB")]
        ]
        data = {
            "raw_formations": raw,
            "diagnostics": [
                {
                    "formation_id": "a",
                    "reason": "REJECT_NON_SMOOTH_STRUCTURAL_APPROACH",
                    "decision_at": 3600,
                }
            ],
            "pending": [],
            "known_through": 3600,
            "reservation_audit": [
                {
                    "decision_at": 3600,
                    "proposals": [
                        {
                            "formation_id": "b",
                            "disposition": "EMITTED",
                            "audit_reason": "FROZEN_PRIORITY_SELECTED",
                        }
                    ],
                }
            ],
            "counts": {"WAIT_REFINEMENT_BOS_CONF": 17},
            "raw_native_formations": [],
        }
        orders = [
            {
                "branch": "STB",
                "formation_at": 0,
                "decision_at": 3600,
                "source_validated": False,
            }
        ]
        result = audit.admission("BTC-USDT-SWAP", data, orders)
        self.assertEqual(result["physical_buckets"], 1)
        self.assertIsNone(
            result["wait_exposure_bounds"]["WAIT_REFINEMENT_BOS_CONF"][
                "exact_unique_origin_count"
            ]
        )
        self.assertEqual(
            result["wait_exposure_bounds"]["WAIT_REFINEMENT_BOS_CONF"][
                "unique_origin_lower_bound"
            ],
            1,
        )
        data["diagnostics"].append(
            {"formation_id": "b", "reason": "EXPIRED_PENDING", "decision_at": 3600}
        )
        with self.assertRaisesRegex(AssertionError, "EXACT_ORIGIN_PARTITION"):
            audit.admission("BTC-USDT-SWAP", data, orders)

    def test_partial_disagreement_is_never_in_closed_summary(self):
        self.assertEqual(
            audit.closed_summary([{"metrics_eligible": False}], "base")["CLOSED"], 0
        )


if __name__ == "__main__":
    unittest.main()
