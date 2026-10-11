"""Stage A: fail closed on incomplete metadata; no unrun stage reported complete."""

from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_original_v1_1_metadata_recovery_v2 import (
    CODE,
    END,
    PARENT,
    ROOT,
    START,
    make_metadata,
    make_status,
    validate_status,
    validate_stop_map,
)
from original_v1_1_evidence_adapter_v2 import metadata_at


class MetadataRecoverySafetyTest(unittest.TestCase):
    def setUp(self):
        self.partial = {
            "verified_historical_instrument_intervals": 0,
            "partial_source_observations": [
                {
                    "symbol": "BTCUSDT",
                    "tick_size_before": "0.5",
                    "tick_size_after": "0.1",
                    "historical_known_at": None,
                    "effective_period_proof": False,
                    "admitted_as_VERIFIED_interval": False,
                }
            ],
        }
        self.metadata = make_metadata(self.partial)
        self.inherited = json.loads((PARENT / "EVIDENCE_FUNNEL.json").read_text())
        self.status = make_status(self.metadata, self.inherited)

    def test_full_unknown_map_cannot_pass_frozen_gate_at_any_boundary(self):
        self.assertEqual(validate_stop_map(self.metadata), 0)
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for at in (START - 1, START, START + 1, END - 1, END, END + 1):
                with self.subTest(symbol=symbol, at=at):
                    self.assertIsNone(metadata_at(self.metadata, symbol, at))

    def test_documentation_tick_not_backfilled_into_unknown_values(self):
        self.metadata["records"][0]["values"] = {"tick_size": "0.1"}
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_empty_values_are_not_a_completed_unknown_record(self):
        self.metadata["records"][0]["values"] = {}
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_status_only_promotion_is_rejected(self):
        self.metadata["records"][0]["verification_status"] = "VERIFIED_HISTORICAL"
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_current_page_timestamp_cannot_be_historical_known_at(self):
        self.metadata["records"][0]["provenance"]["historical_known_at"] = START
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_scope_gap_is_rejected(self):
        self.metadata["records"][0]["effective_to"] = END - 1
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_duplicate_symbol_does_not_cover_both_instruments(self):
        self.metadata["records"][1]["symbol"] = "BTCUSDT"
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_new_verified_proof_cannot_be_silently_discarded(self):
        self.partial["verified_historical_instrument_intervals"] = 1
        with self.assertRaises(ValueError):
            make_metadata(self.partial)

    def test_partial_notice_not_promoted_to_full_period(self):
        self.metadata["partial_source_observations"][0][
            "admitted_as_VERIFIED_interval"
        ] = True
        with self.assertRaises(ValueError):
            validate_stop_map(self.metadata)

    def test_unrun_annotation_units_not_reported_as_measured_zero(self):
        self.assertIsNone(self.status["annotation_units"])
        self.status["annotation_units"] = 0
        with self.assertRaises(ValueError):
            validate_status(self.status)

    def test_financial_or_freeze_flags_cannot_pass_stop(self):
        for flag in (
            "SECOND_FINANCIAL_BACKTEST_RAN",
            "financial_outcomes_computed",
            "trade_entry_allowed",
            "Evidence_v3_freeze_created",
            "second_preregistration_created",
        ):
            status = copy.deepcopy(self.status)
            status[flag] = True
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                validate_status(status)

    def test_string_false_is_not_false(self):
        self.status["trade_entry_allowed"] = "false"
        with self.assertRaises(ValueError):
            validate_status(self.status)

    def test_later_stage_must_remain_not_run(self):
        for stage in "BCDEFGH":
            status = copy.deepcopy(self.status)
            status["stages"][stage] = "PASS"
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                validate_status(status)

    def test_inherited_counts_explicitly_partition_not_new_funnel(self):
        self.assertEqual(self.status["qualitative_required_partition"], 131099)
        self.assertEqual(self.status["remaining_UNKNOWN_partition"], 45266)
        self.assertEqual(self.status["critical_metadata_unresolved_candidates"], 176365)
        self.assertEqual(
            self.status["count_provenance"],
            "INHERITED_FROZEN_V2_NOT_RECOMPUTED_AT_STAGE_A",
        )
        validate_status(self.status)

    def test_no_financial_runner_or_production_imports_in_recovery_scripts(self):
        denied = (
            "original_v1_1_financial_accounting",
            "run_original_v1_1_financial_backtest",
            "crypto_bot",
            "ccxt",
        )
        for filename in CODE:
            if not filename.startswith("scripts/"):
                continue
            tree = ast.parse((ROOT / filename).read_text())
            modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    modules.append(node.module or "")
            self.assertFalse(
                any(module.startswith(denied) for module in modules), filename
            )

    def test_discrepant_notice_uses_body_and_title_as_separate_observations(self):
        path = (
            ROOT
            / "docs/original_v1_1_metadata_recovery_v2/provenance/PARTIAL_METADATA_SOURCE_ASSESSMENT.json"
        )
        records = json.loads(path.read_text())["partial_source_observations"]
        self.assertEqual({r["symbol"] for r in records}, {"BTCUSDT", "ETHUSDT"})
        for record in records:
            self.assertNotEqual(
                record["title_claimed_date"], record["body_claimed_date"][:10]
            )
            self.assertIsNone(record["historical_known_at"])
            self.assertFalse(record["admitted_as_VERIFIED_interval"])
            self.assertFalse(record["implemented_change_proved"])


if __name__ == "__main__":
    unittest.main()
