"""Integration checks for policy selection, causal gating and pending withdrawal."""
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch
import unittest

from crypto_bot.strategy.auto_levels import AutoLevelPolicy, AutomaticLevelResult
from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import derive_automatic_levels
from crypto_bot.strategy.replay import StrategySignal, evaluate_snapshot, opportunity_key
from crypto_bot.strategy.trade_plan import PriceZone
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio
from test_replay import histories
from test_virtual_portfolio import bar, signal


class AutoReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = histories()
        cls.end = cls.data[1][-1].close_time

    def snapshot(self, **kwargs):
        return evaluate_snapshot(self.data, symbol='TEST', as_of=self.end,
                                 htf_minutes=5, ltf_minutes=1, **kwargs)

    def test_default_does_not_invoke_experimental_detector(self):
        with patch('crypto_bot.strategy.replay.derive_automatic_levels') as detector:
            snapshot = self.snapshot()
        detector.assert_not_called()
        self.assertGreater(len(snapshot.signals), 0)
        self.assertTrue(all(s.level_policy == 'EXPLICIT_QUALIFIED_LEVELS_ONLY' for s in snapshot.signals))

    def test_explicit_and_automatic_sources_cannot_mix(self):
        with self.assertRaisesRegex(ValueError, 'cannot be combined'):
            self.snapshot(auto_level_policy=AutoLevelPolicy(), qualified_levels={'one': object()})

    def test_auto_blocked_reason_reaches_signal(self):
        blocked = AutomaticLevelResult(status='BLOCKED', blocked_reasons=('NO_CAUSAL_SWEEP',))
        with patch('crypto_bot.strategy.replay.derive_automatic_levels', return_value=blocked):
            snapshot = self.snapshot(auto_level_policy=AutoLevelPolicy())
        waiting = [s for s in snapshot.signals if s.status == 'WAITING_FOR_AUTO_LEVELS']
        self.assertGreater(len(waiting), 0)
        self.assertTrue(all(s.level_blocking_reasons == ('NO_CAUSAL_SWEEP',) for s in waiting))
        self.assertTrue(all('NO_CAUSAL_SWEEP' in s.reasons for s in waiting))
        self.assertTrue(all(not s.trade_entry_allowed for s in snapshot.signals))

    def ready_result(self, *args, **kwargs):
        # The detector has its own OHLC/evidence tests. This fixture isolates the
        # conversion into the shared signal contract. READY here means the research
        # detector completed its proxy gates, not that the source methodology did.
        opportunity = args[4]
        low, high = opportunity.entry_zone_low, opportunity.entry_zone_high
        if opportunity.expected_direction.value == 'long':
            stop, targets = low - 2, (high + 5, high + 10, high + 15)
        else:
            stop, targets = high + 2, (low - 5, low - 10, low - 15)
        return AutomaticLevelResult(status='READY', known_at=self.end, stop_loss=stop,
                                    targets=targets, stop_policy='SOURCE_OB_EXTREME',
                                    target_policy='THREE_OPPOSING_POIS_BACKTEST_PARAMETER')

    def test_ready_experiment_stays_research_only_and_fail_closed(self):
        with patch('crypto_bot.strategy.replay.derive_automatic_levels', side_effect=self.ready_result):
            snapshot = self.snapshot(auto_level_policy=AutoLevelPolicy())
        research_ready = [s for s in snapshot.signals
                          if 'AUTO_RESEARCH_PROXY_READY_NOT_SOURCE_QUALIFIED' in s.reasons]
        self.assertGreater(len(research_ready), 0)
        self.assertTrue(all(s.status == 'WAITING_FOR_SOURCE_LEVELS' for s in research_ready))
        self.assertTrue(all(s.score == 85 for s in research_ready))
        self.assertTrue(all(s.stop_loss is None and s.targets == () for s in research_ready))
        self.assertTrue(all(s.levels_known_at is None for s in research_ready))
        self.assertTrue(all(s.level_policy == 'AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION'
                            for s in research_ready))
        self.assertTrue(all(s.level_blocking_reasons == ('AUTO_RESEARCH_PROXY_NOT_SOURCE_QUALIFIED',)
                            for s in research_ready))
        self.assertTrue(all(s.status != 'READY_FOR_VIRTUAL_ENTRY' for s in snapshot.signals))
        self.assertTrue(all(not s.trade_entry_allowed for s in snapshot.signals))

    def test_future_detector_references_cannot_unlock_entry(self):
        def future(*args, **kwargs):
            return replace(self.ready_result(*args, **kwargs), known_at=self.end + timedelta(minutes=1))
        with patch('crypto_bot.strategy.replay.derive_automatic_levels', side_effect=future):
            snapshot = self.snapshot(auto_level_policy=AutoLevelPolicy())
        self.assertTrue(all(s.status != 'READY_FOR_VIRTUAL_ENTRY' for s in snapshot.signals))

    def test_real_auto_snapshot_is_deterministic_and_ignores_future_candles(self):
        cutoff = self.data[1][449].close_time
        prefix = {tf: [c for c in cs if c.close_time <= cutoff] for tf, cs in self.data.items()}
        mutated = {tf: [replace(c, open=c.open * 2, high=c.high * 2, low=c.low * 2, close=c.close * 2)
                        if c.close_time > cutoff else c for c in cs] for tf, cs in self.data.items()}
        args = dict(symbol='TEST', as_of=cutoff, htf_minutes=5, ltf_minutes=1,
                    auto_level_policy=AutoLevelPolicy())
        expected = evaluate_snapshot(prefix, **args)
        self.assertGreater(len(expected.signals), 0)
        self.assertEqual(expected, evaluate_snapshot(self.data, **args))
        self.assertEqual(expected, evaluate_snapshot(mutated, **args))

    def test_withdrawn_pending_setup_cannot_enter_on_later_bar(self):
        portfolio = VirtualPortfolio()
        portfolio.step({'TEST': bar(0)}, [signal()])
        self.assertIn('one', portfolio.pending)
        withdrawn = replace(signal(i=1), status='WAITING_FOR_AUTO_LEVELS', stop_loss=None, targets=(),
                            level_blocking_reasons=('OB_FIRST_TEST_CONSUMED',))
        portfolio.step({'TEST': bar(1, 105, 106, 104, 105)}, [withdrawn])
        self.assertEqual(portfolio.pending, {})
        portfolio.step({'TEST': bar(2)})
        self.assertEqual(portfolio.positions, {})
        self.assertFalse(any(d.action == 'VIRTUAL_ENTRY' for d in portfolio.journal))

    def test_research_proxy_cannot_be_manually_promoted_to_canonical_ready(self):
        from test_auto_levels import valid_case

        for direction in Direction:
            with self.subTest(direction=direction):
                case = valid_case(direction)
                levels = derive_automatic_levels(**case)
                self.assertEqual(levels.status, 'READY', levels.blocked_reasons)
                opp, end = case['opportunity'], case['as_of']
                zone = PriceZone(opp.entry_zone_low, opp.entry_zone_high)
                entry = (zone.low + zone.high) / 2
                with self.assertRaisesRegex(ValueError, 'explicitly source-qualified levels'):
                    StrategySignal(
                        opportunity_key('TEST', 60, 5, opp), 'TEST', 60, 5, direction, end,
                        opp.latest_sfp_time, opp.ltf_bos_event_time, 'READY_FOR_VIRTUAL_ENTRY', 100,
                        ('AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION', levels.target_policy),
                        entry_zone=zone, optimal_entry=entry, stop_loss=levels.stop_loss,
                        targets=levels.targets, entry_geometry_ready_time=opp.entry_geometry_ready_time,
                        levels_known_at=levels.known_at,
                        level_policy='AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION',
                        level_evidence=levels.evidence,
                    )

    def test_research_proxy_does_not_create_virtual_position(self):
        with patch('crypto_bot.strategy.replay.derive_automatic_levels', side_effect=self.ready_result):
            snapshot = self.snapshot(auto_level_policy=AutoLevelPolicy())
        research = next(s for s in snapshot.signals
                        if 'AUTO_RESEARCH_PROXY_READY_NOT_SOURCE_QUALIFIED' in s.reasons)
        portfolio = VirtualPortfolio()
        portfolio.step({'TEST': self.data[1][-1]}, [research])
        self.assertEqual(portfolio.positions, {})
        self.assertEqual(portfolio.pending, {})
        self.assertFalse(any(d.action == 'VIRTUAL_ENTRY' for d in portfolio.journal))
