"""Validate full saved pre-entry artifacts and timestamp provenance, without positions."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from verify_machine_strategy_v4_1_implementation_v1 import check_source

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_1_implementation_readiness_v1"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def check(partial=False, expected_progress_sha256=None):
    name = (
        "SOURCE_REPLAY_PROGRESS.json"
        if partial
        else "SOURCE_PREFIX_REPLAY_RECEIPT.json"
    )
    content = (DEST / name).read_bytes()
    receipt = json.loads(content)
    if partial:
        require(
            expected_progress_sha256 == sha256(content).hexdigest(),
            "EXTERNAL_PROGRESS_PIN_MISMATCH",
        )
    else:
        # Field-level PASS cannot upgrade an incomplete two-product replay.
        check_source(receipt)
    for name, expected in receipt["run_context"]["source_code_sha256"].items():
        require(
            sha256((ROOT / name).read_bytes()).hexdigest() == expected,
            "SOURCE_CODE_CHANGED",
        )
    report = {
        "scope": "PARTIAL_GATE_COMPLETED_PRODUCT_FIELDS"
        if partial
        else "FULL_SEALED_SOURCE_FIELD_PROVENANCE",
        "gate_complete": not partial,
        "products": {},
        "historical_position_evaluations": 0,
        "trade_entry_allowed": False,
    }
    funnel = {
        "scope": "SOURCE_ONLY_NO_HISTORICAL_POSITION_COUNTS",
        "products": {},
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
        gate_counts = {}
        for sink in audit["telemetry"]:
            first_gates = set()
            terminals = 0
            for event in sink["events"]:
                require(
                    {
                        "formation_id",
                        "physical_bucket_id",
                        "gate_name",
                        "event_type",
                        "known_at",
                        "decision_cutoff",
                        "context_id",
                        "approach_state",
                        "reason_code",
                    }
                    <= event.keys(),
                    "TELEMETRY_REQUIRED_FIELDS",
                )
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
                gate, kind = event["gate_name"], event["event_type"]
                counter = gate_counts.setdefault(
                    gate,
                    {
                        "first_evaluated_origins": set(),
                        "first_pass_origins": set(),
                        "waiting_origins": set(),
                        "wait_evaluations": 0,
                        "terminal_origins": set(),
                    },
                )
                origin = sink["formation_id"]
                if kind == "FIRST_EVAL":
                    require(gate not in first_gates, "DUPLICATE_FIRST_EVAL")
                    first_gates.add(gate)
                    counter["first_evaluated_origins"].add(origin)
                elif kind == "PASS":
                    counter["first_pass_origins"].add(origin)
                elif kind == "WAIT":
                    counter["waiting_origins"].add(origin)
                    counter["wait_evaluations"] += 1
                elif kind in ("REJECT", "RETIRE", "EOF_CENSOR"):
                    counter["terminal_origins"].add(origin)
                    terminals += 1
                if gate == "approach_state" and kind == "PASS":
                    require(
                        event["approach_state"]
                        in ("APPROACH_CLEAN", "APPROACH_CORRECTIVE"),
                        "MISSING_EVALUATED_APPROACH",
                    )
                if gate in (
                    "htf_context",
                    "refinement_and_poi",
                    "physical_eligibility",
                    "entry_geometry",
                    "fta_lifecycle",
                    "payoff_gate",
                    "adverse_liquidity",
                    "reservation_and_order",
                ) and kind in ("PASS", "ORDER_EMIT"):
                    require(
                        event["context_id"] and event["approach_state"],
                        "MISSING_EVALUATED_CONTEXT_OR_APPROACH",
                    )
            require(terminals <= 1, "MULTIPLE_TERMINAL_ORIGIN_EVENTS")
        funnel["products"][product] = {
            "source_raw_origins": len(raw),
            "unique_source_formations": len({row[0] for row in raw}),
            "unique_source_formations_by_family_direction": {
                key: len({row[0] for row in raw if f"{row[1]}|{row[3]}" == key})
                for key in sorted({f"{row[1]}|{row[3]}" for row in raw})
            },
            "unique_physical_buckets": len(
                {s["physical_bucket_id"] for s in audit["telemetry"]}
            ),
            "physical_selected_POIs": len(inventory["states"]),
            "candidate_parent_associations": sum(
                len(associations)
                for associations in inventory["candidate_associations"].values()
            ),
            "eligible_physical_POIs": sum(
                state["eligibility_at"] is not None
                for state in inventory["states"].values()
            ),
            "reserved_physical_POIs": sum(
                state["reserved_at"] is not None
                for state in inventory["states"].values()
            ),
            "pre_entry_model_proposals": len(orders),
            "historical_retry_and_exposure_counts": "NOT_EVALUATED",
            "historical_position_evaluations": 0,
            "historical_fill_exit_counts": "NOT_EVALUATED",
            "per_gate": {
                g: {k: len(v) if isinstance(v, set) else v for k, v in c.items()}
                for g, c in sorted(gate_counts.items())
            },
        }
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
    report_name = (
        "FULL_SOURCE_CONFORMANCE.partial.json"
        if partial
        else "FULL_SOURCE_CONFORMANCE_RECEIPT.json"
    )
    (DEST / report_name).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    funnel_name = (
        "TELEMETRY_FUNNEL_SOURCE_ONLY.partial.json"
        if partial
        else "TELEMETRY_FUNNEL_SOURCE_ONLY.json"
    )
    (DEST / funnel_name).write_text(json.dumps(funnel, indent=2, sort_keys=True) + "\n")
    return {
        "source_field_conformance": "PASS",
        "gate_complete": not partial,
        "products": len(report["products"]),
        "historical_position_evaluations": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--expected-progress-sha256")
    args = parser.parse_args()
    print(
        json.dumps(check(args.partial, args.expected_progress_sha256), sort_keys=True)
    )
