"""Full automatic OHLC integration, without asserted reports, levels or signals.

The fixture is deliberately constructed test market data, not Bybit observations
or profitability evidence. Every closed HTF candle equals its twelve LTF bars.
The unchanged experimental OB/POI policy must pass all its original gates.
"""
from dataclasses import replace
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import os

from crypto_bot.common.models import Candle, Direction
from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import read_klines_csv, write_klines_csv
from crypto_bot.strategy.auto_levels import AutoLevelPolicy
from crypto_bot.strategy.historical_replay import indexed_signal_updates
from crypto_bot.strategy.replay import evaluate_snapshot
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio

spec=importlib.util.spec_from_file_location('automatic_cli',Path('scripts/run_historical_portfolio.py'))
cli=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def histories(direction=Direction.LONG):
    payload=json.loads((Path(__file__).parent/'fixtures/automatic_lifecycle_ohlc.json').read_text())
    data={int(tf):[Candle(datetime.fromisoformat(r[0]),datetime.fromisoformat(r[1]),*r[2:])
                   for r in rows] for tf,rows in payload.items()}
    if direction==Direction.SHORT:
        data={tf:[replace(c,open=200-c.open,high=200-c.low,low=200-c.high,close=200-c.close)
                  for c in cs] for tf,cs in data.items()}
    return data


class AutomaticLifecycleTests(unittest.TestCase):
    def test_cli_resume_rejects_changed_history_and_mode_without_touching_checkpoint(self):
        data=histories()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for tf,cs in data.items():
                rows=[MarketCandle('BYBIT','E2E',str(tf),int(c.open_time.timestamp()*1000),
                                  c.open,c.high,c.low,c.close) for c in cs]
                write_klines_csv(rows,root/'history/E2E'/f'{tf}.csv')
            common=['--data-root',str(root/'history'),'--report-root',str(root/'report'),
                    '--symbols','E2E','--days','max','--warmup-bars','0',
                    '--checkpoint',str(root/'state.json')]
            cli.main([*common,'--mode','SHADOW','--stop-after-bars','188'])
            previous=(root/'state.json').read_bytes()
            restored=VirtualPortfolio.load_checkpoint(root/'state.json')
            self.assertEqual(restored.positions['E2E'].tp_stage,1)
            self.assertFalse(json.loads((root/'report/summary.json').read_text())['run_complete'])
            with self.assertRaisesRegex(ValueError,'parameters changed'):
                cli.main([*common,'--resume','--mode','BACKTEST'])
            path=root/'history/E2E/5.csv'
            # A volume change leaves OHLC and clocks valid but changes identity.
            rows=read_klines_csv(path)
            rows[-1]=replace(rows[-1],volume_base=1.0)
            write_klines_csv(rows,path)
            with self.assertRaisesRegex(ValueError,'parameters changed'):
                cli.main([*common,'--resume','--mode','SHADOW'])
            self.assertEqual((root/'state.json').read_bytes(),previous)

    def test_backtest_shadow_long_short_full_automatic_lifecycle_and_restart(self):
        results=[]
        for direction in Direction:
            data=histories(direction)
            for i,h in enumerate(data[60]):
                cs=data[5][i*12:(i+1)*12]
                self.assertEqual((h.open,h.high,h.low,h.close),
                    (cs[0].open,max(c.high for c in cs),min(c.low for c in cs),cs[-1].close))
            for mode in ('BACKTEST','SHADOW'):
                updates,_=indexed_signal_updates(data,symbol='E2E',mode=mode,
                                                auto_level_policy=AutoLevelPolicy())
                ready=[s for s in updates if s.status=='READY_FOR_VIRTUAL_ENTRY']
                self.assertEqual(len(ready),1)
                self.assertEqual(ready[0].direction,direction)
                self.assertEqual(ready[0].score,100)
                self.assertGreater(ready[0].rr_minimum,0)
                self.assertLessEqual(ready[0].rr_minimum,ready[0].rr_at_optimal_entry)
                self.assertLessEqual(ready[0].rr_at_optimal_entry,ready[0].rr_maximum)
                p,observed=cli.simulate({'E2E':data[5]},updates,mode=mode)
                self.assertEqual(len(p.trades),1)
                trade=next(iter(p.trades.values()))
                self.assertEqual(trade['status'],'CLOSED')
                exits=[d for d in p.journal if d.action=='VIRTUAL_EXIT']
                self.assertEqual([d.reason for d in exits],['TP1','TP2','TP3'])
                for d,fraction in zip(exits,(.4,.3,.3)):
                    self.assertAlmostEqual(d.quantity/trade['quantity'],fraction)
                self.assertAlmostEqual(p.realized_pnl,trade['net_pnl'])
                self.assertGreater(p.realized_pnl,0)
                self.assertFalse(p.positions)
                self.assertTrue(all(not d.trade_entry_allowed for d in p.journal))
                with tempfile.TemporaryDirectory() as temp:
                    path=Path(temp)/'state.json'
                    # Pending -> entry -> TP1 -> TP2: every restart is identical.
                    for cut in (186,187,188,189):
                        cli.simulate({'E2E':data[5]},updates,mode=mode,checkpoint_path=path,stop_after_bars=cut)
                        restored=VirtualPortfolio.load_checkpoint(path)
                        q,signals=cli.simulate({'E2E':data[5]},updates,mode=mode,portfolio=restored)
                        self.assertEqual(q.snapshot(),p.snapshot())
                        self.assertEqual(signals,observed)
                results.append((direction,mode,p.realized_pnl,p.journal))
        for i in (0,2):
            self.assertEqual(results[i][2:],results[i+1][2:])

    def test_every_prefix_and_future_mutation_preserves_automatic_ready(self):
        data=histories()
        indexed,_=indexed_signal_updates(data,symbol='E2E',auto_level_policy=AutoLevelPolicy())
        states,expected={},[]
        for candle in data[5]:
            snapshot=evaluate_snapshot(data,symbol='E2E',as_of=candle.close_time,
                                        auto_level_policy=AutoLevelPolicy())
            for signal in snapshot.signals:
                signature=replace(signal,event_time=data[5][0].close_time)
                if states.get(signal.signal_id)!=signature:
                    expected.append(signal);states[signal.signal_id]=signature
        self.assertEqual(indexed,tuple(expected))
        ready=next(s for s in indexed if s.status=='READY_FOR_VIRTUAL_ENTRY')
        cutoff=ready.event_time
        altered={tf:[replace(c,open=c.open*2,high=c.high*2,low=c.low*2,close=c.close*2)
                     if c.close_time>cutoff else c for c in cs] for tf,cs in data.items()}
        mutated,_=indexed_signal_updates(altered,symbol='E2E',auto_level_policy=AutoLevelPolicy())
        self.assertEqual([s for s in indexed if s.event_time<=cutoff],
                         [s for s in mutated if s.event_time<=cutoff])
        self.assertEqual(ready.level_blocking_reasons,())

    def test_cli_keeps_causal_ltf_tail_after_last_closed_htf(self):
        data=histories()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for tf,cs in data.items():
                rows=[MarketCandle('BYBIT','E2E',str(tf),int(c.open_time.timestamp()*1000),
                                  c.open,c.high,c.low,c.close) for c in cs]
                write_klines_csv(rows,root/'history/E2E'/f'{tf}.csv')
            cli.main(['--data-root',str(root/'history'),'--report-root',str(root/'report'),
                      '--symbols','E2E','--days','max','--warmup-bars','0'])
            summary=json.loads((root/'report/summary.json').read_text())
            self.assertEqual(summary['execution_end'],data[5][-1].close_time.isoformat())
            self.assertEqual(summary['funnel']['entries'],1)
            self.assertEqual(summary['funnel']['completed_trades'],1)
            # The snapshot CLI has the same causal tail and admission behavior.
            result=subprocess.run([sys.executable,'scripts/run_strategy_replay.py',
                '--data-root',str(root/'history'),'--report-root',str(root/'snapshot'),
                '--symbols','E2E','--bars','190','--warmup-bars','0','--auto-levels'],
                env={**os.environ,'PYTHONPATH':'src'},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            snapshot=json.loads((root/'snapshot/summary.json').read_text())
            self.assertEqual(snapshot['virtual_entry_count'],1)
            self.assertAlmostEqual(snapshot['final_equity'],summary['portfolio']['final_equity'])
