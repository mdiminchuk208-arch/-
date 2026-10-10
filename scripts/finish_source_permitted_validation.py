"""Finish the locked full40 replay, source qualification and measured delivery."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from run_source_permitted_bybit import REPO, digest, verify_manifest, write_json

BASE = REPO / 'data/reports/source_permitted_bybit_2026_10_10'
FINAL = REPO / 'data/reports/source_permitted_physical_bybit_2026_10_10'
QA = REPO / 'data/reports/source_permitted_qa_2026_10_10'
ANALYSIS = REPO / 'data/reports/source_permitted_analysis_2026_10_10'


def run(script, *args, log):
    print('START ' + script, flush=True)
    with (QA / log).open('w') as stream:
        result = subprocess.run([sys.executable, str(REPO / 'scripts' / script), *map(str, args)],
                                cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f'{script} failed ({result.returncode}); preserved log {log}')
    print('PASS ' + script, flush=True)


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume-complete-replay', action='store_true',
                        help='Verify the complete physical replay without rerunning it, then finish QA/report.')
    args = parser.parse_args()
    print('Wait for the complete full40 native detector manifest; no partial trade results are primary.', flush=True)
    while True:
        try:
            if json.loads((BASE / 'manifest.json').read_text())['status'] == 'COMPLETE':
                break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(5)
    verify_manifest(BASE)
    if args.resume_complete_replay:
        verify_manifest(FINAL)
        run('run_source_permitted_physical_union.py', '--source', BASE, '--output', FINAL,
            '--resume-existing', log='recovery_verified_physical_resume.log')
    else:
        run('run_source_permitted_physical_union.py', '--source', BASE, '--output', FINAL,
            log='full_physical_union_execution.log')
    summary = json.loads((FINAL / 'summary.json').read_text())
    primary = summary['primary']
    write_json(QA / 'historical_coverage_decision.json', {
        'native_series': summary['native_series'], 'native_candles': summary['candles'],
        'target_unique_closed': 50, 'observed_source_physical_CLOSED': primary['CLOSED'],
        'history_extension_required': primary['CLOSED'] < 50,
        'reason': 'FIRST_50_UNIQUE_SOURCE_VALID_FILLED_CLOSED_AVAILABLE' if primary['CLOSED'] >= 50
                  else 'AUTOMATIC_PERMITTED_PUBLIC_BYBIT_EXTENSION_REQUIRED',
        'trade_entry_allowed': False})
    if primary['CLOSED'] < 50:
        print('REQUIRES_HISTORY_EXTENSION; this is not a final maximum.', flush=True)
        return
    run('verify_source_physical_evidence.py', '--base', BASE, '--final', FINAL,
        '--prefix-cache', QA / 'real_prefix_optimized_observation.json.gz',
        '--output', QA / 'final_physical_source_evidence.json', log='final_physical_source_evidence.log')
    run('verify_source_permitted_evidence.py', '--folder', FINAL, '--ledger-only',
        '--output', QA / 'final_ledger_evidence.json', log='final_ledger_evidence.log')
    before = {name: snapshot(folder) for name, folder in (('native', BASE), ('physical', FINAL))}
    run('run_source_permitted_bybit.py', '--output', BASE, '--resume-existing', '--workers', '4',
        log='final_native_exact_resume.log')
    run('run_source_permitted_physical_union.py', '--source', BASE, '--output', FINAL, '--resume-existing',
        log='final_physical_exact_resume.log')
    after = {name: snapshot(folder) for name, folder in (('native', BASE), ('physical', FINAL))}
    assert before == after
    write_json(QA / 'final_exact_resume_receipt.json', {
        'status': 'VERIFIED_COMPLETE_NO_MUTATION',
        'artifact_counts': {name: len(rows) for name, rows in before.items()},
        'manifest_sha256': {'native': digest(BASE / 'manifest.json'), 'physical': digest(FINAL / 'manifest.json')},
        'all_before_after_artifact_hashes_equal': True, 'replay_performed': False,
        'trade_entry_allowed': False})
    run('report_source_permitted.py', '--input', FINAL, '--output', ANALYSIS, log='final_report_render.log')
    write_json(QA / 'finish_pipeline_receipt.json', {
        'status': 'COMPLETE_TARGET_50_AND_INDEPENDENT_QA', 'READY': primary['READY'],
        'FILLED': primary['FILLED'], 'CLOSED': primary['CLOSED'], 'primary50': primary['primary'],
        'pipeline_sha256': digest(Path(__file__)), 'trade_entry_allowed': False})
    print('COMPLETE: measured first50, all ledgers, native evidence, exact resume and report.', flush=True)


if __name__ == '__main__':
    main()
