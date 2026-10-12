"""Metadata proof schema, exact arithmetic and actual frozen-candle QA."""

from __future__ import annotations

import copy
import io
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_machine_strategy_v3_market_metadata_recovery as recovery
import collect_machine_strategy_v3_metadata_evidence as collector


def proof_fixture(symbol="BTCUSDT", **overrides):
    # Schema fixture only; never used as historical source evidence/epoch input.
    return {
        "symbol": symbol,
        "contract_type": recovery.CONTRACT,
        "valid_from": recovery.WARMUP,
        "valid_to": recovery.END,
        "tick_size": "0.1",
        "known_at": recovery.WARMUP,
        "effective_at": recovery.WARMUP,
        "verification_status": "VERIFIED",
        "source_bytes_verified": True,
        "effective_application_proven": True,
        "complete_interval_continuity_proven": True,
        "independent_provenance_review_pass": True,
        "evidence_ids": ["SYNTHETIC_SCHEMA_FIXTURE_NOT_REAL_PROOF"],
        **overrides,
    }


class ExactGridTests(unittest.TestCase):
    def test_integer_ratio_divisibility(self):
        self.assertTrue(recovery.on_grid("1563.35", "0.05"))
        self.assertFalse(recovery.on_grid("1563.36", "0.05"))
        self.assertTrue(recovery.on_grid("21931.3", "0.1"))
        self.assertFalse(recovery.on_grid("21931.3", "0.5"))

    def test_decimal_context_cannot_round_away_a_violation(self):
        with localcontext() as ctx:
            ctx.prec = 4
            self.assertFalse(
                recovery.on_grid("1000000000000000000000000000.01", "0.05")
            )
            self.assertTrue(recovery.on_grid("1000000000000000000000000000.05", "0.05"))

    def test_nonfinite_nonpositive_and_float_rejected(self):
        for value, tick in (
            ("NaN", "0.1"),
            ("Infinity", "0.1"),
            ("0", "0.1"),
            ("1", "0"),
            ("1", "-0.1"),
            (0.1, "0.1"),
            ("0.1", 0.1),
            (True, "1"),
        ):
            with self.subTest(value=value, tick=tick), self.assertRaises(ValueError):
                recovery.on_grid(value, tick)

    def test_context_free_integer_prices_supported(self):
        self.assertTrue(recovery.on_grid(10, 2))
        self.assertTrue(recovery.on_grid(Decimal("10.20"), Decimal("0.05")))

    def test_bar_spanning_epoch_change_not_assigned_single_tick(self):
        row = {
            "start": 0,
            "end": 900,
            "open": "10",
            "high": "11",
            "low": "9",
            "close": "10",
        }
        with self.assertRaisesRegex(ValueError, "BAR_SPANS_EPOCH"):
            recovery.grid_check([row], "1", 0, 450)

    def test_grid_check_counts_cells_and_never_mutates_prices(self):
        row = {
            "start": 0,
            "end": 900,
            "open": "10.1",
            "high": "11.2",
            "low": "9.0",
            "close": "10.0",
        }
        before = copy.deepcopy(row)
        result = recovery.grid_check([row], "0.5", 0, 900)
        self.assertEqual((result["off_grid_bars"], result["off_grid_cells"]), (1, 2))
        self.assertEqual(row, before)


class EpochCoverageTests(unittest.TestCase):
    def test_full_unknown_has_zero_separate_warmup_and_development_coverage(self):
        epochs = [recovery.unknown_epoch("BTCUSDT")]
        for begin, end in (
            (recovery.WARMUP, recovery.START),
            (recovery.START, recovery.END),
        ):
            result = recovery.coverage(epochs, "BTCUSDT", begin, end)
            self.assertEqual(result["verified_seconds"], 0)
            self.assertFalse(result["complete_verified"])
            self.assertEqual(
                result["unresolved_intervals"], [{"valid_from": begin, "valid_to": end}]
            )

    def test_empty_map_does_not_imply_coverage(self):
        result = recovery.coverage([], "ETHUSDT", recovery.WARMUP, recovery.END)
        self.assertEqual(result["verified_seconds"], 0)
        self.assertEqual(len(result["unresolved_intervals"]), 1)

    def test_adjacent_unknown_intervals_merge_to_minimal_gap(self):
        a = recovery.unknown_epoch("BTCUSDT")
        b = {**a, "valid_from": recovery.START}
        a["valid_to"] = recovery.START
        result = recovery.coverage([b, a], "BTCUSDT", recovery.WARMUP, recovery.END)
        self.assertEqual(
            result["unresolved_intervals"],
            [{"valid_from": recovery.WARMUP, "valid_to": recovery.END}],
        )

    def test_verified_schema_fixture_counts_exact_duration(self):
        result = recovery.coverage(
            [proof_fixture()], "BTCUSDT", recovery.WARMUP, recovery.END
        )
        self.assertEqual(result["verified_seconds"], recovery.END - recovery.WARMUP)
        self.assertTrue(result["complete_verified"])

    def test_partial_coverage_cannot_authorize_full_scope(self):
        p = proof_fixture(
            valid_from=recovery.START,
            known_at=recovery.START,
            effective_at=recovery.START,
        )
        result = recovery.coverage([p], "BTCUSDT", recovery.WARMUP, recovery.END)
        self.assertFalse(result["complete_verified"])
        self.assertEqual(
            result["unresolved_intervals"],
            [{"valid_from": recovery.WARMUP, "valid_to": recovery.START}],
        )

    def test_overlap_rejected_not_double_counted(self):
        with self.assertRaisesRegex(ValueError, "OVERLAPPING"):
            recovery.validate_epochs([proof_fixture(), proof_fixture()], "BTCUSDT")

    def test_wrong_symbol_or_contract_rejected(self):
        for row in (
            proof_fixture(symbol="ETHUSDT"),
            proof_fixture(contract_type="SPOT"),
        ):
            with self.assertRaisesRegex(ValueError, "WRONG_SYMBOL_OR_CONTRACT"):
                recovery.validate_epochs([row], "BTCUSDT")

    def test_late_known_or_effective_timestamp_rejected(self):
        for field in ("known_at", "effective_at"):
            with self.assertRaisesRegex(ValueError, "RETROACTIVE"):
                recovery.validate_epochs(
                    [proof_fixture(**{field: recovery.WARMUP + 1})], "BTCUSDT"
                )

    def test_affirmative_proof_flags_must_be_literal_true(self):
        for field in (
            "source_bytes_verified",
            "effective_application_proven",
            "complete_interval_continuity_proven",
            "independent_provenance_review_pass",
        ):
            for value in (False, "true", 1, None):
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaisesRegex(ValueError, "INSUFFICIENT"),
                ):
                    recovery.validate_epochs(
                        [proof_fixture(**{field: value})], "BTCUSDT"
                    )

    def test_missing_evidence_and_invalid_tick_rejected(self):
        for overrides in (
            {"evidence_ids": []},
            {"tick_size": "0"},
            {"tick_size": "NaN"},
        ):
            with self.assertRaises(ValueError):
                recovery.validate_epochs([proof_fixture(**overrides)], "BTCUSDT")

    def test_float_bool_times_and_invalid_coverage_rejected(self):
        for value in (True, float(recovery.WARMUP), str(recovery.WARMUP)):
            with self.assertRaises(ValueError):
                recovery.validate_epochs([proof_fixture(valid_from=value)], "BTCUSDT")
        with self.assertRaisesRegex(ValueError, "INVALID_COVERAGE"):
            recovery.coverage([], "BTCUSDT", recovery.START, recovery.START)


class ProvenanceTests(unittest.TestCase):
    def test_http200_is_hashed_capture_and_never_epoch_proof(self):
        class Response:
            status = 200
            headers: ClassVar[dict[str, str]] = {
                "Date": "Mon, 12 Oct 2026 12:00:00 GMT",
                "Content-Type": "application/json",
                "Set-Cookie": "synthetic forbidden header",
            }

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, size):
                return b'{"retCode":10001,"retMsg":"Illegal category","result":{"list":[]}}'

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(collector, "ROOT", root),
                patch.object(collector, "DEST", root / "evidence"),
                patch.object(collector, "urlopen", return_value=Response()),
            ):
                receipt = collector.fetch(
                    (
                        "fixture",
                        "ARCHIVED_API",
                        "https://api.bybit.com/v5/market/instruments-info",
                    )
                )
            self.assertEqual(receipt["http_status"], 200)
            self.assertFalse(receipt["result_is_historical_epoch_proof"])
            self.assertNotIn("Set-Cookie", receipt["headers"])
            self.assertEqual(
                receipt["body_sha256"], recovery.digest(root / receipt["body_path"])
            )
            self.assertFalse(receipt["private_API"])

    def test_http_error_body_retained_without_negative_continuity_inference(self):
        url = "https://api.bybit.com/v5/market/instruments-info"
        error = HTTPError(
            url, 403, "Forbidden", {}, io.BytesIO(b"synthetic public denial")
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(collector, "ROOT", root),
                patch.object(collector, "DEST", root / "evidence"),
                patch.object(collector, "urlopen", side_effect=error),
            ):
                receipt = collector.fetch(("fixture", "CURRENT_CONTEXT_ONLY", url))
            self.assertEqual(receipt["http_status"], 403)
            self.assertEqual(receipt["bytes"], len(b"synthetic public denial"))
            self.assertFalse(receipt["result_is_historical_epoch_proof"])

    def test_network_failure_recorded_and_query_matrix_has_all_source_classes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(collector, "ROOT", root),
                patch.object(collector, "DEST", root / "evidence"),
                patch.object(
                    collector,
                    "urlopen",
                    side_effect=URLError("synthetic network failure"),
                ),
            ):
                receipt = collector.fetch(
                    (
                        "fixture",
                        "CURRENT_CONTEXT_ONLY",
                        "https://api.bybit.com/v5/market/instruments-info",
                    )
                )
            self.assertIsNone(receipt["http_status"])
            self.assertEqual(receipt["error_class"], "URLError")
            self.assertEqual(receipt["bytes"], 0)
        classes = {entry[1] for entry in collector.searches()}
        self.assertTrue(
            {
                "ARCHIVE_INDEX",
                "ARCHIVE_TEXT_INDEX",
                "OFFICIAL_DOC_GIT_CONTEXT_ONLY",
                "THIRD_PARTY_INSTRUMENT_METADATA",
            }
            <= classes
        )

    def test_current_metadata_phase_blocks_public_kernel_accounting_before_history(
        self,
    ):
        import machine_strategy_v3_guarded_runner as runner

        task = (recovery.ROOT / "agent_control/NEXT_TASK.md").read_text()
        self.assertIn(
            "Historical Market-Metadata Recovery Freeze", task.splitlines()[0]
        )
        before = runner.COUNTERS["historical_outcome_evaluations"]
        with (
            patch.object(
                runner, "load_primary", side_effect=AssertionError("History loaded")
            ),
            patch.object(
                runner,
                "observe_m15_bar",
                side_effect=AssertionError("Historical exit evaluated"),
            ),
            patch.object(
                runner,
                "cash_stop_identity",
                side_effect=AssertionError("Historical accounting evaluated"),
            ),
        ):
            for call in (
                lambda: runner.run_historical("BTCUSDT", []),
                lambda: runner._drive_order({}, [], []),
                lambda: runner._closed_record({}),
            ):
                with self.assertRaises(runner.HistoricalOutcomeBlocked):
                    call()
            forged = runner._Authorization(
                runner._MARKER,
                recovery.ROOT
                / "docs/machine_strategy_v3_implementation_readiness/freeze_manifest.json",
                recovery.PARENTS["docs/machine_strategy_v3_implementation_readiness"],
                recovery.ROOT / "nonexistent_metadata_financial_auth.json",
                "a" * 64,
            )
            # Frozen guard errors on the missing fake auth outside its old phase.
            # It still fails before data/outcomes; this error handling is disclosed.
            with self.assertRaises(FileNotFoundError):
                runner.run_historical("BTCUSDT", [], forged)
        self.assertEqual(before, runner.COUNTERS["historical_outcome_evaluations"])

    def test_current_metadata_phase_cannot_promote_frozen_stop_manifest(self):
        import machine_strategy_v3_guarded_runner as runner

        task = (recovery.ROOT / "agent_control/NEXT_TASK.md").read_text()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic_forged_auth.json"
            recovery.save(
                path,
                {
                    "authorized_by_user": True,
                    "phase": "FIRST_V3_DEVELOPMENT_FINANCIAL_BACKTEST",
                    "task_sha256": sha256(task.encode()).hexdigest(),
                    "implementation_manifest": "docs/machine_strategy_v3_implementation_readiness/freeze_manifest.json",
                    "implementation_manifest_sha256": recovery.PARENTS[
                        "docs/machine_strategy_v3_implementation_readiness"
                    ],
                },
            )
            with self.assertRaisesRegex(
                runner.HistoricalOutcomeBlocked, "IMPLEMENTATION_NOT_FINANCIALLY_READY"
            ):
                runner.authorize_later(path)

    def test_timezone_and_subsecond_chronology_remain_exact(self):
        self.assertEqual(
            recovery.iso_seconds("2023-01-01T08:00:00+08:00"), Decimal(recovery.START)
        )
        self.assertEqual(
            recovery.iso_seconds("2023-01-01T00:00:00.001Z"),
            Decimal(recovery.START) + Decimal("0.001"),
        )
        with self.assertRaisesRegex(ValueError, "UNPROVEN_TIMEZONE"):
            recovery.iso_seconds("2023-01-01T00:00:00")

    def test_receipt_body_hash_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            evidence = dest / "evidence"
            evidence.mkdir()
            (evidence / "body.body").write_bytes(b"immutable proof bytes")
            recovery.save(
                evidence / "body.receipt.json",
                {"body_file": "body.body", "body_sha256": "a" * 64},
            )
            with (
                patch.object(recovery, "DEST", dest),
                self.assertRaisesRegex(ValueError, "HASH_MISMATCH"),
            ):
                recovery.receipt_inventory()

    def test_cookie_and_auth_headers_not_deliverable(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            (dest / "evidence").mkdir()
            recovery.save(
                dest / "evidence/test.receipt.json",
                {"response_headers": {"Set-Cookie": "synthetic forbidden header"}},
            )
            with (
                patch.object(recovery, "DEST", dest),
                self.assertRaisesRegex(ValueError, "SENSITIVE_RESPONSE_HEADERS"),
            ):
                recovery.receipt_inventory()

    def test_collector_rejects_private_or_unapproved_destinations_before_request(self):
        for url in (
            "https://api.bybit.com/v5/order/realtime",
            "http://api.bybit.com/v5/market/instruments-info",
            "https://unapproved.invalid/data",
        ):
            with (
                patch.object(
                    collector, "urlopen", side_effect=AssertionError("Request issued")
                ),
                self.assertRaises(ValueError),
            ):
                collector.fetch(("fixture", "fixture", url))

    def test_static_outcome_isolation(self):
        result = recovery.isolation()
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["historical_v3_outcomes_read_or_generated"])

    def test_actual_primary_hash_scope_and_conditional_notice_conflicts(self):
        for symbol, change, tick, expected_bars, expected_cells in (
            ("BTCUSDT", 1676016000, "0.5", 1, 1),
            ("ETHUSDT", 1673942400, "0.05", 4, 6),
        ):
            rows, _ = recovery.primary(symbol)
            self.assertEqual(
                (rows[0]["start"], rows[-1]["end"]), (recovery.WARMUP, recovery.END)
            )
            self.assertEqual(len(rows), 137758)
            check = recovery.grid_check(rows, tick, recovery.START, change)
            self.assertEqual(
                (check["off_grid_bars"], check["off_grid_cells"]),
                (expected_bars, expected_cells),
            )
            self.assertEqual(
                recovery.coverage(
                    [recovery.unknown_epoch(symbol)],
                    symbol,
                    recovery.WARMUP,
                    recovery.END,
                )["verified_seconds"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
