"""Execution-minimum proof gates; no historical outcomes or exchange calls."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from original_v1_1_execution_metadata_v3 import (
    DESCRIPTIVE_FIELDS,
    MODE,
    PRICE_FIELDS,
    SIZE_FIELDS,
    field_requirements,
    interval_eligible,
    literal_detail,
)
from original_v1_1_financial_data import ROOT


def proven_fixture():
    return {
        "symbol": "BTCUSDT",
        "effective_from": 100,
        "effective_to": 200,
        "historical_known_at": 90,
        "proof": {
            k: True
            for k in (
                "historical_version_verified",
                "effective_period_verified",
                "exact_contract_verified",
                "price_filter_verified",
            )
        },
        "values": {
            "tick_size": "0.1",
            "effective_tick_periods": [100, 200],
            "contract_identity": "BTCUSDT",
            "contract_type": "USDT Perpetual",
            "linear_perpetual": True,
        },
    }


class ExecutionMetadataV3Tests(unittest.TestCase):
    def test_normalized_R_price_proof_without_quantity(self):
        self.assertTrue(interval_eligible(proven_fixture()))

    def test_same_interval_not_exchange_executable(self):
        self.assertFalse(
            interval_eligible(proven_fixture(), accounting="EXCHANGE_SIZE_EXECUTION")
        )

    def test_complete_exchange_proof(self):
        r = proven_fixture()
        r["proof"]["quantity_filter_verified"] = True
        r["values"].update(
            qty_step="0.001",
            minimum_qty="0.001",
            quantity_precision=3,
            base_asset="BTC",
            quote_asset="USDT",
            price_precision=1,
        )
        self.assertTrue(interval_eligible(r, accounting="EXCHANGE_SIZE_EXECUTION"))

    def test_future_receipt_not_backdated(self):
        r = proven_fixture()
        r["historical_known_at"] = 201
        self.assertFalse(interval_eligible(r))

    def test_missing_known_at_not_assumed_publication(self):
        r = proven_fixture()
        r["historical_known_at"] = None
        self.assertFalse(interval_eligible(r))

    def test_announced_date_not_effective_period_proof(self):
        r = proven_fixture()
        r["proof"]["effective_period_verified"] = False
        self.assertFalse(interval_eligible(r))

    def test_current_notice_not_immutable_historical_version(self):
        r = proven_fixture()
        r["proof"]["historical_version_verified"] = False
        self.assertFalse(interval_eligible(r))

    def test_no_implementation_observation_no_price_admission(self):
        r = proven_fixture()
        r["proof"]["price_filter_verified"] = False
        self.assertFalse(interval_eligible(r))

    def test_every_price_critical_field_required(self):
        for f in PRICE_FIELDS:
            r = proven_fixture()
            del r["values"][f]
            with self.subTest(field=f):
                self.assertFalse(interval_eligible(r))

    def test_invalid_ticks_rejected(self):
        for tick in ("0", "-0.1", "NaN", "Infinity", "unknown"):
            r = proven_fixture()
            r["values"]["tick_size"] = tick
            with self.subTest(tick=tick):
                self.assertFalse(interval_eligible(r))

    def test_inverse_not_assumed_linear(self):
        r = proven_fixture()
        r["values"]["linear_perpetual"] = False
        self.assertFalse(interval_eligible(r))

    def test_substring_identity_rejected(self):
        r = proven_fixture()
        r["values"]["contract_identity"] = "NEIROBTCUSDT"
        self.assertFalse(interval_eligible(r))

    def test_spot_not_perpetual(self):
        r = proven_fixture()
        r["values"]["contract_type"] = "SPOT"
        self.assertFalse(interval_eligible(r))

    def test_mismatched_tick_period_rejected(self):
        r = proven_fixture()
        r["values"]["effective_tick_periods"] = [100, 300]
        self.assertFalse(interval_eligible(r))

    def test_empty_or_reversed_period_rejected(self):
        for end in (100, 99):
            r = proven_fixture()
            r["effective_to"] = end
            self.assertFalse(interval_eligible(r))

    def test_unknown_accounting_mode_rejected(self):
        with self.assertRaises(ValueError):
            interval_eligible(proven_fixture(), accounting="LIVE")

    def test_omitted_fields_classified_explicitly(self):
        r = field_requirements()
        for f in SIZE_FIELDS + DESCRIPTIVE_FIELDS:
            self.assertEqual(
                r["fields"][f]["normalized_R"], "NOT_REQUIRED_FOR_THIS_ACCOUNTING_VIEW"
            )
        for f in PRICE_FIELDS:
            self.assertEqual(r["fields"][f]["normalized_R"], "REQUIRED")

    def test_no_frozen_adapter_mutation_or_financial_prereg_claim(self):
        r = field_requirements()
        self.assertFalse(r["frozen_metadata_adapter_modified"])
        self.assertFalse(r["trade_entry_allowed"])
        self.assertEqual(r["accounting_mode"], MODE)
        self.assertEqual(
            r["status"], "ELIGIBILITY_CONTRACT_ONLY_NOT_FINANCIAL_PREREGISTRATION"
        )

    def test_proof_gate_immutable_and_deterministic(self):
        r = proven_fixture()
        original = copy.deepcopy(r)
        self.assertEqual(interval_eligible(r), interval_eligible(r))
        self.assertEqual(r, original)

    def test_primary_literal_extraction_unchanged(self):
        for symbol, page in (
            ("ETHUSDT", "bltb4b6d3ffa3c5206c"),
            ("BTCUSDT", "blt80c14139bdd327bc"),
        ):
            path = (
                ROOT
                / "docs/original_v1_1_execution_metadata_v3/provenance"
                / (symbol + "_official_notice.html")
            )
            detail, literal = literal_detail(path)
            prior = (
                ROOT
                / "docs/original_v1_1_metadata_recovery_v2/provenance"
                / ("announcement_article_article_" + page + ".text.txt")
            )
            self.assertEqual(literal, prior.read_text())
            self.assertIn(symbol, literal)
            self.assertIn("2023", detail["date"])

    def test_html_without_primary_structured_body_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "notice.html"
            p.write_text("<html>BTCUSDT 0.1</html>")
            with self.assertRaises(ValueError):
                literal_detail(p)
