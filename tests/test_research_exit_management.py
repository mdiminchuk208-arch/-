from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import unittest

from crypto_bot.common.models import Direction
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio
from test_virtual_portfolio import bar, signal

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from research_exit_management import ExitResearchPortfolio, EXIT_VARIANTS
from run_historical_portfolio import canonical
from run_exit_research import paired_replays, verify_exit_future
from crypto_bot.strategy.virtual_portfolio import SimulationPolicy


def run_case(portfolio,bars,direction=Direction.LONG):
    for i,c in enumerate(bars):
        portfolio.step({'TEST':c},[signal(direction=direction)] if i==0 else [])
    return canonical(dict(trades=portfolio.trades,journal=[asdict(d) for d in portfolio.journal],equity=portfolio.equity_curve))


class ExitResearchTests(unittest.TestCase):
    def test_paired_fills_preserve_original_entry_and_future_exit_invariance(self):
        rows=[bar(0),bar(1),bar(2,108,111,107,110),bar(3,101,103,99,100),bar(4)]
        original=VirtualPortfolio();run_case(original,rows)
        trades=json.loads(canonical(list(original.trades.values())))
        self.assertEqual(trades[0]['status'],'CLOSED')
        pairs=paired_replays(trades,[signal()],{'TEST':rows},SimulationPolicy(),rows[-1].close_time)
        self.assertEqual(len(pairs[0]['variants']),7)
        self.assertTrue(all(p['baseline_entry_reproduced'] and p['backtest_shadow_trade_nav_match'] for p in pairs[0]['variants']))
        proof=verify_exit_future(trades,[signal()],{'TEST':rows},SimulationPolicy())
        self.assertEqual(proof['status'],'PASS')

    def test_a_bit_for_bit_baseline_both_sides_partial_costs_and_collision(self):
        cases=[(Direction.LONG,[bar(0),bar(1),bar(2,108,111,107,110),bar(3,115,121,114,120),bar(4,125,131,124,130)]),
               (Direction.SHORT,[bar(0),bar(1),bar(2,92,93,89,90),bar(3,85,86,79,80),bar(4,75,76,69,70)]),
               (Direction.LONG,[bar(0),bar(1),bar(2,100,131,94,110)]),
               (Direction.SHORT,[bar(0),bar(1),bar(2,100,106,69,90)]),
               (Direction.LONG,[bar(0),bar(1),bar(2,105,131,99,110)]),
               (Direction.SHORT,[bar(0),bar(1),bar(2,95,101,69,90)])]
        for direction,rows in cases:
            with self.subTest(direction=direction,rows=rows):
                self.assertEqual(run_case(VirtualPortfolio(),rows,direction),
                    run_case(ExitResearchPortfolio(variant='A_40_30_30_BE_TP1'),rows,direction))

    def test_each_allocation_closes_entire_quantity_and_conserves_fees(self):
        rows=[bar(0),bar(1),bar(2,108,111,107,110),bar(3,115,121,114,120),bar(4,125,131,124,130)]
        for variant in list(EXIT_VARIANTS)[:4]:
            p=ExitResearchPortfolio(variant=variant)
            run_case(p,rows)
            t=p.trades['one']
            self.assertEqual(t['status'],'CLOSED')
            self.assertAlmostEqual(sum(f['quantity'] for f in t['fills']),t['quantity'])
            self.assertAlmostEqual(sum(f['entry_fee_allocation'] for f in t['fills']),t['entry_fee'])
            self.assertAlmostEqual(t['net_pnl'],t['gross_pnl']-t['fees_total'])
            self.assertEqual([f['reason'] for f in t['fills']],['TP1','TP2','TP3'])
            for f,fraction in zip(t['fills'],EXIT_VARIANTS[variant][0]):
                self.assertAlmostEqual(f['quantity'],t['quantity']*fraction)

    def test_later_close_cannot_retroactively_stop_on_transfer_bar(self):
        p=ExitResearchPortfolio(variant='A_BE_LATER_CLOSE')
        run_case(p,[bar(0),bar(1),bar(2,108,111,107,110)])
        self.assertEqual(p.positions['TEST'].stop_loss,95)
        p.step({'TEST':bar(3,109,110,99,100)})
        self.assertEqual(p.positions['TEST'].stop_loss,95)
        p.step({'TEST':bar(4,101,104,100,103)})
        self.assertIn('TEST',p.positions)
        self.assertGreater(p.positions['TEST'].stop_loss,100)
        p.step({'TEST':bar(5,100,101,98,100)})
        self.assertNotIn('TEST',p.positions)
        self.assertEqual(p.trades['one']['fills'][-1]['reference_price'],100)
        self.assertTrue(p.trades['one']['adverse_gap'])

    def test_original_stop_until_tp2_keeps_old_stop_then_conservative_be(self):
        p=ExitResearchPortfolio(variant='A_ORIGINAL_SL_UNTIL_TP2')
        run_case(p,[bar(0),bar(1),bar(2,108,111,107,110)])
        self.assertEqual(p.positions['TEST'].stop_loss,95)
        p.step({'TEST':bar(3,110,121,99,120)})
        self.assertEqual([f['reason'] for f in p.trades['one']['fills']],['TP1','TP2','BREAKEVEN_SAME_BAR_CONSERVATIVE'])

    def test_structural_trailing_never_reads_future_and_live_is_rejected(self):
        rows=[bar(0),bar(1),bar(2,108,111,107,110),bar(3,110,115,105,112),bar(4,112,115,106,113)]
        future=rows+[bar(i,1000,1100,900,1050) for i in range(5,20)]
        outputs=[]
        for history in (rows,future):
            p=ExitResearchPortfolio(variant='A_STRUCTURAL_AFTER_TP1',history={'TEST':history})
            outputs.append(run_case(p,rows))
            self.assertGreater(len(p.frame_cache),0)
            self.assertTrue(all(r.candle_count<=len(rows) for r in p.frame_cache.values()))
        self.assertEqual(outputs[0],outputs[1])
        with self.assertRaises(ValueError):
            ExitResearchPortfolio(variant='A_40_30_30_BE_TP1',mode='LIVE')

    def test_exit_shadow_matches_backtest_same_frozen_inputs(self):
        rows=[bar(0),bar(1),bar(2,108,111,107,110),bar(3,115,121,114,120),bar(4,125,131,124,130)]
        for variant in EXIT_VARIANTS:
            bt=ExitResearchPortfolio(variant=variant,history={'TEST':rows})
            sh=ExitResearchPortfolio(variant=variant,history={'TEST':rows},mode='SHADOW')
            for i,c in enumerate(rows):
                bt.step({'TEST':c},[signal()] if i==0 else [])
                sh.step({'TEST':c},[replace(signal(),mode='SHADOW')] if i==0 else [])
            self.assertEqual(canonical(bt.trades),canonical(sh.trades))
            self.assertEqual(canonical(bt.equity_curve),canonical(sh.equity_curve))


if __name__=='__main__':
    unittest.main()
