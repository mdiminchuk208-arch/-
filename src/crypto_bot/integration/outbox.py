from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class OutboxRecord:
    event_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str
    delivered_at: str | None
    delivery_attempts: int
    last_error: str | None


class SQLiteEngineOutbox:
    """Durable idempotent handoff between Strategy Engine and a future backend.

    This is intentionally transport-only. It accepts immutable event snapshots,
    stores their exact payload and provides explicit delivery acknowledgement.
    It does not interpret SOURCE rules, risk policy or execution permission.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS engine_outbox (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT,
                    delivery_attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_engine_outbox_pending "
                "ON engine_outbox(delivered_at, created_at, event_id)"
            )

    @staticmethod
    def _aware_iso(value: datetime, name: str) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware")
        return value.isoformat()

    @staticmethod
    def _canonical_payload(payload: Mapping[str, Any]) -> str:
        return json.dumps(dict(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def enqueue(
        self,
        *,
        event_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        created_at: datetime,
    ) -> bool:
        if not event_id.strip() or not event_type.strip():
            raise ValueError("event_id and event_type must be non-empty")
        created = self._aware_iso(created_at, "created_at")
        payload_json = self._canonical_payload(payload)

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT event_type, payload_json FROM engine_outbox WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing is not None:
                if existing["event_type"] != event_type or existing["payload_json"] != payload_json:
                    raise ValueError(f"event_id collision with different payload: {event_id}")
                return False
            connection.execute(
                "INSERT INTO engine_outbox(event_id,event_type,payload_json,created_at) VALUES(?,?,?,?)",
                (event_id, event_type, payload_json, created),
            )
        return True

    def pending(self, *, limit: int = 100) -> tuple[OutboxRecord, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id,event_type,payload_json,created_at,delivered_at,delivery_attempts,last_error
                FROM engine_outbox
                WHERE delivered_at IS NULL
                ORDER BY created_at, event_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return tuple(self._record(row) for row in rows)

    def get(self, event_id: str) -> OutboxRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_id,event_type,payload_json,created_at,delivered_at,delivery_attempts,last_error
                FROM engine_outbox WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._record(row)

    def mark_attempt(self, event_id: str, *, error: str | None = None) -> OutboxRecord:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE engine_outbox
                SET delivery_attempts = delivery_attempts + 1, last_error = ?
                WHERE event_id = ? AND delivered_at IS NULL
                """,
                (error, event_id),
            )
            if cursor.rowcount == 0:
                row = connection.execute(
                    "SELECT event_id FROM engine_outbox WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(event_id)
        return self.get(event_id)

    def mark_delivered(self, event_id: str, *, delivered_at: datetime) -> OutboxRecord:
        delivered = self._aware_iso(delivered_at, "delivered_at")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT created_at, delivered_at FROM engine_outbox WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(event_id)
            created = datetime.fromisoformat(row["created_at"])
            delivered_dt = datetime.fromisoformat(delivered)
            if delivered_dt < created:
                raise ValueError("delivered_at cannot precede created_at")
            if row["delivered_at"] is None:
                connection.execute(
                    "UPDATE engine_outbox SET delivered_at = ?, last_error = NULL WHERE event_id = ?",
                    (delivered, event_id),
                )
        return self.get(event_id)

    @staticmethod
    def _record(row: sqlite3.Row) -> OutboxRecord:
        return OutboxRecord(
            event_id=row["event_id"],
            event_type=row["event_type"],
            payload=json.loads(row["payload_json"]),
            created_at=row["created_at"],
            delivered_at=row["delivered_at"],
            delivery_attempts=int(row["delivery_attempts"]),
            last_error=row["last_error"],
        )
