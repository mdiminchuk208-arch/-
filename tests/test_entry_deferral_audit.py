"""An audit must not attribute the first withdrawal to a later READY update."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class EntryDeferralAuditTests(unittest.TestCase):
    def test_requalified_setup_keeps_first_ready_and_first_withdrawal(self):
        script = Path(__file__).resolve().parents[1] / "scripts/audit_entry_deferrals.py"
        spec = spec_from_file_location("entry_deferral_audit", script)
        assert spec is not None and spec.loader is not None
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        signal = dict(signal_id="same-setup", symbol="BTCUSDT", direction="LONG",
                      status="READY_FOR_VIRTUAL_ENTRY", entry_zone=dict(low=99, high=100),
                      optimal_entry=100, event_time="2026-01-01T00:05:00+00:00")
        later = dict(signal, event_time="2026-01-01T00:20:00+00:00")
        decisions = [
            dict(signal_id="same-setup", action="SETUP_READY", reason="READY"),
            dict(signal_id="same-setup", action="SETUP_WAITING",
                 reason="WAITING_FOR_AUTO_LEVELS|THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND",
                 time="2026-01-01T00:10:00+00:00"),
            dict(signal_id="same-setup", action="SETUP_READY", reason="READY"),
            dict(signal_id="same-setup", action="SETUP_INVALIDATED", reason="LATER_BOS"),
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, rows in (("signals", [signal, later]), ("decisions", decisions),
                               ("trades", [])):
                (root / f"{name}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows))
            result = module.audit(root)
        record = result["records"][0]
        self.assertEqual(record["ready_time"], signal["event_time"])
        self.assertEqual(record["latest_ready_time"], later["event_time"])
        self.assertEqual(record["ready_updates"], 2)
        self.assertLess(record["ready_time"], record["first_terminal"]["time"])
        self.assertEqual(record["terminal_reason"], "ENTRY_LEVEL_EVIDENCE_WITHDRAWN")
        self.assertEqual(record["first_terminal"]["reason"], decisions[1]["reason"])


if __name__ == "__main__":
    unittest.main()
