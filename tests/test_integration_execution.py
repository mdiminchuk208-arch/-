import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.integration.execution import SOURCE_EXECUTION_EVENT_SCHEMA, SourceExecutionPlanSnapshot
from crypto_bot.strategy.source_execution_v2 import (
    EntryMode,
    EntryOption,
    ExitMode,
    ExitPolicy,
    SourceExecutionPlan,
    StopMode,
    StopOption,
)
from crypto_bot.strategy.source_setup_v2 import SetupBranch


UTC = timezone.utc


def exit_policy(target=82_400.0, unresolved=()):
    return ExitPolicy(
        mode=ExitMode.FTA_FULL_OR_PARTIAL,
        primary_fraction=None,
        remainder_fraction=None,
        primary_target_price=target,
        primary_target_object_ids=("fta-1",),
        remainder_target_price=None,
        source_rule_ids=("FTA_TARGET_001",),
        unresolved=unresolved,
    )


def unresolved_plan():
    known = datetime(2026, 10, 28, 9, 15, tzinfo=UTC)
    return SourceExecutionPlan(
        setup_id="setup-1",
        physical_idea_id="idea-1",
        branch=SetupBranch.OB_DIRECT_FIRST_TEST,
        direction=Direction.LONG,
        known_at=known,
        entry_options=(
            EntryOption(
                mode=EntryMode.OB_BOUNDARY_LIMIT,
                zone_low=81_000.0,
                zone_high=81_300.0,
                quote=81_300.0,
                exact_quote=True,
                source_rule_ids=("OB_ENTRY_FIRST_VARIANT_001",),
                note="boundary",
            ),
            EntryOption(
                mode=EntryMode.OB_INSIDE_ZONE,
                zone_low=81_000.0,
                zone_high=81_300.0,
                quote=None,
                exact_quote=False,
                source_rule_ids=("OB_ENTRY_FIRST_VARIANT_001",),
                note="inside zone unresolved",
            ),
        ),
        stop_options=(
            StopOption(
                mode=StopMode.OB_BEYOND_ZONE_EXTREME,
                relation="BELOW",
                anchor_price=81_000.0,
                stop_price=None,
                exact_price=False,
                source_rule_ids=("OB_STOP_VARIANTS_001",),
                note="buffer unresolved",
            ),
        ),
        exit_policy=exit_policy(unresolved=("FTA_PARTIAL_REMAINDER_UNRESOLVED",)),
        invalidation_rules=("invalidate-if-source-object-invalid",),
        unresolved=("OB_ENTRY_BOUNDARY_VS_INSIDE_UNRESOLVED", "OB_STOP_VARIANT_AND_EXACT_BUFFER_UNRESOLVED"),
        source_rule_ids=("OB_ENTRY_FIRST_VARIANT_001", "OB_STOP_VARIANTS_001", "FTA_TARGET_001"),
        technical_normalization_ids=("TN_FTA_FIRST_ZONE_CONTACT",),
        trade_entry_allowed=False,
    )


def resolved_geometry_plan():
    plan = unresolved_plan()
    return replace(
        plan,
        entry_options=(plan.entry_options[0],),
        stop_options=(
            replace(plan.stop_options[0], stop_price=80_950.0, exact_price=True),
        ),
        exit_policy=exit_policy(unresolved=()),
        unresolved=(),
    )


class IntegrationExecutionTests(unittest.TestCase):
    def test_snapshot_preserves_all_source_alternatives_without_ranking(self):
        plan = unresolved_plan()
        snapshot = SourceExecutionPlanSnapshot.from_plan(
            plan,
            emitted_at=plan.known_at + timedelta(minutes=1),
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertEqual(snapshot.schema, SOURCE_EXECUTION_EVENT_SCHEMA)
        self.assertEqual([item.mode for item in snapshot.entry_options], [
            "OB_BOUNDARY_LIMIT",
            "OB_INSIDE_ZONE",
        ])
        self.assertEqual(snapshot.entry_options[0].quote, 81_300.0)
        self.assertIsNone(snapshot.entry_options[1].quote)
        self.assertFalse(snapshot.source_geometry_resolved)
        self.assertFalse(snapshot.trade_entry_allowed)
        self.assertIn("OB_ENTRY_BOUNDARY_VS_INSIDE_UNRESOLVED", snapshot.unresolved)

    def test_resolved_source_geometry_still_does_not_allow_financial_entry(self):
        plan = resolved_geometry_plan()
        self.assertTrue(plan.execution_ready)
        snapshot = SourceExecutionPlanSnapshot.from_plan(
            plan,
            emitted_at=plan.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertTrue(snapshot.source_geometry_resolved)
        self.assertFalse(snapshot.trade_entry_allowed)

    def test_same_plan_reemitted_later_is_idempotent(self):
        plan = unresolved_plan()
        left = SourceExecutionPlanSnapshot.from_plan(
            plan,
            emitted_at=plan.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        right = SourceExecutionPlanSnapshot.from_plan(
            plan,
            emitted_at=plan.known_at + timedelta(hours=1),
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertEqual(left.event_id, right.event_id)
        self.assertNotEqual(left.emitted_at, right.emitted_at)

    def test_changing_one_source_alternative_changes_identity(self):
        plan = unresolved_plan()
        changed = replace(
            plan,
            entry_options=(replace(plan.entry_options[0], quote=81_250.0), plan.entry_options[1]),
        )
        left = SourceExecutionPlanSnapshot.from_plan(
            plan,
            emitted_at=plan.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        right = SourceExecutionPlanSnapshot.from_plan(
            changed,
            emitted_at=changed.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        self.assertNotEqual(left.event_id, right.event_id)

    def test_direct_construction_cannot_flip_execution_permission(self):
        plan = unresolved_plan()
        snapshot = SourceExecutionPlanSnapshot.from_plan(
            plan,
            emitted_at=plan.known_at,
            engine_version="stage23",
            engine_git_commit="abc123",
            dataset_id="dataset-1",
        )
        with self.assertRaises(ValueError):
            replace(snapshot, trade_entry_allowed=True)

    def test_emitted_before_known_is_rejected(self):
        plan = unresolved_plan()
        with self.assertRaises(ValueError):
            SourceExecutionPlanSnapshot.from_plan(
                plan,
                emitted_at=plan.known_at - timedelta(seconds=1),
                engine_version="stage23",
                engine_git_commit="abc123",
                dataset_id="dataset-1",
            )


if __name__ == "__main__":
    unittest.main()
