"""Validate full saved pre-entry artifacts and timestamp provenance, without positions."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_1_implementation_readiness_v1"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def check():
    receipt = json.loads((DEST / "SOURCE_PREFIX_REPLAY_RECEIPT.json").read_text())
    require(receipt["source_only_causality"] == "PASS", "SOURCE_NOT_COMPLETE")
    report = {
        "scope": "FULL_SEALED_SOURCE_FIELD_PROVENANCE",
        "products": {},
        "historical_position_evaluations": 0,
        "trade_entry_allowed": False,
    }
    for product, result in receipt["products"].items():
        path = ROOT / result["source_artifact"]
        require(
            sha256(path.read_bytes()).hexdigest() == result["source_artifact_sha256"],
            "SOURCE_ARTIFACT_CHANGED",
        )
        payload = json.loads(gzip.decompress(path.read_bytes()))
        audit, orders = payload["source_only_audit"], payload["preentry_model_catalog"]
        require(
            audit["historical_position_evaluations"] == 0
            and audit["financial_outcomes_generated"] is False,
            "OUTCOME_SCOPE",
        )
        raw = audit["raw_origins"]
        require(
            all(
                len(row) == 6
                and row[4] in (60, 240)
                and row[2] % (row[4] * 60) == 0
                and row[3] in ("LONG", "SHORT")
                and row[0]
                and row[5]
                for row in raw
            ),
            "RAW_FIELD_PROVENANCE",
        )
        coverage = dict(Counter(f"{r[1]}|H{r[4] // 60}|{r[3]}" for r in raw))
        require(
            coverage == result["raw_family_tf_direction_coverage"]
            and result["raw_field_provenance_validated"] is True,
            "RAW_COVERAGE_CHANGED",
        )
        inventory = audit["inventory"]
        for selected_id, state in inventory["states"].items():
            require(state["selected_poi_id"] == selected_id, "PHYSICAL_ID_MISMATCH")
            associations = inventory["candidate_associations"][selected_id]
            require(state["formation_id"] in associations, "MISSING_OWNER_ASSOCIATION")
            if state["expected_origin_conf_id"] is not None:
                require(
                    state["origin_conf_id"] == state["expected_origin_conf_id"]
                    and state["origin_conf_known_at"]
                    == state["expected_origin_conf_known_at"],
                    "REFINED_ORIGIN_NOT_PUBLISHED",
                )
            if state["eligibility_at"] is not None:
                eligible = state["eligibility_at"]
                require(
                    eligible % 900 == 0
                    and eligible
                    >= max(
                        state["formation_known_at"],
                        state["origin_conf_known_at"],
                        state["reaction_required_at"] or 0,
                        state["zone_born_at"] or 0,
                    ),
                    "ELIGIBILITY_LOWER_BOUND",
                )
                if state["consumed_at"] is not None:
                    require(
                        state["consumed_at"] - state["selected_poi_native_tf"] * 60
                        >= eligible,
                        "PARTIAL_NATIVE_INTERVAL_CONSUMED",
                    )
                if state["reserved_at"] is not None:
                    require(
                        eligible <= state["reserved_at"],
                        "RESERVATION_BEFORE_ELIGIBILITY",
                    )
        for event in inventory["events"]:
            require(
                type(event["known_at"]) is int and event["known_at"] >= 0,
                "INVENTORY_EVENT_TIME",
            )
        for sink in audit["telemetry"]:
            for event in sink["events"]:
                require(
                    event["known_at"] <= event["decision_cutoff"],
                    "TELEMETRY_FUTURE_EVENT",
                )
                require(
                    not (
                        event["event_type"] == "REJECT"
                        and "NO_HTF_CONTEXT" in str(event.get("reason_code"))
                    ),
                    "CONTEXT_WAIT_BECAME_TERMINAL_SCALP_REJECT",
                )
        for conditional in audit["conditional_pending_lifecycle"]:
            require(
                conditional["scope"] == "IF_STILL_PENDING"
                and conditional["flags"]["known_at"] <= conditional["known_at"],
                "CONDITIONAL_LIFECYCLE_SCOPE",
            )
        for order in orders:
            at = order["decision_at"]
            require(
                at % 3600 == 0 and at < order["parent_deadline_at"],
                "H1_EMISSION_OR_HALF_OPEN_DEADLINE",
            )
            state = order["selected_poi_state"]
            require(
                state["origin_conf_known_at"] <= state["eligibility_at"] <= at
                and order["confirmation_known_at"] <= at,
                "ORDER_KNOWN_AT",
            )
            require(
                order["formation_id"]
                in inventory["candidate_associations"][order["entry_poi_id"]],
                "PROPOSAL_ASSOCIATION_MISSING",
            )
            require(
                order["historical_position_evaluations"] == 0
                and order["trade_entry_allowed"] is False,
                "ORDER_SCOPE",
            )
            require(
                len(order["scenario_plans"]) == 9
                and len({p["scenario_id"] for p in order["scenario_plans"]}) == 9,
                "NINE_SCENARIO_GAP",
            )
            require(
                all(s["known_at"] <= at for s in order["states"].values()),
                "CONTEXT_FUTURE_STATE",
            )
        report["products"][product] = {
            "raw_family_tf_direction_coverage": coverage,
            "all_raw_and_inventory_and_proposal_fields_validated": True,
            "all_conditional_lifecycle_events_validated": True,
            "historical_fills_or_exits_evaluated": False,
        }
    (DEST / "FULL_SOURCE_CONFORMANCE_RECEIPT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return {
        "full_source_conformance": "PASS",
        "products": len(report["products"]),
        "historical_position_evaluations": 0,
    }


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
