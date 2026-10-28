from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crypto_bot.data.coverage import CoverageReport, audit_coverage
from crypto_bot.data.manifest import DatasetManifest, build_dataset_manifest, write_dataset_manifest
from crypto_bot.data.models import HistoricalFetch
from crypto_bot.data.qa import DataQualityReport, audit_klines
from crypto_bot.data.storage import write_klines_csv


@dataclass(frozen=True)
class PersistedDataset:
    csv_path: Path
    manifest_path: Path
    manifest: DatasetManifest
    qa: DataQualityReport
    coverage: CoverageReport

    @property
    def is_healthy(self) -> bool:
        return self.qa.is_healthy and self.coverage.missing_count == 0 and self.manifest.closed_only


def persist_audited_dataset(
    fetch: HistoricalFetch,
    *,
    interval_ms: int,
    output_root: str | Path,
    source: str,
) -> PersistedDataset:
    """Audit, persist and fingerprint one historical candle dataset.

    The function is exchange-agnostic. It writes the raw canonical CSV and a
    deterministic manifest beside it. Persistence does not turn unhealthy data
    into valid data: callers must inspect ``is_healthy`` before using a dataset
    for a deterministic replay.
    """
    if not fetch.candles:
        raise ValueError("cannot persist an empty historical dataset")

    qa = audit_klines(fetch.candles, interval_ms)
    coverage = audit_coverage(fetch, interval_ms)
    root = Path(output_root)
    csv_path = root / fetch.exchange.lower() / fetch.symbol.upper() / f"{fetch.interval}.csv"
    manifest_path = csv_path.with_suffix(".manifest.json")

    write_klines_csv(fetch.candles, csv_path)
    manifest = build_dataset_manifest(
        fetch.candles,
        interval_ms=interval_ms,
        source=source,
        requested_start_ms=fetch.requested_start_ms,
        requested_end_ms=fetch.requested_end_ms,
    )
    write_dataset_manifest(manifest, manifest_path)
    return PersistedDataset(
        csv_path=csv_path,
        manifest_path=manifest_path,
        manifest=manifest,
        qa=qa,
        coverage=coverage,
    )
