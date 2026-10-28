import unittest
from dataclasses import replace
from datetime import datetime, timezone

from crypto_bot.integration.ingestion import (
    ExistingEngineEvent,
    IngestionDecision,
    canonical_payload_sha256,
    compare_existing_event,
    prepare_engine_event,
)


NOW = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)


def envelope(payload=None):
    return {
        "event_id": "evt-1",
        "event_type": "crypto-bot.test.v1",
        "created_at": NOW.isoformat(),
        "payload": payload or {
            "event_id": "evt-1",
            "schema": "crypto-bot.test.v1",
            "trade_entry_allowed": False,
            "nested": {"b": 2, "a": 1},
        },
    }


def existing_from(prepared):
    return ExistingEngineEvent(
        event_id=prepared.event_id,
        event_type=prepared.event_type,
        source_created_at=prepared.source_created_at,
        payload=prepared.payload,
        payload_sha256=prepared.payload_sha256,
    )


class IntegrationIngestionTests(unittest.TestCase):
    def test_prepare_validates_and_hashes_canonical_payload(self):
        prepared = prepare_engine_event(envelope())
        self.assertEqual(prepared.event_id, "evt-1")
        self.assertEqual(prepared.event_type, "crypto-bot.test.v1")
        self.assertEqual(len(prepared.payload_sha256), 64)
        self.assertEqual(prepared.payload_sha256, canonical_payload_sha256(prepared.payload))

    def test_canonical_hash_is_key_order_independent(self):
        left = {"a": 1, "nested": {"x": 1, "y": 2}}
        right = {"nested": {"y": 2, "x": 1}, "a": 1}
        self.assertEqual(canonical_payload_sha256(left), canonical_payload_sha256(right))

    def test_absent_event_is_first_accepted(self):
        prepared = prepare_engine_event(envelope())
        result = compare_existing_event(prepared, None)
        self.assertEqual(result.decision, IngestionDecision.FIRST_ACCEPTED)
        self.assertEqual(result.reason, "EVENT_ID_NOT_PRESENT")

    def test_exact_existing_event_is_idempotent_duplicate(self):
        prepared = prepare_engine_event(envelope())
        result = compare_existing_event(prepared, existing_from(prepared))
        self.assertEqual(result.decision, IngestionDecision.EXACT_DUPLICATE)
        self.assertEqual(result.reason, "IMMUTABLE_EVENT_MATCH")

    def test_each_immutable_mismatch_is_collision(self):
        prepared = prepare_engine_event(envelope())
        base = existing_from(prepared)
        cases = (
            replace(base, event_type="different"),
            replace(base, source_created_at="2026-10-28T10:00:01+00:00"),
            replace(base, payload_sha256="0" * 64),
            replace(
                base,
                payload={
                    "event_id": "evt-1",
                    "schema": "crypto-bot.test.v1",
                    "trade_entry_allowed": False,
                    "nested": {"a": 999},
                },
            ),
        )
        for row in cases:
            with self.subTest(row=row):
                result = compare_existing_event(prepared, row)
                self.assertEqual(result.decision, IngestionDecision.COLLISION)
                self.assertTrue(result.reason.startswith("IMMUTABLE_MISMATCH:"))

    def test_wrong_existing_event_id_is_programming_error(self):
        prepared = prepare_engine_event(envelope())
        existing = replace(existing_from(prepared), event_id="other")
        with self.assertRaisesRegex(ValueError, "does not match"):
            compare_existing_event(prepared, existing)

    def test_execution_enablement_is_rejected_before_preparation(self):
        bad = envelope({
            "event_id": "evt-1",
            "schema": "crypto-bot.test.v1",
            "trade_entry_allowed": True,
        })
        with self.assertRaisesRegex(ValueError, "execution enablement"):
            prepare_engine_event(bad)


if __name__ == "__main__":
    unittest.main()
