"""Provenance-retaining EQH/EQL consumer; never trading admission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from math import isfinite

from crypto_bot.strategy.pure_source_replay_v2 import ReplayFrame, _hash_payload
from crypto_bot.strategy.source_claim_binding_v1 import (
    BoundClaimAssessment,
    BoundSourceClaim,
    SourceClaimJournal,
    _validate_frame,
    claim_context_sha256,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import QualitativeScope
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EqualLiquidityEvidence,
    EqualLiquidityKind,
    EvidenceStatus,
    assess_equal_liquidity,
    confirmed_source_swings,
)

QUALIFIED_LIQUIDITY_VERSION = "PURE_SOURCE_STAGE21_QUALIFIED_LIQUIDITY_V1"


@dataclass(frozen=True)
class BoundLiquidityFact:
    semantic_id: str
    scope: QualitativeScope
    timeframe: str
    subject_object_ids: tuple[str, ...]
    observation_start_at: datetime
    observation_end_at: datetime
    assessment: BoundClaimAssessment
    supporting_claims: tuple[BoundSourceClaim, ...]


@dataclass(frozen=True)
class QualifiedEqualLiquidityAssessment:
    evidence: EqualLiquidityEvidence
    geometry_known_at: datetime
    known_at: datetime | None
    facts: tuple[BoundLiquidityFact, ...]
    trade_entry_allowed: bool = False

    def __post_init__(self) -> None:
        if self.trade_entry_allowed is not False:
            raise ValueError("qualified liquidity cannot enable trade entry")


def assess_bound_equal_liquidity(
    journal: SourceClaimJournal,
    frame: ReplayFrame,
    *,
    timeframe: str,
    left_swing_id: str,
    right_swing_id: str,
    kind: EqualLiquidityKind,
    observation_start_at: datetime,
    observation_end_at: datetime,
) -> QualifiedEqualLiquidityAssessment:
    """Resolve exact typed facts internally and retain the complete bound receipts.

    The caller identifies a candidate pair and annotation window, not a winner.
    Swings and their geometry are reconstructed from this actual closed prefix;
    arbitrary legacy evidence IDs/booleans cannot be supplied to this adapter.
    """
    _validate_frame(frame)
    if not isinstance(kind, EqualLiquidityKind):
        raise TypeError("typed equal liquidity kind required")
    if (journal.exchange, journal.symbol) != (frame.exchange, frame.symbol):
        raise ValueError("journal market identity mismatch")
    for at in (observation_start_at, observation_end_at):
        if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("aware observation window required")
    prefix = frame.series_for(timeframe)
    interval = timedelta(milliseconds=prefix.interval_ms)
    if any(c.close_time - c.open_time != interval for c in prefix.candles) or any(
        a.close_time != b.open_time for a, b in pairwise(prefix.candles)
    ):
        raise ValueError("consumer prefix must have authentic continuous intervals")
    if any(
        not all(isfinite(v) and v > 0 for v in (c.open, c.high, c.low, c.close))
        or not c.low <= min(c.open, c.close) <= max(c.open, c.close) <= c.high
        for c in prefix.candles
    ):
        raise ValueError("consumer prefix has invalid OHLC data")
    swings = confirmed_source_swings(
        prefix.candles, symbol=frame.symbol, timeframe=timeframe
    )
    by_id = {s.obj.object_id: s for s in swings}
    if left_swing_id not in by_id or right_swing_id not in by_id:
        raise ValueError("candidate must reference actual closed-prefix swings")
    left, right = by_id[left_swing_id], by_id[right_swing_id]
    earliest = min(prefix.candles[s.center_index - 1].open_time for s in (left, right))
    geometry_known = max(left.obj.known_at, right.obj.known_at)
    if (
        observation_start_at > earliest
        or observation_end_at < geometry_known
        or observation_start_at not in {c.open_time for c in prefix.candles}
        or observation_end_at not in {c.close_time for c in prefix.candles}
        or observation_end_at > frame.decision_at
    ):
        raise ValueError("observation window must cover both closed swing footprints")
    subjects = tuple(sorted({left_swing_id, right_swing_id}))
    if len(subjects) != 2:
        raise ValueError("two distinct swing identities required")
    # Invalid side/order/directional geometry requires no qualitative inference.
    geometry = assess_equal_liquidity(
        left,
        right,
        kind=kind,
        substructure_pair_confirmed=None,
        reasonable_tilt_confirmed=None,
    )
    if geometry.status == EvidenceStatus.FAIL:
        return QualifiedEqualLiquidityAssessment(
            geometry, geometry_known, geometry_known, ()
        )

    objects = tuple(s.obj for s in swings)
    receipts = {r.claim.evidence_id: r for r in journal.records}

    def resolve(semantic: str) -> BoundLiquidityFact:
        assessment = journal.assess(
            semantic_id=semantic,
            scope=QualitativeScope.OBJECT_FORMATION,
            subject_object_ids=subjects,
            timeframe=timeframe,
            observation_start_at=observation_start_at,
            observation_end_at=observation_end_at,
            decision_at=frame.decision_at,
        )
        supporting = tuple(
            receipts[identity] for identity in assessment.supporting_claim_ids
        )
        for receipt in supporting:
            if (
                claim_context_sha256(receipt.claim, frame, objects)
                != receipt.context_sha256
            ):
                raise ValueError("consumer data differs from bound annotation context")
        return BoundLiquidityFact(
            semantic,
            QualitativeScope.OBJECT_FORMATION,
            timeframe,
            subjects,
            observation_start_at,
            observation_end_at,
            assessment,
            supporting,
        )

    substructure = resolve("EQH_EQL_SUBSTRUCTURE_PAIR")
    # Flat geometry has no tilt judgment to resolve. No numeric tolerance is used.
    facts = (
        (substructure,)
        if left.price == right.price
        else (
            substructure,
            resolve("EQH_EQL_REASONABLE_TILT"),
        )
    )
    values = tuple(_confirmed(f.assessment) for f in facts)
    fact_ids = tuple(
        sorted(
            f.assessment.evidence.evidence_id
            for f in facts
            if f.assessment.evidence.evidence_id
        )
    )
    provenance_id = "equal-qual-" + _hash_payload(fact_ids) if fact_ids else None
    result = assess_equal_liquidity(
        left,
        right,
        kind=kind,
        substructure_pair_confirmed=values[0],
        reasonable_tilt_confirmed=values[1] if len(values) == 2 else None,
        qualitative_evidence_id=provenance_id,
    )
    # A timestamp is exposed only for a resolved assessment. It can never precede
    # either swing or any available qualitative dependency considered here.
    available = tuple(
        f.assessment.evidence.known_at
        for f in facts
        if f.assessment.evidence.known_at is not None
    )
    known = (
        max((geometry_known, *available))
        if result.status != EvidenceStatus.UNKNOWN
        else None
    )
    return QualifiedEqualLiquidityAssessment(result, geometry_known, known, facts)


def _confirmed(assessment: BoundClaimAssessment) -> bool | None:
    if assessment.evidence.status == EvidenceStatus.UNKNOWN:
        return None
    return assessment.evidence.status == EvidenceStatus.PASS
