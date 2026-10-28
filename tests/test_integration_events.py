import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.integration.events import STRATEGY_EVENT_SCHEMA, StrategyObjectSnapshot
from crypto_bot.strategy.causal_objects import CausalSourceObject, ObjectStatus, SourceObjectType


UTC = timezone.utc


def source_object(*, eligible=False, status=ObjectStatus.KNOWN):
    formation = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
    known = formation + timedelta(minutes=15)
    return CausalSourceObject(
        object_id="obj-1",
        object_type=SourceObjectType.SETUP,
        symbol="BTC-USDT-SWAP",
        timeframe="15",
        direction="LONG",
        formation_at=formation,
        known_at=known,
        confirmed_at=None,
        invalidated_at=None,
        formation_valid=True,
        trade_eligible=eligible,
        status=status,
        source_rule_ids=("SRC-1", "SRC-2"),
        technical_normalization_ids=("TECH-CLOSED-BAR",),
        rejection_reasons=(),
        parent_object_ids=("parent-1",),
        provenance="test-provenance",
        lifecycle=(),
    )


class IntegrationEventTests(unittest.TestCase):
    def test_snapshot_preserves_engine_state_but_never_grants_execution(self):
        obj = source_object(eligible=True, status=ObjectStatus.READY)
        snapshot = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at + timedelta(minutes=1),
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertTrue(snapshot.trade_eligible)
        self.assertFalse(snapshot.trade_entry_allowed)
        self.assertEqual(snapshot.status, "READY")
        self.assertEqual(snapshot.schema, STRATEGY_EVENT_SCHEMA)

    def test_same_state_has_same_event_id_even_when_reemitted_later(self):
        obj = source_object()
        left = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at + timedelta(minutes=1),
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        right = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at + timedelta(hours=1),
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertEqual(left.event_id, right.event_id)
        self.assertNotEqual(left.emitted_at, right.emitted_at)

    def test_dataset_version_change_changes_event_identity(self):
        obj = source_object()
        left = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        right = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-2",
        )
        self.assertNotEqual(left.event_id, right.event_id)

    def test_geometry_is_optional_and_never_invented(self):
        obj = source_object()
        snapshot = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertIsNone(snapshot.entry_price)
        self.assertIsNone(snapshot.stop_price)
        self.assertIsNone(snapshot.fta_price)

    def test_geometry_changes_event_identity_when_explicitly_supplied(self):
        obj = source_object()
        left = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
            entry_price=81_250,
            stop_price=80_640,
            fta_price=82_380,
        )
        right = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
            entry_price=81_300,
            stop_price=80_640,
            fta_price=82_380,
        )
        self.assertNotEqual(left.event_id, right.event_id)

    def test_source_branch_and_evidence_are_bound_to_event_identity(self):
        obj = source_object()
        left = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
            source_branch_ids=("OB_DIRECT_ENTRY:A",),
            evidence_ids=("evidence-1",),
        )
        right = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
            source_branch_ids=("OB_DIRECT_ENTRY:B",),
            evidence_ids=("evidence-1",),
        )
        self.assertNotEqual(left.event_id, right.event_id)

    def test_direct_construction_cannot_enable_trade_entry(self):
        obj = source_object()
        snapshot = StrategyObjectSnapshot.from_source_object(
            obj,
            emitted_at=obj.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        with self.assertRaises(ValueError):
            replace(snapshot, trade_entry_allowed=True)

    def test_emitted_at_before_known_at_is_rejected(self):
        obj = source_object()
        with self.assertRaises(ValueError):
            StrategyObjectSnapshot.from_source_object(
                obj,
                emitted_at=obj.formation_at,
                engine_version="stage23",
                engine_git_commit="abc123",
                dataset_id="dataset-1",
            )

    def test_nonpositive_price_is_rejected(self):
        obj = source_object()
        with self.assertRaises(ValueError):
            StrategyObjectSnapshot.from_source_object(
                obj,
                emitted_at=obj.known_at,
                engine_version="stage23",
                engine_git_commit="abc123",
                dataset_id="dataset-1",
                stop_price=0,
            )


if __name__ == "__main__":
    unittest.main()
