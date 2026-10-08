from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.strategy.market_analysis import (
    StructuralLevel,
    _bearish_live_update,
    _bearish_structure_ending_at_low,
    _bullish_live_update,
    _bullish_structure_ending_at_high,
    _post_bos_bearish_structure,
    _post_bos_bullish_structure,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def level(i: int, side: str, price: float, *, confirmed_offset: int = 1) -> StructuralLevel:
    return StructuralLevel(
        level_id=i,
        side=side,
        price=price,
        swing_index=i,
        confirmed_index=i + confirmed_offset,
        swing_time=BASE + timedelta(minutes=i),
        confirmed_time=BASE + timedelta(minutes=i + confirmed_offset),
    )


class StructureOrderingTests(unittest.TestCase):
    def test_non_interleaved_lows_and_highs_do_not_form_bullish_structure(self):
        # Same-side prices look bullish, but the lows both occur before the prior high:
        # low -> low -> high -> high. This is not an HH/HL alternating structure sequence.
        levels = [
            level(1, "low", 10),
            level(2, "low", 11),
            level(3, "high", 12),
            level(4, "high", 13),
        ]
        self.assertIsNone(_bullish_structure_ending_at_high(levels, new_high=levels[-1]))
        self.assertIsNone(_post_bos_bullish_structure(levels, bos_index=0, new_high=levels[-1]))

    def test_non_interleaved_highs_and_lows_do_not_form_bearish_structure(self):
        # high -> high -> low -> low must not be accepted as LL/LH structure.
        levels = [
            level(1, "high", 13),
            level(2, "high", 12),
            level(3, "low", 11),
            level(4, "low", 10),
        ]
        self.assertIsNone(_bearish_structure_ending_at_low(levels, new_low=levels[-1]))
        self.assertIsNone(_post_bos_bearish_structure(levels, bos_index=0, new_low=levels[-1]))

    def test_interleaved_bullish_sequence_is_accepted(self):
        levels = [
            level(1, "low", 10),
            level(2, "high", 12),
            level(3, "low", 11),
            level(4, "high", 13),
        ]
        protected, extreme = _bullish_structure_ending_at_high(levels, new_high=levels[-1])
        self.assertEqual(protected.level_id, 3)
        self.assertEqual(extreme.level_id, 4)

    def test_interleaved_bearish_sequence_is_accepted(self):
        levels = [
            level(1, "high", 13),
            level(2, "low", 11),
            level(3, "high", 12),
            level(4, "low", 10),
        ]
        protected, extreme = _bearish_structure_ending_at_low(levels, new_low=levels[-1])
        self.assertEqual(protected.level_id, 3)
        self.assertEqual(extreme.level_id, 4)


    def test_live_bullish_update_must_break_current_key_hh_not_internal_high(self):
        # Current live structure: protected HL=10, key HH=15. A later internal high=12
        # must not let a new high=13 masquerade as a key HH update.
        protected = level(1, "low", 10)
        key_hh = level(2, "high", 15)
        internal_high = level(3, "high", 12)
        correction = level(4, "low", 11)
        new_high = level(5, "high", 13)
        levels = [protected, key_hh, internal_high, correction, new_high]
        self.assertIsNone(
            _bullish_live_update(
                levels, new_high=new_high, protected_hl=protected, key_hh=key_hh
            )
        )

    def test_live_bearish_update_must_break_current_key_ll_not_internal_low(self):
        protected = level(1, "high", 15)
        key_ll = level(2, "low", 10)
        internal_low = level(3, "low", 13)
        correction = level(4, "high", 14)
        new_low = level(5, "low", 12)
        levels = [protected, key_ll, internal_low, correction, new_low]
        self.assertIsNone(
            _bearish_live_update(
                levels, new_low=new_low, protected_lh=protected, key_ll=key_ll
            )
        )

    def test_live_bullish_update_uses_intervening_higher_low(self):
        protected = level(1, "low", 10)
        key_hh = level(2, "high", 12)
        correction = level(3, "low", 11)
        new_high = level(4, "high", 13)
        levels = [protected, key_hh, correction, new_high]
        out = _bullish_live_update(
            levels, new_high=new_high, protected_hl=protected, key_hh=key_hh
        )
        self.assertIsNotNone(out)
        self.assertEqual(out[0].level_id, correction.level_id)
        self.assertEqual(out[1].level_id, new_high.level_id)

    def test_live_bearish_update_uses_intervening_lower_high(self):
        protected = level(1, "high", 15)
        key_ll = level(2, "low", 12)
        correction = level(3, "high", 14)
        new_low = level(4, "low", 11)
        levels = [protected, key_ll, correction, new_low]
        out = _bearish_live_update(
            levels, new_low=new_low, protected_lh=protected, key_ll=key_ll
        )
        self.assertIsNotNone(out)
        self.assertEqual(out[0].level_id, correction.level_id)
        self.assertEqual(out[1].level_id, new_low.level_id)

    def test_post_bos_helper_rejects_pre_bos_or_same_close_confirmation(self):
        # All four centers are on/after BOS, but the final high is not confirmed after BOS.
        levels = [
            level(5, "low", 10),
            level(6, "high", 12),
            level(7, "low", 11),
            StructuralLevel(
                level_id=8,
                side="high",
                price=13,
                swing_index=8,
                confirmed_index=8,
                swing_time=BASE + timedelta(minutes=8),
                confirmed_time=BASE + timedelta(minutes=8),
            ),
        ]
        self.assertIsNone(_post_bos_bullish_structure(levels, bos_index=8, new_high=levels[-1]))


if __name__ == "__main__":
    unittest.main()
