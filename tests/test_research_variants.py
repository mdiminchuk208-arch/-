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
from dataclasses import asdict, replace
import json
from tempfile import TemporaryDirectory
from research_structure_cache import structure_cache, validated_prefix_reuse
from test_replay import histories

START = datetime(2020, 1, 1, tzinfo=timezone.utc)


class ResearchVariantTests(unittest.TestCase):
    def test_seed_cache_excludes_future_and_falls_back_for_changed_history(self):
        series=tuple(Candle(START+timedelta(minutes=5*i),START+timedelta(minutes=5*(i+1)),
                           100+3*i,102+3*i,99+3*i,101+3*i,True) for i in range(12))
        original=auto_levels._seeds
        with validated_prefix_reuse({5:series}):
            for size in range(1,len(series)+1):
                self.assertEqual(auto_levels._seeds(series[:size]),original(series[:size]))
            changed=list(series[:6]);changed[3]=replace(changed[3],low=100)
            self.assertEqual(auto_levels._seeds(changed),original(changed))
        self.assertIs(auto_levels._seeds,original)

    def test_validated_prefix_reuse_is_exact_and_rejects_changed_interior(self):
        data=histories()
        kwargs=dict(symbol='TEST',htf_minutes=5,ltf_minutes=1,auto_level_policy=auto_levels.AutoLevelPolicy())
        expected=historical_replay.indexed_signal_updates(data,**kwargs)
        original=auto_levels._prefix
        with validated_prefix_reuse(data):
            self.assertEqual(historical_replay.indexed_signal_updates(data,**kwargs),expected)
            series=tuple(data[1]);cutoff=series[5].close_time
            self.assertEqual(auto_levels._prefix(series,cutoff),original(series,cutoff))
            corrupted=list(series)
            corrupted[3]=replace(corrupted[3],low=-1)
            with self.assertRaises(ValueError):
                auto_levels._prefix(corrupted,cutoff)
        self.assertIs(auto_levels._prefix,original)

    def test_cached_structural_reports_equal_uncached_frozen_outputs(self):
        data=histories()
        kwargs=dict(symbol='TEST',htf_minutes=5,ltf_minutes=1,auto_level_policy=auto_levels.AutoLevelPolicy())
        expected=historical_replay.indexed_signal_updates(data,**kwargs)
        with TemporaryDirectory() as directory:
            with structure_cache(Path(directory),{5:'fixture-5',1:'fixture-1'},'frozen-test'):
                first=historical_replay.indexed_signal_updates(data,**kwargs)
            with structure_cache(Path(directory),{5:'fixture-5',1:'fixture-1'},'frozen-test'):
                second=historical_replay.indexed_signal_updates(data,**kwargs)
            self.assertEqual(first,expected)
            self.assertEqual(second,expected)
            self.assertEqual(len(list(Path(directory).glob('*.structural.pickle.gz'))),5)

    def test_saved_frozen_signal_restores_exact_geometry_and_knowledge_times(self):
        from crypto_bot.common.models import Direction
        signal=StrategySignal('id','BTCUSDT',60,5,Direction.LONG,START,START,START,
            'READY_FOR_VIRTUAL_ENTRY',100,('evidence',),entry_zone=PriceZone(100,102),
            optimal_entry=102,stop_loss=98,targets=(110,115,120),
            source_qualification_known_at=START,source_poi_kind='ORDER_BLOCK',
            source_entry_path='DIRECT_OB',source_qualification_evidence=('ROUNDTRIP_SOURCE_CONTEXT',))
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

    def test_structure_cache_does_not_reuse_attached_geometry_across_ote_variants(self):
        data=histories()
        kwargs=dict(symbol='TEST',htf_minutes=5,ltf_minutes=1)
        with TemporaryDirectory() as directory:
            all_outputs=[]
            for variant in ('BASE','OTE_SHALLOW_0710'):
                with isolated_variant(variant) as policy:
                    expected=historical_replay.indexed_signal_updates(data,auto_level_policy=policy,**kwargs)
                with structure_cache(Path(directory),{5:'fixture-5',1:'fixture-1'},'frozen-test'):
                    with isolated_variant(variant) as policy:
                        cached=historical_replay.indexed_signal_updates(data,auto_level_policy=policy,**kwargs)
                self.assertEqual(cached,expected)
                all_outputs.append(expected)
            self.assertEqual(len(list(Path(directory).glob('*.structural.pickle.gz'))),6)
            self.assertNotEqual(all_outputs[0],all_outputs[1])


if __name__ == '__main__':
    unittest.main()