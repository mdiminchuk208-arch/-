"""Evidence integrity and STOP-freeze boundaries, never financial evaluation."""

import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_okx_stage_a_v1 as audit


class IntegrityTests(unittest.TestCase):
    def source(
        self, root, *, url="https://www.okx.com/api/v5/public/instruments", auth=False
    ):
        dest = root / "docs/stage"
        folder = dest / "evidence"
        folder.mkdir(parents=True)
        raw = folder / "sample.body"
        raw.write_bytes(b"official sample")
        receipt = {
            "raw_path": str(raw.relative_to(root)),
            "raw_sha256": sha256(raw.read_bytes()).hexdigest(),
            "raw_bytes": len(raw.read_bytes()),
            "requested_url": url,
            "method": "GET",
            "request_auth": auth,
        }
        (folder / "sample.receipt.json").write_text(json.dumps(receipt))
        return dest, raw

    def test_requested_url_schema_and_hash_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest, _ = self.source(root)
            with patch.object(audit, "ROOT", root), patch.object(audit, "DEST", dest):
                self.assertEqual(audit.source_receipts(), 1)

    def test_mutated_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest, raw = self.source(root)
            raw.write_bytes(b"tampered")
            with (
                patch.object(audit, "ROOT", root),
                patch.object(audit, "DEST", dest),
                self.assertRaisesRegex(ValueError, "HASH_OR_LENGTH"),
            ):
                audit.source_receipts()

    def test_nonofficial_host_and_authenticated_capture_rejected(self):
        for url, auth in [
            ("https://okx.com.evil.test/data", False),
            ("https://www.okx.com/public", True),
        ]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                dest, _ = self.source(root, url=url, auth=auth)
                with (
                    patch.object(audit, "ROOT", root),
                    patch.object(audit, "DEST", dest),
                    self.assertRaises(ValueError),
                ):
                    audit.source_receipts()

    def test_resume_requires_external_pin(self):
        with self.assertRaisesRegex(ValueError, "EXTERNALLY_PINNED"):
            audit.resume(None)

    def test_frozen_namespace_addition_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "docs/stage"
            dest.mkdir(parents=True)
            item = dest / "source.txt"
            item.write_text("source")
            manifest = dest / "freeze_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "decision": "STOP",
                        "artifacts": {str(item.relative_to(root)): audit.digest(item)},
                    }
                )
            )
            expected = audit.digest(manifest)
            with patch.object(audit, "ROOT", root), patch.object(audit, "DEST", dest):
                self.assertEqual(audit.resume(expected)["decision"], "STOP")
                (dest / "unregistered.txt").write_text("extra")
                with self.assertRaisesRegex(ValueError, "MEMBERSHIP"):
                    audit.resume(expected)

    def test_financial_authorization_cannot_be_sealed_as_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "STAGE_A_READINESS.json").write_text(
                json.dumps(
                    {
                        "Stage_B_authorized": True,
                        "decision": "MACHINE_STRATEGY_V3_QUALIFICATION_STOP",
                    }
                )
            )
            (dest / "QA_RECEIPT.json").write_text('{"status":"PASS"}')
            with (
                patch.object(audit, "DEST", dest),
                self.assertRaisesRegex(ValueError, "ONLY_QA_VERIFIED"),
            ):
                audit.freeze_stop()


if __name__ == "__main__":
    unittest.main()
