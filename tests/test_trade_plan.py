import unittest

from crypto_bot.common.models import Direction
from crypto_bot.strategy.trade_plan import (
    PriceZone,
    TradePlanGeometryError,
    build_trade_plan_geometry,
    ote_entry_zone,
    rr_range_for_entry_zone,
    rr_ratio,
)


class TradePlanGeometryTests(unittest.TestCase):
    def test_long_ote_zone_is_705_to_790_retracement(self):
        zone = ote_entry_zone(
            direction=Direction.LONG,
            impulse_start_price=100.0,
            impulse_end_price=120.0,
        )
        self.assertAlmostEqual(zone.low, 104.2)
        self.assertAlmostEqual(zone.high, 105.9)

    def test_short_ote_zone_is_705_to_790_retracement(self):
        zone = ote_entry_zone(
            direction=Direction.SHORT,
            impulse_start_price=120.0,
            impulse_end_price=100.0,
        )
        self.assertAlmostEqual(zone.low, 114.1)
        self.assertAlmostEqual(zone.high, 115.8)

    def test_direction_must_match_impulse_direction(self):
        with self.assertRaises(TradePlanGeometryError):
            ote_entry_zone(
                direction=Direction.LONG,
                impulse_start_price=120.0,
                impulse_end_price=100.0,
            )
        with self.assertRaises(TradePlanGeometryError):
            ote_entry_zone(
                direction=Direction.SHORT,
                impulse_start_price=100.0,
                impulse_end_price=120.0,
            )

    def test_long_rr_ratio(self):
        self.assertAlmostEqual(
            rr_ratio(
                direction=Direction.LONG,
                entry_price=105.0,
                stop_loss_price=100.0,
                target_price=115.0,
            ),
            2.0,
        )

    def test_short_rr_ratio(self):
        self.assertAlmostEqual(
            rr_ratio(
                direction=Direction.SHORT,
                entry_price=115.0,
                stop_loss_price=120.0,
                target_price=105.0,
            ),
            2.0,
        )

    def test_rr_rejects_wrong_side_stop_or_target(self):
        with self.assertRaises(TradePlanGeometryError):
            rr_ratio(
                direction=Direction.LONG,
                entry_price=105.0,
                stop_loss_price=106.0,
                target_price=115.0,
            )
        with self.assertRaises(TradePlanGeometryError):
            rr_ratio(
                direction=Direction.SHORT,
                entry_price=115.0,
                stop_loss_price=120.0,
                target_price=116.0,
            )

    def test_rr_range_uses_zone_edges_without_single_optimal_price(self):
        rr = rr_range_for_entry_zone(
            direction=Direction.LONG,
            entry_zone=PriceZone(104.0, 106.0),
            stop_loss_price=100.0,
            target_price=118.0,
        )
        self.assertAlmostEqual(rr.minimum, 2.0)
        self.assertAlmostEqual(rr.maximum, 3.5)

    def test_build_geometry_keeps_optimal_entry_unset(self):
        plan = build_trade_plan_geometry(
            direction=Direction.LONG,
            impulse_start_price=100.0,
            impulse_end_price=120.0,
            stop_loss_price=99.0,
            target_price=130.0,
        )
        self.assertIsNone(plan.optimal_entry_price)
        self.assertEqual(plan.entry_policy, "SOURCE_OTE_0.705_0.79_ZONE")
        self.assertEqual(
            plan.optimal_entry_policy,
            "SOURCE_DEFINES_OPTIMAL_ZONE_NOT_SINGLE_PRICE",
        )


if __name__ == "__main__":
    unittest.main()


class Phase1420StructuralContextTests(unittest.TestCase):
    def test_resolved_expected_opposite_transition_produces_ote(self):
        from types import SimpleNamespace as N
        from datetime import datetime,timedelta,timezone
        from crypto_bot.strategy.market_analysis import MarketEventKind,TrendState
        from crypto_bot.strategy.trade_plan import derive_structural_impulse_context
        t=datetime(2026,1,1,tzinfo=timezone.utc); k=MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS
        d=N(transition_id=7,bos_kind=k.value,bos_index=75,bos_time=t,resolved_time=t+timedelta(minutes=15),resolved_trend=TrendState.BULLISH,resolution_mode="EXPECTED_OPPOSITE_FAST_PATH",broken_extreme_price=90.0,selected_anchor_level_id=1,selected_correction_level_id=2)
        r=N(structure_transition_diagnostics=(d,),levels=(N(level_id=1,price=110.0),N(level_id=2,price=102.0)))
        x=derive_structural_impulse_context(direction=Direction.LONG,ltf_report=r,bos_kind=k,bos_index=75,bos_time=t)
        self.assertIsNotNone(x); self.assertAlmostEqual(x.entry_zone.low,94.2); self.assertAlmostEqual(x.entry_zone.high,95.9)

    def test_same_direction_recovery_does_not_produce_entry_geometry(self):
        from types import SimpleNamespace as N
        from datetime import datetime,timedelta,timezone
        from crypto_bot.strategy.market_analysis import MarketEventKind,TrendState
        from crypto_bot.strategy.trade_plan import derive_structural_impulse_context
        t=datetime(2026,1,1,tzinfo=timezone.utc); k=MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS
        d=N(transition_id=7,bos_kind=k.value,bos_index=75,bos_time=t,resolved_time=t+timedelta(minutes=15),resolved_trend=TrendState.BULLISH,resolution_mode="SAME_DIRECTION_POST_BOS_RECOVERY",broken_extreme_price=90.0,selected_anchor_level_id=1,selected_correction_level_id=2)
        r=N(structure_transition_diagnostics=(d,),levels=(N(level_id=1,price=110.0),N(level_id=2,price=102.0)))
        x=derive_structural_impulse_context(direction=Direction.LONG,ltf_report=r,bos_kind=k,bos_index=75,bos_time=t)
        self.assertIsNone(x)


class Phase1420PlanStatusTests(unittest.TestCase):
    def _opp(self):
        from datetime import datetime,timezone
        from crypto_bot.strategy.market_analysis import MarketEventKind
        from crypto_bot.strategy.mtf_sfp import MtfOpportunity,MtfOpportunityStatus
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        return MtfOpportunity(1,MtfOpportunityStatus.ENTRY_SEARCH_CANDIDATE,Direction.LONG,MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,t,75,9,100.0,(1,),(1,),(1,),t,t,1)

    def test_default_status_waits_for_geometry(self):
        self.assertEqual(self._opp().entry_plan_status,"WAITING_FOR_ENTRY_GEOMETRY")

    def test_ote_status_waits_for_source_sl_target(self):
        from types import SimpleNamespace as N
        from datetime import timedelta
        from crypto_bot.strategy.market_analysis import TrendState
        from crypto_bot.strategy.mtf_sfp import _attach_entry_geometry
        o=self._opp(); t=o.ltf_bos_event_time
        d=N(transition_id=7,bos_kind=o.ltf_bos_kind.value,bos_index=75,bos_time=t,resolved_time=t+timedelta(minutes=15),resolved_trend=TrendState.BULLISH,resolution_mode="EXPECTED_OPPOSITE_FAST_PATH",broken_extreme_price=90.0,selected_anchor_level_id=1,selected_correction_level_id=2)
        r=N(structure_transition_diagnostics=(d,),levels=(N(level_id=1,price=110.0),N(level_id=2,price=102.0)))
        q=_attach_entry_geometry((o,),r)[0]
        self.assertEqual(q.entry_plan_status,"WAITING_FOR_SOURCE_SL_TARGET"); self.assertFalse(q.trade_entry_allowed)


class Phase1420SourceLevelsTests(unittest.TestCase):
    def _ready(self):
        from dataclasses import replace
        o=Phase1420PlanStatusTests()._opp()
        return replace(o,impulse_start_price=90.0,impulse_end_price=110.0,entry_zone_low=94.2,entry_zone_high=95.9,entry_plan_status="WAITING_FOR_SOURCE_SL_TARGET")

    def test_source_levels_derive_rr_but_keep_trade_blocked(self):
        from crypto_bot.strategy.mtf_sfp import attach_source_qualified_trade_levels
        q=attach_source_qualified_trade_levels(self._ready(),stop_loss_price=90.0,target_price=110.0,stop_loss_policy="SOURCE_OB_STOP",target_policy="SOURCE_FTA")
        self.assertEqual(q.entry_plan_status,"RR_READY_SOURCE_LEVELS"); self.assertFalse(q.trade_entry_allowed)
        self.assertAlmostEqual(q.rr_minimum,14.1/5.9); self.assertAlmostEqual(q.rr_maximum,15.8/4.2)

    def test_invalid_long_sl_geometry_is_rejected(self):
        from crypto_bot.strategy.mtf_sfp import attach_source_qualified_trade_levels
        from crypto_bot.strategy.trade_plan import TradePlanGeometryError
        with self.assertRaises(TradePlanGeometryError):
            attach_source_qualified_trade_levels(self._ready(),stop_loss_price=100.0,target_price=110.0,stop_loss_policy="SOURCE_OB_STOP",target_policy="SOURCE_FTA")


class Phase1420SourceReferenceTests(unittest.TestCase):
    def test_long_and_short_reference_geometry(self):
        from crypto_bot.strategy.trade_plan import PriceZone,SourceStopReference,SourceTargetZone,validate_source_reference_geometry
        validate_source_reference_geometry(direction=Direction.LONG,entry_zone=PriceZone(94.2,95.9),stop_reference=SourceStopReference(90.0,"SOURCE_OB_EXTREME"),target_zone=SourceTargetZone(PriceZone(108.0,110.0)))
        validate_source_reference_geometry(direction=Direction.SHORT,entry_zone=PriceZone(104.1,105.8),stop_reference=SourceStopReference(110.0,"SOURCE_ENGULFING_WICK"),target_zone=SourceTargetZone(PriceZone(90.0,92.0)))

    def test_invalid_reference_geometry_is_rejected(self):
        from crypto_bot.strategy.trade_plan import PriceZone,SourceStopReference,SourceTargetZone,TradePlanGeometryError,validate_source_reference_geometry
        with self.assertRaises(TradePlanGeometryError):
            validate_source_reference_geometry(direction=Direction.LONG,entry_zone=PriceZone(94.2,95.9),stop_reference=SourceStopReference(96.0,"SOURCE_OB_EXTREME"),target_zone=SourceTargetZone(PriceZone(108.0,110.0)))
