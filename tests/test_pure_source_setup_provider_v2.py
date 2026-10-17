from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta

from test_pure_source_mtf_v2 import aggregate
from test_pure_source_object_provider_v2 import BASE, data, sfp_data
from test_source_structure_liquidity_v2 import bullish_sequence

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import SourceObjectType
from crypto_bot.strategy.pure_source_replay_v2 import (
    PrefixSeries,
    ReplayFrame,
    compare_replay_prefixes,
)
from crypto_bot.strategy.pure_source_setup_provider_v2 import (
    run_source_setup_replay,
    source_structure_history,
)
from crypto_bot.strategy.source_setup_v2 import SetupBranch
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


def setup_data(*, mirror=False, invalidation=False, extra_poi=False):
    pre = []
    for candle in sfp_data().candles[:6]:
        pre.extend([(candle.open, candle.high, candle.low, candle.close)] * 5)
    rows = pre + [
        (c.open + 99, c.high + 99, c.low + 99, c.close + 99) for c in bullish_sequence()
    ]
    rows += [(110.6, 111, 106, 107)] + [(106, 108, 105, 106)] * 5
    if extra_poi:
        rows += [(103, 104, 102, 103)] * 5
    if invalidation:
        rows += [(114, 116, 113, 115)] * 5
    if mirror:
        rows = [(250 - o, 250 - l, 250 - h, 250 - c) for o, h, l, c in rows]
    lower = data(tuple(rows))
    higher = aggregate(lower, 5)
    return lower, higher


def passed(batch):
    return tuple(a.evidence for a in batch.setup_assessments if a.evidence is not None)


class SourceSetupProviderTests(unittest.TestCase):
    def test_real_causal_sfp_bos_fvg_chain_assembles_without_entry_permission(self):
        run = run_source_setup_replay(setup_data())
        self.assertTrue(run.evidence_batches[-1].bos_events)
        evidence = passed(run.evidence_batches[-1])
        self.assertTrue(evidence)
        self.assertTrue(
            all(
                e.branch == SetupBranch.SFP_LTF_BOS_NEW_POI
                and e.direction == Direction.SHORT
                for e in evidence
            )
        )
        self.assertTrue(
            all(e.known_at == BASE + timedelta(minutes=41) for e in evidence)
        )
        self.assertEqual(run.replay.runtime_summary["setup_count"], len(evidence))
        self.assertEqual(run.replay.runtime_summary["execution_plan_count"], 0)
        self.assertEqual(run.replay.runtime_summary["source_ready_setup_ids"], ())
        self.assertFalse(run.replay.runtime_summary["trade_entry_allowed"])

    def test_mirrored_long_short_structure_and_setup_symmetry(self):
        short = run_source_setup_replay(setup_data())
        long = run_source_setup_replay(setup_data(mirror=True))
        left, right = (
            passed(short.evidence_batches[-1]),
            passed(long.evidence_batches[-1]),
        )
        self.assertEqual(len(left), len(right))
        self.assertTrue(left)
        self.assertTrue(all(e.direction == Direction.LONG for e in right))
        self.assertEqual(
            sorted(e.known_at for e in left), sorted(e.known_at for e in right)
        )
        self.assertEqual(
            len(short.evidence_batches[-1].bos_events),
            len(long.evidence_batches[-1].bos_events),
        )

    def test_bos_uses_known_parent_and_occurs_once_per_structure(self):
        run = run_source_setup_replay(setup_data())
        final = run.evidence_batches[-1]
        objects = {o.object_id: o for o in final.objects}
        parents = [event.structure_parent_id for event in final.bos_events]
        self.assertEqual(len(parents), len(set(parents)))
        for event in final.bos_events:
            parent = objects[event.structure_parent_id]
            self.assertLess(parent.known_at, event.reference.known_at)
            self.assertEqual(parent.invalidated_at, event.reference.known_at)
            self.assertTrue(parent.formation_valid)
        self.assertTrue(
            all(
                event.reference.known_at <= run.replay.receipts[-1].decision_at
                for event in final.bos_events
            )
        )

    def test_all_setup_source_references_are_traceable(self):
        run = run_source_setup_replay(setup_data())
        for receipt, batch in zip(run.replay.receipts, run.evidence_batches):
            objects = {o.object_id: o for o in batch.objects}
            events = {e.reference.evidence_id: e for e in batch.bos_events}
            for evidence in passed(batch):
                self.assertIn(evidence.context_object_id, objects)
                self.assertIn(evidence.entry_poi_id, objects)
                self.assertLessEqual(evidence.known_at, receipt.decision_at)
                self.assertIn(evidence.evidence_ids[0], events)
                self.assertLessEqual(
                    events[evidence.evidence_ids[0]].reference.known_at,
                    evidence.known_at,
                )
                self.assertTrue(evidence.physical_idea.formation_valid)
                self.assertFalse(evidence.setup.trade_eligible)

    def test_qualitative_branches_stay_unknown_without_suppressing_objects(self):
        run = run_source_setup_replay(setup_data())
        final = run.evidence_batches[-1]
        for branch in SetupBranch:
            if branch != SetupBranch.SFP_LTF_BOS_NEW_POI:
                rows = [r for r in final.setup_observations if r.branch == branch]
                self.assertTrue(rows)
                self.assertTrue(all(r.status == EvidenceStatus.UNKNOWN for r in rows))
        self.assertTrue(
            any(o.object_type == SourceObjectType.SFP for o in final.objects)
        )

    def test_later_invalidation_does_not_erase_source_setup_history(self):
        run = run_source_setup_replay(setup_data(invalidation=True))
        before = passed(run.evidence_batches[44])
        self.assertTrue(before)
        final = {e.setup.object_id: e for e in passed(run.evidence_batches[-1])}
        self.assertTrue(all(final[e.setup.object_id] == e for e in before))
        self.assertTrue(
            any(
                r.reason == "SFP_CONTEXT_INVALIDATED_BEFORE_OBSERVATION"
                for r in run.evidence_batches[-1].setup_observations
            )
        )
        self.assertEqual(run.replay.runtime_summary["source_ready_setup_ids"], ())

    def test_later_nonunique_poi_does_not_rewrite_earlier_unique_assembly(self):
        run = run_source_setup_replay(setup_data(extra_poi=True))
        before = passed(run.evidence_batches[44])
        self.assertTrue(before)
        final = {e.setup.object_id: e for e in passed(run.evidence_batches[-1])}
        self.assertTrue(all(final[e.setup.object_id] == e for e in before))
        self.assertTrue(
            any(
                r.reason == "WAIT_NONUNIQUE_ENTRY_POI"
                for r in run.evidence_batches[-1].setup_observations
            )
        )

    def test_independent_prefixes_and_future_invalidation_cannot_backfill_ready(self):
        lower, higher = setup_data(invalidation=True)
        full = run_source_setup_replay((lower, higher))
        for count in (30, 35, 39, 40, 41, 45):
            prefix = run_source_setup_replay(
                (
                    replace(lower, candles=lower.candles[:count]),
                    replace(higher, candles=higher.candles[: count // 5]),
                )
            )
            comparison = compare_replay_prefixes(
                full.replay, prefix.replay, through=BASE + timedelta(minutes=count)
            )
            self.assertTrue(comparison.equal, comparison.reason)
            self.assertEqual(full.evidence_batches[:count], prefix.evidence_batches)
        self.assertFalse(passed(full.evidence_batches[39]))
        self.assertTrue(passed(full.evidence_batches[40]))

    def test_missing_later_context_data_is_unknown_not_pattern_expiry(self):
        lower, higher = setup_data()
        run = run_source_setup_replay(
            (lower, replace(higher, candles=higher.candles[:6]))
        )
        self.assertTrue(
            any(
                r.reason == "WAIT_SOURCE_CLOSED_CONTEXT_DATA"
                for r in run.evidence_batches[-1].setup_observations
            )
        )
        self.assertEqual(run.replay.runtime_summary["setup_count"], 0)
        self.assertTrue(
            all(e.obj.formation_valid for e in run.evidence_batches[-1].sfps)
        )

    def test_public_structure_history_rejects_future_prefix(self):
        lower, _ = setup_data()
        candles = tuple(c.to_strategy_candle(60_000) for c in lower.candles)
        frame = ReplayFrame(
            "TEST",
            "BTCUSDT",
            candles[0].close_time,
            (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
            "fixture",
        )
        with self.assertRaisesRegex(ValueError, "future candle close"):
            source_structure_history(frame)

    def test_structure_first_known_already_broken_does_not_create_later_bos(self):
        rows = [(c.open, c.high, c.low, c.close) for c in bullish_sequence()]
        rows[-1] = (12.6, 12.7, 8.5, 8.8)
        rows.append((8.8, 9.0, 8.0, 8.6))
        reclaimed = [(c.open, c.high, c.low, c.close) for c in bullish_sequence()]
        reclaimed[7] = (11.2, 13, 8.5, 8.8)
        reclaimed[8] = (8.8, 12.7, 8.7, 11.6)
        reclaimed.append((11.6, 11.9, 8.0, 8.6))
        for rows in (rows, reclaimed):
            for mirror in (False, True):
                with self.subTest(mirror=mirror):
                    prices = (
                        [(20 - o, 20 - l, 20 - h, 20 - c) for o, h, l, c in rows]
                        if mirror
                        else rows
                    )
                    series = data(tuple(prices))
                    candles = tuple(
                        c.to_strategy_candle(60_000) for c in series.candles
                    )
                    frame = ReplayFrame(
                        "TEST",
                        "BTCUSDT",
                        candles[-1].close_time,
                        (PrefixSeries("1m", 60_000, candles, candles[-1:]),),
                        "fixture",
                    )
                    structures, events = source_structure_history(frame)
                    self.assertTrue(structures)
                    self.assertEqual(events, ())
                    self.assertTrue(
                        any(
                            o.invalidated_at == BASE + timedelta(minutes=9)
                            and o.formation_valid
                            for o in structures
                        )
                    )


if __name__ == "__main__":
    unittest.main()
