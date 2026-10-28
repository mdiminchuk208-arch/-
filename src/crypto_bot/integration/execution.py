from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from crypto_bot.strategy.source_execution_v2 import SourceExecutionPlan


SOURCE_EXECUTION_EVENT_SCHEMA = "crypto-bot.source-execution-plan-snapshot.v1"


def _iso(value: datetime, name: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.isoformat()


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _json_native(payload: Any) -> Any:
    return json.loads(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )


@dataclass(frozen=True)
class EntryOptionSnapshot:
    mode: str
    zone_low: float
    zone_high: float
    quote: float | None
    exact_quote: bool
    source_rule_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class StopOptionSnapshot:
    mode: str
    relation: str
    anchor_price: float | None
    stop_price: float | None
    exact_price: bool
    source_rule_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class ExitPolicySnapshot:
    mode: str
    primary_fraction: float | None
    remainder_fraction: float | None
    primary_target_price: float | None
    primary_target_object_ids: tuple[str, ...]
    remainder_target_price: float | None
    source_rule_ids: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class SourceExecutionPlanSnapshot:
    """Fail-closed outward representation of a SOURCE execution plan.

    The snapshot intentionally preserves *all* SOURCE-permitted entry and stop
    alternatives. It never ranks them and never collapses a zone to a quote.
    This is the boundary the backend/platform can display or persist without
    accidentally turning unresolved SOURCE semantics into an executable order.
    """

    schema: str
    event_id: str
    emitted_at: str
    setup_id: str
    physical_idea_id: str
    branch: str
    direction: str
    known_at: str
    entry_options: tuple[EntryOptionSnapshot, ...]
    stop_options: tuple[StopOptionSnapshot, ...]
    exit_policy: ExitPolicySnapshot
    invalidation_rules: tuple[str, ...]
    unresolved: tuple[str, ...]
    source_rule_ids: tuple[str, ...]
    technical_normalization_ids: tuple[str, ...]
    source_geometry_resolved: bool
    trade_entry_allowed: bool
    engine_version: str
    engine_git_commit: str
    dataset_id: str

    def __post_init__(self) -> None:
        if self.schema != SOURCE_EXECUTION_EVENT_SCHEMA:
            raise ValueError(f"unsupported execution snapshot schema: {self.schema!r}")
        if self.trade_entry_allowed:
            raise ValueError("trade_entry_allowed must remain false at the platform integration boundary")
        for name in (
            "event_id",
            "setup_id",
            "physical_idea_id",
            "branch",
            "direction",
            "engine_version",
            "engine_git_commit",
            "dataset_id",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        emitted = datetime.fromisoformat(self.emitted_at)
        known = datetime.fromisoformat(self.known_at)
        if emitted.tzinfo is None or emitted.utcoffset() is None:
            raise ValueError("emitted_at must be timezone-aware")
        if known.tzinfo is None or known.utcoffset() is None:
            raise ValueError("known_at must be timezone-aware")
        if emitted < known:
            raise ValueError("emitted_at cannot precede plan known_at")
        if self.source_geometry_resolved and self.unresolved:
            raise ValueError("source_geometry_resolved cannot be true while unresolved items remain")

    def to_dict(self) -> dict[str, Any]:
        # JSON-facing payloads must have stable JSON array semantics rather than
        # depending on Python tuple/list distinctions after persistence.
        return _json_native(asdict(self))

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_plan(
        cls,
        plan: SourceExecutionPlan,
        *,
        emitted_at: datetime,
        engine_version: str,
        engine_git_commit: str,
        dataset_id: str,
    ) -> "SourceExecutionPlanSnapshot":
        emitted = _iso(emitted_at, "emitted_at")
        known = _iso(plan.known_at, "known_at")

        entries = tuple(
            EntryOptionSnapshot(
                mode=option.mode.value,
                zone_low=option.zone_low,
                zone_high=option.zone_high,
                quote=option.quote,
                exact_quote=option.exact_quote,
                source_rule_ids=_dedupe(option.source_rule_ids),
                note=option.note,
            )
            for option in plan.entry_options
        )
        stops = tuple(
            StopOptionSnapshot(
                mode=option.mode.value,
                relation=option.relation,
                anchor_price=option.anchor_price,
                stop_price=option.stop_price,
                exact_price=option.exact_price,
                source_rule_ids=_dedupe(option.source_rule_ids),
                note=option.note,
            )
            for option in plan.stop_options
        )
        exit_policy = ExitPolicySnapshot(
            mode=plan.exit_policy.mode.value,
            primary_fraction=plan.exit_policy.primary_fraction,
            remainder_fraction=plan.exit_policy.remainder_fraction,
            primary_target_price=plan.exit_policy.primary_target_price,
            primary_target_object_ids=_dedupe(plan.exit_policy.primary_target_object_ids),
            remainder_target_price=plan.exit_policy.remainder_target_price,
            source_rule_ids=_dedupe(plan.exit_policy.source_rule_ids),
            unresolved=tuple(plan.exit_policy.unresolved),
        )
        unresolved = tuple(plan.unresolved)

        base: dict[str, Any] = {
            "schema": SOURCE_EXECUTION_EVENT_SCHEMA,
            "setup_id": plan.setup_id,
            "physical_idea_id": plan.physical_idea_id,
            "branch": plan.branch.value,
            "direction": plan.direction.value,
            "known_at": known,
            "entry_options": entries,
            "stop_options": stops,
            "exit_policy": exit_policy,
            "invalidation_rules": tuple(plan.invalidation_rules),
            "unresolved": unresolved,
            "source_rule_ids": _dedupe(plan.source_rule_ids),
            "technical_normalization_ids": _dedupe(plan.technical_normalization_ids),
            "source_geometry_resolved": bool(plan.execution_ready),
            "trade_entry_allowed": False,
            "engine_version": engine_version,
            "engine_git_commit": engine_git_commit,
            "dataset_id": dataset_id,
        }
        serializable = {
            **base,
            "entry_options": [asdict(item) for item in entries],
            "stop_options": [asdict(item) for item in stops],
            "exit_policy": asdict(exit_policy),
        }
        event_id = hashlib.sha256(
            json.dumps(
                serializable,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return cls(event_id=event_id, emitted_at=emitted, **base)
