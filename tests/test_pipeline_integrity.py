"""Regression checks for closed-candle identity before strategy evaluation."""
from dataclasses import replace
from datetime import timedelta
import unittest

from crypto_bot.strategy.market_analysis import analyze_market, MarketAnalysisError
from crypto_bot.strategy.range_engine import analyze_ranges, RangeAnalysisError
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio
from test_virtual_portfolio import bar, signal


class PipelineIntegrityTests(unittest.TestCase):
    def test_market_gap_cannot_be_treated_as_next_confirmation_candle(self):
        with self.assertRaises(MarketAnalysisError):
            analyze_market([bar(0),bar(2)],timeframe_minutes=5)

    def test_market_declared_timeframe_must_match_real_duration(self):
        with self.assertRaises(MarketAnalysisError):
            analyze_market([bar(0),bar(1)],timeframe_minutes=60)

    def test_range_gap_cannot_resolve_a_sweep(self):
        candles=[bar(0),bar(1)]
        with self.assertRaises(RangeAnalysisError):
            analyze_ranges([bar(0),bar(2)],analyze_market(candles))

    def test_fractional_minute_execution_clock_is_rejected_atomically(self):
        candle=replace(bar(0),close_time=bar(0).open_time+timedelta(seconds=330))
        p=VirtualPortfolio()
        with self.assertRaises(ValueError):p.step({'TEST':candle})
        self.assertEqual(p.equity_curve,[])

    def test_unknown_signal_state_is_rejected_atomically(self):
        p=VirtualPortfolio()
        with self.assertRaises(ValueError):
            p.step({'TEST':bar(0)},[replace(signal(),status='MALFORMED_STATE')])
        self.assertEqual(p.journal,())

    def test_duplicate_identity_conflict_is_rejected_before_accounting(self):
        p=VirtualPortfolio()
        with self.assertRaises(ValueError):
            p.step({'TEST':bar(0)},[signal(),replace(signal(),status='INVALIDATED')])
        self.assertEqual(p.equity_curve,[])

    def test_completed_identity_rejection_is_explicit(self):
        p=VirtualPortfolio()
        p.step({'TEST':bar(0)},[signal()])
        p.step({'TEST':bar(1)},[signal(1)])
        self.assertTrue(any(d.action=='SETUP_IGNORED' and d.reason=='CONSUMED_SETUP_ID'
                            for d in p.journal))

    def test_ready_optimal_entry_must_be_inside_zone(self):
        for entry in (None,float('nan'),200):
            p=VirtualPortfolio()
            with self.subTest(entry=entry),self.assertRaises(ValueError):
                p.step({'TEST':bar(0)},[replace(signal(),optimal_entry=entry)])
            self.assertEqual(p.journal,())


if __name__=='__main__':unittest.main()
