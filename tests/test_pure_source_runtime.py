from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy import pure_source_runtime as runtime_module
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.profile import (
    PolicyClass,
    ProjectPolicyContaminationError,
    StrategyProfile,
    StrategyRuntimeConfig,
)
from crypto_bot.strategy.pure_source_runtime import PureSourceRuntime, RuntimeStage
from crypto_bot.strategy.source_execution_v2 import (
    EntryMode,
    EntryOption,
    ExecutionPlanAssessment,
    ExitMode,
    ExitPolicy,
    SourceExecutionPlan,
    StopMode,
    StopOption,
)
from crypto_bot.strategy.source_setup_v2 import (
    SetupAssemblyAssessment,
    SetupBranch,
    SourceSetupEvidence,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

UTC = timezone.utc
T0 = datetime(2026, 1, 1, tzinfo=UTC)
SYMBOL = "BTC-USDT-SWAP"


def t(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def source_object(
    object_type: SourceObjectType,
    *,
    minute: int,
    token: str,
    direction: Direction | None = Direction.LONG,
    timeframe: str | int = 60,
    parents: tuple[str, ...] = (),
    source_rule_ids: tuple[str, ...] = ("TEST_SOURCE_RULE",),
    technical_normalization_ids: tuple[str, ...] = (),
) -> CausalSourceObject:
    at = t(minute)
    return CausalSourceObject.formed(
        object_type=object_type,
        symbol=SYMBOL,
        timeframe=timeframe,
        direction=direction.value if direction is not None else None,
        formation_at=at,
        known_at=at,
        identity_parts={"fixture": token},
        source_rule_ids=source_rule_ids,
        technical_normalization_ids=technical_normalization_ids,
        parent_object_ids=parents,
        provenance="Stage-9 runtime fixture",
    )


def setup_evidence(runtime: PureSourceRuntime) -> SourceSetupEvidence:
    context = source_object(SourceObjectType.ORDER_BLOCK, minute=0, token="context")
    runtime.register_object(context, observed_at=t(0))
    physical = source_object(
        SourceObjectType.PHYSICAL_IDEA,
        minute=0,
        token="physical",
        parents=(context.object_id,),
    )
    setup = source_object(
        SourceObjectType.SETUP,
        minute=5,
        token="setup",
        parents=(physical.object_id, context.object_id),
    )
    evidence = SourceSetupEvidence(
        physical_idea=physical,
        setup=setup,
        branch=SetupBranch.OB_DIRECT_FIRST_TEST,
        direction=Direction.LONG,
        context_object_id=context.object_id,
        known_at=t(5),
        evidence_ids=(),
    )
    runtime.register_setup(evidence, observed_at=t(5))
    return evidence


def execution_plan(evidence: SourceSetupEvidence, *, unresolved: tuple[str, ...]) -> SourceExecutionPlan:
    return SourceExecutionPlan(
        setup_id=evidence.setup.object_id,
        physical_idea_id=evidence.physical_idea.object_id,
        branch=evidence.branch,
        direction=evidence.direction,
        known_at=evidence.known_at,
        entry_options=(
            EntryOption(
                EntryMode.OB_BOUNDARY_LIMIT,
                95.0,
                100.0,
                100.0,
                True,
                ("TEST_ENTRY_SOURCE",),
                "resolved fixture quote",
            ),
        ),
        stop_options=(
            StopOption(
                StopMode.OB_BEYOND_ZONE_EXTREME,
                "BELOW",
                95.0,
                94.0,
                True,
                ("TEST_STOP_SOURCE",),
                "resolved fixture stop",
            ),
        ),
        exit_policy=ExitPolicy(
            ExitMode.FTA_FULL_OR_PARTIAL,
            1.0,
            0.0,
            110.0,
            (),
            None,
            ("TEST_TARGET_SOURCE",),
        ),
        invalidation_rules=(),
        unresolved=unresolved,
        source_rule_ids=("TEST_ENTRY_SOURCE", "TEST_STOP_SOURCE", "TEST_TARGET_SOURCE"),
        trade_entry_allowed=False,
    )


class PureSourceRuntimeTests(unittest.TestCase):
    def test_runtime_is_pure_source_and_never_live(self):
        runtime = PureSourceRuntime(SYMBOL)
        obj = source_object(SourceObjectType.ORDER_BLOCK, minute=0, token="ob")
        runtime.register_object(obj)
        result = runtime.finish()
        self.assertEqual(result["strategy_profile"], StrategyProfile.PURE_SOURCE.value)
        self.assertEqual(result["runtime_version"], "PURE_SOURCE_STAGE9_V2")
        self.assertFalse(result["trade_entry_allowed"])
        self.assertFalse(result["legacy_runtime_adapter_enabled"])
        self.assertFalse(result["project_overlays_enabled"])
        stored = runtime.registry.get(obj.object_id)
        self.assertTrue(stored.formation_valid)
        self.assertFalse(stored.trade_eligible)

    def test_project_policy_cannot_be_applied(self):
        runtime = PureSourceRuntime(SYMBOL)
        with self.assertRaises(ProjectPolicyContaminationError):
            runtime.apply_policy("ANTI_SCALP", PolicyClass.PROJECT_POLICY)

    def test_project_like_policy_id_cannot_hide_in_source_evidence(self):
        runtime = PureSourceRuntime(SYMBOL)
        contaminated = source_object(
            SourceObjectType.ORDER_BLOCK,
            minute=0,
            token="contaminated",
            source_rule_ids=("PROJECT_CUSTOM_FILTER",),
        )
        with self.assertRaises(ValueError):
            runtime.register_object(contaminated, observed_at=t(0))
        self.assertEqual(len(runtime.registry), 0)

    def test_project_overlay_profile_cannot_construct_pure_runtime(self):
        cfg = StrategyRuntimeConfig(strategy_profile=StrategyProfile.PROJECT_OVERLAY)
        with self.assertRaises(ValueError):
            PureSourceRuntime(SYMBOL, config=cfg)

    def test_closed_candles_only_and_future_close_forbidden(self):
        runtime = PureSourceRuntime(SYMBOL)
        closed = Candle(t(0), t(1), 100, 102, 99, 101, True)
        runtime.observe_candles((closed,), decision_at=t(1))
        unfinished = Candle(t(1), t(2), 101, 103, 100, 102, False)
        with self.assertRaises(ValueError):
            runtime.observe_candles((unfinished,), decision_at=t(2))
        future_closed = Candle(t(2), t(3), 102, 104, 101, 103, True)
        with self.assertRaises(ValueError):
            runtime.observe_candles((future_closed,), decision_at=t(2))

    def test_future_lifecycle_mutation_cannot_be_ingested_early(self):
        runtime = PureSourceRuntime(SYMBOL)
        base = source_object(SourceObjectType.ORDER_BLOCK, minute=0, token="future-invalidation")
        mutated = base.invalidate(t(10), "LATER_INVALIDATION")
        with self.assertRaises(ValueError):
            runtime.register_object(mutated, observed_at=t(5))

    def test_stage7_setup_requires_registered_causal_parents(self):
        runtime = PureSourceRuntime(SYMBOL)
        context = source_object(SourceObjectType.ORDER_BLOCK, minute=0, token="missing-context")
        physical = source_object(
            SourceObjectType.PHYSICAL_IDEA,
            minute=0,
            token="physical-missing-parent",
            parents=(context.object_id,),
        )
        setup = source_object(
            SourceObjectType.SETUP,
            minute=5,
            token="setup-missing-parent",
            parents=(physical.object_id, context.object_id),
        )
        evidence = SourceSetupEvidence(
            physical,
            setup,
            SetupBranch.OB_DIRECT_FIRST_TEST,
            Direction.LONG,
            context.object_id,
            t(5),
            (),
        )
        with self.assertRaises(KeyError):
            runtime.register_setup(evidence, observed_at=t(5))

    def test_stage7_unknown_assessment_becomes_setup_blocker(self):
        runtime = PureSourceRuntime(SYMBOL)
        assessment = SetupAssemblyAssessment(EvidenceStatus.UNKNOWN, "WAIT_SOURCE_BRANCH_SELECTION")
        result = runtime.register_setup_assessment(assessment, observed_at=t(5))
        self.assertIsNone(result)
        self.assertEqual(len(runtime.blockers), 1)
        self.assertEqual(runtime.blockers[0].stage, RuntimeStage.SETUP)
        self.assertEqual(runtime.blockers[0].status, EvidenceStatus.UNKNOWN)
        self.assertEqual(runtime.blockers[0].reason, "WAIT_SOURCE_BRANCH_SELECTION")

    def test_malformed_stage7_pass_without_evidence_does_not_advance_runtime(self):
        runtime = PureSourceRuntime(SYMBOL)
        assessment = SetupAssemblyAssessment(EvidenceStatus.PASS, "BROKEN_PASS_CONTRACT")
        with self.assertRaises(ValueError):
            runtime.register_setup_assessment(assessment, observed_at=t(9))
        self.assertIsNone(runtime.decision_watermark)
        self.assertEqual(len(runtime.blockers), 0)

    def test_unresolved_stage8_plan_records_blocker_and_does_not_admit_setup(self):
        runtime = PureSourceRuntime(SYMBOL)
        evidence = setup_evidence(runtime)
        plan = execution_plan(evidence, unresolved=("WAIT_UNRESOLVED_STOP_GEOMETRY",))
        runtime.register_execution_plan(plan, observed_at=t(5))
        stored = runtime.registry.get(evidence.setup.object_id)
        self.assertFalse(stored.trade_eligible)
        self.assertFalse(runtime.trade_entry_allowed)
        self.assertEqual(runtime.blockers[0].stage, RuntimeStage.EXECUTION)
        self.assertEqual(runtime.blockers[0].status, EvidenceStatus.UNKNOWN)
        self.assertEqual(runtime.blockers[0].reason, "WAIT_UNRESOLVED_STOP_GEOMETRY")

    def test_malformed_stage8_pass_without_plan_does_not_advance_runtime(self):
        runtime = PureSourceRuntime(SYMBOL)
        evidence = setup_evidence(runtime)
        before = runtime.decision_watermark
        assessment = ExecutionPlanAssessment(EvidenceStatus.PASS, "BROKEN_PASS_CONTRACT")
        with self.assertRaises(ValueError):
            runtime.register_execution_assessment(
                assessment,
                observed_at=t(9),
                setup_id=evidence.setup.object_id,
            )
        self.assertEqual(runtime.decision_watermark, before)

    def test_nonpass_stage8_assessment_cannot_smuggle_plan(self):
        runtime = PureSourceRuntime(SYMBOL)
        evidence = setup_evidence(runtime)
        plan = execution_plan(evidence, unresolved=())
        assessment = ExecutionPlanAssessment(EvidenceStatus.FAIL, "BROKEN_FAIL_CONTRACT", plan)
        with self.assertRaises(ValueError):
            runtime.register_execution_assessment(
                assessment,
                observed_at=t(9),
                setup_id=evidence.setup.object_id,
            )
        self.assertEqual(runtime.decision_watermark, t(5))
        self.assertFalse(runtime.registry.get(evidence.setup.object_id).trade_eligible)

    def test_source_ready_is_separate_from_live_permission(self):
        runtime = PureSourceRuntime(SYMBOL)
        evidence = setup_evidence(runtime)
        plan = execution_plan(evidence, unresolved=())
        self.assertTrue(plan.execution_ready)
        runtime.register_execution_plan(plan, observed_at=t(5))
        stored = runtime.registry.get(evidence.setup.object_id)
        self.assertTrue(stored.trade_eligible)
        self.assertFalse(runtime.trade_entry_allowed)
        result = runtime.finish()
        self.assertIn(evidence.setup.object_id, result["source_ready_setup_ids"])
        self.assertFalse(result["trade_entry_allowed"])

    def test_old_adapter_advance_path_fails_loudly(self):
        runtime = PureSourceRuntime(SYMBOL)
        with self.assertRaises(RuntimeError):
            runtime.advance(60, 0)

    def test_canonical_runtime_has_no_legacy_or_portfolio_backend_import(self):
        source = inspect.getsource(runtime_module)
        self.assertNotIn("crypto_bot.strategy.source_engine", source)
        self.assertNotIn("crypto_bot.strategy.virtual_portfolio", source)
        self.assertNotIn("crypto_bot.data.bybit", source)
        self.assertNotIn("engine_factory", source)


if __name__ == "__main__":
    unittest.main()
