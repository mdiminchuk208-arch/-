from __future__ import annotations

from datetime import datetime
from typing import Protocol

from crypto_bot.integration.events import StrategyObjectSnapshot
from crypto_bot.integration.execution import SourceExecutionPlanSnapshot


class EventOutbox(Protocol):
    def enqueue(
        self,
        *,
        event_id: str,
        event_type: str,
        payload: dict[str, object],
        created_at: datetime,
    ) -> bool: ...


def publish_strategy_object(
    outbox: EventOutbox,
    snapshot: StrategyObjectSnapshot,
    *,
    created_at: datetime,
) -> bool:
    """Persist one immutable Strategy Engine object snapshot for backend handoff."""
    return outbox.enqueue(
        event_id=snapshot.event_id,
        event_type=snapshot.schema,
        payload=snapshot.to_dict(),
        created_at=created_at,
    )


def publish_source_execution_plan(
    outbox: EventOutbox,
    snapshot: SourceExecutionPlanSnapshot,
    *,
    created_at: datetime,
) -> bool:
    """Persist one fail-closed SOURCE execution-plan snapshot for backend handoff."""
    return outbox.enqueue(
        event_id=snapshot.event_id,
        event_type=snapshot.schema,
        payload=snapshot.to_dict(),
        created_at=created_at,
    )
