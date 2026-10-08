from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from crypto_bot.data.models import MarketCandle


class DataIssueKind(str, Enum):
    GAP = "GAP"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INVALID_OHLC = "INVALID_OHLC"
    UNFINISHED = "UNFINISHED"
    MISALIGNED_TIMESTAMP = "MISALIGNED_TIMESTAMP"
    METADATA_MISMATCH = "METADATA_MISMATCH"


@dataclass(frozen=True)
class DataIssue:
    kind: DataIssueKind
    open_time_ms: int | None
    detail: str


@dataclass(frozen=True)
class DataQualityReport:
    total_rows: int
    unique_rows: int
    gap_count: int
    duplicate_count: int
    out_of_order_count: int
    unfinished_count: int
    invalid_ohlc_count: int
    misaligned_count: int
    metadata_mismatch_count: int
    issues: tuple[DataIssue, ...]

    @property
    def is_healthy(self) -> bool:
        return not self.issues


def audit_klines(candles: Sequence[MarketCandle], interval_ms: int) -> DataQualityReport:
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")

    issues: list[DataIssue] = []
    duplicate_count = 0
    out_of_order_count = 0
    unfinished_count = 0
    invalid_ohlc_count = 0
    gap_count = 0
    misaligned_count = 0
    metadata_mismatch_count = 0

    expected_identity = None
    if candles:
        first = candles[0]
        expected_identity = (first.exchange, first.symbol, first.interval)

    seen: set[int] = set()
    previous_input_time: int | None = None
    for candle in candles:
        if expected_identity is not None and (candle.exchange, candle.symbol, candle.interval) != expected_identity:
            metadata_mismatch_count += 1
            issues.append(
                DataIssue(
                    DataIssueKind.METADATA_MISMATCH,
                    candle.open_time_ms,
                    f"Mixed series metadata: expected {expected_identity}, got {(candle.exchange, candle.symbol, candle.interval)}",
                )
            )

        if candle.open_time_ms in seen:
            duplicate_count += 1
            issues.append(DataIssue(DataIssueKind.DUPLICATE, candle.open_time_ms, "Duplicate candle open time"))
        seen.add(candle.open_time_ms)

        if previous_input_time is not None and candle.open_time_ms < previous_input_time:
            out_of_order_count += 1
            issues.append(DataIssue(DataIssueKind.OUT_OF_ORDER, candle.open_time_ms, "Input is not chronological"))
        previous_input_time = candle.open_time_ms

        if not candle.is_closed:
            unfinished_count += 1
            issues.append(DataIssue(DataIssueKind.UNFINISHED, candle.open_time_ms, "Unfinished candle present"))

        # Phase 1.2 supports fixed UTC-epoch-aligned intraday/D intervals only.
        # Weekly/monthly boundaries are intentionally excluded by the adapter.
        if candle.open_time_ms % interval_ms != 0:
            misaligned_count += 1
            issues.append(
                DataIssue(
                    DataIssueKind.MISALIGNED_TIMESTAMP,
                    candle.open_time_ms,
                    f"Candle open time is not aligned to {interval_ms} ms boundary",
                )
            )

        if candle.low > min(candle.open, candle.close, candle.high) or candle.high < max(candle.open, candle.close, candle.low):
            invalid_ohlc_count += 1
            issues.append(DataIssue(DataIssueKind.INVALID_OHLC, candle.open_time_ms, "Invalid OHLC bounds"))

    unique_sorted = sorted(seen)
    for left, right in zip(unique_sorted, unique_sorted[1:]):
        delta = right - left
        if delta > interval_ms:
            missing = max(1, delta // interval_ms - 1)
            gap_count += missing
            issues.append(
                DataIssue(
                    DataIssueKind.GAP,
                    left + interval_ms,
                    f"Missing {missing} candle(s) between {left} and {right}",
                )
            )
        elif delta != interval_ms:
            # A non-multiple/short interval is also structurally unhealthy.
            gap_count += 1
            issues.append(
                DataIssue(
                    DataIssueKind.GAP,
                    right,
                    f"Unexpected candle spacing: {delta} ms, expected {interval_ms} ms",
                )
            )

    return DataQualityReport(
        total_rows=len(candles),
        unique_rows=len(seen),
        gap_count=gap_count,
        duplicate_count=duplicate_count,
        out_of_order_count=out_of_order_count,
        unfinished_count=unfinished_count,
        invalid_ohlc_count=invalid_ohlc_count,
        misaligned_count=misaligned_count,
        metadata_mismatch_count=metadata_mismatch_count,
        issues=tuple(issues),
    )
