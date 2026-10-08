"""Compare the Phase 1.4.12 technical run with the unmodified v0.4.11 analyzer."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.market_analysis import StructureAnalysisMode, analyze_market
from crypto_bot.strategy.recovery_ablation import market_fingerprint


def load_legacy(root: Path):
    path = root / "src/crypto_bot/strategy/market_analysis.py"
    spec = importlib.util.spec_from_file_location("phase1411_legacy_market_compat", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load legacy analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--timeframes", nargs="+", type=int, default=[15, 60, 240])
    parser.add_argument("--data-root", type=Path, default=Path("data/history/bybit"))
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/reports/phase1_4_14/v0_4_11_fingerprint_comparison.json"),
    )
    args = parser.parse_args()
    if any(tf <= 0 for tf in args.timeframes):
        parser.error("timeframes must be positive")

    legacy = load_legacy(args.legacy_root)
    rows = []
    for symbol in args.symbols:
        for timeframe in args.timeframes:
            path = args.data_root / symbol / f"{timeframe}.csv"
            candles = [r.to_strategy_candle(timeframe * 60000) for r in read_klines_csv(path)]
            start = perf_counter()
            old = legacy.analyze_market(candles, timeframe_minutes=timeframe)
            legacy_seconds = perf_counter() - start
            start = perf_counter()
            technical = analyze_market(
                candles,
                timeframe_minutes=timeframe,
                analysis_mode=StructureAnalysisMode.TECHNICAL_RECOVERY,
            )
            technical_seconds = perf_counter() - start
            rows.append(
                {
                    "symbol": symbol,
                    "timeframe_minutes": timeframe,
                    "candle_count": len(candles),
                    "legacy_event_count": len(old.events),
                    "technical_event_count": len(technical.events),
                    "legacy_fingerprint": market_fingerprint(old),
                    "technical_fingerprint": market_fingerprint(technical),
                    "fingerprint_equal": market_fingerprint(old) == market_fingerprint(technical),
                    "legacy_seconds": round(legacy_seconds, 6),
                    "technical_seconds": round(technical_seconds, 6),
                }
            )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "version": "0.4.14",
                "legacy_version": "0.4.11",
                "mode": StructureAnalysisMode.TECHNICAL_RECOVERY.value,
                "symbols": args.symbols,
                "timeframes": args.timeframes,
                "rows": rows,
                "all_fingerprints_equal": all(row["fingerprint_equal"] for row in rows),
                "scope": "Compatibility spot-check; the full 5m v0.4.11 run is intentionally not repeated because its unoptimized O(n^2) scan is prohibitively slow.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(args.report)
    print(f"all_fingerprints_equal={all(row['fingerprint_equal'] for row in rows)}")
    return 0 if all(row["fingerprint_equal"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
