"""Synthetic fee, book, immutable scoring and public-only capture QA."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from decimal import localcontext
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_exchange_selection_audit_v1 as audit
import exchange_selection_math as math
import exchange_selection_public_capture as public


def book(source="synthetic", at="2026-10-13T00:00:00Z"):
    return {
        "source_id": source,
        "time_utc": at,
        "bids": [["99", "1000"], ["98", "1000"]],
        "asks": [["101", "1000"], ["102", "1000"]],
    }


class FeeTests(unittest.TestCase):
    def test_round_trip_rates_and_every_notional(self):
        x = math.fee_scenarios("0.0002", "0.0006")["scenarios"]
        self.assertEqual(x["TAKER_TAKER"]["percent"], "0.12")
        self.assertEqual(x["TAKER_TAKER"]["bps"], "12")
        self.assertEqual(
            x["TAKER_TAKER"]["usd"],
            {"1000": "1.2", "5000": "6", "10000": "12", "25000": "30", "50000": "60"},
        )
        self.assertEqual(x["MAKER_TAKER"]["bps"], "8")
        self.assertEqual(x["MAKER_MAKER"]["bps"], "4")
        self.assertEqual(x["BLENDED_50_50_TURNOVER"], x["MAKER_TAKER"])

    def test_negative_maker_rebate_sign_preserved(self):
        x = math.fee_scenarios("-0.0001", "0.0005")["scenarios"]
        self.assertEqual(x["MAKER_MAKER"]["bps"], "-2")
        self.assertEqual(x["MAKER_TAKER"]["bps"], "4")

    def test_missing_api_fee_never_falls_back_to_app_promotion(self):
        # Actual MEXC evidence contains promotional/app/product values but the
        # selected primary API maker/taker are null; no fallback path exists.
        facts = audit.read(audit.DEST / "evidence/mexc/FACTS.json")
        self.assertIsNone(facts["fees"]["maker_rate"])
        self.assertFalse(
            math.fee_scenarios(
                facts["fees"]["maker_rate"], facts["fees"]["taker_rate"]
            )["available"]
        )
        self.assertFalse(math.fee_scenarios("0", None)["available"])

    def test_funding_excluded_and_no_maker_fill_guarantee(self):
        x = math.fee_scenarios("0.0002", "0.0006")
        self.assertFalse(x["funding_included"])
        self.assertFalse(x["maker_fill_guaranteed"])

    def test_wrong_fee_units_or_negative_taker_rejected(self):
        for m, t in (("0", "-0.01"), ("2", "0.1"), ("0", "2")):
            with self.assertRaises(ValueError):
                math.fee_scenarios(m, t)

    def test_exact_types_nonfinite_and_precision_independence(self):
        for value in (True, 0.1, "NaN", "Infinity"):
            with self.assertRaises(ValueError):
                math.exact(value)
        with localcontext() as ctx:
            ctx.prec = 3
            self.assertEqual(
                math.exact("1000000000000000000000.001"),
                Fraction(1000000000000000000000001, 1000),
            )
            self.assertEqual(math.display(Fraction(1, 3)), "0.333333333333333333")
            self.assertEqual(
                math.fee_scenarios("0.0002", "0.0006")["scenarios"]["TAKER_TAKER"][
                    "usd"
                ]["50000"],
                "60",
            )


class BookTests(unittest.TestCase):
    def test_lot_valid_quantity_model_separate_from_score(self):
        b = book()
        x = math.lot_grid_impact(b, "1000", "BUY", "0.3")
        self.assertTrue(x["available"])
        self.assertEqual(x["target_base_quantity"], "9.9")
        self.assertEqual(x["actual_reference_notional"], "990")
        self.assertEqual(x["actual_quote_notional"], "999.9")
        self.assertFalse(x["scoring_model_replaced"])
        self.assertFalse(math.lot_grid_impact(b, "1000", "BUY", None)["available"])

    def test_lot_model_insufficient_whole_lot_depth(self):
        b = book()
        b["asks"] = [["101", "0.01"]]
        self.assertFalse(math.lot_grid_impact(b, "1000", "BUY", "0.3")["available"])
        self.assertFalse(math.lot_grid_impact(book(), "1", "BUY", "1")["available"])
        with self.assertRaises(ValueError):
            math.lot_grid_impact(book(), "1000", "BUY", "0")

    def test_mid_spread_depth_and_single_level_vwap(self):
        x = math.analyze_book(book())
        self.assertEqual(x["spread_bps"], "200")
        self.assertEqual(x["notionals"]["1000"]["BUY"]["vwap"], "101")
        self.assertEqual(x["notionals"]["1000"]["SELL"]["vwap"], "99")
        self.assertEqual(x["notionals"]["1000"]["BUY"]["impact_bps"], "100")

    def test_multilevel_quote_budget_exact_reciprocal_vwap(self):
        x = math.market_impact([["101", "1"], ["102", "1"]], "203", "BUY", "100")
        self.assertTrue(x["filled"])
        self.assertEqual(x["vwap"], "101.5")
        self.assertEqual(x["impact_bps"], "150")

    def test_insufficient_depth_never_extrapolated(self):
        x = math.market_impact([["101", "1"]], "102", "BUY", "100")
        self.assertFalse(x["filled"])
        self.assertEqual(x["uncovered_quote"], "1")
        self.assertIsNone(x["vwap"])

    def test_sort_bid_descending_ask_ascending(self):
        self.assertEqual(math.levels([["1", "1"], ["99", "1"]], "SELL")[0][0], 99)
        self.assertEqual(math.levels([["102", "1"], ["101", "1"]], "BUY")[0][0], 101)

    def test_zero_visible_depth_omitted_without_invention(self):
        self.assertEqual(
            math.levels([["100", "0"], ["99", "1"]], "SELL"),
            [(Fraction(99), Fraction(1))],
        )
        with self.assertRaises(ValueError):
            math.levels([["100", "0"]], "SELL")

    def test_invalid_side_negative_duplicate_and_crossed(self):
        for rows, side in (
            ([["1", "1"]], "LONG"),
            ([["1", "-1"]], "BUY"),
            ([["0", "1"]], "BUY"),
            ([["1", "1"], ["1", "2"]], "BUY"),
        ):
            with self.assertRaises(ValueError):
                math.levels(rows, side)
        bad = book()
        bad["bids"][0][0] = "102"
        with self.assertRaises(ValueError):
            math.analyze_book(bad)

    def test_median_worst_and_two_symbols_five_sizes(self):
        books = {
            s: [book(s + "_1"), book(s + "_2", "2026-10-13T01:00:00Z")]
            for s in ("BTC", "ETH")
        }
        x = math.liquidity_summary(books, units_confirmed=True)
        self.assertTrue(x["scoring_usable"])
        self.assertEqual(len(x["cells"]), 20)
        self.assertEqual(x["mean_impact_bps"], "100")
        self.assertEqual(x["spread_aggregation"]["BTC"]["median_bps"], "200")
        self.assertEqual(math.median(["1", "3"]), 2)

    def test_missing_units_fewer_samples_and_cached_duplicate_zero_score(self):
        books = {
            s: [book(s + "_1"), book(s + "_2", "2026-10-13T01:00:00Z")]
            for s in ("BTC", "ETH")
        }
        self.assertFalse(
            math.liquidity_summary(books, units_confirmed=False)["scoring_usable"]
        )
        self.assertFalse(
            math.liquidity_summary(books, units_confirmed=True, remove_source="BTC_1")[
                "scoring_usable"
            ]
        )
        books["BTC"][1]["time_utc"] = books["BTC"][0]["time_utc"]
        self.assertFalse(
            math.liquidity_summary(books, units_confirmed=True)["scoring_usable"]
        )


class ScoringTests(unittest.TestCase):
    def test_preregistered_weights_hash_and_all_twelve_venues(self):
        p = audit.read(audit.DEST / "SCORING_PREREGISTRATION.json")
        self.assertEqual(
            audit.digest(audit.DEST / "SCORING_PREREGISTRATION.json"), audit.PREREG_SHA
        )
        self.assertEqual(sum(p["research_weights"].values()), 100)
        self.assertEqual(sum(p["execution_weights"].values()), 100)
        self.assertEqual(len(p["candidate_venues"]), 12)

    def test_missing_zero_literal_flags_and_source_required(self):
        flags = [{"confirmed": None, "source_ids": []} for _ in range(5)]
        self.assertEqual(math.evidence_points(flags), 0)
        flags[0] = {"confirmed": True, "source_ids": ["synthetic"]}
        self.assertEqual(math.evidence_points(flags), 1)
        for invalid in (
            {"confirmed": True, "source_ids": []},
            {"confirmed": "true", "source_ids": ["x"]},
        ):
            with self.assertRaises(ValueError):
                math.evidence_points([invalid, *flags[1:]])
        with self.assertRaises(ValueError):
            math.evidence_points(flags[:4])

    def test_band_boundaries_exact_and_missing(self):
        self.assertEqual(math.band_score("10", ["10", "15"], [3, 2]), 3)
        self.assertEqual(math.band_score("10.000000000000001", ["10", "15"], [3, 2]), 2)
        self.assertEqual(math.band_score(None, ["10"], [3]), 0)
        self.assertEqual(math.band_score("11", ["10"], [3]), 0)

    def test_frozen_proportional_sensitivity_total_and_no_other_shifts(self):
        w = {
            "cost": 35,
            "liquidity": 25,
            "orders": 15,
            "funding": 10,
            "safety": 10,
            "data": 5,
        }
        for shift in (-5, 5):
            changed = math.shifted_weights(w, shift)
            self.assertEqual(sum(changed.values()), 100)
            self.assertEqual(changed["cost"], 35 + shift)
            self.assertEqual(changed["liquidity"] / changed["orders"], Fraction(25, 15))
        with self.assertRaises(ValueError):
            math.shifted_weights(w, 1)

    def test_score_missing_weight_and_hard_gate_override(self):
        self.assertEqual(math.weighted_score({"a": 5, "b": 0}, {"a": 35, "b": 65}), 35)
        with self.assertRaises(ValueError):
            math.weighted_score({"a": 5}, {"a": 99})
        r = [
            {"venue": "bad", "eligible": False, "score_rational": ["100", "1"]},
            {"venue": "valid", "eligible": True, "score_rational": ["1", "1"]},
        ]
        e = [{"venue": "other", "eligible": True, "score_rational": ["2", "1"]}]
        selected = audit.selection(r, e)
        self.assertEqual(selected["PRIMARY_RESEARCH_VALIDATION_VENUE"], "valid")
        self.assertFalse(selected["trade_entry_allowed"])
        self.assertTrue(audit.selection([], e)["decision"].endswith("STOP"))

    def test_ties_lexicographic_not_evidence_superiority(self):
        r = [
            {"venue": v, "score_rational": ["82", "1"], "eligible": True}
            for v in ("okx", "bitget")
        ]
        self.assertEqual(math.rank(r)[0]["venue"], "bitget")

    def test_timestamp_units_nanoseconds_milliseconds_seconds_and_missing(self):
        for value, unit in (
            ("1000500000000", "nanoseconds"),
            ("1000500", "milliseconds"),
            ("1000.5", "seconds"),
        ):
            self.assertEqual(
                audit.time_from_book(value, "unused", unit),
                "1970-01-01T00:16:40.500000+00:00",
            )
        self.assertEqual(audit.time_from_book(None, "fallback", "seconds"), "fallback")
        with self.assertRaises(ValueError):
            audit.time_from_book(1, "", "unknown")


class PublicBoundaryTests(unittest.TestCase):
    def test_ci_summary_cannot_read_outside_raw_evidence(self):
        summary = {
            "probes": [
                {
                    "source_kind": "book_BTC",
                    "http_status": 200,
                    "truncated": False,
                    "venue": "okx",
                    "raw_file": "../../../../outside-secret",
                }
            ]
        }
        with (
            patch.object(audit, "read", return_value=summary),
            self.assertRaisesRegex(ValueError, "CI_SOURCE_OUTSIDE_PUBLIC_EVIDENCE"),
        ):
            audit.ci_books({"okx": {}})

    def test_confirmed_fee_cannot_hide_missing_rates(self):
        flags = [{"confirmed": False, "source_ids": []} for _ in range(5)]
        a = {
            "research": {"history": flags},
            "execution": {"orders": flags},
            "fee_base_confirmed": True,
        }
        with self.assertRaisesRegex(ValueError, "CONFIRMED_FEE_REQUIRES_ACTUAL_RATES"):
            audit.row_scores(
                "synthetic", a, {"maker_rate": None, "taker_rate": None}, {}, {}
            )

    def test_every_predefined_probe_is_public(self):
        for probes in public.PROBES.values():
            for p in probes:
                public.validate(
                    p[1],
                    "POST" if len(p) == 3 else "GET",
                    p[2] if len(p) == 3 else None,
                )

    def test_private_order_routes_credentials_and_wallet_actions_rejected(self):
        for url, method, data in (
            ("https://api.bybit.com/v5/order/create", "GET", None),
            (
                "https://api.hyperliquid.xyz/info",
                "POST",
                {"type": "userFees", "user": "0x0"},
            ),
            ("https://api.hyperliquid.xyz/info", "POST", {"type": "withdraw3"}),
            (next(iter(public.ALLOWED_URLS)), "DELETE", None),
            ("https://api.hyperliquid.xyz/info?api_key=", "GET", None),
        ):
            with self.assertRaises(ValueError):
                public.validate(url, method, data)

    def test_denial_receipted_secret_headers_removed_and_no_redirect(self):
        url = public.PROBES["bybit"][0][1]
        error = HTTPError(
            url,
            403,
            "blocked",
            {"Content-Type": "text/plain", "Set-Cookie": "synthetic secret"},
            io.BytesIO(b"synthetic denial"),
        )
        with tempfile.TemporaryDirectory() as d:
            with patch.object(public, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                r = public.capture(url, d)
            self.assertEqual(r["http_status"], 403)
            self.assertEqual(r["headers"], {"content-type": "text/plain"})
            self.assertEqual(Path(d, r["raw_file"]).read_bytes(), b"synthetic denial")
        self.assertIsNone(
            public.NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://private.example"
            )
        )

    def test_transport_failure_and_bad_environment(self):
        url = public.PROBES["okx"][0][1]
        with tempfile.TemporaryDirectory() as d:
            with patch.object(public, "build_opener") as opener:
                opener.return_value.open.side_effect = URLError("synthetic failure")
                r = public.capture(url, d)
            self.assertIsNone(r["http_status"])
            self.assertEqual(r["raw_bytes"], 0)
            with self.assertRaises(ValueError):
                public.capture(url, d, environment="VPN")

    def test_existing_freeze_and_missing_external_pin_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "freeze_manifest.json").write_text("synthetic fixture")
            with patch.object(audit, "DEST", Path(d)):
                with self.assertRaises(ValueError):
                    audit.prepare(Path(d))
                with self.assertRaises(ValueError):
                    audit.seal()
                with self.assertRaises(ValueError):
                    audit.verify_existing(None)


if __name__ == "__main__":
    unittest.main()
