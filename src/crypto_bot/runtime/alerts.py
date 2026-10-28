from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable

from crypto_bot.runtime.health import RuntimeHealthSnapshot, RuntimeHealthState


OPERATIONAL_ALERT_SCHEMA = "crypto-bot.operational-alert.v1"


class AlertTransition(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class OperationalAlertEvent:
    schema: str
    event_id: str
    alert_episode_id: str
    code: str
    transition: AlertTransition
    observed_at: str
    health_state: RuntimeHealthState
    details: tuple[str, ...]
    trade_entry_allowed: bool

    def __post_init__(self) -> None:
        if self.schema != OPERATIONAL_ALERT_SCHEMA:
            raise ValueError(f"unsupported operational alert schema: {self.schema!r}")
        if not self.event_id.strip() or not self.alert_episode_id.strip() or not self.code.strip():
            raise ValueError("event_id, alert_episode_id and code must be non-empty")
        observed = datetime.fromisoformat(self.observed_at)
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("operational alert observed_at must be timezone-aware")
        if self.trade_entry_allowed:
            raise ValueError("operational alerts cannot enable trade entry")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["transition"] = self.transition.value
        payload["health_state"] = self.health_state.value
        payload["details"] = list(self.details)
        return payload


@dataclass(frozen=True)
class ActiveOperationalAlert:
    alert_episode_id: str
    code: str
    opened_at: str
    last_seen_at: str
    health_state: RuntimeHealthState


class SQLiteOperationalAlertJournal:
    """Durable one-shot OPEN/RESOLVED state for operational health alerts."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operational_alert_active (
                    code TEXT PRIMARY KEY,
                    alert_episode_id TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    health_state TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operational_alert_events (
                    event_id TEXT PRIMARY KEY,
                    alert_episode_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    transition TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    health_state TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_operational_alert_events_time "
                "ON operational_alert_events(observed_at, event_id)"
            )

    def active(self) -> tuple[ActiveOperationalAlert, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT alert_episode_id,code,opened_at,last_seen_at,health_state
                FROM operational_alert_active
                ORDER BY code
                """
            ).fetchall()
        return tuple(
            ActiveOperationalAlert(
                alert_episode_id=row["alert_episode_id"],
                code=row["code"],
                opened_at=row["opened_at"],
                last_seen_at=row["last_seen_at"],
                health_state=RuntimeHealthState(row["health_state"]),
            )
            for row in rows
        )

    def events(self, *, limit: int | None = None) -> tuple[OperationalAlertEvent, ...]:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be positive when supplied")
        sql = (
            "SELECT payload_json FROM operational_alert_events "
            "ORDER BY observed_at,event_id"
        )
        params: tuple[object, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        result: list[OperationalAlertEvent] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            result.append(
                OperationalAlertEvent(
                    schema=payload["schema"],
                    event_id=payload["event_id"],
                    alert_episode_id=payload["alert_episode_id"],
                    code=payload["code"],
                    transition=AlertTransition(payload["transition"]),
                    observed_at=payload["observed_at"],
                    health_state=RuntimeHealthState(payload["health_state"]),
                    details=tuple(payload.get("details", ())),
                    trade_entry_allowed=bool(payload["trade_entry_allowed"]),
                )
            )
        return tuple(result)

    def reconcile(self, snapshot: RuntimeHealthSnapshot) -> tuple[OperationalAlertEvent, ...]:
        observed = datetime.fromisoformat(snapshot.observed_at)
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("health snapshot observed_at must be timezone-aware")
        if snapshot.trade_entry_allowed:
            raise ValueError("health snapshot cannot grant trade entry")

        desired = _desired_alert_codes(snapshot)
        existing = {row.code: row for row in self.active()}
        emitted: list[OperationalAlertEvent] = []

        for code in sorted(desired):
            active = existing.get(code)
            if active is None:
                episode_id = _hash_parts("episode", code, snapshot.observed_at)
                event = _event(
                    episode_id=episode_id,
                    code=code,
                    transition=AlertTransition.OPEN,
                    snapshot=snapshot,
                )
                self._persist_event_and_open(event)
                emitted.append(event)
            else:
                self._touch_active(code, snapshot)

        for code in sorted(set(existing) - desired):
            active = existing[code]
            event = _event(
                episode_id=active.alert_episode_id,
                code=code,
                transition=AlertTransition.RESOLVED,
                snapshot=snapshot,
            )
            self._persist_event_and_resolve(event)
            emitted.append(event)

        return tuple(emitted)

    def _persist_event_and_open(self, event: OperationalAlertEvent) -> None:
        payload = json.dumps(
            event.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO operational_alert_events(
                    event_id,alert_episode_id,code,transition,observed_at,health_state,payload_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    event.event_id,
                    event.alert_episode_id,
                    event.code,
                    event.transition.value,
                    event.observed_at,
                    event.health_state.value,
                    payload,
                ),
            )
            conn.execute(
                """
                INSERT INTO operational_alert_active(
                    code,alert_episode_id,opened_at,last_seen_at,health_state
                ) VALUES(?,?,?,?,?)
                """,
                (
                    event.code,
                    event.alert_episode_id,
                    event.observed_at,
                    event.observed_at,
                    event.health_state.value,
                ),
            )

    def _persist_event_and_resolve(self, event: OperationalAlertEvent) -> None:
        payload = json.dumps(
            event.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO operational_alert_events(
                    event_id,alert_episode_id,code,transition,observed_at,health_state,payload_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    event.event_id,
                    event.alert_episode_id,
                    event.code,
                    event.transition.value,
                    event.observed_at,
                    event.health_state.value,
                    payload,
                ),
            )
            deleted = conn.execute(
                "DELETE FROM operational_alert_active WHERE code=? AND alert_episode_id=?",
                (event.code, event.alert_episode_id),
            )
            if deleted.rowcount != 1:
                raise RuntimeError("operational alert active episode changed during resolution")

    def _touch_active(self, code: str, snapshot: RuntimeHealthSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE operational_alert_active
                SET last_seen_at=?, health_state=?
                WHERE code=?
                """,
                (snapshot.observed_at, snapshot.state.value, code),
            )


def _hash_parts(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _event(
    *,
    episode_id: str,
    code: str,
    transition: AlertTransition,
    snapshot: RuntimeHealthSnapshot,
) -> OperationalAlertEvent:
    event_id = _hash_parts(
        OPERATIONAL_ALERT_SCHEMA,
        episode_id,
        transition.value,
        snapshot.observed_at,
    )
    return OperationalAlertEvent(
        schema=OPERATIONAL_ALERT_SCHEMA,
        event_id=event_id,
        alert_episode_id=episode_id,
        code=code,
        transition=transition,
        observed_at=snapshot.observed_at,
        health_state=snapshot.state,
        details=tuple(snapshot.reasons),
        trade_entry_allowed=False,
    )


def _desired_alert_codes(snapshot: RuntimeHealthSnapshot) -> set[str]:
    """Translate health diagnostics into operational alert codes only.

    STARTING is intentionally not alerted: it is a deployment/readiness state,
    not an incident. HEALTHY_DIAGNOSTIC yields no active alerts.
    """
    codes: set[str] = set()
    if snapshot.state == RuntimeHealthState.SAFE_MODE:
        codes.add("RUNTIME_SAFE_MODE")
    elif snapshot.state == RuntimeHealthState.DEGRADED:
        codes.add("RUNTIME_DEGRADED")

    for reason in snapshot.reasons:
        if reason.startswith("MARKET_DATA_STALE_"):
            codes.add(reason)
        elif reason in {"ENGINE_OUTBOX_BACKLOG", "DIAGNOSTIC_PIPELINE_UNAVAILABLE"}:
            codes.add(reason)
    return codes
