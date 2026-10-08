from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEventKind


_BOS_KINDS = {
    MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
    MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
}


@dataclass(frozen=True)
class BosSuffixStability:
    compare_start: datetime
    full_count: int
    suffix_count: int
    exact_overlap_count: int
    full_only_count: int
    suffix_only_count: int
    exact_jaccard: float


def _signature(event) -> tuple[str, datetime, float]:
    return (event.kind.value, event.event_time, round(float(event.level_price), 12))


def compare_bos_suffix(
    full_report: MarketAnalysisReport,
    suffix_report: MarketAnalysisReport,
    *,
    compare_start: datetime,
) -> BosSuffixStability:
    """Compare BOS events on the same stabilized recent time window.

    This is QA only. Older history may legitimately affect the left edge of a suffix analysis,
    so callers should pass a compare_start after an explicit stabilization guard. The metric is
    not a trading rule and no pass threshold is hard-coded.
    """
    full = {
        _signature(event)
        for event in full_report.events
        if event.kind in _BOS_KINDS and event.event_time >= compare_start
    }
    suffix = {
        _signature(event)
        for event in suffix_report.events
        if event.kind in _BOS_KINDS and event.event_time >= compare_start
    }
    overlap = full & suffix
    union = full | suffix
    jaccard = len(overlap) / len(union) if union else 1.0
    return BosSuffixStability(
        compare_start=compare_start,
        full_count=len(full),
        suffix_count=len(suffix),
        exact_overlap_count=len(overlap),
        full_only_count=len(full - suffix),
        suffix_only_count=len(suffix - full),
        exact_jaccard=jaccard,
    )
