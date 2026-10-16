from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from crypto_bot.common.models import Candle


class SourceObjectType(str, Enum):
    SWING = "swing"
    STRUCTURE = "structure"
    LIQUIDITY_POOL = "liquidity_pool"
    POI = "poi"
    ORDER_BLOCK = "ob"
    BREAKER = "breaker"
    SFP = "sfp"
    STB_BTS = "stb_bts"
    RANGE = "range"
    FVG = "fvg"
    SETUP = "setup"
    PHYSICAL_IDEA = "physical_idea"


class ObjectStatus(str, Enum):
    FORMED = "FORMED"
    KNOWN = "KNOWN"
    CONFIRMED = "CONFIRMED"
    WAITING = "WAITING"
    READY = "READY"
    INVALIDATED = "INVALIDATED"
    CANCELLED = "CANCELLED"


class RejectionCategory(str, Enum):
    OBJECT_INVALID_SOURCE = "OBJECT_INVALID_SOURCE"
    WAIT_CONFIRMATION = "WAIT_CONFIRMATION"
    WAIT_ENTRY_CHAIN = "WAIT_ENTRY_CHAIN"
    WAIT_UNRESOLVED_SOURCE_RULE = "WAIT_UNRESOLVED_SOURCE_RULE"
    SETUP_REJECTED_SOURCE = "SETUP_REJECTED_SOURCE"
    PROJECT_POLICY_DISABLED = "PROJECT_POLICY_DISABLED"
    CANCELLED_AFTER_READY = "CANCELLED_AFTER_READY"


class LifecycleEventKind(str, Enum):
    FORMATION = "FORMATION"
    KNOWN = "KNOWN"
    CONFIRMATION = "CONFIRMATION"
    TRADE_ELIGIBILITY = "TRADE_ELIGIBILITY"
    REJECTION = "REJECTION"
    INVALIDATION = "INVALIDATION"
    CANCELLATION = "CANCELLATION"


@dataclass(frozen=True)
class LifecycleEvent:
    kind: LifecycleEventKind
    at: datetime
    status: ObjectStatus
    trade_eligible: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.at, "event.at")


@dataclass(frozen=True)
class HistoricalState:
    at: datetime
    status: ObjectStatus
    formation_valid: bool
    trade_eligible: bool
    confirmed_at: datetime | None
    invalidated_at: datetime | None
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class CausalSourceObject:
    object_id: str
    object_type: SourceObjectType
    symbol: str
    timeframe: str
    direction: str | None
    formation_at: datetime
    known_at: datetime
    confirmed_at: datetime | None = None
    invalidated_at: datetime | None = None
    formation_valid: bool = True
    trade_eligible: bool = False
    status: ObjectStatus = ObjectStatus.KNOWN
    source_rule_ids: tuple[str, ...] = ()
    technical_normalization_ids: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    parent_object_ids: tuple[str, ...] = ()
    provenance: str = ""
    lifecycle: tuple[LifecycleEvent, ...] = ()

    def __post_init__(self) -> None:
        if not self.object_id or not self.symbol or not self.timeframe:
            raise ValueError("object_id, symbol and timeframe are required")
        _require_aware(self.formation_at, "formation_at")
        _require_aware(self.known_at, "known_at")
        if self.known_at < self.formation_at:
            raise ValueError("known_at cannot precede formation_at")
        if self.confirmed_at is not None:
            _require_aware(self.confirmed_at, "confirmed_at")
            if self.confirmed_at < self.known_at:
                raise ValueError("confirmed_at cannot precede known_at")
        if self.invalidated_at is not None:
            _require_aware(self.invalidated_at, "invalidated_at")
            if self.invalidated_at < self.known_at:
                raise ValueError("invalidated_at cannot precede known_at")
        if not self.formation_valid and self.trade_eligible:
            raise ValueError("source-invalid object cannot be trade eligible")
        if self.status in (ObjectStatus.INVALIDATED, ObjectStatus.CANCELLED) and self.trade_eligible:
            raise ValueError("invalidated/cancelled object cannot be trade eligible")
        previous: datetime | None = None
        for event in self.lifecycle:
            if previous is not None and event.at < previous:
                raise ValueError("lifecycle events must be chronological")
            previous = event.at

    @classmethod
    def formed(cls, *, object_type: SourceObjectType, symbol: str, timeframe: str | int,
               direction: str | None, formation_at: datetime, known_at: datetime,
               identity_parts: Mapping[str, Any], source_rule_ids: Iterable[str] = (),
               technical_normalization_ids: Iterable[str] = (), parent_object_ids: Iterable[str] = (),
               provenance: str, confirmed_at: datetime | None = None) -> "CausalSourceObject":
        object_id = stable_object_id(object_type=object_type, symbol=symbol, timeframe=timeframe,
                                     direction=direction, formation_at=formation_at,
                                     identity_parts=identity_parts)
        status = ObjectStatus.CONFIRMED if confirmed_at is not None else ObjectStatus.KNOWN
        lifecycle = [LifecycleEvent(LifecycleEventKind.FORMATION, formation_at, ObjectStatus.FORMED, False),
                     LifecycleEvent(LifecycleEventKind.KNOWN, known_at, ObjectStatus.KNOWN, False)]
        if confirmed_at is not None:
            lifecycle.append(LifecycleEvent(LifecycleEventKind.CONFIRMATION, confirmed_at,
                                            ObjectStatus.CONFIRMED, False))
        return cls(object_id=object_id, object_type=object_type, symbol=symbol, timeframe=str(timeframe),
                   direction=direction, formation_at=formation_at, known_at=known_at,
                   confirmed_at=confirmed_at, formation_valid=True, trade_eligible=False,
                   status=status, source_rule_ids=tuple(source_rule_ids),
                   technical_normalization_ids=tuple(technical_normalization_ids),
                   parent_object_ids=tuple(parent_object_ids), provenance=provenance,
                   lifecycle=tuple(lifecycle))

    def confirm(self, at: datetime, reason: str | None = None) -> "CausalSourceObject":
        _at_or_after(at, self.known_at, "confirmation")
        if self.invalidated_at is not None and at >= self.invalidated_at:
            raise ValueError("cannot confirm at/after invalidation")
        event = LifecycleEvent(LifecycleEventKind.CONFIRMATION, at, ObjectStatus.CONFIRMED,
                               self.trade_eligible, reason)
        return replace(self, confirmed_at=at, status=ObjectStatus.CONFIRMED,
                       lifecycle=self.lifecycle + (event,))

    def set_trade_eligible(self, eligible: bool, at: datetime,
                           reason: str | None = None) -> "CausalSourceObject":
        _at_or_after(at, self.known_at, "trade eligibility")
        if eligible and (not self.formation_valid or
                         (self.invalidated_at is not None and at >= self.invalidated_at)):
            raise ValueError("invalid object cannot become trade eligible")
        status = ObjectStatus.READY if eligible else ObjectStatus.WAITING
        event = LifecycleEvent(LifecycleEventKind.TRADE_ELIGIBILITY, at, status, eligible, reason)
        return replace(self, trade_eligible=eligible, status=status,
                       lifecycle=self.lifecycle + (event,))

    def reject(self, category: RejectionCategory, at: datetime,
               reason: str | None = None) -> "CausalSourceObject":
        _at_or_after(at, self.known_at, "rejection")
        token = category.value if reason is None else f"{category.value}:{reason}"
        event = LifecycleEvent(LifecycleEventKind.REJECTION, at, ObjectStatus.WAITING, False, token)
        formation_valid = self.formation_valid and category != RejectionCategory.OBJECT_INVALID_SOURCE
        return replace(self, formation_valid=formation_valid, trade_eligible=False,
                       status=ObjectStatus.WAITING,
                       rejection_reasons=self.rejection_reasons + (token,),
                       lifecycle=self.lifecycle + (event,))

    def invalidate(self, at: datetime, reason: str) -> "CausalSourceObject":
        """Record a new lifecycle fact without rewriting historical formation validity."""
        _at_or_after(at, self.known_at, "invalidation")
        if self.invalidated_at is not None:
            if at == self.invalidated_at:
                return self
            raise ValueError("object already invalidated")
        event = LifecycleEvent(LifecycleEventKind.INVALIDATION, at, ObjectStatus.INVALIDATED,
                               False, reason)
        return replace(self, invalidated_at=at, trade_eligible=False,
                       status=ObjectStatus.INVALIDATED,
                       rejection_reasons=self.rejection_reasons + (reason,),
                       lifecycle=self.lifecycle + (event,))

    def cancel(self, at: datetime,
               reason: str = RejectionCategory.CANCELLED_AFTER_READY.value) -> "CausalSourceObject":
        _at_or_after(at, self.known_at, "cancellation")
        event = LifecycleEvent(LifecycleEventKind.CANCELLATION, at, ObjectStatus.CANCELLED,
                               False, reason)
        return replace(self, trade_eligible=False, status=ObjectStatus.CANCELLED,
                       rejection_reasons=self.rejection_reasons + (reason,),
                       lifecycle=self.lifecycle + (event,))

    def state_at(self, at: datetime) -> HistoricalState:
        _require_aware(at, "state_at")
        if at < self.formation_at:
            raise ValueError("object had not formed yet")
        status = ObjectStatus.FORMED
        eligible = False
        confirmed_at = None
        invalidated_at = None
        reasons: list[str] = []
        formation_valid = True
        for event in self.lifecycle:
            if event.at > at:
                break
            status = event.status
            eligible = event.trade_eligible
            if event.kind == LifecycleEventKind.CONFIRMATION:
                confirmed_at = event.at
            elif event.kind == LifecycleEventKind.INVALIDATION:
                invalidated_at = event.at
            elif event.kind == LifecycleEventKind.REJECTION and event.reason:
                reasons.append(event.reason)
                if event.reason.startswith(RejectionCategory.OBJECT_INVALID_SOURCE.value):
                    formation_valid = False
            elif event.kind == LifecycleEventKind.CANCELLATION and event.reason:
                reasons.append(event.reason)
        return HistoricalState(at, status, formation_valid, eligible, confirmed_at,
                               invalidated_at, tuple(reasons))


class CausalObjectRegistry:
    """Append-only object store. Trade admission never controls object existence."""
    def __init__(self) -> None:
        self._objects: dict[str, CausalSourceObject] = {}

    def add(self, obj: CausalSourceObject) -> CausalSourceObject:
        existing = self._objects.get(obj.object_id)
        if existing is not None and existing != obj:
            raise ValueError(f"stable object id collision: {obj.object_id}")
        self._objects[obj.object_id] = obj
        return obj

    def replace(self, obj: CausalSourceObject) -> CausalSourceObject:
        if obj.object_id not in self._objects:
            raise KeyError(obj.object_id)
        self._objects[obj.object_id] = obj
        return obj

    def get(self, object_id: str) -> CausalSourceObject:
        return self._objects[object_id]

    def objects_known_by(self, at: datetime) -> tuple[CausalSourceObject, ...]:
        _require_aware(at, "known_by")
        return tuple(sorted((o for o in self._objects.values() if o.known_at <= at),
                            key=lambda o: o.object_id))

    def __len__(self) -> int:
        return len(self._objects)


_FORBIDDEN_IDENTITY_KEYS = ("outcome", "pnl", "profit", "loss", "win", "mfe", "mae",
                            "future", "cancel", "ranking", "rank", "score", "project_policy")


def stable_object_id(*, object_type: SourceObjectType, symbol: str, timeframe: str | int,
                     direction: str | None, formation_at: datetime,
                     identity_parts: Mapping[str, Any]) -> str:
    """Create a deterministic ID from facts available at formation time only."""
    _require_aware(formation_at, "formation_at")
    _reject_future_identity_fields(identity_parts)
    payload = {"object_type": object_type.value, "symbol": symbol, "timeframe": str(timeframe),
               "direction": direction, "formation_at": formation_at.isoformat(),
               "identity_parts": _canonical(identity_parts)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()[:32]


def require_closed_candles(candles: Sequence[Candle], *,
                           decision_at: datetime | None = None) -> None:
    if decision_at is not None:
        _require_aware(decision_at, "decision_at")
    previous_close = None
    for candle in candles:
        if not candle.is_closed:
            raise ValueError("unfinished candle is forbidden in PURE_SOURCE")
        if decision_at is not None and candle.close_time > decision_at:
            raise ValueError("future candle close is forbidden in PURE_SOURCE")
        if previous_close is not None and candle.close_time <= previous_close:
            raise ValueError("candles must be strictly chronological")
        previous_close = candle.close_time


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        _require_aware(value, "identity datetime")
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported identity value: {type(value).__name__}")


def _reject_future_identity_fields(value: Any, path: str = "identity_parts") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(token in key_text for token in _FORBIDDEN_IDENTITY_KEYS):
                raise ValueError(f"future/outcome/project field forbidden in stable ID: {path}.{key}")
            _reject_future_identity_fields(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_future_identity_fields(item, f"{path}[{index}]")


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _at_or_after(value: datetime, floor: datetime, name: str) -> None:
    _require_aware(value, name)
    if value < floor:
        raise ValueError(f"{name} cannot precede known_at")
