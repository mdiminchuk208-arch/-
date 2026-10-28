from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from crypto_bot.integration.outbox import SQLiteEngineOutbox
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer
from crypto_bot.strategy.pure_source_diagnostic_replay_v2 import (
    SourceDiagnosticArtifact,
    build_source_diagnostic_artifact,
    verify_source_diagnostic_artifact,
)
from crypto_bot.strategy.pure_source_replay_v2 import ReplaySeries


LIVE_DIAGNOSTIC_EVENT_TYPE = "crypto-bot.pure-source-live-diagnostic.v1"


class LiveDiagnosticStatus(str, Enum):
    WAIT_MTF_HISTORY = "WAIT_MTF_HISTORY"
    DIAGNOSTIC_READY = "DIAGNOSTIC_READY"


@dataclass(frozen=True)
class LiveDiagnosticResult:
    status: LiveDiagnosticStatus
    published: bool
    artifact_sha256: str | None
    last_decision_at: datetime | None
    unresolved_count: int
    trade_entry_allowed: bool


DiagnosticBuilder = Callable[[tuple[ReplaySeries, ...]], SourceDiagnosticArtifact]


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def diagnostic_artifact_payload(artifact: SourceDiagnosticArtifact) -> dict[str, Any]:
    return _jsonable(asdict(artifact))


class LivePureSourceDiagnosticRunner:
    """Recompute the causal PURE SOURCE diagnostic from durable live MTF data.

    This deliberately reuses the audited replay/provider path instead of
    creating a second live strategy implementation. The output is diagnostic
    only and is written to an idempotent outbox for backend/platform ingestion.
    """

    def __init__(
        self,
        *,
        buffer: LiveMtfBuffer,
        outbox: SQLiteEngineOutbox,
        builder: DiagnosticBuilder = build_source_diagnostic_artifact,
    ) -> None:
        self.buffer = buffer
        self.outbox = outbox
        self.builder = builder

    def run_once(self) -> LiveDiagnosticResult:
        status = self.buffer.status()
        if not status.ready:
            return LiveDiagnosticResult(
                status=LiveDiagnosticStatus.WAIT_MTF_HISTORY,
                published=False,
                artifact_sha256=None,
                last_decision_at=None,
                unresolved_count=0,
                trade_entry_allowed=False,
            )

        series = self.buffer.replay_series(require_ready=True)
        artifact = self.builder(series)
        if not verify_source_diagnostic_artifact(artifact):
            raise ValueError("live PURE SOURCE diagnostic artifact fingerprint verification failed")
        if artifact.trade_entry_allowed:
            raise ValueError("live PURE SOURCE diagnostic must remain fail-closed")
        if artifact.financial_run:
            raise ValueError("live PURE SOURCE diagnostic cannot become a financial run")

        payload = {
            "event_type": LIVE_DIAGNOSTIC_EVENT_TYPE,
            "exchange": status.exchange,
            "symbol": status.symbol,
            "mtf_counts": list(status.counts),
            "artifact": diagnostic_artifact_payload(artifact),
        }
        published = self.outbox.enqueue(
            event_id=artifact.artifact_sha256,
            event_type=LIVE_DIAGNOSTIC_EVENT_TYPE,
            payload=payload,
            created_at=artifact.last_decision_at,
        )
        return LiveDiagnosticResult(
            status=LiveDiagnosticStatus.DIAGNOSTIC_READY,
            published=published,
            artifact_sha256=artifact.artifact_sha256,
            last_decision_at=artifact.last_decision_at,
            unresolved_count=len(artifact.unresolved),
            trade_entry_allowed=False,
        )
