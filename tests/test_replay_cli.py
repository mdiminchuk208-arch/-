import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import write_klines_csv
from test_replay import histories


class ReplayCliTests(unittest.TestCase):
    def test_real_cli_replays_identically_and_shadow_keeps_same_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for tf, candles in histories().items():
                rows = [MarketCandle('BYBIT', 'TEST', str(tf), int(c.open_time.timestamp() * 1000),
                                     c.open, c.high, c.low, c.close) for c in candles]
                write_klines_csv(rows, root / 'history' / 'TEST' / f'{tf}.csv')
            reports, journals, fingerprints = [], [], []
            for i, mode in enumerate(('BACKTEST', 'BACKTEST', 'SHADOW')):
                destination = root / str(i)
                result = subprocess.run(
                    [sys.executable, 'scripts/run_strategy_replay.py', '--data-root', str(root / 'history'),
                     '--report-root', str(destination), '--symbols', 'TEST', '--htf', '5', '--ltf', '1',
                     '--bars', '30', '--warmup-bars', '570', '--mode', mode],
                    env={**os.environ, 'PYTHONPATH': 'src'}, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads((destination / 'summary.json').read_text())
                self.assertGreater(payload['unique_signal_count'], 0)
                self.assertEqual(payload['virtual_entry_count'], 0)
                self.assertFalse(payload['trade_entry_allowed'])
                payload.pop('mode')
                for signal in payload['signal_updates']:
                    self.assertIn(signal['direction'], ('LONG', 'SHORT'))
                    signal.pop('mode')
                    self.assertFalse(signal['trade_entry_allowed'])
                reports.append(payload)
                journals.append((destination / 'decisions.jsonl').read_bytes())
                fingerprints.append((destination / 'fingerprint.sha256').read_text())
            self.assertEqual(fingerprints[0], fingerprints[1])
            self.assertEqual(reports[0], reports[1])
            self.assertEqual(reports[0], reports[2])
            self.assertEqual(journals[0], journals[2])

    def test_cli_rejects_live_before_reading_data(self):
        result = subprocess.run([sys.executable, 'scripts/run_strategy_replay.py', '--mode', 'LIVE'],
                                env={**os.environ, 'PYTHONPATH': 'src'}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid choice', result.stderr)

    def test_auto_cli_is_deterministic_shadow_matches_and_no_proxy_entry_occurs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for tf, candles in histories().items():
                rows = [MarketCandle('BYBIT', 'TEST', str(tf), int(c.open_time.timestamp() * 1000),
                                     c.open, c.high, c.low, c.close) for c in candles]
                write_klines_csv(rows, root / 'history' / 'TEST' / f'{tf}.csv')
            reports, journals, fingerprints = [], [], []
            for i, mode in enumerate(('BACKTEST', 'BACKTEST', 'SHADOW')):
                destination = root / str(i)
                result = subprocess.run(
                    [sys.executable, 'scripts/run_strategy_replay.py', '--data-root', str(root / 'history'),
                     '--report-root', str(destination), '--symbols', 'TEST', '--htf', '5', '--ltf', '1',
                     '--bars', '12', '--warmup-bars', '588', '--mode', mode, '--auto-levels'],
                    env={**os.environ, 'PYTHONPATH': 'src'}, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads((destination / 'summary.json').read_text())
                self.assertGreater(payload['unique_signal_count'], 0)
                self.assertEqual(payload['automatic_level_policy']['min_body_fraction'], 0.6)
                self.assertEqual(payload['level_selection_policy'],
                                 'AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION')
                self.assertEqual(payload['virtual_entry_count'], 0)
                self.assertFalse(payload['trade_entry_allowed'])
                self.assertIn('AUTO_LEVELS_ARE_RESEARCH_PROXIES_NOT_SOURCE_QUALIFIED_AND_CANNOT_CANONICALLY_ENTER',
                              payload['limitations'])
                payload.pop('mode')
                for item in payload['signal_updates']:
                    item.pop('mode')
                    self.assertIn('level_blocking_reasons', item)
                    self.assertFalse(item['trade_entry_allowed'])
                reports.append(payload)
                journals.append((destination / 'decisions.jsonl').read_bytes())
                fingerprints.append((destination / 'fingerprint.sha256').read_text())
            self.assertEqual(reports[0], reports[1])
            self.assertEqual(reports[0], reports[2])
            self.assertEqual(journals[0], journals[2])
            self.assertEqual(fingerprints[0], fingerprints[1])

    def test_auto_cli_rejects_invalid_or_mixed_parameters_before_reading_data(self):
        for args in (
            ['--auto-levels', '--qualified-levels', 'unread.json'],
            ['--auto-levels', '--min-ob-body-fraction', 'nan'],
            ['--auto-levels', '--min-ob-body-fraction', '0'],
            ['--auto-levels', '--min-engulf-body-ratio', '0.5'],
            ['--min-ob-body-fraction', '0.8'],
        ):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, 'scripts/run_strategy_replay.py', *args],
                                        env={**os.environ, 'PYTHONPATH': 'src'}, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
