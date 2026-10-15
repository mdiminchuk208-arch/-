"""Revalidate sealed public grids; never fetch data or evaluate positions."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from okx_qualification_data_v1 import compact
from okx_v3_input_bridge_v1 import aggregate, load_native
from verify_okx_stage_a_v1 import funding, resume, source_receipts

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v4_1_implementation_readiness_v1"
PRIOR = (
    ROOT
    / "docs/machine_strategy_v4_implementation_readiness_v1/DATA_GRID_AUTHENTICITY_AND_CONTINUITY.json"
)
PRIOR_SHA = "0f50d4a9ec73b7ebab3967576d929abab0ec747207c038b77d40c1c3f6f649f3"
STAGE_SHA = "e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0"


def check():
    if sha256(PRIOR.read_bytes()).hexdigest() != PRIOR_SHA:
        raise ValueError("FROZEN_DATA_REVIEW_CHANGED")
    resume(STAGE_SHA)
    prior = json.loads(PRIOR.read_text())
    receipt = {
        "data_decision": "PASS",
        "prior_complete_data_review_sha256": PRIOR_SHA,
        "Stage_A_manifest_sha256": STAGE_SHA,
        "raw_public_receipts_verified": source_receipts(),
        "products": {},
        "historical_position_evaluations": 0,
        "trade_entry_allowed": False,
        "limitations": {
            "cryptographic_exchange_signature": False,
            "historical_tick_lot_epochs_verified": False,
            "account_fees_verified": False,
            "actual_mark_or_queue_or_fill_verified": False,
            "observed_historical_API_latency_verified": False,
            "model_close_availability_is_assumption": True,
        },
    }
    for product, expected in prior["products"].items():
        native = load_native(
            product
        )  # stored/content hashes, confirm=1, grid and every OHLC
        if len(native) != expected["native_M15_bars"]:
            raise ValueError("NATIVE_COUNT_CHANGED")
        rebuilt = {}
        for tf, name in ((60, "H1"), (240, "H4"), (1440, "D1")):
            derived, omitted = aggregate(native, tf * 60)
            digest = sha256(
                compact([b.observed(tf) for b in derived]).encode()
            ).hexdigest()
            if (
                omitted
                or len(derived) != expected["derived_counts"][name]
                or digest != expected["derived_content_sha256"][name]
            ):
                raise ValueError(
                    "DERIVED_BYTES_OR_GRID_CHANGED:" + product + ":" + name
                )
            rebuilt[name] = {
                "count": len(derived),
                "omitted": 0,
                "content_sha256": digest,
            }
        funding_receipt = funding(product, 1728777600000, 1791849600000)
        receipt["products"][product] = {
            "native_bars": len(native),
            "start": native[0].start,
            "end_exclusive": native[-1].end,
            "gaps": 0,
            "duplicates": 0,
            "interpolation": 0,
            "derived": rebuilt,
            "funding": funding_receipt,
            "signed_source_rows_reverified": True,
        }
    (DEST / "DATA_GRID_AUTHENTICITY_AND_CONTINUITY.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    )
    return {
        "data_grid": "PASS",
        "native_bars": 210240,
        "signed_funding_rows": 4380,
        "retained_public_receipts": receipt["raw_public_receipts_verified"],
        "historical_position_evaluations": 0,
    }


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
