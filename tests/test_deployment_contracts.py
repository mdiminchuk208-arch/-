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

    def test_compose_backend_delivery_is_opt_in_and_environment_configured(self):
        compose = (ROOT / "compose.live-diagnostic.yml").read_text(encoding="utf-8")
        self.assertIn("crypto-bot-outbox-delivery:", compose)
        self.assertIn("profiles:", compose)
        self.assertIn("- backend", compose)
        self.assertIn("deliver_engine_outbox.py", compose)
        self.assertIn("CRYPTO_BOT_BACKEND_ENDPOINT: ${CRYPTO_BOT_BACKEND_ENDPOINT:-}", compose)
        self.assertIn("CRYPTO_BOT_BACKEND_TOKEN: ${CRYPTO_BOT_BACKEND_TOKEN:-}", compose)
        self.assertIn("engine_outbox.sqlite3", compose)
        self.assertNotRegex(
            compose,
            re.compile(r"CRYPTO_BOT_BACKEND_ENDPOINT:\s*https?://", re.IGNORECASE),
        )

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

    def test_systemd_backend_delivery_uses_external_environment_file(self):
        unit = (ROOT / "deploy/systemd/crypto-bot-outbox-delivery.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("User=cryptobot", unit)
        self.assertIn("Group=cryptobot", unit)
        self.assertIn("EnvironmentFile=/etc/crypto-bot/backend-delivery.env", unit)
        self.assertIn("deliver_engine_outbox.py", unit)
        self.assertIn("engine_outbox.sqlite3", unit)
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("CapabilityBoundingSet=", unit)
        self.assertNotRegex(unit, re.compile(r"https?://", re.IGNORECASE))
        self.assertNotIn("CRYPTO_BOT_BACKEND_TOKEN=", unit)
        self.assertNotIn("OKX_API_KEY", unit)

    def test_runbook_keeps_live_execution_out_of_scope(self):
        runbook = (ROOT / "LIVE_DIAGNOSTIC_RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("trade_entry_allowed=false", runbook)
        self.assertIn("does **not** contain private OKX credentials", runbook)
        self.assertIn("LIVE trading", runbook)
        self.assertIn("public-market-data diagnostic runtime only", runbook)
        self.assertIn("Do not put real credentials", runbook)
        self.assertIn("--profile backend", runbook)


if __name__ == "__main__":
    unittest.main()
