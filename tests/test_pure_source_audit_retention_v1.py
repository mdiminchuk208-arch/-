import json
import shutil
import tempfile
import unittest
from pathlib import Path

from crypto_bot.strategy.pure_source_audit_retention_v1 import (
    validate_retained_handoffs,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path("docs/pure_source_stage19_ledger_v1")


class AuditRetentionTests(unittest.TestCase):
    def test_all_claimed_handoffs_are_retained_with_original_hashes(self):
        self.assertEqual(len(validate_retained_handoffs(ROOT, ROOT / LEDGER)), 4)

    def test_missing_changed_or_temporary_only_retention_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / LEDGER
            shutil.copytree(ROOT / LEDGER, ledger)
            manifest = ledger / "audit/HANDOFF_RETENTION.json"
            original = json.loads(manifest.read_text())
            for name, value in [
                ("repository_path", "/tmp/pretend-retained.json"),
                ("sha256", "0" * 64),
                ("bytes", 0),
            ]:
                changed = json.loads(json.dumps(original))
                changed["handoffs"][0][name] = value
                manifest.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    validate_retained_handoffs(root, ledger)
            manifest.write_text(json.dumps(original))
            retained = root / original["handoffs"][0]["repository_path"]
            retained.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "bytes differ"):
                validate_retained_handoffs(root, ledger)
            retained.unlink()
            with self.assertRaisesRegex(ValueError, "must exist"):
                validate_retained_handoffs(root, ledger)
