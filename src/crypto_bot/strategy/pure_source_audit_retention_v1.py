"""Verify repository-retained historical analyst receipts, not SOURCE semantics."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


HISTORICAL_AGENT_LEDGER_SHA256 = (
    "4e2c93c3a52e4de225de34e0a2cfda3074b6c485d5bfc64a261d15b8338bef22"
)


def validate_retained_handoffs(repository: Path, ledger: Path) -> tuple[str, ...]:
    root = repository.resolve()
    original = ledger / "AGENT_LEDGER.json"
    if sha256(original.read_bytes()).hexdigest() != HISTORICAL_AGENT_LEDGER_SHA256:
        raise ValueError(
            "historical handoff identity ledger differs from independent pin"
        )
    historical = json.loads(original.read_text(encoding="utf-8"))
    expected = historical["actual_agent_handoffs"]
    receipt = json.loads(
        (ledger / "audit/HANDOFF_RETENTION.json").read_text(encoding="utf-8")
    )
    if (
        receipt["classification"] != "TECHNICAL_NORMALIZATION"
        or receipt["source_semantics_changed"] is not False
    ):
        raise ValueError("retention receipt cannot redefine SOURCE")
    rows = receipt["handoffs"]
    if len(rows) != len(expected) or {r["original_locator"] for r in rows} != set(
        expected
    ):
        raise ValueError("historical handoff retention coverage mismatch")
    paths = []
    for row in rows:
        relative = Path(row["repository_path"])
        path = (root / relative).resolve()
        if (
            relative.is_absolute()
            or not path.is_relative_to(root)
            or not path.is_file()
        ):
            raise ValueError("handoff must exist at a repository-relative path")
        raw = path.read_bytes()
        if (
            row["sha256"] != expected[row["original_locator"]]
            or sha256(raw).hexdigest() != row["sha256"]
            or len(raw) != row["bytes"]
        ):
            raise ValueError("retained historical handoff bytes differ")
        paths.append(str(relative))
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate retained handoff path")
    return tuple(sorted(paths))
