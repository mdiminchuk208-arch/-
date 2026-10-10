"""Verify completed dependency locks, every READY proof and executed trade."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

from crypto_bot.research.medium_statistics import closed_statistics
from crypto_bot.strategy.anti_scalp import check_anti_scalp
from crypto_bot.strategy.source_medium_term import actual_setup_tf, portfolio_signal
from crypto_bot.strategy.source_pdf_native import evidence_json
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_medium_role_correction import OLD_ROOTS, validate_original
from run_medium_term_research import (
    REPO,
    ROOT,
    deserialize_signal,
    digest,
    load_data,
    read_rows,
    resume,
    write_json,
)
from verify_medium_term import known_times, preserved_baseline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=tuple(OLD_ROOTS))
    args = parser.parse_args()
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    roots = {c: ROOT / 'role_corrected_v2' / c for c in OLD_ROOTS}
    result = {'status': 'PASS', 'cohorts': {}, 'baseline': preserved_baseline(),
              'trade_entry_allowed': False}
    for cohort in ([args.cohort] if args.cohort else ('bybit_2023_2025', 'native_bybit_2026')):
        base = roots[cohort]
        lock = json.loads((base / 'run_lock.json').read_text())
        if lock['trade_entry_allowed'] is not False:
            raise ValueError('Unsafe registered execution mode')
        if validate_original(cohort) != lock['source_ready_lock']:
            raise ValueError('Archived READY lock mismatch')
        for name, expected in lock['correction_code_hashes'].items():
            if digest(REPO / name) != expected:
                raise ValueError('Registered dependency changed: ' + name)
        clock = lock['policy']['execution_clock']
        owner = {'READY': Counter(), 'known_timestamps_checked': 0, 'ledger_counts': {}}
        signals = {}
        for symbol in lock['symbols']:
            folder = base / 'detection' / symbol
            original_folder = OLD_ROOTS[cohort] / 'detection' / symbol
            expected = sha256(evidence_json({'correction': lock,
                                            'source_manifest': digest(original_folder / 'manifest.json'),
                                            'symbol': symbol}).encode()).hexdigest()
            resume(folder, expected, True)
            candles, _ = load_data(cohort, symbol, policy)
            clock_map = {c.close_time: c for c in candles[clock]}
            for arm in ('enabled', 'disabled_cost_gate'):
                rows = read_rows(folder / arm / 'signals.jsonl.gz')
                originals = read_rows(original_folder / arm / 'signals.jsonl.gz')
                if len(rows) != len(originals):
                    raise ValueError('Qualified READY count changed')
                for raw, old in zip(rows, originals):
                    for key in ('signal_id', 'known_at', 'entry', 'stop', 'targets', 'fractions'):
                        if raw[key] != old[key]:
                            raise ValueError('Qualified READY geometry changed')
                    if raw['evidence']['physical_opportunity_id'] != old['evidence']['physical_opportunity_id']:
                        raise ValueError('Physical READY identity changed')
                physical = set()
                for raw in rows:
                    s = deserialize_signal(raw)
                    if s.trade_entry_allowed or actual_setup_tf(s) not in (60, 240):
                        raise ValueError('Unsafe or micro setup')
                    e = s.evidence
                    if e['macro_context_tf'] not in (240, 1440) or not e['main_setup_valid']:
                        raise ValueError('Missing macro ownership')
                    if e['physical_opportunity_id'] in physical:
                        raise ValueError('Duplicate physical opportunity')
                    physical.add(e['physical_opportunity_id'])
                    d = e['anti_scalp']
                    if abs(d['estimated_round_trip_cost']-sum(d[k] for k in ('entry_fee','exit_fee','entry_slippage','exit_slippage'))) > 1e-9:
                        raise ValueError('Incomplete costs')
                    if arm == 'enabled' and (not d['allowed'] or d['edge_cost_ratio'] < 3.):
                        raise ValueError('Anti-Scalp bypass before READY')
                    for at in known_times(e):
                        if at > s.known_at:
                            raise ValueError('Future READY evidence')
                        owner['known_timestamps_checked'] += 1
                    adapted = portfolio_signal(s, clock)
                    VirtualPortfolio._validate_signal(adapted, s.known_at, {symbol: clock_map[s.known_at]}, adapted.mode)
                    signals[(arm, s.signal_id)] = s
                owner['READY'][arm] += len(rows)
        for arm in ('enabled', 'disabled_cost_gate'):
            folder = base / 'simulation' / arm
            detector_hashes = {s: digest(base / 'detection' / s / 'manifest.json') for s in lock['symbols']}
            expected = sha256(evidence_json({'lock': lock, 'detection': detector_hashes, 'arm': arm}).encode()).hexdigest()
            resume(folder, expected, True)
            if any(d['trade_entry_allowed'] is not False for d in read_rows(folder / 'shared_journal.jsonl.gz')):
                raise ValueError('Unsafe execution decision')
            for account, name in [('independent', 'independent_cases.jsonl.gz'), ('shared', 'shared_trades.jsonl.gz')]:
                rows = read_rows(folder / name)
                ids = set()
                for t in rows:
                    if t['trade_id'] in ids or t.get('trade_entry_allowed', False):
                        raise ValueError('Unsafe/duplicate trade')
                    ids.add(t['trade_id'])
                    from datetime import datetime
                    ready, entry = datetime.fromisoformat(t['ready_time']), datetime.fromisoformat(t['entry_interval_start'])
                    if ready > entry:
                        raise ValueError('Entry before READY')
                    if t['aggregate_risk_fraction_after'] > .06 + 1e-9 or t['risk_percent'] != .02 or t['leverage'] != 3:
                        raise ValueError('Canonical risk cap regression')
                    if arm == 'enabled' and not signals[(arm, t['signal_id'])].evidence['anti_scalp']['allowed']:
                        raise ValueError('Anti-Scalp bypass at entry')
                    source = signals[(arm, t['signal_id'])]
                    d = check_anti_scalp(direction=source.direction, entry=t['theoretical_entry'],
                                        target=source.targets[0], setup_tf=actual_setup_tf(source),
                                        context_tf=source.evidence['macro_context_tf'],
                                        main_setup_valid=True, context_valid=True,
                                        target_known_before_entry=source.known_at <= entry)
                    if arm == 'enabled' and not d.allowed:
                        raise ValueError('Actual reference Anti-Scalp bypass')
                    if t['htf'] != actual_setup_tf(source):
                        raise ValueError('Trade main role mismatch')
                    if t['status'] == 'CLOSED' and abs(sum(f['quantity'] for f in t['fills'])-t['quantity']) > 1e-8*max(1,t['quantity']):
                        raise ValueError('Partial exit quantity mismatch')
                m = closed_statistics(rows)
                owner['ledger_counts'][arm+'/'+account] = {'FILLED': len(rows), 'CLOSED': m['total_trades'],
                                                            'OPEN': len(rows)-m['total_trades'],
                                                            'cost_identity_residual': m['cost_identity_residual']}
        owner['READY'] = dict(owner['READY'])
        result['cohorts'][cohort] = owner
    name = 'artifact_integrity_receipt'+('_'+args.cohort if args.cohort else '')+'.json'
    write_json(ROOT / 'qa' / name, result)


if __name__ == '__main__':
    main()
