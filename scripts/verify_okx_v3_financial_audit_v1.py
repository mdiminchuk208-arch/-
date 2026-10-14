"""Read-only externally pinned verification; never re-evaluates trades."""

from __future__ import annotations

import argparse
import json

from audit_okx_v3_financial_validation_v1 import AUDIT
from okx_qualification_data_v1 import ROOT
from okx_v3_compatibility_binding_v1 import digest
from okx_v3_compatibility_runner_v1 import verify_run_checkpoint


def verify(expected):
    path = AUDIT / "freeze_manifest.json"
    if not expected or digest(path) != expected:
        raise ValueError("EXTERNALLY_PINNED_FINANCIAL_FREEZE_REQUIRED")
    manifest = json.loads(path.read_text())
    names = {
        str(p.relative_to(ROOT)) for p in AUDIT.rglob("*") if p.is_file() and p != path
    }
    if names != {
        n
        for n in manifest["artifacts"]
        if n.startswith(str(AUDIT.relative_to(ROOT)) + "/")
    }:
        raise ValueError("AUDIT_NAMESPACE_CHANGED")
    for name, h in manifest["artifacts"].items():
        if digest(ROOT / name) != h:
            raise ValueError("FROZEN_BYTES_CHANGED_OR_RESTORE_REQUIRED")
    verify_run_checkpoint(manifest["run_checkpoint_sha256"])
    return {
        "verified_resume": True,
        "decision": manifest["decision"],
        "trade_re_evaluations": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-existing", action="store_true", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.expected_manifest_sha256), sort_keys=True))
