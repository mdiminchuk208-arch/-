"""Non-financial frozen contracts for MACHINE_STRATEGY_v4.1 readiness.

This module implements the independently frozen selected-POI and arithmetic-scope
amendment only. It cannot authorize historical fills, exits, finance, PAPER or LIVE.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from hashlib import sha256

VERSION = "MACHINE_STRATEGY_v4.1"
TRADE_ENTRY_ALLOWED = False
DESIGN_PRECISION = 50
LEDGER_PRECISION = 80
PARENT_DEADLINE_SECONDS = 57600


class V41ContractError(ValueError):
    def __init__(self, reason: str):
        self.reason = str(reason)
        super().__init__(self.reason)


class V41Wait(V41ContractError):
    pass


class V41Reject(V41ContractError):
    pass


def timestamp(value: object) -> int:
    if type(value) is not int or value < 0:
        raise V41Reject("REJECT_INEXACT_TIMESTAMP")
    return value


def design_decimal(value: object) -> Decimal:
    if isinstance(value, (bool, float)):
        raise V41Reject("REJECT_INEXACT_DECIMAL")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise V41Reject("REJECT_INVALID_DECIMAL") from exc
    if not parsed.is_finite():
        raise V41Reject("REJECT_NON_FINITE_DECIMAL")
    with localcontext() as ctx:
        ctx.prec = DESIGN_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return +parsed


def ledger_decimal(serialized: str) -> Decimal:
    if not isinstance(serialized, str):
        raise V41Reject("REJECT_LEDGER_REQUIRES_CANONICAL_STRING")
    with localcontext() as ctx:
        ctx.prec = LEDGER_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        try:
            parsed = Decimal(serialized)
        except InvalidOperation as exc:
            raise V41Reject("REJECT_INVALID_LEDGER_DECIMAL") from exc
        if not parsed.is_finite():
            raise V41Reject("REJECT_NON_FINITE_DECIMAL")
        text = format(parsed, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if parsed == 0:
            text = "0"
        if text != serialized or +parsed != parsed:
            raise V41Reject("REJECT_NONCANONICAL_LEDGER_DECIMAL")
        return parsed


def canonical_decimal(value: object) -> str:
    parsed = design_decimal(value)
    if parsed == 0:
        return "0"
    text = format(parsed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"-0", "+0", ""}:
        return "0"
    return text


def _canonical_arg(value: object) -> object:
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    raise V41Reject("REJECT_NONCANONICAL_IDENTITY_ARGUMENT")


def physical_identity(label: str, *parts: object) -> str:
    if not isinstance(label, str) or not label:
        raise V41Reject("REJECT_IDENTITY_LABEL")
    payload = json.dumps(
        [label, *(_canonical_arg(part) for part in parts)],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def selected_poi_identity(
    *,
    family: str,
    existing_id: str | None = None,
    formation_id: str | None = None,
    source_parent_id: str | None = None,
    direction: str | None = None,
    body_low: object | None = None,
    body_high: object | None = None,
    breaker_formation_known_at: int | None = None,
    range_id: str | None = None,
    boundary_price: object | None = None,
) -> str:
    """Return the frozen physical selected-POI identity for one family."""
    if family in {"SFP", "OB"}:
        if not existing_id:
            raise V41Reject("REJECT_MISSING_REFINED_POI_ID")
        return existing_id
    if family == "STB":
        if not formation_id or body_low is None or body_high is None:
            raise V41Reject("REJECT_STB_IDENTITY_INPUT")
        return physical_identity(
            "M4_1_STB_BODY",
            formation_id,
            canonical_decimal(body_low),
            canonical_decimal(body_high),
        )
    if family == "BREAKER":
        if (
            not source_parent_id
            or breaker_formation_known_at is None
            or direction not in {"LONG", "SHORT"}
        ):
            raise V41Reject("REJECT_BREAKER_IDENTITY_INPUT")
        return physical_identity(
            "M4_1_BREAKER_BODY",
            source_parent_id,
            timestamp(breaker_formation_known_at),
            direction,
        )
    if family == "RANGE":
        if not range_id or direction not in {"LONG", "SHORT"} or boundary_price is None:
            raise V41Reject("REJECT_RANGE_IDENTITY_INPUT")
        return physical_identity(
            "M4_1_RANGE_BOUNDARY",
            range_id,
            direction,
            canonical_decimal(boundary_price),
        )
    raise V41Reject("REJECT_FAMILY")


@dataclass(frozen=True)
class SelectedPoiState:
    formation_id: str
    source_parent_id: str
    selected_poi_id: str
    selected_poi_kind: str
    selected_poi_native_tf: int
    formation_known_at: int
    reaction_required_at: int | None = None
    origin_conf_id: str | None = None
    origin_conf_known_at: int | None = None
    eligibility_at: int | None = None
    emission_decision_at: int | None = None
    proposal_selected_conf_id: str | None = None
    consumed_at: int | None = None
    reserved_at: int | None = None
    retired_at: int | None = None
    required_reaction_exempt_contact_at: int | None = None
    zone_born_at: int | None = None
    origin_bos_id: str | None = None
    expected_origin_conf_id: str | None = None
    expected_origin_conf_known_at: int | None = None

    def __post_init__(self) -> None:
        timestamp(self.formation_known_at)
        if self.selected_poi_native_tf not in {15, 60, 240}:
            raise V41Reject("REJECT_SELECTED_POI_NATIVE_TF")
        for name in (
            "reaction_required_at",
            "origin_conf_known_at",
            "eligibility_at",
            "emission_decision_at",
            "consumed_at",
            "reserved_at",
            "retired_at",
            "required_reaction_exempt_contact_at",
            "zone_born_at",
            "expected_origin_conf_known_at",
        ):
            value = getattr(self, name)
            if value is not None:
                timestamp(value)

    @property
    def deadline(self) -> int:
        return self.formation_known_at + PARENT_DEADLINE_SECONDS

    @property
    def terminal(self) -> bool:
        return self.consumed_at is not None or self.retired_at is not None


def latch_eligibility(
    state: SelectedPoiState,
    *,
    cutoff: int,
    origin_conf_id: str,
    origin_conf_known_at: int,
    family_prerequisites_complete: bool,
    m4_gate_admissible: bool,
    completed_context_admissible: bool,
) -> SelectedPoiState:
    """Latch FIRST admissible completed-M15 eligibility; later CONF cannot reset it."""
    cutoff = timestamp(cutoff)
    conf_at = timestamp(origin_conf_known_at)
    for flag in (
        family_prerequisites_complete,
        m4_gate_admissible,
        completed_context_admissible,
    ):
        if type(flag) is not bool:
            raise V41Reject("REJECT_INEXACT_ELIGIBILITY_PROOF")
    if state.eligibility_at is not None:
        return state
    if state.terminal:
        raise V41Reject("REJECT_TERMINAL_POI_ELIGIBILITY")
    if cutoff >= state.deadline:
        raise V41Reject("EXPIRED_PENDING")
    if not family_prerequisites_complete:
        raise V41Wait("WAIT_FAMILY_PREREQUISITES")
    if state.selected_poi_kind == "REFINED_M15_POI":
        if (
            state.zone_born_at is None
            or not state.origin_bos_id
            or not state.expected_origin_conf_id
            or state.expected_origin_conf_known_at is None
        ):
            raise V41Wait("WAIT_REFINED_ORIGIN_EVIDENCE")
        if (origin_conf_id, conf_at) != (
            state.expected_origin_conf_id,
            state.expected_origin_conf_known_at,
        ):
            raise V41Reject("REJECT_UNRELATED_REFINED_ORIGIN_CONF")
    lower = max(
        state.formation_known_at,
        state.reaction_required_at or state.formation_known_at,
        conf_at,
        state.zone_born_at or 0,
    )
    if cutoff < lower:
        raise V41Wait("WAIT_POI_ELIGIBILITY_LOWER_BOUND")
    if not m4_gate_admissible:
        raise V41Wait("WAIT_M4_GATE_FOR_POI_ELIGIBILITY")
    if not completed_context_admissible:
        raise V41Wait("WAIT_CONTEXT_FOR_POI_ELIGIBILITY")
    if not origin_conf_id:
        raise V41Reject("REJECT_ORIGIN_CONF_ID")
    return replace(
        state,
        origin_conf_id=origin_conf_id,
        origin_conf_known_at=conf_at,
        eligibility_at=cutoff,
    )


def native_contact(
    state: SelectedPoiState,
    *,
    native_bar_open: int,
    native_bar_close: int,
    intersects: bool,
    native_context_admissible_at_open: bool,
    is_required_reaction_contact: bool = False,
) -> SelectedPoiState:
    """Publish eligible native first-test at native CLOSE, never retroactively at OPEN."""
    opening = timestamp(native_bar_open)
    closing = timestamp(native_bar_close)
    if closing - opening != state.selected_poi_native_tf * 60:
        raise V41Reject("REJECT_NATIVE_BAR_INTERVAL")
    if any(
        type(v) is not bool
        for v in (
            intersects,
            native_context_admissible_at_open,
            is_required_reaction_contact,
        )
    ):
        raise V41Reject("REJECT_INEXACT_NATIVE_CONTACT_PROOF")
    if is_required_reaction_contact and closing == state.reaction_required_at:
        return replace(state, required_reaction_exempt_contact_at=closing)
    if state.eligibility_at is None:
        return state
    if state.terminal:
        return state
    # A native bar that opened before eligibility is wholly ineligible.
    if opening < state.eligibility_at:
        return state
    if not native_context_admissible_at_open or not intersects:
        return state
    # The required RANGE reaction and creation/formation events never self-consume.
    return replace(state, consumed_at=closing)


def register_emission(
    state: SelectedPoiState,
    *,
    emission_decision_at: int,
    proposal_selected_conf_id: str,
) -> SelectedPoiState:
    decision = timestamp(emission_decision_at)
    if state.eligibility_at is None:
        raise V41Wait("WAIT_SELECTED_POI_ELIGIBILITY")
    if decision >= state.deadline:
        raise V41Reject("EXPIRED_PENDING")
    if decision < state.eligibility_at:
        raise V41Reject("REJECT_EMISSION_BEFORE_ELIGIBILITY")
    if state.reserved_at is not None:
        raise V41Reject("REJECT_ALREADY_RESERVED")
    if state.consumed_at is not None and state.consumed_at <= decision:
        raise V41Reject("REJECT_SELECTED_POI_PRECONSUMED")
    if state.retired_at is not None and state.retired_at <= decision:
        raise V41Reject("REJECT_SELECTED_POI_RETIRED")
    if not proposal_selected_conf_id:
        raise V41Reject("REJECT_PROPOSAL_SELECTED_CONF_ID")
    return replace(
        state,
        emission_decision_at=decision,
        proposal_selected_conf_id=proposal_selected_conf_id,
        reserved_at=decision,
    )


def transport_design_value_to_ledger(value: object) -> tuple[str, Decimal]:
    """Serialize once at Decimal50; ledger Decimal80 consumes bytes without recomputation."""
    serialized = canonical_decimal(value)
    return serialized, ledger_decimal(serialized)


def payoff_equality_passes(target_net: object, stop_unit: object) -> bool:
    with localcontext() as ctx:
        ctx.prec = DESIGN_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return design_decimal(target_net) >= design_decimal(stop_unit)


def assert_financial_execution_blocked() -> None:
    raise V41Reject("HISTORICAL_FINANCIAL_EXECUTION_NOT_AUTHORIZED")
