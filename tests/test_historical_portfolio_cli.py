import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import os
import tempfile
import unittest
from dataclasses import replace

from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import write_klines_csv
from crypto_bot.strategy.portfolio_statistics import trade_statistics
from test_replay import histories
from test_virtual_portfolio import bar, signal


spec=importlib.util.spec_from_file_location('historical_cli',Path('scripts/run_historical_portfolio.py'))
cli=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class HistoricalPortfolioCliTests(unittest.TestCase):
    def test_repeated_backtest_shadow_and_workers_match(self):
        data=histories()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for symbol in ('A','B'):
                for tf,cs in data.items():
                    rows=[MarketCandle('BYBIT',symbol,str(tf),int(c.open_time.timestamp()*1000),
                        c.open,c.high,c.low,c.close) for c in cs]
                    write_klines_csv(rows,root/'history'/symbol/f'{tf}.csv')
            outputs=[]
            for i,(mode,workers) in enumerate((('BACKTEST',1),('BACKTEST',2),('SHADOW',1))):
                destination=root/str(i)
                result=subprocess.run([sys.executable,'scripts/run_historical_portfolio.py',
                    '--data-root',str(root/'history'),'--report-root',str(destination),
                    '--symbols','A','B','--htf','5','--ltf','1','--days','max',
                    '--warmup-bars','100','--mode',mode,'--workers',str(workers)],
                    env={**os.environ,'PYTHONPATH':'src'},capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                summary=json.loads((destination/'summary.json').read_text())
                self.assertEqual(summary['initial_capital'],1170)
                self.assertFalse(summary['trade_entry_allowed'])
                summary.pop('mode')
                signals=[json.loads(row) for row in (destination/'signals.jsonl').read_text().splitlines()]
                for row in signals:
                    row.pop('mode')
                files={name:(destination/name).read_bytes() for name in
                       ('decisions.jsonl','trades.jsonl','equity_curve.jsonl')}
                outputs.append((summary,signals,files))
                if i==0:
                    fingerprint=(destination/'fingerprint.sha256').read_text()
                elif i==1:
                    self.assertEqual(fingerprint,(destination/'fingerprint.sha256').read_text())
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(outputs[0],outputs[2])

    def test_prefix_portfolio_curve_and_fills_cannot_change(self):
        execution={'TEST':[bar(i) for i in range(5)]}
        updates=[signal(),replace(signal(2,ident='two'),status='INVALIDATED')]
        full,observed=cli.simulate(execution,updates)
        prefix,_=cli.simulate({'TEST':execution['TEST'][:3]},updates)
        self.assertEqual(full.equity_curve[:3],prefix.equity_curve)
        self.assertEqual(tuple(d for d in full.journal if d.time<=bar(2).close_time),prefix.journal)

    def test_invalid_capital_and_live_fail_before_loading_history(self):
        for args in (['--mode','LIVE'],['--initial-capital','nan'],['--days','0']):
            result=subprocess.run([sys.executable,'scripts/run_historical_portfolio.py',*args],
                env={**os.environ,'PYTHONPATH':'src'},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('Traceback',result.stderr)

    def test_statistics_use_completed_trades_and_keep_undefined_null(self):
        trades=[]
        for i,pnl in enumerate((10,-5,0,20)):
            trades.append(dict(status='CLOSED',exit_time=bar(i).close_time,symbol='TEST',
                trade_id=str(i),net_pnl=pnl,result_R=pnl/5))
        stats=trade_statistics(trades)
        self.assertEqual(stats['completed_trades'],4)
        self.assertEqual(stats['profit_factor'],6)
        self.assertEqual(stats['win_rate'],.5)
        self.assertEqual(stats['breakevens'],1)
        self.assertEqual(stats['expectancy'],6.25)
        self.assertEqual(stats['realized_contribution_drawdown_usdt'],5)
