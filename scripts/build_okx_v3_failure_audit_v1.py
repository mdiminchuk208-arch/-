"""Diagnosis-only reader of frozen logs and price envelopes; never runs trades."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from itertools import pairwise

from machine_strategy_v2_core import serial
from okx_qualification_data_v1 import ROOT, save
from okx_v3_compatibility_binding_v1 import digest, scenarios
from okx_v3_compatibility_runner_v1 import OUT
from okx_v3_input_bridge_v1 import aggregate, load_native
from verify_okx_v3_financial_audit_v1 import verify

DEST = ROOT / "docs/machine_strategy_v3_okx_failure_audit_v1"
PARENT_SHA = "129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2"
D = Decimal
CODE = [
    "scripts/build_okx_v3_failure_audit_v1.py",
    "tests/test_okx_v3_failure_audit_v1.py",
]


def distribution(values):
    rows = sorted(D(str(v)) for v in values if v is not None)
    if not rows:
        return {"n": 0, "min": None, "median": None, "max": None}
    n = len(rows)
    return serial(
        {
            "n": n,
            "min": rows[0],
            "median": (rows[(n - 1) // 2] + rows[n // 2]) / 2,
            "max": rows[-1],
            "mean": sum(rows, D(0)) / n,
        }
    )


def price_excursion(bars, entry, direction):
    """Retrospective price envelope only; no hypothetical fill or exit."""
    e = D(entry)
    highs = [b.high for b in bars] + [e]
    lows = [b.low for b in bars] + [e]
    return {
        "favorable_D": max(highs) - e if direction == "LONG" else e - min(lows),
        "adverse_D": e - min(lows) if direction == "LONG" else max(highs) - e,
    }


def exposure_excursion_bounds(native, state):
    """Whole exposure bars give lower bounds; boundary bars give upper bounds."""
    flo, fhi = state["fill_time_bounds"]
    xlo, xhi = state["event_time_bounds"]
    e, x = D(state["fill_price"]), D(state["exit_price"])
    possible = [b for b in native if b.end > flo and b.start < xhi]
    certain = [b for b in possible if b.start >= fhi and b.end <= xlo]
    upper = price_excursion(possible, e, state["direction"])
    lower = price_excursion(certain, e, state["direction"])
    signed_exit = (x - e) * (1 if state["direction"] == "LONG" else -1)
    for row in (lower, upper):
        row["favorable_D"] = max(row["favorable_D"], signed_exit)
        row["adverse_D"] = max(row["adverse_D"], -signed_exit)
    assert all(upper[k] >= lower[k] >= 0 for k in upper)
    return serial(
        {
            "lower_D": lower,
            "upper_D": upper,
            "certain_full_bars": len(certain),
            "possible_overlap_bars": len(possible),
            "intrabar_exact_extrema_unknown": flo != fhi or xlo != xhi,
            "definition": "Retrospective bounds, not admission features; excludes bars starting at exact OPEN exit; includes modeled fill/exit endpoints.",
        }
    )


def active_pending_envelope(bars, entry, direction, terminal_open=None):
    result = price_excursion(bars, entry, direction)
    if terminal_open is not None:
        delta = (D(terminal_open) - D(entry)) * (1 if direction == "LONG" else -1)
        result["favorable_D"] = max(result["favorable_D"], delta)
        result["adverse_D"] = max(result["adverse_D"], -delta)
    return result


def admission(product, audit, orders):
    raw = {r["formation_id"]: r for r in audit["raw_formations"]}
    assert len(raw) == len(audit["raw_formations"])
    outcomes = defaultdict(list)
    for r in audit["diagnostics"]:
        outcomes[r["formation_id"]].append(
            {"kind": "TERMINAL", "reason": r["reason"], "at": r["decision_at"]}
        )
    for r in audit["pending"]:
        outcomes[r["formation_id"]].append(
            {
                "kind": "PENDING_EOF",
                "reason": r.get("last_wait"),
                "at": audit["known_through"],
            }
        )
    for group in audit["reservation_audit"]:
        for r in group["proposals"]:
            outcomes[r["formation_id"]].append(
                {
                    "kind": r["disposition"],
                    "reason": r["audit_reason"],
                    "at": group["decision_at"],
                }
            )
    assert set(raw) == set(outcomes) and all(len(r) == 1 for r in outcomes.values()), (
        "EXACT_ORIGIN_PARTITION"
    )
    physical = defaultdict(list)
    records = []
    for key, r in raw.items():
        result = outcomes[key][0]
        bucket = (r["formation_at"], r["direction"])
        physical[bucket].append(result)
        records.append(
            {
                "formation_id": key,
                "physical_key": [product, *bucket],
                "branch": r["branch"],
                "setup_tf": r["setup_tf"],
                "direction": r["direction"],
                "discovered_at": r["discovered_at"],
                "formation_at": r["formation_at"],
                "outcome": result,
                "lag_seconds": result["at"] - r["formation_at"],
            }
        )
    waits = {}
    max_attempts = max(
        (r["expiry"] - r["discovered_at"]) // 3600 + 1 for r in raw.values()
    )
    assert max_attempts == 17
    for name, count in audit["counts"].items():
        if name.startswith("WAIT_"):
            upper = (
                sum(r["branch"] in ("SFP", "OB") for r in raw.values())
                if name == "WAIT_ORIGIN_BOUND_REFINEMENT_POI"
                else len(raw)
            )
            waits[name] = {
                "retry_events": count,
                "unique_origin_lower_bound": (count + max_attempts - 1) // max_attempts,
                "unique_origin_upper_bound": upper,
                "exact_unique_origin_count": None,
                "reason": "Per-origin wait histories were not logged. Bound uses at most17 hourly checks/origin; branch support bounds origin-bound WAIT.",
            }
    kind = Counter(r[0]["kind"] for r in outcomes.values())
    reason = Counter(
        r[0]["reason"] for r in outcomes.values() if r[0]["kind"] == "TERMINAL"
    )
    families = {}
    for branch in ("SFP", "OB", "STB", "RANGE", "BREAKER"):
        n = sum(r["branch"] == branch for r in raw.values())
        c = sum(r["branch"] == branch for r in orders)
        families[branch] = {
            "raw": n,
            "catalog": c,
            "catalog_per_raw": str(D(c) / n) if n else None,
        }
    return {
        "product": product,
        "raw_origins": len(raw),
        "physical_buckets": len(physical),
        "multi_origin_physical_buckets": sum(len(r) > 1 for r in physical.values()),
        "origins_by_disposition": dict(kind),
        "terminal_unique_origins_by_reason": dict(reason),
        "non_smooth_only_physical_buckets": sum(
            all(r["reason"] == "REJECT_NON_SMOOTH_STRUCTURAL_APPROACH" for r in rows)
            for rows in physical.values()
        ),
        "non_smooth_any_physical_buckets": sum(
            any(r["reason"] == "REJECT_NON_SMOOTH_STRUCTURAL_APPROACH" for r in rows)
            for rows in physical.values()
        ),
        "family_rates_descriptive_not_independent": families,
        "wait_exposure_bounds": waits,
        "candidate_formation_to_decision_seconds": distribution(
            r["decision_at"] - r["formation_at"] for r in orders
        ),
        "terminal_lag_seconds_by_reason": {
            name: distribution(
                r["lag_seconds"] for r in records if r["outcome"]["reason"] == name
            )
            for name in reason
        },
        "origin_records": records,
        "native_raw_events_including_warmup": len(audit["raw_native_formations"]),
        "source_validated_catalog": dict(
            Counter(str(r["source_validated"]) for r in orders)
        ),
        "gate_order": [
            "M15_CONF_after_reaction",
            "opposite_BOS_non_smooth",
            "SFP_OB_origin_bound_POI",
            "POI_consumption_reservation",
            "HTF_context_direction",
            "price_FTA_economics",
            "physical_POI_reservation",
        ],
        "evidence_gaps": [
            "No exact per-origin WAIT exposure/overlap/transition rates",
            "Terminal logs omit confirmation/reaction/context snapshots",
            "Discovery reaction_at=None does not prove no eventual reaction",
            "Native-to-pending gap mixes warmup/prefix/exclusions; no per-native exclusion reason",
        ],
    }


def decision_geometry(order, native, starts, ends, tf_bars, tf_ends, raw):
    at = order["decision_at"]
    i = bisect_left(starts, at)
    assert i > 0 and ends[i - 1] == at and starts[i] == at
    mark = native[i - 1].close
    e, s, t, u = (D(order[k]) for k in ("entry", "stop", "target", "fixed_R_unit"))
    direction = 1 if order["direction"] == "LONG" else -1
    j = bisect_right(tf_ends, at)
    assert j >= 15
    previous = tf_bars[j - 15 : j]
    atr = (
        sum(
            (
                max(b.high - b.low, abs(b.high - p.close), abs(b.low - p.close))
                for p, b in pairwise(previous)
            ),
            D(0),
        )
        / 14
    )
    assert all(b.end <= at for b in previous)
    formation = raw[order["formation_id"]]
    distance = direction * (mark - e)
    return serial(
        {
            "completed_mark": mark,
            "mark_known_at": at,
            "first_postdecision_OPEN": native[i].open,
            "first_OPEN_observed_at": native[i].end,
            "last_completed_mark_beyond_target": direction * (mark - t) >= 0,
            "last_completed_mark_beyond_stop": direction * (mark - s) <= 0,
            "signed_entry_distance_from_completed_mark_D": distance,
            "diagnostic_completed_native_TF_SMA14_TR": atr,
            "ATR_known_through": previous[-1].end,
            "entry_distance_in_diagnostic_ATR": distance / atr if atr else None,
            "frozen_formation_ATR_if_SFP": formation["atr"]
            if order["branch"] == "SFP"
            else None,
            "stop_distance_D": abs(e - s),
            "target_distance_D": abs(t - e),
            "raw_target_to_stop_ratio": abs(t - e) / abs(e - s),
            "target_move_to_cost_ratio": order["target_move_to_cost_ratio"],
            "planned_net_at_target_R_ex_funding": D(order["modeled_target_cash_margin"])
            / u,
            "fixed_R_unit": u,
            "stop_cost_share_of_unit": order["stop_cost_share_of_unit"],
            "formation_to_decision_seconds": at - order["formation_at"],
            "reaction_to_confirmation_seconds": order["confirmation_known_at"]
            - formation["reaction_at"]
            if formation["reaction_at"] is not None
            else None,
            "order_lifetime_seconds": order["expires_at"] - at,
            "classification": "DIAGNOSTIC_NORMALIZATION_NOT_SOURCE_RULE; retrospective OPEN and excursions never enter admission",
        }
    )


def no_fill(order, case, native, starts, geometry):
    first = bisect_left(starts, order["decision_at"])
    end = bisect_left(starts, order["expires_at"])
    window = native[first:end]
    assert len(window) == 4
    rows = []
    for state in case["all_scenarios"]:
        assert state["status"] in (
            "UNFILLED_EXPIRED",
            "GAP_INVALIDATED_BEFORE_FILL",
            "ORDER_CENSORED_EOF",
        )
        e, s, t = (D(state[k]) for k in ("entry", "stop", "target"))
        long = order["direction"] == "LONG"
        touched = (
            [b.start for b in window if b.low <= e]
            if long
            else [b.start for b in window if b.high >= e]
        )
        if state["status"] == "GAP_INVALIDATED_BEFORE_FILL":
            bar = native[bisect_left(starts, state["observed_at"])]
            reason = (
                "TARGET_OPEN_INVALIDATED_BEFORE_ENTRY"
                if (bar.open >= t if long else bar.open <= t)
                else "STOP_OPEN_INVALIDATED_BEFORE_ENTRY"
            )
            assert (bar.open <= s if long else bar.open >= s) or (
                bar.open >= t if long else bar.open <= t
            )
            before = [b for b in window if b.start < state["observed_at"]]
            assert all(b.low > e if long else b.high < e for b in before)
            terminal_open = bar.open
            prev_close = native[bisect_left(starts, state["observed_at"]) - 1].close
        else:
            reason = (
                "NO_ENTRY_TOUCH_IN_FROZEN_1H_LIFETIME"
                if state["status"] == "UNFILLED_EXPIRED"
                else "ORDER_EOF_NOT_A_CLOSED_TRADE"
            )
            before = window
            terminal_open = None
            prev_close = None
            if state["status"] == "UNFILLED_EXPIRED":
                assert not touched
        rows.append(
            serial(
                {
                    "scenario_id": state["scenario_id"],
                    "recorded_status": state["status"],
                    "mechanical_reason": reason,
                    "entry": e,
                    "stop": s,
                    "target": t,
                    "observed_at": state["observed_at"],
                    "hours_to_invalidation_or_expiry": D(
                        state["observed_at"] - order["decision_at"]
                    )
                    / 3600,
                    "candidate_price_touch_in_full_expiry_window": bool(touched),
                    "full_expiry_window_price_envelope_D": price_excursion(
                        window, e, order["direction"]
                    ),
                    "full_window_includes_post_cancellation_prices": terminal_open
                    is not None,
                    "active_order_price_envelope_D": active_pending_envelope(
                        before, e, order["direction"], terminal_open
                    ),
                    "terminal_OPEN": terminal_open,
                    "last_completed_CLOSE_before_terminal_OPEN": prev_close,
                    "prior_CLOSE_already_beyond_target": (
                        (prev_close >= t) if long else (prev_close <= t)
                    )
                    if prev_close is not None
                    else None,
                    "pre_invalidation_full_bars_price_envelope_D": price_excursion(
                        before, e, order["direction"]
                    ),
                    "interpretation": "No position exists: these are price envelopes, not trade MFE/MAE. Active envelope ends at cancellation OPEN, excluding its later wicks. Full expiry-window envelope may include post-cancellation prices; not causal evidence for an active order or alternate executed trade.",
                }
            )
        )
    return {
        "case_id": case["case_id"],
        "product": order["product"],
        "direction": order["direction"],
        "branch": order["branch"],
        "setup_tf": order["setup_tf"],
        "context": order["context"],
        "decision_at": order["decision_at"],
        "formation_at": order["formation_at"],
        "geometry": geometry,
        "reference_mechanical_reason": rows[0]["mechanical_reason"],
        "all_scenarios": rows,
        "reservation_or_sibling_caused_selected_case_no_fill": False,
        "claims_not_identifiable": [
            "Expiry too short versus a valid alternative lifetime",
            "Opposite entry/geometry would improve profit",
            "Exact before-fill intrabar sequence",
            "Why the market did not retrace",
        ],
    }


def grid_disagreement(order, case):
    inputs = order["compatibility_plan_inputs"]
    raw = inputs["raw"]
    target = next(r for r in inputs["targets"] if r["id"] == order["nearest_fta_id"])
    rows = []
    for grid, state in zip(
        scenarios(order["product"]), case["all_scenarios"], strict=True
    ):
        tick = D(grid["tick"])
        long = order["direction"] == "LONG"
        e = (D(raw["raw_entry"]) / tick).to_integral_value(
            rounding=ROUND_FLOOR if long else ROUND_CEILING
        ) * tick
        s = (
            (D(raw["raw_stop_boundary"]) / tick).to_integral_value(
                rounding=ROUND_CEILING if long else ROUND_FLOOR
            )
            + (-1 if long else 1)
        ) * tick
        t = (
            (D(target["price"]) / tick).to_integral_value(
                rounding=ROUND_CEILING if long else ROUND_FLOOR
            )
            + (-1 if long else 1)
        ) * tick
        lo, hi = D(inputs["zone_low"]), D(inputs["zone_high"])
        any_grid = (lo / tick).to_integral_value(rounding=ROUND_CEILING) <= (
            hi / tick
        ).to_integral_value(rounding=ROUND_FLOOR)
        rows.append(
            serial(
                {
                    **grid,
                    "status": state["status"],
                    "recorded_rejection_reason": state.get("reason"),
                    "derived_entry": e,
                    "derived_outward_stop": s,
                    "derived_inward_reference_FTA_target": t,
                    "zone_low": lo,
                    "zone_high": hi,
                    "raw_entry": raw["raw_entry"],
                    "raw_stop": raw["raw_stop_boundary"],
                    "raw_reference_FTA": target["price"],
                    "reference_FTA_id": target["id"],
                    "rounded_entry_inside_zone": lo <= e <= hi,
                    "any_price_grid_point_inside_zone": any_grid,
                    "preentry_margin_to_reference_FTA_ex_funding": (t - e)
                    * (1 if long else -1)
                    - D(".0008") * (e + t),
                    "fixed_reference_unit": order["fixed_R_unit"],
                    "never_impute_missing_cash": True,
                }
            )
        )
    grouped = defaultdict(set)
    for r in rows:
        grouped[r["tick"]].add(r["recorded_rejection_reason"])
    assert all(len(r) == 1 for r in grouped.values()), (
        "LOT_VARIANTS_SAME_ELIGIBILITY_REASON"
    )
    return {
        "case_id": case["case_id"],
        "product": order["product"],
        "direction": order["direction"],
        "branch": order["branch"],
        "diagnostic_valid_closed_scenarios": sum(r["status"] == "CLOSED" for r in rows),
        "scenarios": rows,
        "classification": "Synthetic price-grid/fixed-entry-policy representability sensitivity; not verified historical OKX ineligibility.",
        "lot_minimum_or_R_caused_eligibility_rejection": False,
        "STOP_retained": True,
    }


def closed_summary(cases, column):
    rows = [r for r in cases if r["metrics_eligible"]]
    values = [r["columns"][column]["stored_components"] for r in rows]
    net = [D(r["net_R"]) for r in values]
    wins = [v for v in net if v > 0]
    losses = [-v for v in net if v < 0]
    avg_win = sum(wins, D(0)) / len(wins) if wins else None
    avg_loss = sum(losses, D(0)) / len(losses) if losses else None
    return serial(
        {
            "CLOSED": len(rows),
            "WIN": len(wins),
            "LOSS": len(losses),
            "components": {
                k: sum((D(r[k]) for r in values), D(0))
                for k in (
                    "gross_R",
                    "fees_R",
                    "slippage_R",
                    "funding_R",
                    "net_R",
                    "gross_cash",
                    "fees_cash",
                    "slippage_cash",
                    "funding_cash",
                    "net_cash",
                )
            },
            "avg_net_win_R": avg_win,
            "avg_abs_net_loss_R": avg_loss,
            "descriptive_break_even_WR_at_observed_payoff_only": avg_loss
            / (avg_win + avg_loss)
            if avg_win is not None and avg_loss is not None
            else None,
            "payoff_inference_not_a_selected_WR_threshold": True,
            "exit_reasons": dict(
                Counter(r["columns"][column]["exit_reason"] for r in rows)
            ),
            "unit_distribution": distribution(
                r["geometry"]["fixed_R_unit"] for r in rows
            ),
            "stop_cost_share_distribution": distribution(
                r["geometry"]["stop_cost_share_of_unit"] for r in rows
            ),
            "target_stop_ratio_distribution": distribution(
                r["geometry"]["raw_target_to_stop_ratio"] for r in rows
            ),
            "planned_target_net_R_distribution_ex_funding": distribution(
                r["geometry"]["planned_net_at_target_R_ex_funding"] for r in rows
            ),
            "holding_min_seconds_distribution": distribution(
                r["columns"][column]["holding_time_bounds"]["minimum_seconds"]
                for r in rows
            ),
            "holding_max_seconds_distribution": distribution(
                r["columns"][column]["holding_time_bounds"]["maximum_seconds"]
                for r in rows
            ),
        }
    )


def partitions(cases, column):
    result = {}
    for name in (
        "product",
        "direction",
        "branch",
        "setup_tf",
        "context",
        "context_regime",
        "coin_direction",
        "exit_year",
        "exit_month",
    ):
        buckets = defaultdict(list)
        for r in cases:
            if not r["metrics_eligible"]:
                continue
            if name == "coin_direction":
                label = r["product"] + ":" + r["direction"]
            elif name == "context_regime":
                label = r["context"]["context"]
            elif name.startswith("exit_"):
                at = datetime.fromtimestamp(r["columns"][column]["observed_at"], UTC)
                label = (
                    str(at.year) if name == "exit_year" else f"{at.year}-{at.month:02d}"
                )
            else:
                label = str(r[name])
            buckets[label].append(r)
        result[name] = {
            label: closed_summary(rows, column)
            for label, rows in sorted(buckets.items())
        }
    return result


def prepare():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("FROZEN_AUDIT_USE_EXTERNAL_RESUME")
    verify(PARENT_SHA)
    admissions = []
    no_fills = []
    closed = []
    disagreements = []
    all_geometry = []
    with localcontext() as ctx:
        ctx.prec = 40
        for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP"):
            audit = json.loads((OUT / (product + ".catalog_audit.json")).read_text())
            orders = [
                json.loads(line)
                for line in gzip.decompress(
                    (OUT / (product + ".catalog.jsonl.gz")).read_bytes()
                ).splitlines()
            ]
            cases = [
                json.loads(line)
                for line in (OUT / (product + ".cases.jsonl")).read_text().splitlines()
            ]
            assert [r["case_id"] for r in cases] == [r["case_id"] for r in orders]
            admissions.append(admission(product, audit, orders))
            native = load_native(product)
            starts = [b.start for b in native]
            ends = [b.end for b in native]
            market = {}
            market_ends = {}
            for tf in (60, 240):
                market[tf], missing = aggregate(native, tf * 60)
                assert not missing
                market_ends[tf] = [b.end for b in market[tf]]
            raw = {r["formation_id"]: r for r in audit["raw_formations"]}
            for order, case in zip(orders, cases, strict=True):
                geometry = decision_geometry(
                    order,
                    native,
                    starts,
                    ends,
                    market[order["setup_tf"]],
                    market_ends[order["setup_tf"]],
                    raw,
                )
                all_geometry.append(
                    {
                        "case_id": case["case_id"],
                        "product": product,
                        "direction": order["direction"],
                        "branch": order["branch"],
                        "setup_tf": order["setup_tf"],
                        "context": order["context"],
                        "status": case["status"],
                        "geometry": geometry,
                    }
                )
                if case["status"] == "ALL_SCENARIOS_NO_FILL":
                    no_fills.append(no_fill(order, case, native, starts, geometry))
                if case["status"] == "COMPATIBILITY_DISAGREEMENT":
                    disagreements.append(grid_disagreement(order, case))
                if case["adverse"]:
                    columns = {}
                    for column in ("base", "doubled"):
                        selected = next(
                            s
                            for s in case["all_scenarios"]
                            if s["scenario_id"]
                            == case["adverse"][column]["scenario_id"]
                        )
                        columns[column] = {
                            "scenario_id": selected["scenario_id"],
                            "stored_components": selected["columns"][column],
                            "entry": selected["entry"],
                            "fill_price": selected["fill_price"],
                            "stop": selected["stop"],
                            "target": selected["target"],
                            "exit_price": selected["exit_price"],
                            "exit_reason": selected["exit_reason"],
                            "observed_at": selected["observed_at"],
                            "fill_time_bounds": selected["fill_time_bounds"],
                            "event_time_bounds": selected["event_time_bounds"],
                            "holding_time_bounds": selected["holding_time_bounds"],
                            "excursion_bounds": exposure_excursion_bounds(
                                native, selected
                            ),
                        }
                    closed.append(
                        {
                            "case_id": case["case_id"],
                            "product": product,
                            "direction": order["direction"],
                            "branch": order["branch"],
                            "setup_tf": order["setup_tf"],
                            "context": order["context"],
                            "formation_at": order["formation_at"],
                            "decision_at": order["decision_at"],
                            "selected_H1_impulse_id": order["selected_impulse"]["id"],
                            "admission_context_origin_id": order["context"][
                                "origin_id"
                            ],
                            "metrics_eligible": case["status"] == "CLOSED",
                            "diagnostic_partial_disagreement": case["status"]
                            != "CLOSED",
                            "geometry": geometry,
                            "columns": columns,
                        }
                    )
    assert (
        len(all_geometry) == 99
        and len(no_fills) == 70
        and len(disagreements) == 9
        and sum(r["metrics_eligible"] for r in closed) == 20
        and len(closed) == 21
    )
    save(
        DEST / "ADMISSION_FUNNEL_CAUSAL.json",
        {
            "products": admissions,
            "new_signal_evaluations": 0,
            "all_origin_ids_retained": True,
            "counts_not_independent_trials": True,
        },
    )
    save(
        DEST / "NO_FILL_DIAGNOSTICS.json",
        {
            "cases": no_fills,
            "cases_count": 70,
            "reference_reason_counts": dict(
                Counter(r["reference_mechanical_reason"] for r in no_fills)
            ),
            "retrospective_not_entry_filters": True,
            "new_trade_evaluations": 0,
        },
    )
    no_fill_buckets = {}
    for dimension in (
        "reference_mechanical_reason",
        "product",
        "direction",
        "branch",
        "setup_tf",
        "context",
        "context_regime",
    ):
        groups = defaultdict(list)
        for r in no_fills:
            label = (
                r["context"]["context"]
                if dimension == "context_regime"
                else str(r[dimension])
            )
            groups[label].append(r)
        no_fill_buckets[dimension] = {
            key: {
                "count": len(rows),
                "entry_distance_ATR": distribution(
                    r["geometry"]["entry_distance_in_diagnostic_ATR"] for r in rows
                ),
                "first_OPEN_entry_distance_bps": distribution(
                    (
                        D(r["geometry"]["first_postdecision_OPEN"])
                        - D(r["all_scenarios"][0]["entry"])
                    )
                    * (1 if r["direction"] == "LONG" else -1)
                    / D(r["all_scenarios"][0]["entry"])
                    * 10000
                    for r in rows
                ),
                "first_OPEN_minus_completed_mark_bps": distribution(
                    (
                        D(r["geometry"]["first_postdecision_OPEN"])
                        - D(r["geometry"]["completed_mark"])
                    )
                    / D(r["geometry"]["completed_mark"])
                    * 10000
                    for r in rows
                ),
                "order_lifetime_seconds": distribution(
                    r["geometry"]["order_lifetime_seconds"] for r in rows
                ),
                "decision_mark_already_beyond_target": sum(
                    r["geometry"]["last_completed_mark_beyond_target"] for r in rows
                ),
                "terminal_time_hours": dict(
                    Counter(
                        r["all_scenarios"][0]["hours_to_invalidation_or_expiry"]
                        for r in rows
                    )
                ),
            }
            for key, rows in sorted(groups.items())
        }
    save(
        DEST / "NO_FILL_DISTRIBUTIONS.json",
        {
            "diagnostic_partitions": no_fill_buckets,
            "classifications_not_identified": {
                "expiry_too_short": None,
                "alternate_entry_more_profitable": None,
                "stop_displacement_caused_nonretracement": None,
                "market_direction_intrinsically_unprofitable": None,
            },
            "full_expiry_postcancel_touch_cases": sum(
                any(
                    s["candidate_price_touch_in_full_expiry_window"]
                    for s in r["all_scenarios"]
                )
                for r in no_fills
            ),
            "none_replayed_as_trades": True,
        },
    )
    save(
        DEST / "ELIGIBILITY_DISAGREEMENTS.json",
        {
            "cases": disagreements,
            "cases_count": 9,
            "all_nine_scenarios_retained": True,
            "none_imputed_or_removed": True,
        },
    )
    save(
        DEST / "CLOSED_EDGE_DECOMPOSITION.json",
        {
            "cases": closed,
            "known_closed_summaries": {
                c: closed_summary(closed, c) for c in ("base", "doubled")
            },
            "diagnostic_partitions_not_filters": {
                c: partitions(closed, c) for c in ("base", "doubled")
            },
            "unique_selected_H1_impulses_in_known_closed": len(
                {r["selected_H1_impulse_id"] for r in closed if r["metrics_eligible"]}
            ),
            "unique_admission_context_origins_in_known_closed": len(
                {
                    r["admission_context_origin_id"]
                    for r in closed
                    if r["metrics_eligible"]
                }
            ),
            "all_nine_closed_cases": 20,
            "partial_disagreement_cases_diagnostic_only": 1,
            "retrospective_excursions_are_bounds_not_precise_ordered_paths": True,
            "new_financial_evaluations": 0,
        },
    )
    save(
        DEST / "DECISION_GEOMETRY.json",
        {
            "all99_cases": all_geometry,
            "no_case_selection": True,
            "diagnostic_ATR_not_a_SOURCE_RULE_or_strategy_rule": True,
        },
    )
    save(
        DEST / "SOURCE_PROVENANCE.json",
        {
            "parent_financial_manifest_sha256": PARENT_SHA,
            "rules": [
                {
                    "rule": "Opposite M15 BOS after reaction through selected CONF rejects before HTF context",
                    "classification": "INHERITED_MACHINE_POLICY_NOT_UNAMBIGUOUS_SOURCE",
                    "evidence": "scripts/machine_strategy_v3_historical_adapter.py:467; docs/machine_strategy_v3_design/RULE_PROVENANCE.json",
                },
                {
                    "rule": "Nested same-BOS M15 refinement POI and confirmation",
                    "classification": "MACHINE_SELECTOR_NOT_SOURCE_EQUIVALENCE",
                    "evidence": "scripts/machine_strategy_v3_historical_adapter.py:488",
                },
                {
                    "rule": "16H1 pending / 1H1 resting order expiration",
                    "classification": "INHERITED_PROJECT_POLICY",
                    "evidence": "docs/machine_strategy_v3_design/RULE_PROVENANCE.json M3_EXEC",
                },
                {
                    "rule": "Synthetic grid family, worst-state/value, fixed U, funding proxy",
                    "classification": "PREREGISTERED_COMPATIBILITY_PROJECT_POLICY",
                    "evidence": "docs/machine_strategy_v3_okx_compatibility_v1/COMPATIBILITY_POLICY.md",
                },
                {
                    "rule": "SMA14 TR diagnostic and OHLC excursion bounds",
                    "classification": "TECHNICAL_DIAGNOSTIC_NORMALIZATION_NOT_SOURCE_RULE",
                    "evidence": "This builder; not used by frozen admission or trade outcomes",
                },
            ],
            "native_and_catalog_source_validated_false_is_recorded_not_reclassified": True,
            "new_financial_backtest": False,
            "PAPER": False,
            "LIVE": False,
            "trade_entry_allowed": False,
        },
    )
    return {
        "prepare": "PASS",
        "raw_origins": sum(r["raw_origins"] for r in admissions),
        "catalog_cases": 99,
        "no_fill_cases": 70,
        "closed_cases": 20,
        "disagreements": 9,
        "new_trade_evaluations": 0,
    }


def resume(expected):
    path = DEST / "freeze_manifest.json"
    if not expected or digest(path) != expected:
        raise ValueError("EXTERNAL_AUDIT_MANIFEST_REQUIRED")
    manifest = json.loads(path.read_text())
    names = {
        str(p.relative_to(ROOT)) for p in DEST.rglob("*") if p.is_file() and p != path
    }
    if names != {
        n
        for n in manifest["artifacts"]
        if n.startswith(str(DEST.relative_to(ROOT)) + "/")
    }:
        raise ValueError("FROZEN_NAMESPACE_CHANGED")
    for n, h in manifest["artifacts"].items():
        if digest(ROOT / n) != h:
            raise ValueError("FROZEN_BYTES_CHANGED")
    return {
        "verified_resume": True,
        "decision": manifest["decision"],
        "new_trade_evaluations": 0,
    }


def freeze():
    path = DEST / "freeze_manifest.json"
    if path.exists():
        raise ValueError("FROZEN_AUDIT_USE_EXTERNAL_RESUME")
    verify(PARENT_SHA)
    qa = json.loads((DEST / "QA_RECEIPT.json").read_text())
    pins = {n: digest(ROOT / n) for n in CODE}
    if qa["status"] != "PASS" or qa["code_sha256"] != pins:
        raise ValueError("QA_OF_EXACT_DIAGNOSTIC_BYTES_REQUIRED")
    for record in qa["commands"]:
        if (
            record["exit_code"] != 0
            or digest(ROOT / record["log"]) != record["log_sha256"]
        ):
            raise ValueError("QA_LOG_CHANGED")
    review = json.loads((DEST / "FINAL_REVIEW.json").read_text())
    if (
        review["decision"] != "FAILURE_AUDIT_FINAL_REVIEW_PASS"
        or review["code_sha256"] != pins
    ):
        raise ValueError("INDEPENDENT_REVIEW_OF_EXACT_CODE_REQUIRED")
    if (
        "BACKTEST_REVIEW_DIAGNOSIS_PASS"
        not in (DEST / "BACKTEST_REVIEW.json").read_text()
    ):
        raise ValueError("INDEPENDENT_DIAGNOSIS_REVIEW_REQUIRED")
    for name, h in qa["diagnostic_sha256"].items():
        if digest(ROOT / name) != h:
            raise ValueError("POST_QA_DIAGNOSTICS_CHANGED")
    files = [p for p in DEST.rglob("*") if p.is_file()]
    if any("__pycache__" in p.parts or p.suffix in (".tmp", ".pyc") for p in files):
        raise ValueError("CACHE_OR_TEMP_IN_IMMUTABLE_NAMESPACE")
    artifacts = {str(p.relative_to(ROOT)): digest(p) for p in files}
    artifacts.update(pins)
    parent = (
        ROOT / "docs/machine_strategy_v3_okx_financial_audit_v1/freeze_manifest.json"
    )
    artifacts[str(parent.relative_to(ROOT))] = PARENT_SHA
    artifacts.update(json.loads(parent.read_text())["artifacts"])
    save(
        path,
        {
            "version": "MACHINE_STRATEGY_v3_OKX_FAILURE_AUDIT_v1",
            "decision": "MACHINE_STRATEGY_V3_OKX_FAILURE_AUDIT_COMPLETE",
            "artifacts": artifacts,
            "parent_financial_manifest_sha256": PARENT_SHA,
            "exact_unique_WAIT_transition_rates_identifiable": False,
            "actionable_design_hypotheses": True,
            "new_version_design_may_open": "MACHINE_STRATEGY_v4",
            "new_financial_evaluations": 0,
            "new_trade_evaluations": 0,
            "new_financial_authorization": False,
            "strategy_qualification": "MACHINE_STRATEGY_V3_QUALIFICATION_STOP",
            "PAPER": False,
            "LIVE": False,
            "trade_entry_allowed": False,
        },
    )
    return {
        "decision": "MACHINE_STRATEGY_V3_OKX_FAILURE_AUDIT_COMPLETE",
        "manifest_sha256": digest(path),
    }


def qa():
    if (DEST / "freeze_manifest.json").exists():
        raise ValueError("FROZEN_AUDIT_USE_EXTERNAL_RESUME")
    names = [
        "ADMISSION_FUNNEL_CAUSAL.json",
        "NO_FILL_DIAGNOSTICS.json",
        "NO_FILL_DISTRIBUTIONS.json",
        "CLOSED_EDGE_DECOMPOSITION.json",
        "ELIGIBILITY_DISAGREEMENTS.json",
        "DECISION_GEOMETRY.json",
        "SOURCE_PROVENANCE.json",
    ]
    before = {n: digest(DEST / n) for n in names}
    prepare()
    if before != {n: digest(DEST / n) for n in names}:
        raise ValueError("DIAGNOSTIC_REPLAY_CHANGED")
    py = sys.executable
    bin_dir = py.rsplit("/", 1)[0]
    commands = [
        [
            py,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_okx_v3_failure_audit_v1.py",
            "-v",
        ],
        [bin_dir + "/ruff", "check", *CODE],
        [bin_dir + "/ruff", "format", "--check", *CODE],
        [bin_dir + "/mypy", "--follow-imports=silent", CODE[0]],
        [py, "-m", "py_compile", *CODE],
        [
            py,
            "scripts/verify_okx_v3_financial_audit_v1.py",
            "--resume-existing",
            "--expected-manifest-sha256",
            PARENT_SHA,
        ],
    ]
    records = []
    for i, command in enumerate(commands):
        result = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False
        )
        path = DEST / "qa" / f"{i:02d}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.stdout + result.stderr)
        records.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "log": str(path.relative_to(ROOT)),
                "log_sha256": digest(path),
            }
        )
    status = "PASS" if all(r["exit_code"] == 0 for r in records) else "STOP"
    diagnostic = {
        str((DEST / n).relative_to(ROOT)): digest(DEST / n)
        for n in names
        + ["FAILURE_AUDIT_REPORT.md", "REDESIGN_HYPOTHESES.json", "EVIDENCE_GAPS.md"]
    }
    save(
        DEST / "QA_RECEIPT.json",
        {
            "status": status,
            "commands": records,
            "code_sha256": {n: digest(ROOT / n) for n in CODE},
            "diagnostic_sha256": diagnostic,
            "deterministic_reader_replay": True,
            "parent_manifest_sha256": PARENT_SHA,
            "new_trade_evaluations": 0,
            "new_financial_backtests": 0,
        },
    )
    (DEST / "QA_REPORT.md").write_text(f"""# Failure-audit QA

Status: {status}. Eight synthetic evidence-boundary/partition tests executed. Exact commands, statuses and logs are in QA_RECEIPT.json. Ruff/format, mypy and compilation cover new diagnostic source/test only. Frozen financial --resume-existing externally pinned verification confirms unchanged inputs; the old historical strategy runner and whole repository suite were not invoked.

Diagnostic reader replay produced identical bytes for all seven generated evidence JSON files. Tests cover exact OPEN exit/cancellation versus later wicks, future-after-exit/future-after-decision mutations, uncertain wick extrema, LONG/SHORT price symmetry, unique-origin partition and exclusion of partial disagreement closures. No trade execution, cash outcome simulation, numeric parameter search or historical strategy replay occurs.

Missing per-origin WAIT history is null exact counts with conservative bounds. Completed-only diagnostic ATR and retrospective OHLC envelopes remain outside admission. Stored P&L comes from the immutable parent ledger; no OOS/PAPER/LIVE/private API/orders are authorized. trade_entry_allowed=false.
""")
    if status != "PASS":
        raise ValueError("QA_FAILED_READ_LOGS")
    return {
        "QA": status,
        "commands": len(records),
        "diagnostic_replay": "byte-identical",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--qa", action="store_true")
    action.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    print(
        json.dumps(
            prepare()
            if args.prepare
            else freeze()
            if args.freeze
            else qa()
            if args.qa
            else resume(args.expected_manifest_sha256),
            sort_keys=True,
        )
    )
