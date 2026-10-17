from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

from test_source_structure_liquidity_v2 import BASE, c

from crypto_bot.strategy.pure_source_replay_v2 import PrefixSeries, ReplayFrame
from crypto_bot.strategy.source_claim_binding_v1 import (
    SourceClaimJournal,
    _witness_payload,
    claim_context_sha256,
)
from crypto_bot.strategy.source_qualified_liquidity_v1 import (
    assess_bound_equal_liquidity,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    AnnotationMethod,
    load_qualitative_semantic_catalog,
    make_source_qualitative_claim,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EqualLiquidityKind,
    EvidenceStatus,
    confirmed_source_swings,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(*, tilt=False, eql=False, count=6):
    candles = (
        c(0, 10, 11, 9, 10),
        c(1, 10, 13, 9.5, 12),
        c(2, 12, 12, 10, 11),
        c(3, 11, 12, 9, 10),
        c(4, 10, 12.8 if tilt else 13, 9.5, 12),
        c(5, 12, 12, 10, 11),
        c(6, 11, 11.5, 9.5, 10),
        c(7, 10, 11, 9, 10),
    )[:count]
    if eql:
        candles = tuple(
            replace(
                bar,
                open=30 - bar.open,
                high=30 - bar.low,
                low=30 - bar.high,
                close=30 - bar.close,
            )
            for bar in candles
        )
    frame = ReplayFrame(
        "TEST",
        "BTCUSDT",
        candles[-1].close_time,
        (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
        "unused",
    )
    swings = confirmed_source_swings(candles, symbol=frame.symbol, timeframe="1m")
    candidates = tuple(s for s in swings if s.side == ("low" if eql else "high"))
    return frame, swings, candidates[:2]


class QualifiedLiquidityTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_qualitative_semantic_catalog(
            ROOT / "config/pure_source_qualitative_semantics_v2.json"
        )
        self.frame, self.swings, self.pair = fixture()
        self.journal = SourceClaimJournal(
            self.catalog, exchange="TEST", symbol="BTCUSDT"
        )

    def annotate(
        self,
        semantic="EQH_EQL_SUBSTRUCTURE_PAIR",
        *,
        status=EvidenceStatus.PASS,
        annotator="synthetic-QA",
        delivery=None,
        subjects=None,
        window=None,
    ):
        start, end = window or (BASE, BASE + timedelta(minutes=6))
        args = {
            "catalog": self.catalog,
            "semantic_id": semantic,
            "status": status,
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "observation_start_at": start,
            "observation_end_at": end,
            "known_at": end,
            "subject_object_ids": subjects or tuple(s.obj.object_id for s in self.pair),
            "annotation_method": AnnotationMethod.CURATED_SOURCE_DATASET_ANNOTATION,
            "rationale_code": "SYNTHETIC_QA_NOT_MARKET_SOURCE_EVIDENCE",
        }
        template = make_source_qualitative_claim(**args, provenance_ref="template")
        frame = delivery or self.frame
        objects = tuple(
            s.obj
            for s in confirmed_source_swings(
                frame.series[0].candles, symbol=frame.symbol, timeframe="1m"
            )
        )
        context = claim_context_sha256(template, frame, objects)
        raw = json.dumps(
            {**_witness_payload(template, context), "annotator_ref": annotator},
            sort_keys=True,
        ).encode()
        claim = make_source_qualitative_claim(
            **args, provenance_ref="sha256:" + sha256(raw).hexdigest()
        )
        return self.journal.ingest(claim, frame=frame, objects=objects, provenance=raw)

    def assess(self, frame=None, kind=EqualLiquidityKind.EQH, **extra):
        args = {
            "timeframe": "1m",
            "left_swing_id": self.pair[0].obj.object_id,
            "right_swing_id": self.pair[1].obj.object_id,
            "kind": kind,
            "observation_start_at": BASE,
            "observation_end_at": BASE + timedelta(minutes=6),
        }
        args.update(extra)
        return assess_bound_equal_liquidity(self.journal, frame or self.frame, **args)

    def test_exact_pair_requires_bound_substructure_and_retains_full_provenance(self):
        record = self.annotate()
        result = self.assess()
        self.assertEqual(result.evidence.status, EvidenceStatus.PASS)
        self.assertEqual(result.known_at, self.frame.decision_at)
        self.assertEqual(result.facts[0].supporting_claims, (record,))
        self.assertEqual(result.facts[0].scope, record.claim.scope)
        self.assertEqual(
            result.facts[0].subject_object_ids, record.claim.subject_object_ids
        )
        self.assertIn(
            record.provenance_json, result.facts[0].supporting_claims[0].provenance_json
        )
        self.assertFalse(result.trade_entry_allowed)
        self.assertEqual(len(result.facts), 1)

    def test_missing_evidence_stays_unknown_without_fake_timestamp(self):
        result = self.assess()
        self.assertEqual(result.evidence.status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(result.known_at)
        self.assertIsNone(result.evidence.qualitative_evidence_id)
        self.assertEqual(result.facts[0].supporting_claims, ())

    def test_generic_legacy_evidence_cannot_be_injected(self):
        with self.assertRaises(TypeError):
            self.assess(
                substructure_pair_confirmed=True, qualitative_evidence_id="fake"
            )
        with self.assertRaises(TypeError):
            self.assess(kind="EQH")

    def test_tilt_requires_second_exact_semantic_without_numeric_tolerance(self):
        self.frame, self.swings, self.pair = fixture(tilt=True)
        self.annotate()
        self.assertEqual(self.assess().evidence.status, EvidenceStatus.UNKNOWN)
        self.annotate("EQH_EQL_REASONABLE_TILT")
        result = self.assess()
        self.assertEqual(result.evidence.status, EvidenceStatus.PASS)
        self.assertEqual(len(result.facts), 2)

    def test_negative_annotations_remain_negative(self):
        self.annotate(status=EvidenceStatus.FAIL)
        self.assertEqual(self.assess().evidence.status, EvidenceStatus.FAIL)
        self.frame, self.swings, self.pair = fixture(tilt=True)
        self.journal = SourceClaimJournal(
            self.catalog, exchange="TEST", symbol="BTCUSDT"
        )
        self.annotate()
        self.annotate("EQH_EQL_REASONABLE_TILT", status=EvidenceStatus.FAIL)
        self.assertEqual(self.assess().evidence.reason, "TILT_NOT_REASONABLE")

    def test_conflict_has_no_winner_and_preserves_both_receipts(self):
        self.annotate()
        self.annotate(status=EvidenceStatus.FAIL, annotator="other-QA")
        result = self.assess()
        self.assertEqual(result.evidence.status, EvidenceStatus.UNKNOWN)
        self.assertIsNone(result.known_at)
        self.assertEqual(len(result.facts[0].supporting_claims), 2)

    def test_late_annotation_never_backfills_pair(self):
        later, _, _ = fixture(count=8)
        self.annotate(delivery=later)
        self.assertEqual(self.assess().evidence.status, EvidenceStatus.UNKNOWN)
        result = self.assess(later)
        self.assertEqual(result.evidence.status, EvidenceStatus.PASS)
        self.assertEqual(result.geometry_known_at, self.frame.decision_at)
        self.assertEqual(result.known_at, later.decision_at)

    def test_unrelated_subject_or_wrong_semantic_does_not_satisfy_pair(self):
        self.annotate("OB_LARGE_BODY_SMALL_WICKS")
        self.assertEqual(self.assess().evidence.status, EvidenceStatus.UNKNOWN)
        self.annotate(subjects=(self.pair[0].obj.object_id,))
        self.assertEqual(self.assess().evidence.status, EvidenceStatus.UNKNOWN)

    def test_mutated_same_swing_id_context_is_rejected(self):
        self.annotate()
        candles = list(self.frame.series[0].candles)
        candles[0] = replace(candles[0], open=10.01)
        prefix = replace(self.frame.series[0], candles=tuple(candles))
        mutated = replace(self.frame, series=(prefix,))
        with self.assertRaisesRegex(ValueError, "differs from bound"):
            self.assess(mutated)

    def test_actual_swing_identity_and_full_observation_coverage_required(self):
        with self.assertRaisesRegex(ValueError, "actual closed-prefix swings"):
            self.assess(left_swing_id="invented")
        with self.assertRaisesRegex(ValueError, "footprints"):
            self.assess(observation_start_at=BASE + timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.assess(right_swing_id=self.pair[0].obj.object_id)

    def test_prefix_future_mutation_input_order_and_repeat_are_stable(self):
        self.frame, self.swings, self.pair = fixture(tilt=True)
        self.annotate()
        self.annotate("EQH_EQL_REASONABLE_TILT")
        original = self.assess()
        later, _, _ = fixture(tilt=True, count=8)
        self.assertEqual(original, self.assess(later))
        candles = tuple(
            replace(
                bar,
                open=bar.open + 20,
                high=bar.high + 20,
                low=bar.low + 20,
                close=bar.close + 20,
            )
            if bar.open_time >= self.frame.decision_at
            else bar
            for bar in later.series[0].candles
        )
        mutated = replace(
            later,
            series=(
                replace(later.series[0], candles=candles, newly_closed=candles[-1:]),
            ),
        )
        self.assertEqual(original, self.assess(mutated))
        other = SourceClaimJournal(self.catalog, exchange="TEST", symbol="BTCUSDT")
        records = self.journal.records
        for record in reversed(records):
            other.ingest(
                record.claim,
                frame=self.frame,
                objects=tuple(reversed(tuple(s.obj for s in self.swings))),
                provenance=record.provenance_json.encode(),
            )
        prior = self.journal
        self.journal = other
        self.assertEqual(original, self.assess())
        self.journal = prior

    def test_eqh_eql_mirror_symmetry_has_identical_dependency_requirements(self):
        for eql in (False, True):
            self.frame, self.swings, self.pair = fixture(tilt=True, eql=eql)
            self.journal = SourceClaimJournal(
                self.catalog, exchange="TEST", symbol="BTCUSDT"
            )
            self.annotate()
            self.annotate("EQH_EQL_REASONABLE_TILT")
            result = self.assess(
                kind=EqualLiquidityKind.EQL if eql else EqualLiquidityKind.EQH
            )
            self.assertEqual(result.evidence.status, EvidenceStatus.PASS)
            self.assertEqual(result.known_at, self.frame.decision_at)
            self.assertFalse(result.trade_entry_allowed)

    def test_wrong_side_and_reversed_pair_fail_without_annotation(self):
        self.assertEqual(
            self.assess(kind=EqualLiquidityKind.EQL).evidence.status,
            EvidenceStatus.FAIL,
        )
        self.assertEqual(
            self.assess(
                left_swing_id=self.pair[1].obj.object_id,
                right_swing_id=self.pair[0].obj.object_id,
            ).evidence.status,
            EvidenceStatus.FAIL,
        )

    def test_gap_unfinished_or_future_newly_closed_reject(self):
        prefix = self.frame.series[0]
        badprefixes = (
            replace(prefix, candles=prefix.candles[:2] + prefix.candles[3:]),
            replace(
                prefix,
                candles=(
                    *prefix.candles[:-1],
                    replace(prefix.candles[-1], is_closed=False),
                ),
            ),
            replace(prefix, newly_closed=fixture(count=8)[0].series[0].newly_closed),
        )
        for bad in badprefixes:
            with self.assertRaises(ValueError):
                self.assess(replace(self.frame, series=(bad,)))

    def test_invalid_ohlc_and_market_mismatch_reject(self):
        prefix = self.frame.series[0]
        bars = tuple(
            replace(
                c,
                open=c.open - 30,
                high=c.high - 30,
                low=c.low - 30,
                close=c.close - 30,
            )
            for c in prefix.candles
        )
        with self.assertRaisesRegex(ValueError, "invalid OHLC"):
            self.assess(
                replace(
                    self.frame,
                    series=(replace(prefix, candles=bars, newly_closed=bars[-1:]),),
                )
            )
        with self.assertRaisesRegex(ValueError, "market identity"):
            self.assess(replace(self.frame, symbol="OTHER"))


if __name__ == "__main__":
    unittest.main()
