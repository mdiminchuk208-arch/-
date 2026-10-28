import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_bot.common.models import Direction
from crypto_bot.integration.events import StrategyObjectSnapshot
from crypto_bot.integration.execution import SourceExecutionPlanSnapshot
from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.integration.publish import publish_source_execution_plan, publish_strategy_object
from crypto_bot.strategy.causal_objects import CausalSourceObject, ObjectStatus, SourceObjectType
from crypto_bot.strategy.source_execution_v2 import EntryMode, EntryOption, ExitMode, ExitPolicy, SourceExecutionPlan, StopMode, StopOption
from crypto_bot.strategy.source_setup_v2 import SetupBranch


UTC = timezone.utc
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


def object_snapshot():
    obj = CausalSourceObject(
        object_id="obj-1",
        object_type=SourceObjectType.LIQUIDITY,
        symbol="BTC-USDT-SWAP",
        timeframe="15",
        direction="LONG",
        formation_at=NOW,
        known_at=NOW,
        confirmed_at=None,
        invalidated_at=None,
        formation_valid=True,
        trade_eligible=False,
        status=ObjectStatus.KNOWN,
        source_rule_ids=("SRC-1",),
        technical_normalization_ids=("TN-1",),
        rejection_reasons=(),
        parent_object_ids=(),
        provenance="test",
        lifecycle=(),
    )
    return StrategyObjectSnapshot.from_source_object(
        obj,
        emitted_at=NOW,
        engine_version="stage23",
        engine_git_commit="abc123",
        dataset_id="dataset-1",
    )


def execution_snapshot():
    plan = SourceExecutionPlan(
        setup_id="setup-1",
        physical_idea_id="idea-1",
        branch=SetupBranch.OB_DIRECT_FIRST_TEST,
        direction=Direction.LONG,
        known_at=NOW,
        entry_options=(EntryOption(
            mode=EntryMode.OB_BOUNDARY_LIMIT,
            zone_low=81_000.0,
            zone_high=81_300.0,
            quote=81_300.0,
            exact_quote=True,
            source_rule_ids=("ENTRY-1",),
            note="boundary",
        ),),
        stop_options=(StopOption(
            mode=StopMode.OB_BEYOND_ZONE_EXTREME,
            relation="BELOW",
            anchor_price=81_000.0,
            stop_price=None,
            exact_price=False,
            source_rule_ids=("STOP-1",),
            note="unresolved buffer",
        ),),
        exit_policy=ExitPolicy(
            mode=ExitMode.FTA_FULL_OR_PARTIAL,
            primary_fraction=None,
            remainder_fraction=None,
            primary_target_price=82_400.0,
            primary_target_object_ids=("fta-1",),
            remainder_target_price=None,
            source_rule_ids=("FTA-1",),
            unresolved=("FTA_PARTIAL_REMAINDER_UNRESOLVED",),
        ),
        invalidation_rules=("invalidate-if-object-invalid",),
        unresolved=("STOP_BUFFER_UNRESOLVED",),
        source_rule_ids=("ENTRY-1", "STOP-1", "FTA-1"),
        technical_normalization_ids=(),
        trade_entry_allowed=False,
    )
    return SourceExecutionPlanSnapshot.from_plan(
        plan,
        emitted_at=NOW,
        engine_version="stage23",
        engine_git_commit="abc123",
        dataset_id="dataset-1",
    )


class IntegrationPublishTests(unittest.TestCase):
    def test_object_snapshot_publishes_exact_payload_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3")
            snapshot = object_snapshot()
            self.assertTrue(publish_strategy_object(outbox, snapshot, created_at=NOW))
            self.assertFalse(publish_strategy_object(outbox, snapshot, created_at=NOW))
            record = outbox.get(snapshot.event_id)
        self.assertEqual(record.event_type, snapshot.schema)
        self.assertEqual(record.payload, snapshot.to_dict())
        self.assertFalse(record.payload["trade_entry_allowed"])

    def test_execution_snapshot_publishes_all_alternatives_without_execution_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3")
            snapshot = execution_snapshot()
            self.assertTrue(publish_source_execution_plan(outbox, snapshot, created_at=NOW))
            record = outbox.get(snapshot.event_id)
        self.assertEqual(record.event_type, snapshot.schema)
        self.assertEqual(record.payload["entry_options"][0]["mode"], "OB_BOUNDARY_LIMIT")
        self.assertFalse(record.payload["trade_entry_allowed"])
        self.assertIn("STOP_BUFFER_UNRESOLVED", record.payload["unresolved"])


if __name__ == "__main__":
    unittest.main()
