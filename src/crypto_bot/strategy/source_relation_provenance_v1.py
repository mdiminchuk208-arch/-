"""Typed causal relation evidence for priority-1 PURE SOURCE reconstruction.

Stage24 carries exact supplied object/event relationships that Stage18 qualitative
claims intentionally cannot express. It never discovers market relations, ranks
alternatives, creates setups or grants trading permission.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from crypto_bot.strategy.source_qualitative_provenance_v2 import AnnotationMethod
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus

RELATION_PROVENANCE_VERSION = "PURE_SOURCE_STAGE24_RELATION_PROVENANCE_V1"
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
        "classification",
        "baseline_identifiability",
        "trade_entry_allowed",
        "financial_backtest_allowed",
        "paper_allowed",
        "live_allowed",
        "private_api_allowed",
        "project_policy_applied",
        "automatic_relation_inference_allowed",
        "annotation_methods",
        "relations",
        "forbidden_fields",
    }
)
RELATION_FIELDS = frozenset(
    {
        "semantic_id",
        "source_refs",
        "source_rule_ids",
        "subject_roles",
        "event_roles",
        "ordered_event_roles",
        "description",
    }
)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _strings(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{name} must be a JSON string array")
    result = tuple(v.strip() for v in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicates")
    return result


@dataclass(frozen=True)
class SourceRelationDefinition:
    semantic_id: str
    source_refs: tuple[str, ...]
    source_rule_ids: tuple[str, ...]
    subject_roles: tuple[str, ...]
    event_roles: tuple[str, ...]
    ordered_event_roles: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class SourceRelationCatalog:
    version: str
    classification: str
    baseline_identifiability: str
    trade_entry_allowed: bool
    financial_backtest_allowed: bool
    paper_allowed: bool
    live_allowed: bool
    private_api_allowed: bool
    automatic_relation_inference_allowed: bool
    project_policy_applied: tuple[str, ...]
    annotation_methods: tuple[AnnotationMethod, ...]
    forbidden_fields: tuple[str, ...]
    relations: tuple[SourceRelationDefinition, ...]

    def relation(self, semantic_id: str) -> SourceRelationDefinition:
        rows = tuple(row for row in self.relations if row.semantic_id == semantic_id)
        if len(rows) != 1:
            raise KeyError(f"unknown or non-unique relation semantic: {semantic_id}")
        return rows[0]


@dataclass(frozen=True, order=True)
class RelationSubject:
    role: str
    subject_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _text(self.role, "subject role"))
        object.__setattr__(self, "subject_id", _text(self.subject_id, "subject id"))


@dataclass(frozen=True, order=True)
class RelationEvent:
    role: str
    evidence_id: str
    occurred_at: datetime
    known_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _text(self.role, "event role"))
        object.__setattr__(self, "evidence_id", _text(self.evidence_id, "event evidence id"))
        occurred = _aware(self.occurred_at, "event occurred_at")
        known = _aware(self.known_at, "event known_at")
        if known < occurred:
            raise ValueError("event cannot be known before it occurs")
        object.__setattr__(self, "occurred_at", occurred)
        object.__setattr__(self, "known_at", known)


@dataclass(frozen=True)
class SourceRelationClaim:
    semantic_id: str
    status: EvidenceStatus
    symbol: str
    timeframe: str
    observation_start_at: datetime
    observation_end_at: datetime
    known_at: datetime
    subjects: tuple[RelationSubject, ...]
    events: tuple[RelationEvent, ...]
    source_refs: tuple[str, ...]
    source_rule_ids: tuple[str, ...]
    annotation_method: AnnotationMethod | None
    provenance_ref: str | None
    rationale_code: str | None
    evidence_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_id", _text(self.semantic_id, "semantic_id"))
        object.__setattr__(self, "symbol", _text(self.symbol, "symbol"))
        object.__setattr__(self, "timeframe", _text(self.timeframe, "timeframe"))
        if not isinstance(self.status, EvidenceStatus):
            raise ValueError("typed EvidenceStatus required")
        start = _aware(self.observation_start_at, "observation_start_at")
        end = _aware(self.observation_end_at, "observation_end_at")
        known = _aware(self.known_at, "known_at")
        if not start < end:
            raise ValueError("relation observation window must be positive")
        if known < end:
            raise ValueError("relation cannot be known before observed data closes")
        object.__setattr__(self, "observation_start_at", start)
        object.__setattr__(self, "observation_end_at", end)
        object.__setattr__(self, "known_at", known)
        if type(self.subjects) is not tuple or not self.subjects:
            raise ValueError("immutable relation subjects required")
        if type(self.events) is not tuple:
            raise ValueError("immutable relation events required")
        if any(not isinstance(v, RelationSubject) for v in self.subjects):
            raise TypeError("typed RelationSubject required")
        if any(not isinstance(v, RelationEvent) for v in self.events):
            raise TypeError("typed RelationEvent required")
        if len({v.role for v in self.subjects}) != len(self.subjects):
            raise ValueError("duplicate relation subject role")
        if len({v.role for v in self.events}) != len(self.events):
            raise ValueError("duplicate relation event role")
        if len({v.subject_id for v in self.subjects}) != len(self.subjects):
            raise ValueError("one physical subject cannot silently fill multiple relation roles")
        if any(event.known_at > known for event in self.events):
            raise ValueError("claim known_at cannot precede event availability")
        for collection, name in ((self.source_refs, "source_refs"), (self.source_rule_ids, "source_rule_ids")):
            if type(collection) is not tuple or any(not isinstance(v, str) or not v.strip() for v in collection):
                raise ValueError(f"{name} must be an immutable text tuple")
        if not self.source_refs or not self.source_rule_ids:
            raise ValueError("relation claim requires frozen SOURCE references and rule IDs")
        if self.annotation_method is not None and not isinstance(self.annotation_method, AnnotationMethod):
            raise TypeError("typed annotation method required")
        if self.status == EvidenceStatus.UNKNOWN:
            if any(v is not None for v in (self.annotation_method, self.provenance_ref, self.rationale_code, self.evidence_id)):
                raise ValueError("UNKNOWN relation cannot carry audited provenance")
        else:
            if self.annotation_method is None:
                raise ValueError("PASS/FAIL relation requires annotation method")
            provenance = _text(self.provenance_ref, "provenance_ref")
            rationale = _text(self.rationale_code, "rationale_code")
            evidence = _text(self.evidence_id, "evidence_id")
            expected = source_relation_claim_id(
                semantic_id=self.semantic_id,
                status=self.status,
                symbol=self.symbol,
                timeframe=self.timeframe,
                observation_start_at=start,
                observation_end_at=end,
                known_at=known,
                subjects=self.subjects,
                events=self.events,
                source_refs=self.source_refs,
                source_rule_ids=self.source_rule_ids,
                annotation_method=self.annotation_method,
                provenance_ref=provenance,
                rationale_code=rationale,
            )
            if evidence != expected:
                raise ValueError("relation evidence_id does not match canonical causal payload")

    @property
    def subject_object_ids(self) -> tuple[str, ...]:
        return tuple(sorted(subject.subject_id for subject in self.subjects))


@dataclass(frozen=True)
class RelationAssessment:
    status: EvidenceStatus
    reason: str
    supporting_claim_ids: tuple[str, ...]
    known_at: datetime | None


def load_source_relation_catalog(path: str | Path) -> SourceRelationCatalog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("relation catalog root must be an object")
    return parse_source_relation_catalog(raw)


def parse_source_relation_catalog(raw: Mapping[str, Any]) -> SourceRelationCatalog:
    if set(raw) != CATALOG_FIELDS:
        raise ValueError("unknown or missing relation catalog fields")
    if raw.get("version") != RELATION_PROVENANCE_VERSION:
        raise ValueError("unexpected relation provenance version")
    if raw.get("classification") != "TECHNICAL_NORMALIZATION":
        raise ValueError("relation transport must be TECHNICAL_NORMALIZATION")
    if raw.get("baseline_identifiability") != "NOT_IDENTIFIABLE":
        raise ValueError("relation transport cannot claim baseline identifiability")
    for field in (
        "trade_entry_allowed",
        "financial_backtest_allowed",
        "paper_allowed",
        "live_allowed",
        "private_api_allowed",
        "automatic_relation_inference_allowed",
    ):
        if raw.get(field) is not False:
            raise ValueError(f"{field} must remain false")
    project = _strings(raw.get("project_policy_applied"), "project_policy_applied")
    if project:
        raise ValueError("PROJECT policy is forbidden in SOURCE relation transport")
    forbidden = _strings(raw.get("forbidden_fields"), "forbidden_fields")
    if not REQUIRED_FORBIDDEN_FIELDS <= frozenset(v.lower() for v in forbidden):
        raise ValueError("relation metadata deny list cannot weaken the contract")
    methods_raw = _strings(raw.get("annotation_methods"), "annotation_methods")
    try:
        methods = tuple(AnnotationMethod(v) for v in methods_raw)
    except ValueError as exc:
        raise ValueError("unsupported relation annotation method") from exc
    if set(methods) != set(AnnotationMethod):
        raise ValueError("relation catalog must freeze all allowed annotation methods")
    rows = raw.get("relations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("relation catalog requires relations")
    definitions = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != RELATION_FIELDS:
            raise ValueError("unknown or missing relation definition fields")
        semantic = _text(row.get("semantic_id"), "semantic_id")
        if semantic in seen:
            raise ValueError("duplicate relation semantic")
        seen.add(semantic)
        refs = _strings(row.get("source_refs"), f"{semantic}.source_refs")
        rules = _strings(row.get("source_rule_ids"), f"{semantic}.source_rule_ids")
        subjects = _strings(row.get("subject_roles"), f"{semantic}.subject_roles")
        events = _strings(row.get("event_roles"), f"{semantic}.event_roles")
        ordered = _strings(row.get("ordered_event_roles"), f"{semantic}.ordered_event_roles")
        if not refs or not rules or not subjects:
            raise ValueError("relation definitions require source refs/rules/subjects")
        if any(role not in events for role in ordered):
            raise ValueError("ordered event role must be declared in event_roles")
        definitions.append(
            SourceRelationDefinition(
                semantic,
                refs,
                rules,
                subjects,
                events,
                ordered,
                _text(row.get("description"), "description"),
            )
        )
    return SourceRelationCatalog(
        RELATION_PROVENANCE_VERSION,
        "TECHNICAL_NORMALIZATION",
        "NOT_IDENTIFIABLE",
        False,
        False,
        False,
        False,
        False,
        False,
        project,
        tuple(sorted(methods, key=lambda v: v.value)),
        forbidden,
        tuple(sorted(definitions, key=lambda v: v.semantic_id)),
    )


def validate_relation_against_catalog(claim: SourceRelationClaim, catalog: SourceRelationCatalog) -> None:
    definition = catalog.relation(claim.semantic_id)
    if claim.source_refs != definition.source_refs or claim.source_rule_ids != definition.source_rule_ids:
        raise ValueError("relation claim does not match frozen SOURCE references")
    if tuple(subject.role for subject in claim.subjects) != definition.subject_roles:
        raise ValueError("relation subject roles do not match frozen semantic")
    if tuple(event.role for event in claim.events) != definition.event_roles:
        raise ValueError("relation event roles do not match frozen semantic")
    event_map = {event.role: event for event in claim.events}
    ordered = tuple(event_map[role] for role in definition.ordered_event_roles)
    if any(right.occurred_at < left.occurred_at for left, right in zip(ordered, ordered[1:])):
        raise ValueError("SOURCE relation event occurrence order violated")
    if claim.annotation_method is not None and claim.annotation_method not in catalog.annotation_methods:
        raise ValueError("relation annotation method is not catalog-approved")


def make_source_relation_claim(
    *,
    catalog: SourceRelationCatalog,
    semantic_id: str,
    status: EvidenceStatus,
    symbol: str,
    timeframe: str | int,
    observation_start_at: datetime,
    observation_end_at: datetime,
    known_at: datetime,
    subjects: tuple[RelationSubject, ...],
    events: tuple[RelationEvent, ...] = (),
    annotation_method: AnnotationMethod | None = None,
    provenance_ref: str | None = None,
    rationale_code: str | None = None,
) -> SourceRelationClaim:
    definition = catalog.relation(semantic_id)
    if type(subjects) is not tuple or type(events) is not tuple:
        raise TypeError("immutable relation subjects/events required")
    normalized_subjects = tuple(subjects)
    normalized_events = tuple(events)
    if tuple(v.role for v in normalized_subjects) != definition.subject_roles:
        raise ValueError("relation subject roles do not match frozen semantic")
    if tuple(v.role for v in normalized_events) != definition.event_roles:
        raise ValueError("relation event roles do not match frozen semantic")
    if status == EvidenceStatus.UNKNOWN:
        claim = SourceRelationClaim(
            semantic_id,
            status,
            symbol,
            str(timeframe),
            observation_start_at,
            observation_end_at,
            known_at,
            normalized_subjects,
            normalized_events,
            definition.source_refs,
            definition.source_rule_ids,
            None,
            None,
            None,
            None,
        )
        validate_relation_against_catalog(claim, catalog)
        return claim
    if annotation_method is None or not provenance_ref or not rationale_code:
        raise ValueError("PASS/FAIL relation requires method, provenance and rationale")
    evidence_id = source_relation_claim_id(
        semantic_id=semantic_id,
        status=status,
        symbol=symbol,
        timeframe=str(timeframe),
        observation_start_at=_aware(observation_start_at, "observation_start_at"),
        observation_end_at=_aware(observation_end_at, "observation_end_at"),
        known_at=_aware(known_at, "known_at"),
        subjects=normalized_subjects,
        events=normalized_events,
        source_refs=definition.source_refs,
        source_rule_ids=definition.source_rule_ids,
        annotation_method=annotation_method,
        provenance_ref=provenance_ref,
        rationale_code=rationale_code,
    )
    claim = SourceRelationClaim(
        semantic_id,
        status,
        symbol,
        str(timeframe),
        observation_start_at,
        observation_end_at,
        known_at,
        normalized_subjects,
        normalized_events,
        definition.source_refs,
        definition.source_rule_ids,
        annotation_method,
        provenance_ref,
        rationale_code,
        evidence_id,
    )
    validate_relation_against_catalog(claim, catalog)
    return claim


def source_relation_claim_id(
    *,
    semantic_id: str,
    status: EvidenceStatus,
    symbol: str,
    timeframe: str,
    observation_start_at: datetime,
    observation_end_at: datetime,
    known_at: datetime,
    subjects: tuple[RelationSubject, ...],
    events: tuple[RelationEvent, ...],
    source_refs: tuple[str, ...],
    source_rule_ids: tuple[str, ...],
    annotation_method: AnnotationMethod,
    provenance_ref: str,
    rationale_code: str,
) -> str:
    payload = {
        "version": RELATION_PROVENANCE_VERSION,
        "semantic_id": semantic_id,
        "status": status.value,
        "symbol": symbol,
        "timeframe": timeframe,
        "observation_start_at": _aware(observation_start_at, "observation_start_at").isoformat(),
        "observation_end_at": _aware(observation_end_at, "observation_end_at").isoformat(),
        "known_at": _aware(known_at, "known_at").isoformat(),
        "subjects": [(v.role, v.subject_id) for v in subjects],
        "events": [
            (v.role, v.evidence_id, v.occurred_at.isoformat(), v.known_at.isoformat())
            for v in events
        ],
        "source_refs": list(source_refs),
        "source_rule_ids": list(source_rule_ids),
        "annotation_method": annotation_method.value,
        "provenance_ref": provenance_ref,
        "rationale_code": rationale_code,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "source-relation-" + sha256(raw).hexdigest()
