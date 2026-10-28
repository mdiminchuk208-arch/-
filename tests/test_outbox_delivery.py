import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_bot.integration.delivery import (
    DeliveryResponse,
    HttpDeliveryConfig,
    deliver_pending,
    deliver_record,
)
from crypto_bot.integration.outbox import SQLiteEngineOutbox


UTC = timezone.utc
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)


class OutboxDeliveryTests(unittest.TestCase):
    def make_outbox(self, tmp):
        return SQLiteEngineOutbox(Path(tmp) / "outbox.sqlite3")

    def enqueue(self, outbox, event_id="evt-1", created_at=NOW):
        outbox.enqueue(
            event_id=event_id,
            event_type="crypto-bot.test.v1",
            payload={"trade_entry_allowed": False, "value": event_id},
            created_at=created_at,
        )
        return outbox.get(event_id)

    def config(self):
        return HttpDeliveryConfig(endpoint="https://backend.example.test/events")

    def test_https_is_required_except_explicit_localhost_development(self):
        with self.assertRaisesRegex(ValueError, "plain HTTP"):
            HttpDeliveryConfig(endpoint="http://backend.example.test/events")
        local = HttpDeliveryConfig(
            endpoint="http://127.0.0.1:8080/events",
            allow_plain_http_localhost=True,
        )
        self.assertEqual(local.endpoint, "http://127.0.0.1:8080/events")

    def test_success_sends_exact_envelope_and_marks_delivered(self):
        captured = {}

        def transport(url, body, headers, timeout):
            captured.update(
                url=url,
                body=json.loads(body.decode("utf-8")),
                headers=dict(headers),
                timeout=timeout,
            )
            return DeliveryResponse(202, b"accepted")

        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make_outbox(tmp)
            record = self.enqueue(outbox)
            result = deliver_record(
                outbox,
                record,
                config=self.config(),
                transport=transport,
                delivered_at=NOW + timedelta(seconds=1),
            )
            stored = outbox.get("evt-1")

        self.assertTrue(result.delivered)
        self.assertEqual(result.status_code, 202)
        self.assertEqual(result.delivery_attempts, 1)
        self.assertIsNotNone(stored.delivered_at)
        self.assertEqual(captured["body"]["event_id"], "evt-1")
        self.assertEqual(captured["body"]["payload"]["trade_entry_allowed"], False)
        self.assertEqual(captured["headers"]["Idempotency-Key"], "evt-1")
        self.assertEqual(captured["headers"]["X-Crypto-Bot-Event-Type"], "crypto-bot.test.v1")

    def test_non_2xx_is_retryable_and_not_acknowledged(self):
        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make_outbox(tmp)
            record = self.enqueue(outbox)
            result = deliver_record(
                outbox,
                record,
                config=self.config(),
                transport=lambda *args: DeliveryResponse(503, b"unavailable"),
            )
            stored = outbox.get("evt-1")

        self.assertFalse(result.delivered)
        self.assertEqual(result.error, "HTTP_STATUS_503")
        self.assertEqual(stored.delivery_attempts, 1)
        self.assertIsNone(stored.delivered_at)
        self.assertEqual(stored.last_error, "HTTP_STATUS_503")

    def test_transport_error_is_durable_without_ack(self):
        def transport(*args):
            raise ConnectionError("offline")

        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make_outbox(tmp)
            record = self.enqueue(outbox)
            result = deliver_record(
                outbox,
                record,
                config=self.config(),
                transport=transport,
            )
            stored = outbox.get("evt-1")

        self.assertFalse(result.delivered)
        self.assertIsNone(result.status_code)
        self.assertTrue(result.error.startswith("TRANSPORT_ERROR:ConnectionError:"))
        self.assertEqual(stored.delivery_attempts, 1)
        self.assertIsNone(stored.delivered_at)

    def test_pending_batch_preserves_order_and_stops_on_first_failure(self):
        calls = []

        def transport(url, body, headers, timeout):
            event_id = json.loads(body.decode("utf-8"))["event_id"]
            calls.append(event_id)
            if event_id == "evt-1":
                return DeliveryResponse(500)
            return DeliveryResponse(200)

        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make_outbox(tmp)
            self.enqueue(outbox, "evt-1", NOW)
            self.enqueue(outbox, "evt-2", NOW + timedelta(seconds=1))
            results = deliver_pending(
                outbox,
                config=self.config(),
                limit=10,
                transport=transport,
            )

        self.assertEqual(calls, ["evt-1"])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].delivered)

    def test_bearer_auth_is_added_only_when_explicit(self):
        captured = {}

        def transport(url, body, headers, timeout):
            captured.update(headers)
            return DeliveryResponse(200)

        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make_outbox(tmp)
            record = self.enqueue(outbox)
            config = HttpDeliveryConfig(
                endpoint="https://backend.example.test/events",
                bearer_token="secret-token",
            )
            deliver_record(
                outbox,
                record,
                config=config,
                transport=transport,
                delivered_at=NOW + timedelta(seconds=1),
            )
        self.assertEqual(captured["Authorization"], "Bearer secret-token")

    def test_already_delivered_record_is_not_sent_again(self):
        calls = []

        def transport(*args):
            calls.append(args)
            return DeliveryResponse(200)

        with tempfile.TemporaryDirectory() as tmp:
            outbox = self.make_outbox(tmp)
            record = self.enqueue(outbox)
            outbox.mark_delivered("evt-1", delivered_at=NOW + timedelta(seconds=1))
            delivered_record = outbox.get("evt-1")
            result = deliver_record(
                outbox,
                delivered_record,
                config=self.config(),
                transport=transport,
            )
        self.assertTrue(result.delivered)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
