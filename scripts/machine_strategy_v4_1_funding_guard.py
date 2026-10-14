"""Registered-synthetic-only funding guard for MACHINE_STRATEGY_v4.1 readiness.

No historical OKX funding series may enter this module before a later financial gate.
The purpose here is to freeze and test coherent adverse funding witness semantics only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext

from machine_strategy_v4_1_contracts import LEDGER_PRECISION, V41Reject, timestamp

VERSION = "MACHINE_STRATEGY_v4.1"
TRADE_ENTRY_ALLOWED = False
_MARKER = object()
_REGISTERED = {
    "LONG_POSITIVE_FUNDING",
    "SHORT_POSITIVE_FUNDING",
    "NEGATIVE_FUNDING",
    "NO_FUNDING",
    "SAME_TIMESTAMP_BOUNDARY",
}
_ISSUED: dict[int, "SyntheticFundingCapability"] = {}


@dataclass(frozen=True)
class SyntheticFundingCapability:
    marker: object
    fixture_name: str


def synthetic_capability(fixture_name: str) -> SyntheticFundingCapability:
    if fixture_name not in _REGISTERED:
        raise V41Reject("UNREGISTERED_SYNTHETIC_FUNDING_FIXTURE")
    capability = SyntheticFundingCapability(_MARKER, fixture_name)
    _ISSUED[id(capability)] = capability
    return capability


def _check(capability: SyntheticFundingCapability) -> None:
    if (
        not isinstance(capability, SyntheticFundingCapability)
        or capability.marker is not _MARKER
        or _ISSUED.get(id(capability)) is not capability
        or capability.fixture_name not in _REGISTERED
    ):
        raise V41Reject("NO_REGISTERED_SYNTHETIC_FUNDING_CAPABILITY")


def _ledger_decimal(value: object) -> Decimal:
    if isinstance(value, (bool, float)):
        raise V41Reject("REJECT_INEXACT_FUNDING_DECIMAL")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise V41Reject("REJECT_INVALID_FUNDING_DECIMAL") from exc
    if not parsed.is_finite():
        raise V41Reject("REJECT_NON_FINITE_FUNDING_DECIMAL")
    return parsed


def adverse_funding_witness(
    capability: SyntheticFundingCapability,
    *,
    direction: str,
    fill_time_bounds: tuple[int, int],
    exit_time_bounds: tuple[int, int],
    settlements: list[tuple[int, object, object]],
    quantity_base: object,
) -> dict:
    """Minimize signed funding cash across coherent -1/+1 event-slot witnesses."""
    _check(capability)
    if direction not in {"LONG", "SHORT"}:
        raise V41Reject("REJECT_DIRECTION")
    flo, fhi = map(timestamp, fill_time_bounds)
    xlo, xhi = map(timestamp, exit_time_bounds)
    if flo > fhi or xlo > xhi or flo > xhi:
        raise V41Reject("REJECT_FUNDING_TIME_BOUNDS")

    normalized = []
    for at, rate, price in settlements:
        when = timestamp(at)
        r = _ledger_decimal(rate)
        p = _ledger_decimal(price)
        if p <= 0:
            raise V41Reject("REJECT_FUNDING_MARK_PRICE")
        normalized.append((when, r, p))
    normalized.sort(key=lambda row: row[0])
    if len({row[0] for row in normalized}) != len(normalized):
        raise V41Reject("REJECT_DUPLICATE_FUNDING_SETTLEMENT")

    with localcontext() as ctx:
        ctx.prec = LEDGER_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        quantity = _ledger_decimal(quantity_base)
        if quantity <= 0:
            raise V41Reject("REJECT_FUNDING_QUANTITY")
        relevant = [row for row in normalized if flo <= row[0] <= xhi]
        fill_slots = {(flo, -1), (flo, 1), (fhi, -1), (fhi, 1)}
        exit_slots = {(xlo, -1), (xlo, 1), (xhi, -1), (xhi, 1)}
        for when, _, _ in relevant:
            if flo <= when <= fhi:
                fill_slots.update(((when, -1), (when, 1)))
            if xlo <= when <= xhi:
                exit_slots.update(((when, -1), (when, 1)))

        sign = Decimal(1 if direction == "LONG" else -1)
        candidates = []
        for fill_slot in sorted(fill_slots):
            for exit_slot in sorted(exit_slots):
                if fill_slot > exit_slot:
                    continue
                included = [
                    row for row in relevant if fill_slot < (row[0], 0) < exit_slot
                ]
                cash = sum(
                    (-sign * rate * quantity * price for _, rate, price in included),
                    Decimal(0),
                )
                candidates.append(
                    (
                        cash,
                        fill_slot,
                        exit_slot,
                        [row[0] for row in included],
                    )
                )
        if not candidates:
            raise V41Reject("WAIT_COHERENT_FUNDING_TIMELINE")
        cash, fill_slot, exit_slot, included_times = min(
            candidates, key=lambda row: (row[0], row[1], row[2])
        )
        return {
            "version": VERSION,
            "fixture": capability.fixture_name,
            "funding_cash": str(cash),
            "model_fill_event_slot": fill_slot,
            "model_exit_event_slot": exit_slot,
            "settlements_included": included_times,
            "precision": LEDGER_PRECISION,
            "rounding": "ROUND_HALF_EVEN",
            "slot_order": "-1 before same-timestamp settlement; +1 after",
            "historical_source_used": False,
            "trade_entry_allowed": False,
        }


def assert_historical_funding_blocked() -> None:
    raise V41Reject("HISTORICAL_V4_1_FUNDING_NOT_AUTHORIZED")
