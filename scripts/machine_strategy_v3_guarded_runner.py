"""Later v3 outcome infrastructure, fail-closed during implementation readiness.

This module's only runnable test path uses internally registered toy fixtures.
There is no caller-supplied 'synthetic' switch and no exchange/order client.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from machine_strategy_research_io import verify_machine
from machine_strategy_v3_contracts import (
    CONTRACT_TYPE,
    ContractWait,
    cash_stop_identity,
    censor_eof,
    holding_duration_bounds,
    observe_m15_bar,
    proven_tick_epoch,
)
from machine_strategy_v3_historical_adapter import (
    HistoricalAdapter,
    bar_record,
    derive_market,
    load_primary,
)
from original_v1_1_financial_data import END, ROOT, START, Bar, compact

_MARKER = object()
COUNTERS = {
    "historical_attempts_blocked": 0,
    "historical_outcome_evaluations": 0,
    "synthetic_fixture_runs": 0,
}


class HistoricalOutcomeBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class _Authorization:
    marker: object
    manifest_path: Path
    manifest_sha256: str
    authorization_path: Path
    authorization_sha256: str


def authorize_later(authorization_path):
    """Requires a separate authorized phase and a committed READY freeze."""
    task = (ROOT / "agent_control/NEXT_TASK.md").read_text()
    if "Implementation Readiness Freeze" in task.splitlines()[0]:
        raise HistoricalOutcomeBlocked(
            "IMPLEMENTATION_READINESS_FORBIDS_HISTORICAL_OUTCOMES"
        )
    authorization = json.loads(Path(authorization_path).read_text())
    if (
        authorization.get("authorized_by_user") is not True
        or authorization.get("phase") != "FIRST_V3_DEVELOPMENT_FINANCIAL_BACKTEST"
        or authorization.get("task_sha256") != sha256(task.encode()).hexdigest()
    ):
        raise HistoricalOutcomeBlocked("MISSING_SEPARATE_FINANCIAL_AUTHORIZATION")
    relative = authorization["implementation_manifest"]
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / "docs") or path.name != "freeze_manifest.json":
        raise HistoricalOutcomeBlocked("INVALID_IMPLEMENTATION_FREEZE_PATH")
    expected = authorization["implementation_manifest_sha256"]
    manifest = json.loads(path.read_text())
    if (
        manifest.get("decision")
        != "V3_IMPLEMENTATION_FROZEN_READY_FOR_FIRST_FINANCIAL_BACKTEST"
    ):
        raise HistoricalOutcomeBlocked("IMPLEMENTATION_NOT_FINANCIALLY_READY")
    verify_machine(path.parent, expected)
    committed = subprocess.check_output(
        ["git", "show", authorization["freeze_commit"] + ":" + relative], cwd=ROOT
    )
    if sha256(committed).hexdigest() != expected:
        raise HistoricalOutcomeBlocked("FREEZE_COMMIT_BYTES_MISMATCH")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", authorization["freeze_commit"], "HEAD"],
        cwd=ROOT,
        check=True,
    )
    return _Authorization(
        _MARKER,
        path,
        expected,
        Path(authorization_path).resolve(),
        sha256(Path(authorization_path).read_bytes()).hexdigest(),
    )


def _authorized(capability):
    task = (ROOT / "agent_control/NEXT_TASK.md").read_text()
    if "Implementation Readiness Freeze" in task.splitlines()[0]:
        COUNTERS["historical_attempts_blocked"] += 1
        raise HistoricalOutcomeBlocked(
            "IMPLEMENTATION_READINESS_FORBIDS_HISTORICAL_OUTCOMES"
        )
    if not isinstance(capability, _Authorization) or capability.marker is not _MARKER:
        COUNTERS["historical_attempts_blocked"] += 1
        raise HistoricalOutcomeBlocked("NO_COMMITTED_AUTHORIZED_HISTORICAL_CAPABILITY")
    if (
        sha256(capability.authorization_path.read_bytes()).hexdigest()
        != capability.authorization_sha256
    ):
        raise HistoricalOutcomeBlocked("FINANCIAL_AUTHORIZATION_CHANGED")
    renewed = authorize_later(capability.authorization_path)
    if renewed != capability:
        raise HistoricalOutcomeBlocked("HISTORICAL_CAPABILITY_CHANGED")


def _drive_order(order, bars, epochs, *, capability=None, fixture_name=None):
    """Every kernel entry validates authorization or exact registered toy bytes."""
    if fixture_name is None:
        _authorized(capability)
    else:
        expected_order, expected_bars, expected_epochs = _fixture_inputs(fixture_name)
        if (
            order != expected_order
            or bars != expected_bars
            or epochs != expected_epochs
        ):
            COUNTERS["historical_attempts_blocked"] += 1
            raise HistoricalOutcomeBlocked(
                "INPUTS_DO_NOT_MATCH_REGISTERED_SYNTHETIC_FIXTURE"
            )
    state = dict(order)
    observed_through = order["decision_at"]
    for bar in bars:
        if bar.start < order["decision_at"]:
            continue
        try:
            state = observe_m15_bar(state, bar_record(bar), epochs)
        except ContractWait as exc:
            return {
                **state,
                "status": "UNRESOLVED_METADATA"
                if exc.reason == "WAIT_HISTORICAL_TICK_METADATA"
                else "UNRESOLVED_DATA_GAP",
                "status_before_uncertainty": state["status"],
                "uncertainty_reason": exc.reason,
                "unresolved_since": bar.start,
                "observed_through": observed_through,
                "financial_outcome": None,
                "trade_entry_allowed": False,
            }
        observed_through = bar.end
        if state["status"] not in ("PENDING", "FILLED"):
            break
    if state["status"] in ("PENDING", "FILLED"):
        state = censor_eof(state, observed_through)
    if state["status"] == "EXIT_OBSERVED":
        state["holding_time_bounds"] = holding_duration_bounds(
            state["fill_time_bounds"], state["event_time_bounds"]
        )
    return state


def _closed_record(state, capability=None):
    """Defined for the later authorized phase; never called in readiness QA."""
    _authorized(capability)
    if state["status"] != "EXIT_OBSERVED":
        return {
            **state,
            "financial_outcome": None,
        }
    amounts = cash_stop_identity(
        state["fill_price"], state["stop"], state["exit_price"], state["direction"]
    )
    return {
        "case_id": state["case_id"],
        "status": state["status"],
        "amounts": {
            k: str(v) if isinstance(v, Decimal) else v for k, v in amounts.items()
        },
        "funding": None,
        "trade_entry_allowed": False,
    }


def run_historical(symbol, epochs, capability=None):
    # Check capability before loading data, building historical orders or calling exits.
    _authorized(capability)
    m15, source = load_primary(symbol)
    manifest = json.loads(capability.manifest_path.read_text())
    frozen_epochs = json.loads(
        (capability.manifest_path.parent / "TICK_EPOCHS.json").read_text()
    )["verified_core_epochs"]
    if epochs != frozen_epochs:
        raise HistoricalOutcomeBlocked("AUTHORIZED_TICK_EPOCHS_MISMATCH")
    validate_historical_epochs(symbol, frozen_epochs, manifest)
    if manifest["artifacts"].get(source["path"]) != source["sha256"]:
        raise HistoricalOutcomeBlocked("AUTHORIZED_DATASET_HASH_MISMATCH")
    market, _ = derive_market(m15)
    orders, _ = HistoricalAdapter(symbol, market, epochs).run()
    COUNTERS["historical_outcome_evaluations"] += 1
    return [
        _closed_record(
            _drive_order(order, m15, epochs, capability=capability), capability
        )
        for order in orders
    ]


def validate_historical_epochs(symbol, epochs, manifest):
    """Authenticate frozen source/effective-proof bytes and complete dev coverage.

    The pure contract deliberately checks digest syntax only. This boundary
    additionally requires evidence files pinned in the implementation manifest.
    It does not turn an announcement into continuity proof automatically.
    """
    selected = sorted(
        (e for e in epochs if e.get("symbol") == symbol),
        key=lambda e: e["effective_from"],
    )
    cursor = START
    for epoch in selected:
        if epoch["effective_until"] <= START or epoch["effective_from"] >= END:
            continue
        if epoch["effective_from"] > cursor:
            raise HistoricalOutcomeBlocked("HISTORICAL_TICK_COVERAGE_GAP")
        for role in ("source", "effective_proof"):
            name = epoch.get(role + "_path")
            digest = epoch.get(role + "_sha256")
            path = (ROOT / str(name)).resolve()
            if (
                not path.is_relative_to(ROOT / "docs")
                or manifest["artifacts"].get(name) != digest
            ):
                raise HistoricalOutcomeBlocked("TICK_EVIDENCE_NOT_MANIFEST_PINNED")
            if sha256(path.read_bytes()).hexdigest() != digest:
                raise HistoricalOutcomeBlocked("TICK_EVIDENCE_BYTES_MISMATCH")
        if epoch.get("interval_verification_status") != "VERIFIED_COMPLETE_INTERVAL":
            raise HistoricalOutcomeBlocked("TICK_INTERVAL_CONTINUITY_NOT_VERIFIED")
        # Schema, literal verified flag, known publication times, no overlaps.
        proven_tick_epoch(
            epochs=epochs,
            symbol=symbol,
            contract_type=CONTRACT_TYPE,
            at=max(START, epoch["effective_from"]),
            decision_at=max(START, epoch["effective_from"]),
        )
        cursor = max(cursor, epoch["effective_until"])
    if cursor < END:
        raise HistoricalOutcomeBlocked("HISTORICAL_TICK_COVERAGE_GAP")


def _fixture_inputs(name):
    recipes = {
        "open_stop": [(100, 102, 94, 101)],
        "wick_ambiguous": [(102, 111, 99, 103)],
        "prefill_target_gap": [(111, 112, 110, 111)],
        "filled_then_stop_gap": [(102, 103, 99, 101), (94, 96, 93, 95)],
        "filled_eof": [(102, 103, 99, 101)],
        "unfilled_eof": [(102, 103, 101, 102)],
        "dual_touch": [(100, 112, 94, 102)],
        "filled_epoch_change": [(102, 103, 99, 101), (102, 103, 101, 102)],
        "filled_data_gap": [(102, 103, 99, 101), (102, 103, 101, 102)],
    }
    if name not in recipes:
        raise HistoricalOutcomeBlocked("UNKNOWN_INTERNAL_SYNTHETIC_FIXTURE")
    seed = compact(["FIXTURE_ONLY", name, recipes[name]])
    epoch = {
        "id": "fixture_epoch",
        "symbol": "FIXTURE",
        "contract_type": CONTRACT_TYPE,
        "tick": "0.1",
        "verified": True,
        "effective_from": 0,
        "effective_until": 100000,
        "known_at": 0,
        "source_known_at": 0,
        "effective_proof_known_at": 0,
        "source_sha256": sha256(seed.encode()).hexdigest(),
    }
    order = {
        "symbol": "FIXTURE",
        "contract_type": CONTRACT_TYPE,
        "tick_epoch_id": "fixture_epoch",
        "status": "PENDING",
        "direction": "LONG",
        "entry": "100",
        "stop": "95",
        "target": "110",
        "decision_at": 0,
        "expires_at": 3600,
        "trade_entry_allowed": False,
    }
    bars = [
        Bar(i * 900, (i + 1) * 900, *(Decimal(str(v)) for v in row))
        for i, row in enumerate(recipes[name])
    ]
    epochs = [epoch]
    if name == "filled_epoch_change":
        epochs = [
            {**epoch, "effective_until": 900},
            {**epoch, "id": "changed_fixture_epoch", "effective_from": 900},
        ]
    elif name == "filled_data_gap":
        bars[1] = Bar(
            1800, 2700, bars[1].open, bars[1].high, bars[1].low, bars[1].close
        )
    return order, bars, epochs


def run_registered_fixture(name):
    """Only internal fixed synthetic inputs, never arbitrary historical bytes."""
    order, bars, epochs = _fixture_inputs(name)
    COUNTERS["synthetic_fixture_runs"] += 1
    state = _drive_order(order, bars, epochs, fixture_name=name)
    # Return event evidence only, not financial amounts or labels.
    return {
        k: v
        for k, v in state.items()
        if k
        in {
            "status",
            "event_time_bounds",
            "fill_time_bounds",
            "holding_time_bounds",
            "exit_reason",
            "price_evidence_tag",
            "trade_entry_allowed",
            "status_before_uncertainty",
            "uncertainty_reason",
            "unresolved_since",
            "observed_through",
        }
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-fixture")
    parser.add_argument("--historical-symbol", choices=("BTCUSDT", "ETHUSDT"))
    parser.add_argument("--financial-authorization", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.synthetic_fixture:
        print(json.dumps(run_registered_fixture(args.synthetic_fixture), default=str))
    elif args.historical_symbol:
        if not args.financial_authorization:
            raise HistoricalOutcomeBlocked("HISTORICAL_FINANCIAL_RUN_NOT_AUTHORIZED")
        capability = authorize_later(args.financial_authorization)
        # Tick evidence is independently frozen; records are never inferred here.
        records = json.loads(
            (capability.manifest_path.parent / "TICK_EPOCHS.json").read_text()
        )["verified_core_epochs"]
        if not args.output or args.output.exists():
            raise HistoricalOutcomeBlocked(
                "NEW_SEPARATE_FINANCIAL_OUTPUT_PATH_REQUIRED"
            )
        result = run_historical(args.historical_symbol, records, capability)
        args.output.write_text(
            json.dumps(result, sort_keys=True, indent=2, default=str) + "\n"
        )
    else:
        print("READINESS_ONLY: historical financial evaluation disabled")


if __name__ == "__main__":
    main()
