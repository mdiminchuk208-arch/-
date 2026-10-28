from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Iterable

from crypto_bot.strategy.causal_objects import CausalSourceObject


STRATEGY_EVENT_SCHEMA = "crypto-bot.strategy-object-snapshot.v1"


def _aware_iso(value: datetime | None, name: str) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.isoformat()


def _price(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive when supplied")
    return number


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _json_native(payload: Any) -> Any:
    """Normalize immutable Python tuples into the exact JSON boundary shape."""
    return json.loads(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )


@dataclass(frozen=True)
class StrategyObjectSnapshot:
    """Immutable outward-facing snapshot of one Strategy Engine object.

    This is a transport contract only. It deliberately preserves the
    distinction between ``trade_eligible`` (a fact inside the engine's current
    object state) and ``trade_entry_allowed`` (financial execution authority).
    The latter is hard-disabled in this contract while the project remains
    fail-closed.

    ``entry_price``, ``stop_price`` and ``fta_price`` are optional transport
    fields. Their absence means the engine did not supply that geometry; the
    integration layer never invents it.
    """

    schema: str
    event_id: str
    emitted_at: str
    object_id: str
    object_type: str
    symbol: str
    timeframe: str
    direction: str | None
    status: str
    formation_at: str
    known_at: str
    confirmed_at: str | None
    invalidated_at: str | None
    formation_valid: bool
    trade_eligible: bool
    trade_entry_allowed: bool
    source_rule_ids: tuple[str, ...]
    technical_normalization_ids: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    parent_object_ids: tuple[str, ...]
    provenance: str
    source_branch_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    engine_version: str
    engine_git_commit: str
    dataset_id: str
    entry_price: float | None = None
    stop_price: float | None = None
    fta_price: float | None = None

    def __post_init__(self) -> None:
        if self.schema != STRATEGY_EVENT_SCHEMA:
            raise ValueError(f"unsupported strategy event schema: {self.schema!r}")
        if self.trade_entry_allowed:
            raise ValueError("trade_entry_allowed must remain false in the fail-closed integration contract")
        for name in (
            "event_id",
            "object_id",
            "object_type",
            "symbol",
            "timeframe",
            "status",
            "engine_version",
            "engine_git_commit",
            "dataset_id",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        parsed = {
            "emitted_at": datetime.fromisoformat(self.emitted_at),
            "formation_at": datetime.fromisoformat(self.formation_at),
            "known_at": datetime.fromisoformat(self.known_at),
            "confirmed_at": datetime.fromisoformat(self.confirmed_at) if self.confirmed_at else None,
            "invalidated_at": datetime.fromisoformat(self.invalidated_at) if self.invalidated_at else None,
        }
        for name, value in parsed.items():
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{name} must be timezone-aware")
        if parsed["known_at"] < parsed["formation_at"]:
            raise ValueError("known_at cannot precede formation_at")
        if parsed["emitted_at"] < parsed["known_at"]:
            raise ValueError("emitted_at cannot precede known_at")
        if parsed["confirmed_at"] is not None and parsed["confirmed_at"] < parsed["known_at"]:
            raise ValueError("confirmed_at cannot precede known_at")
        if parsed["invalidated_at"] is not None and parsed["invalidated_at"] < parsed["known_at"]:
            raise ValueError("invalidated_at cannot precede known_at")
        _price(self.entry_price, "entry_price")
        _price(self.stop_price, "stop_price")
        _price(self.fta_price, "fta_price")

    def to_dict(self) -> dict[str, Any]:
        # API/outbox payloads are JSON-native: arrays are lists rather than
        # Python tuples. The dataclass itself remains immutable internally.
        return _json_native(asdict(self))

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_source_object(
        cls,
        obj: CausalSourceObject,
        *,
        emitted_at: datetime,
        engine_version: str,
        engine_git_commit: str,
        dataset_id: str,
        source_branch_ids: Iterable[str] = (),
        evidence_ids: Iterable[str] = (),
        entry_price: float | None = None,
        stop_price: float | None = None,
        fta_price: float | None = None,
    ) -> "StrategyObjectSnapshot":
        emitted = _aware_iso(emitted_at, "emitted_at")
        formation = _aware_iso(obj.formation_at, "formation_at")
        known = _aware_iso(obj.known_at, "known_at")
        confirmed = _aware_iso(obj.confirmed_at, "confirmed_at")
        invalidated = _aware_iso(obj.invalidated_at, "invalidated_at")
        assert emitted is not None and formation is not None and known is not None

        base = {
            "schema": STRATEGY_EVENT_SCHEMA,
            "object_id": obj.object_id,
            "object_type": obj.object_type.value,
            "symbol": obj.symbol,
            "timeframe": obj.timeframe,
            "direction": obj.direction,
            "status": obj.status.value,
            "formation_at": formation,
            "known_at": known,
            "confirmed_at": confirmed,
            "invalidated_at": invalidated,
            "formation_valid": obj.formation_valid,
            "trade_eligible": obj.trade_eligible,
            "trade_entry_allowed": False,
            "source_rule_ids": _unique(obj.source_rule_ids),
            "technical_normalization_ids": _unique(obj.technical_normalization_ids),
            "rejection_reasons": tuple(obj.rejection_reasons),
            "parent_object_ids": _unique(obj.parent_object_ids),
            "provenance": obj.provenance,
            "source_branch_ids": _unique(source_branch_ids),
            "evidence_ids": _unique(evidence_ids),
            "engine_version": engine_version,
            "engine_git_commit": engine_git_commit,
            "dataset_id": dataset_id,
            "entry_price": _price(entry_price, "entry_price"),
            "stop_price": _price(stop_price, "stop_price"),
            "fta_price": _price(fta_price, "fta_price"),
        }

        fingerprint = hashlib.sha256(
            json.dumps(
                base,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return cls(event_id=fingerprint, emitted_at=emitted, **base)
