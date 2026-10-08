"""Real OHLC touch execution, adverse ambiguity and causal capital accounting."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from crypto_bot.common.models import Direction
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy, VirtualPortfolio
from test_virtual_portfolio import bar, signal


class RestingLimitExecutionTests(unittest.TestCase):
    def portfolio(self, **kwargs):
        return VirtualPortfolio(policy=SimulationPolicy(fee_fraction=0, slippage_fraction=0, **kwargs))

    def ready(self, p, direction=Direction.LONG):
        p.step({'TEST': bar(0)}, [signal(direction=direction)])

    def test_signal_bar_touch_never_fills(self):
        p=self.portfolio()
        self.ready(p)
        self.assertFalse(p.trades)

    def test_actual_quote_touch_long_short_boundary_equality(self):
        for direction in Direction:
            p=self.portfolio();self.ready(p,direction)
            candle=bar(1,105,106,100,103) if direction==Direction.LONG else bar(1,95,100,94,97)
            p.step({'TEST':candle})
            trade=p.trades['one']
            self.assertEqual(trade['theoretical_entry'],100)
            self.assertEqual(trade['fill_model'],'RESTING_LIMIT_TOUCH')
            self.assertEqual(trade['entry_time'],candle.close_time)
            self.assertEqual(trade['entry_interval_start'],candle.open_time)
            self.assertFalse(p.trade_entry_allowed)

    def test_no_quote_touch_and_gap_below_zone_cannot_create_fill(self):
        for candle in (bar(1,105,106,101,103),bar(1,98,100,97,99)):
            p=self.portfolio();self.ready(p)
            p.step({'TEST':candle})
            self.assertFalse(p.trades)

    def test_no_fill_above_buy_limit_even_inside_execution_zone(self):
        p=self.portfolio();self.ready(p)
        p.step({'TEST':bar(1,100.5,101,100.1,100.2)})
        self.assertFalse(p.trades)

    def test_profitable_extreme_may_precede_touch_and_cannot_award_tp(self):
        for direction in Direction:
            p=self.portfolio();self.ready(p,direction)
            candle=bar(1,105,131,99,103) if direction==Direction.LONG else bar(1,95,101,69,97)
            p.step({'TEST':candle})
            self.assertFalse([d for d in p.journal if d.action=='VIRTUAL_EXIT'])
            self.assertEqual(p.trades['one']['MFE'],3)

    def test_adverse_stop_wins_unknown_entry_bar_order(self):
        for direction in Direction:
            p=self.portfolio();self.ready(p,direction)
            candle=bar(1,105,131,94,120) if direction==Direction.LONG else bar(1,95,106,69,80)
            p.step({'TEST':candle})
            self.assertEqual(p.trades['one']['exit_reason'],'STOP_FIRST_CONSERVATIVE')
            self.assertAlmostEqual(p.equity,9800)

    def test_close_after_touch_can_prove_tp_but_breakeven_wins_ambiguity(self):
        p=self.portfolio();self.ready(p)
        p.step({'TEST':bar(1,105,121,99,120)})
        self.assertEqual([d.reason for d in p.journal if d.action=='VIRTUAL_EXIT'],
                         ['TP1','BREAKEVEN_SAME_BAR_CONSERVATIVE'])

    def test_first_touch_fill_is_not_retroactively_erased_by_close_withdrawal(self):
        p=self.portfolio();self.ready(p)
        withdrawal=replace(signal(1),status='WAITING_FOR_AUTO_LEVELS',level_blocking_reasons=('OB_FIRST_TEST_ALREADY_CONSUMED',))
        p.step({'TEST':bar(1,105,106,99,103)},[withdrawal])
        self.assertIn('TEST',p.positions)
        self.assertNotIn('one',p.pending)

    def test_limit_admissions_do_not_use_preentry_open_or_future_close_profits(self):
        p=self.portfolio()
        names=('A','B','C','D')
        p.step({s:bar(0) for s in names},[signal(symbol=s,ident=s) for s in names])
        p.step({s:bar(1,120,131,99,130) for s in names})
        self.assertEqual(len(p.trades),3)
        self.assertTrue(any(d.signal_id=='D' and d.reason=='TOTAL_RISK_CAP_6_PERCENT' for d in p.journal))
        self.assertEqual([p.trades[s]['risk_amount'] for s in ('A','B','C')],[200]*3)

    def test_checkpoint_pending_and_open_limit_resume_matches_full_run(self):
        full=self.portfolio();self.ready(full)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pending.json'
            full.save_checkpoint(path)
            resumed=VirtualPortfolio.load_checkpoint(path)
            for p in (full,resumed):p.step({'TEST':bar(1,105,106,99,103)})
            self.assertEqual(full.snapshot(),resumed.snapshot())
            full.save_checkpoint(path);resumed=VirtualPortfolio.load_checkpoint(path)
            for p in (full,resumed):p.step({'TEST':bar(2,108,111,107,110)})
            self.assertEqual(full.snapshot(),resumed.snapshot())

    def test_explicit_legacy_policy_remains_open_only(self):
        p=self.portfolio(resting_limit_entries=False);self.ready(p)
        p.step({'TEST':bar(1,105,106,99,103)})
        self.assertFalse(p.trades)


if __name__=='__main__':
    unittest.main()
