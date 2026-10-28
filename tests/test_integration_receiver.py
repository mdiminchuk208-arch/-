import unittest
from datetime import datetime, timezone

from crypto_bot.integration.receiver import validate_engine_event_envelope


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
        },
    }


class IntegrationReceiverTests(unittest.TestCase):
    def test_valid_envelope_round_trips(self):
        validated = validate_engine_event_envelope(envelope())
        self.assertEqual(validated.event_id, "evt-1")
        self.assertEqual(validated.event_type, "crypto-bot.test.v1")
        self.assertFalse(validated.payload["trade_entry_allowed"])

    def test_top_level_execution_enablement_is_rejected(self):
        bad = envelope({
            "event_id": "evt-1",
            "schema": "crypto-bot.test.v1",
            "trade_entry_allowed": True,
        })
        with self.assertRaisesRegex(ValueError, "execution enablement"):
            validate_engine_event_envelope(bad)

    def test_nested_execution_enablement_is_rejected(self):
        bad = envelope({
            "event_id": "evt-1",
            "schema": "crypto-bot.test.v1",
            "artifact": {
                "trade_entry_allowed": True,
            },
        })
        with self.assertRaisesRegex(ValueError, "payload.artifact.trade_entry_allowed"):
            validate_engine_event_envelope(bad)

    def test_nested_lists_are_checked_recursively(self):
        bad = envelope({
            "event_id": "evt-1",
            "schema": "crypto-bot.test.v1",
            "items": [{"trade_entry_allowed": False}, {"trade_entry_allowed": True}],
        })
        with self.assertRaisesRegex(ValueError, r"payload.items\[1\].trade_entry_allowed"):
            validate_engine_event_envelope(bad)

    def test_payload_identity_must_match_envelope_when_present(self):
        with self.assertRaisesRegex(ValueError, "payload event_id"):
            validate_engine_event_envelope(envelope({
                "event_id": "different",
                "schema": "crypto-bot.test.v1",
            }))
        with self.assertRaisesRegex(ValueError, "payload schema"):
            validate_engine_event_envelope(envelope({
                "event_id": "evt-1",
                "schema": "different-schema",
            }))

    def test_missing_extra_nonobject_and_naive_timestamp_are_rejected(self):
        missing = envelope()
        del missing["payload"]
        with self.assertRaisesRegex(ValueError, "missing fields"):
            validate_engine_event_envelope(missing)

        extra = envelope()
        extra["unexpected"] = 1
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            validate_engine_event_envelope(extra)

        wrong_payload = envelope()
        wrong_payload["payload"] = []
        with self.assertRaisesRegex(ValueError, "JSON object"):
            validate_engine_event_envelope(wrong_payload)

        naive = envelope()
        naive["created_at"] = "2026-10-28T10:00:00"
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            validate_engine_event_envelope(naive)


if __name__ == "__main__":
    unittest.main()
