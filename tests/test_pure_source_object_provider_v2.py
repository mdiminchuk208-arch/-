from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from crypto_bot.common.models import Direction
from crypto_bot.data.models import MarketCandle
from crypto_bot.strategy.causal_objects import SourceObjectType
from crypto_bot.strategy.pure_source_object_provider_v2 import (
    DEFERRED_SOURCE_INPUTS,
    SourceObjectReplayProvider,
    build_source_object_batch,
    run_source_object_replay,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    PrefixSeries,
    ReplayFrame,
    ReplaySeries,
    compare_replay_prefixes,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def data(rows, *, timeframe="1m", interval_ms=60_000):
    return ReplaySeries(
        timeframe,
        interval_ms,
        tuple(
            MarketCandle(
                "TEST",
                "BTCUSDT",
                timeframe,
                int(BASE.timestamp() * 1000) + index * interval_ms,
                *prices,
                100.0,
                1000.0,
                True,
            )
            for index, prices in enumerate(rows)
        ),
    )


def sfp_data():
    return data(
        (
            (100, 102, 98, 100),
            (100, 110, 99, 105),
            (105, 106, 100, 104),
            (104, 108, 101, 107),
            (107, 112, 103, 108),
            (109, 111, 105, 107),
            (107, 116, 106, 114),
            (114, 115, 110, 113),
        )
    )


def fvg_data():
    return data(((100, 101, 99, 100), (103, 104, 102, 103), (106, 107, 105, 106)))


class SourceObjectProviderTests(unittest.TestCase):
    def test_fvg_appears_only_after_third_close(self):
        run = run_source_object_replay((fvg_data(),))
        self.assertFalse(
            any(
                o.object_type == SourceObjectType.FVG
                for b in run.evidence_batches[:2]
                for o in b.objects
            )
        )
        self.assertEqual(
            len(
                [
                    o
                    for o in run.evidence_batches[2].objects
                    if o.object_type == SourceObjectType.FVG
                ]
            ),
            1,
        )
        self.assertEqual(
            run.assessment_counts()["IMB_FVG"], {"PASS": 1, "FAIL": 0, "UNKNOWN": 2}
        )
        self.assertFalse(run.replay.runtime_summary["trade_entry_allowed"])
        self.assertEqual(run.replay.runtime_summary["setup_count"], 0)

    def test_sfp_observed_at_closed_next_candle_without_retroactive_receipt(self):
        run = run_source_object_replay((sfp_data(),))

        def pattern(batch):
            return [
                o
                for o in batch.objects
                if o.object_type == SourceObjectType.SFP
                and o.known_at == BASE + timedelta(minutes=5)
            ]

        self.assertEqual(pattern(run.evidence_batches[4]), [])
        sfps = pattern(run.evidence_batches[5])
        self.assertTrue(sfps)
        self.assertTrue(
            all(
                o.direction == Direction.SHORT.value
                and o.formation_valid
                and not o.trade_eligible
                for o in sfps
            )
        )
        self.assertTrue(all(o.invalidated_at is None for o in sfps))
        ids = {o.object_id for o in sfps}
        invalidated = [
            o for o in run.evidence_batches[-1].objects if o.object_id in ids
        ]
        self.assertEqual({o.object_id for o in invalidated}, ids)
        self.assertTrue(
            all(
                o.formation_valid and o.invalidated_at == BASE + timedelta(minutes=7)
                for o in invalidated
            )
        )
        self.assertTrue(
            all(
                o.state_at(BASE + timedelta(minutes=6)).invalidated_at is None
                for o in invalidated
            )
        )

    def test_full_vs_independently_truncated_prefixes(self):
        original = sfp_data()
        full = run_source_object_replay((original,))
        for count in range(1, len(original.candles) + 1):
            with self.subTest(count=count):
                prefix = run_source_object_replay(
                    (replace(original, candles=original.candles[:count]),)
                )
                through = BASE + timedelta(minutes=count)
                comparison = compare_replay_prefixes(
                    full.replay, prefix.replay, through=through
                )
                self.assertTrue(comparison.equal, comparison.reason)
                self.assertEqual(full.evidence_batches[:count], prefix.evidence_batches)

    def test_future_suffix_and_ohlc_mutation_preserve_earlier_evidence(self):
        original = sfp_data()
        changed = original.candles[:6] + tuple(
            replace(c, high=c.high + 100, low=c.low / 2, close=c.open)
            for c in original.candles[6:]
        )
        left = run_source_object_replay((original,))
        right = run_source_object_replay((replace(original, candles=changed),))
        comparison = compare_replay_prefixes(
            left.replay, right.replay, through=BASE + timedelta(minutes=6)
        )
        self.assertTrue(comparison.equal)
        self.assertEqual(left.evidence_batches[:6], right.evidence_batches[:6])

    def test_every_object_and_parent_is_causal(self):
        run = run_source_object_replay((sfp_data(),))
        for receipt, batch in zip(run.replay.receipts, run.evidence_batches):
            by_id = {o.object_id: o for o in batch.objects}
            for obj in batch.objects:
                self.assertLessEqual(obj.known_at, receipt.decision_at)
                self.assertTrue(obj.source_rule_ids)
                for event in obj.lifecycle:
                    self.assertLessEqual(event.at, receipt.decision_at)
                for parent_id in obj.parent_object_ids:
                    self.assertIn(parent_id, by_id)
                    self.assertLessEqual(by_id[parent_id].known_at, obj.known_at)

    def test_typed_source_geometry_and_lifecycle_are_retained(self):
        for source in (sfp_data(), fvg_data()):
            run = run_source_object_replay((source,))
            for batch in run.evidence_batches:
                by_id = {o.object_id: o for o in batch.objects}
                self.assertEqual(
                    {e.obj.object_id for e in batch.sfps},
                    {
                        o.object_id
                        for o in batch.objects
                        if o.object_type == SourceObjectType.SFP
                    },
                )
                self.assertEqual(
                    {e.obj.object_id for e in batch.imbalances},
                    {
                        o.object_id
                        for o in batch.objects
                        if o.object_type == SourceObjectType.FVG
                    },
                )
                for evidence in (*batch.sfps, *batch.imbalances):
                    self.assertEqual(by_id[evidence.obj.object_id], evidence.obj)
        imbalance = (
            run_source_object_replay((fvg_data(),)).evidence_batches[-1].imbalances[0]
        )
        self.assertEqual((imbalance.zone_low, imbalance.zone_high), (101, 105))

    def test_qualitative_families_stay_unknown_with_source_references(self):
        run = run_source_object_replay((sfp_data(),))
        for family, reason, source in DEFERRED_SOURCE_INPUTS:
            self.assertEqual(
                run.assessment_counts()[family], {"PASS": 0, "FAIL": 0, "UNKNOWN": 8}
            )
            rows = [
                a
                for b in run.evidence_batches
                for a in b.object_assessments
                if a.family == family
            ]
            self.assertTrue(
                all(
                    a.reason == reason
                    and a.source_reference == source
                    and a.object_id is None
                    for a in rows
                )
            )

    def test_same_close_mtf_and_input_order_are_deterministic(self):
        lower = sfp_data()
        part = lower.candles[:5]
        higher = data(
            (
                (
                    part[0].open,
                    max(c.high for c in part),
                    min(c.low for c in part),
                    part[-1].close,
                ),
            ),
            timeframe="5m",
            interval_ms=300_000,
        )
        left = run_source_object_replay((lower, higher))
        right = run_source_object_replay((higher, lower))
        self.assertEqual(left, right)
        for family, _, _ in DEFERRED_SOURCE_INPUTS:
            self.assertEqual(
                left.assessment_counts()[family]["UNKNOWN"], 9
            )  # 8 M1 + 1 M5 close

    def test_provider_is_stateless_and_diagnostics_are_fingerprinted(self):
        original = fvg_data()
        candles = tuple(c.to_strategy_candle(60_000) for c in original.candles)
        frame = ReplayFrame(
            "TEST",
            "BTCUSDT",
            candles[-1].close_time,
            (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
            "fixture",
        )
        provider = SourceObjectReplayProvider()
        self.assertEqual(provider.produce(frame), provider.produce(frame))
        from crypto_bot.strategy.pure_source_replay_v2 import _hash_payload

        batch = provider.produce(frame)
        changed = replace(batch, object_assessments=())
        self.assertNotEqual(_hash_payload(batch), _hash_payload(changed))

    def test_direct_batch_rejects_future_or_malformed_prefix(self):
        candles = tuple(c.to_strategy_candle(60_000) for c in fvg_data().candles)
        frame = ReplayFrame(
            "TEST",
            "BTCUSDT",
            candles[0].close_time,
            (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
            "fixture",
        )
        with self.assertRaisesRegex(ValueError, "future candle close"):
            build_source_object_batch(frame)
        with self.assertRaisesRegex(ValueError, "newly_closed"):
            build_source_object_batch(
                replace(
                    frame,
                    decision_at=candles[-1].close_time,
                    series=(replace(frame.series[0], newly_closed=()),),
                )
            )

    def test_provider_has_no_legacy_or_exchange_dependency(self):
        path = (
            Path(__file__).parents[1]
            / "src/crypto_bot/strategy/pure_source_object_provider_v2.py"
        )
        tree = ast.parse(path.read_text())
        imports = [
            node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        ]
        self.assertFalse(
            any(
                name
                and any(
                    bad in name
                    for bad in (
                        "source_engine",
                        "virtual_portfolio",
                        "historical_replay",
                        "exchange",
                    )
                )
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
