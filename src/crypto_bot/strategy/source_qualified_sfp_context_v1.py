"""Bound SFP trade-context facts, separate from pattern and trade readiness."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import pairwise

from crypto_bot.strategy.causal_objects import CausalSourceObject, HistoricalState
from crypto_bot.strategy.pure_source_object_provider_v2 import build_source_object_batch
from crypto_bot.strategy.pure_source_replay_v2 import ReplayFrame
from crypto_bot.strategy.source_claim_binding_v1 import (
    BoundClaimAssessment,
    BoundSourceClaim,
    SourceClaimJournal,
    _validate_frame,
    claim_context_sha256,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import QualitativeScope
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

QUALIFIED_SFP_CONTEXT_VERSION = "PURE_SOURCE_STAGE22_QUALIFIED_SFP_CONTEXT_V1"


@dataclass(frozen=True)
class QualifiedSfpContextAssessment:
    transport_object: CausalSourceObject
    transport_state: HistoricalState
    parent_liquidity_id: str
    timeframe: str
    subject_object_ids: tuple[str, ...]
    observation_start_at: datetime
    observation_end_at: datetime
    transport_closed_observable_at: datetime
    context: BoundClaimAssessment
    context_known_at: datetime | None
    supporting_claims: tuple[BoundSourceClaim, ...]
    scope: QualitativeScope = field(default=QualitativeScope.TRADE_CONTEXT, init=False)
    priority1_pattern_status: EvidenceStatus = field(
        default=EvidenceStatus.UNKNOWN, init=False
    )
    execution_ready: bool = False
    trade_entry_allowed: bool = False

    def __post_init__(self) -> None:
        # Domain validation stays stable across dataclasses.replace versions.
        if self.execution_ready is not False or self.trade_entry_allowed is not False:
            raise ValueError(
                "qualified SFP context cannot enable execution or trade entry"
            )


def assess_bound_sfp_context(
    journal: SourceClaimJournal,
    frame: ReplayFrame,
    *,
    sfp_object_id: str,
    observation_start_at: datetime,
    observation_end_at: datetime,
) -> QualifiedSfpContextAssessment:
    """Assess context for one actual SW8 next-open transport without promoting it.

    Methodichka's three/optional-fourth pattern qualification is not inferred
    from the SW8 transport. A context PASS is neither pattern PASS nor admission.
    """
    _validate_frame(frame)
    if (journal.exchange, journal.symbol) != (frame.exchange, frame.symbol):
        raise ValueError("journal market identity mismatch")
    for at in (observation_start_at, observation_end_at):
        if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("aware observation window required")
    for prefix in frame.series:
        duration = timedelta(milliseconds=prefix.interval_ms)
        if any(
            c.close_time - c.open_time != duration or c.low <= 0 for c in prefix.candles
        ) or any(a.close_time != b.open_time for a, b in pairwise(prefix.candles)):
            raise ValueError("consumer requires continuous positive closed market data")
    batch = build_source_object_batch(frame)
    matches = tuple(s for s in batch.sfps if s.obj.object_id == sfp_object_id)
    if len(matches) != 1:
        raise ValueError(
            "context subject must be an actual closed-prefix SFP transport"
        )
    sfp = matches[0]
    prefix = frame.series_for(sfp.obj.timeframe)
    confirmation = next(
        c for c in prefix.candles if c.open_time == sfp.confirmation_open_time
    )
    if (
        observation_start_at > sfp.sweep_open_time
        or observation_end_at < confirmation.close_time
        or observation_start_at not in {c.open_time for c in prefix.candles}
        or observation_end_at not in {c.close_time for c in prefix.candles}
        or observation_end_at > frame.decision_at
    ):
        raise ValueError(
            "context window must cover closed sweep and confirmation transport"
        )
    subjects = tuple(sorted((sfp.obj.object_id, sfp.parent_liquidity_id)))
    context = journal.assess(
        semantic_id="SFP_LIQUIDITY_CONTEXT",
        scope=QualitativeScope.TRADE_CONTEXT,
        subject_object_ids=subjects,
        timeframe=sfp.obj.timeframe,
        observation_start_at=observation_start_at,
        observation_end_at=observation_end_at,
        decision_at=frame.decision_at,
    )
    receipts = {r.claim.evidence_id: r for r in journal.records}
    supporting = tuple(receipts[identity] for identity in context.supporting_claim_ids)
    for receipt in supporting:
        if (
            claim_context_sha256(receipt.claim, frame, batch.objects)
            != receipt.context_sha256
        ):
            raise ValueError("consumer data differs from bound SFP context")
    known = (
        max(confirmation.close_time, context.evidence.known_at)
        if context.evidence.known_at is not None
        else None
    )
    return QualifiedSfpContextAssessment(
        sfp.obj,
        sfp.obj.state_at(frame.decision_at),
        sfp.parent_liquidity_id,
        sfp.obj.timeframe,
        subjects,
        observation_start_at,
        observation_end_at,
        confirmation.close_time,
        context,
        known,
        supporting,
    )
