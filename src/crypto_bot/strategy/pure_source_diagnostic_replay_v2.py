"""Stage 15: deterministic PURE SOURCE diagnostic replay artifacts.

This module does not add SOURCE rules or execution permission.  It summarizes
Stage-14 causal replay output into a reproducible audit artifact and verifies
that a repeated replay produces the exact same causal receipts.  Missing SOURCE
inputs remain explicit blockers; no entry quote, ATR, FTA, exit allocation,
PROJECT policy, PnL simulation or order execution is introduced here.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256

from crypto_bot.strategy.pure_source_execution_provider_v2 import (
    ExecutionReplayEvidenceBatch,
    run_source_execution_replay,
)
from crypto_bot.strategy.pure_source_replay_v2 import ReplaySeries, _hash_payload
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


DIAGNOSTIC_REPLAY_VERSION = "PURE_SOURCE_STAGE15_DIAGNOSTIC_REPLAY_V2"
BASELINE_IDENTIFIABILITY = "NOT_IDENTIFIABLE"


@dataclass(frozen=True)
class DiagnosticReasonCount:
    layer: str
    status: str
    reason: str
    observation_count: int


@dataclass(frozen=True)
class SourceDiagnosticArtifact:
    version: str
    replay_version: str
    provider_id: str
    provider_version: str
    dataset_sha256: str
    first_decision_at: datetime
    last_decision_at: datetime
    receipt_count: int
    evidence_batch_count: int
    receipt_chain_sha256: str
    evidence_chain_sha256: str
    final_runtime_sha256: str
    causal_object_count: int
    setup_count: int
    execution_plan_count: int
    source_ready_setup_count: int
    execution_ready_observation_count: int
    unresolved: tuple[DiagnosticReasonCount, ...]
    baseline_identifiability: str
    trade_entry_allowed: bool
    financial_run: bool
    artifact_sha256: str


@dataclass(frozen=True)
class DiagnosticResumeVerification:
    verified: bool
    reason: str
    existing_artifact_sha256: str
    repeated_artifact_sha256: str | None = None


def _chain_hash(parts: Sequence[str]) -> str:
    payload = "\n".join(parts).encode("utf-8")
    return sha256(payload).hexdigest()


def _reason_counts(
    batches: Sequence[ExecutionReplayEvidenceBatch],
) -> tuple[DiagnosticReasonCount, ...]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for batch in batches:
        for row in batch.object_assessments:
            if row.status != EvidenceStatus.PASS:
                counts[("OBJECT", row.status.value, row.reason)] += 1
        for row in batch.setup_observations:
            if row.status != EvidenceStatus.PASS:
                counts[("SETUP", row.status.value, row.reason)] += 1
        for row in batch.execution_observations:
            if row.status != EvidenceStatus.PASS or row.unresolved:
                # A Stage-14 PASS can still be non-executable by design.  Count
                # every explicit unresolved reason instead of relabelling PASS.
                if row.unresolved:
                    for reason in row.unresolved:
                        counts[("EXECUTION", row.status.value, reason)] += 1
                elif row.status != EvidenceStatus.PASS:
                    counts[("EXECUTION", row.status.value, row.reason)] += 1
    return tuple(
        DiagnosticReasonCount(layer, status, reason, count)
        for (layer, status, reason), count in sorted(counts.items())
    )


def _artifact_hash(artifact: SourceDiagnosticArtifact) -> str:
    return _hash_payload(replace(artifact, artifact_sha256=""))


def verify_source_diagnostic_artifact(artifact: SourceDiagnosticArtifact) -> bool:
    """Verify the artifact's self-fingerprint without changing runtime state."""

    return bool(artifact.artifact_sha256) and artifact.artifact_sha256 == _artifact_hash(
        artifact
    )


def build_source_diagnostic_artifact(
    series: Sequence[ReplaySeries], *, through: datetime | None = None
) -> SourceDiagnosticArtifact:
    """Run Stage 14 end-to-end and freeze only diagnostic/audit facts.

    The result is intentionally not a trade ledger and contains no financial
    outcome.  It fails closed if any upstream runtime ever exposes live entry
    permission.
    """

    run = run_source_execution_replay(series, through=through)
    replay = run.replay
    batches = tuple(run.evidence_batches)
    receipts = replay.receipts
    if not receipts:
        raise ValueError("diagnostic replay requires at least one receipt")
    if len(receipts) != len(batches):
        raise ValueError("replay receipts and evidence batches must remain aligned")

    summary = replay.runtime_summary
    trade_entry_allowed = bool(summary["trade_entry_allowed"])
    if trade_entry_allowed:
        raise ValueError("PURE SOURCE diagnostic replay must fail closed")

    receipt_chain = _chain_hash(
        tuple(
            "|".join(
                (
                    row.decision_at.isoformat(),
                    row.prefix_sha256,
                    row.evidence_batch_sha256,
                    row.runtime_sha256,
                )
            )
            for row in receipts
        )
    )
    evidence_chain = _chain_hash(tuple(_hash_payload(batch) for batch in batches))
    execution_ready_observations = sum(
        1
        for batch in batches
        for row in batch.execution_observations
        if row.execution_ready
    )

    artifact = SourceDiagnosticArtifact(
        version=DIAGNOSTIC_REPLAY_VERSION,
        replay_version=replay.version,
        provider_id=replay.provider_id,
        provider_version=replay.provider_version,
        dataset_sha256=replay.manifest.dataset_sha256,
        first_decision_at=receipts[0].decision_at,
        last_decision_at=receipts[-1].decision_at,
        receipt_count=len(receipts),
        evidence_batch_count=len(batches),
        receipt_chain_sha256=receipt_chain,
        evidence_chain_sha256=evidence_chain,
        final_runtime_sha256=receipts[-1].runtime_sha256,
        causal_object_count=int(summary["causal_object_count"]),
        setup_count=int(summary["setup_count"]),
        execution_plan_count=int(summary["execution_plan_count"]),
        source_ready_setup_count=len(tuple(summary["source_ready_setup_ids"])),
        execution_ready_observation_count=execution_ready_observations,
        unresolved=_reason_counts(batches),
        baseline_identifiability=BASELINE_IDENTIFIABILITY,
        trade_entry_allowed=False,
        financial_run=False,
        artifact_sha256="",
    )
    return replace(artifact, artifact_sha256=_artifact_hash(artifact))


def verify_source_diagnostic_resume(
    existing: SourceDiagnosticArtifact,
    series: Sequence[ReplaySeries],
    *,
    through: datetime | None = None,
) -> DiagnosticResumeVerification:
    """Verify an existing artifact against a fresh exact causal replay.

    This is verification, not runtime-state hydration: Stage 15 deliberately
    does not skip computation or deserialize a mutable strategy runtime.  A true
    incremental checkpoint would require a separately audited state contract.
    """

    if not verify_source_diagnostic_artifact(existing):
        return DiagnosticResumeVerification(
            False, "EXISTING_ARTIFACT_FINGERPRINT_MISMATCH", existing.artifact_sha256
        )

    repeated = build_source_diagnostic_artifact(series, through=through)
    if existing.version != repeated.version:
        reason = "DIAGNOSTIC_VERSION_MISMATCH"
    elif existing.replay_version != repeated.replay_version:
        reason = "REPLAY_VERSION_MISMATCH"
    elif existing.provider_id != repeated.provider_id:
        reason = "PROVIDER_ID_MISMATCH"
    elif existing.provider_version != repeated.provider_version:
        reason = "PROVIDER_VERSION_MISMATCH"
    elif existing.dataset_sha256 != repeated.dataset_sha256:
        reason = "DATASET_SHA256_MISMATCH"
    elif existing.receipt_count != repeated.receipt_count:
        reason = "RECEIPT_COUNT_MISMATCH"
    elif existing.receipt_chain_sha256 != repeated.receipt_chain_sha256:
        reason = "RECEIPT_CHAIN_MISMATCH"
    elif existing.evidence_chain_sha256 != repeated.evidence_chain_sha256:
        reason = "EVIDENCE_CHAIN_MISMATCH"
    elif existing.final_runtime_sha256 != repeated.final_runtime_sha256:
        reason = "FINAL_RUNTIME_MISMATCH"
    elif existing.artifact_sha256 != repeated.artifact_sha256:
        reason = "ARTIFACT_SHA256_MISMATCH"
    else:
        return DiagnosticResumeVerification(
            True,
            "EXACT_DIAGNOSTIC_REPLAY_MATCH",
            existing.artifact_sha256,
            repeated.artifact_sha256,
        )
    return DiagnosticResumeVerification(
        False, reason, existing.artifact_sha256, repeated.artifact_sha256
    )
