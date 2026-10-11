"""Hash-only stage boundaries and offline QA; no financial entry points."""

from __future__ import annotations

import gzip
import json
import re
import subprocess
from contextlib import contextmanager

from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_financial_data import ROOT, checksum, compact, save
from run_original_v1_1_evidence_completion_v3 import DEST as V3
from run_original_v1_1_evidence_completion_v3 import resume as resume_v3

V3_SHA = "2ac66c22e51ca21cfa802002a98fdc52d60c1d16c57899cfb2d3aaaf7365055e"
RESEARCH_BRANCH = "medium-term-source-research"


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            no_outcomes(row)
            yield row


@contextmanager
def writer(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("wb") as raw,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9
        ) as stream,
    ):
        yield lambda row: stream.write((compact(row) + "\n").encode())


def verify_originals():
    if checksum(V3 / "freeze_manifest.json") != V3_SHA:
        raise ValueError("Pinned v3 manifest changed")
    resume_v3()
    return {
        "v3_manifest_sha256": V3_SHA,
        "v1_v1_1_v2_v3_recovery_first_result_dataset_hashes": "PASS",
    }


def stage_artifacts(dest, code):
    return {
        str(p.relative_to(ROOT)): checksum(p)
        for p in dest.rglob("*")
        if p.is_file() and p.name != "freeze_manifest.json"
    } | {name: checksum(ROOT / name) for name in code}


def verify_stage(dest, *, expected_sha=None):
    path = dest / "freeze_manifest.json"
    manifest = read(path)
    if expected_sha and checksum(path) != expected_sha:
        raise ValueError("Parent stage SHA changed")
    actual = {
        str(p.relative_to(ROOT)) for p in dest.rglob("*") if p.is_file() and p != path
    }
    namespace = str(dest.relative_to(ROOT)) + "/"
    if actual != {name for name in manifest["artifacts"] if name.startswith(namespace)}:
        raise ValueError("Closed stage namespace membership changed")
    for name, expected in manifest["artifacts"].items():
        if checksum(ROOT / name) != expected:
            raise ValueError("Stage artifact changed: " + name)
    if (
        manifest["trade_entry_allowed"] is not False
        or manifest["SECOND_FINANCIAL_BACKTEST_RAN"] is not False
    ):
        raise ValueError("Unsafe nonfinancial stage manifest")
    return {
        "manifest": str(path.relative_to(ROOT)),
        "sha256": checksum(path),
        "artifacts": len(manifest["artifacts"]),
    }


def validate_qa(dest, code, replay, generated, *, minimum_tests):
    verify_originals()
    originals = {name: checksum(dest / name) for name in generated}
    if originals != {name: checksum(replay / name) for name in generated}:
        raise ValueError("Deterministic replay mismatch")
    logs = {
        name: (dest / "qa" / f"{name}.log").read_text()
        for name in ("full_unittest", "ruff", "compile", "mypy", "frozen_parent_resume")
    }
    match = re.search(r"Ran (\d+) tests[^\n]*\n\nOK(?:\n|$)", logs["full_unittest"])
    if (
        not match
        or int(match[1]) < minimum_tests
        or "FAILED (" in logs["full_unittest"]
        or "skipped=" in logs["full_unittest"]
    ):
        raise ValueError("Inherited/new test gate failed")
    if (
        "All checks passed!" not in logs["ruff"]
        or logs["compile"].strip()
        or "Success: no issues found" not in logs["mypy"]
        or "VERIFIED_RESUME v1.1" not in logs["frozen_parent_resume"]
    ):
        raise ValueError("Tooling/archive invariance gate failed")
    receipt = {
        "status": "PASS",
        "tests": int(match[1]),
        "deterministic_replay_outputs": len(generated),
        "replay_sha256": originals,
        "frozen_v1_v1_1_v2_v3_recovery_first_result_dataset": "PASS",
        "baseline_source_audit_archive_invariance": "PASS",
        "code_sha256": {name: checksum(ROOT / name) for name in code},
        "qa_log_sha256": {name: checksum(dest / "qa" / f"{name}.log") for name in logs},
        "SECOND_FINANCIAL_BACKTEST_RAN": False,
        "trade_entry_allowed": False,
    }
    save(dest / "QA_RECEIPT.json", receipt)
    return receipt


def seal(dest, code, *, name, parent, status):
    path = dest / "freeze_manifest.json"
    if path.exists():
        raise ValueError("Existing seal preserved; use --resume-existing")
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != RESEARCH_BRANCH
    ):
        raise ValueError("Research branch required")
    qa = read(dest / "QA_RECEIPT.json")
    if qa["status"] != "PASS":
        raise ValueError("QA required")
    for filename, expected in qa["code_sha256"].items():
        if checksum(ROOT / filename) != expected:
            raise ValueError("Code changed after QA")
    for key, expected in qa["qa_log_sha256"].items():
        if checksum(dest / "qa" / f"{key}.log") != expected:
            raise ValueError("QA log changed")
    for filename, expected in qa["replay_sha256"].items():
        if checksum(dest / filename) != expected:
            raise ValueError("Output changed after replay")
    verify_originals()
    save(
        path,
        {
            "name": name,
            "status": status,
            "parent": parent,
            "artifacts": dict(sorted(stage_artifacts(dest, code).items())),
            "QA": "PASS",
            "QA_tests": qa["tests"],
            "SECOND_FINANCIAL_BACKTEST_RAN": False,
            "trade_entry_allowed": False,
        },
    )
    print(
        "FROZEN",
        name,
        len(read(path)["artifacts"]),
        "artifacts; SHA256",
        checksum(path),
        flush=True,
    )
