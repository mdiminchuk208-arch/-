from __future__ import annotations

import unittest
from decimal import Decimal

from source_strategy_v1_fta_resolver import known_prefix_contextual_inventory, nearest_contextual_fta


class FakeIndex:
    def __init__(self, objects):
        self.by_id = {obj["id"]: obj for obj in objects}


def poi(identifier, kind, tf, direction, low, high, known_at, validated=True):
    return {
        "id": identifier,
        "kind": kind,
        "tf": tf,
        "known_at": known_at,
        "completed_at": known_at,
        "source_validated": validated,
        "payload": {"direction": direction, "low": str(low), "high": str(high)},
        "evidence": "synthetic source POI",
    }


class TestSourceStrategyV1FtaResolver(unittest.TestCase):
    def test_long_selects_nearest_opposing_poi_ahead(self):
        indexes = {
            15: FakeIndex([
                poi("short-near", "FVG", 15, "SHORT", 110, 115, 1000),
                poi("long-own", "FVG", 15, "LONG", 105, 108, 1000),
            ]),
            60: FakeIndex([poi("short-far", "OB", 60, "SHORT", 125, 130, 900)]),
        }
        inventory = known_prefix_contextual_inventory(indexes, "LONG", 100, 2000)
        self.assertEqual([row["id"] for row in inventory["contextual_pois"]], ["short-near", "short-far"])
        target = nearest_contextual_fta(inventory)
        self.assertEqual(target["price"], "110")
        self.assertEqual(target["poi_ids"], ["short-near"])

    def test_short_selects_nearest_opposing_poi_below(self):
        indexes = {
            15: FakeIndex([poi("long-near", "FVG", 15, "LONG", 85, 90, 1000)]),
            240: FakeIndex([poi("long-far", "OB", 240, "LONG", 70, 75, 900)]),
        }
        target = nearest_contextual_fta(known_prefix_contextual_inventory(indexes, "SHORT", 100, 2000))
        self.assertEqual(target["price"], "90")
        self.assertEqual(target["poi_ids"], ["long-near"])

    def test_future_consumed_unvalidated_and_same_direction_are_excluded(self):
        indexes = {
            15: FakeIndex([
                poi("future", "FVG", 15, "SHORT", 105, 106, 3000),
                poi("consumed", "FVG", 15, "SHORT", 107, 108, 1000),
                poi("unvalidated", "OB", 15, "SHORT", 109, 110, 1000, validated=False),
                poi("same", "FVG", 15, "LONG", 111, 112, 1000),
            ])
        }
        inventory = known_prefix_contextual_inventory(indexes, "LONG", 100, 2000, consumed_ids=["consumed"])
        self.assertEqual(inventory["contextual_pois"], [])
        self.assertIsNone(nearest_contextual_fta(inventory))

    def test_tied_same_price_preserves_all_ids(self):
        indexes = {
            15: FakeIndex([poi("a", "FVG", 15, "SHORT", 110, 111, 1000)]),
            60: FakeIndex([poi("b", "OB", 60, "SHORT", 110, 112, 1000)]),
        }
        target = nearest_contextual_fta(known_prefix_contextual_inventory(indexes, "LONG", Decimal("100"), 2000))
        self.assertEqual(target["price"], "110")
        self.assertEqual(set(target["poi_ids"]), {"a", "b"})
        self.assertFalse(target["trade_entry_allowed"])


if __name__ == "__main__":
    unittest.main()
