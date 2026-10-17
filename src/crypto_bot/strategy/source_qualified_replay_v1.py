"""Explicit annotation arrivals and bound consumers in diagnostic replay only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256

from crypto_bot.strategy.pure_source_object_provider_v2 import (
    ObjectReplayEvidenceBatch,
    build_source_object_batch,
)
from crypto_bot.strategy.pure_source_replay_v2 import (
    PureSourceReplayResult,
    ReplayFrame,
    ReplaySeries,
    _hash_payload,
    run_pure_source_replay,
)
from crypto_bot.strategy.source_claim_binding_v1 import (
    BoundSourceClaim,
    SourceClaimJournal,
)
from crypto_bot.strategy.source_qualified_liquidity_v1 import (
    QualifiedEqualLiquidityAssessment,
    assess_bound_equal_liquidity,
)
from crypto_bot.strategy.source_qualified_sfp_context_v1 import (
    QualifiedSfpContextAssessment,
    assess_bound_sfp_context,
)
from crypto_bot.strategy.source_qualitative_provenance_v2 import (
    QualitativeSemanticCatalog,
    SourceQualitativeClaim,
    validate_claim_against_catalog,
)
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    EqualLiquidityKind,
    EvidenceStatus,
)

QUALIFIED_REPLAY_VERSION = "PURE_SOURCE_STAGE23_QUALIFIED_DIAGNOSTIC_REPLAY_V1"


def _aware(at: datetime) -> None:
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("aware input schedule timestamp required")


@dataclass(frozen=True)
class AnnotationDelivery:
    observed_at: datetime
    claim: SourceQualitativeClaim
    provenance: bytes

    def __post_init__(self):
        _aware(self.observed_at)
        if not isinstance(self.claim, SourceQualitativeClaim):
            raise TypeError("typed immutable SOURCE claim required")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(UTC))
        object.__setattr__(
            self,
            "claim",
            replace(
                self.claim,
                observation_start_at=self.claim.observation_start_at.astimezone(UTC),
                observation_end_at=self.claim.observation_end_at.astimezone(UTC),
                known_at=self.claim.known_at.astimezone(UTC),
            ),
        )
        if type(self.provenance) is not bytes:
            raise TypeError("immutable witness bytes required")
        if self.observed_at < self.claim.known_at:
            raise ValueError("delivery cannot precede declared claim availability")
        if self.claim.provenance_ref != "sha256:" + sha256(self.provenance).hexdigest():
            raise ValueError("delivery witness content hash mismatch")


@dataclass(frozen=True)
class EqualPairRequest:
    requested_at: datetime
    timeframe: str
    left_swing_id: str
    right_swing_id: str
    kind: EqualLiquidityKind
    observation_start_at: datetime
    observation_end_at: datetime

    def __post_init__(self):
        _request_window(
            self.requested_at, self.observation_start_at, self.observation_end_at
        )
        _normalize_request_times(self)
        if not isinstance(self.kind, EqualLiquidityKind):
            raise TypeError("typed equal liquidity kind required")
        if any(
            not isinstance(s, str) or not s.strip()
            for s in (self.timeframe, self.left_swing_id, self.right_swing_id)
        ):
            raise ValueError("explicit pair identity required")


@dataclass(frozen=True)
class SfpContextRequest:
    requested_at: datetime
    sfp_object_id: str
    observation_start_at: datetime
    observation_end_at: datetime

    def __post_init__(self):
        _request_window(
            self.requested_at, self.observation_start_at, self.observation_end_at
        )
        _normalize_request_times(self)
        if not isinstance(self.sfp_object_id, str) or not self.sfp_object_id.strip():
            raise ValueError("explicit SFP identity required")


def _request_window(requested, start, end):
    for at in (requested, start, end):
        _aware(at)
    if not start < end <= requested:
        raise ValueError("request window must already be closed")


def _normalize_request_times(request):
    for key in ("requested_at", "observation_start_at", "observation_end_at"):
        object.__setattr__(request, key, getattr(request, key).astimezone(UTC))


@dataclass(frozen=True)
class QualifiedDiagnosticBatch(ObjectReplayEvidenceBatch):
    # Future schedule identities deliberately do not enter per-step evidence.
    annotation_receipts: tuple[BoundSourceClaim, ...] = ()
    equal_pair_requests: tuple[EqualPairRequest, ...] = ()
    equal_liquidity: tuple[QualifiedEqualLiquidityAssessment, ...] = ()
    sfp_context_requests: tuple[SfpContextRequest, ...] = ()
    sfp_contexts: tuple[QualifiedSfpContextAssessment, ...] = ()


@dataclass(frozen=True)
class QualifiedDiagnosticRun:
    replay: PureSourceReplayResult
    batches: tuple[QualifiedDiagnosticBatch, ...]
    annotation_input_sha256: str


class QualifiedDiagnosticProvider:
    """Single-use monotonic replay session; malformed input poisons the session.

    Future arrivals/requests remain private input until their scheduled frame.
    Their full input hash is run metadata, never a prefix decision dependency.
    No annotations, candidate requests or branch winners are generated here.
    """

    provider_id = "PURE_SOURCE_QUALIFIED_DIAGNOSTICS"
    provider_version = QUALIFIED_REPLAY_VERSION

    def __init__(
        self,
        catalog: QualitativeSemanticCatalog,
        *,
        exchange: str,
        symbol: str,
        deliveries: tuple[AnnotationDelivery, ...] = (),
        requests: tuple[EqualPairRequest | SfpContextRequest, ...] = (),
    ):
        if (
            catalog.trade_entry_allowed is not False
            or catalog.financial_backtest_allowed is not False
            or catalog.numeric_proxy_inference_allowed is not False
            or catalog.project_policy_applied
            or catalog.classification != "TECHNICAL_NORMALIZATION"
        ):
            raise ValueError("qualified replay requires fail-closed SOURCE catalog")
        if type(deliveries) is not tuple or type(requests) is not tuple:
            raise TypeError("immutable delivery/request schedules required")
        if any(not isinstance(d, AnnotationDelivery) for d in deliveries) or any(
            not isinstance(r, (EqualPairRequest, SfpContextRequest)) for r in requests
        ):
            raise TypeError("unsupported annotation delivery or consumer request")
        for delivery in deliveries:
            validate_claim_against_catalog(delivery.claim, catalog)
            if delivery.claim.status == EvidenceStatus.UNKNOWN:
                raise ValueError("UNKNOWN is not an audited delivered annotation")
            if delivery.claim.symbol != symbol:
                raise ValueError("delivery market identity mismatch")
        keys = tuple(_hash_payload(r) for r in requests)
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate consumer request")
        self._deliveries = tuple(
            sorted(deliveries, key=lambda d: (d.observed_at, d.claim.evidence_id))
        )
        self._requests = tuple(sorted(requests, key=_hash_payload))
        self._journal = SourceClaimJournal(catalog, exchange=exchange, symbol=symbol)
        self._next_delivery = 0
        self._last_at = None
        self._failed = False
        self._batches = []
        self._annotation_input_sha256 = _hash_payload(
            {
                "version": self.provider_version,
                "exchange": exchange,
                "symbol": symbol,
                "catalog": catalog,
                "deliveries": tuple(
                    (d.observed_at, d.claim, sha256(d.provenance).hexdigest())
                    for d in self._deliveries
                ),
                "requests": self._requests,
            }
        )

    @property
    def annotation_input_sha256(self) -> str:
        return self._annotation_input_sha256

    @property
    def batches(self) -> tuple[QualifiedDiagnosticBatch, ...]:
        return tuple(self._batches)

    def produce(self, frame: ReplayFrame) -> QualifiedDiagnosticBatch:
        if self._failed:
            raise ValueError("failed replay session cannot be reused")
        try:
            if self._last_at is not None and frame.decision_at <= self._last_at:
                raise ValueError(
                    "qualified replay clock must advance; use a fresh session for repeat"
                )
            self._journal.observe_frame(frame)
            base = build_source_object_batch(frame)
            while self._next_delivery < len(self._deliveries):
                delivery = self._deliveries[self._next_delivery]
                if delivery.observed_at > frame.decision_at:
                    break
                self._journal.ingest(
                    delivery.claim,
                    frame=frame,
                    objects=base.objects,
                    provenance=delivery.provenance,
                )
                self._next_delivery += 1
            pair_requests = tuple(
                r
                for r in self._requests
                if isinstance(r, EqualPairRequest)
                and r.requested_at <= frame.decision_at
            )
            sfp_requests = tuple(
                r
                for r in self._requests
                if isinstance(r, SfpContextRequest)
                and r.requested_at <= frame.decision_at
            )
            pairs = tuple(
                assess_bound_equal_liquidity(
                    self._journal,
                    frame,
                    timeframe=r.timeframe,
                    left_swing_id=r.left_swing_id,
                    right_swing_id=r.right_swing_id,
                    kind=r.kind,
                    observation_start_at=r.observation_start_at,
                    observation_end_at=r.observation_end_at,
                )
                for r in pair_requests
            )
            contexts = tuple(
                assess_bound_sfp_context(
                    self._journal,
                    frame,
                    sfp_object_id=r.sfp_object_id,
                    observation_start_at=r.observation_start_at,
                    observation_end_at=r.observation_end_at,
                )
                for r in sfp_requests
            )
            result = QualifiedDiagnosticBatch(
                objects=base.objects,
                object_assessments=base.object_assessments,
                sfps=base.sfps,
                imbalances=base.imbalances,
                annotation_receipts=self._journal.records,
                equal_pair_requests=pair_requests,
                equal_liquidity=pairs,
                sfp_context_requests=sfp_requests,
                sfp_contexts=contexts,
            )
            self._batches.append(result)
            self._last_at = frame.decision_at
            return result
        except Exception:
            # Per-claim ingestion is atomic, but a frame can contain many inputs.
            # No incomplete frame is emitted or accepted for further session use.
            self._failed = True
            raise


def run_qualified_diagnostic_replay(
    series: Sequence[ReplaySeries],
    catalog: QualitativeSemanticCatalog,
    *,
    deliveries: tuple[AnnotationDelivery, ...] = (),
    requests: tuple[EqualPairRequest | SfpContextRequest, ...] = (),
    through: datetime | None = None,
) -> QualifiedDiagnosticRun:
    if not series or not series[0].candles:
        raise ValueError("nonempty replay dataset required")
    first = series[0].candles[0]
    provider = QualifiedDiagnosticProvider(
        catalog,
        exchange=first.exchange,
        symbol=first.symbol,
        deliveries=deliveries,
        requests=requests,
    )
    replay = run_pure_source_replay(series, provider, through=through)
    return QualifiedDiagnosticRun(
        replay, provider.batches, provider.annotation_input_sha256
    )
