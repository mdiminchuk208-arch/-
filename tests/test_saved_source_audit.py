from hashlib import sha256
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_saved_source_trades import audit, classify  # noqa: E402
from verify_frozen_research_resume import protected_bytes, verify_saved_artifacts  # noqa: E402
from research_inventory import save_artifact_hashes  # noqa: E402


class SavedSourceAuditTests(unittest.TestCase):
    def test_audit_uses_only_pre_entry_evidence_and_excludes_constructed_trades(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            folder = repo / 'data/reports/history/case'
            folder.mkdir(parents=True)
            trade = dict(status='CLOSED', signal_id='saved', trade_id='saved', htf=60, ltf=5,
                         entry_interval_start='2026-01-01T01:00:00+00:00',
                         net_pnl=-1, gross_pnl=0, fees_total=1,
                         fills=[dict(net_pnl=-1, reason='STOP_FIRST_CONSERVATIVE')],
                         actual_entry_after_slippage=100, stop=99, targets=[101, 102, 103])
            (folder / 'trades.jsonl').write_text(json.dumps(trade) + '\n')
            past = dict(signal_id='saved', event_time='2026-01-01T00:55:00+00:00', sfp_time='past')
            future = dict(signal_id='saved', event_time='2026-01-01T01:05:00+00:00', sfp_time='future')
            (folder / 'signals.jsonl').write_text(json.dumps(past) + '\n' + json.dumps(future) + '\n')
            constructed = repo / 'data/reports/constructed/case'
            constructed.mkdir(parents=True)
            (constructed / 'trades.jsonl').write_text(json.dumps(trade) + '\n')
            output = repo / 'audit_output'
            audit(repo, output)
            records = [json.loads(line) for line in (output / 'closed_trade_source_audit.jsonl').read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['context']['sfp_time'], 'past')
            self.assertEqual(records[0]['classification'], 'UNCERTAIN_SOURCE')
            self.assertEqual((folder / 'trades.jsonl').read_text(), json.dumps(trade) + '\n')

    def test_completed_execution_manifest_rejects_a_corrupted_trade_file(self):
        with TemporaryDirectory() as directory:
            report = Path(directory)
            case = report / 'execution_sensitivity' / 'COST_150'
            case.mkdir(parents=True)
            trade = case / 'trades.jsonl'
            trade.write_text('original recorded execution\n')
            save_artifact_hashes(case)
            self.assertEqual(verify_saved_artifacts(report)['verified_artifact_manifests'], 1)
            trade.write_text('corrupted execution\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_saved_artifacts(report)

    def test_profitable_outcome_and_caller_attestation_do_not_certify_original_sources(self):
        signal = dict(source_qualification_evidence=['asserted by caller'])
        for pnl in (-23.4, 200):
            category, _, scope = classify(dict(ltf=5, net_pnl=pnl), signal)
            self.assertEqual(category, 'UNCERTAIN_SOURCE')
            self.assertEqual(scope, 'ORIGINAL_METHODOLOGY_COMPLIANCE')

    def test_unsupported_conservative_mapping_is_explicitly_scoped(self):
        category, _, scope = classify(dict(ltf=60), {})
        self.assertEqual(category, 'FALSE_POSITIVE_IMPLEMENTATION')
        self.assertEqual(scope, 'SOURCE_CONSERVATIVE_ENTRY_CLAIM_ONLY')

    def test_frozen_runtime_rejects_corruption_without_overwriting_current_source(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            path = repo / 'source.py'
            path.write_text('current source')
            blob = b'original frozen source'
            lock = dict(baseline_commit='original', code_hashes={'source.py': sha256(blob).hexdigest()})
            with patch.object(subprocess, 'run'), patch.object(subprocess, 'check_output', return_value=blob):
                self.assertEqual(protected_bytes(repo, lock), {'source.py': blob})
            with patch.object(subprocess, 'run'), patch.object(subprocess, 'check_output', return_value=b'corrupt'):
                with self.assertRaisesRegex(ValueError, 'registered hash'):
                    protected_bytes(repo, lock)
            self.assertEqual(path.read_text(), 'current source')
            lock['code_hashes'] = {'../escape.py': 'invalid'}
            with patch.object(subprocess, 'run'):
                with self.assertRaisesRegex(ValueError, 'Unsafe baseline path'):
                    protected_bytes(repo, lock)


if __name__ == '__main__':
    unittest.main()
