"""Reuse fully verified READY proofs and replay actual-main-TF body exits."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from crypto_bot.strategy.source_medium_term import actual_setup_tf
from crypto_bot.strategy.source_pdf_native import evidence_json

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_medium_term_research as runner

ARCHIVED_CODE = '0b6bd4e'
REPO = runner.REPO
BASE = runner.ROOT
ROOT = BASE / 'role_corrected_v2'
OLD_ROOTS = {'native_bybit_2026': BASE / 'causal_final/native_bybit_2026',
             'bybit_2023_2025': BASE / 'compiled_primary/bybit_2023_2025'}


def validate_original(cohort):
    old = OLD_ROOTS[cohort]
    lock = json.loads((old / 'run_lock.json').read_text())
    for name, expected in lock['code_and_data_hashes'].items():
        path = REPO / name
        if name.startswith('data/history/'):
            observed = runner.digest(path)
        else:
            raw = subprocess.check_output(['git', 'show', ARCHIVED_CODE+':'+name], cwd=REPO)
            observed = sha256(raw).hexdigest()
        if observed != expected:
            raise ValueError('Original dependency proof mismatch: '+name)
    for symbol in lock['symbols']:
        folder = old / 'detection' / symbol
        expected = sha256(evidence_json({'lock': lock, 'symbol': symbol}).encode()).hexdigest()
        runner.resume(folder, expected, True)
    return lock


def annotated(row):
    row = copy.deepcopy(row)
    signal = runner.deserialize_signal(row)
    setup_tf = actual_setup_tf(signal)
    if setup_tf not in (60, 240):
        raise ValueError('Reused READY has no valid main ownership')
    row['evidence'].update(actual_setup_tf=setup_tf, setup_tf=setup_tf,
                           flow_owner_tf=row['htf'], role_annotation='DERIVED_FROM_IMMUTABLE_READY_POI_IDENTITY')
    return row


def prepare(cohort, lock, use_resume):
    old = OLD_ROOTS[cohort]
    correction = {'source_ready_lock': lock, 'archive_commit': ARCHIVED_CODE,
                  'correction_code_hashes': {str(p.relative_to(REPO)): runner.digest(p)
                                             for p in list((REPO / 'src').rglob('*.py'))+
                                             [Path(__file__), REPO / 'MEDIUM_TERM_ROLE_CORRECTION_PROTOCOL.md',
                                              REPO / 'scripts/run_medium_term_research.py']},
                  'policy': lock['policy'], 'symbols': lock['symbols'], 'trade_entry_allowed': False}
    root = ROOT / cohort
    path = root / 'run_lock.json'
    if path.exists():
        if json.loads(path.read_text()) != correction:
            raise ValueError('Correction registered dependencies changed')
    else:
        runner.write_json(path, correction)
    for symbol in lock['symbols']:
        target, source = root / 'detection' / symbol, old / 'detection' / symbol
        source_manifest_sha = runner.digest(source / 'manifest.json')
        fp = sha256(evidence_json({'correction': correction, 'source_manifest': source_manifest_sha,
                                  'symbol': symbol}).encode()).hexdigest()
        if runner.resume(target, fp, use_resume):
            continue
        data, audits = runner.load_data(cohort, symbol, lock['policy'])
        target.mkdir(parents=True)
        runner.write_json(target / 'dataset_audit.json', audits)
        adjustments = []
        for arm in ('enabled', 'disabled_cost_gate'):
            old_signals = runner.read_rows(source / arm / 'signals.jsonl.gz')
            rows = [annotated(s) for s in old_signals]
            exits = runner.read_rows(source / arm / 'exit_events.jsonl.gz')
            cancellations = runner.read_rows(source / arm / 'cancellations.jsonl.gz')
            for before, after in zip(old_signals, rows):
                for key in ['signal_id', 'known_at', 'entry', 'stop', 'targets', 'fractions']:
                    if before[key] != after[key]:
                        raise ValueError('READY geometry/chronology changed')
                e = after['evidence']
                if e['actual_setup_tf'] == after['htf']:
                    continue
                ready = datetime.fromisoformat(after['known_at'])
                parent = e['htf_poi']
                terminal = min((datetime.fromisoformat(r['known_at']) for r in exits
                                if r['signal_id'] == after['signal_id']),
                               default=data[e['actual_setup_tf']][-1].close_time+timedelta(minutes=1))
                body = next((c for c in data[e['actual_setup_tf']] if ready < c.close_time < terminal
                             and (c.close < parent['low'] if after['direction']=='LONG' else c.close > parent['high'])), None)
                if body is not None:
                    event = {'signal_id': after['signal_id'], 'known_at': body.close_time.isoformat(),
                             'reason': 'MAIN_SOURCE_POI_BODY_INVALIDATED', 'price': body.close,
                             'actual_setup_tf': e['actual_setup_tf'], 'flow_owner_tf': after['htf']}
                    exits.append(event)
                    # Existing pending-only cancellation already records the
                    # same H1 death in ordinary cases; never create a late fill.
                    cancellations.append({'signal_id': after['signal_id'], 'known_at': body.close_time.isoformat(),
                                          'cohort': lock['policy']['primary_cancellation'],
                                          'reason': 'MAIN_SOURCE_POI_BODY_INVALIDATED', 'trade_entry_allowed': False})
                    adjustments.append({'arm': arm, **event})
            key = lambda r: (datetime.fromisoformat(r['known_at']), r['signal_id'], r['reason'])
            # One terminal update per signal/CLOSE; prefer explicit main cause.
            unique = {}
            for c in cancellations:
                unique[(c['signal_id'], datetime.fromisoformat(c['known_at']))] = c
            runner.write_rows(target / arm / 'signals.jsonl.gz', rows)
            runner.write_rows(target / arm / 'cancellations.jsonl.gz', sorted(unique.values(), key=key))
            runner.write_rows(target / arm / 'exit_events.jsonl.gz', sorted(exits, key=key))
            for name in ['attempts.jsonl.gz','anti_scalp_rejections.jsonl.gz','setup_lifecycle.jsonl.gz']:
                (target / arm / name).write_bytes((source / arm / name).read_bytes())
            (target / arm / 'funnel.json').write_bytes((source / arm / 'funnel.json').read_bytes())
        runner.write_rows(target / 'ownership_corrections.jsonl.gz', adjustments)
        runner.seal(target, fp, {'source_manifest_sha256': source_manifest_sha,
                                'qualified_READY_geometry_unchanged': True,
                                'role_corrected_exit_events': len(adjustments), 'symbol': symbol,
                                'arms': ['enabled','disabled_cost_gate']})
    runner.ROOT = ROOT
    return correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=tuple(OLD_ROOTS), required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--resume-existing', action='store_true')
    args = parser.parse_args()
    original = validate_original(args.cohort)
    correction = prepare(args.cohort, original, args.resume_existing)
    if args.prepare_only:
        print('REGISTERED_ROLE_CORRECTION_BEFORE_PNL', args.cohort, flush=True)
        return
    for arm in ('enabled','disabled_cost_gate'):
        runner.simulate(args.cohort, original['symbols'], original['policy'], correction, arm, args.resume_existing)


if __name__ == '__main__':
    main()
