"""Stage 13: causal SOURCE setup facts, distinct from entry permission."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta
from hashlib import sha256

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import (
    CausalSourceObject,
    ObjectStatus,
    require_closed_candles,
)
from crypto_bot.strategy.pure_source_evidence_v2 import (
    build_structure_liquidity_snapshot,
)
from crypto_bot.strategy.pure_source_mtf_v2 import (
    MtfReplayEvidenceBatch,
    compose_mtf_source_evidence,
)
from crypto_bot.strategy.pure_source_object_provider_v2 import SourceObjectReplayRun
from crypto_bot.strategy.pure_source_replay_v2 import (
    ReplayFrame,
    ReplaySeries,
    run_pure_source_replay,
)
from crypto_bot.strategy.source_ob_breaker_v2 import BosReference
from crypto_bot.strategy.source_setup_v2 import (
    SetupAssemblyAssessment,
    SetupBranch,
    assemble_sfp_ltf_bos_new_poi,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EvidenceStatus,
    bos_breaks_active_leg,
)

SETUP_PROVIDER_VERSION = "PURE_SOURCE_STAGE13_SETUPS_V2"


@dataclass(frozen=True)
class SourceBosEvent:
    timeframe: str
    reference: BosReference
    structure_parent_id: str
    trigger_open_time: datetime
    source_rule_ids: tuple[str, ...] = ("MS_BOS_CONTEXT_001",)
    technical_normalization_ids: tuple[str, ...] = (
        "TN_BOS_FIRST_STRUCTURAL_INVALIDATION",
    )


@dataclass(frozen=True)
class SetupObservation:
    branch: SetupBranch
    context_id: str | None
    refinement_timeframe: str | None
    observed_at: datetime
    status: EvidenceStatus
    reason: str
    setup_id: str | None = None


@dataclass(frozen=True)
class SetupReplayEvidenceBatch(MtfReplayEvidenceBatch):
    bos_events: tuple[SourceBosEvent, ...] = ()
    setup_observations: tuple[SetupObservation, ...] = ()


class SourceSetupReplayProvider:
    provider_id = "PURE_SOURCE_SETUPS"
    provider_version = SETUP_PROVIDER_VERSION

    def produce(self, frame: ReplayFrame) -> SetupReplayEvidenceBatch:
        return build_source_setup_batch(frame)


def source_structure_history(
    frame: ReplayFrame,
) -> tuple[tuple[CausalSourceObject, ...], tuple[SourceBosEvent, ...]]:
    """Append the first SOURCE body-break of each already-known structure.

    The existing Stage2 interleaved geometry determines the prior leg. A leg
    learned at this close cannot be broken retroactively by this same close.
    Once that structure identity is invalidated, repeated closes beyond its
    protected point are not new structural breaks. No trade/re-entry rule is
    inferred. CONF anchor selection is not invented here.
    """
    structures: dict[str, CausalSourceObject] = {}
    events: dict[str, SourceBosEvent] = {}
    for prefix in frame.series:
        require_closed_candles(prefix.candles, decision_at=frame.decision_at)
        for index, candle in enumerate(prefix.candles):
            prior = build_structure_liquidity_snapshot(
                prefix.candles[:index], symbol=frame.symbol, timeframe=prefix.timeframe
            )
            if (
                prior.structure_object is not None
                and prior.latest_formed_leg is not None
            ):
                obj = structures.setdefault(
                    prior.structure_object.object_id, prior.structure_object
                )
                if obj.invalidated_at is None and bos_breaks_active_leg(
                    candle, prior.latest_formed_leg
                ):
                    obj = obj.invalidate(candle.close_time, "SOURCE_MS_BOS_BODY_CLOSE")
                    structures[obj.object_id] = obj
                    direction = (
                        Direction.SHORT
                        if prior.latest_formed_leg.direction == "BULLISH"
                        else Direction.LONG
                    )
                    identity = (
                        prefix.timeframe,
                        obj.object_id,
                        candle.open_time.isoformat(),
                        candle.close_time.isoformat(),
                        candle.close,
                    )
                    event_id = (
                        "bos-"
                        + sha256(
                            json.dumps(
                                identity, separators=(",", ":"), allow_nan=False
                            ).encode()
                        ).hexdigest()[:32]
                    )
                    events[event_id] = SourceBosEvent(
                        prefix.timeframe,
                        BosReference(direction, candle.close_time, event_id),
                        obj.object_id,
                        candle.open_time,
                    )
            current = build_structure_liquidity_snapshot(
                prefix.candles[: index + 1],
                symbol=frame.symbol,
                timeframe=prefix.timeframe,
            )
            if current.structure_object is not None:
                new = current.structure_object
                if new.object_id not in structures:
                    # Formation geometry can first become knowable on a close
                    # already beyond its protected point. Retain that geometry
                    # as inactive; it cannot supply a retroactive BOS or a new
                    # BOS on the following repeated beyond-point close.
                    leg = current.latest_formed_leg
                    if leg is not None:
                        protected = next(
                            swing
                            for swing in current.swings
                            if swing.obj.object_id == leg.protected_swing_id
                        )
                        breached = any(
                            protected.obj.known_at <= bar.close_time
                            and bos_breaks_active_leg(bar, leg)
                            for bar in prefix.candles[: index + 1]
                        )
                        if breached:
                            # Observed now, never backdated before known_at.
                            # A reclaim does not silently reactivate this ID.
                            new = new.invalidate(
                                candle.close_time, "STRUCTURE_ALREADY_BROKEN_WHEN_KNOWN"
                            )
                    structures[new.object_id] = new
    return tuple(structures[key] for key in sorted(structures)), tuple(
        events[key] for key in sorted(events)
    )


def _active(obj: CausalSourceObject, at: datetime) -> bool:
    if obj.known_at > at:
        return False
    state = obj.state_at(at)
    return state.formation_valid and state.status not in (
        ObjectStatus.INVALIDATED,
        ObjectStatus.CANCELLED,
    )


def _data_available(frame: ReplayFrame, timeframe: str, at: datetime) -> bool:
    prefix = frame.series_for(timeframe)
    visible = tuple(c for c in prefix.candles if c.close_time <= at)
    return bool(
        visible
        and visible[-1].close_time + timedelta(milliseconds=prefix.interval_ms) > at
    )


def build_source_setup_batch(frame: ReplayFrame) -> SetupReplayEvidenceBatch:
    base = compose_mtf_source_evidence(frame)
    structures, events = source_structure_history(frame)
    objects = {obj.object_id: obj for obj in base.objects}
    objects.update({obj.object_id: obj for obj in structures})
    observations: list[SetupObservation] = []
    accepted: dict[str, SetupAssemblyAssessment] = {}

    for sfp in base.sfps:
        context_tf = sfp.obj.timeframe
        context_prefix = frame.series_for(context_tf)
        first_observation = sfp.confirmation_open_time + timedelta(
            milliseconds=context_prefix.interval_ms
        )
        relations = tuple(
            r for r in base.refinement_candidates if r.context_timeframe == context_tf
        )
        if not relations:
            observations.append(
                SetupObservation(
                    SetupBranch.SFP_LTF_BOS_NEW_POI,
                    sfp.obj.object_id,
                    None,
                    frame.decision_at,
                    EvidenceStatus.UNKNOWN,
                    "WAIT_SOURCE_LOWER_TIMEFRAME_EVIDENCE",
                )
            )
        for relation in relations:
            source_events = tuple(
                e
                for e in events
                if e.timeframe == relation.refinement_timeframe
                and e.reference.direction == sfp.direction
                and e.reference.known_at >= sfp.obj.known_at
            )
            if not source_events:
                observations.append(
                    SetupObservation(
                        SetupBranch.SFP_LTF_BOS_NEW_POI,
                        sfp.obj.object_id,
                        relation.refinement_timeframe,
                        frame.decision_at,
                        EvidenceStatus.UNKNOWN,
                        "WAIT_DIRECTIONAL_LTF_BOS",
                    )
                )
            for event in source_events:
                candidates = tuple(
                    e.obj
                    for e in base.imbalances
                    if e.obj.timeframe == relation.refinement_timeframe
                )
                # Evaluate each information arrival, retaining earlier unique
                # assemblies even if a later alternative makes selection UNKNOWN.
                times = {
                    max(first_observation, event.reference.known_at, poi.known_at)
                    for poi in candidates
                    if poi.known_at >= event.reference.known_at
                }
                times.add(frame.decision_at)
                for observed in sorted(t for t in times if t <= frame.decision_at):
                    if not _active(sfp.obj, observed):
                        assessment = SetupAssemblyAssessment(
                            EvidenceStatus.FAIL,
                            "SFP_CONTEXT_INVALIDATED_BEFORE_OBSERVATION",
                        )
                    elif not _data_available(
                        frame, context_tf, observed
                    ) or not _data_available(
                        frame, relation.refinement_timeframe, observed
                    ):
                        assessment = SetupAssemblyAssessment(
                            EvidenceStatus.UNKNOWN, "WAIT_SOURCE_CLOSED_CONTEXT_DATA"
                        )
                    else:
                        assessment = assemble_sfp_ltf_bos_new_poi(
                            sfp,
                            pair=relation.pair,
                            ltf_bos=event.reference,
                            entry_poi_candidates=candidates,
                            decision_at=observed,
                        )
                    if assessment.evidence is not None:
                        setup_id = assessment.evidence.setup.object_id
                        prior = accepted.get(setup_id)
                        if prior is not None and prior != assessment:
                            raise ValueError(
                                "conflicting SOURCE setup evidence for stable identity"
                            )
                        accepted[setup_id] = assessment
                    if observed == frame.decision_at:
                        observations.append(
                            SetupObservation(
                                SetupBranch.SFP_LTF_BOS_NEW_POI,
                                sfp.obj.object_id,
                                relation.refinement_timeframe,
                                observed,
                                assessment.status,
                                assessment.reason,
                                assessment.evidence.setup.object_id
                                if assessment.evidence
                                else None,
                            )
                        )

    if not base.sfps:
        observations.append(
            SetupObservation(
                SetupBranch.SFP_LTF_BOS_NEW_POI,
                None,
                None,
                frame.decision_at,
                EvidenceStatus.UNKNOWN,
                "WAIT_SOURCE_VALID_SFP_OBJECT",
            )
        )
    # Those branches require qualitatively qualified objects/chain inputs that
    # this data-only provider does not possess. Absence is not a failed object.
    observations.extend(
        SetupObservation(
            branch,
            None,
            None,
            frame.decision_at,
            EvidenceStatus.UNKNOWN,
            "WAIT_SOURCE_QUALIFIED_PARENT_AND_CHAIN:" + branch.value,
        )
        for branch in SetupBranch
        if branch != SetupBranch.SFP_LTF_BOS_NEW_POI
    )
    unknowns = tuple(
        SetupAssemblyAssessment(row.status, row.reason)
        for row in observations
        if row.status != EvidenceStatus.PASS
    )
    values = {field.name: getattr(base, field.name) for field in fields(base)}
    values["objects"] = tuple(objects[key] for key in sorted(objects))
    values["timeframe_views"] = tuple(
        replace(
            view,
            object_ids=tuple(
                obj.object_id
                for obj in values["objects"]
                if obj.timeframe == view.timeframe
            ),
        )
        for view in base.timeframe_views
    )
    values["setup_assessments"] = (
        tuple(accepted[key] for key in sorted(accepted)) + unknowns
    )
    return SetupReplayEvidenceBatch(
        **values,
        bos_events=events,
        setup_observations=tuple(
            sorted(
                observations,
                key=lambda row: (
                    row.branch.value,
                    row.context_id or "",
                    row.refinement_timeframe or "",
                    row.reason,
                    row.setup_id or "",
                ),
            )
        ),
    )


def run_source_setup_replay(
    series: Sequence[ReplaySeries], *, through: datetime | None = None
) -> SourceObjectReplayRun:
    batches: list[SetupReplayEvidenceBatch] = []

    class Recorder(SourceSetupReplayProvider):
        def produce(self, frame: ReplayFrame) -> SetupReplayEvidenceBatch:
            batch = super().produce(frame)
            batches.append(batch)
            return batch

    replay = run_pure_source_replay(series, Recorder(), through=through)
    return SourceObjectReplayRun(replay, tuple(batches))
