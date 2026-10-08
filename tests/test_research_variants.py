from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

from crypto_bot.common.models import Candle
from crypto_bot.strategy import auto_levels, historical_replay, trade_plan
from crypto_bot.strategy.trade_plan import PriceZone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from research_variants import isolated_variant, touch_variant
from run_research_execution_scenarios import restore_signal
from run_historical_portfolio import canonical
from crypto_bot.strategy.replay import StrategySignal
from dataclasses import asdict
import json

START = datetime(2020, 1, 1, tzinfo=timezone.utc)


class ResearchVariantTests(unittest.TestCase):
    def test_saved_frozen_signal_restores_exact_geometry_and_knowledge_times(self):
        from crypto_bot.common.models import Direction
        signal=StrategySignal('id','BTCUSDT',60,5,Direction.LONG,START,START,START,
            'READY_FOR_VIRTUAL_ENTRY',100,('evidence',),entry_zone=PriceZone(100,102),
            optimal_entry=102,stop_loss=98,targets=(110,115,120))
        self.assertEqual(restore_signal(json.loads(canonical(asdict(signal)))),signal)

    def test_touch_variants_distinguish_boundary_and_body_with_causal_cutoff(self):
        a=Candle(START,START+timedelta(minutes=5),103,105,102,104,True)
        b=Candle(a.close_time,a.close_time+timedelta(minutes=5),100,104,99,101,True)
        index=auto_levels._TouchIndex([a,b])
        zone=PriceZone(100,102)
        self.assertEqual(index.first_touch(zone,START,a.close_time),a.close_time)
        self.assertIsNone(touch_variant(index,zone,START,a.close_time,'EXCLUSIVE_WICK'))
        self.assertIsNone(touch_variant(index,zone,START,a.close_time,'BODY'))
        self.assertEqual(touch_variant(index,zone,START,b.close_time,'BODY'),b.close_time)

    def test_runtime_isolation_restores_every_patch_on_error(self):
        before=(trade_plan.OTE_SHALLOW,trade_plan.OTE_DEEP,auto_levels._TouchIndex.first_touch,
                historical_replay.derive_automatic_levels)
        with self.assertRaises(RuntimeError):
            with isolated_variant('FRESH_BODY',[]) as policy:
                self.assertEqual(policy.min_body_fraction,.6)
                self.assertIsNot(auto_levels._TouchIndex.first_touch,before[2])
                raise RuntimeError('test interrupted research')
        after=(trade_plan.OTE_SHALLOW,trade_plan.OTE_DEEP,auto_levels._TouchIndex.first_touch,
               historical_replay.derive_automatic_levels)
        self.assertEqual(before,after)


if __name__ == '__main__':
    unittest.main()
