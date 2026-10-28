from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.data.verify import DatasetVerification, require_replay_eligible_dataset
from crypto_bot.strategy.pure_source_replay_v2 import ReplaySeries


@dataclass(frozen=True)
class VerifiedReplaySeries:
    series: ReplaySeries
    verification: DatasetVerification
    csv_path: Path
    manifest_path: Path


def load_verified_replay_series(
    csv_path: str | Path,
    manifest_path: str | Path,
) -> VerifiedReplaySeries:
    """Load one persisted dataset into Stage-10 replay only after verification."""
    csv = Path(csv_path)
    manifest = Path(manifest_path)
    verification = require_replay_eligible_dataset(csv, manifest)
    candles = tuple(read_klines_csv(csv))
    replay = ReplaySeries(
        timeframe=verification.manifest.interval,
        interval_ms=verification.manifest.interval_ms,
        candles=candles,
    )
    return VerifiedReplaySeries(
        series=replay,
        verification=verification,
        csv_path=csv,
        manifest_path=manifest,
    )


def load_verified_mtf_replay_series(
    datasets: Iterable[tuple[str | Path, str | Path]],
) -> tuple[VerifiedReplaySeries, ...]:
    """Load an MTF replay set while enforcing one exchange/symbol and unique TFs."""
    loaded = tuple(load_verified_replay_series(csv, manifest) for csv, manifest in datasets)
    if not loaded:
        raise ValueError("at least one verified replay dataset is required")

    first = loaded[0].verification.manifest
    identity = (first.exchange, first.symbol)
    timeframes: set[str] = set()
    for item in loaded:
        manifest = item.verification.manifest
        if (manifest.exchange, manifest.symbol) != identity:
            raise ValueError("MTF replay datasets must share exchange and symbol")
        if manifest.interval in timeframes:
            raise ValueError(f"duplicate MTF replay interval: {manifest.interval}")
        timeframes.add(manifest.interval)

    return tuple(sorted(loaded, key=lambda item: (item.series.interval_ms, str(item.series.timeframe))))
