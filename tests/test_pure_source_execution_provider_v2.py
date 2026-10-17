from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta

from test_pure_source_object_provider_v2 import BASE
from test_pure_source_setup_provider_v2 import setup_data

from crypto_bot.common.models import Direction
from crypto_bot.strategy.pure_source_execution_provider_v2 import (
    run_source_execution_replay,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    _hash_payload,
    compare_replay_prefixes,
)
from crypto_bot.strategy.source_execution_v2 import EntryMode, ExitMode, StopMode
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


def plans(run):
    return tuple(
        a.assessment.plan for a in run.evidence_batches[-1].execution_assessments
    )


class SourceExecutionProviderTests(unittest.TestCase):
    def test_real_parents_capture_semantics_without_fabricating_execution(self):
        run = run_source_execution_replay(setup_data())
        self.assertTrue(plans(run))
        self.assertEqual(
            run.replay.runtime_summary["execution_plan_count"], len(plans(run))
        )
        self.assertEqual(run.replay.runtime_summary["source_ready_setup_ids"], ())
        self.assertFalse(run.replay.runtime_summary["trade_entry_allowed"])
        for plan in plans(run):
            self.assertFalse(plan.execution_ready)
            self.assertEqual(plan.entry_options[0].mode, EntryMode.NEW_POI_ZONE)
            self.assertIsNone(plan.entry_options[0].quote)
            self.assertFalse(plan.entry_options[0].exact_quote)
            self.assertEqual(plan.stop_options[0].mode, StopMode.UNRESOLVED)
            self.assertIsNone(plan.stop_options[0].stop_price)
            self.assertEqual(plan.exit_policy.mode, ExitMode.WAIT_FTA)
            self.assertIsNone(plan.exit_policy.primary_target_price)
            self.assertEqual(
                set(plan.unresolved),
                {
                    "SFP_ENTRY_QUOTE_WITHIN_NEW_POI_UNRESOLVED",
                    "WAIT_SFP_ATR_EVIDENCE",
                    "WAIT_FIRST_TROUBLE_AREA",
                },
            )

    def test_semantics_pass_is_not_execution_ready(self):
        run = run_source_execution_replay(setup_data())
        for assessment in run.evidence_batches[-1].execution_assessments:
            self.assertEqual(assessment.assessment.status, EvidenceStatus.PASS)
        for row in run.evidence_batches[-1].execution_observations:
            self.assertFalse(row.execution_ready)
            self.assertTrue(row.unresolved)
        self.assertTrue(run.evidence_batches[-1].execution_observations)
        self.assertTrue(
            all(p.known_at == BASE + timedelta(minutes=41) for p in plans(run))
        )

    def test_long_short_mirror_keeps_same_unknowns_and_observation_times(self):
        short = run_source_execution_replay(setup_data())
        long = run_source_execution_replay(setup_data(mirror=True))
        self.assertEqual(len(plans(short)), len(plans(long)))
        self.assertTrue(all(p.direction == Direction.SHORT for p in plans(short)))
        self.assertTrue(all(p.direction == Direction.LONG for p in plans(long)))
        self.assertEqual(
            [p.unresolved for p in plans(short)], [p.unresolved for p in plans(long)]
        )
        self.assertEqual(
            [p.known_at for p in plans(short)], [p.known_at for p in plans(long)]
        )

    def test_later_context_invalidation_and_extra_poi_preserve_exact_plan(self):
        initial = run_source_execution_replay(setup_data())
        later = run_source_execution_replay(
            setup_data(invalidation=True, extra_poi=True)
        )
        self.assertEqual(plans(initial), plans(later))
        self.assertTrue(
            compare_replay_prefixes(
                initial.replay, later.replay, through=BASE + timedelta(minutes=45)
            ).equal
        )
        self.assertEqual(initial.evidence_batches, later.evidence_batches[:45])
        self.assertEqual(later.replay.runtime_summary["source_ready_setup_ids"], ())

    def test_independent_prefixes_and_input_order_are_deterministic(self):
        lower, higher = setup_data()
        full = run_source_execution_replay((lower, higher))
        reverse = run_source_execution_replay((higher, lower))
        self.assertEqual(full, reverse)
        for count in (35, 40, 41):
            prefix = run_source_execution_replay(
                (
                    replace(lower, candles=lower.candles[:count]),
                    replace(higher, candles=higher.candles[: count // 5]),
                )
            )
            result = compare_replay_prefixes(
                full.replay, prefix.replay, through=BASE + timedelta(minutes=count)
            )
            self.assertTrue(result.equal, result.reason)
            self.assertEqual(full.evidence_batches[:count], prefix.evidence_batches)

    def test_execution_diagnostics_are_in_batch_fingerprint(self):
        run = run_source_execution_replay(setup_data())
        batch = run.evidence_batches[-1]
        changed = replace(batch, execution_observations=())
        self.assertNotEqual(_hash_payload(batch), _hash_payload(changed))


if __name__ == "__main__":
    unittest.main()
