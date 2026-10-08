import unittest
from dataclasses import replace
from crypto_bot.common.models import Direction
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio, SimulationPolicy
from crypto_bot.strategy.portfolio_statistics import portfolio_statistics
from test_virtual_portfolio import bar, signal


class PortfolioAccountingTests(unittest.TestCase):
    def portfolio(self, **kwargs):
        return VirtualPortfolio(equity=1170,policy=SimulationPolicy(**kwargs))

    def open(self,p,ident='one',i=0,direction=Direction.LONG):
        p.step({'TEST':bar(i)},[signal(i,ident=ident,direction=direction)])
        p.step({'TEST':bar(i+1)})
        return p.positions['TEST']

    def test_initial_balance_and_empty_statistics(self):
        p=self.portfolio()
        self.assertEqual((p.starting_balance,p.balance,p.equity,p.realized_pnl),(1170,1170,1170,0))
        stats=portfolio_statistics(p,[],['TEST'])
        self.assertIsNone(stats['profit_factor'])
        self.assertIsNone(stats['win_rate'])
        self.assertIsNone(stats['best_worst']['by_symbol']['best'])

    def test_entry_fee_is_paid_immediately_and_unrealized_is_marked(self):
        p=self.portfolio()
        pos=self.open(p)
        self.assertAlmostEqual(p.balance,1170-pos.quantity*pos.entry_price*.0006)
        self.assertAlmostEqual(p.unrealized_pnl,pos.quantity*(100-pos.entry_price))
        self.assertAlmostEqual(p.equity,p.balance+p.unrealized_pnl)
        self.assertAlmostEqual(p.allocated_margin,pos.quantity*pos.entry_price/3)
        self.assertAlmostEqual(p.available_equity,p.equity-p.allocated_margin)
        self.assertAlmostEqual(pos.quantity*p._loss_per_unit(pos.entry_price,pos.stop_loss,Direction.LONG),23.4)

    def test_partial_and_final_costs_reconcile_without_double_entry_fee(self):
        for direction in Direction:
            p=self.portfolio()
            self.open(p,direction=direction)
            for i,target in enumerate((110,120,130) if direction==Direction.LONG else (90,80,70),start=2):
                p.step({'TEST':bar(i,target,target+.1,target-.1,target)})
            t=p.trades['one']
            self.assertAlmostEqual(p.balance-1170,t['net_pnl'])
            self.assertAlmostEqual(p.realized_pnl,sum(d.balance_change for d in p.journal))
            self.assertAlmostEqual(t['net_pnl'],t['gross_pnl']-t['fees_total'])
            self.assertAlmostEqual(p.fees_paid,t['fees_total'])
            self.assertAlmostEqual(p.slippage_cost,t['slippage_total'])
            self.assertAlmostEqual(sum(f['entry_fee_allocation'] for f in t['fills']),t['entry_fee'])
            self.assertEqual([round(f['quantity']/t['quantity'],8) for f in t['fills']],[.4,.3,.3])
            self.assertGreaterEqual(t['max_equity_during_trade'],t['equity_after_trade'])

    def test_next_trade_compounds_after_profit_and_decompounds_after_loss(self):
        p=self.portfolio(fee_fraction=0,slippage_fraction=0)
        self.open(p)
        p.step({'TEST':bar(2,108,131,107,130)})
        profit_equity=p.equity
        self.open(p,'two',3)
        self.assertAlmostEqual(p.trades['two']['risk_amount'],profit_equity*.02)
        self.assertGreater(p.trades['two']['risk_amount'],23.4)
        p.step({'TEST':bar(5,100,101,94,95)})
        after_loss=p.equity
        self.open(p,'three',6)
        self.assertAlmostEqual(p.trades['three']['risk_amount'],after_loss*.02)
        self.assertLess(p.trades['three']['risk_amount'],p.trades['two']['risk_amount'])

    def test_open_pnl_changes_next_risk_without_using_future_close(self):
        p=self.portfolio(fee_fraction=0,slippage_fraction=0)
        p.step({'A':bar(0),'B':bar(0)},[signal(symbol='A',ident='a')])
        p.step({'A':bar(1),'B':bar(1)},[signal(1,symbol='B',ident='b')])
        p.step({'A':bar(2,105,131,104,130),'B':bar(2)})
        self.assertAlmostEqual(p.trades['b']['initial_equity'],1170+4.68*5)
        self.assertAlmostEqual(p.trades['b']['risk_amount'],(1170+4.68*5)*.02)

    def test_costs_are_reserved_before_margin_and_aggregate_admission(self):
        p=self.portfolio()
        names=['A','B','C','D']
        p.step({s:bar(0) for s in names},[signal(symbol=s,ident=s) for s in names])
        p.step({s:bar(1) for s in names})
        self.assertLessEqual(p.aggregate_stop_risk,p.equity*.06+1e-9)
        self.assertGreaterEqual(p.available_equity,0)
        self.assertTrue(any(d.reason=='TOTAL_RISK_CAP_6_PERCENT' for d in p.journal))

    def test_gap_bankruptcy_is_explicit_and_blocks_new_admissions(self):
        p=self.portfolio(fee_fraction=0,slippage_fraction=0)
        from crypto_bot.strategy.trade_plan import PriceZone
        p.step({'TEST':bar(0)},[replace(signal(),stop_loss=99,entry_zone=PriceZone(99.5,100.5))])
        p.step({'TEST':bar(1,100,100.1,99.9,100)})
        # Wide adverse gap, not a clamped nominal stop fill.
        p.step({'TEST':bar(2,1,2,.5,1)},[signal(2,ident='two')])
        self.assertTrue(p.trades['one']['adverse_gap'])
        self.assertGreater(p.trades['one']['net_pnl']*-1,p.trades['one']['risk_amount'])
        self.assertLess(p.balance,0)
        self.assertEqual(p.status,'BANKRUPT')
        p.step({'TEST':bar(3)})
        self.assertEqual(p.positions,{})
        self.assertEqual(len(p.trades),1)

    def test_drawdown_and_curve_match_marked_equity(self):
        p=self.portfolio(fee_fraction=0,slippage_fraction=0)
        self.open(p)
        p.step({'TEST':bar(2,105,106,104,105)})
        peak=p.equity
        p.step({'TEST':bar(3,100,101,99,100)})
        self.assertAlmostEqual(p.max_drawdown,(peak-p.equity)/peak)
        self.assertEqual(p.equity_curve[-1]['equity'],p.equity)
        self.assertEqual(p.equity_curve[-1]['balance'],p.balance)
