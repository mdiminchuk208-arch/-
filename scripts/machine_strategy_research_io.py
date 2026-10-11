"""Immutable research stage I/O and hash verification; no order/private API access."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from original_v1_1_financial_data import ROOT, checksum, save
from original_v1_1_staged_research_common import (
    stage_artifacts,
    verify_originals,
    verify_stage,
)

PARENTS = {
    "docs/original_v1_1_blinded_annotation_v1": "8f2a7e150802ba6a066592cd9052f82dba1711ec18e45de10eac80b0de8a9ce1",
    "docs/original_v1_1_evidence_completion_v4": "ab55a6f99cc6acdd3cc55be23b21f14e8d9fe7768896dc8b521478dca4acde6b",
    "docs/original_v1_1_execution_metadata_v3": "9320bcbacef61442aa4b5fc4c1d76b03528fc200092ef27af25f6ad6dd2fbf50",
}


def original_invariance():
    result = verify_originals()
    result["latest_frozen_predecessors"] = {
        name: verify_stage(ROOT / name, expected_sha=sha)
        for name, sha in PARENTS.items()
    }
    return result


def read(path):
    return json.loads(path.read_text())


def verify_machine(path, expected=None):
    path = Path(path)
    m = read(path / "freeze_manifest.json")
    if expected and checksum(path / "freeze_manifest.json") != expected:
        raise ValueError("Pinned machine manifest changed")
    names = {
        str(p.relative_to(ROOT))
        for p in path.rglob("*")
        if p.is_file() and p.name != "freeze_manifest.json"
    }
    prefix = str(path.relative_to(ROOT)) + "/"
    if names != {p for p in m["artifacts"] if p.startswith(prefix)}:
        raise ValueError("Machine namespace membership changed")
    for name, sha in m["artifacts"].items():
        if checksum(ROOT / name) != sha:
            raise ValueError("Machine frozen artifact changed: " + name)
    if m["trade_entry_allowed"] is not False or m["LIVE_enabled"] is not False:
        raise ValueError("Unsafe research stage")
    return {
        "path": str((path / "freeze_manifest.json").relative_to(ROOT)),
        "sha256": checksum(path / "freeze_manifest.json"),
    }


def qa_stage(dest, code, replay, files, *, minimum_tests=912):
    original_invariance()
    hashes = {name: checksum(dest / name) for name in files}
    if hashes != {name: checksum(replay / name) for name in files}:
        raise ValueError("Replay output mismatch")
    logs = {
        n: (dest / "qa" / f"{n}.log").read_text()
        for n in ("full_unittest", "ruff", "compile", "mypy", "frozen_parent_resume")
    }
    match = re.search(r"Ran (\d+) tests[^\n]*\n\nOK(?:\n|$)", logs["full_unittest"])
    if (
        not match
        or int(match[1]) < minimum_tests
        or "FAILED (" in logs["full_unittest"]
        or "skipped=" in logs["full_unittest"]
    ):
        raise ValueError("Full inherited/new tests failed")
    if (
        "All checks passed!" not in logs["ruff"]
        or logs["compile"].strip()
        or "Success: no issues found" not in logs["mypy"]
        or "VERIFIED_RESUME v1.1" not in logs["frozen_parent_resume"]
    ):
        raise ValueError("Static/archive QA failed")
    receipt = {
        "status": "PASS",
        "tests": int(match[1]),
        "deterministic_replay_outputs": len(files),
        "replay_sha256": hashes,
        "code_sha256": {n: checksum(ROOT / n) for n in code},
        "qa_log_sha256": {n: checksum(dest / "qa" / f"{n}.log") for n in logs},
        "original_invariance": "PASS",
        "trade_entry_allowed": False,
    }
    save(dest / "QA_RECEIPT.json", receipt)
    return receipt


def seal_machine(dest, code, *, stage, version, parents, status, outcomes=False):
    path = dest / "freeze_manifest.json"
    if path.exists():
        raise ValueError("Existing freeze preserved; use --resume-existing")
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != "medium-term-source-research"
    ):
        raise ValueError("Research branch required")
    qa = read(dest / "QA_RECEIPT.json")
    for name, sha in qa["code_sha256"].items():
        if checksum(ROOT / name) != sha:
            raise ValueError("Code changed after QA")
    for name, sha in qa["qa_log_sha256"].items():
        if checksum(dest / "qa" / f"{name}.log") != sha:
            raise ValueError("QA log changed")
    for name, sha in qa["replay_sha256"].items():
        if checksum(dest / name) != sha:
            raise ValueError("Output changed after replay")
    for name, sha in parents.items():
        if checksum(ROOT / name) != sha:
            raise ValueError("Parent manifest changed")
    original_invariance()
    save(
        path,
        {
            "stage": stage,
            "version": version,
            "status": status,
            "parents": parents,
            "artifacts": dict(sorted(stage_artifacts(dest, code).items())),
            "QA_tests": qa["tests"],
            "outcomes_computed": outcomes,
            "trade_entry_allowed": False,
            "LIVE_enabled": False,
            "historical_exchange_execution_claimed": False,
        },
    )
    print("FROZEN", stage, version, checksum(path), flush=True)


def commit_stage(dest, message):
    """Explicit research commit, with exact staged-byte verification."""
    manifest = dest / "freeze_manifest.json"
    m = read(manifest)
    names = set(m["artifacts"]) | {str(manifest.relative_to(ROOT))}
    subprocess.run(["git", "add", "--", *sorted(names)], cwd=ROOT, check=True)
    staged = set(
        subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")[:-1]
    )
    if staged != names:
        raise ValueError("Unexpected staging scope")
    from hashlib import sha256

    for name in staged:
        expected = m["artifacts"].get(name, checksum(manifest))
        if (
            sha256(
                subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
            ).hexdigest()
            != expected
        ):
            raise ValueError("Staged byte conversion: " + name)
    subprocess.run(
        ["git", "diff", "--cached", "--check", "--", ".", ":(exclude)**/provenance/*"],
        cwd=ROOT,
        check=True,
    )
    stat = subprocess.check_output(
        ["git", "diff", "--cached", "--stat"], cwd=ROOT, text=True
    )
    print(stat.splitlines()[-1], flush=True)
    proc = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    print(proc.stdout.splitlines()[0], flush=True)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
