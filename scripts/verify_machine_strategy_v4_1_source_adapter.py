"""Executed-QA entrypoint for MACHINE_STRATEGY_v4.1 source-only readiness.

This verifier is intentionally incapable of producing historical trade outcomes.
It proves deterministic source/lifecycle replay, future-tail non-influence and a
hard absence of the historical financial runner from the runtime import graph.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from machine_strategy_v4_1_historical_adapter import (
    V41HistoricalSourceAdapter,
    market_inputs,
)
from okx_v3_input_bridge_v1 import NativeBar

PRODUCTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP")
DEV_START = int(datetime(2024, 10, 13, tzinfo=UTC).timestamp())
DEV_END = int(datetime(2026, 10, 13, tzinfo=UTC).timestamp())
FINANCIAL_RUNNER_MODULE = "okx_v3_compatibility_runner_v1"


def _canonical(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def digest(value) -> str:
    return sha256(_canonical(value)).hexdigest()


def _run(product: str, market: dict, cutoff: int) -> tuple[dict, str]:
    adapter = V41HistoricalSourceAdapter(
        product,
        market,
        DEV_START,
        DEV_END,
    )
    proposals, receipt = adapter.run(cutoff)
    assert receipt["historical_position_engine_calls"] == 0
    assert receipt["historical_position_evaluations"] == 0
    assert receipt["financial_outcomes_generated"] is False
    assert receipt["trade_entry_allowed"] is False
    assert all(row["trade_entry_allowed"] is False for row in proposals)
    result = {"proposals": proposals, "receipt": receipt}
    return result, digest(result)


def _mutate_future_m15(market: dict, cutoff: int) -> dict:
    mutated = {tf: list(bars) for tf, bars in market.items()}
    future_index = next(
        (i for i, bar in enumerate(mutated[15]) if bar.start > cutoff + 86400),
        None,
    )
    if future_index is None:
        raise AssertionError("NO_FUTURE_BAR_FOR_MUTATION")
    bar = mutated[15][future_index]
    bump = max(Decimal("0.01"), bar.close * Decimal("0.001"))
    close = bar.close + bump
    high = max(bar.high, close)
    mutated[15][future_index] = NativeBar(
        bar.start,
        bar.end,
        bar.open,
        high,
        bar.low,
        close,
        bar.product,
    )
    return mutated


def verify_product(product: str, *, full: bool) -> dict:
    market = market_inputs(product)
    bounded_cutoff = DEV_START + 7 * 86400

    first, first_digest = _run(product, market, bounded_cutoff)
    _second, second_digest = _run(product, market, bounded_cutoff)
    assert first_digest == second_digest, "NONDETERMINISTIC_PREFIX_REPLAY"

    mutated_market = _mutate_future_m15(market, bounded_cutoff)
    mutated, mutated_digest = _run(product, mutated_market, bounded_cutoff)
    assert mutated_digest == first_digest, "FUTURE_TAIL_MUTATED_PREFIX"
    assert mutated == first, "FUTURE_TAIL_CHANGED_PREFIX_BYTES"

    full_digest = None
    full_replay_digest = None
    if full:
        full_result, full_digest = _run(product, market, DEV_END - 1)
        replay, full_replay_digest = _run(product, market, DEV_END - 1)
        assert full_digest == full_replay_digest, "NONDETERMINISTIC_FULL_REPLAY"
        assert full_result == replay, "FULL_REPLAY_BYTES_DIFFER"

    assert FINANCIAL_RUNNER_MODULE not in sys.modules, "FINANCIAL_RUNNER_IMPORTED"
    return {
        "product": product,
        "bounded_cutoff": bounded_cutoff,
        "bounded_digest": first_digest,
        "future_mutation_digest": mutated_digest,
        "full_executed": full,
        "full_digest": full_digest,
        "full_replay_digest": full_replay_digest,
        "historical_position_engine_calls": 0,
        "financial_runner_imported": False,
        "trade_entry_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="also execute deterministic full development-period replay twice",
    )
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--expected-progress-sha256")
    args = parser.parse_args()
    if FINANCIAL_RUNNER_MODULE in sys.modules:
        raise AssertionError("FINANCIAL_RUNNER_PREIMPORTED")
    if args.full:
        # Full QA uses the checkpointed, externally pinnable production replay.
        # It includes all-history deterministic replay, three preregistered
        # truncated-prefix/future-tail comparisons per product and engine traps.
        from check_machine_strategy_v4_1_source_replay import check

        result = check(args.resume_existing, args.expected_progress_sha256)
        print(json.dumps(result, sort_keys=True))
        return
    receipts = [verify_product(product, full=False) for product in PRODUCTS]
    print(
        json.dumps(
            {
                "decision": "V4_1_SOURCE_ADAPTER_QA_PASS",
                "products": receipts,
                "financial_metrics_generated": False,
                "trade_entry_allowed": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
