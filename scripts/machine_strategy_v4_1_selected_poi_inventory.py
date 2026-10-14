"""Observer/source-only selected-POI inventory for MACHINE_STRATEGY_v4.1.

The inventory is intentionally unable to execute positions or compute financial
outcomes. It exists to make preproposal eligibility and native first-test lifecycle
deterministic on completed data before a future H1 proposal exists.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
from typing import Mapping

from machine_strategy_v4_1_contracts import (
    SelectedPoiState,
    V41Reject,
    V41Wait,
    latch_eligibility,
    native_contact,
    register_emission,
    selected_poi_identity,
    timestamp,
)

VERSION = "MACHINE_STRATEGY_v4.1"
TRADE_ENTRY_ALLOWED = False


class SelectedPoiInventory:
    def __init__(self) -> None:
        self._states: dict[str, SelectedPoiState] = {}
        self._events: list[dict] = []

    def register(
        self,
        *,
        family: str,
        formation_id: str,
        source_parent_id: str,
        native_tf: int,
        formation_known_at: int,
        reaction_required_at: int | None,
        existing_id: str | None = None,
        direction: str | None = None,
        body_low: object | None = None,
        body_high: object | None = None,
        breaker_formation_known_at: int | None = None,
        range_id: str | None = None,
        boundary_price: object | None = None,
    ) -> SelectedPoiState:
        selected_id = selected_poi_identity(
            family=family,
            existing_id=existing_id,
            formation_id=formation_id,
            source_parent_id=source_parent_id,
            direction=direction,
            body_low=body_low,
            body_high=body_high,
            breaker_formation_known_at=breaker_formation_known_at,
            range_id=range_id,
            boundary_price=boundary_price,
        )
        if selected_id in self._states:
            existing = self._states[selected_id]
            if (
                existing.formation_id != formation_id
                or existing.source_parent_id != source_parent_id
                or existing.selected_poi_native_tf != native_tf
            ):
                raise V41Reject("REJECT_SELECTED_POI_IDENTITY_COLLISION")
            return existing
        kind = {
            "SFP": "REFINED_M15_POI",
            "OB": "REFINED_M15_POI",
            "STB": "STB_BODY",
            "BREAKER": "BREAKER_BODY",
            "RANGE": "RANGE_BOUNDARY",
        }.get(family)
        if kind is None:
            raise V41Reject("REJECT_FAMILY")
        state = SelectedPoiState(
            formation_id=formation_id,
            source_parent_id=source_parent_id,
            selected_poi_id=selected_id,
            selected_poi_kind=kind,
            selected_poi_native_tf=native_tf,
            formation_known_at=timestamp(formation_known_at),
            reaction_required_at=(
                timestamp(reaction_required_at)
                if reaction_required_at is not None
                else None
            ),
        )
        self._states[selected_id] = state
        self._events.append(
            {
                "event": "REGISTER",
                "selected_poi_id": selected_id,
                "family": family,
                "known_at": formation_known_at,
            }
        )
        return state

    def latch_m15(
        self,
        selected_poi_id: str,
        *,
        cutoff: int,
        origin_conf_id: str,
        origin_conf_known_at: int,
        family_prerequisites_complete: bool,
        m4_gate_admissible: bool,
        completed_context_admissible: bool,
    ) -> SelectedPoiState:
        state = self._states[selected_poi_id]
        before = state.eligibility_at
        state = latch_eligibility(
            state,
            cutoff=cutoff,
            origin_conf_id=origin_conf_id,
            origin_conf_known_at=origin_conf_known_at,
            family_prerequisites_complete=family_prerequisites_complete,
            m4_gate_admissible=m4_gate_admissible,
            completed_context_admissible=completed_context_admissible,
        )
        self._states[selected_poi_id] = state
        if before is None and state.eligibility_at is not None:
            self._events.append(
                {
                    "event": "ELIGIBILITY_LATCH",
                    "selected_poi_id": selected_poi_id,
                    "origin_conf_id": state.origin_conf_id,
                    "known_at": state.eligibility_at,
                }
            )
        return state

    def observe_native_bar(
        self,
        selected_poi_id: str,
        *,
        native_bar_open: int,
        native_bar_close: int,
        intersects: bool,
        native_context_admissible_at_open: bool,
        is_required_reaction_contact: bool = False,
    ) -> SelectedPoiState:
        state = self._states[selected_poi_id]
        previous_consumed = state.consumed_at
        state = native_contact(
            state,
            native_bar_open=native_bar_open,
            native_bar_close=native_bar_close,
            intersects=intersects,
            native_context_admissible_at_open=native_context_admissible_at_open,
            is_required_reaction_contact=is_required_reaction_contact,
        )
        self._states[selected_poi_id] = state
        if state.required_reaction_exempt_contact_at == native_bar_close:
            self._events.append(
                {
                    "event": "REQUIRED_REACTION_EXEMPT",
                    "selected_poi_id": selected_poi_id,
                    "known_at": native_bar_close,
                }
            )
        if previous_consumed is None and state.consumed_at is not None:
            self._events.append(
                {
                    "event": "FIRST_TEST_CONSUMED",
                    "selected_poi_id": selected_poi_id,
                    "known_at": state.consumed_at,
                }
            )
        return state

    def emit_h1_proposal(
        self,
        selected_poi_id: str,
        *,
        emission_decision_at: int,
        proposal_selected_conf_id: str,
    ) -> SelectedPoiState:
        state = register_emission(
            self._states[selected_poi_id],
            emission_decision_at=emission_decision_at,
            proposal_selected_conf_id=proposal_selected_conf_id,
        )
        self._states[selected_poi_id] = state
        self._events.append(
            {
                "event": "H1_PROPOSAL_RESERVED",
                "selected_poi_id": selected_poi_id,
                "origin_conf_id": state.origin_conf_id,
                "proposal_selected_conf_id": state.proposal_selected_conf_id,
                "known_at": emission_decision_at,
            }
        )
        return state

    def retire(self, selected_poi_id: str, *, known_at: int, reason: str) -> None:
        state = self._states[selected_poi_id]
        when = timestamp(known_at)
        if state.retired_at is None:
            self._states[selected_poi_id] = replace(state, retired_at=when)
            self._events.append(
                {
                    "event": "RETIRE",
                    "selected_poi_id": selected_poi_id,
                    "known_at": when,
                    "reason": reason,
                }
            )

    def state(self, selected_poi_id: str) -> dict:
        return asdict(self._states[selected_poi_id])

    def snapshot(self) -> dict:
        return {
            "version": VERSION,
            "states": {key: asdict(value) for key, value in sorted(self._states.items())},
            "events": list(self._events),
            "historical_position_evaluations": 0,
            "financial_metrics_generated": False,
            "trade_entry_allowed": False,
        }

    def __len__(self) -> int:
        return len(self._states)
