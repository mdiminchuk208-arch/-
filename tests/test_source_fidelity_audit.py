from __future__ import annotations

import copy
import sys
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from test_medium_term import T, fixture

from crypto_bot.common.models import Candle

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_source_fidelity_exits import exit_spec, simulate_fixed_trade
from audit_source_fidelity_state import source_snapshot


class SourceFidelityAuditTests(unittest.TestCase):
    def seed(self):
        engine,parent,raid=fixture()
        engine._emit('OB_DIRECT_FIRST_TEST',60,15,parent,parent,T+timedelta(hours=4),
                     'FROZEN',1,T+timedelta(hours=2),raid,entry_tf=60)
        signal=engine.signals[0]
        entry=signal.entry*1.0002
        trade={'trade_id': signal.signal_id,'signal_id': signal.signal_id,'symbol': 'BTCUSDT',
            'direction': 'LONG','entry_time': (T+timedelta(hours=4,minutes=15)).isoformat(),
            'entry_interval_start': (T+timedelta(hours=4)).isoformat(),
            'entry_interval_end': (T+timedelta(hours=4,minutes=15)).isoformat(),
            'theoretical_entry': signal.entry,'actual_entry_after_slippage': entry,
            'quantity': 1.,'initial_equity': 1170.,'entry_fee': entry*.0006,
            'stop': signal.stop,'risk_amount': 10.,'fill_model': 'RESTING_LIMIT_TOUCH',
            'htf': 60,'ltf': 15,'targets': list(signal.targets),'source_setup': signal.setup_type}
        return signal,trade

    def bar(self,index,opening,high,low,close):
        start=T+timedelta(hours=4,minutes=15*index)
        return Candle(start,start+timedelta(minutes=15),opening,high,low,close)

    def test_entry_bar_favourable_high_cannot_manufacture_tp(self):
        s,t=self.seed();bars=[self.bar(0,102,135,99,101)]
        for model in ['C_CANONICAL','D_NO_BE','B1_FULL_BASELINE_FIRST_TARGET']:
            r=simulate_fixed_trade(t,s,bars,[],model=model)
            self.assertEqual(r['status'],'OPEN')
            self.assertEqual(r['fills'],[])
            self.assertLess(r['MFE'],2)

    def test_stop_first_preserves_adverse_entry_envelope(self):
        s,t=self.seed()
        r=simulate_fixed_trade(t,s,[self.bar(0,102,135,85,130)],[],model='C_CANONICAL')
        self.assertEqual(r['exit_reason'],'STOP_FIRST_CONSERVATIVE')
        self.assertEqual(len(r['fills']),1)

    def test_tp1_be_and_no_be_differ_without_future_filter(self):
        s,t=self.seed()
        bars=[self.bar(0,102,114,99,111),self.bar(1,112,132,105,130)]
        c=simulate_fixed_trade(t,s,bars,[],model='C_CANONICAL')
        d=simulate_fixed_trade(t,s,bars,[],model='D_NO_BE')
        self.assertEqual(c['exit_reason'],'BREAKEVEN_SAME_BAR_CONSERVATIVE')
        self.assertEqual(d['exit_reason'],'TP3')
        self.assertGreater(d['net_pnl'],c['net_pnl'])
        self.assertIsNone(d['new_breakeven'])

    def test_gap_stop_fills_adversely_at_open(self):
        s,t=self.seed()
        bars=[self.bar(0,102,103,99,101),self.bar(1,80,85,75,82)]
        r=simulate_fixed_trade(t,s,bars,[],model='D_NO_BE')
        self.assertEqual(r['fills'][0]['reference_price'],80)

    def test_structural_exit_is_observable_close_and_costs_reconcile(self):
        s,t=self.seed();bars=[self.bar(0,102,103,99,101)]
        event={'known_at': bars[0].close_time.isoformat(),'price': 101,'reason': 'BODY_DEATH'}
        r=simulate_fixed_trade(t,s,bars,[event],model='D_NO_BE')
        self.assertEqual(r['exit_time'],event['known_at'])
        self.assertEqual(r['exit_reason'],'STRUCTURAL_BODY_DEATH')
        self.assertAlmostEqual(r['gross_pnl']-r['fees_total'],r['net_pnl'])
        self.assertAlmostEqual(sum(f['quantity'] for f in r['fills']),t['quantity'])

    def test_prefix_future_mutation_and_modes_match(self):
        s,t=self.seed();bars=[self.bar(0,102,103,99,101),self.bar(1,101,135,95,130)]
        cut=bars[0].close_time
        mutated=[bars[0],replace(bars[1],open=404,high=540,low=380,close=520)]
        for model in ['C_CANONICAL','D_NO_BE','B1_FULL_BASELINE_FIRST_TARGET']:
            a=simulate_fixed_trade(t,s,bars,[],model=model,cutoff=cut)
            b=simulate_fixed_trade(t,s,bars[:1],[],model=model,cutoff=cut)
            c=simulate_fixed_trade(t,s,mutated,[],model=model,cutoff=cut,mode='SHADOW')
            self.assertEqual(a,b)
            self.assertEqual(b,c)
            self.assertFalse(a['trade_entry_allowed'])

    def test_no_fta_is_undefined_instead_of_far_target_substitution(self):
        s,_=self.seed()
        self.assertIsNone(exit_spec(s,{'old_source_fta':None},'B2_FULL_OLD_SOURCE_FTA'))

    def test_open_remainder_not_force_closed(self):
        s,t=self.seed();bars=[self.bar(0,102,115,99,111)]
        r=simulate_fixed_trade(t,s,bars,[],model='A_SOURCE_PERMITTED_EXIT_DIAGNOSTIC',
                               target_prices=(110,150),fractions=(.8,.2))
        self.assertEqual(r['status'],'OPEN')
        self.assertEqual(len(r['fills']),1)
        self.assertAlmostEqual(r['fills'][0]['quantity'],.8)
        self.assertNotIn('exit_time',r)

    def test_state_snapshot_must_be_frozen_before_future_bos_updates(self):
        # Mirrors the actual read-only snapshot boundary, not a trade rule.
        engine,_,_=fixture()
        for owner in engine.series.values():
            owner.bos={};owner.conf={}
        req={'id':'X','stage':'NO_HTF_CONTEXT','rejection':{'discovery':{'parent_id':'NONE'}}}
        for owner in engine.series.values():owner.zone_registry={}
        raw=source_snapshot(engine,req,T+timedelta(hours=5))
        frozen=copy.deepcopy(raw)
        engine.series[60].bos['LONG']={'known_at':T+timedelta(days=1)}
        self.assertEqual(frozen['timeframe_states'][60]['bos'],{})


if __name__=='__main__':
    unittest.main()
