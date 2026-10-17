from __future__ import annotations

import json
import unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from test_pure_source_object_provider_v2 import BASE, sfp_data

from crypto_bot.strategy.pure_source_object_provider_v2 import build_source_object_batch
from crypto_bot.strategy.pure_source_replay_v2 import PrefixSeries, ReplayFrame
from crypto_bot.strategy.source_claim_binding_v1 import (
    SourceClaimJournal,
    _witness_payload,
    claim_context_sha256,
)
from crypto_bot.strategy.source_qualified_sfp_context_v1 import assess_bound_sfp_context
from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    AnnotationMethod,
    QualitativeScope,
    load_qualitative_semantic_catalog,
    make_source_qualitative_claim,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

ROOT = Path(__file__).resolve().parents[1]


def frame_at(count=6, *, hourly=False, mirrored=False):
    bars = tuple(c.to_strategy_candle(60_000) for c in sfp_data().candles[:count])
    if hourly:
        bars = tuple(
            replace(
                c,
                open_time=BASE + (c.open_time - BASE) * 60,
                close_time=BASE + (c.close_time - BASE) * 60,
            )
            for c in bars
        )
    if mirrored:
        bars = tuple(
            replace(
                c,
                open=300 - c.open,
                high=300 - c.low,
                low=300 - c.high,
                close=300 - c.close,
            )
            for c in bars
        )
    return ReplayFrame(
        "TEST",
        "BTCUSDT",
        bars[-1].close_time,
        (
            PrefixSeries(
                "1h" if hourly else "1m",
                3_600_000 if hourly else 60_000,
                bars,
                bars[-1:],
            ),
        ),
        "unused",
    )


class QualifiedSfpContextTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_qualitative_semantic_catalog(
            ROOT / "config/pure_source_qualitative_semantics_v2.json"
        )
        self.frame = frame_at()
        self.journal = SourceClaimJournal(
            self.catalog, exchange="TEST", symbol="BTCUSDT"
        )
        self.select_sfp()

    def select_sfp(self):
        self.batch = build_source_object_batch(self.frame)
        self.sfp = self.batch.sfps[0]
        self.start = BASE
        self.end = self.frame.decision_at

    def annotate(
        self,
        *,
        semantic="SFP_LIQUIDITY_CONTEXT",
        status=EvidenceStatus.PASS,
        subjects=None,
        annotator="synthetic-QA",
        delivery=None,
    ):
        args = {
            "catalog": self.catalog,
            "semantic_id": semantic,
            "status": status,
            "symbol": "BTCUSDT",
            "timeframe": self.sfp.obj.timeframe,
            "observation_start_at": self.start,
            "observation_end_at": self.end,
            "known_at": self.end,
            "subject_object_ids": subjects
            or (self.sfp.obj.object_id, self.sfp.parent_liquidity_id),
            "annotation_method": AnnotationMethod.CURATED_SOURCE_DATASET_ANNOTATION,
            "rationale_code": "SYNTHETIC_QA_NOT_MARKET_SOURCE_EVIDENCE",
        }
        template = make_source_qualitative_claim(**args, provenance_ref="template")
        frame = delivery or self.frame
        objects = build_source_object_batch(frame).objects
        context = claim_context_sha256(template, frame, objects)
        raw = json.dumps(
            {**_witness_payload(template, context), "annotator_ref": annotator},
            sort_keys=True,
        ).encode()
        claim = make_source_qualitative_claim(
            **args, provenance_ref="sha256:" + sha256(raw).hexdigest()
        )
        return self.journal.ingest(claim, frame=frame, objects=objects, provenance=raw)

    def assess(self, frame=None, **changes):
        args = {
            "sfp_object_id": self.sfp.obj.object_id,
            "observation_start_at": self.start,
            "observation_end_at": self.end,
        }
        args.update(changes)
        return assess_bound_sfp_context(self.journal, frame or self.frame, **args)

    def test_context_pass_retains_provenance_but_not_pattern_or_trade_admission(self):
        record = self.annotate()
        result = self.assess()
        self.assertEqual(result.context.evidence.status, EvidenceStatus.PASS)
        self.assertEqual(result.supporting_claims, (record,))
        self.assertEqual(result.scope, QualitativeScope.TRADE_CONTEXT)
        self.assertEqual(result.priority1_pattern_status, EvidenceStatus.UNKNOWN)
        self.assertFalse(result.trade_entry_allowed)
        self.assertFalse(result.execution_ready)
        self.assertFalse(result.transport_object.trade_eligible)
        self.assertEqual(result.context_known_at, self.frame.decision_at)
        self.assertEqual(result.transport_closed_observable_at, self.frame.decision_at)
        with self.assertRaises(ValueError):
            replace(result, trade_entry_allowed=True)

    def test_missing_context_never_uses_structural_formation_as_substitute(self):
        result = self.assess()
        self.assertTrue(result.transport_object.formation_valid)
        self.assertEqual(result.context.evidence.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.priority1_pattern_status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(result.context_known_at)
        self.assertEqual(result.supporting_claims, ())

    def test_context_failure_does_not_mutate_structural_object(self):
        original = self.sfp.obj
        self.annotate(status=EvidenceStatus.FAIL)
        result = self.assess()
        self.assertEqual(result.context.evidence.status, EvidenceStatus.FAIL)
        self.assertEqual(result.transport_object, original)
        self.assertTrue(result.transport_state.formation_valid)
        self.assertEqual(self.batch.sfps[0].obj, original)

    def test_late_context_cannot_backfill_prior_decision(self):
        later = frame_at(8)
        self.annotate(delivery=later)
        self.assertEqual(self.assess().context.evidence.status, EvidenceStatus.UNKNOWN)
        result = self.assess(later)
        self.assertEqual(result.context.evidence.status, EvidenceStatus.PASS)
        self.assertEqual(result.context_known_at, later.decision_at)

    def test_conflict_has_no_winner_and_keeps_complete_receipts(self):
        self.annotate()
        self.annotate(status=EvidenceStatus.FAIL, annotator="other-QA")
        result = self.assess()
        self.assertEqual(result.context.evidence.status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(result.context_known_at)
        self.assertEqual(len(result.supporting_claims), 2)

    def test_wrong_semantic_scope_subject_or_parent_cannot_be_injected(self):
        self.annotate(semantic="OB_LARGE_BODY_SMALL_WICKS")
        self.annotate(subjects=(self.sfp.obj.object_id,))
        self.assertEqual(self.assess().context.evidence.status, EvidenceStatus.UNKNOWN)
        with self.assertRaises(TypeError):
            self.assess(scope=QualitativeScope.OBJECT_FORMATION)
        with self.assertRaises(TypeError):
            self.assess(context_confirmed=True)

    def test_noncanonical_or_future_sfp_identity_rejects(self):
        with self.assertRaisesRegex(ValueError, "actual closed-prefix SFP"):
            self.assess(sfp_object_id="invented")
        with self.assertRaisesRegex(ValueError, "actual closed-prefix SFP"):
            self.assess(frame_at(5))

    def test_observation_window_requires_closed_transport_not_earlier_next_open(self):
        with self.assertRaisesRegex(ValueError, "cover closed sweep"):
            self.assess(observation_end_at=self.sfp.obj.known_at)
        with self.assertRaisesRegex(ValueError, "cover closed sweep"):
            self.assess(observation_start_at=self.frame.decision_at)

    def test_bound_context_tampering_preserving_subject_ids_rejects(self):
        self.annotate()
        prefix = self.frame.series[0]
        bars = (replace(prefix.candles[0], open=100.01), *prefix.candles[1:])
        changed = replace(self.frame, series=(replace(prefix, candles=bars),))
        with self.assertRaisesRegex(ValueError, "differs from bound SFP"):
            self.assess(changed)

    def test_later_invalidation_does_not_rewrite_prior_context_or_formation(self):
        self.annotate()
        original = self.assess()
        later = self.assess(frame_at(8))
        self.assertEqual(later.context, original.context)
        self.assertEqual(later.supporting_claims, original.supporting_claims)
        self.assertEqual(later.context_known_at, original.context_known_at)
        self.assertIsNone(original.transport_state.invalidated_at)
        self.assertIsNotNone(later.transport_state.invalidated_at)
        self.assertTrue(later.transport_state.formation_valid)
        self.assertEqual(self.assess(), original)

    def test_future_ohlc_mutation_repeat_and_input_order_preserve_past_context(self):
        self.annotate()
        self.annotate(annotator="second-QA")
        original = self.assess()
        later = frame_at(8)
        prefix = later.series[0]
        bars = tuple(
            replace(
                c,
                open=c.open + 30,
                high=c.high + 30,
                low=c.low + 30,
                close=c.close + 30,
            )
            if c.open_time >= self.frame.decision_at
            else c
            for c in prefix.candles
        )
        changed = replace(
            later, series=(replace(prefix, candles=bars, newly_closed=bars[-1:]),)
        )
        actual = self.assess(changed)
        self.assertEqual(actual.context, original.context)
        self.assertEqual(actual.supporting_claims, original.supporting_claims)
        other = SourceClaimJournal(self.catalog, exchange="TEST", symbol="BTCUSDT")
        for receipt in reversed(self.journal.records):
            other.ingest(
                receipt.claim,
                frame=self.frame,
                objects=tuple(reversed(self.batch.objects)),
                provenance=receipt.provenance_json.encode(),
            )
        self.journal = other
        self.assertEqual(self.assess(), original)

    def test_all_timeframes_and_long_short_context_transport_are_symmetric(self):
        for hourly in (False, True):
            for mirrored in (False, True):
                self.frame = frame_at(hourly=hourly, mirrored=mirrored)
                self.journal = SourceClaimJournal(
                    self.catalog, exchange="TEST", symbol="BTCUSDT"
                )
                self.select_sfp()
                self.annotate()
                result = self.assess()
                self.assertEqual(result.context.evidence.status, EvidenceStatus.PASS)
                self.assertFalse(result.trade_entry_allowed)
                self.assertEqual(
                    result.priority1_pattern_status, EvidenceStatus.UNKNOWN
                )

    def test_future_newly_closed_gap_and_market_mismatch_reject(self):
        prefix = self.frame.series[0]
        for malformed in (
            replace(
                self.frame,
                series=(
                    replace(prefix, newly_closed=frame_at(8).series[0].newly_closed),
                ),
            ),
            replace(
                self.frame,
                series=(
                    replace(prefix, candles=prefix.candles[:1] + prefix.candles[2:]),
                ),
            ),
            replace(self.frame, symbol="OTHER"),
        ):
            with self.assertRaises(ValueError):
                self.assess(malformed)


if __name__ == "__main__":
    unittest.main()
