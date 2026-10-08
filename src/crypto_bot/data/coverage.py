from __future__ import annotations

from dataclasses import dataclass

from crypto_bot.data.models import HistoricalFetch


@dataclass(frozen=True)
class CoverageReport:
    symbol: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    effective_end_ms: int
    first_expected_ms: int | None
    last_expected_ms: int | None
    first_candle_ms: int | None
    last_candle_ms: int | None
    expected_count: int
    actual_count: int
    missing_count: int
    leading_missing_count: int
    internal_missing_count: int
    trailing_missing_count: int
    missing_open_times_ms: tuple[int, ...]
    completeness_pct: float

    @property
    def boundary_missing_count(self) -> int:
        return self.leading_missing_count + self.trailing_missing_count

    @property
    def has_internal_gap(self) -> bool:
        return self.internal_missing_count > 0

    @property
    def coverage_status(self) -> str:
        if self.missing_count == 0:
            return "COMPLETE"
        if self.internal_missing_count:
            return "INTERNAL_GAP"
        if self.boundary_missing_count:
            return "BOUNDARY_SHORTFALL"
        return "INCOMPLETE"


def _ceil_to_interval(value: int, interval_ms: int) -> int:
    return ((value + interval_ms - 1) // interval_ms) * interval_ms


def _floor_to_interval(value: int, interval_ms: int) -> int:
    return (value // interval_ms) * interval_ms


def audit_coverage(fetch: HistoricalFetch, interval_ms: int) -> CoverageReport:
    """Audit requested-window coverage separately from row-to-row QA.

    DataQualityReport answers: "are the rows we have internally continuous/valid?"
    CoverageReport answers: "did we receive every expected closed slot in the requested window?"

    This distinction explains cases such as 99.9942% coverage with QA healthy=True: the
    fetched series can be internally continuous while missing one requested boundary slot.
    """
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")

    first_expected = _ceil_to_interval(fetch.requested_start_ms, interval_ms)
    latest_closed_open = _floor_to_interval(fetch.server_time_ms - interval_ms, interval_ms)
    effective_end = min(fetch.requested_end_ms, latest_closed_open)
    last_expected = _floor_to_interval(effective_end, interval_ms)

    if last_expected < first_expected:
        expected_times: tuple[int, ...] = ()
    else:
        expected_times = tuple(range(first_expected, last_expected + interval_ms, interval_ms))

    actual_open_times = {
        c.open_time_ms
        for c in fetch.candles
        if first_expected <= c.open_time_ms <= last_expected and c.is_closed
    }
    missing = tuple(t for t in expected_times if t not in actual_open_times)

    if not actual_open_times:
        leading_missing = len(missing)
        internal_missing = 0
        trailing_missing = 0
    else:
        actual_first = min(actual_open_times)
        actual_last = max(actual_open_times)
        leading_missing = sum(t < actual_first for t in missing)
        trailing_missing = sum(t > actual_last for t in missing)
        internal_missing = len(missing) - leading_missing - trailing_missing

    expected_count = len(expected_times)
    actual_count = len(actual_open_times)
    missing_count = len(missing)
    completeness = 100.0 if expected_count == 0 else 100.0 * actual_count / expected_count

    return CoverageReport(
        symbol=fetch.symbol,
        interval=fetch.interval,
        requested_start_ms=fetch.requested_start_ms,
        requested_end_ms=fetch.requested_end_ms,
        effective_end_ms=effective_end,
        first_expected_ms=first_expected if expected_times else None,
        last_expected_ms=last_expected if expected_times else None,
        first_candle_ms=min(actual_open_times) if actual_open_times else None,
        last_candle_ms=max(actual_open_times) if actual_open_times else None,
        expected_count=expected_count,
        actual_count=actual_count,
        missing_count=missing_count,
        leading_missing_count=leading_missing,
        internal_missing_count=internal_missing,
        trailing_missing_count=trailing_missing,
        missing_open_times_ms=missing,
        completeness_pct=completeness,
    )
