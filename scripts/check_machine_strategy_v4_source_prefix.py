"""Sealed-source prefix/future mutation checks; position engines are trapped."""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from machine_strategy_v4_historical_adapter import (
    V4HistoricalAdapter,
    identity,
    market_inputs,
)
from okx_v3_input_bridge_v1 import aggregate

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_implementation_readiness_v1"


def check():
    start = 1728777600  # 2024-10-13T00:00:00Z, fixed exposed-development start.
    cutoff = start + 7 * 86400
    receipt = {
        "scope": "BOUNDED_SOURCE_ONLY_PROTOTYPE_CAUSALITY_NOT_IMPLEMENTATION_READY",
        "decision": "MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP",
        "cutoff": cutoff,
        "products": {},
        "historical_position_evaluations": 0,
        "financial_authorization": False,
        "trade_entry_allowed": False,
    }
    forbidden = {
        "observe_m15_bar",
        "_drive_case",
        "_cash",
        "_funding_min",
        "_closed_cash",
        "evaluate_fixture",
        "evaluate_historical_catalog",
    }

    def trap(frame, event, arg):
        if event == "call" and frame.f_code.co_name in forbidden:
            raise RuntimeError("HISTORICAL_POSITION_ENGINE_FORBIDDEN")

    for product in ("BTC-USDT-SWAP", "ETH-USDT-SWAP"):
        market = market_inputs(product)
        end = market[15][-1].end
        prefix = {
            tf: [b for b in bars if b.end <= cutoff] for tf, bars in market.items()
        }
        native = []
        for b in market[15]:
            native.append(
                b
                if b.end <= cutoff
                else replace(
                    b,
                    **{
                        k: getattr(b, k) * Decimal(2)
                        for k in ("open", "high", "low", "close")
                    },
                )
            )
        mutated = {15: native}
        for tf in (60, 240, 1440):
            mutated[tf], _ = aggregate(native, tf * 60)
        digests = []
        baseline = None
        old = sys.getprofile()
        sys.setprofile(trap)
        try:
            for label, source in (
                ("full", market),
                ("prefix", prefix),
                ("future_mutated", mutated),
            ):
                rows, audit = V4HistoricalAdapter(product, source, start, end).catalog(
                    cutoff
                )
                digests.append(identity("source_replay", rows, audit))
                if baseline is None:
                    baseline = audit
                print("SOURCE_ONLY", product, label, "complete", flush=True)
        finally:
            sys.setprofile(old)
        if len(set(digests)) != 1:
            raise RuntimeError("SOURCE_PREFIX_OR_FUTURE_MUTATION_MISMATCH")
        assert baseline is not None
        receipt["products"][product] = {
            "full_prefix_digest": digests[0],
            "trimmed_prefix_digest": digests[1],
            "future_mutation_digest": digests[2],
            "raw_origin_count": len(baseline["raw_origins"]),
            "raw_families": dict(Counter(r[1] for r in baseline["raw_origins"])),
            "frame_prefix_digests": baseline["frame_prefix_digests"],
            "position_engine_trap_active": True,
            "source_only_causality": "PASS",
            "selected_POI_first_test_conformance": "UNRESOLVED_FROZEN_DESIGN",
        }
    (DEST / "SOURCE_PREFIX_REPLAY_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return receipt


if __name__ == "__main__":
    result = check()
    print(
        json.dumps(
            {
                "source_only_causality": "PASS",
                "products": len(result["products"]),
                "historical_position_evaluations": 0,
                "implementation_ready": False,
            }
        )
    )
