from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from crypto_bot.data.replay_loader import load_verified_mtf_replay_series
from crypto_bot.strategy.pure_source_diagnostic_replay_v2 import (
    build_source_diagnostic_artifact,
    verify_source_diagnostic_artifact,
)


DEFAULT_INTERVALS = ("5", "15", "60", "240", "D")


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"unsupported diagnostic JSON value: {type(value).__name__}")


def artifact_to_json(artifact: object) -> str:
    return json.dumps(
        asdict(artifact),
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        default=_json_default,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify persisted OKX MTF datasets and run the fail-closed PURE SOURCE "
            "diagnostic replay. This is not a financial backtest."
        )
    )
    parser.add_argument("--symbol", default="BTC-USDT-SWAP")
    parser.add_argument("--intervals", nargs="+", default=list(DEFAULT_INTERVALS))
    parser.add_argument("--data-root", default="data/history")
    parser.add_argument("--output-root", default="artifacts/diagnostic")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    data_root = Path(args.data_root)
    dataset_paths: list[tuple[Path, Path]] = []
    for interval in args.intervals:
        csv_path = data_root / "okx" / symbol / f"{interval}.csv"
        manifest_path = csv_path.with_suffix(".manifest.json")
        if not csv_path.exists() or not manifest_path.exists():
            print(
                f"ERROR: missing verified dataset files for {symbol} {interval}: "
                f"{csv_path} / {manifest_path}"
            )
            return 2
        dataset_paths.append((csv_path, manifest_path))

    try:
        loaded = load_verified_mtf_replay_series(dataset_paths)
        artifact = build_source_diagnostic_artifact(tuple(item.series for item in loaded))
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 2

    if not verify_source_diagnostic_artifact(artifact):
        print("ERROR: diagnostic artifact self-fingerprint verification failed")
        return 2
    if artifact.trade_entry_allowed or artifact.financial_run:
        print("ERROR: fail-closed PURE SOURCE diagnostic unexpectedly exposed financial execution")
        return 2

    output_path = Path(args.output_root) / "okx" / symbol / "pure_source_diagnostic.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(artifact_to_json(artifact), encoding="utf-8")

    print(f"PURE SOURCE diagnostic replay: {symbol}")
    print(f"  intervals:                  {' '.join(str(item.series.timeframe) for item in loaded)}")
    print(f"  dataset_sha256:             {artifact.dataset_sha256}")
    print(f"  receipt_count:              {artifact.receipt_count}")
    print(f"  causal_object_count:        {artifact.causal_object_count}")
    print(f"  setup_count:                {artifact.setup_count}")
    print(f"  execution_plan_count:       {artifact.execution_plan_count}")
    print(f"  source_ready_setup_count:   {artifact.source_ready_setup_count}")
    print(f"  baseline_identifiability:   {artifact.baseline_identifiability}")
    print(f"  trade_entry_allowed:        {artifact.trade_entry_allowed}")
    print(f"  financial_run:              {artifact.financial_run}")
    print(f"  artifact_sha256:            {artifact.artifact_sha256}")
    print(f"  output:                     {output_path}")
    if artifact.unresolved:
        print("  unresolved:")
        for row in artifact.unresolved:
            print(f"    {row.layer}/{row.status} x{row.observation_count}: {row.reason}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
