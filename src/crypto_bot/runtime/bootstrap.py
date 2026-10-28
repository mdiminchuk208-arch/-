from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from crypto_bot.data.replay_loader import load_verified_mtf_replay_series
from crypto_bot.runtime.mtf_buffer import LiveMtfBuffer


@dataclass(frozen=True)
class MtfBootstrapReport:
    exchange: str
    symbol: str
    inserted_count: int
    duplicate_count: int
    series_counts: tuple[tuple[str, int], ...]
    ready: bool


def bootstrap_live_mtf_from_verified_datasets(
    buffer: LiveMtfBuffer,
    datasets: Iterable[tuple[str | Path, str | Path]],
    *,
    require_all_configured_timeframes: bool = True,
) -> MtfBootstrapReport:
    """Seed live durable MTF state only from replay-eligible persisted datasets.

    Every CSV is verified against its immutable manifest before any candle is
    accepted. Exact duplicates are idempotent, so the same bootstrap can be
    safely repeated after a process restart.
    """
    loaded = load_verified_mtf_replay_series(datasets)
    manifest_identity = (
        loaded[0].verification.manifest.exchange.upper(),
        loaded[0].verification.manifest.symbol.upper(),
    )
    if manifest_identity != (buffer.exchange, buffer.symbol):
        raise ValueError("verified bootstrap dataset identity does not match live MTF buffer")

    supplied = {str(item.series.timeframe) for item in loaded}
    configured = set(buffer.specs)
    unknown = supplied - configured
    if unknown:
        raise ValueError(f"verified bootstrap contains unconfigured timeframes: {sorted(unknown)}")
    if require_all_configured_timeframes and supplied != configured:
        missing = configured - supplied
        raise ValueError(f"verified bootstrap is missing configured timeframes: {sorted(missing)}")

    inserted = 0
    duplicates = 0
    series_counts: list[tuple[str, int]] = []
    for item in loaded:
        timeframe = str(item.series.timeframe)
        spec = buffer.specs[timeframe]
        if item.series.interval_ms != spec.interval_ms:
            raise ValueError(f"verified bootstrap interval mismatch for {timeframe}")
        count = 0
        for candle in item.series.candles:
            if buffer.ingest(candle):
                inserted += 1
            else:
                duplicates += 1
            count += 1
        series_counts.append((timeframe, count))

    # Full retained history is re-validated by the replay snapshot builder.
    buffer.replay_series(require_ready=require_all_configured_timeframes)
    status = buffer.status()
    return MtfBootstrapReport(
        exchange=buffer.exchange,
        symbol=buffer.symbol,
        inserted_count=inserted,
        duplicate_count=duplicates,
        series_counts=tuple(sorted(series_counts, key=lambda row: buffer.specs[row[0]].interval_ms)),
        ready=status.ready,
    )
