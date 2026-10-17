"""Causal provenance contract for qualitative PURE SOURCE evidence.

SOURCE contains terms that are intentionally not assigned numeric thresholds
(aggressive, reasonable tilt, full engulf, last movement, etc.). Stage 18 makes
such claims auditable without converting them into ATR/percent/score proxies.
This module does not create market objects, choose branches or allow trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


QUALITATIVE_PROVENANCE_VERSION = "PURE_SOURCE_STAGE18_QUALITATIVE_PROVENANCE_V2"


# Input may extend the deny list, never weaken the baseline schema contract.
REQUIRED_FORBIDDEN_FIELDS = frozenset(
    {
        "rank",
        "score",
        "confidence",
        "probability",
        "weight",
        "preferred",
        "win_rate",
        "profit_factor",
        "expectancy",
        "pnl",
        "backtest_result",
    }
)
CATALOG_FIELDS = frozenset(
    {
        "version",
        "base_stage17_head",
        "classification",
        "purpose",
        "trade_entry_allowed",
        "financial_backtest_allowed",
        "project_policy_applied",
        "numeric_proxy_inference_allowed",
        "annotation_methods",
        "semantics",
        "forbidden_fields",
    }
)
SEMANTIC_FIELDS = frozenset(
    {"semantic_id", "scope", "source_refs", "source_rule_ids", "description"}
)


class QualitativeScope(str, Enum):
    OBJECT_FORMATION = "OBJECT_FORMATION"
    TRADE_CONTEXT = "TRADE_CONTEXT"


class AnnotationMethod(str, Enum):
    HUMAN_SOURCE_ANNOTATION = "HUMAN_SOURCE_ANNOTATION"
    CURATED_SOURCE_DATASET_ANNOTATION = "CURATED_SOURCE_DATASET_ANNOTATION"


@dataclass(frozen=True)
class QualitativeSemanticDefinition:
    semantic_id: str
    scope: QualitativeScope
    source_refs: tuple[str, ...]
    source_rule_ids: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class QualitativeSemanticCatalog:
    version: str
    classification: str
    trade_entry_allowed: bool
    financial_backtest_allowed: bool
    numeric_proxy_inference_allowed: bool
    project_policy_applied: tuple[str, ...]
    annotation_methods: tuple[AnnotationMethod, ...]
    forbidden_fields: tuple[str, ...]
    semantics: tuple[QualitativeSemanticDefinition, ...]

    def semantic(self, semantic_id: str) -> QualitativeSemanticDefinition:
        matches = [row for row in self.semantics if row.semantic_id == semantic_id]
        if len(matches) != 1:
            raise KeyError(f"unknown or non-unique qualitative semantic: {semantic_id}")
        return matches[0]


@dataclass(frozen=True)
class SourceQualitativeClaim:
    semantic_id: str
    scope: QualitativeScope
    status: EvidenceStatus
    symbol: str
    timeframe: str
    observation_start_at: datetime
    observation_end_at: datetime
    known_at: datetime
    subject_object_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    source_rule_ids: tuple[str, ...]
    annotation_method: AnnotationMethod | None
    provenance_ref: str | None
    rationale_code: str | None
    evidence_id: str | None

    def __post_init__(self) -> None:
        for name in ("semantic_id", "symbol", "timeframe"):
            _audit_text(getattr(self, name), name)
        if not isinstance(self.scope, QualitativeScope) or not isinstance(self.status, EvidenceStatus):
            raise ValueError("qualitative claim requires typed scope and status")
        if self.annotation_method is not None and not isinstance(self.annotation_method, AnnotationMethod):
            raise ValueError("qualitative claim requires a typed annotation method")
        for name in ("subject_object_ids", "source_refs", "source_rule_ids"):
            values = getattr(self, name)
            if type(values) is not tuple:
                raise ValueError("qualitative identity collections must be immutable tuples")
            for value in values:
                _audit_text(value, name)
        # Subjects are unordered membership, as in the factory and assessment.
        # Event/anchor roles must be carried by separate typed contracts.
        object.__setattr__(self, "subject_object_ids", tuple(sorted(set(self.subject_object_ids))))
        for name, value in (
            ("observation_start_at", self.observation_start_at),
            ("observation_end_at", self.observation_end_at),
            ("known_at", self.known_at),
        ):
            _aware(name, value)
        if self.observation_end_at < self.observation_start_at:
            raise ValueError("qualitative observation window cannot run backwards")
        if self.known_at < self.observation_end_at:
            raise ValueError("qualitative claim cannot be known before observed data closes")
        if not self.subject_object_ids:
            raise ValueError("qualitative claim requires subject_object_ids")
        if not self.source_refs:
            raise ValueError("qualitative claim requires source_refs")

        if self.status == EvidenceStatus.UNKNOWN:
            if any(
                value is not None
                for value in (
                    self.annotation_method,
                    self.provenance_ref,
                    self.rationale_code,
                    self.evidence_id,
                )
            ):
                raise ValueError("UNKNOWN qualitative claim cannot masquerade as audited evidence")
        else:
            for name in ("provenance_ref", "rationale_code", "evidence_id"):
                _audit_text(getattr(self, name), name)
            if self.annotation_method is None:
                raise ValueError("PASS/FAIL qualitative claim requires annotation_method")
            if not self.provenance_ref or not self.rationale_code or not self.evidence_id:
                raise ValueError("PASS/FAIL qualitative claim requires auditable provenance")
            expected = source_qualitative_claim_id(
                semantic_id=self.semantic_id,
                scope=self.scope,
                status=self.status,
                symbol=self.symbol,
                timeframe=self.timeframe,
                observation_start_at=self.observation_start_at,
                observation_end_at=self.observation_end_at,
                known_at=self.known_at,
                subject_object_ids=self.subject_object_ids,
                source_refs=self.source_refs,
                source_rule_ids=self.source_rule_ids,
                annotation_method=self.annotation_method,
                provenance_ref=self.provenance_ref,
                rationale_code=self.rationale_code,
            )
            if self.evidence_id != expected:
                raise ValueError("qualitative evidence_id does not match canonical causal payload")

    @property
    def provenance_ready(self) -> bool:
        return self.status != EvidenceStatus.UNKNOWN and bool(self.evidence_id)

    def available_at(self, decision_at: datetime) -> bool:
        _aware("decision_at", decision_at)
        return self.known_at <= decision_at


@dataclass(frozen=True)
class LegacyQualitativeProjection:
    """Compatibility projection for existing Stage4/6 consumers.

    It carries only the legacy fields. The audited SourceQualitativeClaim remains
    the authoritative evidence record and must be retained by callers.
    """

    status: EvidenceStatus
    evidence_id: str | None
    known_at: datetime


def load_qualitative_semantic_catalog(path: str | Path) -> QualitativeSemanticCatalog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("qualitative semantic catalog root must be an object")
    return parse_qualitative_semantic_catalog(raw)


def parse_qualitative_semantic_catalog(raw: Mapping[str, Any]) -> QualitativeSemanticCatalog:
    if set(raw) != CATALOG_FIELDS:
        raise ValueError("unknown or missing qualitative catalog fields")
    _nonempty(raw.get("purpose"), "purpose")
    _nonempty(raw.get("base_stage17_head"), "base_stage17_head")
    forbidden = _string_tuple(raw.get("forbidden_fields"), "forbidden_fields")
    declared = frozenset(item.lower() for item in forbidden)
    if not REQUIRED_FORBIDDEN_FIELDS <= declared:
        raise ValueError(
            "qualitative metadata deny list cannot weaken the schema contract"
        )
    _reject_forbidden_metadata(raw, REQUIRED_FORBIDDEN_FIELDS | declared)


    if raw.get("version") != QUALITATIVE_PROVENANCE_VERSION:
        raise ValueError("unexpected qualitative provenance version")
    if raw.get("classification") != "TECHNICAL_NORMALIZATION":
        raise ValueError("qualitative provenance catalog must be TECHNICAL_NORMALIZATION")
    if raw.get("trade_entry_allowed") is not False:
        raise ValueError("qualitative provenance must fail closed")
    if raw.get("financial_backtest_allowed") is not False:
        raise ValueError("Stage18 does not authorize financial backtesting")
    if raw.get("numeric_proxy_inference_allowed") is not False:
        raise ValueError("qualitative SOURCE terms may not be auto-numericized")
    project = _string_tuple(raw.get("project_policy_applied"), "project_policy_applied")
    if project:
        raise ValueError("PROJECT policy is forbidden in qualitative SOURCE provenance")

    method_rows = _string_tuple(raw.get("annotation_methods"), "annotation_methods")
    try:
        methods = tuple(AnnotationMethod(row) for row in method_rows)
    except ValueError as exc:
        raise ValueError("unsupported qualitative annotation method") from exc
    if set(methods) != set(AnnotationMethod):
        raise ValueError("qualitative catalog must explicitly freeze allowed annotation methods")

    rows = raw.get("semantics")
    if not isinstance(rows, list) or not rows:
        raise ValueError("qualitative semantic catalog requires semantics")
    semantics: list[QualitativeSemanticDefinition] = []
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("qualitative semantic must be an object")
        if set(row) != SEMANTIC_FIELDS:
            raise ValueError("unknown or missing qualitative semantic fields")
        semantic_id = _nonempty(row.get("semantic_id"), "semantic_id")
        if semantic_id in ids:
            raise ValueError(f"duplicate qualitative semantic: {semantic_id}")
        ids.add(semantic_id)
        try:
            scope = QualitativeScope(_nonempty(row.get("scope"), "scope"))
        except ValueError as exc:
            raise ValueError(f"invalid qualitative scope for {semantic_id}") from exc
        source_refs = _string_tuple(row.get("source_refs"), f"{semantic_id}.source_refs")
        if not source_refs:
            raise ValueError(f"{semantic_id} requires source_refs")
        source_rule_ids = _string_tuple(
            row.get("source_rule_ids"), f"{semantic_id}.source_rule_ids"
        )
        description = _nonempty(row.get("description"), "description")
        semantics.append(
            QualitativeSemanticDefinition(
                semantic_id, scope, source_refs, source_rule_ids, description
            )
        )
    semantics.sort(key=lambda item: item.semantic_id)
    return QualitativeSemanticCatalog(
        version=QUALITATIVE_PROVENANCE_VERSION,
        classification="TECHNICAL_NORMALIZATION",
        trade_entry_allowed=False,
        financial_backtest_allowed=False,
        numeric_proxy_inference_allowed=False,
        project_policy_applied=project,
        annotation_methods=tuple(sorted(methods, key=lambda item: item.value)),
        forbidden_fields=forbidden,
        semantics=tuple(semantics),
    )


def make_source_qualitative_claim(
    *,
    catalog: QualitativeSemanticCatalog,
    semantic_id: str,
    status: EvidenceStatus,
    symbol: str,
    timeframe: str | int,
    observation_start_at: datetime,
    observation_end_at: datetime,
    known_at: datetime,
    subject_object_ids: tuple[str, ...],
    annotation_method: AnnotationMethod | None = None,
    provenance_ref: str | None = None,
    rationale_code: str | None = None,
) -> SourceQualitativeClaim:
    if not isinstance(status, EvidenceStatus):
        raise ValueError("status must be EvidenceStatus")
    if annotation_method is not None and not isinstance(annotation_method, AnnotationMethod):
        raise ValueError("annotation method must be AnnotationMethod")
    if type(subject_object_ids) is not tuple:
        raise ValueError("subject IDs must be an immutable tuple")
    for value in subject_object_ids:
        _audit_text(value, "subject_object_ids")
    if status != EvidenceStatus.UNKNOWN:
        _audit_text(provenance_ref, "provenance_ref")
        _audit_text(rationale_code, "rationale_code")
    definition = catalog.semantic(semantic_id)
    timeframe_text = str(timeframe)
    normalized_subjects = tuple(sorted(set(subject_object_ids)))
    if status == EvidenceStatus.UNKNOWN:
        return SourceQualitativeClaim(
            semantic_id=semantic_id,
            scope=definition.scope,
            status=status,
            symbol=symbol,
            timeframe=timeframe_text,
            observation_start_at=observation_start_at,
            observation_end_at=observation_end_at,
            known_at=known_at,
            subject_object_ids=normalized_subjects,
            source_refs=definition.source_refs,
            source_rule_ids=definition.source_rule_ids,
            annotation_method=None,
            provenance_ref=None,
            rationale_code=None,
            evidence_id=None,
        )
    if annotation_method is None or not provenance_ref or not rationale_code:
        raise ValueError("PASS/FAIL claim requires method, provenance_ref and rationale_code")
    if annotation_method not in catalog.annotation_methods:
        raise ValueError("annotation method is not allowed by frozen catalog")
    evidence_id = source_qualitative_claim_id(
        semantic_id=semantic_id,
        scope=definition.scope,
        status=status,
        symbol=symbol,
        timeframe=timeframe_text,
        observation_start_at=observation_start_at,
        observation_end_at=observation_end_at,
        known_at=known_at,
        subject_object_ids=normalized_subjects,
        source_refs=definition.source_refs,
        source_rule_ids=definition.source_rule_ids,
        annotation_method=annotation_method,
        provenance_ref=provenance_ref,
        rationale_code=rationale_code,
    )
    return SourceQualitativeClaim(
        semantic_id=semantic_id,
        scope=definition.scope,
        status=status,
        symbol=symbol,
        timeframe=timeframe_text,
        observation_start_at=observation_start_at,
        observation_end_at=observation_end_at,
        known_at=known_at,
        subject_object_ids=normalized_subjects,
        source_refs=definition.source_refs,
        source_rule_ids=definition.source_rule_ids,
        annotation_method=annotation_method,
        provenance_ref=provenance_ref,
        rationale_code=rationale_code,
        evidence_id=evidence_id,
    )


def validate_claim_against_catalog(
    claim: SourceQualitativeClaim, catalog: QualitativeSemanticCatalog
) -> None:
    definition = catalog.semantic(claim.semantic_id)
    if claim.scope != definition.scope:
        raise ValueError("qualitative claim scope does not match catalog")
    if claim.source_refs != definition.source_refs:
        raise ValueError("qualitative claim source_refs do not match frozen catalog")
    if claim.source_rule_ids != definition.source_rule_ids:
        raise ValueError("qualitative claim source_rule_ids do not match frozen catalog")
    if claim.annotation_method is not None and claim.annotation_method not in catalog.annotation_methods:
        raise ValueError("qualitative claim annotation method is not catalog-approved")


def project_legacy_qualitative(claim: SourceQualitativeClaim) -> LegacyQualitativeProjection:
    """Project audited claim to old status/id/time shape without losing claim itself."""

    return LegacyQualitativeProjection(claim.status, claim.evidence_id, claim.known_at)


def source_qualitative_claim_id(
    *,
    semantic_id: str,
    scope: QualitativeScope,
    status: EvidenceStatus,
    symbol: str,
    timeframe: str,
    observation_start_at: datetime,
    observation_end_at: datetime,
    known_at: datetime,
    subject_object_ids: tuple[str, ...],
    source_refs: tuple[str, ...],
    source_rule_ids: tuple[str, ...],
    annotation_method: AnnotationMethod,
    provenance_ref: str,
    rationale_code: str,
) -> str:
    payload = {
        "version": QUALITATIVE_PROVENANCE_VERSION,
        "semantic_id": semantic_id,
        "scope": scope.value,
        "status": status.value,
        "symbol": symbol,
        "timeframe": timeframe,
        "observation_start_at": observation_start_at.astimezone(UTC).isoformat(),
        "observation_end_at": observation_end_at.astimezone(UTC).isoformat(),
        "known_at": known_at.astimezone(UTC).isoformat(),
        "subject_object_ids": sorted(set(subject_object_ids)),
        "source_refs": list(source_refs),
        "source_rule_ids": list(source_rule_ids),
        "annotation_method": annotation_method.value,
        "provenance_ref": provenance_ref,
        "rationale_code": rationale_code,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()[:32]


def _reject_forbidden_metadata(value: Any, forbidden: frozenset[str], path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in forbidden:
                raise ValueError(f"forbidden qualitative ranking/proxy metadata at {path}.{key}")
            _reject_forbidden_metadata(child, forbidden, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_metadata(child, forbidden, f"{path}[{index}]")


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return tuple(_nonempty(item, name) for item in value)


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _audit_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank immutable text")


def _aware(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
