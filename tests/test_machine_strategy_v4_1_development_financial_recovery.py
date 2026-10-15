from __future__ import annotations

import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import recover_machine_strategy_v4_1_development_financial_v1 as recovery
import run_machine_strategy_v4_1_development_financial_v1 as original
import test_machine_strategy_v4_1_development_financial_runner as fixtures


class BoundedRecoveryTests(unittest.TestCase):
    def test_bounded_worker_and_final_assembly_match_registered_case_exactly(self):
        helper = fixtures.V41PreRunIntegrityTests()
        first = helper._registered_source("long_stb_h4_midbar")
        expected = original._adverse_case(first[0], helper._drive(*first))
        order, native, funding, source = helper._registered_source("long_stb_h4_midbar")
        restored = json.loads(original._compact(order))
        catalogs = {"BTC-USDT-SWAP": [restored], "ETH-USDT-SWAP": []}
        prereg = json.loads(original.PREREG.read_text())
        prereg["development_window"] = {
            "start_utc": "1970-01-01T00:00:00Z",
            "end_exclusive_utc": "1970-01-03T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            stage = out / "recovery"
            stage.mkdir()
            state_path = stage / "STATE.json"
            state = {
                "gate": original.GATE,
                "groups": recovery.groups_for(catalogs),
                "next_group": 0,
                "completed_financial_evaluations": 0,
                "code_sha256": {"fixture": "immutable"},
                "artifacts_sha256": {},
                "trade_entry_allowed": False,
            }
            (stage / "CATALOG_AUDIT.json").write_text("{}")
            with (
                patch.object(recovery, "ROOT", out),
                patch.object(recovery, "OUT", out),
                patch.object(recovery, "STAGE", stage),
                patch.object(recovery, "STATE", state_path),
                patch.object(recovery, "authorize", return_value=prereg),
                patch.object(
                    recovery,
                    "state_load",
                    side_effect=lambda expected: copy.deepcopy(state),
                ),
                patch.object(recovery, "catalogs_from", return_value=catalogs),
                patch.object(original, "market_inputs", return_value={15: native}),
                patch.object(original, "_funding_inputs", return_value=funding),
                patch.object(original, "V41HistoricalAdapter", return_value=source),
            ):
                response = recovery.next_group("a" * 64)
                self.assertEqual(response["groups_complete"], 1)
                state = json.loads(state_path.read_text())
                completed = json.loads(
                    gzip.decompress((stage / "group_000.jsonl.gz").read_bytes())
                )
                self.assertEqual(completed, expected)
                with patch.object(original, "_drive_decision_group") as engine:
                    response = recovery.finalize(recovery.digest(state_path))
                    engine.assert_not_called()
                self.assertEqual(response["completed_financial_evaluations"], 1)
                final_cases = json.loads(
                    gzip.decompress((out / "BTC-USDT-SWAP.cases.jsonl.gz").read_bytes())
                )
                self.assertEqual(final_cases, expected)
                checkpoint = json.loads((out / "RUN_CHECKPOINT.json").read_text())
                self.assertEqual(
                    set(checkpoint["artifacts_sha256"]),
                    set(original.FINAL_FILES) - {"RUN_CHECKPOINT.json"},
                )
                for name, sha in checkpoint["artifacts_sha256"].items():
                    self.assertEqual(recovery.digest(out / name), sha)

    def fixture(self, direction="long"):
        helper = fixtures.V41PreRunIntegrityTests()
        order, native, funding, source = helper._registered_source(
            direction + "_stb_h4_midbar"
        )
        states = helper._drive(order, native, funding, source)
        case = original._adverse_case(order, states)
        group = {
            "index": 0,
            "product": order["product"],
            "decision_at": order["decision_at"],
            "case_ids": [order["case_id"]],
        }
        return order, case, group

    def test_frozen_original_bytes_are_preserved(self):
        self.assertEqual(
            set(recovery.code_pins()),
            recovery.ORIGINAL_SOURCES | recovery.RECOVERY_SOURCES,
        )

    def test_no_boolean_or_path_can_authorize_recovery(self):
        with self.assertRaises(TypeError):
            recovery.authorize(True)
        with self.assertRaises(TypeError):
            recovery.authorize(manifest_path="arbitrary")

    def test_registered_closed_source_survives_json_round_trip_exactly(self):
        for direction in ("long", "short"):
            helper = fixtures.V41PreRunIntegrityTests()
            a = helper._registered_source(direction + "_stb_h4_midbar")
            first = original._jsonable(helper._drive(*a))
            b = helper._registered_source(direction + "_stb_h4_midbar")
            restored = json.loads(original._compact(b[0]))
            second = original._jsonable(helper._drive(restored, *b[1:]))
            self.assertEqual(first, second)
            order, case, group = self.fixture(direction)
            recovery.validate_group(group, [case])
            self.assertEqual(case["case_id"], order["case_id"])

    def test_exclusive_create_never_replaces_a_completed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            recovery.exclusive_json(path, {"original": True})
            first = path.read_bytes()
            with self.assertRaises(FileExistsError):
                recovery.exclusive_json(path, {"replacement": True})
            self.assertEqual(path.read_bytes(), first)

    def test_group_rejects_missing_duplicate_identity_and_scenario_coverage(self):
        _, case, group = self.fixture()
        for bad_cases, error in (([], "PARTITION"), ([case, case], "PARTITION")):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                recovery.validate_group(group, bad_cases)
        for field, value, error in (
            ("decision_at", -1, "IDENTITY"),
            ("product", "WRONG", "IDENTITY"),
            ("all_scenarios", case["all_scenarios"][:-1], "ALL_NINE"),
        ):
            bad = copy.deepcopy(case)
            bad[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, error):
                recovery.validate_group(group, [bad])

    def test_state_requires_external_pin_and_committed_same_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "recovery"
            stage.mkdir()
            state_path = stage / "STATE.json"
            payload = stage / "payload"
            payload.write_text("exact")
            state = {
                "gate": original.GATE,
                "completed_financial_evaluations": 0,
                "trade_entry_allowed": False,
                "code_sha256": {"code": "exact"},
                "artifacts_sha256": {"recovery/payload": recovery.digest(payload)},
            }
            state_path.write_text(json.dumps(state))
            with (
                patch.object(recovery, "ROOT", root),
                patch.object(recovery, "STATE", state_path),
                patch.object(recovery, "code_pins", return_value={"code": "exact"}),
                patch.object(recovery, "verify_pins") as pins,
                patch.object(recovery, "published") as publication,
            ):
                with self.assertRaisesRegex(ValueError, "EXTERNAL_RECOVERY"):
                    recovery.state_load(None)
                self.assertEqual(
                    recovery.state_load(recovery.digest(state_path)), state
                )
                pins.assert_called_once_with(state["artifacts_sha256"])
                publication.assert_has_calls([call(state_path), call(payload)])
                publication.side_effect = lambda path: (
                    (_ for _ in ()).throw(ValueError("UNPUBLISHED_ARTIFACT"))
                    if path == payload
                    else None
                )
                with self.assertRaisesRegex(ValueError, "UNPUBLISHED_ARTIFACT"):
                    recovery.state_load(recovery.digest(state_path))
                with (
                    patch.object(
                        recovery, "code_pins", return_value={"code": "changed"}
                    ),
                    self.assertRaisesRegex(ValueError, "CODE_CHANGED"),
                ):
                    recovery.state_load(recovery.digest(state_path))

    def test_completed_or_existing_group_cannot_execute_again(self):
        _, _, group = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            stage = out / "recovery"
            stage.mkdir()
            for complete in (False, True):
                state = {
                    "completed_financial_evaluations": 0,
                    "next_group": 1 if complete else 0,
                    "groups": [group],
                }
                (stage / "group_000.jsonl.gz").write_bytes(b"already emitted")
                with (
                    patch.object(recovery, "OUT", out),
                    patch.object(recovery, "STAGE", stage),
                    patch.object(recovery, "authorize", return_value={}),
                    patch.object(recovery, "state_load", return_value=state),
                    patch.object(recovery, "catalogs_from", return_value={}),
                    patch.object(original, "market_inputs") as engine,
                    self.assertRaisesRegex(
                        ValueError,
                        "NO_UNFINISHED_GROUP" if complete else "EXISTING_SHARD",
                    ),
                ):
                    recovery.next_group("x")
                engine.assert_not_called()

    def test_aggregation_requires_complete_exact_partition_and_receipts(self):
        order, case, group = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            path = stage / "group_000.jsonl.gz"
            path.write_bytes(gzip.compress(original._compact(case) + b"\n", mtime=0))
            receipt = {
                "group": group,
                "shard_sha256": recovery.digest(path),
                "code_sha256": {"code": "exact"},
            }
            (stage / "group_000.receipt.json").write_text(json.dumps(receipt))
            state = {
                "groups": [group],
                "next_group": 1,
                "code_sha256": {"code": "exact"},
            }
            catalogs = {order["product"]: [order]}
            with patch.object(recovery, "STAGE", stage):
                result = recovery.collect_cases(state, catalogs)
                self.assertEqual(result, {order["product"]: [case]})
                with self.assertRaisesRegex(ValueError, "INCOMPLETE_GROUP_COVERAGE"):
                    recovery.collect_cases({**state, "next_group": 0}, catalogs)
                with self.assertRaisesRegex(ValueError, "CATALOG_CASE_SET"):
                    recovery.collect_cases(state, {order["product"]: [order, order]})
                receipt["shard_sha256"] = "0" * 64
                (stage / "group_000.receipt.json").write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError, "SHARD_RECEIPT_DRIFT"):
                    recovery.collect_cases(state, catalogs)


if __name__ == "__main__":
    unittest.main()
