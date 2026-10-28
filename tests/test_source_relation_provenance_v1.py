from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

from test_source_claim_binding_v1 import BASE, frame_at

from crypto_bot.strategy.pure_source_object_provider_v2 import build_source_object_batch
from crypto_bot.strategy.source_claim_binding_v1 import (
    claim_context_sha256,
    source_candle_subject_id,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    AnnotationMethod,
    load_qualitative_semantic_catalog,
)
from crypto_bot.strategy.source_relation_binding_v1 import (
    SourceRelationJournal,
    relation_witness_payload,
)
from crypto_bot.strategy.source_relation_provenance_v1 import (
    RelationEvent,
    RelationSubject,
    load_source_relation_catalog,
    make_source_relation_claim,
    validate_relation_against_catalog,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

ROOT = Path(__file__).resolve().parents[1]


class SourceRelationProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_qualitative_semantic_catalog(
            ROOT / "config/pure_source_qualitative_semantics_v2.json"
        )
        self.relation_catalog = load_source_relation_catalog(
            ROOT / "config/pure_source_relation_provenance_v1.json"
        )
        self.frame = frame_at()
        self.objects = build_source_object_batch(self.frame).objects
        self.journal = SourceRelationJournal(
            self.catalog,
            self.relation_catalog,
            exchange="TEST",
            symbol="BTCUSDT",
        )
        self.candle_ids = tuple(
            source_candle_subject_id("TEST", "BTCUSDT", "1m", candle)
            for candle in self.frame.series[0].candles
        )

    def subjects(self, semantic: str) -> tuple[RelationSubject, ...]:
        roles = self.relation_catalog.relation(semantic).subject_roles
        if len(roles) > len(self.candle_ids):
            raise AssertionError("fixture needs more unique closed candle subjects")
        return tuple(
            RelationSubject(role, self.candle_ids[index])
            for index, role in enumerate(roles)
        )

    def events(self, semantic: str, *, reverse_order: bool = False):
        roles = self.relation_catalog.relation(semantic).event_roles
        result = []
        for index, role in enumerate(roles, start=2):
            minute = index
            if reverse_order and len(roles) >= 2 and role == roles[-1]:
                minute = 1
            at = BASE + timedelta(minutes=minute)
            result.append(RelationEvent(role, f"synthetic-event-{role}", at, at))
        return tuple(result)

    def annotation(
        self,
        semantic="OB_LAST_BEFORE_IMBALANCE",
        *,
        status=EvidenceStatus.PASS,
        frame=None,
        subjects=None,
        events=None,
        annotator="synthetic-curated-QA-not-market-truth",
    ):
        frame = frame or self.frame
        subjects = self.subjects(semantic) if subjects is None else subjects
        events = self.events(semantic) if events is None else events
        kwargs = {
            "catalog": self.relation_catalog,
            "semantic_id": semantic,
            "status": status,
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "observation_start_at": BASE,
            "observation_end_at": BASE + timedelta(minutes=6),
            "known_at": BASE + timedelta(minutes=6),
            "subjects": subjects,
            "events": events,
            "annotation_method": AnnotationMethod.CURATED_SOURCE_DATASET_ANNOTATION,
            "rationale_code": "SYNTHETIC_QA_NOT_HISTORICAL_OR_MARKET_SOURCE_TRUTH",
        }
        template = make_source_relation_claim(
            **kwargs,
            provenance_ref="unbound-template",
        )
        context = claim_context_sha256(
            template, frame, build_source_object_batch(frame).objects
        )
        payload = {
            **relation_witness_payload(template, context),
            "annotator_ref": annotator,
        }
        raw = json.dumps(payload, sort_keys=True).encode()
        claim = make_source_relation_claim(
            **kwargs,
            provenance_ref="sha256:" + sha256(raw).hexdigest(),
        )
        return claim, raw

    def assess(self, claim, *, at=None):
        return self.journal.assess_relation(
            semantic_id=claim.semantic_id,
            subjects=claim.subjects,
            timeframe=claim.timeframe,
            observation_start_at=claim.observation_start_at,
            observation_end_at=claim.observation_end_at,
            decision_at=at or self.frame.decision_at,
        )

    def test_catalog_freezes_priority1_relations_without_generic_bos_or_policy(self):
        definitions = {row.semantic_id: row for row in self.relation_catalog.relations}
        self.assertEqual(
            definitions["OB_LAST_BEFORE_IMBALANCE"].source_rule_ids,
            ("M_OB_ORIGIN",),
        )
        self.assertEqual(
            definitions["OB_SWEEPS_REFERENCE"].source_rule_ids,
            ("M_OB_SWEEP",),
        )
        self.assertEqual(
            definitions["OB_STRUCTURE_UPDATE_CHOCH"].source_rule_ids,
            ("M_OB_STRUCTURE",),
        )
        self.assertEqual(
            definitions["OB_STRUCTURE_UPDATE_DIRECTIONAL_CONTINUATION"].source_rule_ids,
            ("M_OB_STRUCTURE",),
        )
        self.assertEqual(
            definitions["BREAKER_PARENT_OB"].source_rule_ids,
            ("M_BREAKER_PARENT",),
        )
        self.assertEqual(
            definitions["BREAKER_SWEEP_PIERCE_CHOCH_SEQUENCE"].source_rule_ids,
            ("M_BREAKER_SEQUENCE",),
        )
        self.assertFalse(self.relation_catalog.trade_entry_allowed)
        self.assertFalse(self.relation_catalog.financial_backtest_allowed)
        self.assertFalse(self.relation_catalog.paper_allowed)
        self.assertFalse(self.relation_catalog.live_allowed)
        self.assertFalse(self.relation_catalog.private_api_allowed)
        self.assertFalse(self.relation_catalog.automatic_relation_inference_allowed)
        self.assertEqual(self.relation_catalog.project_policy_applied, ())
        serialized = json.dumps(
            [row.__dict__ for row in self.relation_catalog.relations], default=str
        ).upper()
        self.assertNotIn('"GENERIC_BOS"', serialized)
        self.assertNotIn('"PREFERRED"', serialized)

    def test_bound_relation_projects_typed_fact_but_never_trade_admission(self):
        claim, raw = self.annotation()
        record = self.journal.ingest_relation(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        result = self.assess(claim)
        self.assertEqual(result.status, EvidenceStatus.PASS)
        self.assertEqual(result.known_at, self.frame.decision_at)
        self.assertIn("NOT_OBJECT_OR_TRADE_ADMISSION", result.reason)
        self.assertEqual(record.provenance_json.encode(), raw)
        self.assertEqual(len(self.journal.relation_records), 1)
        self.assertEqual(self.journal.records, ())

    def test_late_relation_delivery_cannot_backfill_declared_earlier_known_at(self):
        claim, _ = self.annotation()
        later = frame_at(8)
        claim, raw = self.annotation(frame=later)
        record = self.journal.ingest_relation(
            claim,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=raw,
        )
        self.assertEqual(record.first_observed_at, later.decision_at)
        self.assertEqual(record.effective_known_at, later.decision_at)
        self.assertEqual(
            self.assess(claim, at=self.frame.decision_at).status,
            EvidenceStatus.UNKNOWN,
        )
        self.assertEqual(
            self.assess(claim, at=later.decision_at).status,
            EvidenceStatus.PASS,
        )

    def test_unknown_relation_cannot_be_ingested_or_carry_fake_provenance(self):
        semantic = "OB_LAST_BEFORE_IMBALANCE"
        unknown = make_source_relation_claim(
            catalog=self.relation_catalog,
            semantic_id=semantic,
            status=EvidenceStatus.UNKNOWN,
            symbol="BTCUSDT",
            timeframe="1m",
            observation_start_at=BASE,
            observation_end_at=self.frame.decision_at,
            known_at=self.frame.decision_at,
            subjects=self.subjects(semantic),
        )
        with self.assertRaises(ValueError):
            self.journal.ingest_relation(
                unknown, frame=self.frame, objects=self.objects, provenance=b"{}"
            )
        with self.assertRaises(ValueError):
            replace(unknown, provenance_ref="sha256:fake")
        self.assertEqual(self.journal.relation_records, ())

    def test_tampered_witness_and_unknown_subject_fail_closed(self):
        claim, raw = self.annotation()
        with self.assertRaisesRegex(ValueError, "content hash"):
            self.journal.ingest_relation(
                claim, frame=self.frame, objects=self.objects, provenance=raw + b" "
            )
        bad_subjects = (
            RelationSubject("ob_candidate", "fabricated-subject"),
            RelationSubject("imbalance", self.candle_ids[1]),
        )
        with self.assertRaisesRegex(ValueError, "unknown subject"):
            self.annotation(subjects=bad_subjects)
        self.assertEqual(self.journal.relation_records, ())

    def test_breaker_sequence_requires_sweep_then_pierce_then_choch(self):
        semantic = "BREAKER_SWEEP_PIERCE_CHOCH_SEQUENCE"
        claim, _ = self.annotation(semantic)
        validate_relation_against_catalog(claim, self.relation_catalog)
        self.assertEqual(
            tuple(event.role for event in claim.events),
            ("sweep_event", "pierce_event", "choch_event"),
        )
        with self.assertRaisesRegex(ValueError, "occurrence order"):
            self.annotation(semantic, events=self.events(semantic, reverse_order=True))

    def test_event_cannot_be_known_after_relation_claim(self):
        semantic = "BREAKER_PARENT_OB"
        role = self.relation_catalog.relation(semantic).event_roles[0]
        occurred = BASE + timedelta(minutes=5)
        event = RelationEvent(
            role,
            "synthetic-late-known-event",
            occurred,
            BASE + timedelta(minutes=7),
        )
        with self.assertRaisesRegex(ValueError, "claim known_at cannot precede"):
            self.annotation(semantic, events=(event,))

    def test_conflicting_relation_annotations_keep_both_and_select_no_winner(self):
        passed, raw = self.annotation()
        self.journal.ingest_relation(
            passed, frame=self.frame, objects=self.objects, provenance=raw
        )
        later = frame_at(8)
        failed, negative = self.annotation(
            status=EvidenceStatus.FAIL,
            frame=later,
            annotator="second-conflicting-synthetic-QA",
        )
        self.journal.ingest_relation(
            failed,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=negative,
        )
        result = self.assess(passed, at=later.decision_at)
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(result.known_at)
        self.assertEqual(result.reason, "CONFLICTING_SOURCE_RELATIONS_NO_WINNER")
        self.assertEqual(len(result.supporting_claim_ids), 2)
        self.assertEqual(len(self.journal.relation_records), 2)

    def test_exact_repeat_is_idempotent_and_keeps_first_observation(self):
        claim, raw = self.annotation()
        first = self.journal.ingest_relation(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        later = frame_at(8)
        repeat = self.journal.ingest_relation(
            claim,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=raw,
        )
        self.assertEqual(first, repeat)
        self.assertEqual(len(self.journal.relation_records), 1)
        self.assertEqual(first.first_observed_at, self.frame.decision_at)

    def test_shared_journal_clock_and_closed_history_revision_fail_closed(self):
        claim, raw = self.annotation()
        self.journal.ingest_relation(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        prefix = self.frame.series[0]
        changed = replace(prefix.candles[0], close=prefix.candles[0].close + 0.1)
        revised = replace(
            self.frame,
            series=(replace(prefix, candles=(changed,) + prefix.candles[1:]),),
        )
        with self.assertRaisesRegex(ValueError, "history changed"):
            self.journal.observe_frame(revised)
        with self.assertRaisesRegex(ValueError, "clock cannot move backwards"):
            self.journal.observe_frame(frame_at(5))
        self.assertEqual(len(self.journal.relation_records), 1)


if __name__ == "__main__":
    unittest.main()
