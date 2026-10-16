from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol, Sequence

from crypto_bot.common.models import Candle
from crypto_bot.data.models import MarketCandle
from crypto_bot.data.qa import DataQualityReport, audit_klines
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.pure_source_evidence_v2 import build_structure_liquidity_snapshot
from crypto_bot.strategy.pure_source_runtime import PureSourceRuntime
from crypto_bot.strategy.source_execution_v2 import ExecutionPlanAssessment
from crypto_bot.strategy.source_setup_v2 import SetupAssemblyAssessment


REPLAY_VERSION = "PURE_SOURCE_STAGE10_REPLAY_V2"


@dataclass(frozen=True)
class ReplaySeries:
    """One immutable, already-downloaded market-data series.

    ``interval_ms`` is an infrastructure fact used for timestamp/continuity QA.
    ``timeframe`` is carried into SOURCE object provenance; Stage 10 does not
    invent a universal HTF/LTF ladder.
    """

    timeframe: str | int
    interval_ms: int
    candles: tuple[MarketCandle, ...]

    def __post_init__(self) -> None:
        if self.interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        if not self.candles:
            raise ValueError("replay series cannot be empty")
        market_interval_ms = _parse_fixed_interval_ms(self.candles[0].interval)
        if market_interval_ms is not None and market_interval_ms != self.interval_ms:
            raise ValueError("MarketCandle interval does not match replay interval_ms")
        timeframe_interval_ms = _parse_fixed_interval_ms(str(self.timeframe))
        if timeframe_interval_ms is not None and timeframe_interval_ms != self.interval_ms:
            raise ValueError("replay timeframe label does not match interval_ms")


@dataclass(frozen=True)
class ReplaySeriesManifest:
    timeframe: str
    interval_ms: int
    candle_count: int
    first_open_time_ms: int
    last_open_time_ms: int
    series_sha256: str


@dataclass(frozen=True)
class ReplayDatasetManifest:
    version: str
    exchange: str
    symbol: str
    series: tuple[ReplaySeriesManifest, ...]
    dataset_sha256: str
    total_candles: int


@dataclass(frozen=True)
class PrefixSeries:
    timeframe: str
    interval_ms: int
    candles: tuple[Candle, ...]
    newly_closed: tuple[Candle, ...]


@dataclass(frozen=True)
class ReplayFrame:
    """The only market-data view an evidence provider receives.

    No full-dataset hash, total future row count or future candle is exposed.
    All ``candles`` close at or before ``decision_at``.
    """

    exchange: str
    symbol: str
    decision_at: datetime
    series: tuple[PrefixSeries, ...]
    prefix_sha256: str

    def series_for(self, timeframe: str | int) -> PrefixSeries:
        key = str(timeframe)
        for item in self.series:
            if item.timeframe == key:
                return item
        raise KeyError(key)


@dataclass(frozen=True)
class ReplayExecutionAssessment:
    assessment: ExecutionPlanAssessment
    setup_id: str | None = None


@dataclass(frozen=True)
class ReplayEvidenceBatch:
    """Stage-2..8 evidence emitted from one closed-prefix decision point."""

    objects: tuple[CausalSourceObject, ...] = ()
    setup_assessments: tuple[SetupAssemblyAssessment, ...] = ()
    execution_assessments: tuple[ReplayExecutionAssessment, ...] = ()


class PureSourceEvidenceProvider(Protocol):
    provider_id: str

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        ...


@dataclass(frozen=True)
class ReplayStepReceipt:
    decision_at: datetime
    prefix_sizes: tuple[tuple[str, int], ...]
    prefix_sha256: str
    evidence_batch_sha256: str
    runtime_sha256: str
    causal_object_count: int
    setup_count: int
    execution_plan_count: int
    blocker_count: int


@dataclass(frozen=True)
class PureSourceReplayResult:
    version: str
    provider_id: str
    manifest: ReplayDatasetManifest
    receipts: tuple[ReplayStepReceipt, ...]
    runtime_summary: Mapping[str, Any]


@dataclass(frozen=True)
class PrefixReplayComparison:
    equal: bool
    compared_steps: int
    through: datetime
    mismatch_at: datetime | None = None
    reason: str | None = None


@dataclass(frozen=True)
class _PreparedSeries:
    timeframe: str
    interval_ms: int
    market: tuple[MarketCandle, ...]
    strategy: tuple[Candle, ...]
    qa: DataQualityReport
    prefix_hashes: tuple[str, ...]


class StructureLiquidityReplayProvider:
    """Concrete clean Stage-2 provider used to prove the transport path.

    Stage 10 deliberately does not fabricate the qualitative evidence needed by
    later SOURCE stages. Additional Stage-3..8 providers can emit their already-
    causal assessments through the same ``ReplayEvidenceBatch`` contract.
    """

    provider_id = "PURE_SOURCE_STAGE2_STRUCTURE_LIQUIDITY_V2"

    def produce(self, frame: ReplayFrame) -> ReplayEvidenceBatch:
        objects: dict[str, CausalSourceObject] = {}
        for prefix in frame.series:
            snapshot = build_structure_liquidity_snapshot(
                prefix.candles,
                symbol=frame.symbol,
                timeframe=prefix.timeframe,
            )
            for swing in snapshot.swings:
                objects[swing.obj.object_id] = swing.obj
            for pool in snapshot.liquidity:
                objects[pool.obj.object_id] = pool.obj
            if snapshot.structure_object is not None:
                objects[snapshot.structure_object.object_id] = snapshot.structure_object
        return ReplayEvidenceBatch(objects=tuple(objects[key] for key in sorted(objects)))


def run_pure_source_replay(
    series: Sequence[ReplaySeries],
    provider: PureSourceEvidenceProvider,
    *,
    through: datetime | None = None,
) -> PureSourceReplayResult:
    """Replay healthy market data into the clean Stage-9 runtime causally.

    Same-close candles from multiple timeframes become visible together before
    the provider is invoked. The provider receives only prefixes ending at the
    current decision timestamp. Market objects are topologically registered
    before Stage-7 setup assessments, which are registered before Stage-8
    execution assessments.
    """

    provider_id = str(getattr(provider, "provider_id", "")).strip()
    if not provider_id:
        raise ValueError("evidence provider requires non-empty provider_id")
    if through is not None:
        _aware("through", through)

    prepared, manifest = _prepare_dataset(series)
    runtime = PureSourceRuntime(manifest.symbol)
    decision_times = sorted(
        {
            candle.close_time
            for item in prepared
            for candle in item.strategy
            if through is None or candle.close_time <= through
        }
    )
    if not decision_times:
        raise ValueError("replay cutoff leaves no closed candles")

    positions = [0 for _ in prepared]
    receipts: list[ReplayStepReceipt] = []

    for decision_at in decision_times:
        frame_series: list[PrefixSeries] = []
        for index, item in enumerate(prepared):
            old_position = positions[index]
            position = old_position
            while position < len(item.strategy) and item.strategy[position].close_time <= decision_at:
                position += 1
            positions[index] = position
            newly_closed = item.strategy[old_position:position]
            if newly_closed:
                # Validate each timeframe independently. Cross-TF candles can share
                # one close timestamp and therefore must not be concatenated into
                # a single strict-chronology sequence.
                runtime.observe_candles(newly_closed, decision_at=decision_at)
            frame_series.append(
                PrefixSeries(
                    timeframe=item.timeframe,
                    interval_ms=item.interval_ms,
                    candles=item.strategy[:position],
                    newly_closed=newly_closed,
                )
            )

        prefix_hash = _combined_prefix_hash(prepared, positions)
        frame = ReplayFrame(
            exchange=manifest.exchange,
            symbol=manifest.symbol,
            decision_at=decision_at,
            series=tuple(frame_series),
            prefix_sha256=prefix_hash,
        )
        _validate_frame(frame)
        batch = provider.produce(frame)
        if not isinstance(batch, ReplayEvidenceBatch):
            raise TypeError("provider must return ReplayEvidenceBatch")
        batch_hash = _hash_payload(batch)
        _apply_batch(runtime, batch, decision_at=decision_at)
        summary = runtime.finish()
        receipts.append(
            ReplayStepReceipt(
                decision_at=decision_at,
                prefix_sizes=tuple((item.timeframe, len(item.candles)) for item in frame.series),
                prefix_sha256=prefix_hash,
                evidence_batch_sha256=batch_hash,
                runtime_sha256=_runtime_fingerprint(runtime, decision_at),
                causal_object_count=int(summary["causal_object_count"]),
                setup_count=int(summary["setup_count"]),
                execution_plan_count=int(summary["execution_plan_count"]),
                blocker_count=len(summary["runtime_blockers"]),
            )
        )

    return PureSourceReplayResult(
        version=REPLAY_VERSION,
        provider_id=provider_id,
        manifest=manifest,
        receipts=tuple(receipts),
        runtime_summary=runtime.finish(),
    )


def compare_replay_prefixes(
    left: PureSourceReplayResult,
    right: PureSourceReplayResult,
    *,
    through: datetime,
) -> PrefixReplayComparison:
    """Compare causal receipts while intentionally ignoring future manifest data."""

    _aware("through", through)
    if left.version != right.version:
        return PrefixReplayComparison(False, 0, through, reason="REPLAY_VERSION_MISMATCH")
    if left.provider_id != right.provider_id:
        return PrefixReplayComparison(False, 0, through, reason="PROVIDER_ID_MISMATCH")
    if (left.manifest.exchange, left.manifest.symbol) != (right.manifest.exchange, right.manifest.symbol):
        return PrefixReplayComparison(False, 0, through, reason="DATASET_IDENTITY_MISMATCH")

    left_rows = tuple(row for row in left.receipts if row.decision_at <= through)
    right_rows = tuple(row for row in right.receipts if row.decision_at <= through)
    if len(left_rows) != len(right_rows):
        return PrefixReplayComparison(
            False,
            min(len(left_rows), len(right_rows)),
            through,
            reason="PREFIX_DECISION_COUNT_MISMATCH",
        )
    for index, (lhs, rhs) in enumerate(zip(left_rows, right_rows)):
        if lhs.decision_at != rhs.decision_at:
            return PrefixReplayComparison(
                False,
                index,
                through,
                mismatch_at=min(lhs.decision_at, rhs.decision_at),
                reason="PREFIX_DECISION_TIME_MISMATCH",
            )
        if lhs.prefix_sizes != rhs.prefix_sizes:
            return PrefixReplayComparison(
                False,
                index,
                through,
                mismatch_at=lhs.decision_at,
                reason="PREFIX_SIZE_MISMATCH",
            )
        if lhs.prefix_sha256 != rhs.prefix_sha256:
            return PrefixReplayComparison(
                False,
                index,
                through,
                mismatch_at=lhs.decision_at,
                reason="PREFIX_DATA_MUTATED",
            )
        if lhs.evidence_batch_sha256 != rhs.evidence_batch_sha256:
            return PrefixReplayComparison(
                False,
                index,
                through,
                mismatch_at=lhs.decision_at,
                reason="EVIDENCE_PREFIX_MUTATED",
            )
        if lhs.runtime_sha256 != rhs.runtime_sha256:
            return PrefixReplayComparison(
                False,
                index,
                through,
                mismatch_at=lhs.decision_at,
                reason="RUNTIME_PREFIX_MUTATED",
            )
    return PrefixReplayComparison(True, len(left_rows), through)


def _prepare_dataset(
    series: Sequence[ReplaySeries],
) -> tuple[tuple[_PreparedSeries, ...], ReplayDatasetManifest]:
    if not series:
        raise ValueError("at least one replay series is required")

    prepared: list[_PreparedSeries] = []
    timeframe_keys: set[str] = set()
    exchange: str | None = None
    symbol: str | None = None

    for spec in sorted(series, key=lambda item: (item.interval_ms, str(item.timeframe))):
        timeframe = str(spec.timeframe)
        if timeframe in timeframe_keys:
            raise ValueError(f"duplicate replay timeframe: {timeframe}")
        timeframe_keys.add(timeframe)

        qa = audit_klines(spec.candles, spec.interval_ms)
        if not qa.is_healthy:
            first = qa.issues[0]
            raise ValueError(f"unhealthy replay data {timeframe}: {first.kind.value}: {first.detail}")

        first_market = spec.candles[0]
        market_interval_ms = _parse_fixed_interval_ms(first_market.interval)
        if market_interval_ms is not None and market_interval_ms != spec.interval_ms:
            raise ValueError(f"market interval mismatch for replay timeframe {timeframe}")
        timeframe_interval_ms = _parse_fixed_interval_ms(timeframe)
        if timeframe_interval_ms is not None and timeframe_interval_ms != spec.interval_ms:
            raise ValueError(f"timeframe label mismatch for replay timeframe {timeframe}")

        if exchange is None:
            exchange = first_market.exchange
            symbol = first_market.symbol
        elif first_market.exchange != exchange or first_market.symbol != symbol:
            raise ValueError("all replay series must share exchange and symbol")

        strategy = tuple(candle.to_strategy_candle(spec.interval_ms) for candle in spec.candles)
        prefix_hashes = _series_prefix_hashes(timeframe, spec.interval_ms, spec.candles)
        prepared.append(
            _PreparedSeries(
                timeframe=timeframe,
                interval_ms=spec.interval_ms,
                market=spec.candles,
                strategy=strategy,
                qa=qa,
                prefix_hashes=prefix_hashes,
            )
        )

    assert exchange is not None and symbol is not None
    series_manifests = tuple(
        ReplaySeriesManifest(
            timeframe=item.timeframe,
            interval_ms=item.interval_ms,
            candle_count=len(item.market),
            first_open_time_ms=item.market[0].open_time_ms,
            last_open_time_ms=item.market[-1].open_time_ms,
            series_sha256=item.prefix_hashes[-1],
        )
        for item in prepared
    )
    dataset_hash = _hash_payload(
        {
            "version": REPLAY_VERSION,
            "exchange": exchange,
            "symbol": symbol,
            "series": series_manifests,
        }
    )
    manifest = ReplayDatasetManifest(
        version=REPLAY_VERSION,
        exchange=exchange,
        symbol=symbol,
        series=series_manifests,
        dataset_sha256=dataset_hash,
        total_candles=sum(len(item.market) for item in prepared),
    )
    return tuple(prepared), manifest


def _series_prefix_hashes(
    timeframe: str,
    interval_ms: int,
    candles: Sequence[MarketCandle],
) -> tuple[str, ...]:
    state = sha256(
        _canonical_json(
            {
                "version": REPLAY_VERSION,
                "timeframe": timeframe,
                "interval_ms": interval_ms,
                "prefix_count": 0,
            }
        )
    ).digest()
    hashes = [state.hex()]
    for candle in candles:
        state = sha256(state + _canonical_json(candle)).digest()
        hashes.append(state.hex())
    return tuple(hashes)


def _combined_prefix_hash(prepared: Sequence[_PreparedSeries], positions: Sequence[int]) -> str:
    payload = {
        "version": REPLAY_VERSION,
        "series": tuple(
            {
                "timeframe": item.timeframe,
                "interval_ms": item.interval_ms,
                "prefix_count": position,
                "prefix_sha256": item.prefix_hashes[position],
            }
            for item, position in zip(prepared, positions)
        ),
    }
    return _hash_payload(payload)


def _validate_frame(frame: ReplayFrame) -> None:
    _aware("frame decision_at", frame.decision_at)
    previous_key: tuple[int, str] | None = None
    for item in frame.series:
        key = (item.interval_ms, item.timeframe)
        if previous_key is not None and key <= previous_key:
            raise ValueError("replay frame series order must be deterministic and unique")
        previous_key = key
        for candle in item.candles:
            if not candle.is_closed or candle.close_time > frame.decision_at:
                raise ValueError("provider frame contains unfinished/future candle")
        for candle in item.newly_closed:
            if candle.close_time != frame.decision_at:
                raise ValueError("newly_closed candle must close at frame decision_at")


def _apply_batch(runtime: PureSourceRuntime, batch: ReplayEvidenceBatch, *, decision_at: datetime) -> None:
    _register_market_objects(runtime, batch.objects, decision_at=decision_at)

    def setup_key(assessment: SetupAssemblyAssessment) -> tuple[str, str, str]:
        object_id = assessment.evidence.setup.object_id if assessment.evidence is not None else ""
        return assessment.status.value, assessment.reason, object_id

    for assessment in sorted(batch.setup_assessments, key=setup_key):
        runtime.register_setup_assessment(assessment, observed_at=decision_at)

    def execution_key(item: ReplayExecutionAssessment) -> tuple[str, str, str]:
        plan_id = item.assessment.plan.setup_id if item.assessment.plan is not None else ""
        return item.setup_id or plan_id, item.assessment.status.value, item.assessment.reason

    for item in sorted(batch.execution_assessments, key=execution_key):
        runtime.register_execution_assessment(
            item.assessment,
            observed_at=decision_at,
            setup_id=item.setup_id,
        )


def _register_market_objects(
    runtime: PureSourceRuntime,
    objects: Sequence[CausalSourceObject],
    *,
    decision_at: datetime,
) -> None:
    by_id: dict[str, CausalSourceObject] = {}
    for obj in objects:
        if obj.object_type in (SourceObjectType.SETUP, SourceObjectType.PHYSICAL_IDEA):
            raise ValueError("provider market-object batch cannot bypass Stage-7 setup wiring")
        if obj.object_id in by_id and by_id[obj.object_id] != obj:
            raise ValueError(f"provider emitted conflicting object versions in one frame: {obj.object_id}")
        by_id[obj.object_id] = obj

    pending = dict(by_id)
    while pending:
        progressed = False
        for object_id in sorted(tuple(pending)):
            obj = pending[object_id]
            if not _parents_available(runtime, obj, pending):
                continue
            runtime.register_object(obj, observed_at=decision_at)
            del pending[object_id]
            progressed = True
        if not progressed:
            unresolved = ",".join(sorted(pending))
            raise ValueError(f"unresolved/cyclic causal parentage in provider batch: {unresolved}")


def _parents_available(
    runtime: PureSourceRuntime,
    obj: CausalSourceObject,
    pending: Mapping[str, CausalSourceObject],
) -> bool:
    for parent_id in obj.parent_object_ids:
        if parent_id in pending:
            return False
        try:
            runtime.registry.get(parent_id)
        except KeyError:
            return False
    return True


def _runtime_fingerprint(runtime: PureSourceRuntime, decision_at: datetime) -> str:
    objects = runtime.registry.objects_known_by(decision_at)
    return _hash_payload(
        {
            "objects": objects,
            "summary": runtime.finish(),
        }
    )


def _hash_payload(value: Any) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        _aware("serialized datetime", value)
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported replay fingerprint value: {type(value).__name__}")


def _parse_fixed_interval_ms(value: str) -> int | None:
    text = str(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        minutes = int(text)
        return minutes * 60_000 if minutes > 0 else None
    if text == "d":
        return 86_400_000
    if text.endswith("m") and text[:-1].isdigit():
        minutes = int(text[:-1])
        return minutes * 60_000 if minutes > 0 else None
    if text.endswith("h") and text[:-1].isdigit():
        hours = int(text[:-1])
        return hours * 3_600_000 if hours > 0 else None
    if text.endswith("d") and text[:-1].isdigit():
        days = int(text[:-1])
        return days * 86_400_000 if days > 0 else None
    if text.startswith("m") and text[1:].isdigit():
        minutes = int(text[1:])
        return minutes * 60_000 if minutes > 0 else None
    if text.startswith("h") and text[1:].isdigit():
        hours = int(text[1:])
        return hours * 3_600_000 if hours > 0 else None
    if text.startswith("d") and text[1:].isdigit():
        days = int(text[1:])
        return days * 86_400_000 if days > 0 else None
    return None


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
