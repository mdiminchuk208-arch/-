from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from crypto_bot.runtime.health import RuntimeHealthSnapshot, RuntimeHealthState


RUNTIME_HEALTH_FILE_SCHEMA = "crypto-bot.runtime-health.v1"


@dataclass(frozen=True)
class RuntimeHealthFile:
    schema: str
    health: RuntimeHealthSnapshot


@dataclass(frozen=True)
class RuntimeHealthCheck:
    ok: bool
    reason: str
    state: RuntimeHealthState | None
    age_seconds: float | None


def write_runtime_health_file(snapshot: RuntimeHealthSnapshot, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": RUNTIME_HEALTH_FILE_SCHEMA,
        "health": {
            **asdict(snapshot),
            "state": snapshot.state.value,
        },
    }
    fd, tmp_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, destination)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return destination


def read_runtime_health_file(path: str | Path) -> RuntimeHealthFile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != RUNTIME_HEALTH_FILE_SCHEMA:
        raise ValueError(f"unsupported runtime health schema: {payload.get('schema')!r}")
    row = payload.get("health")
    if not isinstance(row, dict):
        raise ValueError("runtime health file must contain health object")
    health = RuntimeHealthSnapshot(
        observed_at=str(row["observed_at"]),
        state=RuntimeHealthState(str(row["state"])),
        reasons=tuple(row.get("reasons", ())),
        mtf_ready=bool(row["mtf_ready"]),
        stale_timeframes=tuple(row.get("stale_timeframes", ())),
        pending_outbox=int(row["pending_outbox"]),
        diagnostic_pipeline_available=bool(row["diagnostic_pipeline_available"]),
        trade_entry_allowed=bool(row["trade_entry_allowed"]),
    )
    if health.trade_entry_allowed:
        raise ValueError("runtime health file cannot grant trade entry")
    observed = datetime.fromisoformat(health.observed_at)
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("runtime health observed_at must be timezone-aware")
    return RuntimeHealthFile(schema=RUNTIME_HEALTH_FILE_SCHEMA, health=health)


def check_runtime_health_file(
    path: str | Path,
    *,
    now: datetime,
    max_age_seconds: float,
) -> RuntimeHealthCheck:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("health check clock must be timezone-aware")
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    try:
        record = read_runtime_health_file(path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return RuntimeHealthCheck(False, f"HEALTH_FILE_INVALID:{exc}", None, None)

    observed = datetime.fromisoformat(record.health.observed_at).astimezone(timezone.utc)
    age = (now.astimezone(timezone.utc) - observed).total_seconds()
    if age < -1:
        return RuntimeHealthCheck(False, "HEALTH_CLOCK_IN_FUTURE", record.health.state, age)
    if age > max_age_seconds:
        return RuntimeHealthCheck(False, "HEALTH_FILE_STALE", record.health.state, age)
    if record.health.state == RuntimeHealthState.SAFE_MODE:
        return RuntimeHealthCheck(False, "RUNTIME_SAFE_MODE", record.health.state, age)
    if record.health.state == RuntimeHealthState.STARTING:
        return RuntimeHealthCheck(False, "RUNTIME_STARTING", record.health.state, age)
    return RuntimeHealthCheck(True, "RUNTIME_RESPONSIVE", record.health.state, age)
