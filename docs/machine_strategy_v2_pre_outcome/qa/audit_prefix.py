"""Outcome-free actual prefix/future-mutation and mode audit of frozen machine cohort."""

from __future__ import annotations

from machine_strategy_v2_core import build_cohort
from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_financial_data import ROOT, Bar, compact, load_market, save
from run_machine_strategy_research import rows

CUTOFF = 1719792000  # 2024-07-01 UTC, fixed midpoint audit; not a strategy parameter.


def audit():
    market, _ = load_market()
    frozen = rows(ROOT / "docs/machine_strategy_v2_pre_outcome/FROZEN_CASES.jsonl.gz")
    receipt = {
        "cutoff": CUTOFF,
        "symbols": {},
        "status": "PASS",
        "trade_entry_allowed": False,
    }
    for symbol in ("BTCUSDT", "ETHUSDT"):
        expected = [
            r for r in frozen if r["symbol"] == symbol and r["decision_at"] <= CUTOFF
        ]
        prefix = {
            tf: [b for b in data if b.end <= CUTOFF]
            for tf, data in market[symbol].items()
        }
        actual, _ = build_cohort(symbol, prefix, mode="SHADOW")
        if compact(actual) != compact(expected):
            raise ValueError("Real historical prefix inconsistency")
        mutated = {
            tf: [
                b
                if b.end <= CUTOFF
                else Bar(
                    b.start, b.end, b.open * 10, b.high * 10, b.low * 10, b.close * 10
                )
                for b in data
            ]
            for tf, data in market[symbol].items()
        }
        future, _ = build_cohort(symbol, mutated)
        retained = [r for r in future if r["decision_at"] <= CUTOFF]
        if compact(retained) != compact(expected):
            raise ValueError("Future mutation changed past machine case")
        for r in expected:
            no_outcomes(r)
            if any(
                r[k] > r["decision_at"]
                for k in (
                    "known_at",
                    "confirmation_known_at",
                    "FTA_known_at",
                    "poi_born_at",
                )
            ):
                raise ValueError("Historical pre-entry future evidence")
            if r["source_validated"] is not False:
                raise ValueError("Machine case promoted to SOURCE")
        receipt["symbols"][symbol] = {
            "prefix_cases": len(expected),
            "prefix_SHADOW_identity": "PASS",
            "future_suffix_10x_mutation": "PASS",
        }
        print("ACTUAL_PREFIX_QA", symbol, len(expected), flush=True)
    save(
        ROOT
        / "docs/machine_strategy_v2_pre_outcome/ACTUAL_PREFIX_FUTURE_MUTATION_QA.json",
        receipt,
    )


if __name__ == "__main__":
    audit()
