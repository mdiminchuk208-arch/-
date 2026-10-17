"""Typed, non-ranked registry for explicit PURE SOURCE alternatives.

Stage 17 does not choose a trading branch.  It gives finite alternatives stable
identities and preserves which parts are exact, bounded, relative or still
under-specified by SOURCE.  Historical outcomes, PROJECT scores and preference
metadata are rejected by schema validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


BRANCH_REGISTRY_VERSION = "PURE_SOURCE_STAGE17_BRANCH_REGISTRY_V2"
SELECTION_POLICY = "NO_PRECEDENCE_NO_RANKING_NO_OUTCOME_SELECTION"


class BranchDimension(str, Enum):
    ENTRY = "ENTRY"
    ENTRY_PATH = "ENTRY_PATH"
    STOP = "STOP"
    EXIT_ALLOCATION = "EXIT_ALLOCATION"
    PARAMETER = "PARAMETER"


class GeometryStatus(str, Enum):
    EXACT_IF_PARENT_GEOMETRY_KNOWN = "EXACT_IF_PARENT_GEOMETRY_KNOWN"
    BOUNDED_ZONE_NO_EXACT_QUOTE = "BOUNDED_ZONE_NO_EXACT_QUOTE"
    PATH_DEFINED_GEOMETRY_DEPENDS_ON_ENTRY_BRANCH = "PATH_DEFINED_GEOMETRY_DEPENDS_ON_ENTRY_BRANCH"
    PATH_DEFINED_FINAL_QUOTE_UNRESOLVED = "PATH_DEFINED_FINAL_QUOTE_UNRESOLVED"
    RELATIVE_ANCHOR_NO_EXACT_BUFFER = "RELATIVE_ANCHOR_NO_EXACT_BUFFER"
    EXACT_ALLOCATION_IF_FTA_KNOWN = "EXACT_ALLOCATION_IF_FTA_KNOWN"
    ALLOCATION_FAMILY_NO_EXACT_FRACTION = "ALLOCATION_FAMILY_NO_EXACT_FRACTION"
    EXACT_PARAMETER = "EXACT_PARAMETER"
    PARAMETER_FAMILY_NO_SOURCE_PRECEDENCE = "PARAMETER_FAMILY_NO_SOURCE_PRECEDENCE"


@dataclass(frozen=True)
class SourceBranchAlternative:
    family_id: str
    alternative_id: str
    dimension: BranchDimension
    source_refs: tuple[str, ...]
    geometry_status: GeometryStatus
    exact_value: int | float | None
    requirements: tuple[str, ...]
    unresolved: tuple[str, ...]
    description: str

    @property
    def is_exact_choice(self) -> bool:
        """Whether SOURCE supplies exact branch geometry/parameter once parents exist.

        This is *not* trade eligibility and must never be used as ranking.
        """

        return self.geometry_status in {
            GeometryStatus.EXACT_IF_PARENT_GEOMETRY_KNOWN,
            GeometryStatus.EXACT_ALLOCATION_IF_FTA_KNOWN,
            GeometryStatus.EXACT_PARAMETER,
        }

    @property
    def needs_additional_resolution(self) -> bool:
        return bool(self.unresolved)


@dataclass(frozen=True)
class SourceBranchFamily:
    family_id: str
    dimension: BranchDimension
    source_refs: tuple[str, ...]
    alternatives: tuple[SourceBranchAlternative, ...]


@dataclass(frozen=True)
class SourceBranchRegistry:
    version: str
    classification: str
    selection_policy: str
    trade_entry_allowed: bool
    financial_backtest_allowed: bool
    project_policy_applied: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    families: tuple[SourceBranchFamily, ...]

    def alternatives(self, family_id: str) -> tuple[SourceBranchAlternative, ...]:
        for family in self.families:
            if family.family_id == family_id:
                return family.alternatives
        raise KeyError(f"unknown SOURCE branch family: {family_id}")

    def alternative(self, alternative_id: str) -> SourceBranchAlternative:
        matches = [
            option
            for family in self.families
            for option in family.alternatives
            if option.alternative_id == alternative_id
        ]
        if len(matches) != 1:
            raise KeyError(f"unknown or non-unique SOURCE alternative: {alternative_id}")
        return matches[0]


def load_source_branch_registry(path: str | Path) -> SourceBranchRegistry:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("SOURCE branch registry root must be an object")
    return parse_source_branch_registry(raw)


def parse_source_branch_registry(raw: Mapping[str, Any]) -> SourceBranchRegistry:
    """Parse and validate the Stage-17 no-precedence branch contract."""

    forbidden = _string_tuple(raw.get("forbidden_fields"), "forbidden_fields")
    _reject_forbidden_metadata(raw, frozenset(field.lower() for field in forbidden))

    if raw.get("version") != BRANCH_REGISTRY_VERSION:
        raise ValueError("unexpected PURE SOURCE branch registry version")
    if raw.get("classification") != "TECHNICAL_NORMALIZATION":
        raise ValueError("Stage17 branch registry must remain TECHNICAL_NORMALIZATION")
    if raw.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("SOURCE alternatives must have no precedence/ranking/outcome selection")
    if raw.get("trade_entry_allowed") is not False:
        raise ValueError("PURE SOURCE branch registry must fail closed")
    if raw.get("financial_backtest_allowed") is not False:
        raise ValueError("Stage17 does not authorize financial backtesting")
    project_policy = _string_tuple(raw.get("project_policy_applied"), "project_policy_applied")
    if project_policy:
        raise ValueError("PROJECT policy is forbidden in PURE SOURCE branch registry")

    family_rows = raw.get("families")
    if not isinstance(family_rows, list) or not family_rows:
        raise ValueError("branch registry requires non-empty families")

    families: list[SourceBranchFamily] = []
    family_ids: set[str] = set()
    alternative_ids: set[str] = set()
    for family_row in family_rows:
        if not isinstance(family_row, dict):
            raise ValueError("branch family must be an object")
        family_id = _nonempty(family_row.get("family_id"), "family_id")
        if family_id in family_ids:
            raise ValueError(f"duplicate SOURCE branch family: {family_id}")
        family_ids.add(family_id)
        try:
            dimension = BranchDimension(_nonempty(family_row.get("dimension"), "dimension"))
        except ValueError as exc:
            raise ValueError(f"invalid branch dimension for {family_id}") from exc
        source_refs = _string_tuple(family_row.get("source_refs"), f"{family_id}.source_refs")
        if not source_refs:
            raise ValueError(f"{family_id} requires source_refs")
        alternatives_raw = family_row.get("alternatives")
        if not isinstance(alternatives_raw, list) or len(alternatives_raw) < 2:
            raise ValueError(f"{family_id} must represent at least two SOURCE alternatives")

        alternatives: list[SourceBranchAlternative] = []
        for option_row in alternatives_raw:
            if not isinstance(option_row, dict):
                raise ValueError(f"{family_id} alternative must be an object")
            alternative_id = _nonempty(option_row.get("alternative_id"), "alternative_id")
            if alternative_id in alternative_ids:
                raise ValueError(f"duplicate SOURCE alternative id: {alternative_id}")
            alternative_ids.add(alternative_id)
            try:
                geometry = GeometryStatus(
                    _nonempty(option_row.get("geometry_status"), "geometry_status")
                )
            except ValueError as exc:
                raise ValueError(f"invalid geometry status for {alternative_id}") from exc
            exact_value = option_row.get("exact_value")
            if exact_value is not None and (
                isinstance(exact_value, bool) or not isinstance(exact_value, (int, float))
            ):
                raise ValueError(f"{alternative_id}.exact_value must be numeric or null")
            requirements = _string_tuple(
                option_row.get("requirements"), f"{alternative_id}.requirements"
            )
            unresolved = _string_tuple(
                option_row.get("unresolved"), f"{alternative_id}.unresolved"
            )
            description = _nonempty(option_row.get("description"), "description")
            _validate_geometry_resolution(alternative_id, geometry, exact_value, unresolved)
            alternatives.append(
                SourceBranchAlternative(
                    family_id=family_id,
                    alternative_id=alternative_id,
                    dimension=dimension,
                    source_refs=source_refs,
                    geometry_status=geometry,
                    exact_value=exact_value,
                    requirements=requirements,
                    unresolved=unresolved,
                    description=description,
                )
            )
        alternatives.sort(key=lambda row: row.alternative_id)
        families.append(
            SourceBranchFamily(
                family_id=family_id,
                dimension=dimension,
                source_refs=source_refs,
                alternatives=tuple(alternatives),
            )
        )

    families.sort(key=lambda row: row.family_id)
    return SourceBranchRegistry(
        version=BRANCH_REGISTRY_VERSION,
        classification="TECHNICAL_NORMALIZATION",
        selection_policy=SELECTION_POLICY,
        trade_entry_allowed=False,
        financial_backtest_allowed=False,
        project_policy_applied=project_policy,
        forbidden_fields=forbidden,
        families=tuple(families),
    )


def source_branch_registry_fingerprint(registry: SourceBranchRegistry) -> str:
    """Stable fingerprint independent of JSON declaration order."""

    payload = {
        "version": registry.version,
        "classification": registry.classification,
        "selection_policy": registry.selection_policy,
        "trade_entry_allowed": registry.trade_entry_allowed,
        "financial_backtest_allowed": registry.financial_backtest_allowed,
        "project_policy_applied": list(registry.project_policy_applied),
        "forbidden_fields": sorted(registry.forbidden_fields),
        "families": [
            {
                "family_id": family.family_id,
                "dimension": family.dimension.value,
                "source_refs": list(family.source_refs),
                "alternatives": [
                    {
                        "alternative_id": option.alternative_id,
                        "geometry_status": option.geometry_status.value,
                        "exact_value": option.exact_value,
                        "requirements": list(option.requirements),
                        "unresolved": list(option.unresolved),
                        "description": option.description,
                    }
                    for option in family.alternatives
                ],
            }
            for family in registry.families
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()


def _validate_geometry_resolution(
    alternative_id: str,
    geometry: GeometryStatus,
    exact_value: int | float | None,
    unresolved: Sequence[str],
) -> None:
    unresolved_statuses = {
        GeometryStatus.BOUNDED_ZONE_NO_EXACT_QUOTE,
        GeometryStatus.PATH_DEFINED_GEOMETRY_DEPENDS_ON_ENTRY_BRANCH,
        GeometryStatus.PATH_DEFINED_FINAL_QUOTE_UNRESOLVED,
        GeometryStatus.RELATIVE_ANCHOR_NO_EXACT_BUFFER,
        GeometryStatus.ALLOCATION_FAMILY_NO_EXACT_FRACTION,
        GeometryStatus.PARAMETER_FAMILY_NO_SOURCE_PRECEDENCE,
    }
    if geometry in unresolved_statuses and not unresolved:
        raise ValueError(f"{alternative_id} must preserve explicit unresolved blockers")
    if geometry == GeometryStatus.EXACT_PARAMETER and exact_value is None:
        raise ValueError(f"{alternative_id} exact parameter requires exact_value")
    if geometry == GeometryStatus.EXACT_ALLOCATION_IF_FTA_KNOWN and exact_value != 1.0:
        raise ValueError(f"{alternative_id} full FTA allocation must be exactly 1.0")


def _reject_forbidden_metadata(value: Any, forbidden: frozenset[str], path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in forbidden:
                raise ValueError(f"forbidden outcome/ranking metadata at {path}.{key}")
            _reject_forbidden_metadata(child, forbidden, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_metadata(child, forbidden, f"{path}[{index}]")


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    out: list[str] = []
    for item in value:
        out.append(_nonempty(item, name))
    return tuple(out)


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
