"""Materialize one v3 annotation unit as a strictly cutoff-limited view."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from materialize_original_v1_1_annotation_pack import read_prefix
from original_strategy_executable_profile_v1 import digest
from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_financial_data import ROOT, checksum, save
from run_original_v1_1_evidence_completion_v3 import DEST, resume


def materialize(unit, *, root=DEST):
    no_outcomes(unit)
    at = unit["decision_cutoff"]
    objects, candles = {}, {}
    for tf, view in unit["blinded_prefixes"].items():
        if view["decision_cutoff"] != at:
            raise ValueError("Unit cutoff inconsistent")
        objects[tf] = list(read_prefix(root / view["objects_file"], at))
        candles[tf] = list(read_prefix(ROOT / view["blinded_candles_file"], at))
        if (
            len(candles[tf]) != view["completed_candles"]
            or len(objects[tf]) != view["objects"]
        ):
            raise ValueError("Causal prefix count changed")
        hashed = "0" * 64
        for obj in objects[tf]:
            hashed = digest(["CAUSAL_OBJECT_PREFIX_v3", hashed, obj["id"]])
        if hashed != view["object_prefix_sha256"]:
            raise ValueError("Causal object prefix changed")
    result = {
        "annotation_unit": unit,
        "causal_objects": objects,
        "completed_candles": candles,
        "states": ["PASS", "FAIL", "UNKNOWN"],
        "annotation_protocol": "EVIDENCE_COMPLETION_V3_SPEC.md",
        "future_candles_exposed": False,
        "trade_entry_allowed": False,
    }
    no_outcomes(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("New output path required")
    resume()
    with gzip.open(DEST / "ANNOTATION_UNIT_MAP.jsonl.gz", "rt") as stream:
        for line in stream:
            unit = json.loads(line)
            if unit["annotation_unit_id"] == args.unit_id:
                result = materialize(unit)
                save(args.output, result)
                print(
                    "BLINDED_V3_UNIT_MATERIALIZED",
                    checksum(args.output),
                    "finance NOT_RUN",
                )
                return
    raise SystemExit("Annotation unit not found")


if __name__ == "__main__":
    main()
