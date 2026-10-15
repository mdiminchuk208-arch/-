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


@dataclass(frozen=True)
class SyntheticFundingCapability:
    marker: object
    fixture_name: str


def _authority():
    # Payloads are sealed in closure at startup; a label never licenses arbitrary data.
    payloads = {
        "LONG_POSITIVE_FUNDING": (
            "LONG",
            (100, 100),
            (300, 300),
            ((200, "0.001", "100"),),
            "1",
        ),
        "SHORT_POSITIVE_FUNDING": (
            "SHORT",
            (200, 200),
            (300, 300),
            ((200, "0.001", "100"),),
            "1",
        ),
        "SAME_TIMESTAMP_BOUNDARY": (
            "LONG",
            (200, 200),
            (300, 300),
            ((200, "0.001", "100"), (300, "0.001", "100")),
            "1",
        ),
        "NEGATIVE_FUNDING": (
            "LONG",
            (100, 100),
            (300, 300),
            ((200, "-0.001", "100"),),
            "1",
        ),
        "NO_FUNDING": ("LONG", (100, 100), (300, 300), (), "1"),
    }
    issued = {}

    def mint(name):
        if name not in payloads:
            raise V41Reject("UNREGISTERED_SYNTHETIC_FUNDING_FIXTURE")
        cap = SyntheticFundingCapability(object(), name)
        issued[cap.marker] = (cap, payloads[name])
        return cap

    def check(cap, payload):
        record = issued.get(getattr(cap, "marker", None))
        if record is None or record[0] is not cap:
            raise V41Reject("NO_REGISTERED_SYNTHETIC_FUNDING_CAPABILITY")
        if record[1] != payload:
            raise V41Reject("UNREGISTERED_SYNTHETIC_FUNDING_INPUT")

    return mint, check


synthetic_capability, _check = _authority()


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
    normalized_payload = (
        direction,
        tuple(fill_time_bounds),
        tuple(exit_time_bounds),
        tuple((at, str(rate), str(price)) for at, rate, price in settlements),
        str(quantity_base),
    )
    _check(capability, normalized_payload)
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
