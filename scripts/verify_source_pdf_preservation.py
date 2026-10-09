"""Verify retained Git blobs and the frozen baseline without changing artifacts."""
from __future__ import annotations

from collections import Counter
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[1]
OLD = "74a6f8de22511653943a78399fb52638a1dc9215"
PDF_STAGE = "cbcd30a"


def retained(commit: str, prefixes: tuple[str, ...], exclude: tuple[str, ...] = ()):
    entries = subprocess.check_output(["git", "ls-tree", "-rz", commit], cwd=REPO)
    counts: Counter[str] = Counter()
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        meta, raw_name = entry.split(b"\t", 1)
        name = raw_name.decode()
        if not name.startswith(prefixes) or name in exclude:
            continue
        mode, kind, expected = meta.split()
        assert kind == b"blob" and mode in (b"100644", b"100755"), name
        content = (REPO / name).read_bytes()
        actual = sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        assert actual == expected.decode(), (commit, name)
        counts[name.split("/", 1)[0]] += 1
    return {"unchanged_git_blobs": sum(counts.values()), "by_directory": dict(counts)}


def verify():
    old = retained(OLD, ("config/", "data/", "scripts/", "src/", "tests/"))
    assert old["unchanged_git_blobs"] == 15069
    pdf = retained(PDF_STAGE, ("config/", "data/", "scripts/", "src/", "tests/"),
                   ("scripts/verify_source_pdf_native_evidence.py",))
    lock = json.loads((REPO / "data/reports/robustness_research/baseline_lock.json").read_text())
    for name, expected in lock["code_hashes"].items():
        original = subprocess.check_output(["git", "show", lock["baseline_commit"] + ":" + name], cwd=REPO)
        assert sha256(original).hexdigest() == expected, name
    archives = (
        (OLD, "SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md", "data/reports/source_cases_74a6f8d_intermediate/report.md"),
        ("63ab3ae", "SOURCE_RECONSTRUCTION_2026_10_09.md", "data/reports/source_pdf_closed_htf_intermediate/SOURCE_RECONSTRUCTION_2026_10_09.md"),
    )
    for commit, name, copy in archives:
        original = subprocess.check_output(["git", "show", commit + ":" + name], cwd=REPO)
        assert (REPO / copy).read_bytes() == original, copy
    return {"status": "PASS", "retained_74a6f8d": old, "retained_cbcd30a": pdf,
            "permitted_modified_new_helper": "scripts/verify_source_pdf_native_evidence.py",
            "baseline_registered_git_hashes_verified": len(lock["code_hashes"]),
            "baseline_commit": lock["baseline_commit"], "old_reports_byte_exact": True,
            "canonical_source_config_tests_unchanged_since_74a6f8d": True,
            "trade_entry_allowed": False}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
