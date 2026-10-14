"""Pure non-financial readiness contracts for MACHINE_STRATEGY_v4.

This module implements frozen design semantics only.  It does not load historical
strategy outcomes, simulate positions, compute qualification metrics, or enable
trading.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Decimal,
    InvalidOperation,
    localcontext,
)

VERSION = "MACHINE_STRATEGY_v4"
TRADE_ENTRY_ALLOWED = False
BASE_COST_PER_LEG = Decimal("0.0008")
DOUBLED_COST_PER_LEG = Decimal("0.0016")
PARENT_DEADLINE_SECONDS = 57600


class V4ContractError(ValueError):
    """Deterministic contract violation."""

    def __init__(self, reason):
        self.reason = str(reason)
        super().__init__(self.reason)


class V4Wait(V4ContractError):
    pass


class V4Reject(V4ContractError):
    pass


def dec(value) -> Decimal:
    if isinstance(value, (bool, float)):
        raise V4Reject("REJECT_INEXACT_DECIMAL")
    try:
        value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise V4Reject("REJECT_INVALID_DECIMAL") from exc
    if not value.is_finite():
        raise V4Reject("REJECT_NON_FINITE_DECIMAL")
    return value


def timestamp(value) -> int:
    if type(value) is not int or value < 0:
        raise V4Reject("REJECT_INEXACT_TIMESTAMP")
    return value


def _floor_to_tick(value: Decimal, tick: Decimal) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def _ceil_to_tick(value: Decimal, tick: Decimal) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def classify_approach(
    *,
    direction: str,
    reaction_at: int,
    selected_conf: Mapping | None,
    opposing_events: Sequence[Mapping],
    decision_at: int,
    data_complete: bool,
    structurally_retired: bool,
) -> dict:
    """Apply the frozen M4_APPROACH priority without P&L inputs."""
    if direction not in {"LONG", "SHORT"}:
        raise V4Reject("REJECT_DIRECTION")
    if not data_complete:
        raise V4Wait("WAIT_REQUIRED_CAUSAL_EVIDENCE")
    if structurally_retired:
        return {"state": "APPROACH_INVALID", "reason": "STRUCTURAL_RETIREMENT"}
    if selected_conf is None:
        raise V4Wait("WAIT_REFINEMENT_BOS_CONF")
    timestamp(reaction_at)
    timestamp(decision_at)
    conf_at = timestamp(selected_conf["known_at"])
    if not (reaction_at < conf_at <= decision_at):
        raise V4Wait("WAIT_REQUIRED_CAUSAL_EVIDENCE")
    if selected_conf.get("direction") != direction:
        raise V4Reject("REJECT_SELECTED_CONFIRMATION_DIRECTION")

    visible = [
        event
        for event in opposing_events
        if reaction_at < timestamp(event["known_at"]) <= decision_at
    ]
    dual = [event for event in visible if timestamp(event["known_at"]) == conf_at]
    later = [event for event in visible if timestamp(event["known_at"]) > conf_at]
    if dual:
        raise V4Wait("WAIT_DUAL_OPPOSING_EVENT")
    if later:
        raise V4Wait("WAIT_RECONFIRMATION")
    return {
        "state": "APPROACH_CORRECTIVE" if visible else "APPROACH_CLEAN",
        "reason": None,
        "opposing_event_ids": [str(event.get("id", "")) for event in visible],
    }


def target_lifecycle_ok(
    *, direction: str, completed_close, raw_fta, inward_target
) -> None:
    close = dec(completed_close)
    raw = dec(raw_fta)
    target = dec(inward_target)
    if direction == "LONG":
        if close >= raw:
            raise V4Reject("FTA_ALREADY_COMPLETED")
        if close >= target:
            raise V4Reject("EXECUTABLE_TARGET_ALREADY_COMPLETED")
    elif direction == "SHORT":
        if close <= raw:
            raise V4Reject("FTA_ALREADY_COMPLETED")
        if close <= target:
            raise V4Reject("EXECUTABLE_TARGET_ALREADY_COMPLETED")
    else:
        raise V4Reject("REJECT_DIRECTION")


def executable_plan(
    *,
    direction: str,
    raw_entry,
    protective_boundary,
    raw_fta,
    structural_low,
    structural_high,
    tick,
) -> dict:
    """Build one scenario plan under the frozen H04 technical envelope."""
    entry_raw, boundary, fta = map(dec, (raw_entry, protective_boundary, raw_fta))
    low, high, tick_value = map(dec, (structural_low, structural_high, tick))
    if min(entry_raw, boundary, fta, low, high) <= 0 or tick_value <= 0 or low > high:
        raise V4Reject("REJECT_EXECUTABLE_ZONE_INPUT")
    if not low <= entry_raw <= high:
        raise V4Reject("REJECT_RAW_ENTRY_OUTSIDE_STRUCTURAL_ZONE")
    exec_low, exec_high = low - tick_value, high + tick_value

    if direction == "LONG":
        entry = _floor_to_tick(entry_raw, tick_value)
        stop = _ceil_to_tick(boundary, tick_value) - tick_value
        target = _ceil_to_tick(fta, tick_value) - tick_value
        geometry = Decimal(0) < stop < entry < target
    elif direction == "SHORT":
        entry = _ceil_to_tick(entry_raw, tick_value)
        stop = _floor_to_tick(boundary, tick_value) + tick_value
        target = _floor_to_tick(fta, tick_value) + tick_value
        geometry = Decimal(0) < target < entry < stop
    else:
        raise V4Reject("REJECT_DIRECTION")

    if not exec_low <= entry <= exec_high:
        raise V4Reject("REJECT_ROUNDED_ENTRY_OUTSIDE_EXECUTABLE_ZONE")
    if not geometry:
        raise V4Reject("REJECT_EXECUTABLE_GEOMETRY")
    return {
        "entry": entry,
        "stop": stop,
        "target": target,
        "exec_low": exec_low,
        "exec_high": exec_high,
        "tick": tick_value,
    }


def planned_payoff_gate(*, direction: str, entry, stop, target) -> dict:
    """Frozen H05 gate: doubled-cost target net >= one base-cost stop unit."""
    entry_value, stop_value, target_value = map(dec, (entry, stop, target))
    direction_sign = Decimal(
        1 if direction == "LONG" else -1 if direction == "SHORT" else 0
    )
    if not direction_sign:
        raise V4Reject("REJECT_DIRECTION")
    if not (
        0 < stop_value < entry_value < target_value
        if direction == "LONG"
        else 0 < target_value < entry_value < stop_value
    ):
        raise V4Reject("REJECT_EXECUTABLE_GEOMETRY")
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_EVEN
        stop_unit = direction_sign * (entry_value - stop_value) + BASE_COST_PER_LEG * (
            entry_value + stop_value
        )
        target_net = direction_sign * (
            target_value - entry_value
        ) - DOUBLED_COST_PER_LEG * (entry_value + target_value)
        if stop_unit <= 0:
            raise V4Reject("REJECT_NONPOSITIVE_PLANNED_STOP_UNIT")
        ratio = target_net / stop_unit
        if target_net < stop_unit:
            raise V4Reject("REJECT_INSUFFICIENT_STRUCTURAL_PAYOFF")
        return {
            "planned_stop_unit": stop_unit,
            "net_target_doubled": target_net,
            "ratio": ratio,
        }


def pending_alive(
    *,
    formation_known_at: int,
    bar_open_at: int,
    lifecycle_flags: Mapping[str, bool],
) -> bool:
    """Half-open structural lifetime for a PENDING order only."""
    deadline = timestamp(formation_known_at) + PARENT_DEADLINE_SECONDS
    opening = timestamp(bar_open_at)
    if opening < formation_known_at:
        raise V4Reject("REJECT_PRE_FORMATION_LIFECYCLE")
    if lifecycle_flags.get("data_integrity_stop"):
        raise V4Wait("UNKNOWN_DATA_GAP")
    if opening >= deadline:
        return False
    terminal = (
        "structural_break",
        "source_retired",
        "context_invalid",
        "poi_consumed",
        "refinement_stale",
        "target_completed",
        "data_integrity_stop",
    )
    if any(
        type(lifecycle_flags[k]) is not bool for k in terminal if k in lifecycle_flags
    ):
        raise V4Reject("REJECT_LIFECYCLE_FLAG_TYPE")
    return not any(lifecycle_flags.get(name, False) for name in terminal)


_FORBIDDEN_TELEMETRY_KEYS = {
    "pnl",
    "net_pnl",
    "gross_pnl",
    "win",
    "loss",
    "profit_factor",
    "expectancy",
    "mfe",
    "mae",
    "exit_price",
    "net_r",
    "gross_r",
}


@dataclass
class GateTelemetry:
    """Write-only decision sink; snapshots are detached diagnostic copies."""

    formation_id: str
    physical_bucket_id: str
    source_family: str
    direction: str
    formation_known_at: int
    _events: list[dict] = field(default_factory=list, repr=False)
    _first: set[str] = field(default_factory=set, repr=False)

    def emit(self, record: Mapping) -> None:
        def check(value):
            if isinstance(value, Mapping):
                if {str(k).lower() for k in value} & _FORBIDDEN_TELEMETRY_KEYS:
                    raise V4Reject("REJECT_OUTCOME_FIELD_IN_TELEMETRY")
                for v in value.values():
                    check(v)
            elif isinstance(value, (list, tuple)):
                for v in value:
                    check(v)

        check(record)
        item = deepcopy(dict(record))
        # Legacy test aliases are normalized at this observer-only boundary.
        if "gate" in item:
            item["gate_name"] = item.pop("gate")
        if "evaluated_at" in item:
            item["known_at"] = item.pop("evaluated_at")
        if "status" in item:
            item["event_type"] = item.pop("status")
        for key in ("gate_name", "known_at", "event_type"):
            if key not in item:
                raise V4Reject("REJECT_TELEMETRY_SCHEMA")
        item.setdefault("decision_cutoff", item["known_at"])
        if timestamp(item["known_at"]) > timestamp(item["decision_cutoff"]):
            raise V4Reject("REJECT_FUTURE_TELEMETRY")
        if item["event_type"] not in {
            "FIRST_EVAL",
            "PASS",
            "WAIT",
            "REJECT",
            "RETIRE",
            "ORDER_EMIT",
            "FILL",
            "EXIT",
            "EOF_CENSOR",
        }:
            raise V4Reject("REJECT_TELEMETRY_EVENT")
        item.setdefault("context_id", None)
        item.setdefault("approach_state", None)
        item.setdefault("reason_code", None)
        item.update(
            formation_id=self.formation_id,
            physical_bucket_id=self.physical_bucket_id,
            family=self.source_family,
            direction=self.direction,
            formation_known_at=self.formation_known_at,
        )
        gate = item["gate_name"]
        if gate not in self._first and item["event_type"] != "FIRST_EVAL":
            self._events.append({**item, "event_type": "FIRST_EVAL"})
        self._first.add(gate)
        self._events.append(item)

    def snapshot(self) -> dict:
        return deepcopy(
            {
                "formation_id": self.formation_id,
                "physical_bucket_id": self.physical_bucket_id,
                "source_family": self.source_family,
                "direction": self.direction,
                "formation_known_at": self.formation_known_at,
                "events": self._events,
                "trade_entry_allowed": False,
            }
        )
