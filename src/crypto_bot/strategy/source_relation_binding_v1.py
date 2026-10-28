"""Stage24 structural-relation binding on the existing Stage20 journal clock.

SourceRelationJournal is a strict extension of SourceClaimJournal: one instance
retains qualitative and structural-relation receipts under the same closed-data,
object-history and monotonic replay boundary. It does not infer relations or
create strategy objects/trades.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from crypto_bot.strategy.causal_objects import CausalSourceObject
from crypto_bot.strategy.pure_source_replay_v2 import ReplayFrame, _hash_payload
from crypto_bot.strategy.source_claim_binding_v1 import (
    SourceClaimJournal,
    _utc,
    claim_context_sha256,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import QualitativeSemanticCatalog
from crypto_bot.strategy.source_relation_provenance_v1 import (
    RelationAssessment,
    RelationSubject,
    SourceRelationCatalog,
    SourceRelationClaim,
    validate_relation_against_catalog,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

RELATION_BINDING_VERSION = "PURE_SOURCE_STAGE24_RELATION_BINDING_V1"


def relation_witness_payload(claim: SourceRelationClaim, context_sha: str) -> dict:
    return {
        "schema": RELATION_BINDING_VERSION,
        "context_sha256": context_sha,
        "semantic_id": claim.semantic_id,
        "status": claim.status.value,
        "symbol": claim.symbol,
        "timeframe": claim.timeframe,
        "observation_start_at": _utc(claim.observation_start_at),
        "observation_end_at": _utc(claim.observation_end_at),
        "known_at": _utc(claim.known_at),
        "subjects": [(v.role, v.subject_id) for v in claim.subjects],
        "events": [
            (
                v.role,
                v.evidence_id,
                _utc(v.occurred_at),
                _utc(v.known_at),
            )
            for v in claim.events
        ],
        "source_refs": list(claim.source_refs),
        "source_rule_ids": list(claim.source_rule_ids),
        "annotation_method": claim.annotation_method.value if claim.annotation_method else None,
        "rationale_code": claim.rationale_code,
    }


def validate_relation_witness(
    claim: SourceRelationClaim, context_sha: str, raw: bytes
) -> str:
    if type(raw) is not bytes:
        raise ValueError("immutable relation provenance artifact bytes required")
    if claim.provenance_ref != "sha256:" + sha256(raw).hexdigest():
        raise ValueError("relation provenance content hash mismatch")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate relation provenance key")
            result[key] = value
        return result

    text = raw.decode("utf-8")
    document = json.loads(text, object_pairs_hook=unique)
    expected = relation_witness_payload(claim, context_sha)
    if not isinstance(document, dict) or set(document) != {*expected, "annotator_ref"}:
        raise ValueError("unexpected relation provenance artifact fields")
    annotator = document.pop("annotator_ref")
    if not isinstance(annotator, str) or not annotator.strip() or document != expected:
        raise ValueError("relation provenance artifact does not attest this bounded relation")
    return text


@dataclass(frozen=True)
class BoundSourceRelation:
    claim: SourceRelationClaim
    first_observed_at: datetime
    effective_known_at: datetime
    context_sha256: str
    first_frame_sha256: str
    provenance_json: str


class SourceRelationJournal(SourceClaimJournal):
    """One Stage20/24 journal with separate typed record namespaces."""

    def __init__(
        self,
        catalog: QualitativeSemanticCatalog,
        relation_catalog: SourceRelationCatalog,
        *,
        exchange: str,
        symbol: str,
    ):
        super().__init__(catalog, exchange=exchange, symbol=symbol)
        if (
            relation_catalog.classification != "TECHNICAL_NORMALIZATION"
            or relation_catalog.baseline_identifiability != "NOT_IDENTIFIABLE"
            or relation_catalog.trade_entry_allowed is not False
            or relation_catalog.financial_backtest_allowed is not False
            or relation_catalog.paper_allowed is not False
            or relation_catalog.live_allowed is not False
            or relation_catalog.private_api_allowed is not False
            or relation_catalog.automatic_relation_inference_allowed is not False
            or relation_catalog.project_policy_applied
        ):
            raise ValueError("relation journal requires fail-closed Stage24 catalog")
        self.relation_catalog = relation_catalog
        self._relation_records: dict[str, BoundSourceRelation] = {}

    @property
    def relation_records(self) -> tuple[BoundSourceRelation, ...]:
        return tuple(
            sorted(
                self._relation_records.values(),
                key=lambda row: (row.first_observed_at, row.claim.evidence_id),
            )
        )

    def ingest_relation(
        self,
        claim: SourceRelationClaim,
        *,
        frame: ReplayFrame,
        objects: Sequence[CausalSourceObject],
        provenance: bytes,
    ) -> BoundSourceRelation:
        validate_relation_against_catalog(claim, self.relation_catalog)
        current = self._frame_progress(frame)
        object_updates = self._check_object_history(objects)
        if claim.status == EvidenceStatus.UNKNOWN or not claim.evidence_id:
            raise ValueError("UNKNOWN is not an audited SOURCE relation to ingest")
        context = claim_context_sha256(claim, frame, objects)  # shared Stage20 context binder
        witness = validate_relation_witness(claim, context, provenance)
        old = self._relation_records.get(claim.evidence_id)
        if old is not None:
            if old.claim != claim or old.context_sha256 != context or old.provenance_json != witness:
                raise ValueError("bound relation changed for stable identity")
            self._commit_progress(frame, current, object_updates)
            return old
        frame_sha = _hash_payload(
            (
                frame.exchange,
                frame.symbol,
                frame.decision_at,
                tuple(sorted(current.items())),
            )
        )
        record = BoundSourceRelation(
            claim=claim,
            first_observed_at=frame.decision_at,
            effective_known_at=max(claim.known_at, frame.decision_at),
            context_sha256=context,
            first_frame_sha256=frame_sha,
            provenance_json=witness,
        )
        self._relation_records[claim.evidence_id] = record
        self._commit_progress(frame, current, object_updates)
        return record

    def _commit_progress(self, frame: ReplayFrame, current: dict, object_updates: dict) -> None:
        self._watermark = frame.decision_at
        self._prefixes = current
        self._object_history.update(object_updates)
        self._object_observed_at.update(
            {identity: frame.decision_at for identity in object_updates}
        )

    def assess_relation(
        self,
        *,
        semantic_id: str,
        subjects: tuple[RelationSubject, ...],
        timeframe: str,
        observation_start_at: datetime,
        observation_end_at: datetime,
        decision_at: datetime,
    ) -> RelationAssessment:
        _utc(decision_at)
        _utc(observation_start_at)
        _utc(observation_end_at)
        if type(subjects) is not tuple:
            raise TypeError("immutable typed relation subjects required")
        definition = self.relation_catalog.relation(semantic_id)
        if tuple(subject.role for subject in subjects) != definition.subject_roles:
            raise ValueError("relation subject roles do not match frozen semantic")
        records = tuple(
            row
            for row in self.relation_records
            if row.claim.semantic_id == semantic_id
            and row.claim.subjects == subjects
            and row.claim.timeframe == timeframe
            and row.claim.observation_start_at == observation_start_at
            and row.claim.observation_end_at == observation_end_at
            and row.effective_known_at <= decision_at
        )
        ids = tuple(sorted(row.claim.evidence_id for row in records))
        if not records:
            return RelationAssessment(
                EvidenceStatus.UNKNOWN,
                "WAIT_CAUSAL_SOURCE_RELATION",
                (),
                None,
            )
        statuses = {row.claim.status for row in records}
        if len(statuses) != 1:
            return RelationAssessment(
                EvidenceStatus.UNKNOWN,
                "CONFLICTING_SOURCE_RELATIONS_NO_WINNER",
                ids,
                None,
            )
        return RelationAssessment(
            next(iter(statuses)),
            "BOUND_SOURCE_RELATION_NOT_OBJECT_OR_TRADE_ADMISSION",
            ids,
            min(row.effective_known_at for row in records),
        )
