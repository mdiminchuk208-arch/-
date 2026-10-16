from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Direction
from crypto_bot.strategy.causal_objects import CausalSourceObject, SourceObjectType
from crypto_bot.strategy.source_demand_supply_v2 import DemandSupplyKind, SourceDemandSupplyEvidence
from crypto_bot.strategy.source_execution_v2 import (
    AtrReference,
    EntryMode,
    ExitMode,
    PriceAnchorReference,
    SourcePoiTargetReference,
    StopMode,
    plan_breaker_execution,
    plan_demand_supply_execution,
    plan_ob_execution,
    plan_range_execution,
    plan_sfp_execution,
    plan_stb_bts_execution,
    select_source_fta,
)
from crypto_bot.strategy.source_ob_breaker_v2 import SourceBreakerEvidence, SourceOrderBlockEvidence
from crypto_bot.strategy.source_range_stb_v2 import (
    RangeDeviationEvidence,
    RangeDeviationSide,
    SourceRangeEvidence,
    SourceStbBtsEvidence,
)
from crypto_bot.strategy.source_sfp_v2 import SfpOrigin, SourceSfpEvidence
from crypto_bot.strategy.source_setup_v2 import SetupBranch, SourceSetupEvidence
from crypto_bot.strategy.source_structure_liquidity_v2 import EvidenceStatus


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def t(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def causal_obj(
    object_type: SourceObjectType,
    *,
    direction: Direction | None,
    timeframe: str | int,
    minute: int,
    token: str,
) -> CausalSourceObject:
    at = t(minute)
    return CausalSourceObject.formed(
        object_type=object_type,
        symbol="BTC-USDT-SWAP",
        timeframe=timeframe,
        direction=direction.value if direction is not None else None,
        formation_at=at,
        known_at=at,
        identity_parts={"fixture": token},
        source_rule_ids=("TEST_SOURCE_RULE",),
        provenance="Stage-8 unit fixture",
    )


def setup_evidence(
    branch: SetupBranch,
    context: CausalSourceObject,
    direction: Direction,
    *,
    minute: int = 5,
    entry_poi_id: str | None = None,
) -> SourceSetupEvidence:
    known = t(minute)
    physical = CausalSourceObject.formed(
        object_type=SourceObjectType.PHYSICAL_IDEA,
        symbol=context.symbol,
        timeframe=context.timeframe,
        direction=direction.value,
        formation_at=context.formation_at,
        known_at=context.known_at,
        identity_parts={"context": context.object_id, "direction": direction.value},
        source_rule_ids=context.source_rule_ids,
        parent_object_ids=(context.object_id,),
        provenance="Stage-8 physical fixture",
    )
    setup = CausalSourceObject.formed(
        object_type=SourceObjectType.SETUP,
        symbol=context.symbol,
        timeframe=context.timeframe,
        direction=direction.value,
        formation_at=known,
        known_at=known,
        identity_parts={"physical": physical.object_id, "branch": branch.value, "entry_poi": entry_poi_id},
        source_rule_ids=("TEST_SETUP_RULE",),
        parent_object_ids=(physical.object_id, context.object_id),
        provenance="Stage-8 setup fixture",
    )
    return SourceSetupEvidence(
        physical_idea=physical,
        setup=setup,
        branch=branch,
        direction=direction,
        context_object_id=context.object_id,
        known_at=known,
        evidence_ids=(),
        entry_poi_id=entry_poi_id,
    )


def ob_evidence() -> SourceOrderBlockEvidence:
    context = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=60, minute=0, token="ob")
    return SourceOrderBlockEvidence(
        context, Direction.LONG, 95, 100, t(0), t(1), t(2), "liq", "htf", "structure", "bos", True
    )


def sfp_evidence() -> SourceSfpEvidence:
    context = causal_obj(SourceObjectType.SFP, direction=Direction.LONG, timeframe=60, minute=0, token="sfp")
    return SourceSfpEvidence(
        context, Direction.LONG, SfpOrigin.STRUCTURAL_LIQUIDITY, "liq", "low", 98,
        t(0), t(1), t(1), 97,
    )


class FtaSelectionTests(unittest.TestCase):
    def test_future_poi_cannot_change_current_fta(self):
        current = SourcePoiTargetReference(
            causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.SHORT, timeframe=240, minute=1, token="current-fta"),
            110,
            112,
            "ORDER_BLOCK",
        )
        future_nearer = SourcePoiTargetReference(
            causal_obj(SourceObjectType.BREAKER, direction=Direction.SHORT, timeframe=240, minute=20, token="future-fta"),
            105,
            106,
            "BREAKER",
        )
        a = select_source_fta(
            direction=Direction.LONG, entry_price=100, trade_timeframe_minutes=15,
            candidates=(current,), decision_at=t(5),
        )
        b = select_source_fta(
            direction=Direction.LONG, entry_price=100, trade_timeframe_minutes=15,
            candidates=(current, future_nearer), decision_at=t(5),
        )
        self.assertEqual(a.status, EvidenceStatus.PASS)
        self.assertEqual(b.status, EvidenceStatus.PASS)
        self.assertEqual(a.first_contact_price, 110)
        self.assertEqual(b.first_contact_price, 110)
        self.assertEqual(a.candidates[0].obj.object_id, b.candidates[0].obj.object_id)

    def test_consumed_poi_is_not_fta_but_future_consumption_does_not_rewrite_past(self):
        obj = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.SHORT, timeframe=240, minute=1, token="consumed")
        ref = SourcePoiTargetReference(obj, 110, 112, "ORDER_BLOCK", consumed_at=t(10))
        before = select_source_fta(
            direction=Direction.LONG, entry_price=100, trade_timeframe_minutes=15,
            candidates=(ref,), decision_at=t(5),
        )
        after = select_source_fta(
            direction=Direction.LONG, entry_price=100, trade_timeframe_minutes=15,
            candidates=(ref,), decision_at=t(11),
        )
        self.assertEqual(before.status, EvidenceStatus.PASS)
        self.assertEqual(after.status, EvidenceStatus.UNKNOWN)
        self.assertEqual(after.reason, "WAIT_FIRST_TROUBLE_AREA")

    def test_first_contact_uses_near_edge_of_nearest_opposing_higher_tf_zone(self):
        far = SourcePoiTargetReference(
            causal_obj(SourceObjectType.POI, direction=Direction.SHORT, timeframe="4h", minute=1, token="far"),
            120, 124, "SUPPLY",
        )
        near = SourcePoiTargetReference(
            causal_obj(SourceObjectType.BREAKER, direction=Direction.SHORT, timeframe="1h", minute=1, token="near"),
            108, 111, "BREAKER",
        )
        result = select_source_fta(
            direction=Direction.LONG, entry_price=100, trade_timeframe_minutes=5,
            candidates=(far, near), decision_at=t(5),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        self.assertEqual(result.first_contact_price, 108)
        self.assertEqual(result.candidates[0].obj.object_id, near.obj.object_id)


class SourceExecutionStage8Tests(unittest.TestCase):
    def test_ob_direct_preserves_entry_and_stop_variants_without_enabling_trade(self):
        ob = ob_evidence()
        setup = setup_evidence(SetupBranch.OB_DIRECT_FIRST_TEST, ob.obj, Direction.LONG)
        fta_ref = SourcePoiTargetReference(
            causal_obj(SourceObjectType.POI, direction=Direction.SHORT, timeframe=240, minute=1, token="fta-ob"),
            110, 112, "SUPPLY",
        )
        fta = select_source_fta(
            direction=Direction.LONG, entry_price=100, trade_timeframe_minutes=60,
            candidates=(fta_ref,), decision_at=setup.known_at,
        )
        result = plan_ob_execution(
            setup, ob,
            engulfing_wick_extreme=PriceAnchorReference(94, t(2), "engulf-wick", "closed engulfing candle"),
            fta=fta,
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual({x.mode for x in result.plan.entry_options}, {EntryMode.OB_BOUNDARY_LIMIT, EntryMode.OB_INSIDE_ZONE})
        boundary = next(x for x in result.plan.entry_options if x.mode == EntryMode.OB_BOUNDARY_LIMIT)
        self.assertEqual(boundary.quote, 100)
        self.assertTrue(boundary.exact_quote)
        self.assertEqual(len(result.plan.stop_options), 2)
        self.assertIn(StopMode.OB_BEYOND_ZONE_EXTREME, {x.mode for x in result.plan.stop_options})
        self.assertIn(StopMode.OB_BEYOND_ENGULFING_WICK, {x.mode for x in result.plan.stop_options})
        self.assertEqual(result.plan.exit_policy.mode, ExitMode.FTA_FULL_OR_PARTIAL)
        self.assertEqual(result.plan.exit_policy.primary_target_price, 110)
        self.assertFalse(result.plan.trade_entry_allowed)
        self.assertFalse(result.plan.execution_ready)
        self.assertIn("OB_ENTRY_BOUNDARY_VS_INSIDE_UNRESOLVED", result.plan.unresolved)
        self.assertIn("FTA_FULL_VS_PARTIAL_FRACTION_UNRESOLVED", result.plan.unresolved)

    def test_ob_conservative_uses_new_poi_zone_and_does_not_inherit_unproven_stop(self):
        ob = ob_evidence()
        poi_obj = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=4, token="ltf-poi")
        poi = SourcePoiTargetReference(poi_obj, 98, 99, "ORDER_BLOCK")
        setup = setup_evidence(
            SetupBranch.OB_CONSERVATIVE_LTF_BOS_NEW_POI, ob.obj, Direction.LONG, entry_poi_id=poi_obj.object_id
        )
        result = plan_ob_execution(setup, ob, entry_poi=poi)
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual(result.plan.entry_options[0].mode, EntryMode.NEW_POI_ZONE)
        self.assertFalse(result.plan.entry_options[0].exact_quote)
        self.assertEqual(result.plan.stop_options[0].mode, StopMode.UNRESOLVED)
        self.assertIn("WAIT_UNRESOLVED_STOP_GEOMETRY", result.plan.unresolved)

    def test_breaker_keeps_aggressive_and_conservative_stop_variants(self):
        context = causal_obj(SourceObjectType.BREAKER, direction=Direction.LONG, timeframe=60, minute=0, token="breaker")
        breaker = SourceBreakerEvidence(context, Direction.LONG, 96, 100, "ob-parent", t(1), "shift")
        setup = setup_evidence(SetupBranch.BREAKER_DIRECT, context, Direction.LONG)
        result = plan_breaker_execution(
            setup, breaker,
            sweep_impulse_extreme=PriceAnchorReference(93, t(1), "sweep-extreme", "closed impulse candle"),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual({x.mode for x in result.plan.stop_options}, {
            StopMode.BREAKER_AGGRESSIVE_BEYOND_ZONE,
            StopMode.BREAKER_CONSERVATIVE_BEYOND_SWEEP_IMPULSE,
        })
        self.assertFalse(any(x.exact_price for x in result.plan.stop_options))
        self.assertFalse(result.plan.execution_ready)

    def test_sfp_atr14_stop_is_directional_and_body_close_invalidation_is_preserved(self):
        sfp = sfp_evidence()
        poi_obj = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=4, token="sfp-entry")
        poi = SourcePoiTargetReference(poi_obj, 99, 100, "ORDER_BLOCK")
        setup = setup_evidence(SetupBranch.SFP_LTF_BOS_NEW_POI, sfp.obj, Direction.LONG, entry_poi_id=poi_obj.object_id)
        result = plan_sfp_execution(
            setup, sfp, entry_poi=poi,
            atr=AtrReference(2, 14, t(1), "atr14", "ATR value known on completed SFP candle"),
        )
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual(result.plan.stop_options[0].mode, StopMode.SFP_ATR_FROM_PATTERN_EXTREME)
        self.assertEqual(result.plan.stop_options[0].stop_price, 95)
        self.assertTrue(result.plan.stop_options[0].exact_price)
        self.assertIn("SFP_BODY_CLOSE_BEYOND_PATTERN_EXTREME_INVALIDATES", result.plan.invalidation_rules)
        self.assertIn("SFP_PROTECTIVE_STOP_NOT_MOVED", result.plan.invalidation_rules)
        self.assertNotIn("SFP_ATR_PERIOD_NOT_FROZEN_BY_SOURCE_STRATEGY", result.plan.unresolved)
        self.assertFalse(result.plan.trade_entry_allowed)

    def test_nonstandard_sfp_atr_period_stays_explicitly_unresolved(self):
        sfp = sfp_evidence()
        poi_obj = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=4, token="sfp-entry-7")
        poi = SourcePoiTargetReference(poi_obj, 99, 100, "ORDER_BLOCK")
        setup = setup_evidence(SetupBranch.SFP_LTF_BOS_NEW_POI, sfp.obj, Direction.LONG, entry_poi_id=poi_obj.object_id)
        result = plan_sfp_execution(
            setup, sfp, entry_poi=poi,
            atr=AtrReference(1.5, 7, t(1), "atr7", "source says ATR period may be changed"),
        )
        assert result.plan is not None
        self.assertIn("SFP_ATR_PERIOD_NOT_FROZEN_BY_SOURCE_STRATEGY", result.plan.unresolved)
        self.assertFalse(result.plan.execution_ready)

    def test_future_atr_is_rejected(self):
        sfp = sfp_evidence()
        poi_obj = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.LONG, timeframe=5, minute=4, token="sfp-entry-future")
        poi = SourcePoiTargetReference(poi_obj, 99, 100, "ORDER_BLOCK")
        setup = setup_evidence(SetupBranch.SFP_LTF_BOS_NEW_POI, sfp.obj, Direction.LONG, entry_poi_id=poi_obj.object_id)
        result = plan_sfp_execution(
            setup, sfp, entry_poi=poi,
            atr=AtrReference(2, 14, t(8), "future-atr", "future fixture"),
        )
        self.assertEqual(result.status, EvidenceStatus.FAIL)
        self.assertEqual(result.reason, "SFP_ATR_FROM_FUTURE")

    def test_stb_bts_keeps_midpoint_and_directional_part_without_stop_invention(self):
        context = causal_obj(SourceObjectType.STB_BTS, direction=Direction.LONG, timeframe=60, minute=0, token="stb")
        stb = SourceStbBtsEvidence(context, "STB", Direction.LONG, 90, 100, 95, "manip", "structure")
        setup = setup_evidence(SetupBranch.STB_BTS_DIRECT, context, Direction.LONG)
        result = plan_stb_bts_execution(setup, stb)
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        midpoint = next(x for x in result.plan.entry_options if x.mode == EntryMode.STB_BTS_MIDPOINT)
        part = next(x for x in result.plan.entry_options if x.mode == EntryMode.STB_BTS_DIRECTIONAL_PART)
        self.assertEqual(midpoint.quote, 95)
        self.assertTrue(midpoint.exact_quote)
        self.assertEqual((part.zone_low, part.zone_high), (95, 100))
        self.assertEqual(result.plan.stop_options[0].mode, StopMode.UNRESOLVED)
        self.assertIn("WAIT_UNRESOLVED_STOP_GEOMETRY", result.plan.unresolved)

    def test_range_conservative_entry_and_80_20_exit_are_source_specific(self):
        context = causal_obj(SourceObjectType.RANGE, direction=Direction.LONG, timeframe=60, minute=0, token="range")
        range_ev = SourceRangeEvidence(context, Direction.LONG, 90, 110, 100, 110, 90, "impulse", "correction")
        deviation = RangeDeviationEvidence("dev-low", context.object_id, RangeDeviationSide.LOW, 90, 88, t(3))
        setup = setup_evidence(SetupBranch.RANGE_CONSERVATIVE_RETURN_RETEST, context, Direction.LONG)
        result = plan_range_execution(setup, range_ev, deviation=deviation)
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual(result.plan.entry_options[0].mode, EntryMode.RANGE_BOUNDARY_RETEST)
        self.assertEqual(result.plan.entry_options[0].quote, 90)
        self.assertEqual(result.plan.exit_policy.mode, ExitMode.RANGE_80_20)
        self.assertEqual(result.plan.exit_policy.primary_fraction, 0.8)
        self.assertEqual(result.plan.exit_policy.remainder_fraction, 0.2)
        self.assertEqual(result.plan.exit_policy.primary_target_price, 110)
        self.assertIsNone(result.plan.exit_policy.remainder_target_price)
        self.assertIn("RANGE_REMAINDER_TRUE_BREAKOUT_TARGET_UNRESOLVED", result.plan.unresolved)
        self.assertFalse(result.plan.trade_entry_allowed)

    def test_range_aggressive_keeps_external_poi_zone_quote_unresolved(self):
        context = causal_obj(SourceObjectType.RANGE, direction=Direction.LONG, timeframe=60, minute=0, token="range-aggressive")
        range_ev = SourceRangeEvidence(context, Direction.LONG, 90, 110, 100, 110, 90, "impulse", "correction")
        deviation = RangeDeviationEvidence("dev-high", context.object_id, RangeDeviationSide.HIGH, 110, 112, t(3))
        setup = setup_evidence(SetupBranch.RANGE_AGGRESSIVE_EXTERNAL_POI, context, Direction.SHORT)
        external_obj = causal_obj(SourceObjectType.ORDER_BLOCK, direction=Direction.SHORT, timeframe=240, minute=1, token="external")
        external = SourcePoiTargetReference(external_obj, 111, 113, "ORDER_BLOCK")
        result = plan_range_execution(setup, range_ev, deviation=deviation, external_poi=external)
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual(result.plan.entry_options[0].mode, EntryMode.RANGE_DEVIATION_EXTERNAL_POI)
        self.assertFalse(result.plan.entry_options[0].exact_quote)
        self.assertIn("RANGE_AGGRESSIVE_EXACT_QUOTE_UNRESOLVED", result.plan.unresolved)

    def test_demand_supply_does_not_invent_entry_quote_or_stop(self):
        context = causal_obj(SourceObjectType.POI, direction=Direction.LONG, timeframe=60, minute=0, token="demand")
        ds = SourceDemandSupplyEvidence(context, DemandSupplyKind.DEMAND, Direction.LONG, 95, 100, "move", "raid")
        setup = setup_evidence(SetupBranch.DEMAND_SUPPLY_DIRECT, context, Direction.LONG)
        result = plan_demand_supply_execution(setup, ds)
        self.assertEqual(result.status, EvidenceStatus.PASS)
        assert result.plan is not None
        self.assertEqual(result.plan.entry_options[0].mode, EntryMode.DEMAND_SUPPLY_ZONE)
        self.assertFalse(result.plan.entry_options[0].exact_quote)
        self.assertEqual(result.plan.stop_options[0].mode, StopMode.UNRESOLVED)
        self.assertIn("DEMAND_SUPPLY_EXACT_ENTRY_QUOTE_UNRESOLVED", result.plan.unresolved)
        self.assertIn("WAIT_UNRESOLVED_STOP_GEOMETRY", result.plan.unresolved)


if __name__ == "__main__":
    unittest.main()
