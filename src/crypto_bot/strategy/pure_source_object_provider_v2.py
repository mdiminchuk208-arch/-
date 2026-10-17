"""Stage 11: closed-prefix SOURCE object evidence, without trade selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from crypto_bot.strategy.causal_objects import require_closed_candles
from crypto_bot.strategy.pure_source_evidence_v2 import (
    build_structure_liquidity_snapshot,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    PureSourceReplayResult,
    ReplayEvidenceBatch,
    ReplayFrame,
    ReplaySeries,
    StructureLiquidityReplayProvider,
    run_pure_source_replay,
)
from crypto_bot.strategy.source_imb_ote_pd_v2 import (
    SourceImbalanceEvidence,
    detect_source_imbalance,
)
from crypto_bot.strategy.source_sfp_v2 import (
    SfpLiquidityReference,
    SourceSfpEvidence,
    apply_sfp_invalidation,
    detect_source_sfp,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EvidenceStatus,
    LiquidityLocation,
)

OBJECT_PROVIDER_VERSION = "PURE_SOURCE_STAGE11_OBJECTS_V2"

# These are missing SOURCE inputs, not failed objects or numeric admission rules.
# No quality/anchor/TF/selection proxy is fabricated from OHLC.
DEFERRED_SOURCE_INPUTS = (
    ("EQH_EQL", "WAIT_SUBSTRUCTURE_AND_REASONABLE_TILT_PROVENANCE", "SW6 p7-10"),
    (
        "OB",
        "WAIT_OB_QUALITATIVE_GEOMETRY_AND_CONTEXT_PROVENANCE",
        "Методичка p9-10; SW9 p2-3",
    ),
    ("BREAKER", "WAIT_SOURCE_VALID_OB_AND_BREAKER_CONFIRMATION", "SW9; Методичка"),
    ("RANGE", "WAIT_RANGE_ENDPOINT_AND_QUALITATIVE_CONFIRMATION", "SW10; Методичка"),
    ("STB_BTS", "WAIT_MANIPULATION_AND_FULL_ENGULF_PROVENANCE", "SW22 p1-3"),
    ("DEMAND_SUPPLY", "WAIT_LAST_MOVEMENT_SEGMENTATION_PROVENANCE", "SRC_DS_001"),
    (
        "OTE_PD",
        "WAIT_SOURCE_QUALIFIED_IMPULSE_OR_DEALING_RANGE_ANCHORS",
        "Методичка; SW8",
    ),
    (
        "LIQUIDITY_CONTEXT",
        "WAIT_MEANINGFUL_LIQUIDITY_CONTEXT_RESOLUTION",
        "User task section8: unresolved meaningful liquidity; Stage8 FTA input contract",
    ),
)


@dataclass(frozen=True)
class ObjectAssessment:
    family: str
    timeframe: str
    status: EvidenceStatus
    reason: str
    observed_at: datetime
    object_id: str | None = None
    parent_object_ids: tuple[str, ...] = ()
    source_reference: str = ""


@dataclass(frozen=True)
class ObjectReplayEvidenceBatch(ReplayEvidenceBatch):
    # The Stage-10 canonical serializer fingerprints inherited AND new fields.
    # Diagnostics are not smuggled into Stage-7 setup assessments/admission.
    object_assessments: tuple[ObjectAssessment, ...] = ()
    sfps: tuple[SourceSfpEvidence, ...] = ()
    imbalances: tuple[SourceImbalanceEvidence, ...] = ()


@dataclass(frozen=True)
class SourceObjectReplayRun:
    replay: PureSourceReplayResult
    evidence_batches: tuple[ObjectReplayEvidenceBatch, ...]

    def assessment_counts(self) -> dict[str, dict[str, int]]:
        """Counts of per-close observations, not unique objects or trades."""
        counts: dict[str, dict[str, int]] = {}
        for batch in self.evidence_batches:
            for item in batch.object_assessments:
                group = counts.setdefault(
                    item.family, {status.value: 0 for status in EvidenceStatus}
                )
                group[item.status.value] += 1
        return counts


class SourceObjectReplayProvider:
    """Stateless evidence production; no legacy engine, annotation guesses or orders."""

    provider_id = "PURE_SOURCE_OBJECTS"
    provider_version = OBJECT_PROVIDER_VERSION

    def produce(self, frame: ReplayFrame) -> ObjectReplayEvidenceBatch:
        return build_source_object_batch(frame)


def build_source_object_batch(frame: ReplayFrame) -> ObjectReplayEvidenceBatch:
    """Reconstruct visible formations/lifecycle solely from the supplied prefixes.

    All prior detected SFP/FVG objects remain in each batch, including invalidated
    SFPs. Stage2 supplies its latest structure snapshot; the Stage9 append-only
    registry retains every structure observed in earlier frames.
    Assessments describe newly closed windows only, so unchanged higher-TF
    prefixes do not create duplicate higher-TF observations at lower-TF closes.
    SFP formation uses its SOURCE next-open timestamp; closed-only transport
    observes that opening fact later, at the next candle's CLOSE. No past
    receipt or READY is inserted at its intrinsic earlier known_at.
    """
    for prefix in frame.series:
        require_closed_candles(prefix.candles, decision_at=frame.decision_at)
        expected_new = tuple(
            c for c in prefix.candles if c.close_time == frame.decision_at
        )
        if prefix.newly_closed != expected_new:
            raise ValueError(
                "newly_closed must match the decision-time closed prefix suffix"
            )
    objects = {
        obj.object_id: obj
        for obj in StructureLiquidityReplayProvider().produce(frame).objects
    }
    assessments: list[ObjectAssessment] = []
    sfps: dict[str, SourceSfpEvidence] = {}
    imbalances: dict[str, SourceImbalanceEvidence] = {}
    for prefix in frame.series:
        candles = prefix.candles
        if not candles:
            continue
        snapshot = build_structure_liquidity_snapshot(
            candles, symbol=frame.symbol, timeframe=prefix.timeframe
        )
        external = tuple(
            pool
            for pool in snapshot.liquidity
            if pool.location == LiquidityLocation.EXTERNAL
        )
        current = bool(prefix.newly_closed)

        for third_index in range(2, len(candles)):
            result = detect_source_imbalance(
                *candles[third_index - 2 : third_index + 1],
                symbol=frame.symbol,
                timeframe=prefix.timeframe,
            )
            obj = result.evidence.obj if result.evidence is not None else None
            if obj is not None:
                objects[obj.object_id] = obj
                imbalances[obj.object_id] = result.evidence
            if current and third_index == len(candles) - 1:
                assessments.append(
                    ObjectAssessment(
                        "IMB_FVG",
                        prefix.timeframe,
                        EvidenceStatus.PASS if result.valid else EvidenceStatus.FAIL,
                        result.reason,
                        frame.decision_at,
                        obj.object_id if obj else None,
                        source_reference="SW8 p1-3; Методичка p11",
                    )
                )

        for next_index in range(1, len(candles)):
            sweep, next_candle = candles[next_index - 1 : next_index + 1]
            parents = tuple(
                pool for pool in external if pool.obj.known_at <= sweep.open_time
            )
            for pool in parents:
                result = detect_source_sfp(
                    sweep,
                    next_candle,
                    SfpLiquidityReference.from_structural_liquidity(pool),
                    symbol=frame.symbol,
                    timeframe=prefix.timeframe,
                )
                evidence = result.evidence
                if evidence is not None:
                    # Each invalidation is appended only when the corresponding
                    # closed candle is in this prefix; formation remains valid.
                    for later in candles[next_index:]:
                        evidence = apply_sfp_invalidation(evidence, later)
                    objects[evidence.obj.object_id] = evidence.obj
                    sfps[evidence.obj.object_id] = evidence
                if current and next_index == len(candles) - 1:
                    assessments.append(
                        ObjectAssessment(
                            "SFP",
                            prefix.timeframe,
                            EvidenceStatus.PASS
                            if result.valid
                            else EvidenceStatus.FAIL,
                            result.reason,
                            frame.decision_at,
                            evidence.obj.object_id if evidence else None,
                            (pool.obj.object_id,),
                            "SW8 p5; SW12 p13",
                        )
                    )
            if current and next_index == len(candles) - 1 and not parents:
                assessments.append(
                    ObjectAssessment(
                        "SFP",
                        prefix.timeframe,
                        EvidenceStatus.UNKNOWN,
                        "WAIT_KNOWN_EXTERNAL_LIQUIDITY",
                        frame.decision_at,
                        source_reference="SW8 p5",
                    )
                )

        if current:
            if len(candles) < 3:
                assessments.append(
                    ObjectAssessment(
                        "IMB_FVG",
                        prefix.timeframe,
                        EvidenceStatus.UNKNOWN,
                        "WAIT_THREE_CLOSED_CANDLES",
                        frame.decision_at,
                        source_reference="SW8 p1-3; Методичка p11",
                    )
                )
            if len(candles) < 2:
                assessments.append(
                    ObjectAssessment(
                        "SFP",
                        prefix.timeframe,
                        EvidenceStatus.UNKNOWN,
                        "WAIT_CLOSED_NEXT_OPEN_OBSERVATION",
                        frame.decision_at,
                        source_reference="SW8 p5",
                    )
                )
            assessments.extend(
                ObjectAssessment(
                    family,
                    prefix.timeframe,
                    EvidenceStatus.UNKNOWN,
                    reason,
                    frame.decision_at,
                    source_reference=source,
                )
                for family, reason, source in DEFERRED_SOURCE_INPUTS
            )

    return ObjectReplayEvidenceBatch(
        objects=tuple(objects[key] for key in sorted(objects)),
        sfps=tuple(sfps[key] for key in sorted(sfps)),
        imbalances=tuple(imbalances[key] for key in sorted(imbalances)),
        object_assessments=tuple(
            sorted(
                assessments,
                key=lambda a: (
                    a.timeframe,
                    a.family,
                    a.parent_object_ids,
                    a.object_id or "",
                    a.reason,
                ),
            )
        ),
    )


def run_source_object_replay(
    series: Sequence[ReplaySeries],
    *,
    through: datetime | None = None,
) -> SourceObjectReplayRun:
    """Retain the complete evidence batches as well as Stage-10 hash receipts.

    A fresh recorder is allocated per run. Its history is output-only and is
    never passed to the stateless evidence computation or used for selection.
    """
    batches: list[ObjectReplayEvidenceBatch] = []

    class Recorder(SourceObjectReplayProvider):
        def produce(self, frame: ReplayFrame) -> ObjectReplayEvidenceBatch:
            batch = super().produce(frame)
            batches.append(batch)
            return batch

    replay = run_pure_source_replay(series, Recorder(), through=through)
    return SourceObjectReplayRun(replay, tuple(batches))
