from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEventKind
from crypto_bot.strategy.mtf_sfp import MtfSfpReport


@dataclass(frozen=True)
class BosInventory:
    bullish_structure_broken_bos: int
    bearish_structure_broken_bos: int


@dataclass(frozen=True)
class CandidateBosDiagnostic:
    candidate_id: int
    sfp_time: datetime
    direction: str
    candidate_status: str
    invalidation_time: datetime | None
    first_expected_bos_after_sfp: datetime | None
    first_opposite_bos_after_sfp: datetime | None
    expected_bos_exists_after_sfp: bool
    expected_bos_before_invalidation: bool


def ltf_bos_inventory(report: MarketAnalysisReport) -> BosInventory:
    return BosInventory(
        bullish_structure_broken_bos=sum(
            e.kind == MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS for e in report.events
        ),
        bearish_structure_broken_bos=sum(
            e.kind == MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS for e in report.events
        ),
    )


def build_candidate_bos_diagnostics(
    mtf_report: MtfSfpReport,
    ltf_report: MarketAnalysisReport,
) -> tuple[CandidateBosDiagnostic, ...]:
    """Explain zero/low confirmation counts without changing strategy logic.

    This diagnostic deliberately looks at later LTF BOS events even when a candidate was
    invalidated or expired. It is an audit aid only: those later events do not retroactively
    validate the candidate and are never used by the trading state machine.
    """
    bos_events = sorted(
        (
            e
            for e in ltf_report.events
            if e.kind
            in {
                MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
                MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
            }
        ),
        key=lambda e: (e.event_time, e.candle_index, e.kind.value, e.level_id),
    )

    rows: list[CandidateBosDiagnostic] = []
    for c in mtf_report.candidates:
        expected = next(
            (
                e
                for e in bos_events
                if e.event_time > c.htf_sfp_event_time and e.kind == c.expected_ltf_bos_kind
            ),
            None,
        )
        opposite = next(
            (
                e
                for e in bos_events
                if e.event_time > c.htf_sfp_event_time and e.kind != c.expected_ltf_bos_kind
            ),
            None,
        )
        rows.append(
            CandidateBosDiagnostic(
                candidate_id=c.candidate_id,
                sfp_time=c.htf_sfp_event_time,
                direction=c.expected_direction.value,
                candidate_status=c.status.value,
                invalidation_time=c.sfp_invalidation_event_time,
                first_expected_bos_after_sfp=expected.event_time if expected else None,
                first_opposite_bos_after_sfp=opposite.event_time if opposite else None,
                expected_bos_exists_after_sfp=expected is not None,
                expected_bos_before_invalidation=(
                    expected is not None
                    and (
                        c.sfp_invalidation_event_time is None
                        or expected.event_time < c.sfp_invalidation_event_time
                    )
                ),
            )
        )
    return tuple(rows)
