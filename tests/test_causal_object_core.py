from datetime import datetime, timedelta, timezone
import unittest
from crypto_bot.common.models import Candle
from crypto_bot.strategy.causal_objects import CausalObjectRegistry, CausalSourceObject, ObjectStatus, RejectionCategory, SourceObjectType, require_closed_candles, stable_object_id
UTC=timezone.utc; T0=datetime(2026,1,1,tzinfo=UTC)
class CausalObjectCoreTests(unittest.TestCase):
    def make_object(self, object_type=SourceObjectType.ORDER_BLOCK):
        return CausalSourceObject.formed(object_type=object_type,symbol="BTC-USDT-SWAP",timeframe="1H",direction="LONG",formation_at=T0,known_at=T0+timedelta(hours=1),identity_parts={"anchor_index":10,"low":100.0,"high":101.0},source_rule_ids=("SRC_TEST",),technical_normalization_ids=("TN_RIGHT_CLOSED",),provenance="unit-test")
    def test_formation_valid_is_independent_from_trade_eligibility(self):
        obj=self.make_object(); self.assertTrue(obj.formation_valid); self.assertFalse(obj.trade_eligible)
        waiting=obj.reject(RejectionCategory.WAIT_ENTRY_CHAIN,T0+timedelta(hours=2)); self.assertTrue(waiting.formation_valid); self.assertFalse(waiting.trade_eligible)
    def test_object_invalid_source_is_distinct_rejection(self):
        rejected=self.make_object().reject(RejectionCategory.OBJECT_INVALID_SOURCE,T0+timedelta(hours=2),"bad geometry"); self.assertFalse(rejected.formation_valid); self.assertTrue(rejected.rejection_reasons[0].startswith("OBJECT_INVALID_SOURCE"))
    def test_later_invalidation_does_not_rewrite_past_validity(self):
        obj=self.make_object().set_trade_eligible(True,T0+timedelta(hours=2)); invalidated=obj.invalidate(T0+timedelta(hours=4),"SOURCE_BODY_INVALIDATION")
        old=invalidated.state_at(T0+timedelta(hours=3)); new=invalidated.state_at(T0+timedelta(hours=5)); self.assertTrue(invalidated.formation_valid); self.assertTrue(old.trade_eligible); self.assertIsNone(old.invalidated_at); self.assertEqual(new.invalidated_at,T0+timedelta(hours=4)); self.assertFalse(new.trade_eligible)
    def test_later_cancellation_preserves_setup_history(self):
        setup=self.make_object(SourceObjectType.SETUP).set_trade_eligible(True,T0+timedelta(hours=2)); cancelled=setup.cancel(T0+timedelta(hours=5)); before=cancelled.state_at(T0+timedelta(hours=4)); after=cancelled.state_at(T0+timedelta(hours=6)); self.assertEqual(before.status,ObjectStatus.READY); self.assertTrue(before.trade_eligible); self.assertEqual(after.status,ObjectStatus.CANCELLED); self.assertTrue(cancelled.formation_valid)
    def test_stable_id_is_prefix_safe_and_outcome_independent(self):
        kwargs=dict(object_type=SourceObjectType.SWING,symbol="ETH-USDT-SWAP",timeframe="15m",direction=None,formation_at=T0,identity_parts={"center_open_time":T0,"kind":"high","price":3000.0}); self.assertEqual(stable_object_id(**kwargs),stable_object_id(**kwargs))
        for bad in ({"price":3000.0,"PnL":50.0},{"price":3000.0,"future_touch":T0+timedelta(days=1)},{"price":3000.0,"branch_score":0.9}):
            with self.assertRaises(ValueError): stable_object_id(**{**kwargs,"identity_parts":bad})
    def test_prefix_replay_matches_full_history_at_cutoff(self):
        prefix=CausalObjectRegistry(); full=CausalObjectRegistry(); early=self.make_object(SourceObjectType.POI); prefix.add(early); full.add(early)
        future=CausalSourceObject.formed(object_type=SourceObjectType.FVG,symbol="BTC-USDT-SWAP",timeframe="1H",direction="LONG",formation_at=T0+timedelta(hours=5),known_at=T0+timedelta(hours=6),identity_parts={"left":20,"right":22},provenance="unit-test"); full.add(future); cutoff=T0+timedelta(hours=3); self.assertEqual([o.object_id for o in prefix.objects_known_by(cutoff)],[o.object_id for o in full.objects_known_by(cutoff)])
    def test_future_mutation_keeps_old_identity_and_state(self):
        obj=self.make_object(SourceObjectType.LIQUIDITY_POOL); mutated=obj.invalidate(T0+timedelta(hours=8),"LATER_SWEEP"); self.assertEqual(mutated.object_id,obj.object_id); self.assertIsNone(mutated.state_at(T0+timedelta(hours=3)).invalidated_at)
    def test_closed_candle_only(self):
        closed=Candle(T0,T0+timedelta(minutes=15),100,102,99,101,True); require_closed_candles([closed],decision_at=T0+timedelta(minutes=15)); unfinished=Candle(T0+timedelta(minutes=15),T0+timedelta(minutes=30),101,103,100,102,False)
        with self.assertRaises(ValueError): require_closed_candles([closed,unfinished],decision_at=T0+timedelta(minutes=30))
        future=Candle(T0+timedelta(minutes=15),T0+timedelta(minutes=30),101,103,100,102,True)
        with self.assertRaises(ValueError): require_closed_candles([closed,future],decision_at=T0+timedelta(minutes=20))
    def test_contract_covers_stage_one_object_types(self):
        self.assertEqual({i.value for i in SourceObjectType},{"swing","structure","liquidity_pool","poi","ob","breaker","sfp","stb_bts","range","fvg","setup","physical_idea"})
if __name__=="__main__": unittest.main()
