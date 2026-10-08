"""Touch semantics and exact indexed equivalence; no numeric rule relaxation."""
from dataclasses import replace
from datetime import timedelta
from math import nextafter, inf
import unittest

from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import FreshnessIndex, _PoiSeed, _fresh, derive_automatic_levels
from crypto_bot.strategy.trade_plan import PriceZone
from test_auto_levels import valid_case


class FreshnessIndexTests(unittest.TestCase):
    def setUp(self):
        self.case=valid_case()
        self.histories=(tuple(self.case['htf_candles']),tuple(self.case['ltf_candles']))

    def test_every_seed_cutoff_matches_independent_linear_touch_scan(self):
        from crypto_bot.strategy.auto_levels import _seeds
        index=FreshnessIndex(self.histories)
        for seed in _seeds(self.histories[0]):
            for candle in self.histories[1]:
                cutoff=candle.close_time
                expected=not any(seed.known_at<c.close_time<=cutoff
                    and c.low<=seed.zone.high and c.high>=seed.zone.low
                    for history in self.histories for c in history)
                self.assertEqual(index.is_fresh(seed,cutoff),expected)
                self.assertEqual(_fresh(seed,self.histories,cutoff),expected)

    def test_wick_touch_is_enough_body_and_close_can_be_outside(self):
        candle=self.histories[1][10]
        seed=_PoiSeed(Direction.LONG,PriceZone(98,99),self.histories[1][9].close_time,())
        wick=replace(candle,low=99,open=100,close=100.5)
        index=FreshnessIndex(((wick,),))
        self.assertFalse(index.is_fresh(seed,wick.close_time))

    def test_formation_candle_and_earlier_prices_are_excluded(self):
        candle=self.histories[1][10]
        seed=_PoiSeed(Direction.LONG,PriceZone(candle.low,candle.high),candle.close_time,())
        self.assertTrue(FreshnessIndex(((candle,),)).is_fresh(seed,candle.close_time))

    def test_open_cutoff_does_not_include_that_candles_later_wick(self):
        candle=self.histories[1][10]
        seed=_PoiSeed(Direction.LONG,PriceZone(candle.low,candle.high),candle.open_time-timedelta(minutes=5),())
        index=FreshnessIndex(((candle,),))
        self.assertTrue(index.is_fresh(seed,candle.open_time))
        self.assertFalse(index.is_fresh(seed,candle.close_time))

    def test_boundary_equality_and_next_representable_float(self):
        candle=self.histories[1][10]
        seed=_PoiSeed(Direction.LONG,PriceZone(98,99),candle.open_time,())
        for low,expected in ((99,False),(nextafter(99,inf),True)):
            changed=replace(candle,low=low)
            self.assertEqual(FreshnessIndex(((changed,),)).is_fresh(seed,changed.close_time),expected)

    def test_future_suffix_cannot_change_past_predicate(self):
        candles=self.histories[1]
        cutoff=candles[10].close_time
        seed=_PoiSeed(Direction.LONG,PriceZone(90,91),candles[0].open_time,())
        future=tuple(replace(c,low=80) if c.close_time>cutoff else c for c in candles)
        self.assertEqual(FreshnessIndex((candles,)).is_fresh(seed,cutoff),FreshnessIndex((future,)).is_fresh(seed,cutoff))

    def test_different_ohlc_index_is_rejected(self):
        case=self.case
        changed=tuple(replace(c,low=c.low-1) for c in self.histories[1])
        with self.assertRaisesRegex(ValueError,'does not match'):
            derive_automatic_levels(**case,freshness_index=FreshnessIndex((self.histories[0],changed)))

    def test_plain_and_indexed_qualification_match_long_short(self):
        for direction in (Direction.LONG,Direction.SHORT):
            case=valid_case(direction)
            index=FreshnessIndex((case['htf_candles'],case['ltf_candles']))
            self.assertEqual(derive_automatic_levels(**case),derive_automatic_levels(**case,freshness_index=index))


if __name__=='__main__':
    unittest.main()
