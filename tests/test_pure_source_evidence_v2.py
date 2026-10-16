from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle
from crypto_bot.strategy.pure_source_evidence_v2 import build_structure_liquidity_snapshot
from crypto_bot.strategy.source_structure_liquidity_v2 import (
    LiquidityLocation,
    confirmed_source_swings,
    latest_structure_leg,
    structural_liquidity,
)


BASE = datetime(2026, 2, 1, tzinfo=timezone.utc)


def c(i: int, o: float, h: float, l: float, cl: float) -> Candle:
    start = BASE + timedelta(minutes=i)
    return Candle(start, start + timedelta(minutes=1), o, h, l, cl, True)


def bullish_sequence() -> list[Candle]:
    return [
        c(0, 10, 11, 9.5, 10.2),
        c(1, 10.2, 10.5, 8, 9),
        c(2, 9, 11, 8.5, 10.4),
        c(3, 10.4, 12, 9, 11.3),
        c(4, 11.3, 11.5, 9.5, 10.2),
        c(5, 10.2, 11, 9, 9.6),
        c(6, 9.6, 12, 9.3, 11.2),
        c(7, 11.2, 13, 10, 12.6),
        c(8, 12.6, 12.7, 10.5, 11.6),
    ]


class PureSourceEvidenceV2Tests(unittest.TestCase):
    def test_empty_prefix_has_no_evidence(self):
        snapshot = build_structure_liquidity_snapshot([], symbol="BTC-USDT-SWAP", timeframe="1m")
        self.assertIsNone(snapshot.decision_at)
        self.assertEqual(snapshot.swings, ())
        self.assertEqual(snapshot.liquidity, ())
        self.assertIsNone(snapshot.latest_formed_leg)
        self.assertIsNone(snapshot.structure_object)
        self.assertFalse(snapshot.bos_on_last_close)

    def test_snapshot_builds_structure_object_from_source_swings(self):
        snapshot = build_structure_liquidity_snapshot(
            bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m"
        )
        self.assertIsNotNone(snapshot.latest_formed_leg)
        self.assertIsNotNone(snapshot.structure_object)
        assert snapshot.latest_formed_leg is not None
        assert snapshot.structure_object is not None
        self.assertEqual(snapshot.latest_formed_leg.direction, "BULLISH")
        self.assertEqual(snapshot.structure_object.direction, "LONG")
        self.assertIn("MS_TREND_001", snapshot.structure_object.source_rule_ids)
        self.assertFalse(snapshot.bos_on_last_close)

    def test_bos_on_last_close_uses_structure_known_before_that_close(self):
        candles = bullish_sequence()
        candles.append(c(9, 11.6, 11.9, 8.5, 8.8))
        snapshot = build_structure_liquidity_snapshot(
            candles, symbol="BTC-USDT-SWAP", timeframe="1m"
        )
        self.assertTrue(snapshot.bos_on_last_close)

    def test_future_extension_preserves_prior_physical_ids(self):
        prefix = bullish_sequence()
        full = prefix + [c(9, 11.6, 14, 10, 13), c(10, 13, 13.5, 11, 12)]
        a = build_structure_liquidity_snapshot(prefix, symbol="BTC-USDT-SWAP", timeframe="1m")
        b = build_structure_liquidity_snapshot(full, symbol="BTC-USDT-SWAP", timeframe="1m")
        self.assertEqual(
            [s.obj.object_id for s in a.swings],
            [s.obj.object_id for s in b.swings[: len(a.swings)]],
        )
        self.assertEqual(
            [p.obj.object_id for p in a.liquidity],
            [p.obj.object_id for p in b.liquidity[: len(a.liquidity)]],
        )

    def test_pool_identity_does_not_change_with_context_label(self):
        swings = confirmed_source_swings(
            bullish_sequence(), symbol="BTC-USDT-SWAP", timeframe="1m"
        )
        leg = latest_structure_leg(swings)
        assert leg is not None
        high = next(s for s in swings if s.side == "high" and s.price == 12)
        external = structural_liquidity(
            high, symbol="BTC-USDT-SWAP", timeframe="1m", active_leg=None
        )
        internal = structural_liquidity(
            high, symbol="BTC-USDT-SWAP", timeframe="1m", active_leg=leg
        )
        self.assertEqual(external.location, LiquidityLocation.EXTERNAL)
        self.assertEqual(internal.location, LiquidityLocation.INTERNAL)
        self.assertEqual(external.obj.object_id, internal.obj.object_id)


if __name__ == "__main__":
    unittest.main()
