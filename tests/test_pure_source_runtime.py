from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
import unittest
from crypto_bot.common.models import Candle
from crypto_bot.strategy.causal_objects import SourceObjectType
from crypto_bot.strategy.profile import PolicyClass,ProjectPolicyContaminationError,StrategyProfile,StrategyRuntimeConfig
from crypto_bot.strategy.pure_source_runtime import PureSourceRuntime
UTC=timezone.utc; T0=datetime(2026,1,1,tzinfo=UTC)
class FakeEngine:
    def __init__(self,symbol,series): self.symbol=symbol; self.series=series; self.setups=[]; self.signals=[]
    def advance(self,timeframe,index): self.series[timeframe].index=index
    def finish(self): return {"trade_entry_allowed":False}
class PureSourceRuntimeTests(unittest.TestCase):
    def series(self,closed=True):
        candle=Candle(T0,T0+timedelta(hours=1),100,102,99,101,closed); zone=SimpleNamespace(zone_id="zone-1",kind="ORDER_BLOCK",direction="LONG",low=99.0,high=100.0,formed_at=candle.close_time,known_at=candle.close_time,origin_index=0,invalidated_at=None)
        return SimpleNamespace(candles=[candle],index=-1,pools={},zone_registry={"zone-1":zone},events={},range_bounds={})
    def test_runtime_is_pure_source_and_never_live(self):
        runtime=PureSourceRuntime("BTC-USDT-SWAP",{60:self.series()},engine_factory=FakeEngine); runtime.advance(60,0); result=runtime.finish(); self.assertEqual(result["strategy_profile"],StrategyProfile.PURE_SOURCE.value); self.assertFalse(result["trade_entry_allowed"]); objects=runtime.registry.objects_known_by(T0+timedelta(hours=1)); self.assertEqual(len(objects),1); self.assertEqual(objects[0].object_type,SourceObjectType.ORDER_BLOCK); self.assertTrue(objects[0].formation_valid); self.assertFalse(objects[0].trade_eligible)
    def test_project_policy_cannot_be_applied(self):
        runtime=PureSourceRuntime("BTC-USDT-SWAP",{60:self.series()},engine_factory=FakeEngine)
        with self.assertRaises(ProjectPolicyContaminationError): runtime.apply_policy("ANTI_SCALP",PolicyClass.PROJECT_POLICY)
    def test_project_overlay_profile_cannot_construct_pure_runtime(self):
        cfg=StrategyRuntimeConfig(strategy_profile=StrategyProfile.PROJECT_OVERLAY)
        with self.assertRaises(ValueError): PureSourceRuntime("BTC-USDT-SWAP",{60:self.series()},config=cfg,engine_factory=FakeEngine)
    def test_unfinished_candle_is_rejected_before_engine_advance(self):
        runtime=PureSourceRuntime("BTC-USDT-SWAP",{60:self.series(False)},engine_factory=FakeEngine)
        with self.assertRaises(ValueError): runtime.advance(60,0)
if __name__=="__main__": unittest.main()
