"""Stage 12: causal MTF evidence composition, without a context-selection policy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime, timedelta

from crypto_bot.strategy.causal_objects import require_closed_candles
from crypto_bot.strategy.pure_source_object_provider_v2 import (
    ObjectReplayEvidenceBatch,
    SourceObjectReplayRun,
    build_source_object_batch,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    PrefixSeries,
    ReplayFrame,
    ReplaySeries,
    run_pure_source_replay,
)
from crypto_bot.strategy.source_setup_v2 import LowerTimeframePair
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

MTF_PROVIDER_VERSION = "PURE_SOURCE_STAGE12_MTF_V2"


@dataclass(frozen=True)
class TimeframeView:
    timeframe: str
    interval_ms: int
    known_through: datetime | None
    object_ids: tuple[str, ...]


@dataclass(frozen=True)
class RefinementCandidate:
    context_timeframe: str
    refinement_timeframe: str
    pair: LowerTimeframePair


@dataclass(frozen=True)
class MtfPriceAudit:
    lower_timeframe: str
    higher_timeframe: str
    status: EvidenceStatus
    complete_tiles: int
    incomplete_tiles: int
    reason: str


@dataclass(frozen=True)
class MtfReplayEvidenceBatch(ObjectReplayEvidenceBatch):
    timeframe_views: tuple[TimeframeView, ...] = ()
    refinement_candidates: tuple[RefinementCandidate, ...] = ()
    mtf_price_audits: tuple[MtfPriceAudit, ...] = ()


class MtfSourceReplayProvider:
    provider_id = "PURE_SOURCE_MTF_OBJECTS"
    provider_version = MTF_PROVIDER_VERSION

    def produce(self, frame: ReplayFrame) -> MtfReplayEvidenceBatch:
        return compose_mtf_source_evidence(frame)


def compose_mtf_source_evidence(frame: ReplayFrame) -> MtfReplayEvidenceBatch:
    """Preserve every declared lower-TF alternative; select no SOURCE context.

    A duration relationship is a candidate only. Its presence does not assert
    context validity, branch validity, entry permission or an HTF direction.
    OHLC consistency is a data-quality check, never a trading admission rule.
    """
    seen_durations: set[int] = set()
    ordered = tuple(sorted(frame.series, key=lambda s: (s.interval_ms, s.timeframe)))
    for prefix in ordered:
        require_closed_candles(prefix.candles, decision_at=frame.decision_at)
        if prefix.interval_ms <= 0 or prefix.interval_ms % 60_000:
            raise ValueError(
                "MTF composition requires positive fixed whole-minute intervals"
            )
        if prefix.interval_ms in seen_durations:
            raise ValueError(
                "duplicate physical timeframe duration; normalize aliases before replay"
            )
        if any(
            c.close_time - c.open_time != timedelta(milliseconds=prefix.interval_ms)
            for c in prefix.candles
        ):
            raise ValueError("MTF candle duration does not match declared interval")
        seen_durations.add(prefix.interval_ms)
    audits = tuple(
        _audit_prices(lower, higher)
        for higher in ordered
        for lower in ordered
        if lower.interval_ms < higher.interval_ms
    )
    base = build_source_object_batch(frame)
    views = tuple(
        TimeframeView(
            prefix.timeframe,
            prefix.interval_ms,
            prefix.candles[-1].close_time if prefix.candles else None,
            tuple(
                obj.object_id
                for obj in base.objects
                if obj.timeframe == prefix.timeframe
            ),
        )
        for prefix in ordered
    )
    refinements = tuple(
        RefinementCandidate(
            higher.timeframe,
            lower.timeframe,
            LowerTimeframePair(
                higher.interval_ms // 60_000, lower.interval_ms // 60_000
            ),
        )
        for higher in ordered
        for lower in ordered
        if lower.interval_ms < higher.interval_ms and lower.candles and higher.candles
    )
    return MtfReplayEvidenceBatch(
        **{field.name: getattr(base, field.name) for field in fields(base)},
        timeframe_views=views,
        refinement_candidates=refinements,
        mtf_price_audits=audits,
    )


def _audit_prices(lower: PrefixSeries, higher: PrefixSeries) -> MtfPriceAudit:
    """Compare exact OHLC only when complete fixed-grid tiling is observable.

    Missing coverage or nonintegral grids are UNKNOWN, not evidence of price
    agreement. Volume/session reconstruction is outside this OHLC audit.
    """
    if higher.interval_ms % lower.interval_ms:
        return MtfPriceAudit(
            lower.timeframe,
            higher.timeframe,
            EvidenceStatus.UNKNOWN,
            0,
            len(higher.candles),
            "NONINTEGRAL_FIXED_GRID",
        )
    by_open = {candle.open_time: candle for candle in lower.candles}
    complete = incomplete = 0
    count = higher.interval_ms // lower.interval_ms
    for candle in higher.candles:
        if count > len(by_open):
            incomplete += 1
            continue
        starts = tuple(
            candle.open_time + timedelta(milliseconds=index * lower.interval_ms)
            for index in range(count)
        )
        if any(start not in by_open for start in starts):
            incomplete += 1
            continue
        pieces = tuple(by_open[start] for start in starts)
        if any(piece.close_time > candle.close_time for piece in pieces):
            raise ValueError("MTF lower candle extends beyond higher candle")
        actual = (
            pieces[0].open,
            max(c.high for c in pieces),
            min(c.low for c in pieces),
            pieces[-1].close,
        )
        expected = (candle.open, candle.high, candle.low, candle.close)
        if actual != expected:
            raise ValueError(
                f"MTF OHLC mismatch: {lower.timeframe}->{higher.timeframe} at {candle.open_time.isoformat()}"
            )
        complete += 1
    status = (
        EvidenceStatus.PASS if complete and not incomplete else EvidenceStatus.UNKNOWN
    )
    reason = (
        "COMPLETE_CLOSED_OHLC_TILES_MATCH"
        if status == EvidenceStatus.PASS
        else "INCOMPLETE_VISIBLE_LOWER_COVERAGE"
    )
    return MtfPriceAudit(
        lower.timeframe, higher.timeframe, status, complete, incomplete, reason
    )


def run_mtf_source_replay(
    series: Sequence[ReplaySeries],
    *,
    through: datetime | None = None,
) -> SourceObjectReplayRun:
    batches: list[MtfReplayEvidenceBatch] = []

    class Recorder(MtfSourceReplayProvider):
        def produce(self, frame: ReplayFrame) -> MtfReplayEvidenceBatch:
            batch = super().produce(frame)
            batches.append(batch)
            return batch

    replay = run_pure_source_replay(series, Recorder(), through=through)
    return SourceObjectReplayRun(replay, tuple(batches))
