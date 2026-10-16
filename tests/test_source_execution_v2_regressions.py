from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_execution_v2 import SourcePoiTargetReference, select_source_fta
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def t(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def range_object() -> CausalSourceObject:
    return CausalSourceObject.formed(
        object_type=SourceObjectType.RANGE,
        symbol="BTC-USDT-SWAP",
        timeframe="4h",
        direction=Direction.SHORT.value,
        formation_at=t(0),
        known_at=t(1),
        identity_parts={"fixture": "range-not-generic-fta"},
        source_rule_ids=("RANGE_SOURCE_FIXTURE",),
        provenance="Stage-8 regression fixture: Range.direction is forming impulse semantics",
    )


class Stage8FtaRegressionTests(unittest.TestCase):
    def test_range_object_is_not_generic_fta_candidate(self):
        candidate = SourcePoiTargetReference(
            range_object(),
            zone_low=110,
            zone_high=120,
            source_kind="RANGE",
        )
        result = select_source_fta(
            direction=Direction.LONG,
            entry_price=100,
            trade_timeframe_minutes=15,
            candidates=(candidate,),
            decision_at=t(5),
        )
        self.assertEqual(result.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(result.reason, "WAIT_FIRST_TROUBLE_AREA")
        self.assertEqual(result.candidates, ())
        self.assertIsNone(result.first_contact_price)


if __name__ == "__main__":
    unittest.main()
