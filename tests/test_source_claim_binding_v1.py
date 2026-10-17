from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

from test_pure_source_object_provider_v2 import BASE, sfp_data

from crypto_bot.strategy.causal_objects import SourceObjectType
from crypto_bot.strategy.pure_source_object_provider_v2 import build_source_object_batch
from crypto_bot.strategy.pure_source_replay_v2 import PrefixSeries, ReplayFrame
from crypto_bot.strategy.source_claim_binding_v1 import (
    SourceClaimJournal,
    _witness_payload,
    claim_context_sha256,
    source_candle_subject_id,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    AnnotationMethod,
    QualitativeScope,
    load_qualitative_semantic_catalog,
    make_source_qualitative_claim,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

ROOT = Path(__file__).resolve().parents[1]


def frame_at(count=6):
    data = sfp_data()
    candles = tuple(c.to_strategy_candle(60_000) for c in data.candles[:count])
    return ReplayFrame(
        "TEST",
        "BTCUSDT",
        candles[-1].close_time,
        (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
        "transport-prefix",
    )


class SourceClaimBindingTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_qualitative_semantic_catalog(
            ROOT / "config/pure_source_qualitative_semantics_v2.json"
        )
        self.frame = frame_at()
        self.objects = build_source_object_batch(self.frame).objects
        self.subjects = (
            source_candle_subject_id(
                "TEST", "BTCUSDT", "1m", self.frame.series[0].candles[1]
            ),
        )
        self.journal = SourceClaimJournal(
            self.catalog, exchange="TEST", symbol="BTCUSDT"
        )

    def annotation(
        self,
        *,
        status=EvidenceStatus.PASS,
        semantic="OB_LARGE_BODY_SMALL_WICKS",
        subjects=None,
        frame=None,
        objects=None,
        annotator="synthetic-curated-QA",
    ):
        frame = frame or self.frame
        objects = self.objects if objects is None else objects
        kwargs = {
            "catalog": self.catalog,
            "semantic_id": semantic,
            "status": status,
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "observation_start_at": BASE,
            "observation_end_at": BASE + timedelta(minutes=6),
            "known_at": BASE + timedelta(minutes=6),
            "subject_object_ids": self.subjects if subjects is None else subjects,
            "annotation_method": AnnotationMethod.CURATED_SOURCE_DATASET_ANNOTATION,
            "rationale_code": "SYNTHETIC_QA_NOT_HISTORICAL_ANNOTATION",
        }
        template = make_source_qualitative_claim(
            **kwargs, provenance_ref="unbound-template"
        )
        context = claim_context_sha256(template, frame, objects)
        payload = {**_witness_payload(template, context), "annotator_ref": annotator}
        raw = json.dumps(payload, sort_keys=True).encode()
        claim = make_source_qualitative_claim(
            **kwargs, provenance_ref="sha256:" + sha256(raw).hexdigest()
        )
        return claim, raw

    def query(self, claim, at=None, **kwargs):
        return self.journal.assess(
            semantic_id=claim.semantic_id,
            subject_object_ids=claim.subject_object_ids,
            timeframe=claim.timeframe,
            observation_start_at=claim.observation_start_at,
            observation_end_at=claim.observation_end_at,
            scope=claim.scope,
            decision_at=at or self.frame.decision_at,
            **kwargs,
        )

    def test_real_closed_window_and_content_bound_artifact_project_typed_fact(self):
        claim, raw = self.annotation()
        record = self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        assessment = self.query(claim)
        self.assertEqual(assessment.evidence.status, EvidenceStatus.PASS)
        self.assertTrue(assessment.evidence.provenance_ready)
        self.assertEqual(record.provenance_json.encode(), raw)
        self.assertEqual(assessment.evidence.known_at, self.frame.decision_at)
        self.assertIn("NOT_OBJECT_OR_TRADE_ADMISSION", assessment.reason)

    def test_late_ingestion_cannot_backfill_declared_earlier_known_at(self):
        claim, raw = self.annotation()
        later = frame_at(8)
        record = self.journal.ingest(
            claim,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=raw,
        )
        self.assertEqual(record.first_observed_at, later.decision_at)
        self.assertEqual(record.effective_known_at, later.decision_at)
        self.assertEqual(
            self.query(claim, at=self.frame.decision_at).evidence.status,
            EvidenceStatus.UNKNOWN,
        )
        self.assertEqual(
            self.query(claim, at=later.decision_at).evidence.status, EvidenceStatus.PASS
        )

    def test_missing_claim_stays_unknown_and_cannot_forge_provenance(self):
        claim, _ = self.annotation()
        result = self.query(claim)
        self.assertEqual(result.evidence.status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(result.evidence.evidence_id)
        self.assertIsNone(result.evidence.known_at)

    def test_unknown_and_future_claims_fail_atomically(self):
        unknown = make_source_qualitative_claim(
            catalog=self.catalog,
            semantic_id="OB_LARGE_BODY_SMALL_WICKS",
            status=EvidenceStatus.UNKNOWN,
            symbol="BTCUSDT",
            timeframe="1m",
            observation_start_at=BASE,
            observation_end_at=self.frame.decision_at,
            known_at=self.frame.decision_at,
            subject_object_ids=self.subjects,
        )
        with self.assertRaises(ValueError):
            self.journal.ingest(
                unknown, frame=self.frame, objects=self.objects, provenance=b"{}"
            )
        claim, raw = self.annotation()
        early = frame_at(5)
        with self.assertRaises(ValueError):
            self.journal.ingest(
                claim, frame=early, objects=self.objects, provenance=raw
            )
        self.assertEqual(self.journal.records, ())

    def test_tampered_or_wrong_context_provenance_is_rejected(self):
        claim, raw = self.annotation()
        with self.assertRaisesRegex(ValueError, "content hash"):
            self.journal.ingest(
                claim, frame=self.frame, objects=self.objects, provenance=raw + b" "
            )
        payload = json.loads(raw)
        payload["context_sha256"] = "0" * 64
        wrong = json.dumps(payload).encode()
        altered = make_source_qualitative_claim(
            catalog=self.catalog,
            semantic_id=claim.semantic_id,
            status=claim.status,
            symbol=claim.symbol,
            timeframe=claim.timeframe,
            observation_start_at=claim.observation_start_at,
            observation_end_at=claim.observation_end_at,
            known_at=claim.known_at,
            subject_object_ids=claim.subject_object_ids,
            annotation_method=claim.annotation_method,
            rationale_code=claim.rationale_code,
            provenance_ref="sha256:" + sha256(wrong).hexdigest(),
        )
        with self.assertRaisesRegex(ValueError, "does not attest"):
            self.journal.ingest(
                altered, frame=self.frame, objects=self.objects, provenance=wrong
            )
        self.assertEqual(self.journal.records, ())

    def test_unknown_subject_future_parent_and_missing_ancestry_reject(self):
        with self.assertRaisesRegex(ValueError, "unknown subject"):
            self.annotation(subjects=("fabricated-object",))
        pool = next(
            o for o in self.objects if o.object_type == SourceObjectType.LIQUIDITY_POOL
        )
        without = tuple(
            o for o in self.objects if o.object_id not in pool.parent_object_ids
        )
        with self.assertRaisesRegex(ValueError, "missing/future causal parent"):
            self.annotation(subjects=(pool.object_id,), objects=without)
        future = replace(pool, known_at=self.frame.decision_at + timedelta(minutes=1))
        objects = tuple(
            future if o.object_id == pool.object_id else o for o in self.objects
        )
        with self.assertRaisesRegex(ValueError, "future lifecycle"):
            self.annotation(subjects=(pool.object_id,), objects=objects)

    def test_closed_coverage_gaps_and_unfinished_candles_reject(self):
        prefix = self.frame.series[0]
        for candles in (
            prefix.candles[:-1],
            prefix.candles[:2] + prefix.candles[3:],
            (replace(prefix.candles[0], is_closed=False),) + prefix.candles[1:],
        ):
            malformed = replace(self.frame, series=(replace(prefix, candles=candles),))
            with self.assertRaises(ValueError):
                self.annotation(frame=malformed)

    def test_market_identity_and_scope_cannot_change(self):
        claim, raw = self.annotation()
        with self.assertRaisesRegex(ValueError, "market identity"):
            self.journal.ingest(
                claim,
                frame=replace(self.frame, exchange="OTHER"),
                objects=self.objects,
                provenance=raw,
            )
        context, raw = self.annotation(semantic="SFP_LIQUIDITY_CONTEXT")
        self.journal.ingest(
            context, frame=self.frame, objects=self.objects, provenance=raw
        )
        with self.assertRaisesRegex(ValueError, "trade context"):
            self.journal.assess(
                semantic_id=context.semantic_id,
                subject_object_ids=context.subject_object_ids,
                timeframe="1m",
                observation_start_at=BASE,
                observation_end_at=self.frame.decision_at,
                scope=QualitativeScope.OBJECT_FORMATION,
                decision_at=self.frame.decision_at,
            )

    def test_conflicting_annotations_keep_both_and_select_no_winner(self):
        passed, raw = self.annotation()
        failed, negative = self.annotation(status=EvidenceStatus.FAIL)
        self.journal.ingest(
            passed, frame=self.frame, objects=self.objects, provenance=raw
        )
        before = self.query(passed)
        later = frame_at(8)
        self.journal.ingest(
            failed,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=negative,
        )
        self.assertEqual(self.query(passed), before)
        result = self.query(passed, at=later.decision_at)
        self.assertEqual(result.evidence.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(len(result.supporting_claim_ids), 2)
        self.assertEqual(len(self.journal.records), 2)

    def test_idempotent_later_delivery_keeps_first_observation_and_fact_identity(self):
        claim, raw = self.annotation()
        first = self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        fact = self.query(claim)
        later = frame_at(8)
        repeat = self.journal.ingest(
            claim,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=raw,
        )
        self.assertEqual(first, repeat)
        self.assertEqual(self.query(claim, at=later.decision_at), fact)
        self.assertEqual(len(self.journal.records), 1)

    def test_closed_history_revision_and_clock_reversal_reject_atomically(self):
        claim, raw = self.annotation()
        self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        before = self.journal.records
        prefix = self.frame.series[0]
        changed = replace(prefix.candles[0], close=prefix.candles[0].close + 0.1)
        revised = replace(
            self.frame,
            series=(replace(prefix, candles=(changed,) + prefix.candles[1:]),),
        )
        with self.assertRaisesRegex(ValueError, "history changed"):
            self.journal.ingest(
                claim, frame=revised, objects=self.objects, provenance=raw
            )
        with self.assertRaises(ValueError):
            self.journal.ingest(
                claim, frame=frame_at(5), objects=self.objects, provenance=raw
            )
        self.assertEqual(self.journal.records, before)

    def test_future_invalidation_does_not_change_declared_past_parent_context(self):
        sfp = next(o for o in self.objects if o.object_type == SourceObjectType.SFP)
        claim, raw = self.annotation(
            subjects=(sfp.object_id,), semantic="SFP_LIQUIDITY_CONTEXT"
        )
        first = self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        later = frame_at(8)
        future_objects = build_source_object_batch(later).objects
        self.assertTrue(
            next(
                o for o in future_objects if o.object_id == sfp.object_id
            ).invalidated_at
        )
        self.assertEqual(
            claim_context_sha256(claim, later, future_objects), first.context_sha256
        )
        repeated = self.journal.ingest(
            claim, frame=later, objects=future_objects, provenance=raw
        )
        self.assertEqual(first, repeated)

    def test_independent_prefixes_and_future_ohlc_mutation_preserve_past(self):
        claim, raw = self.annotation()
        negative, nraw = self.annotation(status=EvidenceStatus.FAIL)
        self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        original = self.journal.records[0]
        later = frame_at(8)
        self.journal.ingest(
            negative,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=nraw,
        )
        prefix = SourceClaimJournal(self.catalog, exchange="TEST", symbol="BTCUSDT")
        prefix.ingest(claim, frame=self.frame, objects=self.objects, provenance=raw)
        for minute in (6, 7):
            kwargs = {
                "semantic_id": claim.semantic_id,
                "subject_object_ids": claim.subject_object_ids,
                "timeframe": "1m",
                "observation_start_at": BASE,
                "observation_end_at": BASE + timedelta(minutes=6),
                "scope": claim.scope,
                "decision_at": BASE + timedelta(minutes=minute),
            }
            self.assertEqual(self.journal.assess(**kwargs), prefix.assess(**kwargs))
        low = later.series[0]
        changed = tuple(
            replace(
                c,
                open=c.open + 50,
                high=c.high + 50,
                low=c.low + 50,
                close=c.close + 50,
            )
            if c.open_time >= BASE + timedelta(minutes=6)
            else c
            for c in low.candles
        )
        mutated = replace(
            later, series=(replace(low, candles=changed, newly_closed=changed[-1:]),)
        )
        alternative = SourceClaimJournal(
            self.catalog, exchange="TEST", symbol="BTCUSDT"
        )
        alternative.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        alternative.ingest(
            negative,
            frame=mutated,
            objects=build_source_object_batch(mutated).objects,
            provenance=nraw,
        )
        self.assertEqual(alternative.records[0], original)
        self.assertEqual(self.journal.records[0], original)

    def test_agreeing_later_annotation_does_not_select_author_or_change_fact_id(self):
        claim, raw = self.annotation()
        other, second = self.annotation(annotator="other-synthetic-QA-author")
        self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        fact = self.query(claim).evidence
        later = frame_at(8)
        self.journal.ingest(
            other,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=second,
        )
        result = self.query(claim, at=later.decision_at)
        self.assertEqual(result.evidence, fact)
        self.assertEqual(len(result.supporting_claim_ids), 2)

    def test_future_newly_closed_channel_and_hidden_suffix_are_rejected(self):
        claim, raw = self.annotation()
        prefix = self.frame.series[0]
        for newly in (frame_at(8).series[0].newly_closed, (), prefix.candles[-2:]):
            malformed = replace(
                self.frame, series=(replace(prefix, newly_closed=newly),)
            )
            with self.assertRaisesRegex(ValueError, "newly_closed"):
                self.journal.ingest(
                    claim, frame=malformed, objects=self.objects, provenance=raw
                )
        self.assertEqual(self.journal.records, ())

    def test_clock_can_advance_without_claims_and_prevents_backdated_ingestion(self):
        claim, raw = self.annotation()
        later = frame_at(8)
        self.journal.observe_frame(later)
        with self.assertRaisesRegex(ValueError, "clock cannot move backwards"):
            self.journal.ingest(
                claim, frame=self.frame, objects=self.objects, provenance=raw
            )
        record = self.journal.ingest(
            claim,
            frame=later,
            objects=build_source_object_batch(later).objects,
            provenance=raw,
        )
        self.assertEqual(record.effective_known_at, later.decision_at)
        self.assertEqual(self.query(claim).evidence.status, EvidenceStatus.UNKNOWN)

    def test_source_object_content_cannot_be_revised_under_same_identity(self):
        sfp = next(o for o in self.objects if o.object_type == SourceObjectType.SFP)
        claim, raw = self.annotation(
            subjects=(sfp.object_id,), semantic="SFP_LIQUIDITY_CONTEXT"
        )
        self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        changed = tuple(
            replace(o, provenance="rewritten source attribution")
            if o.object_id == sfp.object_id
            else o
            for o in self.objects
        )
        before = self.journal.records
        with self.assertRaisesRegex(ValueError, "identity/history changed"):
            self.journal.ingest(
                claim, frame=self.frame, objects=changed, provenance=raw
            )
        self.assertEqual(self.journal.records, before)

    def test_lifecycle_append_cannot_rewrite_previously_observed_parent_state(self):
        pool = next(
            o for o in self.objects if o.object_type == SourceObjectType.LIQUIDITY_POOL
        )
        claim, raw = self.annotation(subjects=(pool.object_id,))
        self.journal.ingest(
            claim, frame=self.frame, objects=self.objects, provenance=raw
        )
        later = frame_at(8)
        objects = tuple(
            pool.confirm(self.frame.decision_at, "backdated confirmation")
            if o.object_id == pool.object_id
            else o
            for o in self.objects
        )
        second, artifact = self.annotation(
            subjects=(pool.object_id,),
            frame=later,
            objects=objects,
            annotator="second-synthetic-QA",
        )
        before = self.journal.records
        with self.assertRaisesRegex(ValueError, "rewrites observed history"):
            self.journal.ingest(
                second, frame=later, objects=objects, provenance=artifact
            )
        self.assertEqual(self.journal.records, before)
        self.assertEqual(self.query(claim).evidence.status, EvidenceStatus.PASS)

    def test_context_commits_same_status_but_different_historical_eligibility(self):
        pool = next(
            o for o in self.objects if o.object_type == SourceObjectType.LIQUIDITY_POOL
        )
        pool = pool.confirm(self.frame.decision_at)
        active = replace(
            pool,
            trade_eligible=True,
            lifecycle=(
                *pool.lifecycle[:-1],
                replace(pool.lifecycle[-1], trade_eligible=True),
            ),
        )
        self.assertEqual(
            pool.state_at(self.frame.decision_at).status,
            active.state_at(self.frame.decision_at).status,
        )

        def context(obj):
            objects = tuple(
                obj if o.object_id == pool.object_id else o for o in self.objects
            )
            claim, _ = self.annotation(subjects=(pool.object_id,), objects=objects)
            return claim_context_sha256(claim, self.frame, objects)

        self.assertNotEqual(context(pool), context(active))

    def test_future_eligibility_and_rejection_do_not_change_past_context(self):
        pool = next(
            o for o in self.objects if o.object_type == SourceObjectType.LIQUIDITY_POOL
        )
        claim, _ = self.annotation(subjects=(pool.object_id,))
        before = claim_context_sha256(claim, self.frame, self.objects)
        future = pool.set_trade_eligible(True, frame_at(8).decision_at)
        objects = tuple(
            future if o.object_id == pool.object_id else o for o in self.objects
        )
        self.assertEqual(before, claim_context_sha256(claim, frame_at(8), objects))

    def test_subject_set_normalized_by_direct_constructor_ingestion_and_assessment(
        self,
    ):
        subjects = tuple(
            source_candle_subject_id("TEST", "BTCUSDT", "1m", c)
            for c in self.frame.series[0].candles[1:3]
        )
        claim, raw = self.annotation(subjects=subjects)
        changed = replace(claim, subject_object_ids=(*reversed(subjects), subjects[0]))
        self.assertEqual(changed, claim)
        self.assertEqual(changed.evidence_id, claim.evidence_id)
        self.assertEqual(
            claim_context_sha256(changed, self.frame, self.objects),
            claim_context_sha256(claim, self.frame, self.objects),
        )
        self.journal.ingest(
            changed, frame=self.frame, objects=self.objects, provenance=raw
        )
        self.assertEqual(self.query(claim).evidence.status, EvidenceStatus.PASS)
        repeated = self.journal.ingest(
            changed, frame=self.frame, objects=self.objects, provenance=raw
        )
        self.assertEqual(len(self.journal.records), 1)
        self.assertEqual(repeated, self.journal.records[0])
        result = self.journal.assess(
            semantic_id=claim.semantic_id,
            subject_object_ids=(*reversed(subjects), subjects[0]),
            timeframe=claim.timeframe,
            observation_start_at=claim.observation_start_at,
            observation_end_at=claim.observation_end_at,
            scope=claim.scope,
            decision_at=self.frame.decision_at,
        )
        self.assertEqual(result, self.query(claim))
        with self.assertRaisesRegex(ValueError, "canonical causal payload"):
            replace(claim, subject_object_ids=("conflicting-identity",))

    def test_rejection_reason_is_bound_but_future_cancellation_is_not(self):
        pool = next(
            o for o in self.objects if o.object_type == SourceObjectType.LIQUIDITY_POOL
        )
        claim, _ = self.annotation(subjects=(pool.object_id,))

        def context(obj, frame=self.frame):
            objects = tuple(
                obj if o.object_id == pool.object_id else o for o in self.objects
            )
            return claim_context_sha256(claim, frame, objects)

        self.assertNotEqual(
            context(pool.cancel(self.frame.decision_at, "reason-A")),
            context(pool.cancel(self.frame.decision_at, "reason-B")),
        )
        self.assertEqual(
            context(pool),
            context(pool.cancel(frame_at(8).decision_at, "later"), frame_at(8)),
        )


if __name__ == "__main__":
    unittest.main()
