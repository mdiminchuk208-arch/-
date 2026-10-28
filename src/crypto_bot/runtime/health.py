from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping

from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer


class RuntimeHealthState(str, Enum):
    STARTING = "STARTING"
    HEALTHY_DIAGNOSTIC = "HEALTHY_DIAGNOSTIC"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class RuntimeHealthPolicy:
    stale_after_seconds: Mapping[str, int]
    max_pending_outbox: int

    def __post_init__(self) -> None:
        if self.max_pending_outbox < 0:
            raise ValueError("max_pending_outbox cannot be negative")
        if not self.stale_after_seconds:
            raise ValueError("stale_after_seconds must be explicit and non-empty")
        for timeframe, seconds in self.stale_after_seconds.items():
            if not str(timeframe):
                raise ValueError("stale policy timeframe must be non-empty")
            if int(seconds) <= 0:
                raise ValueError("stale thresholds must be positive")


@dataclass(frozen=True)
class RuntimeHealthSnapshot:
    observed_at: str
    state: RuntimeHealthState
    reasons: tuple[str, ...]
    mtf_ready: bool
    stale_timeframes: tuple[str, ...]
    pending_outbox: int
    diagnostic_pipeline_available: bool
    trade_entry_allowed: bool



def evaluate_runtime_health(
    *,
    buffer: LiveMtfBuffer,
    outbox: SQLiteEngineOutbox,
    policy: RuntimeHealthPolicy,
    observed_at: datetime,
    diagnostic_pipeline_available: bool,
) -> RuntimeHealthSnapshot:
    """Evaluate operational health without changing strategy or execution state."""
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    now_utc = observed_at.astimezone(timezone.utc)
    status = buffer.status()

    configured = set(buffer.specs)
    policy_keys = {str(key) for key in policy.stale_after_seconds}
    if configured != policy_keys:
        missing = configured - policy_keys
        extra = policy_keys - configured
        raise ValueError(
            "stale policy must exactly match configured MTF timeframes "
            f"(missing={sorted(missing)}, extra={sorted(extra)})"
        )

    stale: list[str] = []
    if status.ready:
        for timeframe, spec in sorted(buffer.specs.items(), key=lambda item: item[1].interval_ms):
            rows = buffer.store.load_series(
                exchange=buffer.exchange,
                symbol=buffer.symbol,
                interval=timeframe,
                limit=1,
            )
            if not rows:
                stale.append(timeframe)
                continue
            latest = rows[-1]
            close_ms = latest.open_time_ms + spec.interval_ms
            age_seconds = now_utc.timestamp() - close_ms / 1000
            if age_seconds > policy.stale_after_seconds[timeframe]:
                stale.append(timeframe)

    pending_rows = outbox.pending(limit=policy.max_pending_outbox + 1 or 1)
    pending_count = len(pending_rows)
    outbox_over_limit = pending_count > policy.max_pending_outbox

    reasons: list[str] = []
    if not status.ready:
        reasons.append("MTF_HISTORY_NOT_READY")
        for timeframe in status.missing_timeframes:
            reasons.append(f"MTF_MISSING_{timeframe}")
    for timeframe in stale:
        reasons.append(f"MARKET_DATA_STALE_{timeframe}")
    if outbox_over_limit:
        reasons.append("ENGINE_OUTBOX_BACKLOG")
    if not diagnostic_pipeline_available:
        reasons.append("DIAGNOSTIC_PIPELINE_UNAVAILABLE")

    if stale:
        state = RuntimeHealthState.SAFE_MODE
    elif not status.ready:
        state = RuntimeHealthState.STARTING
    elif outbox_over_limit or not diagnostic_pipeline_available:
        state = RuntimeHealthState.DEGRADED
    else:
        state = RuntimeHealthState.HEALTHY_DIAGNOSTIC

    return RuntimeHealthSnapshot(
        observed_at=observed_at.isoformat(),
        state=state,
        reasons=tuple(reasons),
        mtf_ready=status.ready,
        stale_timeframes=tuple(stale),
        pending_outbox=pending_count,
        diagnostic_pipeline_available=diagnostic_pipeline_available,
        trade_entry_allowed=False,
    )
