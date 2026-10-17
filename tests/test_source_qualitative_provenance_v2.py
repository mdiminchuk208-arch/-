from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    AnnotationMethod,
    QualitativeScope,
    SourceQualitativeClaim,
    load_qualitative_semantic_catalog,
    make_source_qualitative_claim,
    parse_qualitative_semantic_catalog,
    project_legacy_qualitative,
    source_qualitative_claim_id,
    validate_claim_against_catalog,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "pure_source_qualitative_semantics_v2.json"
BASE = datetime(2026, 4, 1, tzinfo=timezone.utc)


class SourceQualitativeProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.catalog = load_qualitative_semantic_catalog(CONFIG)

    def claim(
        self,
        semantic_id: str = "OB_AGGRESSIVE_IMPULSE",
        *,
        status: EvidenceStatus = EvidenceStatus.PASS,
        known_minute: int = 12,
        subjects: tuple[str, ...] = ("candidate-ob", "impulse-candle"),
    ) -> SourceQualitativeClaim:
        kwargs = {}
        if status != EvidenceStatus.UNKNOWN:
            kwargs = {
                "annotation_method": AnnotationMethod.HUMAN_SOURCE_ANNOTATION,
                "provenance_ref": "annotation-set:source-review-v1:row-17",
                "rationale_code": "SOURCE_TERM_CONFIRMED_FROM_CLOSED_WINDOW",
            }
        return make_source_qualitative_claim(
            catalog=self.catalog,
            semantic_id=semantic_id,
            status=status,
            symbol="BTC-USDT-SWAP",
            timeframe="15m",
            observation_start_at=BASE + timedelta(minutes=10),
            observation_end_at=BASE + timedelta(minutes=11),
            known_at=BASE + timedelta(minutes=known_minute),
            subject_object_ids=subjects,
            **kwargs,
        )

    def test_catalog_is_fail_closed_and_numeric_proxy_inference_is_forbidden(self):
        catalog = self.catalog
        self.assertFalse(catalog.trade_entry_allowed)
        self.assertFalse(catalog.financial_backtest_allowed)
        self.assertFalse(catalog.numeric_proxy_inference_allowed)
        self.assertEqual(catalog.project_policy_applied, ())
        self.assertGreaterEqual(len(catalog.semantics), 13)
        self.assertEqual(
            set(catalog.annotation_methods),
            {
                AnnotationMethod.HUMAN_SOURCE_ANNOTATION,
                AnnotationMethod.CURATED_SOURCE_DATASET_ANNOTATION,
            },
        )

    def test_pass_claim_has_canonical_auditable_identity(self):
        claim = self.claim()
        self.assertEqual(claim.status, EvidenceStatus.PASS)
        self.assertTrue(claim.provenance_ready)
        self.assertEqual(claim.scope, QualitativeScope.OBJECT_FORMATION)
        self.assertTrue(claim.evidence_id)
        validate_claim_against_catalog(claim, self.catalog)

        repeated = self.claim(subjects=("impulse-candle", "candidate-ob"))
        self.assertEqual(claim, repeated)
        self.assertEqual(claim.evidence_id, repeated.evidence_id)

    def test_fail_claim_is_auditable_not_silent_negative(self):
        claim = self.claim(status=EvidenceStatus.FAIL)
        self.assertEqual(claim.status, EvidenceStatus.FAIL)
        self.assertTrue(claim.provenance_ready)
        self.assertTrue(claim.evidence_id)
        validate_claim_against_catalog(claim, self.catalog)

    def test_unknown_claim_cannot_masquerade_as_provenance(self):
        claim = self.claim(status=EvidenceStatus.UNKNOWN)
        self.assertFalse(claim.provenance_ready)
        self.assertIsNone(claim.evidence_id)
        self.assertIsNone(claim.annotation_method)
        self.assertIsNone(claim.provenance_ref)
        projection = project_legacy_qualitative(claim)
        self.assertEqual(projection.status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(projection.evidence_id)

    def test_claim_cannot_be_known_before_observed_closed_window(self):
        with self.assertRaisesRegex(ValueError, "cannot be known before observed data closes"):
            self.claim(known_minute=10)

    def test_future_claim_is_not_available_at_earlier_decision(self):
        claim = self.claim(known_minute=12)
        self.assertFalse(claim.available_at(BASE + timedelta(minutes=11)))
        self.assertTrue(claim.available_at(BASE + timedelta(minutes=12)))

    def test_trade_context_semantic_stays_distinct_from_object_formation(self):
        claim = self.claim("SFP_LIQUIDITY_CONTEXT")
        self.assertEqual(claim.scope, QualitativeScope.TRADE_CONTEXT)
        validate_claim_against_catalog(claim, self.catalog)

        tampered = SourceQualitativeClaim(
            semantic_id=claim.semantic_id,
            scope=QualitativeScope.OBJECT_FORMATION,
            status=claim.status,
            symbol=claim.symbol,
            timeframe=claim.timeframe,
            observation_start_at=claim.observation_start_at,
            observation_end_at=claim.observation_end_at,
            known_at=claim.known_at,
            subject_object_ids=claim.subject_object_ids,
            source_refs=claim.source_refs,
            source_rule_ids=claim.source_rule_ids,
            annotation_method=claim.annotation_method,
            provenance_ref=claim.provenance_ref,
            rationale_code=claim.rationale_code,
            evidence_id=source_qualitative_claim_id(
                semantic_id=claim.semantic_id,
                scope=QualitativeScope.OBJECT_FORMATION,
                status=claim.status,
                symbol=claim.symbol,
                timeframe=claim.timeframe,
                observation_start_at=claim.observation_start_at,
                observation_end_at=claim.observation_end_at,
                known_at=claim.known_at,
                subject_object_ids=claim.subject_object_ids,
                source_refs=claim.source_refs,
                source_rule_ids=claim.source_rule_ids,
                annotation_method=claim.annotation_method,
                provenance_ref=claim.provenance_ref,
                rationale_code=claim.rationale_code,
            ),
        )
        with self.assertRaisesRegex(ValueError, "scope does not match catalog"):
            validate_claim_against_catalog(tampered, self.catalog)

    def test_catalog_rejects_ranking_confidence_and_outcome_metadata(self):
        for field, value in (
            ("rank", 1),
            ("score", 0.9),
            ("confidence", 0.95),
            ("probability", 0.8),
            ("preferred", True),
            ("win_rate", 0.7),
            ("pnl", 100),
        ):
            raw = deepcopy(self.raw)
            raw["semantics"][0][field] = value
            with self.assertRaisesRegex(ValueError, "forbidden qualitative ranking/proxy metadata"):
                parse_qualitative_semantic_catalog(raw)

    def test_catalog_rejects_project_policy_trade_permission_and_numericization(self):
        raw = deepcopy(self.raw)
        raw["project_policy_applied"] = ["ANTI_SCALP"]
        with self.assertRaisesRegex(ValueError, "PROJECT policy"):
            parse_qualitative_semantic_catalog(raw)

        raw = deepcopy(self.raw)
        raw["trade_entry_allowed"] = True
        with self.assertRaisesRegex(ValueError, "fail closed"):
            parse_qualitative_semantic_catalog(raw)

        raw = deepcopy(self.raw)
        raw["numeric_proxy_inference_allowed"] = True
        with self.assertRaisesRegex(ValueError, "may not be auto-numericized"):
            parse_qualitative_semantic_catalog(raw)


if __name__ == "__main__":
    unittest.main()
