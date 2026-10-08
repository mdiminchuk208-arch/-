import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import write_klines_csv


class RecoveryAblationCliTests(unittest.TestCase):
    def test_requested_evaluation_window_accepts_coverage_and_rejects_short_history(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/analyze_recovery_ablation.py'
        spec = importlib.util.spec_from_file_location('recovery_ablation_cli_test', script)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for tf in (5, 15, 60, 240):
                rows = [
                    MarketCandle('BYBIT', 'BTCUSDT', str(tf), i * tf * 60000,
                                 100, 101, 99, 100)
                    for i in range(1440 // tf)
                ]
                write_klines_csv(rows, root / 'input/BTCUSDT' / f'{tf}.csv')
            arguments = [str(script), '--symbols', 'BTCUSDT',
                         '--data-root', str(root / 'input'),
                         '--tolerances', '0.08', '--wait-minutes', '60',
                         '--cluster-minutes', '0']
            with self.subTest(window_days=1):
                args = arguments + ['--evaluation-days', '1', '--report-root', str(root / 'accepted')]
                with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(runner.main(), 0)
                manifest = json.loads((root / 'accepted/BTCUSDT/manifest.json').read_text())
                summary = json.loads((root / 'accepted/BTCUSDT/summary.json').read_text())
                self.assertEqual(manifest['evaluation_days'], 1)
                self.assertTrue(summary['checks_passed'])
                self.assertEqual(set(manifest['inputs']), {'5', '15', '60', '240'})
            for window_days in (2, 240):
                with self.subTest(window_days=window_days):
                    dest = root / f'rejected_{window_days}'
                    args = arguments + ['--evaluation-days', str(window_days), '--report-root', str(dest)]
                    with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(ValueError, f'requested {window_days}d evaluation window'):
                            runner.main()
                    self.assertFalse((dest / 'BTCUSDT/summary.json').exists())
