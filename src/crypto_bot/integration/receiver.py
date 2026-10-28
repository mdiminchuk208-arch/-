from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class EngineEventEnvelope:
    event_id: str
    event_type: str
    created_at: str
    payload: dict[str, Any]


def _assert_no_execution_enablement(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) == "trade_entry_allowed" and child is True:
                raise ValueError(
                    f"financial execution enablement is forbidden at integration boundary: {child_path}"
                )
            _assert_no_execution_enablement(child, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_no_execution_enablement(child, f"{path}[{index}]")


def validate_engine_event_envelope(value: Mapping[str, Any]) -> EngineEventEnvelope:
    """Validate the generic POST envelope before backend persistence.

    This validator is intentionally transport/backend agnostic. It provides the
    minimum receiver contract without inventing an HTTP route or framework.
    """
    required = {"event_id", "event_type", "created_at", "payload"}
    missing = required - set(value)
    extra = set(value) - required
    if missing:
        raise ValueError(f"engine event envelope missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"engine event envelope contains unknown fields: {sorted(extra)}")

    event_id = str(value["event_id"])
    event_type = str(value["event_type"])
    created_at = str(value["created_at"])
    payload = value["payload"]
    if not event_id.strip() or not event_type.strip():
        raise ValueError("event_id and event_type must be non-empty")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    parsed = datetime.fromisoformat(created_at)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")

    payload_event_id = payload.get("event_id")
    if payload_event_id is not None and str(payload_event_id) != event_id:
        raise ValueError("payload event_id does not match envelope event_id")
    payload_schema = payload.get("schema")
    if payload_schema is not None and str(payload_schema) != event_type:
        raise ValueError("payload schema does not match envelope event_type")

    _assert_no_execution_enablement(payload)
    return EngineEventEnvelope(
        event_id=event_id,
        event_type=event_type,
        created_at=created_at,
        payload=dict(payload),
    )
