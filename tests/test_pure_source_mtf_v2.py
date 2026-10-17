from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta

from test_pure_source_object_provider_v2 import BASE, data

from crypto_bot.strategy.pure_source_mtf_v2 import (
    compose_mtf_source_evidence,
    run_mtf_source_replay,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    PrefixSeries,
    ReplayFrame,
    ReplaySeries,
    _hash_payload,
    compare_replay_prefixes,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


def lower_data(count=15):
    return data(tuple((100 + i, 102 + i, 99 + i, 101 + i) for i in range(count)))


def aggregate(lower, minutes):
    candles = []
    for start in range(0, len(lower.candles) - minutes + 1, minutes):
        part = lower.candles[start : start + minutes]
        candles.append(
            replace(
                part[0],
                interval=f"{minutes}m",
                high=max(c.high for c in part),
                low=min(c.low for c in part),
                close=part[-1].close,
                volume_base=sum(c.volume_base for c in part),
                turnover_quote=sum(c.turnover_quote for c in part),
            )
        )
    return ReplaySeries(f"{minutes}m", minutes * 60_000, tuple(candles))


class SourceMtfTests(unittest.TestCase):
    def test_consistent_ohlc_and_all_lower_relations_without_fixed_ladder(self):
        lower = lower_data()
        result = run_mtf_source_replay(
            (lower, aggregate(lower, 5), aggregate(lower, 15))
        )
        batch = result.evidence_batches[-1]
        self.assertEqual(
            {
                (r.context_timeframe, r.refinement_timeframe)
                for r in batch.refinement_candidates
            },
            {("5m", "1m"), ("15m", "1m"), ("15m", "5m")},
        )
        self.assertTrue(
            all(a.status == EvidenceStatus.PASS for a in batch.mtf_price_audits)
        )
        self.assertEqual([a.complete_tiles for a in batch.mtf_price_audits], [3, 1, 1])
        self.assertEqual(result.replay.runtime_summary["setup_count"], 0)
        self.assertFalse(result.replay.runtime_summary["trade_entry_allowed"])

    def test_future_higher_tf_has_no_objects_or_context_relation(self):
        lower = lower_data(5)
        result = run_mtf_source_replay(
            (lower, aggregate(lower, 5)), through=BASE + timedelta(minutes=4)
        )
        batch = result.evidence_batches[-1]
        self.assertEqual(batch.refinement_candidates, ())
        higher = next(v for v in batch.timeframe_views if v.timeframe == "5m")
        self.assertIsNone(higher.known_through)
        self.assertEqual(higher.object_ids, ())
        self.assertTrue(
            all(a.status == EvidenceStatus.UNKNOWN for a in batch.mtf_price_audits)
        )

    def test_mtf_price_disagreement_fails_closed(self):
        lower = lower_data(5)
        higher = aggregate(lower, 5)
        for field, value in (
            ("open", 100.5),
            ("high", 107),
            ("low", 98),
            ("close", 104.5),
        ):
            with self.subTest(field=field):
                bad = replace(
                    higher, candles=(replace(higher.candles[0], **{field: value}),)
                )
                with self.assertRaisesRegex(ValueError, "MTF OHLC mismatch"):
                    run_mtf_source_replay((lower, bad))

    def test_partial_lower_coverage_is_unknown_not_false_pass(self):
        lower = lower_data(5)
        higher = aggregate(lower, 5)
        result = run_mtf_source_replay(
            (replace(lower, candles=lower.candles[2:]), higher)
        )
        audit = result.evidence_batches[-1].mtf_price_audits[0]
        self.assertEqual(audit.status, EvidenceStatus.UNKNOWN)
        self.assertEqual((audit.complete_tiles, audit.incomplete_tiles), (0, 1))

    def test_nonintegral_grids_do_not_define_a_universal_mapping(self):
        three = data(((100, 102, 99, 101),), timeframe="3m", interval_ms=180_000)
        five = data(((100, 102, 99, 101),), timeframe="5m", interval_ms=300_000)
        result = run_mtf_source_replay((three, five))
        batch = result.evidence_batches[-1]
        self.assertEqual(batch.mtf_price_audits[0].reason, "NONINTEGRAL_FIXED_GRID")
        self.assertEqual(len(batch.refinement_candidates), 1)
        self.assertEqual(batch.refinement_candidates[0].pair.refinement_minutes, 3)

    def test_duplicate_physical_tf_aliases_are_not_double_contexts(self):
        lower = lower_data(3)
        alias = replace(
            lower,
            timeframe="1",
            candles=tuple(replace(c, interval="1") for c in lower.candles),
        )
        with self.assertRaisesRegex(ValueError, "duplicate physical timeframe"):
            run_mtf_source_replay((lower, alias))

    def test_independent_mtf_prefixes_preserve_all_evidence(self):
        lower = lower_data(12)
        higher = aggregate(lower, 5)
        full = run_mtf_source_replay((lower, higher))
        for count in range(5, 13):
            with self.subTest(count=count):
                prefix = run_mtf_source_replay(
                    (
                        replace(lower, candles=lower.candles[:count]),
                        replace(higher, candles=higher.candles[: count // 5]),
                    )
                )
                compared = compare_replay_prefixes(
                    full.replay, prefix.replay, through=BASE + timedelta(minutes=count)
                )
                self.assertTrue(compared.equal, compared.reason)
                self.assertEqual(full.evidence_batches[:count], prefix.evidence_batches)

    def test_future_suffix_mutation_and_input_order_do_not_change_past(self):
        lower = lower_data(12)
        higher = aggregate(lower, 5)
        changed = replace(
            lower,
            candles=lower.candles[:10]
            + tuple(replace(c, high=c.high + 20) for c in lower.candles[10:]),
        )
        full = run_mtf_source_replay((lower, higher))
        other = run_mtf_source_replay((higher, changed))
        self.assertTrue(
            compare_replay_prefixes(
                full.replay, other.replay, through=BASE + timedelta(minutes=10)
            ).equal
        )
        self.assertEqual(full.evidence_batches[:10], other.evidence_batches[:10])

    def test_all_timeframe_view_parents_are_known_and_diagnostics_are_hashed(self):
        lower = lower_data(5)
        result = run_mtf_source_replay((lower, aggregate(lower, 5)))
        for receipt, batch in zip(result.replay.receipts, result.evidence_batches):
            objects = {o.object_id: o for o in batch.objects}
            for view in batch.timeframe_views:
                if view.known_through:
                    self.assertLessEqual(view.known_through, receipt.decision_at)
                for object_id in view.object_ids:
                    self.assertEqual(objects[object_id].timeframe, view.timeframe)
                    self.assertLessEqual(
                        objects[object_id].known_at, receipt.decision_at
                    )
        batch = result.evidence_batches[-1]
        self.assertNotEqual(
            _hash_payload(batch),
            _hash_payload(replace(batch, refinement_candidates=())),
        )

    def test_direct_composition_rejects_future_and_wrong_duration(self):
        candles = tuple(c.to_strategy_candle(60_000) for c in lower_data(2).candles)
        frame = ReplayFrame(
            "TEST",
            "BTCUSDT",
            candles[0].close_time,
            (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
            "fixture",
        )
        with self.assertRaisesRegex(ValueError, "future candle close"):
            compose_mtf_source_evidence(frame)
        with self.assertRaisesRegex(ValueError, "duration"):
            compose_mtf_source_evidence(
                replace(
                    frame,
                    decision_at=candles[-1].close_time,
                    series=(replace(frame.series[0], interval_ms=300_000),),
                )
            )


if __name__ == "__main__":
    unittest.main()
