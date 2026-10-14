"""Publish large audit JSON losslessly as gzip; restore exact original bytes."""

from __future__ import annotations

import argparse
import gzip
import json
from hashlib import sha256

from audit_okx_v3_financial_validation_v1 import AUDIT
from okx_qualification_data_v1 import ROOT, save
from okx_v3_compatibility_runner_v1 import OUT, verify_run_checkpoint

MANIFEST = AUDIT / "CATALOG_AUDIT_STORAGE.json"
NAMES = ("BTC-USDT-SWAP.catalog_audit.json", "ETH-USDT-SWAP.catalog_audit.json")


def pack(expected):
    verify_run_checkpoint(expected)
    entries = {}
    for name in NAMES:
        source = OUT / name
        data = source.read_bytes()
        target = AUDIT / "packed" / (name + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = gzip.compress(data, mtime=0)
        if target.exists() and target.read_bytes() != payload:
            raise ValueError("EXISTING_PACKED_ARTIFACT_CHANGED")
        target.write_bytes(payload)
        entries[str(source.relative_to(ROOT))] = {
            "raw_sha256": sha256(data).hexdigest(),
            "raw_bytes": len(data),
            "packed_path": str(target.relative_to(ROOT)),
            "packed_sha256": sha256(payload).hexdigest(),
            "packed_bytes": len(payload),
        }
        if gzip.decompress(payload) != data:
            raise ValueError("LOSSLESS_ROUNDTRIP_REQUIRED")
    result = {
        "entries": entries,
        "original_raw_files_retained_in_workspace": True,
        "run_checkpoint_sha256": expected,
        "policy_or_financial_result_changed": False,
    }
    if MANIFEST.exists() and json.loads(MANIFEST.read_text()) != result:
        raise ValueError("EXISTING_PACKING_MANIFEST_CHANGED")
    save(MANIFEST, result)
    return {"lossless_packing": "PASS", "files": len(entries)}


def restore():
    manifest = json.loads(MANIFEST.read_text())
    expected = {str((OUT / name).relative_to(ROOT)) for name in NAMES}
    if set(manifest["entries"]) != expected:
        raise ValueError("ONLY_TWO_SCOPED_CATALOG_AUDITS_ALLOWED")
    for name, record in manifest["entries"].items():
        packed = ROOT / record["packed_path"]
        if not packed.resolve().is_relative_to(AUDIT / "packed"):
            raise ValueError("PACKED_PATH_OUTSIDE_NAMESPACE")
        payload = packed.read_bytes()
        if sha256(payload).hexdigest() != record["packed_sha256"]:
            raise ValueError("PACKED_HASH_CHANGED")
        if record["raw_bytes"] > 1024**3:
            raise ValueError("RAW_LENGTH_BOUND")
        data = gzip.decompress(payload)
        if (
            len(data) != record["raw_bytes"]
            or sha256(data).hexdigest() != record["raw_sha256"]
        ):
            raise ValueError("RAW_HASH_OR_LENGTH_CHANGED")
        target = ROOT / name
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError("REFUSE_OVERWRITE_CHANGED_RAW_ARTIFACT")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".restore.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
    verify_run_checkpoint(manifest["run_checkpoint_sha256"])
    return {"exact_restore_and_checkpoint_verification": "PASS"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--pack", action="store_true")
    actions.add_argument("--restore", action="store_true")
    parser.add_argument("--expected-run-checkpoint-sha256")
    args = parser.parse_args()
    print(
        json.dumps(
            pack(args.expected_run_checkpoint_sha256) if args.pack else restore(),
            sort_keys=True,
        )
    )
