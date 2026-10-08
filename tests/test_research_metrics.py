from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import csv
import gzip
from tempfile import TemporaryDirectory
import unittest

from crypto_bot.common.models import Candle
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio

spec = spec_from_file_location('research_support', Path(__file__).resolve().parents[1] / 'scripts/research_support.py')
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
START = datetime(2020, 1, 1, tzinfo=timezone.utc)


class ResearchMetricsTests(unittest.TestCase):
    def test_compressed_reader_keeps_complete_bars_in_exact_interval(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'bars.csv.gz'
            with gzip.open(path,'wt',newline='') as handle:
                writer=csv.writer(handle)
                writer.writerow(['exchange','symbol','interval','open_time_ms','open','high','low','close','volume_base','turnover_quote','is_closed'])
                for i in range(6):
                    writer.writerow(['BYBIT','TEST','5',int((START+timedelta(minutes=5*i)).timestamp()*1000),100,101,99,100,'','','1'])
            full=module.read_compressed(path,5)
            begin=START+timedelta(minutes=5);end=START+timedelta(minutes=21)
            expected=[c for c in full if c.open_time>=begin and c.close_time<=end]
            self.assertEqual(module.read_compressed(path,5,begin=begin,end=end),expected)
            self.assertEqual(len(expected),3)
            self.assertEqual(expected[-1].close_time,START+timedelta(minutes=20))

    def test_regime_cannot_read_future_or_incomplete_day(self):
        days = [Candle(START+timedelta(days=i), START+timedelta(days=i+1),
                       100+i, 102+i, 99+i, 101+i, True) for i in range(50)]
        cutoff = START + timedelta(days=31, hours=12)
        self.assertEqual(module.regime(days, cutoff), module.regime(days[:31], cutoff))
        future = days[:31] + [Candle(c.open_time, c.close_time, 2000, 2001, 1999, 2000, True) for c in days[31:]]
        self.assertEqual(module.regime(days, cutoff), module.regime(future, cutoff))
        self.assertEqual(module.regime(days[:30], cutoff), ('UNKNOWN', 'UNKNOWN'))

    def test_drawdown_duration_includes_recovery_and_censored_tail(self):
        curve = [dict(timestamp=START+timedelta(days=i), equity=value)
                 for i, value in enumerate([100, 90, 80, 100, 95, 94, 93, 92])]
        dd, seconds = module.drawdown_duration(curve, START, 100)
        self.assertAlmostEqual(dd, .2)
        self.assertEqual(seconds, 4*86400)

    def test_overlapping_positions_are_not_double_counted_as_exposure(self):
        intervals = [(START, START+timedelta(hours=3)),
                     (START+timedelta(hours=2), START+timedelta(hours=4))]
        self.assertEqual(module.interval_union_seconds(intervals), 4*3600)

    def test_zero_trade_sample_does_not_manufacture_ratios_or_monte_carlo(self):
        p = VirtualPortfolio(equity=1170)
        result = module.performance(p, [], START, START+timedelta(days=180))
        self.assertIsNone(result['profit_factor'])
        self.assertIsNone(result['sharpe'])
        self.assertIsNone(result['payoff_ratio'])
        self.assertEqual(result['exposure_fraction_upper_bound'], 0)
        self.assertEqual(result['monte_carlo_status'], 'WITHHELD_BELOW_50_COMPARABLE_CLOSED_TRADES')
        self.assertEqual(result['inference_status'], 'INSUFFICIENT_SAMPLE')

    def test_trade_measurements_accept_live_objects_and_json_roundtrip(self):
        p = VirtualPortfolio(equity=1170)
        p.trades['x'] = dict(trade_id='x',status='CLOSED',symbol='BTCUSDT',direction='LONG',
            entry_interval_start=START,entry_time=START+timedelta(minutes=5),exit_time=START+timedelta(hours=1),
            net_pnl=0,result_R=0,gross_pnl=0,fees_total=0,fills=[])
        a=module.performance(p,[],START,START+timedelta(days=1))
        self.assertEqual(a['average_holding_seconds_known_time_lower_bound'],55*60)
        for key in ('entry_interval_start','entry_time','exit_time'):
            p.trades['x'][key]=p.trades['x'][key].isoformat()
        b=module.performance(p,[],START,START+timedelta(days=1))
        self.assertEqual(a,b)


if __name__ == '__main__':
    unittest.main()
