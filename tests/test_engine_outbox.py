import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.integration.outbox import SQLiteEngineOutbox


UTC = timezone.utc
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


class EngineOutboxTests(unittest.TestCase):
    def make(self, tmp):
        return SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3")

    def test_enqueue_is_idempotent_for_exact_same_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            payload = {"schema": "x", "value": 1}
            self.assertTrue(outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload=payload, created_at=NOW))
            self.assertFalse(outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload=payload, created_at=NOW))
            self.assertEqual(len(outbox.pending()), 1)

    def test_same_event_id_with_different_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload={"value": 1}, created_at=NOW)
            with self.assertRaises(ValueError):
                outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload={"value": 2}, created_at=NOW)

    def test_pending_is_ordered_and_delivery_ack_removes_from_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            outbox.enqueue(event_id="evt-b", event_type="OBJECT", payload={"v": 2}, created_at=NOW + timedelta(seconds=1))
            outbox.enqueue(event_id="evt-a", event_type="OBJECT", payload={"v": 1}, created_at=NOW)
            self.assertEqual([row.event_id for row in outbox.pending()], ["evt-a", "evt-b"])
            delivered = outbox.mark_delivered("evt-a", delivered_at=NOW + timedelta(seconds=2))
            self.assertIsNotNone(delivered.delivered_at)
            self.assertEqual([row.event_id for row in outbox.pending()], ["evt-b"])

    def test_failed_delivery_attempt_is_durable_and_retryable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "outbox.sqlite3"
            outbox = SQLiteEngineOutbox(path)
            outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload={"v": 1}, created_at=NOW)
            first = outbox.mark_attempt("evt-1", error="backend unavailable")
            self.assertEqual(first.delivery_attempts, 1)
            self.assertEqual(first.last_error, "backend unavailable")

            restarted = SQLiteEngineOutbox(path)
            pending = restarted.pending()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].delivery_attempts, 1)
            second = restarted.mark_attempt("evt-1")
            self.assertEqual(second.delivery_attempts, 2)
            self.assertIsNone(second.last_error)

    def test_delivery_ack_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload={"v": 1}, created_at=NOW)
            first = outbox.mark_delivered("evt-1", delivered_at=NOW + timedelta(seconds=1))
            second = outbox.mark_delivered("evt-1", delivered_at=NOW + timedelta(seconds=2))
            self.assertEqual(first.delivered_at, second.delivered_at)

    def test_delivery_before_creation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            outbox.enqueue(event_id="evt-1", event_type="OBJECT", payload={"v": 1}, created_at=NOW)
            with self.assertRaises(ValueError):
                outbox.mark_delivered("evt-1", delivered_at=NOW - timedelta(seconds=1))

    def test_unknown_event_operations_raise_key_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            with self.assertRaises(KeyError):
                outbox.get("missing")
            with self.assertRaises(KeyError):
                outbox.mark_attempt("missing")
            with self.assertRaises(KeyError):
                outbox.mark_delivered("missing", delivered_at=NOW)

    def test_naive_timestamps_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make(tmp)
            with self.assertRaises(ValueError):
                outbox.enqueue(
                    event_id="evt-1",
                    event_type="OBJECT",
                    payload={"v": 1},
                    created_at=datetime(2026, 10, 28, 10, 0),
                )


if __name__ == "__main__":
    unittest.main()
