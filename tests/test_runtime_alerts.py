import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.runtime.alerts import AlertTransition, SQLiteOperationalAlertJournal
from crypto_bot.runtime.health import RuntimeHealthSnapshot, RuntimeHealthState


UTC = timezone.utc
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


def health(
    *,
    state=RuntimeHealthState.HEALTHY_DIAGNOSTIC,
    reasons=(),
    observed_at=NOW,
):
    return RuntimeHealthSnapshot(
        observed_at=observed_at.isoformat(),
        state=state,
        reasons=tuple(reasons),
        mtf_ready=True,
        stale_timeframes=tuple(
            reason.removeprefix("MARKET_DATA_STALE_")
            for reason in reasons
            if reason.startswith("MARKET_DATA_STALE_")
        ),
        pending_outbox=0,
        diagnostic_pipeline_available=True,
        trade_entry_allowed=False,
    )


class OperationalAlertTests(unittest.TestCase):
    def make(self, tmp):
        return SQLiteOperationalAlertJournal(Path(tmp) / "alerts.sqlite3")

    def test_healthy_and_starting_do_not_open_incidents(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self.make(tmp)
            self.assertEqual(journal.reconcile(health()), ())
            starting = health(
                state=RuntimeHealthState.STARTING,
                reasons=("MTF_HISTORY_NOT_READY", "MTF_MISSING_15"),
            )
            self.assertEqual(journal.reconcile(starting), ())
            self.assertEqual(journal.active(), ())

    def test_safe_mode_opens_state_and_stale_reason_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self.make(tmp)
            snapshot = health(
                state=RuntimeHealthState.SAFE_MODE,
                reasons=("MARKET_DATA_STALE_5",),
            )
            first = journal.reconcile(snapshot)
            self.assertEqual({row.code for row in first}, {"RUNTIME_SAFE_MODE", "MARKET_DATA_STALE_5"})
            self.assertTrue(all(row.transition == AlertTransition.OPEN for row in first))
            self.assertTrue(all(not row.trade_entry_allowed for row in first))

            repeated = journal.reconcile(
                health(
                    state=RuntimeHealthState.SAFE_MODE,
                    reasons=("MARKET_DATA_STALE_5",),
                    observed_at=NOW + timedelta(seconds=30),
                )
            )
            self.assertEqual(repeated, ())
            self.assertEqual(len(journal.events()), 2)
            self.assertEqual(len(journal.active()), 2)

    def test_recovery_emits_one_resolved_event_per_active_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self.make(tmp)
            journal.reconcile(
                health(
                    state=RuntimeHealthState.DEGRADED,
                    reasons=("ENGINE_OUTBOX_BACKLOG",),
                )
            )
            resolved = journal.reconcile(
                health(observed_at=NOW + timedelta(minutes=1))
            )
            self.assertEqual(
                {row.code for row in resolved},
                {"RUNTIME_DEGRADED", "ENGINE_OUTBOX_BACKLOG"},
            )
            self.assertTrue(all(row.transition == AlertTransition.RESOLVED for row in resolved))
            self.assertEqual(journal.active(), ())
            self.assertEqual(len(journal.events()), 4)

    def test_reason_change_resolves_old_and_opens_new_without_reopening_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self.make(tmp)
            journal.reconcile(
                health(
                    state=RuntimeHealthState.DEGRADED,
                    reasons=("ENGINE_OUTBOX_BACKLOG",),
                )
            )
            changed = journal.reconcile(
                health(
                    state=RuntimeHealthState.DEGRADED,
                    reasons=("DIAGNOSTIC_PIPELINE_UNAVAILABLE",),
                    observed_at=NOW + timedelta(minutes=1),
                )
            )
            by_code = {row.code: row.transition for row in changed}
            self.assertEqual(by_code["ENGINE_OUTBOX_BACKLOG"], AlertTransition.RESOLVED)
            self.assertEqual(by_code["DIAGNOSTIC_PIPELINE_UNAVAILABLE"], AlertTransition.OPEN)
            self.assertNotIn("RUNTIME_DEGRADED", by_code)

    def test_restart_keeps_active_episode_and_does_not_spam_duplicate_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alerts.sqlite3"
            journal = SQLiteOperationalAlertJournal(path)
            snapshot = health(
                state=RuntimeHealthState.SAFE_MODE,
                reasons=("MARKET_DATA_STALE_15",),
            )
            first = journal.reconcile(snapshot)
            episode_ids = {row.code: row.alert_episode_id for row in first}

            restarted = SQLiteOperationalAlertJournal(path)
            repeated = restarted.reconcile(
                health(
                    state=RuntimeHealthState.SAFE_MODE,
                    reasons=("MARKET_DATA_STALE_15",),
                    observed_at=NOW + timedelta(minutes=1),
                )
            )
            self.assertEqual(repeated, ())
            active = {row.code: row.alert_episode_id for row in restarted.active()}
            self.assertEqual(active, episode_ids)

    def test_new_episode_after_resolution_gets_new_episode_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self.make(tmp)
            incident = health(
                state=RuntimeHealthState.DEGRADED,
                reasons=("ENGINE_OUTBOX_BACKLOG",),
            )
            first = journal.reconcile(incident)
            first_id = next(row.alert_episode_id for row in first if row.code == "ENGINE_OUTBOX_BACKLOG")
            journal.reconcile(health(observed_at=NOW + timedelta(minutes=1)))
            reopened = journal.reconcile(
                health(
                    state=RuntimeHealthState.DEGRADED,
                    reasons=("ENGINE_OUTBOX_BACKLOG",),
                    observed_at=NOW + timedelta(minutes=2),
                )
            )
            second_id = next(row.alert_episode_id for row in reopened if row.code == "ENGINE_OUTBOX_BACKLOG")
            self.assertNotEqual(first_id, second_id)

    def test_execution_permission_in_health_snapshot_is_rejected(self):
        bad = RuntimeHealthSnapshot(
            observed_at=NOW.isoformat(),
            state=RuntimeHealthState.DEGRADED,
            reasons=("ENGINE_OUTBOX_BACKLOG",),
            mtf_ready=True,
            stale_timeframes=(),
            pending_outbox=1,
            diagnostic_pipeline_available=True,
            trade_entry_allowed=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "cannot grant trade entry"):
                self.make(tmp).reconcile(bad)


if __name__ == "__main__":
    unittest.main()
