from dataclasses import replace
from datetime import datetime
from pathlib import Path
import json
import unittest

from crypto_bot.common.models import Candle

from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.replay import evaluate_snapshot
from test_replay import histories


def changes(data, auto=None, mode='BACKTEST'):
    states, out = {}, []
    for candle in data[1]:
        snap = evaluate_snapshot(data, symbol='TEST', as_of=candle.close_time,
            htf_minutes=5, ltf_minutes=1, auto_level_policy=auto, mode=mode)
        for s in snap.signals:
            signature = replace(s, event_time=data[1][0].close_time)
            if states.get(s.signal_id) != signature:
                states[s.signal_id] = signature
                out.append(s)
    return tuple(out)


class HistoricalReplayTests(unittest.TestCase):
    def test_ob_touch_known_before_geometry_cannot_rewind_signal_clock(self):
        # Unmodified ADAUSDT OHLC excerpt from the uploaded history. A watch
        # discovered at geometry resolution already has a past first touch.
        payload=json.loads((Path(__file__).parent/'fixtures/ada_historical_prefix.json').read_text())
        data={int(tf):[Candle(datetime.fromisoformat(row[0]),datetime.fromisoformat(row[1]),*row[2:])
                      for row in rows] for tf,rows in payload.items()}
        states,expected={},[]
        for candle in data[5]:
            for s in evaluate_snapshot(data,symbol='ADAUSDT',as_of=candle.close_time,
                                       auto_level_policy=AutoLevelPolicy()).signals:
                signature=replace(s,event_time=data[5][0].close_time)
                if states.get(s.signal_id)!=signature:
                    expected.append(s)
                    states[s.signal_id]=signature
        indexed,_=indexed_signal_updates(data,symbol='ADAUSDT',auto_level_policy=AutoLevelPolicy())
        self.assertGreater(len(expected),0)
        self.assertEqual(indexed,tuple(expected))

    def test_every_prefix_matches_reference_with_and_without_auto(self):
        data = histories()
        for auto in (None, AutoLevelPolicy()):
            with self.subTest(auto=auto):
                indexed, _ = indexed_signal_updates(data, symbol='TEST', htf_minutes=5,
                                                    ltf_minutes=1, auto_level_policy=auto)
                expected = changes(data, auto)
                self.assertGreater(len(expected), 0)
                self.assertEqual(indexed, expected)

    def test_future_changes_and_prefix_cannot_change_past_signals(self):
        data = histories()
        cutoff = data[1][449].close_time
        prefix = {tf:[c for c in cs if c.close_time<=cutoff] for tf,cs in data.items()}
        future = {tf:[replace(c, open=c.open*2, high=c.high*2, low=c.low*2, close=c.close*2)
                      if c.close_time>cutoff else c for c in cs] for tf,cs in data.items()}
        results=[]
        for sample in (data, prefix, future):
            updates, _ = indexed_signal_updates(sample,symbol='TEST',htf_minutes=5,ltf_minutes=1,
                                                auto_level_policy=AutoLevelPolicy())
            results.append(tuple(s for s in updates if s.event_time<=cutoff))
        self.assertGreater(len(results[0]),0)
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[0],results[2])

    def test_gap_unfinished_and_live_are_rejected(self):
        data=histories()
        for sample in ({**data,1:data[1][:40]+data[1][41:]},
                       {**data,1:[replace(data[1][0],is_closed=False),*data[1][1:]]}):
            with self.assertRaises(ValueError):
                indexed_signal_updates(sample,symbol='TEST',htf_minutes=5,ltf_minutes=1)
        with self.assertRaises(ValueError):
            indexed_signal_updates(data,symbol='TEST',htf_minutes=5,ltf_minutes=1,mode='LIVE')

    def test_shadow_signal_semantics_match(self):
        data=histories()
        results=[]
        for mode in ('BACKTEST','SHADOW'):
            updates,_=indexed_signal_updates(data,symbol='TEST',htf_minutes=5,ltf_minutes=1,
                                            mode=mode,auto_level_policy=AutoLevelPolicy())
            results.append(tuple(replace(s,mode='BACKTEST') for s in updates))
        self.assertEqual(*results)
