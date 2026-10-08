from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory
from hashlib import sha256
import json

from crypto_bot.common.models import Candle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_robustness_research import common_segments, slice_bars, retained_results, write_rows
from research_inventory import reusable_case, verify_expected_fingerprint, restore_checkpoint_schema
from run_historical_portfolio import canonical

START = datetime(2020, 1, 1, tzinfo=timezone.utc)


def bar(index):
    return Candle(START+timedelta(minutes=5*index), START+timedelta(minutes=5*(index+1)),
                  100, 101, 99, 100, True)


class ResearchWindowTests(unittest.TestCase):
    def test_legacy_audit_recovery_requires_original_hash_and_keeps_modern_diagnostic(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)/'case';folder.mkdir()
            name='target_availability_qualification_only.jsonl.gz'
            rows=[dict(symbol='BTCUSDT',bos_level_price=100,qualified_ob=True)]
            write_rows(folder/name,[{k:v for k,v in rows[0].items() if k!='bos_level_price'}])
            (folder/'trades.jsonl').write_text('unchanged execution evidence\n')
            old={n:sha256((folder/n).read_bytes()).hexdigest() for n in (name,'trades.jsonl')}
            expected=sha256(canonical(old).encode()).hexdigest()
            write_rows(folder/name,rows)
            expanded={n:sha256((folder/n).read_bytes()).hexdigest() for n in old}
            (folder/'artifact_hashes.json').write_text(canonical(expanded))
            (folder/'fingerprint.sha256').write_text(sha256(canonical(expanded).encode()).hexdigest())
            diagnostics=Path(directory)/'diagnostics'
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            with self.assertRaises(ValueError):
                restore_checkpoint_schema(folder,'unrelated checkpoint',diagnostics)
            self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})
            self.assertEqual(restore_checkpoint_schema(folder,expected,diagnostics),expected)
            self.assertEqual(sha256((folder/'trades.jsonl').read_bytes()).hexdigest(),old['trades.jsonl'])
            self.assertEqual(sha256((diagnostics/'target_availability_qualification_only.v2.jsonl.gz').read_bytes()).hexdigest(),expanded[name])
            self.assertEqual(verify_expected_fingerprint(folder,expected),expected)

    def test_targeted_recovery_preserves_other_windows_and_segments(self):
        rows=[dict(window='REFERENCE',segment=0),dict(window='REFERENCE',segment=1),
              dict(window='VALIDATION',segment=0)]
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/'results.json').write_text(json.dumps(rows))
            self.assertEqual(retained_results(folder,['REFERENCE'],[0]),rows[1:])
            self.assertEqual(retained_results(folder,None,[0]),[rows[1]])
            self.assertEqual(retained_results(folder,None,None),[])

    def test_resume_requires_exact_inputs_and_every_original_artifact_hash(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory);context=dict(ltf=5,input_hashes={'bars':'source-sha'},policy={'risk':.02})
            self.assertIsNone(reusable_case(folder,context))
            (folder/'summary.json').write_text(canonical(dict(context,performance={'closed':1})))
            (folder/'trades.jsonl').write_text('actual previously observed trade\n')
            hashes={name:sha256((folder/name).read_bytes()).hexdigest() for name in ('summary.json','trades.jsonl')}
            (folder/'artifact_hashes.json').write_text(canonical(hashes))
            (folder/'fingerprint.sha256').write_text(sha256(canonical(hashes).encode()).hexdigest())
            self.assertEqual(reusable_case(folder,context)['performance'],{'closed':1})
            fingerprint=sha256(canonical(hashes).encode()).hexdigest()
            self.assertEqual(verify_expected_fingerprint(folder,fingerprint),fingerprint)
            with self.assertRaisesRegex(ValueError,'Recovery fingerprint mismatch'):
                verify_expected_fingerprint(folder,'different checkpoint')
            with self.assertRaises(ValueError):
                reusable_case(folder,dict(context,policy={'risk':.025}))
            (folder/'trades.jsonl').write_text('corrupted\n')
            with self.assertRaises(AssertionError):
                reusable_case(folder,context)
            with self.assertRaises(AssertionError):
                verify_expected_fingerprint(folder,fingerprint)

    def test_every_symbol_gap_partitions_shared_execution_clock(self):
        a = [bar(i) for i in range(8) if i != 2]
        b = [bar(i) for i in range(8) if i != 3]
        segments, gaps = common_segments({'A': a, 'B': b})
        self.assertEqual(gaps, [(bar(2).open_time, bar(3).close_time)])
        self.assertEqual(segments, [(START, bar(1).close_time), (bar(4).open_time, bar(7).close_time)])
        for begin, end in segments:
            self.assertEqual([c.close_time for c in slice_bars(a, begin, end)],
                             [c.close_time for c in slice_bars(b, begin, end)])

    def test_slicing_excludes_candle_not_closed_at_cutoff(self):
        rows = [bar(i) for i in range(8)]
        self.assertEqual(slice_bars(rows, START, START+timedelta(minutes=12)), rows[:2])
        self.assertEqual(slice_bars(rows, START+timedelta(minutes=6), START+timedelta(minutes=16)), rows[2:3])


if __name__ == '__main__':
    unittest.main()
