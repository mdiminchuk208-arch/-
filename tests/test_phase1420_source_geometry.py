import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.order_block import OrderBlockAssessment, derive_qualified_order_block_geometry
from crypto_bot.strategy.trade_plan import PriceZone, TradePlanGeometryError, select_first_opposing_poi_fta


def candle(minute, o, h, l, c):
    t=datetime(2026,1,1,0,minute,tzinfo=timezone.utc)
    return Candle(t,t+timedelta(minutes=1),o,h,l,c)


class QualifiedObGeometryTests(unittest.TestCase):
    def setUp(self):
        self.a=OrderBlockAssessment(True,True,"A",tuple())
        self.engulfed=candle(0,100,108,99,105)
        self.engulfing=candle(1,105,110,98,109)

    def test_long_boundary_and_source_stop_references(self):
        q=derive_qualified_order_block_geometry(direction=Direction.LONG,engulfed_candle=self.engulfed,engulfing_candle=self.engulfing,assessment=self.a)
        self.assertEqual(q.zone,PriceZone(99,108)); self.assertEqual(q.entry_reference_price,108); self.assertEqual(q.stop_reference.price,99)
        w=derive_qualified_order_block_geometry(direction=Direction.LONG,engulfed_candle=self.engulfed,engulfing_candle=self.engulfing,assessment=self.a,stop_policy="SOURCE_ENGULFING_WICK")
        self.assertEqual(w.stop_reference.price,98)

    def test_short_boundary_is_lower_ob_boundary(self):
        q=derive_qualified_order_block_geometry(direction=Direction.SHORT,engulfed_candle=self.engulfed,engulfing_candle=self.engulfing,assessment=self.a)
        self.assertEqual(q.entry_reference_price,99); self.assertEqual(q.stop_reference.price,108)

    def test_non_trade_eligible_ob_is_rejected(self):
        with self.assertRaises(ValueError):
            derive_qualified_order_block_geometry(direction=Direction.LONG,engulfed_candle=self.engulfed,engulfing_candle=self.engulfing,assessment=OrderBlockAssessment(True,False,"IMB_UNRESOLVED",tuple()))


class QualifiedFtaSelectionTests(unittest.TestCase):
    def test_first_opposing_poi_is_nearest_in_trade_direction(self):
        long_fta=select_first_opposing_poi_fta(direction=Direction.LONG,entry_zone=PriceZone(94.2,95.9),opposing_poi_zones=(PriceZone(120,125),PriceZone(102,103),PriceZone(108,110)))
        self.assertEqual(long_fta.zone,PriceZone(102,103))
        short_fta=select_first_opposing_poi_fta(direction=Direction.SHORT,entry_zone=PriceZone(104.1,105.8),opposing_poi_zones=(PriceZone(80,85),PriceZone(100,101),PriceZone(90,92)))
        self.assertEqual(short_fta.zone,PriceZone(100,101))

    def test_missing_directional_fta_is_rejected(self):
        with self.assertRaises(TradePlanGeometryError):
            select_first_opposing_poi_fta(direction=Direction.LONG,entry_zone=PriceZone(100,105),opposing_poi_zones=(PriceZone(90,95),))
