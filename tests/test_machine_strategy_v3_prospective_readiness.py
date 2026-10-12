"""Phase-independent synthetic integrity/control probes; no candidate execution."""

from __future__ import annotations

import copy
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_machine_strategy_v3_prospective_readiness as build
import collect_machine_strategy_v3_prospective_public as capture
import machine_strategy_v3_prospective_integrity as integrity


def payload(**overrides):
    item = {
        "symbol": "BTCUSDT",
        "contractType": "LinearPerpetual",
        "quoteCoin": "USDT",
        "settleCoin": "USDT",
        "status": "Trading",
        "priceFilter": {"tickSize": "0.10", "minPrice": "0.10", "maxPrice": "1000000"},
        **overrides,
    }
    return json.dumps(
        {"retCode": 0, "result": {"category": "linear", "list": [item]}}
    ).encode()


class IntegrityTests(unittest.TestCase):
    def test_completed_cutoff_cannot_admit_future_claimed_closed_bar(self):
        self.assertEqual(integrity.completed_cutoff(901), 900)
        self.assertEqual(integrity.completed_cutoff(900), 900)
        with self.assertRaisesRegex(integrity.IntegrityDenied, "FUTURE_OR_UNCOMPLETED"):
            integrity.worker(
                "BTCUSDT",
                0,
                999999999999,
                integrity.DEST / "evidence/integrity_access/not-created.json",
            )

    def test_strict_next_midnight_including_exact_midnight(self):
        self.assertEqual(integrity.earliest_boundary(0, 86400), 172800)
        self.assertEqual(integrity.earliest_boundary(86401, 86400), 172800)

    def test_registration_missing_is_not_invented(self):
        with self.assertRaises(ValueError):
            integrity.earliest_boundary(0, None)
        for t in (True, 1.1, "1"):
            with self.assertRaises(ValueError):
                integrity.earliest_boundary(0, t)

    def test_timestamp_offset_subsecond_and_naive(self):
        self.assertEqual(
            integrity.timestamp("1970-01-01T08:00:00.001+08:00"), Decimal(".001")
        )
        with self.assertRaises(ValueError):
            integrity.timestamp("2026-10-13T00:00:00")

    def test_missing_runs_exact_m15_and_tail(self):
        self.assertEqual(
            integrity.missing_runs({0, 1800}, 0, 3600),
            [
                {"from": 900, "to_exclusive": 1800, "bars": 1},
                {"from": 2700, "to_exclusive": 3600, "bars": 1},
            ],
        )
        for start, end in ((1, 900), (900, 0), (0, True)):
            with self.assertRaises(ValueError):
                integrity.missing_runs(set(), start, end)

    def test_exact_overlap_and_conflict(self):
        base = tuple(Decimal(x) for x in ("10", "12", "8", "11", "2", "20"))
        equal = tuple(Decimal(str(x) + "0") if x == Decimal(2) else x for x in base)
        same = integrity.prefix_summary([{0: base}, {0: base}], 0, 900)
        self.assertEqual(same["overlap_bars"], 1)
        self.assertTrue(same["complete"])
        changed = integrity.prefix_summary([{0: base}, {0: equal}], 0, 900)
        self.assertEqual(changed["conflicts"][0]["fields"], ["volume_base"])
        self.assertFalse(changed["complete"])

    def test_future_mutation_and_prefix_hash_is_exact(self):
        row = tuple(Decimal("100000000000000000000000.01") for _ in integrity.FIELDS)
        a = integrity.prefix_summary([{0: row}], 0, 900)
        with localcontext() as ctx:
            ctx.prec = 4
            b = integrity.prefix_summary(
                [{0: row, 900: tuple(Decimal(8) for _ in row)}], 0, 900
            )
        self.assertEqual(a, b)

    def test_native_csv_identity_duplicate_ohlcv_closed(self):
        header = [
            "exchange",
            "symbol",
            "interval",
            "is_closed",
            "open_time_ms",
            *integrity.FIELDS,
        ]
        valid = ["BYBIT", "BTCUSDT", "15", "1", "0", "10", "12", "8", "11", "2", "20"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"

            def write(rows):
                with path.open("w", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(header)
                    writer.writerows(rows)

            write([valid])
            self.assertEqual(len(integrity.read_m15(path, "BTCUSDT", 0, 900)), 1)
            for index, value in (
                (0, "BINANCE"),
                (1, "ETHUSDT"),
                (2, "5"),
                (3, "0"),
                (4, "1"),
                (6, "9"),
                (9, "-1"),
                (5, "NaN"),
            ):
                changed = valid.copy()
                changed[index] = value
                write([changed])
                with self.assertRaises(ValueError):
                    integrity.read_m15(path, "BTCUSDT", 0, 900)
            write([valid, valid])
            with self.assertRaisesRegex(ValueError, "DUPLICATE"):
                integrity.read_m15(path, "BTCUSDT", 0, 900)

    def test_native_csv_ignores_unclosed_future_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            path.write_text(
                "exchange,symbol,interval,is_closed,open_time_ms,open,high,low,close,volume_base,turnover_quote\nBYBIT,BTCUSDT,15,1,0,10,12,8,11,2,20\nBYBIT,BTCUSDT,15,0,900000,NaN,NaN,NaN,NaN,NaN,NaN\n"
            )
            self.assertEqual(len(integrity.read_m15(path, "BTCUSDT", 0, 900)), 1)

    def test_official_metadata_success_is_point_only(self):
        selected = integrity.selected_instrument(payload(), 200, "BTCUSDT")
        self.assertEqual(selected["tick_size"], "0.10")
        observed = integrity.prospective_observation(
            selected, "2026-10-12T00:00:00Z", "2026-10-12T00:00:00.5Z"
        )
        self.assertFalse(observed["continuous_interval_proven"])
        self.assertFalse(observed["epoch_opened"])

    def test_csv_future_numeric_mutation_preserves_completed_prefix(self):
        header = "exchange,symbol,interval,is_closed,open_time_ms,open,high,low,close,volume_base,turnover_quote\n"
        prefix = "BYBIT,BTCUSDT,15,1,0,10,12,8,11,2,20\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            path.write_text(header + prefix)
            original = integrity.read_m15(path, "BTCUSDT", 0, 900)
            path.write_text(
                header + prefix + "WRONG,OTHER,1,0,900001,NaN,NaN,NaN,NaN,NaN,NaN\n"
            )
            self.assertEqual(original, integrity.read_m15(path, "BTCUSDT", 0, 900))
            # Unidentifiable time cannot be classified future; global corruption
            # must fail closed rather than silently discard a potentially old row.
            path.write_text(
                header + prefix + "WRONG,OTHER,1,0,unknown,NaN,NaN,NaN,NaN,NaN,NaN\n"
            )
            with self.assertRaisesRegex(ValueError, "INVALID_NATIVE_M15_TIMESTAMP"):
                integrity.read_m15(path, "BTCUSDT", 0, 900)

    def test_metadata_failure_does_not_parse_error_as_instrument(self):
        selected = integrity.selected_instrument(b"not json", 403, "BTCUSDT")
        self.assertFalse(selected["verified"])
        self.assertFalse(
            integrity.prospective_observation(
                selected, "2026-10-12T00:00Z", "2026-10-12T00:01Z"
            )["epoch_opened"]
        )

    def test_metadata_wrong_contract_quote_settle_status_and_symbol(self):
        for field, value in (
            ("symbol", "BTCUSD"),
            ("contractType", "InversePerpetual"),
            ("quoteCoin", "USDC"),
            ("settleCoin", "USDC"),
            ("status", "PreLaunch"),
        ):
            with self.assertRaises(ValueError):
                integrity.selected_instrument(payload(**{field: value}), 200, "BTCUSDT")

    def test_metadata_duplicate_illegal_category_retcode_display_only(self):
        original = json.loads(payload())
        for alter in ("duplicate", "category", "retcode", "display"):
            p = copy.deepcopy(original)
            if alter == "duplicate":
                p["result"]["list"] *= 2
            elif alter == "category":
                p["result"]["category"] = "spot"
            elif alter == "retcode":
                p["retCode"] = 10001
            else:
                p["result"]["list"][0].pop("priceFilter")
                p["result"]["list"][0]["priceScale"] = "2"
            with self.assertRaises((ValueError, KeyError)):
                integrity.selected_instrument(json.dumps(p).encode(), 200, "BTCUSDT")

    def test_metadata_tick_float_nonpositive_nonfinite_rejected(self):
        for tick in (0.1, "0", "-1", "NaN", "Infinity"):
            with self.assertRaises(ValueError):
                integrity.selected_instrument(
                    payload(priceFilter={"tickSize": tick}), 200, "BTCUSDT"
                )

    def test_reversed_or_future_effective_cannot_open_observation(self):
        selected = integrity.selected_instrument(payload(), 200, "BTCUSDT")
        for a, b, effective in (
            ("2026-10-12T00:01Z", "2026-10-12T00:00Z", None),
            ("2026-10-12T00:00Z", "2026-10-12T00:01Z", "2026-10-13T00:00Z"),
        ):
            with self.assertRaises(ValueError):
                integrity.prospective_observation(
                    selected, a, b, effective_at=effective
                )

    def test_all_forged_authorizations_denied_before_any_file_access(self):
        with patch.object(
            Path, "read_bytes", side_effect=AssertionError("Auth/data read")
        ):
            for auth in (
                None,
                object(),
                "/nonexistent",
                {"authorized_by_user": True},
                {"phase": "FIRST_V3_DEVELOPMENT_FINANCIAL_BACKTEST"},
            ):
                with self.assertRaisesRegex(
                    integrity.HistoricalOutcomeDenied, "NO_FINANCIAL_CAPABILITY"
                ):
                    integrity.deny_historical_execution(auth)

    def test_worker_rejects_unknown_symbol_and_outside_log(self):
        with self.assertRaises(ValueError):
            integrity.worker("BTCUSD", 0, 900, "/tmp/log")
        with self.assertRaises(integrity.IntegrityDenied):
            integrity.worker("BTCUSDT", 0, 900, "/tmp/log")

    def test_worker_dynamic_denial_of_file_import_socket_and_process(self):
        # Fresh interpreter, no strategy module imported and no runner invoked.
        script = """import sys,json,socket,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import machine_strategy_v3_prospective_integrity as i
i.install_boundary([],[])
calls=[lambda:Path(sys.argv[1]+"/machine_strategy_v3_guarded_runner.py").read_bytes(),lambda:__import__("machine_strategy_v3_contracts"),lambda:socket.socket(),lambda:subprocess.run(["true"])]
denied=0
for call in calls:
 try: call()
 except i.IntegrityDenied: denied+=1
print(json.dumps({"denied":denied}))
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(integrity.ROOT / "scripts")],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["denied"], 4)

    def test_static_import_isolation(self):
        self.assertFalse(build.static_isolation()["strategy_or_state_modules_imported"])


class PublicCaptureTests(unittest.TestCase):
    def test_truncated_or_unasserted_complete_response_never_accepted(self):
        for flag in (True, None, "false", 0):
            self.assertFalse(
                build.selected_capture(
                    payload(),
                    {"response_truncated": flag, "http_status": 200},
                    "BTCUSDT",
                )["verified"]
            )
        self.assertTrue(
            build.selected_capture(
                payload(), {"response_truncated": False, "http_status": 200}, "BTCUSDT"
            )["verified"]
        )

    def test_successful_public_capture_and_oversize_failure_receipted(self):
        class Response:
            code = 200

            def __init__(self):
                self.headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, limit):
                return payload()[:limit]

        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT"
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(capture, "build_opener") as opener:
                opener.return_value.open.return_value = Response()
                success = capture.capture(url, directory)
                with patch.object(capture, "LIMIT", 5):
                    failure = capture.capture(url, directory)
            self.assertFalse(success["response_truncated"])
            self.assertTrue(failure["response_truncated"])
            self.assertEqual(failure["body_bytes"], 5)
            self.assertEqual(
                failure["error_class"], "BOUNDED_RESPONSE_TRUNCATED_UNVERIFIABLE"
            )
            self.assertNotEqual(success["id"], failure["id"])

    def test_url_exact_public_only(self):
        capture.validate_url(
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT"
        )
        capture.validate_url(
            "https://api.bybit.com/v5/market/kline?category=linear&symbol=ETHUSDT&interval=15&start=0&end=900000&limit=1000"
        )
        capture.validate_url("https://announcements.bybit.com/en/article/fixture/")

    def test_private_host_and_auth_query_rejected(self):
        urls = (
            "https://api.bybit.com/v5/order/create?category=linear&symbol=BTCUSDT",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT&api_key=x",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT&api_key=",
            "http://api.bybit.com/",
            "https://user:secret@api.bybit.com/",
            "https://api.bybit.com:443/",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT&symbol=ETHUSDT",
            "https://unknown.example/",
            "https://announcements.bybit.com/en/?private=x",
        )
        for url in urls:
            with self.assertRaises(ValueError):
                capture.validate_url(url)

    def test_native_bounded_requests_only(self):
        prefix = "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&"
        for tail in (
            "interval=5&start=0&end=1&limit=1000",
            "interval=15&start=0&end=1&limit=1001",
            "interval=15&start=-1&end=1&limit=2",
            "interval=15&start=2&end=1&limit=2",
        ):
            with self.assertRaises(ValueError):
                capture.validate_url(prefix + tail)

    def test_no_redirects(self):
        self.assertIsNone(
            capture.NoRedirect().redirect_request(
                None, None, 301, "redirect", {}, "https://private.example"
            )
        )

    def test_capture_failure_raw_bytes_and_header_exclusion(self):
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT"
        error = HTTPError(
            url,
            403,
            "denied",
            {
                "Content-Type": "text/plain",
                "Set-Cookie": "secret",
                "Authorization": "secret",
            },
            io.BytesIO(b"synthetic denial"),
        )
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(capture, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                receipt = capture.capture(url, directory)
            self.assertEqual(receipt["http_status"], 403)
            self.assertEqual(receipt["headers"], {"content-type": "text/plain"})
            self.assertEqual(
                Path(directory, receipt["body_file"]).read_bytes(), b"synthetic denial"
            )
            self.assertFalse(receipt["continuous_epoch_proof"])

    def test_capture_transport_error_is_receipted(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(capture, "build_opener") as opener:
                opener.return_value.open.side_effect = URLError("synthetic failure")
                receipt = capture.capture(
                    "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT",
                    directory,
                )
            self.assertIsNone(receipt["http_status"])
            self.assertEqual(receipt["body_bytes"], 0)
            self.assertEqual(receipt["error_class"], "URLError")

    def test_retained_receipt_integrity(self):
        paths = list((build.DEST / "evidence").rglob("*.receipt.json"))
        self.assertGreaterEqual(len(paths), 14)
        for path in paths:
            build.receipt_body(path)


class FreezeBoundaryTests(unittest.TestCase):
    def test_receipt_tamper_traversal_time_and_secret_headers_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            evidence = dest / "evidence"
            evidence.mkdir()
            body = evidence / "body"
            body.write_bytes(b"synthetic bytes")
            receipt = evidence / "capture.receipt.json"
            good = {
                "body_file": "body",
                "body_sha256": build.digest(body),
                "body_bytes": body.stat().st_size,
                "request_started_at_utc": "2026-10-12T00:00Z",
                "retrieved_at_utc": "2026-10-12T00:01Z",
            }
            with patch.object(build, "DEST", dest):
                build.save(receipt, good)
                build.receipt_body(receipt)
                for overrides in (
                    {"body_file": "../outside"},
                    {"body_sha256": "a" * 64},
                    {"body_bytes": 1},
                    {"retrieved_at_utc": "2026-10-11T23:59Z"},
                    {
                        "response_headers_allowlist": {
                            "Set-Cookie": "synthetic forbidden"
                        }
                    },
                ):
                    build.save(receipt, {**good, **overrides})
                    with self.assertRaises(ValueError):
                        build.receipt_body(receipt)

    def test_existing_freeze_cannot_be_prepared_or_sealed_again(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            (dest / "freeze_manifest.json").write_text("synthetic immutable fixture")
            with patch.object(build, "DEST", dest):
                with self.assertRaisesRegex(ValueError, "EXISTING_FREEZE"):
                    build.prepare(dest)
                with self.assertRaisesRegex(ValueError, "EXISTING_FREEZE"):
                    build.seal()

    def test_stop_seal_requires_honest_scope_and_independent_review(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            qa = {
                "targeted_status": "PASS",
                "full_current_phase_status": "FAIL",
                "scope": "OBJECTIVE_STOP_WITH_IMMUTABLE_TEST_CONFLICT",
            }
            with patch.object(build, "DEST", dest):
                build.save(
                    dest / "QA_RECEIPT.json",
                    {**qa, "full_current_phase_status": "PASS"},
                )
                with self.assertRaisesRegex(ValueError, "HONEST_STOP_QA_REQUIRED"):
                    build.seal()
                (dest / "reviews").mkdir()
                (dest / "reviews/final_independent_reviewer.md").write_text(
                    "No final seal yet"
                )
                build.save(dest / "QA_RECEIPT.json", qa)
                with self.assertRaisesRegex(
                    ValueError, "FINAL_INDEPENDENT_REVIEW_REQUIRED"
                ):
                    build.seal()

    def test_seal_refuses_post_qa_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            (dest / "reviews").mkdir()
            (dest / "reviews/final_independent_reviewer.md").write_text(
                "SYNTHETIC STOP-SEAL FIXTURE: FINAL_REVIEW_PASS_FOR_PROSPECTIVE_STOP"
            )
            build.save(
                dest / "QA_RECEIPT.json",
                {
                    "targeted_status": "PASS",
                    "full_current_phase_status": "FAIL",
                    "scope": "OBJECTIVE_STOP_WITH_IMMUTABLE_TEST_CONFLICT",
                    "code_sha256": {build.CODE[0]: "a" * 64},
                    "log_sha256": {},
                    "replay_sha256": {},
                },
            )
            with (
                patch.object(build, "DEST", dest),
                self.assertRaisesRegex(ValueError, "POST_QA_BYTES_CHANGED"),
            ):
                build.seal()

    def test_wrong_external_parent_pin_rejected_before_reading_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            (dest / "freeze_manifest.json").write_text("synthetic manifest")
            with self.assertRaisesRegex(ValueError, "PARENT_MANIFEST_CHANGED"):
                build.verify_parent(dest, "a" * 64)


if __name__ == "__main__":
    unittest.main()
