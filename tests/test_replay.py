import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.replay import EngineMode, QualifiedLevels, evaluate_snapshot


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def histories():
    rng = random.Random(7)
    ltf, price = [], 100.0
    for i in range(600):
        end = max(20, price + rng.uniform(-3, 3))
        t = BASE + timedelta(minutes=i)
        ltf.append(Candle(t, t + timedelta(minutes=1), price,
                          max(price, end) + rng.uniform(.1, 2), min(price, end) - rng.uniform(.1, 2), end))
        price = end
    htf = []
    for i in range(0, len(ltf), 5):
        batch = ltf[i:i + 5]
        htf.append(Candle(batch[0].open_time, batch[-1].close_time, batch[0].open,
                          max(c.high for c in batch), min(c.low for c in batch), batch[-1].close))
    return {1: ltf, 5: htf}


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = histories()
        cls.end = cls.data[1][-1].close_time

    def snapshot(self, data=None, as_of=None, **kwargs):
        return evaluate_snapshot(self.data if data is None else data, symbol='TEST',
                                 as_of=as_of or self.end, htf_minutes=5, ltf_minutes=1, **kwargs)

    def test_identical_history_is_deterministic_with_nonempty_signals(self):
        first, second = self.snapshot(), self.snapshot()
        self.assertEqual(first, second)
        self.assertGreater(len(first.signals), 0)

    def test_future_candles_cannot_change_past_snapshot(self):
        cutoff = BASE + timedelta(minutes=300)
        prefix = {tf: [c for c in cs if c.close_time <= cutoff] for tf, cs in self.data.items()}
        self.assertEqual(self.snapshot(as_of=cutoff), self.snapshot(prefix, cutoff))
        mutated = {tf: [replace(c, open=c.open * 2, high=c.high * 2, low=c.low * 2, close=c.close * 2)
                        if c.close_time > cutoff else c for c in cs] for tf, cs in self.data.items()}
        self.assertEqual(self.snapshot(as_of=cutoff), self.snapshot(mutated, cutoff))

    def test_invalidated_setup_never_resurrects_on_later_snapshots(self):
        terminal, checked = set(), 0
        for minute in range(150, 601, 15):
            for signal in self.snapshot(as_of=BASE + timedelta(minutes=minute)).signals:
                if signal.signal_id in terminal:
                    self.assertEqual(signal.status, 'INVALIDATED')
                    checked += 1
                if signal.status == 'INVALIDATED':
                    terminal.add(signal.signal_id)
        self.assertGreater(checked, 0)

    def test_signals_are_causal_and_fail_closed_without_source_levels(self):
        s = self.snapshot()
        for signal in s.signals:
            self.assertLess(signal.sfp_time, signal.bos_time)
            self.assertLessEqual(signal.bos_time, signal.event_time)
            self.assertEqual(signal.event_time, self.end)
            self.assertFalse(signal.trade_entry_allowed)
            self.assertNotEqual(signal.status, 'READY_FOR_VIRTUAL_ENTRY')

    def levels_for(self, signal, known_at):
        zone = signal.entry_zone
        if signal.direction == Direction.LONG:
            stop, targets = zone.low - 2, (zone.high + 5, zone.high + 10, zone.high + 15)
        else:
            stop, targets = zone.high + 2, (zone.low - 5, zone.low - 10, zone.low - 15)
        return QualifiedLevels(known_at, stop, targets, 'SOURCE_OB_EXTREME', 'CALLER_QUALIFIED_OPPOSING_POIS')

    def test_source_levels_unlock_only_virtual_signal_after_availability(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        future = self.levels_for(waiting, self.end + timedelta(minutes=1))
        unavailable = self.snapshot(qualified_levels={waiting.signal_id: future})
        self.assertEqual(next(s for s in unavailable.signals if s.signal_id == waiting.signal_id).status, 'WAITING_FOR_SOURCE_LEVELS')
        levels = replace(future, known_at=self.end)
        available = self.snapshot(qualified_levels={waiting.signal_id: levels})
        signal = next(s for s in available.signals if s.signal_id == waiting.signal_id)
        self.assertEqual(signal.status, 'READY_FOR_VIRTUAL_ENTRY')
        self.assertEqual(signal.score, 100)
        self.assertEqual(signal.targets, levels.targets)
        self.assertFalse(signal.trade_entry_allowed)

    def test_invalidated_context_cannot_be_enabled_by_qualified_levels(self):
        dead = next(s for s in self.snapshot().signals if s.status == 'INVALIDATED' and s.entry_zone)
        result = self.snapshot(qualified_levels={dead.signal_id: self.levels_for(dead, self.end)})
        self.assertEqual(next(s for s in result.signals if s.signal_id == dead.signal_id).status, 'INVALIDATED')

    def test_end_to_end_qualified_snapshot_to_virtual_tp_management(self):
        from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        levels = self.levels_for(waiting, self.end)
        snapshot = self.snapshot(qualified_levels={waiting.signal_id: levels})
        ready = next(s for s in snapshot.signals if s.signal_id == waiting.signal_id)
        portfolio = VirtualPortfolio()
        portfolio.step({'TEST': self.data[1][-1]}, [ready])
        t, entry = self.end, ready.optimal_entry
        portfolio.step({'TEST': Candle(t, t + timedelta(minutes=1), entry, entry + .1, entry - .1, entry)})
        self.assertIn('TEST', portfolio.positions)
        for i, target in enumerate(ready.targets, start=1):
            t = self.end + timedelta(minutes=i)
            portfolio.step({'TEST': Candle(t, t + timedelta(minutes=1), target, target + .1, target - .1, target)})
        self.assertEqual(portfolio.positions, {})
        self.assertEqual([d.reason for d in portfolio.journal if d.action == 'VIRTUAL_EXIT'], ['TP1', 'TP2', 'TP3'])
        self.assertTrue(all(not d.trade_entry_allowed for d in portfolio.journal))
        self.assertEqual([d.time for d in portfolio.journal], sorted(d.time for d in portfolio.journal))

    def test_bad_source_target_order_is_rejected(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        levels = self.levels_for(waiting, self.end)
        with self.assertRaises(ValueError):
            self.snapshot(qualified_levels={waiting.signal_id: replace(levels, targets=tuple(reversed(levels.targets)))})

    def test_shadow_has_identical_analysis_and_no_trade_permission(self):
        backtest, shadow = self.snapshot(), self.snapshot(mode='SHADOW')
        self.assertEqual(backtest.mtf, shadow.mtf)
        self.assertEqual(backtest.ranges, shadow.ranges)
        self.assertTrue(all(s.mode == EngineMode.SHADOW and not s.trade_entry_allowed for s in shadow.signals))

    def test_live_and_paper_modes_are_rejected(self):
        for mode in ('LIVE', 'PAPER'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.snapshot(mode=mode)

    def test_invalid_history_is_rejected(self):
        for kind in ('gap', 'duplicate', 'reverse', 'unfinished', 'wrong_duration', 'zero_price'):
            data = {tf: list(cs) for tf, cs in self.data.items()}
            if kind == 'gap':
                del data[1][3]
            elif kind == 'duplicate':
                data[1].insert(3, data[1][2])
            elif kind == 'reverse':
                data[1].reverse()
            elif kind == 'unfinished':
                data[1][3] = replace(data[1][3], is_closed=False)
            elif kind == 'wrong_duration':
                data[1][3] = replace(data[1][3], close_time=data[1][3].close_time + timedelta(seconds=1))
            else:
                data[1][3] = replace(data[1][3], low=0)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.snapshot(data)

    def test_empty_history_is_safe(self):
        self.assertEqual(self.snapshot({1: [], 5: []}).signals, ())

    def test_qualified_input_validates_timestamp_and_prices(self):
        with self.assertRaises(ValueError):
            QualifiedLevels(datetime(2026, 1, 1), 95, (110, 120, 130), 'stop', 'targets')
        with self.assertRaises(ValueError):
            QualifiedLevels(self.end, float('nan'), (110, 120, 130), 'stop', 'targets')
