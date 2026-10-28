import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.runtime.health import RuntimeHealthSnapshot, RuntimeHealthState
from crypto_bot.runtime.health_store import (
    RUNTIME_HEALTH_FILE_SCHEMA,
    check_runtime_health_file,
    read_runtime_health_file,
    write_runtime_health_file,
)


UTC = timezone.utc
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


def snapshot(state=RuntimeHealthState.HEALTHY_DIAGNOSTIC, observed_at=NOW):
    return RuntimeHealthSnapshot(
        observed_at=observed_at.isoformat(),
        state=state,
        reasons=(),
        mtf_ready=True,
        stale_timeframes=(),
        pending_outbox=0,
        diagnostic_pipeline_available=True,
        trade_entry_allowed=False,
    )


class HealthStoreTests(unittest.TestCase):
    def test_round_trip_preserves_fail_closed_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "health.json"
            write_runtime_health_file(snapshot(), path)
            restored = read_runtime_health_file(path)
        self.assertEqual(restored.schema, RUNTIME_HEALTH_FILE_SCHEMA)
        self.assertEqual(restored.health.state, RuntimeHealthState.HEALTHY_DIAGNOSTIC)
        self.assertFalse(restored.health.trade_entry_allowed)

    def test_fresh_healthy_or_degraded_file_is_responsive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "health.json"
            for state in (RuntimeHealthState.HEALTHY_DIAGNOSTIC, RuntimeHealthState.DEGRADED):
                write_runtime_health_file(snapshot(state), path)
                result = check_runtime_health_file(path, now=NOW + timedelta(seconds=10), max_age_seconds=30)
                self.assertTrue(result.ok)
                self.assertEqual(result.reason, "RUNTIME_RESPONSIVE")

    def test_safe_mode_and_starting_are_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "health.json"
            write_runtime_health_file(snapshot(RuntimeHealthState.SAFE_MODE), path)
            self.assertEqual(
                check_runtime_health_file(path, now=NOW, max_age_seconds=30).reason,
                "RUNTIME_SAFE_MODE",
            )
            write_runtime_health_file(snapshot(RuntimeHealthState.STARTING), path)
            self.assertEqual(
                check_runtime_health_file(path, now=NOW, max_age_seconds=30).reason,
                "RUNTIME_STARTING",
            )

    def test_stale_invalid_and_future_health_files_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "health.json"
            write_runtime_health_file(snapshot(observed_at=NOW), path)
            stale = check_runtime_health_file(path, now=NOW + timedelta(seconds=31), max_age_seconds=30)
            self.assertFalse(stale.ok)
            self.assertEqual(stale.reason, "HEALTH_FILE_STALE")

            future = check_runtime_health_file(path, now=NOW - timedelta(seconds=2), max_age_seconds=30)
            self.assertFalse(future.ok)
            self.assertEqual(future.reason, "HEALTH_CLOCK_IN_FUTURE")

            path.write_text("not-json", encoding="utf-8")
            invalid = check_runtime_health_file(path, now=NOW, max_age_seconds=30)
            self.assertFalse(invalid.ok)
            self.assertTrue(invalid.reason.startswith("HEALTH_FILE_INVALID:"))

    def test_health_file_cannot_enable_trade_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "health.json"
            payload = {
                "schema": RUNTIME_HEALTH_FILE_SCHEMA,
                "health": {
                    "observed_at": NOW.isoformat(),
                    "state": "HEALTHY_DIAGNOSTIC",
                    "reasons": [],
                    "mtf_ready": True,
                    "stale_timeframes": [],
                    "pending_outbox": 0,
                    "diagnostic_pipeline_available": True,
                    "trade_entry_allowed": True,
                },
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot grant trade entry"):
                read_runtime_health_file(path)


if __name__ == "__main__":
    unittest.main()
