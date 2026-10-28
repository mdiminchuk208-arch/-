from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from crypto_bot.integration.receiver import EngineEventEnvelope, validate_engine_event_envelope


class IngestionDecision(str, Enum):
    FIRST_ACCEPTED = "FIRST_ACCEPTED"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    COLLISION = "COLLISION"


@dataclass(frozen=True)
class PreparedEngineEvent:
    event_id: str
    event_type: str
    source_created_at: str
    payload: dict[str, Any]
    payload_sha256: str


@dataclass(frozen=True)
class ExistingEngineEvent:
    event_id: str
    event_type: str
    source_created_at: str
    payload: dict[str, Any]
    payload_sha256: str


@dataclass(frozen=True)
class IngestionComparison:
    decision: IngestionDecision
    reason: str
    prepared: PreparedEngineEvent


def canonical_payload_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def canonical_payload_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_payload_json(payload).encode("utf-8")).hexdigest()


def prepare_engine_event(value: Mapping[str, Any]) -> PreparedEngineEvent:
    envelope: EngineEventEnvelope = validate_engine_event_envelope(value)
    return PreparedEngineEvent(
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        source_created_at=envelope.created_at,
        payload=envelope.payload,
        payload_sha256=canonical_payload_sha256(envelope.payload),
    )


def compare_existing_event(
    prepared: PreparedEngineEvent,
    existing: ExistingEngineEvent | None,
) -> IngestionComparison:
    """Classify first insert, exact idempotent retry, or immutable collision.

    Database mutation is intentionally outside this pure function. A backend
    must execute the resulting persistence operations inside one transaction.
    """
    if existing is None:
        return IngestionComparison(
            decision=IngestionDecision.FIRST_ACCEPTED,
            reason="EVENT_ID_NOT_PRESENT",
            prepared=prepared,
        )

    if existing.event_id != prepared.event_id:
        raise ValueError("existing event identity does not match prepared event_id")

    differences: list[str] = []
    if existing.event_type != prepared.event_type:
        differences.append("EVENT_TYPE")

    existing_created = datetime.fromisoformat(existing.source_created_at)
    prepared_created = datetime.fromisoformat(prepared.source_created_at)
    if existing_created.tzinfo is None or existing_created.utcoffset() is None:
        raise ValueError("existing source_created_at must be timezone-aware")
    if prepared_created.tzinfo is None or prepared_created.utcoffset() is None:
        raise ValueError("prepared source_created_at must be timezone-aware")
    if existing_created != prepared_created:
        differences.append("SOURCE_CREATED_AT")

    if existing.payload_sha256 != prepared.payload_sha256:
        differences.append("PAYLOAD_SHA256")

    # Hash equality is necessary but the canonical JSON is also compared. This
    # makes the collision decision independent of relying on a hash alone.
    if canonical_payload_json(existing.payload) != canonical_payload_json(prepared.payload):
        differences.append("PAYLOAD")

    if differences:
        return IngestionComparison(
            decision=IngestionDecision.COLLISION,
            reason="IMMUTABLE_MISMATCH:" + ",".join(differences),
            prepared=prepared,
        )

    return IngestionComparison(
        decision=IngestionDecision.EXACT_DUPLICATE,
        reason="IMMUTABLE_EVENT_MATCH",
        prepared=prepared,
    )
