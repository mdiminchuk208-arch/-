import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.replay import (
    EngineMode,
    QualifiedLevels,
    SourceQualification,
    _source_qualification_blocker,
    evaluate_snapshot,
)


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

    def qualification_for(self, known_at, **changes):
        values = dict(
            known_at=known_at,
            poi_kind='ORDER_BLOCK',
            entry_path='DIRECT_OB',
            poi_source='TEST_MANUAL_SOURCE_ASSERTION',
            structure_path_confirmed=True,
            order_flow_aligned=True,
            opposing_liquidity_cleared=True,
            premium_discount_valid=True,
            fresh_untested=True,
            evidence=('TEST_SOURCE_POI', 'TEST_ORDER_FLOW', 'TEST_LIQUIDITY_MAP'),
        )
        values.update(changes)
        return SourceQualification(**values)

    def repeat_ob_qualification_for(self, known_at, **changes):
        values = dict(
            fresh_untested=False,
            repeat_test_ltf_reaction_confirmed=True,
            repeat_test_ltf_reaction_known_at=known_at - timedelta(minutes=1),
            repeat_test_ltf_reaction_evidence=('TEST_CAUSAL_LTF_REACTION',),
        )
        values.update(changes)
        return self.qualification_for(known_at, **values)

    def levels_for(self, signal, known_at, *, qualification=True):
        zone = signal.entry_zone
        if signal.direction == Direction.LONG:
            stop, targets = zone.low - 2, (zone.high + 5, zone.high + 10, zone.high + 15)
        else:
            stop, targets = zone.high + 2, (zone.low - 5, zone.low - 10, zone.low - 15)
        source = self.qualification_for(known_at) if qualification else None
        return QualifiedLevels(known_at, stop, targets, 'SOURCE_OB_EXTREME',
                               'CALLER_QUALIFIED_OPPOSING_POIS', source)

    def test_levels_without_source_context_cannot_unlock_ready(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        result = self.snapshot(qualified_levels={waiting.signal_id: self.levels_for(waiting, self.end, qualification=False)})
        signal = next(s for s in result.signals if s.signal_id == waiting.signal_id)
        self.assertEqual(signal.status, 'WAITING_FOR_SOURCE_QUALIFICATION')
        self.assertEqual(signal.level_blocking_reasons, ('SOURCE_QUALIFICATION_MISSING',))
        self.assertIsNone(signal.stop_loss)
        self.assertEqual(signal.targets, ())

    def test_each_source_context_gate_fails_closed(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        cases = {
            'structure_path_confirmed': 'SOURCE_STRUCTURE_PATH_NOT_CONFIRMED',
            'order_flow_aligned': 'SOURCE_ORDER_FLOW_NOT_ALIGNED',
            'opposing_liquidity_cleared': 'LIQUIDITY_AGAINST_SETUP',
            'premium_discount_valid': 'SOURCE_PREMIUM_DISCOUNT_NOT_VALID',
            'fresh_untested': 'SOURCE_POI_NOT_FRESH',
        }
        for field, blocker in cases.items():
            with self.subTest(field=field):
                levels = self.levels_for(waiting, self.end)
                levels = replace(levels, qualification=replace(levels.qualification, **{field: False}))
                result = self.snapshot(qualified_levels={waiting.signal_id: levels})
                signal = next(s for s in result.signals if s.signal_id == waiting.signal_id)
                self.assertEqual(signal.status, 'WAITING_FOR_SOURCE_QUALIFICATION')
                self.assertEqual(signal.level_blocking_reasons, (blocker,))

    def test_source_levels_unlock_only_virtual_signal_after_availability(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        future = self.levels_for(waiting, self.end + timedelta(minutes=1))
        unavailable = self.snapshot(qualified_levels={waiting.signal_id: future})
        self.assertEqual(next(s for s in unavailable.signals if s.signal_id == waiting.signal_id).status, 'WAITING_FOR_SOURCE_LEVELS')
        levels = replace(future, known_at=self.end,
                         qualification=replace(future.qualification, known_at=self.end))
        available = self.snapshot(qualified_levels={waiting.signal_id: levels})
        signal = next(s for s in available.signals if s.signal_id == waiting.signal_id)
        self.assertEqual(signal.status, 'READY_FOR_VIRTUAL_ENTRY')
        self.assertEqual(signal.score, 100)
        self.assertEqual(signal.targets, levels.targets)
        self.assertEqual(signal.source_poi_kind, 'ORDER_BLOCK')
        self.assertEqual(signal.source_entry_path, 'DIRECT_OB')
        self.assertEqual(signal.source_qualification_known_at, self.end)
        self.assertGreater(len(signal.source_qualification_evidence), 0)
        self.assertIn('SOURCE_POI_FRESH', signal.reasons)
        self.assertFalse(signal.trade_entry_allowed)

    def test_repeated_order_block_requires_separate_causal_ltf_reaction(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        levels = self.levels_for(waiting, self.end)
        unproved = replace(levels, qualification=replace(levels.qualification, fresh_untested=False))
        blocked = self.snapshot(qualified_levels={waiting.signal_id: unproved})
        blocked_signal = next(s for s in blocked.signals if s.signal_id == waiting.signal_id)
        self.assertEqual(blocked_signal.status, 'WAITING_FOR_SOURCE_QUALIFICATION')
        self.assertEqual(blocked_signal.level_blocking_reasons, ('SOURCE_POI_NOT_FRESH',))

        repeated = replace(levels, qualification=self.repeat_ob_qualification_for(self.end))
        allowed = self.snapshot(qualified_levels={waiting.signal_id: repeated})
        signal = next(s for s in allowed.signals if s.signal_id == waiting.signal_id)
        self.assertEqual(signal.status, 'READY_FOR_VIRTUAL_ENTRY')
        self.assertIn('SOURCE_OB_REPEAT_TEST_LTF_REACTION_CONFIRMED', signal.reasons)
        self.assertIn('TEST_CAUSAL_LTF_REACTION', signal.source_qualification_evidence)
        self.assertNotIn('SOURCE_POI_FRESH', signal.reasons)
        self.assertFalse(signal.trade_entry_allowed)

    def test_repeated_order_block_gate_is_symmetric_for_long_and_short(self):
        qualification = self.repeat_ob_qualification_for(self.end)
        for direction in (Direction.LONG, Direction.SHORT):
            with self.subTest(direction=direction):
                self.assertIsNone(_source_qualification_blocker(
                    qualification,
                    direction=direction,
                    htf_minutes=60,
                    ltf_minutes=5,
                ))

    def test_repeated_order_block_proof_is_fail_closed_and_causal(self):
        with self.assertRaises(ValueError):
            self.repeat_ob_qualification_for(
                self.end,
                repeat_test_ltf_reaction_known_at=self.end + timedelta(minutes=1),
            )
        with self.assertRaises(ValueError):
            self.repeat_ob_qualification_for(
                self.end,
                repeat_test_ltf_reaction_evidence=(),
            )
        with self.assertRaises(ValueError):
            self.qualification_for(
                self.end,
                fresh_untested=False,
                repeat_test_ltf_reaction_confirmed=False,
                repeat_test_ltf_reaction_known_at=self.end - timedelta(minutes=1),
                repeat_test_ltf_reaction_evidence=('TEST_CAUSAL_LTF_REACTION',),
            )
        with self.assertRaises(ValueError):
            self.repeat_ob_qualification_for(self.end, fresh_untested=True)

    def test_demand_supply_cannot_use_order_block_repeat_test_exception(self):
        for poi_kind, direction in (('DEMAND', Direction.LONG), ('SUPPLY', Direction.SHORT)):
            with self.subTest(poi_kind=poi_kind):
                qualification = self.qualification_for(
                    self.end,
                    poi_kind=poi_kind,
                    fresh_untested=False,
                )
                self.assertEqual(_source_qualification_blocker(
                    qualification,
                    direction=direction,
                    htf_minutes=60,
                    ltf_minutes=5,
                ), 'SOURCE_POI_NOT_FRESH')
                with self.assertRaises(ValueError):
                    self.repeat_ob_qualification_for(self.end, poi_kind=poi_kind)

    def test_demand_supply_direction_and_conservative_tf_are_enforced(self):
        waiting = next(s for s in self.snapshot().signals if s.status == 'WAITING_FOR_SOURCE_LEVELS')
        wrong_kind = 'SUPPLY' if waiting.direction == Direction.LONG else 'DEMAND'
        levels = self.levels_for(waiting, self.end)
        levels = replace(levels, qualification=replace(levels.qualification, poi_kind=wrong_kind))
        result = self.snapshot(qualified_levels={waiting.signal_id: levels})
        signal = next(s for s in result.signals if s.signal_id == waiting.signal_id)
        expected = 'SUPPLY_REQUIRES_SHORT' if waiting.direction == Direction.LONG else 'DEMAND_REQUIRES_LONG'
        self.assertEqual(signal.level_blocking_reasons, (expected,))

        levels = self.levels_for(waiting, self.end)
        levels = replace(levels, qualification=replace(levels.qualification, entry_path='CONSERVATIVE_HTF_LTF'))
        result = self.snapshot(qualified_levels={waiting.signal_id: levels})
        signal = next(s for s in result.signals if s.signal_id == waiting.signal_id)
        self.assertEqual(signal.level_blocking_reasons,
                         ('CONSERVATIVE_HTF_LTF_TIMEFRAME_OUT_OF_SOURCE_RANGE',))

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

    def test_qualified_input_validates_timestamp_prices_and_context(self):
        with self.assertRaises(ValueError):
            QualifiedLevels(datetime(2026, 1, 1), 95, (110, 120, 130), 'stop', 'targets')
        with self.assertRaises(ValueError):
            QualifiedLevels(self.end, float('nan'), (110, 120, 130), 'stop', 'targets')
        with self.assertRaises(ValueError):
            self.qualification_for(self.end, poi_kind='UNKNOWN')
        with self.assertRaises(ValueError):
            self.qualification_for(self.end, evidence=())
        future_context = self.qualification_for(self.end + timedelta(minutes=1))
        with self.assertRaises(ValueError):
            QualifiedLevels(self.end, 95, (110, 120, 130), 'stop', 'targets', future_context)