from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta, timezone

import test_source_qualified_liquidity_v1 as liquidity_fixture
import test_source_qualified_sfp_context_v1 as sfp_fixture
from test_pure_source_object_provider_v2 import data, sfp_data

from crypto_bot.strategy.pure_source_replay_v2 import compare_replay_prefixes
from crypto_bot.strategy.source_qualified_replay_v1 import (
    AnnotationDelivery,
    EqualPairRequest,
    QualifiedDiagnosticProvider,
    SfpContextRequest,
    run_qualified_diagnostic_replay,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EqualLiquidityKind,
    EvidenceStatus,
)

BASE = liquidity_fixture.BASE


class QualifiedReplayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = liquidity_fixture.QualifiedLiquidityTests()
        self.fixture.setUp()
        self.fixture.frame, self.fixture.swings, self.fixture.pair = (
            liquidity_fixture.fixture(tilt=True)
        )
        self.catalog = self.fixture.catalog
        f = liquidity_fixture.fixture(tilt=True, count=8)[0]
        self.series = data(
            tuple((c.open, c.high, c.low, c.close) for c in f.series[0].candles)
        )
        self.request = EqualPairRequest(
            BASE + timedelta(minutes=6),
            "1m",
            self.fixture.pair[0].obj.object_id,
            self.fixture.pair[1].obj.object_id,
            EqualLiquidityKind.EQH,
            BASE,
            BASE + timedelta(minutes=6),
        )

    def deliveries(self, minute=6):
        self.fixture.annotate()
        self.fixture.annotate("EQH_EQL_REASONABLE_TILT")
        return tuple(
            AnnotationDelivery(
                BASE + timedelta(minutes=minute), r.claim, r.provenance_json.encode()
            )
            for r in self.fixture.journal.records
        )

    def run_case(self, deliveries=(), requests=None, series=None, through=None):
        return run_qualified_diagnostic_replay(
            series or (self.series,),
            self.catalog,
            deliveries=deliveries,
            requests=(self.request,) if requests is None else requests,
            through=through,
        )

    def test_end_to_end_diagnostic_replay_retains_provenance_without_setups_or_plans(
        self,
    ):
        run = self.run_case(self.deliveries())
        self.assertEqual(len(run.batches), 8)
        for batch in run.batches[:5]:
            self.assertEqual(batch.annotation_receipts, ())
            self.assertEqual(batch.equal_liquidity, ())
        sixth = run.batches[5]
        self.assertEqual(sixth.equal_liquidity[0].evidence.status, EvidenceStatus.PASS)
        self.assertEqual(len(sixth.annotation_receipts), 2)
        self.assertTrue(
            sixth.equal_liquidity[0].facts[0].supporting_claims[0].provenance_json
        )
        self.assertFalse(run.replay.runtime_summary["trade_entry_allowed"])
        self.assertTrue(
            all(
                not b.setup_assessments and not b.execution_assessments
                for b in run.batches
            )
        )
        self.assertTrue(
            all(not o.trade_eligible for b in run.batches for o in b.objects)
        )

    def test_missing_annotation_stays_unknown_in_real_runner(self):
        run = self.run_case()
        for batch in run.batches[5:]:
            self.assertEqual(
                batch.equal_liquidity[0].evidence.status, EvidenceStatus.UNKNOWN
            )
            self.assertIsNone(batch.equal_liquidity[0].known_at)

    def test_late_and_off_grid_delivery_use_first_actual_closed_replay_frame(self):
        deliveries = tuple(
            replace(d, observed_at=BASE + timedelta(minutes=6, seconds=30))
            for d in self.deliveries()
        )
        run = self.run_case(deliveries)
        self.assertEqual(
            run.batches[5].equal_liquidity[0].evidence.status, EvidenceStatus.UNKNOWN
        )
        self.assertEqual(
            run.batches[6].equal_liquidity[0].known_at, BASE + timedelta(minutes=7)
        )
        self.assertTrue(
            all(
                r.first_observed_at == BASE + timedelta(minutes=7)
                for r in run.batches[6].annotation_receipts
            )
        )

    def test_later_conflict_never_selects_winner_or_rewrites_prefix(self):
        deliveries = self.deliveries()
        negative = self.fixture.annotate(
            status=EvidenceStatus.FAIL, annotator="conflicting-QA"
        )
        delivery = AnnotationDelivery(
            BASE + timedelta(minutes=8),
            negative.claim,
            negative.provenance_json.encode(),
        )
        run = self.run_case((*deliveries, delivery))
        earlier = self.run_case(deliveries, through=BASE + timedelta(minutes=7))
        self.assertTrue(
            compare_replay_prefixes(
                run.replay, earlier.replay, through=BASE + timedelta(minutes=7)
            ).equal
        )
        self.assertEqual(
            run.batches[7].equal_liquidity[0].evidence.status, EvidenceStatus.UNKNOWN
        )
        self.assertEqual(
            len(run.batches[7].equal_liquidity[0].facts[0].supporting_claims), 2
        )

    def test_exact_repeat_and_reversed_receipt_request_order_are_identical(self):
        deliveries = self.deliveries()
        second = replace(self.request, requested_at=BASE + timedelta(minutes=8))
        left = self.run_case(deliveries, (self.request, second))
        right = self.run_case(tuple(reversed(deliveries)), (second, self.request))
        self.assertEqual(left, right)
        self.assertEqual(left, self.run_case(deliveries, (self.request, second)))

    def test_future_market_mutation_cannot_change_prefix_receipts(self):
        deliveries = self.deliveries()
        original = self.run_case(deliveries)
        candles = tuple(
            replace(
                c,
                open=c.open + 20,
                high=c.high + 20,
                low=c.low + 20,
                close=c.close + 20,
            )
            if index >= 6
            else c
            for index, c in enumerate(self.series.candles)
        )
        changed = self.run_case(
            deliveries, series=(replace(self.series, candles=candles),)
        )
        self.assertTrue(
            compare_replay_prefixes(
                original.replay, changed.replay, through=BASE + timedelta(minutes=6)
            ).equal
        )
        self.assertEqual(original.batches[5], changed.batches[5])

    def test_future_schedule_identity_is_run_metadata_not_prefix_evidence(self):
        deliveries = self.deliveries()
        first = self.run_case(deliveries)
        future = replace(
            self.request,
            requested_at=BASE + timedelta(minutes=9),
            left_swing_id="future-not-yet-subject",
        )
        second = self.run_case(deliveries, (self.request, future))
        self.assertNotEqual(
            first.annotation_input_sha256, second.annotation_input_sha256
        )
        self.assertEqual(first.replay.receipts, second.replay.receipts)
        self.assertEqual(first.batches, second.batches)

    def test_future_annotation_content_cannot_leak_through_full_input_hash(self):
        deliveries = self.deliveries()
        negative = self.fixture.annotate(
            status=EvidenceStatus.FAIL, annotator="future-QA"
        )
        event = AnnotationDelivery(
            BASE + timedelta(minutes=8),
            negative.claim,
            negative.provenance_json.encode(),
        )
        first = self.run_case(deliveries)
        second = self.run_case((*deliveries, event))
        self.assertNotEqual(
            first.annotation_input_sha256, second.annotation_input_sha256
        )
        self.assertTrue(
            compare_replay_prefixes(
                first.replay, second.replay, through=BASE + timedelta(minutes=7)
            ).equal
        )

    def test_context_consumer_integration_keeps_pattern_unknown(self):
        fixture = sfp_fixture.QualifiedSfpContextTests()
        fixture.setUp()
        receipt = fixture.annotate()
        request = SfpContextRequest(
            fixture.end, fixture.sfp.obj.object_id, fixture.start, fixture.end
        )
        delivery = AnnotationDelivery(
            fixture.end, receipt.claim, receipt.provenance_json.encode()
        )
        run = self.run_case((delivery,), (request,), series=(sfp_data(),))
        result = run.batches[5].sfp_contexts[0]
        self.assertEqual(result.context.evidence.status, EvidenceStatus.PASS)
        self.assertEqual(result.priority1_pattern_status, EvidenceStatus.UNKNOWN)
        self.assertFalse(result.execution_ready)
        self.assertFalse(result.trade_entry_allowed)
        self.assertIsNotNone(
            run.batches[7].sfp_contexts[0].transport_state.invalidated_at
        )

    def test_failed_frame_is_not_emitted_and_session_cannot_be_reused(self):
        provider = QualifiedDiagnosticProvider(
            self.catalog,
            exchange="TEST",
            symbol="BTCUSDT",
            deliveries=self.deliveries(),
            requests=(replace(self.request, left_swing_id="invented"),),
        )
        for n in range(1, 6):
            provider.produce(liquidity_fixture.fixture(tilt=True, count=n)[0])
        with self.assertRaisesRegex(ValueError, "actual closed-prefix swings"):
            provider.produce(self.fixture.frame)
        self.assertEqual(len(provider.batches), 5)
        with self.assertRaisesRegex(ValueError, "failed replay session"):
            provider.produce(liquidity_fixture.fixture(tilt=True, count=7)[0])
        self.assertEqual(len(provider.batches), 5)

    def test_clock_advances_without_annotations_and_changed_past_is_rejected(self):
        provider = QualifiedDiagnosticProvider(
            self.catalog, exchange="TEST", symbol="BTCUSDT"
        )
        provider.produce(self.fixture.frame)
        later = liquidity_fixture.fixture(tilt=True, count=7)[0]
        prefix = later.series[0]
        bars = (replace(prefix.candles[0], open=10.01), *prefix.candles[1:])
        changed = replace(later, series=(replace(prefix, candles=bars),))
        with self.assertRaisesRegex(ValueError, "history changed"):
            provider.produce(changed)
        self.assertEqual(len(provider.batches), 1)

    def test_schedules_catalog_market_and_witness_integrity_fail_closed(self):
        delivery = self.deliveries()[0]
        with self.assertRaisesRegex(ValueError, "content hash"):
            replace(delivery, provenance=delivery.provenance + b" ")
        with self.assertRaisesRegex(ValueError, "precede"):
            replace(delivery, observed_at=BASE)
        for field in (
            "trade_entry_allowed",
            "financial_backtest_allowed",
            "numeric_proxy_inference_allowed",
        ):
            with self.assertRaisesRegex(ValueError, "fail-closed SOURCE catalog"):
                run_qualified_diagnostic_replay(
                    (self.series,), replace(self.catalog, **{field: True})
                )
        with self.assertRaisesRegex(ValueError, "fail-closed SOURCE catalog"):
            self.run_with_catalog(
                replace(self.catalog, project_policy_applied=("fake-policy",))
            )
        with self.assertRaisesRegex(ValueError, "market identity"):
            QualifiedDiagnosticProvider(
                self.catalog, exchange="TEST", symbol="OTHER", deliveries=(delivery,)
            )
        with self.assertRaises(TypeError):
            self.run_case(deliveries=[delivery])
        with self.assertRaisesRegex(ValueError, "duplicate consumer request"):
            self.run_case(requests=(self.request, self.request))

    def run_with_catalog(self, catalog):
        return run_qualified_diagnostic_replay((self.series,), catalog)

    def test_request_cannot_observe_future_window_or_carry_policy_fields(self):
        with self.assertRaisesRegex(ValueError, "already be closed"):
            replace(self.request, observation_end_at=BASE + timedelta(minutes=7))
        with self.assertRaises(TypeError):
            EqualPairRequest(**{**self.request.__dict__, "score": 99})
        with self.assertRaises(TypeError):
            replace(self.request, kind="EQH")
        with self.assertRaises(ValueError):
            run_qualified_diagnostic_replay((), self.catalog)

    def test_multiple_timeframe_input_order_preserves_complete_run(self):
        deliveries = self.deliveries()
        bars = self.series.candles
        higher = data(
            tuple(
                (
                    bars[i].open,
                    max(bars[i].high, bars[i + 1].high),
                    min(bars[i].low, bars[i + 1].low),
                    bars[i + 1].close,
                )
                for i in range(0, 8, 2)
            ),
            timeframe="2m",
            interval_ms=120_000,
        )
        self.assertEqual(
            self.run_case(deliveries, series=(self.series, higher)),
            self.run_case(deliveries, series=(higher, self.series)),
        )

    def test_dataset_market_identity_cannot_be_bypassed_by_qualified_provider(self):
        other = data(((10, 11, 9, 10),) * 4, timeframe="2m", interval_ms=120_000)
        other = replace(
            other, candles=tuple(replace(c, symbol="OTHER") for c in other.candles)
        )
        with self.assertRaisesRegex(ValueError, "exchange and symbol"):
            self.run_case(series=(self.series, other))

    def test_equivalent_timezone_deliveries_have_order_invariant_fingerprints(self):
        deliveries = self.deliveries()
        first = deliveries[0]
        offset = timezone(timedelta(hours=3))
        shifted_claim = replace(
            first.claim,
            observation_start_at=first.claim.observation_start_at.astimezone(offset),
            observation_end_at=first.claim.observation_end_at.astimezone(offset),
            known_at=first.claim.known_at.astimezone(offset),
        )
        shifted = replace(
            first, observed_at=first.observed_at.astimezone(offset), claim=shifted_claim
        )
        left = self.run_case((first, shifted, *deliveries[1:]))
        right = self.run_case((shifted, first, *deliveries[1:]))
        self.assertEqual(left.annotation_input_sha256, right.annotation_input_sha256)
        self.assertEqual(left.replay.receipts, right.replay.receipts)
        self.assertEqual(left, right)

    def test_equivalent_timezone_requests_are_canonical_and_cannot_evade_duplicates(
        self,
    ):
        offset = timezone(timedelta(hours=3))
        shifted = replace(
            self.request,
            requested_at=self.request.requested_at.astimezone(offset),
            observation_start_at=self.request.observation_start_at.astimezone(offset),
            observation_end_at=self.request.observation_end_at.astimezone(offset),
        )
        deliveries = self.deliveries()
        self.assertEqual(
            self.run_case(deliveries), self.run_case(deliveries, (shifted,))
        )
        with self.assertRaisesRegex(ValueError, "duplicate consumer request"):
            self.run_case(deliveries, (self.request, shifted))
        sfp = SfpContextRequest(
            shifted.requested_at,
            "not-a-market-claim",
            shifted.observation_start_at,
            shifted.observation_end_at,
        )
        self.assertEqual(sfp.requested_at.utcoffset(), timedelta(0))


if __name__ == "__main__":
    unittest.main()
