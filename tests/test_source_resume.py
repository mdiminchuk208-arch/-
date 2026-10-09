from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_source_bybit import verify_segment, stats


class SourceResumeTests(unittest.TestCase):
    def test_resume_requires_exact_inputs_code_and_all_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            files = ('signals.jsonl.gz', 'cancellations.jsonl.gz', 'setup_outcomes.jsonl.gz',
                     'summary.json', 'old_loss_audit.json')
            for f in files:
                (p / f).write_bytes(b'original fixture')
            manifest = {'status': 'COMPLETE', 'fingerprint': 'exact-input-and-code',
                        'artifacts': {f: sha256((p / f).read_bytes()).hexdigest() for f in files}}
            (p / 'manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_segment(p, 'exact-input-and-code'), manifest)
            with self.assertRaises(ValueError):
                verify_segment(p, 'changed-code-or-input')
            (p / files[0]).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                verify_segment(p, 'exact-input-and-code')

    def test_incomplete_segment_cannot_be_promoted_by_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'manifest.json').write_text(json.dumps({'status': 'COMPLETE', 'fingerprint': 'x', 'artifacts': {}}))
            with self.assertRaises(ValueError):
                verify_segment(p, 'x')

    def test_undefined_statistics_and_expectancy_are_not_infinite(self):
        self.assertIsNone(stats([])['WinRate'])
        self.assertIsNone(stats([])['ProfitFactor'])
        rows = [{'net_pnl': n, 'result_R': n / 10, 'quote_gross_pnl': n + 2,
                 'gross_pnl': n + 1, 'fees': 1, 'slippage': 1, 'holding_seconds': 300}
                for n in (20, -10, -10)]
        result = stats(rows, [{'equity': 100}, {'equity': 120}, {'equity': 110}, {'equity': 100}])
        self.assertAlmostEqual(result['Expectancy'], 0)
        self.assertEqual(result['ProfitFactor'], 1)
        self.assertEqual(result['MaxDrawdown'], 20)
        self.assertEqual(result['MaxLosingStreak'], 2)


if __name__ == '__main__':
    unittest.main()
