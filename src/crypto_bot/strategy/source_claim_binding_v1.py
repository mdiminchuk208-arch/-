"""Causal admission of qualitative evidence, never trading admission."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from itertools import pairwise

from crypto_bot.common.models import Candle
from crypto_bot.strategy.causal_objects import (
    CausalSourceObject,
    require_closed_candles,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    ReplayFrame,
    _hash_payload,
    _parse_fixed_interval_ms,
)
from crypto_bot.strategy.source_ob_breaker_v2 import QualitativeEvidence
from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    QualitativeScope,
    QualitativeSemanticCatalog,
    SourceQualitativeClaim,
    validate_claim_against_catalog,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

CLAIM_BINDING_VERSION = "PURE_SOURCE_STAGE23_1_CLAIM_BINDING_V2"


def _utc(at: datetime) -> str:
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("aware datetime required")
    return at.astimezone(UTC).isoformat()


def source_candle_subject_id(
    exchange: str, symbol: str, timeframe: str, candle: Candle
) -> str:
    return "candle-" + _hash_payload(
        (
            exchange,
            symbol,
            timeframe,
            _utc(candle.open_time),
            _utc(candle.close_time),
            candle.open,
            candle.high,
            candle.low,
            candle.close,
        )
    )


def _validate_frame(frame: ReplayFrame) -> None:
    _utc(frame.decision_at)
    if len({p.timeframe for p in frame.series}) != len(frame.series):
        raise ValueError("duplicate timeframe prefix")
    for prefix in frame.series:
        if _parse_fixed_interval_ms(prefix.timeframe) != prefix.interval_ms:
            raise ValueError("declared timeframe duration mismatch")
        require_closed_candles(prefix.candles, decision_at=frame.decision_at)
        if any(c.is_closed is not True for c in prefix.candles):
            raise ValueError("unfinished evidence candle")
        expected = tuple(c for c in prefix.candles if c.close_time == frame.decision_at)
        if tuple(prefix.newly_closed) != expected:
            raise ValueError(
                "newly_closed must be the exact decision-time prefix suffix"
            )
    if not any(p.newly_closed for p in frame.series):
        raise ValueError("replay decision must observe a closed candle")


def claim_context_sha256(
    claim: SourceQualitativeClaim,
    frame: ReplayFrame,
    objects: Sequence[CausalSourceObject],
) -> str:
    """Bind an annotation's declared past window and actual causal subject IDs.

    Object geometry/truth remains the responsibility of the canonical object
    producer. Later lifecycle events are excluded from the declared-time view.
    """
    _validate_frame(frame)
    if claim.symbol != frame.symbol or claim.known_at > frame.decision_at:
        raise ValueError("claim symbol/future availability mismatch")
    prefix = frame.series_for(claim.timeframe)
    window = tuple(
        c
        for c in prefix.candles
        if c.open_time >= claim.observation_start_at
        and c.close_time <= claim.observation_end_at
    )
    if (
        not window
        or window[0].open_time != claim.observation_start_at
        or window[-1].close_time != claim.observation_end_at
    ):
        raise ValueError("claim window lacks exact closed-data coverage")
    interval = timedelta(milliseconds=prefix.interval_ms)
    if prefix.interval_ms <= 0 or any(
        c.close_time - c.open_time != interval for c in window
    ):
        raise ValueError("claim window duration mismatch")
    if any(right.open_time != left.close_time for left, right in pairwise(window)):
        raise ValueError("claim window contains gaps or overlap")
    object_map = {obj.object_id: obj for obj in objects}
    if len(object_map) != len(objects):
        raise ValueError("duplicate subject object identities")
    candle_ids = {
        source_candle_subject_id(frame.exchange, frame.symbol, claim.timeframe, c)
        for c in window
    }
    subjects = []
    ancestry = {}

    def visit(obj, visiting):
        if obj.object_id in visiting:
            raise ValueError("cyclic causal parent chain")
        if obj.object_id in ancestry:
            return
        if (
            obj.symbol != frame.symbol
            or obj.known_at > claim.known_at
            or any(event.at > frame.decision_at for event in obj.lifecycle)
            or any(
                at is not None and at > frame.decision_at
                for at in (obj.confirmed_at, obj.invalidated_at)
            )
        ):
            raise ValueError("subject symbol/future lifecycle mismatch")
        frame.series_for(obj.timeframe)
        for identity in obj.parent_object_ids:
            parent = object_map.get(identity)
            if parent is None or parent.known_at > obj.known_at:
                raise ValueError("missing/future causal parent")
            visit(parent, visiting | {obj.object_id})
        state = obj.state_at(claim.known_at)
        ancestry[obj.object_id] = {
            "object_id": obj.object_id,
            "symbol": obj.symbol,
            "timeframe": obj.timeframe,
            "formation_at": _utc(obj.formation_at),
            "known_at": _utc(obj.known_at),
            "snapshot_at": _utc(state.at),
            "status": state.status.value,
            "formation_valid": state.formation_valid,
            "trade_eligible": state.trade_eligible,
            "rejection_reasons": state.rejection_reasons,
            "causal_lifecycle": [
                {
                    "kind": event.kind.value,
                    "at": _utc(event.at),
                    "status": event.status.value,
                    "trade_eligible": event.trade_eligible,
                    "reason": event.reason,
                }
                for event in obj.lifecycle
                if event.at <= claim.known_at
            ],
            "confirmed_at": _utc(state.confirmed_at) if state.confirmed_at else None,
            "invalidated_at": _utc(state.invalidated_at)
            if state.invalidated_at
            else None,
            "parents": sorted(obj.parent_object_ids),
            "object_type": obj.object_type.value,
            "direction": obj.direction,
            "source_rule_ids": obj.source_rule_ids,
            "technical_normalization_ids": obj.technical_normalization_ids,
            "provenance": obj.provenance,
        }

    has_target_subject = False
    for identity in claim.subject_object_ids:
        if identity in candle_ids:
            subjects.append({"candle_id": identity})
            has_target_subject = True
            continue
        obj = object_map.get(identity)
        if obj is None:
            raise ValueError("claim references an unknown subject")
        visit(obj, set())
        subjects.append({"object_id": identity})
        has_target_subject |= obj.timeframe == claim.timeframe
    if not has_target_subject:
        raise ValueError("claim has no subject on its declared timeframe")
    return _hash_payload(
        {
            "exchange": frame.exchange,
            "symbol": frame.symbol,
            "timeframe": claim.timeframe,
            "window": [
                (
                    source_candle_subject_id(
                        frame.exchange, frame.symbol, claim.timeframe, c
                    ),
                    _utc(c.open_time),
                    _utc(c.close_time),
                )
                for c in window
            ],
            "subjects": subjects,
            "causal_ancestry": [ancestry[key] for key in sorted(ancestry)],
        }
    )


def _witness_payload(claim: SourceQualitativeClaim, context_sha: str) -> dict:
    return {
        "schema": CLAIM_BINDING_VERSION,
        "context_sha256": context_sha,
        "semantic_id": claim.semantic_id,
        "scope": claim.scope.value,
        "status": claim.status.value,
        "symbol": claim.symbol,
        "timeframe": claim.timeframe,
        "observation_start_at": _utc(claim.observation_start_at),
        "observation_end_at": _utc(claim.observation_end_at),
        "known_at": _utc(claim.known_at),
        "subject_object_ids": list(claim.subject_object_ids),
        "source_refs": list(claim.source_refs),
        "source_rule_ids": list(claim.source_rule_ids),
        "annotation_method": claim.annotation_method.value
        if claim.annotation_method
        else None,
        "rationale_code": claim.rationale_code,
    }


def _validate_witness(
    claim: SourceQualitativeClaim, context_sha: str, raw: bytes
) -> str:
    if type(raw) is not bytes:
        raise ValueError("immutable provenance artifact bytes required")
    expected_ref = "sha256:" + sha256(raw).hexdigest()
    if claim.provenance_ref != expected_ref:
        raise ValueError("provenance content hash mismatch")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate provenance key")
            result[key] = value
        return result

    text = raw.decode("utf-8")
    document = json.loads(text, object_pairs_hook=unique)
    expected = _witness_payload(claim, context_sha)
    if not isinstance(document, dict) or set(document) != {*expected, "annotator_ref"}:
        raise ValueError("unexpected provenance artifact fields")
    annotator = document.pop("annotator_ref")
    if not isinstance(annotator, str) or not annotator.strip() or document != expected:
        raise ValueError("provenance artifact does not attest this bounded claim")
    return text


@dataclass(frozen=True)
class BoundSourceClaim:
    claim: SourceQualitativeClaim
    first_observed_at: datetime
    effective_known_at: datetime
    context_sha256: str
    first_frame_sha256: str
    provenance_json: str


@dataclass(frozen=True)
class BoundClaimAssessment:
    evidence: QualitativeEvidence
    reason: str
    supporting_claim_ids: tuple[str, ...]


class SourceClaimJournal:
    """Append-only ingestion journal; late delivery can never backfill evidence."""

    def __init__(
        self, catalog: QualitativeSemanticCatalog, *, exchange: str, symbol: str
    ):
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (exchange, symbol)
        ):
            raise ValueError("journal requires explicit market identity")
        self.catalog = catalog
        self.exchange, self.symbol = exchange, symbol
        self._prefixes = {}
        self._object_history = {}
        self._object_observed_at = {}
        self._records: dict[str, BoundSourceClaim] = {}
        self._watermark: datetime | None = None

    @property
    def records(self) -> tuple[BoundSourceClaim, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda r: (r.first_observed_at, r.claim.evidence_id),
            )
        )

    def _frame_progress(self, frame: ReplayFrame) -> dict:
        _validate_frame(frame)
        if (frame.exchange, frame.symbol) != (self.exchange, self.symbol):
            raise ValueError("journal market identity mismatch")
        if self._watermark is not None and frame.decision_at < self._watermark:
            raise ValueError("annotation ingestion clock cannot move backwards")
        current = {p.timeframe: (p.interval_ms, tuple(p.candles)) for p in frame.series}
        if self._prefixes and set(current) != set(self._prefixes):
            raise ValueError("journal timeframe grid changed")
        for tf, (interval, candles) in self._prefixes.items():
            if current[tf][0] != interval or current[tf][1][: len(candles)] != candles:
                raise ValueError("journal closed history changed or truncated")
        return current

    def observe_frame(self, frame: ReplayFrame) -> None:
        """Advance the authoritative caller clock even when no claim arrives."""
        current = self._frame_progress(frame)
        self._watermark, self._prefixes = frame.decision_at, current

    def _check_object_history(self, objects: Sequence[CausalSourceObject]) -> dict:
        current = {o.object_id: o for o in objects}
        if len(current) != len(objects):
            raise ValueError("duplicate subject object identities")
        static = (
            "object_type",
            "symbol",
            "timeframe",
            "direction",
            "formation_at",
            "known_at",
            "source_rule_ids",
            "technical_normalization_ids",
            "parent_object_ids",
            "provenance",
        )
        for identity, obj in current.items():
            prior = self._object_history.get(identity)
            if prior is not None and (
                any(getattr(obj, key) != getattr(prior, key) for key in static)
                or obj.lifecycle[: len(prior.lifecycle)] != prior.lifecycle
            ):
                raise ValueError("source object identity/history changed")
            if prior is not None and any(
                event.at <= self._object_observed_at[identity]
                for event in obj.lifecycle[len(prior.lifecycle) :]
            ):
                raise ValueError("source lifecycle append rewrites observed history")
        return current

    def ingest(
        self,
        claim: SourceQualitativeClaim,
        *,
        frame: ReplayFrame,
        objects: Sequence[CausalSourceObject],
        provenance: bytes,
    ) -> BoundSourceClaim:
        validate_claim_against_catalog(claim, self.catalog)
        current = self._frame_progress(frame)
        object_updates = self._check_object_history(objects)
        if claim.status == EvidenceStatus.UNKNOWN or not claim.evidence_id:
            raise ValueError("UNKNOWN is not an audited annotation to ingest")
        context = claim_context_sha256(claim, frame, objects)
        witness = _validate_witness(claim, context, provenance)
        # Complete validation precedes every mutation, including idempotent replay.
        old = self._records.get(claim.evidence_id)
        if old is not None:
            if (
                old.claim != claim
                or old.context_sha256 != context
                or old.provenance_json != witness
            ):
                raise ValueError("bound claim changed for stable identity")
            self._watermark = frame.decision_at
            self._prefixes = current
            self._object_history.update(object_updates)
            self._object_observed_at.update(
                {identity: frame.decision_at for identity in object_updates}
            )
            return old
        frame_sha = _hash_payload(
            (
                frame.exchange,
                frame.symbol,
                frame.decision_at,
                tuple(sorted(current.items())),
            )
        )
        record = BoundSourceClaim(
            claim,
            frame.decision_at,
            max(claim.known_at, frame.decision_at),
            context,
            frame_sha,
            witness,
        )
        self._records[claim.evidence_id] = record
        self._watermark = frame.decision_at
        self._prefixes = current
        self._object_history.update(object_updates)
        self._object_observed_at.update(
            {identity: frame.decision_at for identity in object_updates}
        )
        return record

    def assess(
        self,
        *,
        semantic_id: str,
        subject_object_ids: tuple[str, ...],
        timeframe: str,
        observation_start_at: datetime,
        observation_end_at: datetime,
        scope: QualitativeScope,
        decision_at: datetime,
    ) -> BoundClaimAssessment:
        _utc(decision_at)
        if (
            not isinstance(scope, QualitativeScope)
            or type(subject_object_ids) is not tuple
        ):
            raise ValueError("typed scope and immutable subject IDs required")
        _utc(observation_start_at)
        _utc(observation_end_at)
        definition = self.catalog.semantic(semantic_id)
        if definition.scope != scope:
            raise ValueError("trade context cannot be projected as object formation")
        if not subject_object_ids or any(
            not isinstance(s, str) or not s.strip() for s in subject_object_ids
        ):
            raise ValueError("subject IDs must be nonblank immutable text")
        subjects = tuple(sorted(set(subject_object_ids)))
        records = tuple(
            r
            for r in self.records
            if r.claim.semantic_id == semantic_id
            and r.claim.subject_object_ids == subjects
            and r.claim.timeframe == timeframe
            and r.claim.observation_start_at == observation_start_at
            and r.claim.observation_end_at == observation_end_at
            and r.effective_known_at <= decision_at
        )
        ids = tuple(sorted(r.claim.evidence_id for r in records))
        if not records:
            return BoundClaimAssessment(
                QualitativeEvidence(EvidenceStatus.UNKNOWN, None, None),
                "WAIT_CAUSAL_SOURCE_ANNOTATION",
                (),
            )
        statuses = {r.claim.status for r in records}
        if len(statuses) != 1:
            return BoundClaimAssessment(
                QualitativeEvidence(EvidenceStatus.UNKNOWN, None, None),
                "CONFLICTING_SOURCE_ANNOTATIONS_NO_WINNER",
                ids,
            )
        status = next(iter(statuses))
        known = min(r.effective_known_at for r in records)
        # Identity of the first available agreeing fact, never a selected annotator.
        fact_id = "qual-" + _hash_payload(
            (
                self.exchange,
                self.symbol,
                semantic_id,
                scope.value,
                timeframe,
                _utc(observation_start_at),
                _utc(observation_end_at),
                subjects,
                status.value,
                _utc(known),
            )
        )
        return BoundClaimAssessment(
            QualitativeEvidence(status, fact_id, known),
            "BOUND_SOURCE_ANNOTATION_NOT_OBJECT_OR_TRADE_ADMISSION",
            ids,
        )
