from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from crypto_bot.integration.outbox import OutboxRecord, SQLiteEngineOutbox


@dataclass(frozen=True)
class HttpDeliveryConfig:
    endpoint: str
    timeout_seconds: float = 10.0
    bearer_token: str | None = None
    allow_plain_http_localhost: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("delivery endpoint must be an absolute http(s) URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if parsed.scheme == "http":
            host = (parsed.hostname or "").lower()
            if not self.allow_plain_http_localhost or host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("plain HTTP delivery is allowed only for explicit localhost development")
        if self.bearer_token is not None and not self.bearer_token.strip():
            raise ValueError("bearer_token cannot be blank")


@dataclass(frozen=True)
class DeliveryResponse:
    status_code: int
    body: bytes = b""


@dataclass(frozen=True)
class DeliveryAttemptResult:
    event_id: str
    delivered: bool
    status_code: int | None
    error: str | None
    delivery_attempts: int


Transport = Callable[[str, bytes, Mapping[str, str], float], DeliveryResponse]


def _default_transport(
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> DeliveryResponse:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            # Backend acknowledgements do not need to return the event. Cap the
            # diagnostic body so a remote peer cannot force unbounded memory.
            return DeliveryResponse(int(response.status), response.read(4096))
    except HTTPError as exc:
        return DeliveryResponse(int(exc.code), exc.read(4096))
    except URLError as exc:
        raise ConnectionError(str(exc.reason)) from exc


def _event_body(record: OutboxRecord) -> bytes:
    envelope = {
        "event_id": record.event_id,
        "event_type": record.event_type,
        "created_at": record.created_at,
        "payload": record.payload,
    }
    return json.dumps(
        envelope,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def deliver_record(
    outbox: SQLiteEngineOutbox,
    record: OutboxRecord,
    *,
    config: HttpDeliveryConfig,
    transport: Transport = _default_transport,
    delivered_at: datetime | None = None,
) -> DeliveryAttemptResult:
    """Attempt one exact outbox event and acknowledge only a 2xx response."""
    if record.delivered_at is not None:
        return DeliveryAttemptResult(
            event_id=record.event_id,
            delivered=True,
            status_code=None,
            error=None,
            delivery_attempts=record.delivery_attempts,
        )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Idempotency-Key": record.event_id,
        "X-Crypto-Bot-Event-Id": record.event_id,
        "X-Crypto-Bot-Event-Type": record.event_type,
    }
    if config.bearer_token is not None:
        headers["Authorization"] = f"Bearer {config.bearer_token}"

    try:
        response = transport(
            config.endpoint,
            _event_body(record),
            headers,
            config.timeout_seconds,
        )
    except Exception as exc:
        error = f"TRANSPORT_ERROR:{type(exc).__name__}:{exc}"
        updated = outbox.mark_attempt(record.event_id, error=error)
        return DeliveryAttemptResult(
            event_id=record.event_id,
            delivered=False,
            status_code=None,
            error=error,
            delivery_attempts=updated.delivery_attempts,
        )

    if 200 <= response.status_code < 300:
        attempted = outbox.mark_attempt(record.event_id)
        at = delivered_at or datetime.now(timezone.utc)
        delivered = outbox.mark_delivered(record.event_id, delivered_at=at)
        return DeliveryAttemptResult(
            event_id=record.event_id,
            delivered=True,
            status_code=response.status_code,
            error=None,
            delivery_attempts=max(attempted.delivery_attempts, delivered.delivery_attempts),
        )

    error = f"HTTP_STATUS_{response.status_code}"
    updated = outbox.mark_attempt(record.event_id, error=error)
    return DeliveryAttemptResult(
        event_id=record.event_id,
        delivered=False,
        status_code=response.status_code,
        error=error,
        delivery_attempts=updated.delivery_attempts,
    )


def deliver_pending(
    outbox: SQLiteEngineOutbox,
    *,
    config: HttpDeliveryConfig,
    limit: int = 100,
    transport: Transport = _default_transport,
) -> tuple[DeliveryAttemptResult, ...]:
    """Deliver a bounded pending batch in durable outbox order."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    rows = outbox.pending(limit=limit)
    results: list[DeliveryAttemptResult] = []
    for record in rows:
        result = deliver_record(
            outbox,
            record,
            config=config,
            transport=transport,
        )
        results.append(result)
        # Preserve ordered delivery. A failed earlier event is not skipped by a
        # later one; the next worker cycle retries from the same durable prefix.
        if not result.delivered:
            break
    return tuple(results)
