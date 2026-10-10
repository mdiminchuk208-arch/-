"""Verify completed dependency locks, every READY proof and executed trade."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from crypto_bot.research.medium_statistics import closed_statistics
from crypto_bot.strategy.source_medium_term import portfolio_signal
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    roots = {'bybit_2023_2025': ROOT / 'compiled_primary/bybit_2023_2025',
             'native_bybit_2026': ROOT / 'causal_final/native_bybit_2026'}
    result = {'status': 'PASS', 'cohorts': {}, 'baseline': preserved_baseline(),
              'trade_entry_allowed': False}
    for cohort in ('bybit_2023_2025', 'native_bybit_2026'):
        base = roots[cohort]
        lock = json.loads((base / 'run_lock.json').read_text())
        for name, expected in lock['code_and_data_hashes'].items():
            if digest(REPO / name) != expected:
                raise ValueError('Registered dependency changed: ' + name)
        clock = lock['policy']['execution_clock']
        owner = {'READY': Counter(), 'known_timestamps_checked': 0, 'ledger_counts': {}}
        signals = {}
        for symbol in lock['symbols']:
            folder = base / 'detection' / symbol
            manifest = json.loads((folder / 'manifest.json').read_text())
            resume(folder, manifest['fingerprint'], True)
            candles, _ = load_data(cohort, symbol, policy)
            clock_map = {c.close_time: c for c in candles[clock]}
            for arm in ('enabled', 'disabled_cost_gate'):
                rows = read_rows(folder / arm / 'signals.jsonl.gz')
                physical = set()
                for raw in rows:
                    s = deserialize_signal(raw)
                    if s.trade_entry_allowed or s.htf not in (60, 240):
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
            manifest = json.loads((folder / 'manifest.json').read_text())
            resume(folder, manifest['fingerprint'], True)
            for account, name in [('independent', 'independent_cases.jsonl.gz'), ('shared', 'shared_trades.jsonl.gz')]:
                rows = read_rows(folder / name)
                ids = set()
                for t in rows:
                    if t['trade_id'] in ids or t['trade_entry_allowed']:
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
                    if t['status'] == 'CLOSED' and abs(sum(f['quantity'] for f in t['fills'])-t['quantity']) > 1e-8*max(1,t['quantity']):
                        raise ValueError('Partial exit quantity mismatch')
                m = closed_statistics(rows)
                owner['ledger_counts'][arm+'/'+account] = {'FILLED': len(rows), 'CLOSED': m['total_trades'],
                                                            'OPEN': len(rows)-m['total_trades'],
                                                            'cost_identity_residual': m['cost_identity_residual']}
        owner['READY'] = dict(owner['READY'])
        result['cohorts'][cohort] = owner
    write_json(ROOT / 'qa/artifact_integrity_receipt.json', result)


if __name__ == '__main__':
    main()
