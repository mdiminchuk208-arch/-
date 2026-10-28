from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crypto_bot.data.coverage import CoverageReport, audit_coverage
from crypto_bot.data.manifest import DatasetManifest, candle_content_sha256, read_dataset_manifest
from crypto_bot.data.models import HistoricalFetch
from crypto_bot.data.qa import DataQualityReport, audit_klines
from crypto_bot.data.storage import read_klines_csv


@dataclass(frozen=True)
class DatasetVerification:
    manifest: DatasetManifest
    qa: DataQualityReport
    coverage: CoverageReport
    observed_content_sha256: str
    hash_matches: bool
    identity_matches: bool
    row_count_matches: bool
    bounds_match: bool

    @property
    def is_replay_eligible(self) -> bool:
        return (
            self.hash_matches
            and self.identity_matches
            and self.row_count_matches
            and self.bounds_match
            and self.manifest.closed_only
            and self.qa.is_healthy
            and self.coverage.missing_count == 0
        )


def verify_persisted_dataset(
    csv_path: str | Path,
    manifest_path: str | Path,
) -> DatasetVerification:
    """Verify a persisted candle dataset against its immutable manifest.

    This is a fail-closed gate intended to sit immediately before deterministic
    replay/backtest loading. It does not repair data and it does not rewrite a
    manifest. Any mismatch means the dataset is not replay-eligible.
    """
    manifest = read_dataset_manifest(manifest_path)
    candles = read_klines_csv(csv_path)

    if not candles:
        raise ValueError("persisted candle dataset is empty")

    observed_hash = candle_content_sha256(candles)
    identity = (manifest.exchange, manifest.symbol, manifest.interval)
    identity_matches = all(
        (candle.exchange, candle.symbol, candle.interval) == identity for candle in candles
    )
    row_count_matches = len(candles) == manifest.row_count
    observed_first = min(candle.open_time_ms for candle in candles)
    observed_last = max(candle.open_time_ms for candle in candles)
    bounds_match = (
        observed_first == manifest.first_open_time_ms
        and observed_last == manifest.last_open_time_ms
    )

    qa = audit_klines(candles, manifest.interval_ms)
    fetch = HistoricalFetch(
        exchange=manifest.exchange,
        symbol=manifest.symbol,
        interval=manifest.interval,
        requested_start_ms=(
            manifest.requested_start_ms
            if manifest.requested_start_ms is not None
            else observed_first
        ),
        requested_end_ms=(
            manifest.requested_end_ms
            if manifest.requested_end_ms is not None
            else observed_last
        ),
        server_time_ms=max(
            observed_last + manifest.interval_ms,
            manifest.requested_end_ms or observed_last,
        ),
        candles=tuple(candles),
    )
    coverage = audit_coverage(fetch, manifest.interval_ms)

    return DatasetVerification(
        manifest=manifest,
        qa=qa,
        coverage=coverage,
        observed_content_sha256=observed_hash,
        hash_matches=observed_hash == manifest.content_sha256,
        identity_matches=identity_matches,
        row_count_matches=row_count_matches,
        bounds_match=bounds_match,
    )


def require_replay_eligible_dataset(
    csv_path: str | Path,
    manifest_path: str | Path,
) -> DatasetVerification:
    result = verify_persisted_dataset(csv_path, manifest_path)
    if not result.is_replay_eligible:
        reasons: list[str] = []
        if not result.hash_matches:
            reasons.append("CONTENT_HASH_MISMATCH")
        if not result.identity_matches:
            reasons.append("DATASET_IDENTITY_MISMATCH")
        if not result.row_count_matches:
            reasons.append("ROW_COUNT_MISMATCH")
        if not result.bounds_match:
            reasons.append("TIME_BOUNDS_MISMATCH")
        if not result.manifest.closed_only:
            reasons.append("MANIFEST_NOT_CLOSED_ONLY")
        if not result.qa.is_healthy:
            reasons.append("DATA_QUALITY_FAILED")
        if result.coverage.missing_count:
            reasons.append("COVERAGE_INCOMPLETE")
        raise ValueError("dataset is not replay-eligible: " + ",".join(reasons))
    return result
