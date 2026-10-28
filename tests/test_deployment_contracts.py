import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentContractTests(unittest.TestCase):
    def test_postgres_engine_events_are_append_only_and_idempotent(self):
        sql = (ROOT / "deploy/postgres/001_engine_events.sql").read_text(encoding="utf-8")
        upper = sql.upper()
        self.assertIn("EVENT_ID TEXT PRIMARY KEY", upper)
        self.assertIn("PAYLOAD JSONB NOT NULL", upper)
        self.assertIn("PAYLOAD_SHA256 TEXT NOT NULL", upper)
        self.assertIn("BEFORE UPDATE ON ENGINE_EVENTS", upper)
        self.assertIn("BEFORE DELETE ON ENGINE_EVENTS", upper)
        self.assertIn("ENGINE_EVENT_RECEIPTS", upper)
        self.assertNotRegex(
            upper,
            re.compile(r"ON\s+CONFLICT\s*\(\s*EVENT_ID\s*\)\s+DO\s+UPDATE\s+SET\s+PAYLOAD"),
        )

    def test_docker_runtime_is_nonroot_readonly_and_has_healthcheck(self):
        dockerfile = (ROOT / "Dockerfile.live-diagnostic").read_text(encoding="utf-8")
        compose = (ROOT / "compose.live-diagnostic.yml").read_text(encoding="utf-8")
        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("check_live_diagnostic_health.py", dockerfile)
        self.assertIn("read_only: true", compose)
        self.assertIn("cap_drop:", compose)
        self.assertIn("- ALL", compose)
        self.assertIn("no-new-privileges:true", compose)
        self.assertIn("./data/history:/app/data/history:ro", compose)
        self.assertNotIn("OKX_API_KEY", dockerfile + compose)
        self.assertNotIn("OKX_SECRET", dockerfile + compose)

    def test_systemd_runtime_is_unprivileged_and_has_no_capabilities(self):
        unit = (ROOT / "deploy/systemd/crypto-bot-live-diagnostic.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("User=cryptobot", unit)
        self.assertIn("Group=cryptobot", unit)
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("CapabilityBoundingSet=", unit)
        self.assertIn("AmbientCapabilities=", unit)
        self.assertIn("ReadWritePaths=/var/lib/crypto-bot", unit)
        self.assertNotIn("OKX_API_KEY", unit)

    def test_runbook_keeps_live_execution_out_of_scope(self):
        runbook = (ROOT / "LIVE_DIAGNOSTIC_RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("trade_entry_allowed=false", runbook)
        self.assertIn("does **not** contain private OKX credentials", runbook)
        self.assertIn("LIVE trading", runbook)
        self.assertIn("public-market-data diagnostic runtime only", runbook)


if __name__ == "__main__":
    unittest.main()
