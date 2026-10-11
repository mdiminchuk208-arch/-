"""Commit only changed frozen artifacts, preserving shared-code and parent hashes."""

from __future__ import annotations

import argparse
import subprocess
from hashlib import sha256
from pathlib import Path

from machine_strategy_research_io import verify_machine
from original_v1_1_financial_data import ROOT, checksum


def commit(directory, message):
    directory = directory.resolve()
    verify_machine(directory)
    import json

    path = directory / "freeze_manifest.json"
    manifest = json.loads(path.read_text())
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != "medium-term-source-research"
    ):
        raise ValueError("Research branch required")
    expected = {}
    for name, h in (
        manifest["artifacts"].items()
        | {str(path.relative_to(ROOT)): checksum(path)}.items()
    ):
        previous = subprocess.run(
            ["git", "show", "HEAD:" + name], cwd=ROOT, capture_output=True, check=False
        )
        if previous.returncode or sha256(previous.stdout).hexdigest() != h:
            expected[name] = h
    subprocess.run(["git", "add", "--", *sorted(expected)], cwd=ROOT, check=True)
    staged = set(
        subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")[:-1]
    )
    if staged != set(expected):
        raise ValueError("Unexpected changed staging scope")
    for name, h in expected.items():
        if (
            sha256(
                subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
            ).hexdigest()
            != h
        ):
            raise ValueError("Staged bytes differ")
    subprocess.run(
        ["git", "diff", "--cached", "--check", "--", ".", ":(exclude)**/provenance/*"],
        cwd=ROOT,
        check=True,
    )
    print(
        subprocess.check_output(
            ["git", "diff", "--cached", "--stat"], cwd=ROOT, text=True
        ).splitlines()[-1],
        flush=True,
    )
    r = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    print(r.stdout.splitlines()[0], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("message")
    a = p.parse_args()
    commit(a.directory, a.message)
