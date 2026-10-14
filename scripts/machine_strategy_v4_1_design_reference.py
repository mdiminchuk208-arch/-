"""Hand-fixture design oracle only; no market adapter, trading or financial engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext

FAMILIES = ("SFP", "OB", "STB", "BREAKER", "RANGE")
DIRECTIONS = ("LONG", "SHORT")
PHASE = {
    "EXECUTION": 0,
    "EXPOSURE_ENDED": 1,
    "CONTEXT": 2,
    "PREREQUISITES": 3,
    "PROPOSAL_CONF": 4,
    "CONTACT": 5,
    "EMIT": 6,
}


def canonical(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("FINITE_DECIMAL_REQUIRED")
    if value == 0:
        return "0"
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def identity(*args) -> str:
    payload = [canonical(a) if isinstance(a, Decimal) else a for a in args]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class POI:
    family: str
    direction: str
    native_tf: int
    formation_id: str
    parent_id: str
    formation_at: int
    reaction_at: int
    conf_at: int
    born_at: int
    conf_id: str
    low: Decimal
    high: Decimal
    refined_id: str = "refined_fixture"

    def __post_init__(self):
        if self.family not in FAMILIES or self.direction not in DIRECTIONS:
            raise ValueError("UNKNOWN_FAMILY_DIRECTION")
        if self.native_tf not in ((15,) if self.family in ("SFP", "OB") else (60, 240)):
            raise ValueError("WRONG_NATIVE_TF")
        for value in (self.formation_at, self.reaction_at, self.conf_at, self.born_at):
            if type(value) is not int or value < 0:
                raise ValueError("EXACT_CAUSAL_TIMESTAMP_REQUIRED")
        if self.low > self.high or not self.conf_id:
            raise ValueError("INVALID_GEOMETRY_OR_ORIGIN")
        canonical(self.low)
        canonical(self.high)
        if self.family == "RANGE" and self.low != self.high:
            raise ValueError("RANGE_BOUNDARY_MUST_BE_ZERO_WIDTH")

    @property
    def prerequisite_at(self):
        return max(self.formation_at, self.reaction_at, self.conf_at, self.born_at)

    @property
    def selected_id(self):
        if self.family in ("SFP", "OB"):
            return self.refined_id
        if self.family == "STB":
            return identity("M4_1_STB_BODY", self.formation_id, self.low, self.high)
        if self.family == "BREAKER":
            return identity(
                "M4_1_BREAKER_BODY", self.parent_id, self.formation_at, self.direction
            )
        return identity("M4_1_RANGE_BOUNDARY", self.parent_id, self.direction, self.low)


class WitnessState:
    """One selected physical POI with supplied causal context/limit-fill witnesses.

    Context admission and modeled fill facts are hand fixture inputs, not computed
    strategy signals or price execution. Production conformance remains a later gate.
    """

    def __init__(self, poi: POI):
        self.poi = poi
        self.eligibility_at = None
        self.context_ok = False
        self.consumed_at = None
        self.reserved_at = None
        self.filled_at = None
        self.emitted_at = None
        self.status = "WAIT_CONTEXT_FOR_POI_ELIGIBILITY"
        self.last_at = -1
        self.trace: list[tuple[int, str, str]] = []
        self.proposal_conf_id = None
        self.latest_conf_id = None
        self.exposure_active = False

    @property
    def deadline(self):
        return self.poi.formation_at + 57600

    def _eligible(self, at):
        if (
            self.eligibility_at is None
            and self.context_ok
            and at >= self.poi.prerequisite_at
        ):
            self.eligibility_at = at
            self.status = "ELIGIBLE"

    def apply(self, event):
        kind, at = event["kind"], event["at"]
        if kind not in PHASE or type(at) is not int or at < self.last_at:
            raise ValueError("UNKNOWN_OR_NONCAUSAL_EVENT")
        self.last_at = at
        if kind == "EXPOSURE_ENDED":
            if self.filled_at is None:
                raise ValueError("EXPOSURE_MARKER_REQUIRES_FILL_WITNESS")
            self.exposure_active = False
        elif kind == "CONTEXT":
            if type(event["admissible"]) is not bool:
                raise ValueError("EXACT_CONTEXT_PROOF_REQUIRED")
            self.context_ok = event["admissible"]
            if not self.context_ok and self.status == "PENDING":
                self.status = "RETIRED_CONTEXT"
            self._eligible(at)
        elif kind == "PREREQUISITES":
            if self.latest_conf_id is None:
                self.latest_conf_id = self.poi.conf_id
            self._eligible(at)
        elif kind == "PROPOSAL_CONF":
            self.latest_conf_id = event["id"]
        elif kind == "EMIT":
            self.proposal_conf_id = self.latest_conf_id
            self._eligible(at)
            if at >= self.deadline:
                result = "EXPIRED_PENDING"
            elif self.consumed_at is not None:
                result = "REJECT_SELECTED_POI_PRECONSUMED"
            elif self.reserved_at is not None:
                result = "REJECT_ALREADY_RESERVED"
            elif self.eligibility_at is None or not self.context_ok:
                result = "WAIT_CONTEXT_FOR_POI_ELIGIBILITY"
            else:
                self.reserved_at = self.emitted_at = at
                self.status = result = "PENDING"
            self.trace.append((at, kind, result))
            return
        elif kind == "EXECUTION":
            start = event["start"]
            if type(start) is not int or at - start != 900 or start < 0:
                raise ValueError("M15_EXECUTION_INTERVAL_REQUIRED")
            if type(event["modeled_fill"]) is not bool:
                raise ValueError("EXACT_FILL_WITNESS_REQUIRED")
            if self.status == "PENDING":
                if start >= self.deadline:
                    self.status = "EXPIRED_PENDING"
                elif (
                    self.emitted_at is not None
                    and start >= self.emitted_at
                    and event["modeled_fill"]
                ):
                    self.filled_at = start
                    self.status = "FILLED_WITNESS"
                    self.exposure_active = True
        elif kind == "CONTACT":
            start = event["start"]
            if type(start) is not int or at - start != self.poi.native_tf * 60:
                raise ValueError("NATIVE_CONTACT_INTERVAL_REQUIRED")
            if type(event["native_context_at_open"]) is not bool:
                raise ValueError("EXACT_NATIVE_CONTEXT_REQUIRED")
            known = event["native_context_known_at"]
            if type(known) is not int or known > start:
                raise ValueError("FUTURE_NATIVE_CONTEXT_PROOF")
            # Native-context-at-OPEN is an explicit hand proof. CLOSE context is
            # not a substitute. OHLC is never used until its completed event.
            low, high = Decimal(event["low"]), Decimal(event["high"])
            if not low.is_finite() or not high.is_finite() or low > high:
                raise ValueError("INVALID_CONTACT_GEOMETRY")
            intersects = low <= self.poi.high and high >= self.poi.low
            if (
                self.eligibility_at is not None
                and start >= self.eligibility_at
                and event["native_context_at_open"]
                and intersects
                and self.consumed_at is None
            ):
                self.consumed_at = at
                if self.status == "PENDING":
                    self.status = "RETIRED_CONTACT"
                # FILLED_WITNESS is retained; native CLOSE cannot undo it.
        self.trace.append((at, kind, self.status))

    def snapshot(self):
        return {
            "eligibility_at": self.eligibility_at,
            "consumed_at": self.consumed_at,
            "reserved_at": self.reserved_at,
            "filled_at": self.filled_at,
            "status": self.status,
            "trace": list(self.trace),
            "origin_conf_id": self.poi.conf_id
            if self.eligibility_at is not None
            else None,
            "proposal_selected_conf_id": self.proposal_conf_id,
            "exposure_active": self.exposure_active,
        }


def replay(poi, events, cutoff):
    state = WitnessState(poi)
    completed = [e for e in events if e["at"] <= cutoff]
    completed.append(
        {"kind": "PREREQUISITES", "at": poi.prerequisite_at}
    ) if poi.prerequisite_at <= cutoff else None
    for event in sorted(completed, key=lambda e: (e["at"], PHASE[e["kind"]])):
        state.apply(event)
    return state.snapshot()


def design_third():
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 50, ROUND_HALF_EVEN
        return canonical(Decimal(1) / Decimal(3))


def ledger_boundary(text):
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 80, ROUND_HALF_EVEN
        number = Decimal(text)
        if canonical(number) != text:
            raise ValueError("NONCANONICAL_BOUNDARY")
        return number


def design_quantity(contract_base, lot):
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 50, ROUND_HALF_EVEN
        count = ((Decimal(1) / contract_base) / lot).to_integral_value(
            rounding=ROUND_FLOOR
        ) * lot
        return canonical(count)


def planned_equal(direction):
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 50, ROUND_HALF_EVEN
        sign = Decimal(1 if direction == "LONG" else -1)
        cost = Decimal("0.0008")
        scale = abs(sign - 2 * cost)
        entry = Decimal(100) * scale
        stop = Decimal(99 if direction == "LONG" else 101) * scale
        unit = sign * (entry - stop) + cost * (entry + stop)
        target = (unit + (sign + 2 * cost) * entry) / (sign - 2 * cost)
        planned = sign * (target - entry) - 2 * cost * (entry + target)
        return canonical(unit), canonical(planned)
