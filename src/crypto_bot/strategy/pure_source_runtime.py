from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Sequence

from crypto_bot.common.models import Candle
from crypto_bot.strategy.causal_objects import (
    CausalObjectRegistry,
    CausalSourceObject,
    LifecycleEventKind,
    ObjectStatus,
    RejectionCategory,
    SourceObjectType,
    require_closed_candles,
)
from crypto_bot.strategy.profile import (
    PROJECT_POLICY_IDS,
    PURE_SOURCE_CONFIG,
    PolicyClass,
    StrategyProfile,
    StrategyRuntimeConfig,
)
from crypto_bot.strategy.source_execution_v2 import ExecutionPlanAssessment, SourceExecutionPlan
from crypto_bot.strategy.source_setup_v2 import SetupAssemblyAssessment, SourceSetupEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


class RuntimeStage(str, Enum):
    OBJECT = "OBJECT"
    SETUP = "SETUP"
    EXECUTION = "EXECUTION"


@dataclass(frozen=True)
class RuntimeBlocker:
    stage: RuntimeStage
    status: EvidenceStatus
    reason: str
    observed_at: datetime
    setup_id: str | None = None

    def __post_init__(self) -> None:
        _aware("blocker observed_at", self.observed_at)
        if self.status == EvidenceStatus.PASS:
            raise ValueError("PASS cannot be recorded as a runtime blocker")
        if not self.reason:
            raise ValueError("runtime blocker reason is required")


@dataclass
class PureSourceRuntime:
    """Canonical Stage-9 PURE_SOURCE runtime shell.

    The runtime consumes causal evidence produced by Stages 1-8. It does not
    infer SOURCE truth through historical/canonical adapters, does not select a
    branch by outcome, and never enables order execution. Object existence,
    setup assembly, SOURCE trade eligibility and live-order permission remain
    separate concepts.
    """

    symbol: str
    config: StrategyRuntimeConfig = PURE_SOURCE_CONFIG

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol is required")
        if self.config.strategy_profile != StrategyProfile.PURE_SOURCE:
            raise ValueError("PureSourceRuntime requires strategy_profile=PURE_SOURCE")
        self.config.__post_init__()
        self.registry = CausalObjectRegistry()
        self._setups: dict[str, SourceSetupEvidence] = {}
        self._execution_plans: dict[str, SourceExecutionPlan] = {}
        self._blockers: dict[tuple[str, str, str | None, datetime], RuntimeBlocker] = {}
        self._decision_watermark: datetime | None = None

    @property
    def trade_entry_allowed(self) -> bool:
        return False

    @property
    def decision_watermark(self) -> datetime | None:
        return self._decision_watermark

    @property
    def blockers(self) -> tuple[RuntimeBlocker, ...]:
        return tuple(
            sorted(
                self._blockers.values(),
                key=lambda item: (
                    item.observed_at,
                    item.stage.value,
                    item.setup_id or "",
                    item.reason,
                ),
            )
        )

    def apply_policy(self, policy_id: str, policy_class: PolicyClass) -> None:
        self._assert_policy_ids_clean((policy_id,))
        self.config = self.config.record_policy(policy_id, policy_class)

    def observe_candles(self, candles: Sequence[Candle], *, decision_at: datetime) -> None:
        """Advance only the causal clock; detectors stay in their Stage-2..8 modules."""
        _aware("decision_at", decision_at)
        require_closed_candles(candles, decision_at=decision_at)
        self._advance_watermark(decision_at)

    def register_object(
        self,
        obj: CausalSourceObject,
        *,
        observed_at: datetime | None = None,
    ) -> CausalSourceObject:
        """Persist or causally extend one Stage-2..6.5 market object.

        Existing history may only be extended by later lifecycle events. Earlier
        events, identity/provenance and SOURCE classifications are immutable.
        SETUP/PHYSICAL_IDEA objects must use the dedicated Stage-7 wiring path.
        """
        if obj.object_type in (SourceObjectType.SETUP, SourceObjectType.PHYSICAL_IDEA):
            raise ValueError("SETUP/PHYSICAL_IDEA objects must use register_setup")
        if obj.trade_eligible:
            raise ValueError("market objects cannot arrive pre-admitted")
        if any(event.kind == LifecycleEventKind.TRADE_ELIGIBILITY for event in obj.lifecycle):
            raise ValueError("market-object trade-eligibility lifecycle is owned by runtime/setup wiring")

        at = self._observation_time(observed_at, obj.known_at)
        self._validate_object(obj, at)
        self._assert_policy_ids_clean(obj.source_rule_ids)
        self._assert_policy_ids_clean(obj.technical_normalization_ids)

        try:
            existing = self.registry.get(obj.object_id)
        except KeyError:
            self.registry.add(obj)
        else:
            if existing != obj:
                self._validate_object_extension(existing, obj)
                self.registry.replace(obj)
        self._advance_watermark(at)
        return obj

    def register_setup_assessment(
        self,
        assessment: SetupAssemblyAssessment,
        *,
        observed_at: datetime,
    ) -> SourceSetupEvidence | None:
        """Preserve Stage-7 PASS/UNKNOWN/FAIL without manufacturing a setup."""
        _aware("setup assessment observed_at", observed_at)
        if assessment.status == EvidenceStatus.PASS:
            if assessment.evidence is None:
                raise ValueError("PASS setup assessment requires evidence")
            return self.register_setup(assessment.evidence, observed_at=observed_at)
        if assessment.evidence is not None:
            raise ValueError("non-PASS setup assessment cannot contain evidence")
        self.record_blocker(
            RuntimeStage.SETUP,
            assessment.status,
            assessment.reason,
            observed_at,
        )
        return None

    def register_setup(
        self,
        evidence: SourceSetupEvidence,
        *,
        observed_at: datetime | None = None,
    ) -> SourceSetupEvidence:
        """Wire a Stage-7 setup only after every causal parent is already registered."""
        at = self._observation_time(observed_at, evidence.known_at)
        if evidence.setup.object_type != SourceObjectType.SETUP:
            raise ValueError("Stage-7 setup evidence must contain a SETUP object")
        if evidence.physical_idea.object_type != SourceObjectType.PHYSICAL_IDEA:
            raise ValueError("Stage-7 setup evidence must contain a PHYSICAL_IDEA object")
        if evidence.setup.symbol != self.symbol or evidence.physical_idea.symbol != self.symbol:
            raise ValueError("setup symbol does not match runtime symbol")
        if evidence.setup.known_at != evidence.known_at:
            raise ValueError("setup known_at contract mismatch")
        if evidence.setup.direction != evidence.direction.value:
            raise ValueError("setup direction contract mismatch")
        if evidence.physical_idea.direction != evidence.direction.value:
            raise ValueError("physical idea direction contract mismatch")
        if evidence.setup.trade_eligible or evidence.physical_idea.trade_eligible:
            raise ValueError("Stage-7 objects cannot arrive pre-admitted")

        context = self._require_registered(evidence.context_object_id)
        self._assert_active_at(context, evidence.known_at, "setup context")
        if evidence.context_object_id not in evidence.physical_idea.parent_object_ids:
            raise ValueError("physical idea must reference Stage-7 context object")
        if evidence.context_object_id not in evidence.setup.parent_object_ids:
            raise ValueError("setup must reference Stage-7 context object")
        if evidence.physical_idea.object_id not in evidence.setup.parent_object_ids:
            raise ValueError("setup must reference its physical idea")

        if evidence.entry_poi_id is not None:
            entry_poi = self._require_registered(evidence.entry_poi_id)
            self._assert_active_at(entry_poi, evidence.known_at, "entry POI")
            if evidence.entry_poi_id not in evidence.setup.parent_object_ids:
                raise ValueError("setup must reference its entry POI")

        self._validate_object(evidence.physical_idea, at)
        self._assert_policy_ids_clean(evidence.physical_idea.source_rule_ids)
        self._assert_policy_ids_clean(evidence.physical_idea.technical_normalization_ids)
        for parent_id in evidence.physical_idea.parent_object_ids:
            self._require_registered(parent_id)
        self.registry.add(evidence.physical_idea)

        self._validate_object(evidence.setup, at)
        for parent_id in evidence.setup.parent_object_ids:
            self._require_registered(parent_id)
        self._assert_policy_ids_clean(evidence.setup.source_rule_ids)
        self._assert_policy_ids_clean(evidence.setup.technical_normalization_ids)
        self.registry.add(evidence.setup)

        existing = self._setups.get(evidence.setup.object_id)
        if existing is not None and existing != evidence:
            raise ValueError(f"setup id collision: {evidence.setup.object_id}")
        self._setups[evidence.setup.object_id] = evidence
        self._advance_watermark(at)
        return evidence

    def register_execution_assessment(
        self,
        assessment: ExecutionPlanAssessment,
        *,
        observed_at: datetime,
        setup_id: str | None = None,
    ) -> SourceExecutionPlan | None:
        """Preserve Stage-8 PASS/UNKNOWN/FAIL; malformed contracts fail loudly."""
        _aware("execution observed_at", observed_at)
        if assessment.status == EvidenceStatus.PASS:
            if assessment.plan is None:
                raise ValueError("PASS execution assessment requires plan")
            if setup_id is not None and assessment.plan.setup_id != setup_id:
                raise ValueError("execution assessment setup_id mismatch")
            return self.register_execution_plan(assessment.plan, observed_at=observed_at)
        if assessment.plan is not None:
            raise ValueError("non-PASS execution assessment cannot contain plan")
        self.record_blocker(
            RuntimeStage.EXECUTION,
            assessment.status,
            assessment.reason,
            observed_at,
            setup_id=setup_id,
        )
        return None

    def register_execution_plan(
        self,
        plan: SourceExecutionPlan,
        *,
        observed_at: datetime | None = None,
    ) -> SourceExecutionPlan:
        at = self._observation_time(observed_at, plan.known_at)
        if plan.trade_entry_allowed is not False:
            raise ValueError("Stage-8 plan cannot enable trade entry")
        if plan.known_at > at:
            raise ValueError("execution plan is not known at observed_at")
        self._assert_policy_ids_clean(plan.source_rule_ids)
        self._assert_policy_ids_clean(plan.technical_normalization_ids)
        for entry in plan.entry_options:
            self._assert_policy_ids_clean(entry.source_rule_ids)
        for stop in plan.stop_options:
            self._assert_policy_ids_clean(stop.source_rule_ids)
        self._assert_policy_ids_clean(plan.exit_policy.source_rule_ids)

        setup_evidence = self._setups.get(plan.setup_id)
        if setup_evidence is None:
            raise KeyError(f"Stage-8 plan references unregistered setup: {plan.setup_id}")
        if setup_evidence.physical_idea.object_id != plan.physical_idea_id:
            raise ValueError("execution plan physical idea mismatch")
        if setup_evidence.branch != plan.branch or setup_evidence.direction != plan.direction:
            raise ValueError("execution plan branch/direction mismatch")
        if setup_evidence.known_at != plan.known_at:
            raise ValueError("execution plan known_at must equal Stage-7 setup known_at")

        setup_obj = self.registry.get(plan.setup_id)
        self._assert_active_at(setup_obj, at, "execution setup")

        existing = self._execution_plans.get(plan.setup_id)
        if existing is not None and existing != plan:
            raise ValueError(f"execution plan changed for setup: {plan.setup_id}")
        self._execution_plans[plan.setup_id] = plan

        for reason in plan.unresolved:
            self.record_blocker(
                RuntimeStage.EXECUTION,
                EvidenceStatus.UNKNOWN,
                reason,
                at,
                setup_id=plan.setup_id,
            )

        setup_obj = self.registry.get(plan.setup_id)
        if plan.execution_ready and not setup_obj.trade_eligible:
            self.registry.replace(
                setup_obj.set_trade_eligible(
                    True,
                    at,
                    "SOURCE_STAGE8_EXECUTION_READY_NO_LIVE_PERMISSION",
                )
            )
        self._advance_watermark(at)
        return plan

    def record_blocker(
        self,
        stage: RuntimeStage,
        status: EvidenceStatus,
        reason: str,
        observed_at: datetime,
        *,
        setup_id: str | None = None,
    ) -> RuntimeBlocker:
        _aware("blocker observed_at", observed_at)
        if status == EvidenceStatus.PASS:
            raise ValueError("PASS cannot be recorded as a runtime blocker")
        if setup_id is not None and setup_id not in self._setups:
            raise KeyError(f"blocker references unregistered setup: {setup_id}")
        blocker = RuntimeBlocker(stage, status, reason, observed_at, setup_id)
        key = (stage.value, reason, setup_id, observed_at)
        self._blockers[key] = blocker
        self._advance_watermark(observed_at)
        return blocker

    def get_execution_plan(self, setup_id: str) -> SourceExecutionPlan:
        return self._execution_plans[setup_id]

    def finish(self) -> dict:
        ready_setup_ids = tuple(
            sorted(
                setup_id
                for setup_id in self._setups
                if self.registry.get(setup_id).trade_eligible
            )
        )
        blocker_rows = tuple(
            {
                "stage": blocker.stage.value,
                "status": blocker.status.value,
                "reason": blocker.reason,
                "observed_at": blocker.observed_at.isoformat(),
                "setup_id": blocker.setup_id,
            }
            for blocker in self.blockers
        )
        return {
            "strategy_profile": StrategyProfile.PURE_SOURCE.value,
            "runtime_version": "PURE_SOURCE_STAGE9_V2",
            "trade_entry_allowed": False,
            "legacy_runtime_adapter_enabled": False,
            "project_overlays_enabled": False,
            "causal_object_count": len(self.registry),
            "setup_count": len(self._setups),
            "execution_plan_count": len(self._execution_plans),
            "source_ready_setup_ids": ready_setup_ids,
            "decision_watermark": (
                self._decision_watermark.isoformat()
                if self._decision_watermark is not None
                else None
            ),
            "runtime_blockers": blocker_rows,
            "unresolved_blockers": blocker_rows,
        }

    def advance(self, *args: object, **kwargs: object) -> None:
        """Fail loudly if an old adapter-style caller reaches the canonical runtime."""
        del args, kwargs
        raise RuntimeError(
            "legacy runtime advance path is disabled; provide causal Stage-2..8 evidence explicitly"
        )

    def _validate_object(self, obj: CausalSourceObject, observed_at: datetime) -> None:
        if obj.symbol != self.symbol:
            raise ValueError("object symbol does not match runtime symbol")
        if obj.known_at > observed_at:
            raise ValueError("object is not known at observed_at")
        if obj.confirmed_at is not None and obj.confirmed_at > observed_at:
            raise ValueError("future confirmation is forbidden in PURE_SOURCE")
        if obj.invalidated_at is not None and obj.invalidated_at > observed_at:
            raise ValueError("future invalidation is forbidden in PURE_SOURCE")
        if any(event.at > observed_at for event in obj.lifecycle):
            raise ValueError("future lifecycle event is forbidden in PURE_SOURCE")
        self._validate_lifecycle_projection(obj)

    def _validate_lifecycle_projection(self, obj: CausalSourceObject) -> None:
        if not obj.lifecycle:
            raise ValueError("causal SOURCE object requires lifecycle provenance")
        status = obj.lifecycle[-1].status
        trade_eligible = obj.lifecycle[-1].trade_eligible
        formation_valid = True
        confirmed_at: datetime | None = None
        invalidated_at: datetime | None = None
        rejection_reasons: list[str] = []
        for event in obj.lifecycle:
            if event.kind == LifecycleEventKind.CONFIRMATION:
                confirmed_at = event.at
            elif event.kind == LifecycleEventKind.INVALIDATION:
                invalidated_at = event.at
            if event.kind == LifecycleEventKind.REJECTION and event.reason:
                rejection_reasons.append(event.reason)
                if event.reason.startswith(RejectionCategory.OBJECT_INVALID_SOURCE.value):
                    formation_valid = False
            elif event.kind in (LifecycleEventKind.INVALIDATION, LifecycleEventKind.CANCELLATION) and event.reason:
                rejection_reasons.append(event.reason)
        projected = (
            status,
            formation_valid,
            trade_eligible,
            confirmed_at,
            invalidated_at,
            tuple(rejection_reasons),
        )
        actual = (
            obj.status,
            obj.formation_valid,
            obj.trade_eligible,
            obj.confirmed_at,
            obj.invalidated_at,
            obj.rejection_reasons,
        )
        if projected != actual:
            raise ValueError("causal object top-level state does not match lifecycle history")

    def _validate_object_extension(
        self,
        existing: CausalSourceObject,
        new: CausalSourceObject,
    ) -> None:
        immutable_existing = (
            existing.object_id,
            existing.object_type,
            existing.symbol,
            existing.timeframe,
            existing.direction,
            existing.formation_at,
            existing.known_at,
            existing.source_rule_ids,
            existing.technical_normalization_ids,
            existing.parent_object_ids,
            existing.provenance,
        )
        immutable_new = (
            new.object_id,
            new.object_type,
            new.symbol,
            new.timeframe,
            new.direction,
            new.formation_at,
            new.known_at,
            new.source_rule_ids,
            new.technical_normalization_ids,
            new.parent_object_ids,
            new.provenance,
        )
        if immutable_existing != immutable_new:
            raise ValueError("causal object immutable identity/provenance changed")
        if len(new.lifecycle) < len(existing.lifecycle):
            raise ValueError("causal lifecycle cannot shrink")
        if new.lifecycle[: len(existing.lifecycle)] != existing.lifecycle:
            raise ValueError("causal lifecycle history cannot be rewritten")

    def _assert_active_at(self, obj: CausalSourceObject, at: datetime, label: str) -> None:
        state = obj.state_at(at)
        if (
            not state.formation_valid
            or state.invalidated_at is not None
            or state.status in (ObjectStatus.INVALIDATED, ObjectStatus.CANCELLED)
        ):
            raise ValueError(f"{label} is not source-active at decision time")

    def _assert_policy_ids_clean(self, policy_ids: Sequence[str]) -> None:
        contaminated = {
            policy_id
            for policy_id in policy_ids
            if (
                policy_id in PROJECT_POLICY_IDS
                or str(policy_id).upper().startswith("PROJECT_")
                or "PROJECT_POLICY" in str(policy_id).upper()
            )
        }
        if contaminated:
            joined = ",".join(sorted(contaminated))
            raise ValueError(f"PROJECT_POLICY ids are forbidden in PURE_SOURCE evidence: {joined}")

    def _require_registered(self, object_id: str) -> CausalSourceObject:
        try:
            return self.registry.get(object_id)
        except KeyError as exc:
            raise KeyError(f"causal parent is not registered: {object_id}") from exc

    def _observation_time(self, explicit: datetime | None, floor: datetime) -> datetime:
        _aware("observation floor", floor)
        if explicit is None:
            if self._decision_watermark is not None and self._decision_watermark >= floor:
                return self._decision_watermark
            return floor
        _aware("observed_at", explicit)
        if explicit < floor:
            raise ValueError("observed_at cannot precede evidence known_at")
        return explicit

    def _advance_watermark(self, at: datetime) -> None:
        _aware("runtime watermark", at)
        if self._decision_watermark is not None and at < self._decision_watermark:
            raise ValueError("PURE_SOURCE runtime decision watermark cannot move backward")
        self._decision_watermark = at


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
