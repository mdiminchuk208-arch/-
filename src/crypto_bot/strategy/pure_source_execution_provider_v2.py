from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime

from crypto_bot.strategy.pure_source_object_provider_v2 import SourceObjectReplayRun
from crypto_bot.strategy.pure_source_replay_v2 import (
    ReplayExecutionAssessment,
    ReplayFrame,
    ReplaySeries,
    run_pure_source_replay,
)
from crypto_bot.strategy.pure_source_setup_provider_v2 import (
    SetupReplayEvidenceBatch,
    build_source_setup_batch,
)
from crypto_bot.strategy.source_execution_v2 import (
    ExecutionPlanAssessment,
    SourcePoiTargetReference,
    plan_sfp_execution,
)
from crypto_bot.strategy.source_setup_v2 import SetupBranch
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

EXECUTION_PROVIDER_VERSION = "PURE_SOURCE_STAGE14_EXECUTION_V2"


@dataclass(frozen=True)
class ExecutionObservation:
    setup_id: str
    observed_at: datetime
    status: EvidenceStatus
    reason: str
    execution_ready: bool
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionReplayEvidenceBatch(SetupReplayEvidenceBatch):
    execution_observations: tuple[ExecutionObservation, ...] = ()


class SourceExecutionReplayProvider:
    provider_id = "PURE_SOURCE_EXECUTION"
    provider_version = EXECUTION_PROVIDER_VERSION

    def produce(self, frame: ReplayFrame) -> ExecutionReplayEvidenceBatch:
        return build_source_execution_batch(frame)


def build_source_execution_batch(frame: ReplayFrame) -> ExecutionReplayEvidenceBatch:
    """Capture source-permitted semantics; never guess missing execution inputs.

    Historical setup evidence remains historical. Current prospective setup
    status is available separately in the inherited setup_observations.
    """
    base = build_source_setup_batch(frame)
    sfps = {e.obj.object_id: e for e in base.sfps}
    imbalances = {e.obj.object_id: e for e in base.imbalances}
    assessments: list[ReplayExecutionAssessment] = []
    observations: list[ExecutionObservation] = []
    for assessment in base.setup_assessments:
        setup = assessment.evidence
        if setup is None:
            continue
        sfp = sfps.get(setup.context_object_id)
        poi = imbalances.get(setup.entry_poi_id)
        if (
            setup.branch != SetupBranch.SFP_LTF_BOS_NEW_POI
            or sfp is None
            or poi is None
        ):
            execution = ExecutionPlanAssessment(
                EvidenceStatus.UNKNOWN, "WAIT_SOURCE_TYPED_EXECUTION_PARENTS"
            )
        else:
            execution = plan_sfp_execution(
                setup,
                sfp,
                entry_poi=SourcePoiTargetReference(
                    poi.obj, poi.zone_low, poi.zone_high, "FVG"
                ),
                # Neither a period/normalization nor a quote/target is selected
                # from absent source evidence or future candles.
                atr=None,
                fta=None,
            )
        assessments.append(ReplayExecutionAssessment(execution, setup.setup.object_id))
        plan = execution.plan
        observations.append(
            ExecutionObservation(
                setup.setup.object_id,
                frame.decision_at,
                execution.status,
                execution.reason,
                plan.execution_ready if plan else False,
                plan.unresolved if plan else (execution.reason,),
            )
        )
    values = {field.name: getattr(base, field.name) for field in fields(base)}
    values["execution_assessments"] = tuple(assessments)
    return ExecutionReplayEvidenceBatch(
        **values, execution_observations=tuple(observations)
    )


def run_source_execution_replay(
    series: Sequence[ReplaySeries], *, through: datetime | None = None
) -> SourceObjectReplayRun:
    batches: list[ExecutionReplayEvidenceBatch] = []

    class Recorder(SourceExecutionReplayProvider):
        def produce(self, frame: ReplayFrame) -> ExecutionReplayEvidenceBatch:
            batch = super().produce(frame)
            batches.append(batch)
            return batch

    replay = run_pure_source_replay(series, Recorder(), through=through)
    return SourceObjectReplayRun(replay, tuple(batches))
