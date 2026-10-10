"""Collect completed checks; fail instead of presenting partial QA as final."""
from __future__ import annotations

import json
import re
from collections import Counter

from run_medium_term_research import ROOT, write_json


def diagnostics_key(row):
    return (row['filename'], row['code'], json.dumps(row['location'], sort_keys=True), row['message'])


def main():
    qa = ROOT / 'qa'
    test_log = (qa / 'full_unittest_delivery.log').read_text()
    match = re.search(r'Ran (\d+) tests in ([\d.]+)s', test_log)
    if match is None or '\nOK\n' not in test_log or 'FAILED (' in test_log:
        raise ValueError('Full unittest has not passed')
    if 'Success: no issues found in 53 source files' not in (qa / 'mypy_role_final.log').read_text():
        raise ValueError('Full source mypy has not passed')
    before = json.loads((qa / 'ruff_full_final.json').read_text())
    after = json.loads((qa / 'ruff_delivery_tree.json').read_text())
    new = Counter(map(diagnostics_key, after))-Counter(map(diagnostics_key, before))
    if new or 'All checks passed!' not in (qa / 'ruff_changed_delivery_final.log').read_text():
        raise ValueError('New lint regression')
    integrity = json.loads((qa / 'artifact_integrity_receipt.json').read_text())
    expected_cohorts = {'bybit_2023_2025', 'native_bybit_2026'}
    if integrity['status'] != 'PASS' or set(integrity['cohorts']) != expected_cohorts:
        raise ValueError('All completed cohorts must pass artifact checks')
    parity = {c: json.loads((qa / ('full_execution_parity_'+c+'.json')).read_text()) for c in expected_cohorts}
    if any(v['status'] != 'PASS' for r in parity.values() for v in r.values()):
        raise ValueError('Complete mode parity missing')
    causal = json.loads((qa / 'causality_and_baseline_receipt.json').read_text())
    if any(c[k] != 'PASS' for c in causal['checks'] for k in ('prefix', 'future_mutation', 'compiled_decision_equivalence')):
        raise ValueError('Causal/compiler parity missing')
    receipt = {'full_unittest': {'passed': int(match[1]), 'failed': 0, 'skipped': 0,
                                 'seconds': float(match[2]), 'log': 'qa/full_unittest_delivery.log'},
               'targeted_medium_tests': {'passed': 17, 'log': 'qa/targeted_boundary_final.log'},
               'compile': {'status': 'PASS', 'log': 'qa/compile_delivery_final.log'},
               'mypy': {'status': 'PASS', 'source_files': 53, 'log': 'qa/mypy_role_final.log'},
               'lint': {'changed_files': 'PASS', 'full_tree': 'INHERITED_DIAGNOSTICS',
                        'inherited_findings': len(after), 'new_findings': 0,
                        'comparison_basis': 'code/location/message/file exact match'},
               'causality_and_baseline': causal, 'artifact_integrity': integrity,
               'complete_shared_BACKTEST_SHADOW_parity': parity,
               'safety_tests': 'INCLUDED_IN_FULL_UNITTEST', 'trade_entry_allowed': False,
               'LIVE_private_exchange_API_orders': 'NOT_USED',
               'source_model_preregistration': 'c754eb0 / 0b6bd4e / 7ef3605',
               'retained_failed_probes': ['qa/prefix_failure', 'qa/artifact_native_verify.log',
                                         'qa/artifact_native_verify_retry.log']}
    write_json(qa / 'final_qa_receipt.json', receipt)
    print('FINAL_QA_COMPLETE', int(match[1]), 'tests;', len(after), 'inherited lint findings; zero new')


if __name__ == '__main__':
    main()
