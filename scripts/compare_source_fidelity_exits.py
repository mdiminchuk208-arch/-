"""Publish every fixed-entry outcome transition; never select a model."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_source_fidelity_exits import MODELS
from audit_source_fidelity_state import ROOT
from run_medium_term_research import read_rows, write_json

from crypto_bot.research.v2_common import write_csv


def result(trade):
    if trade is None:
        return 'UNDEFINED'
    if trade['status'] != 'CLOSED':
        return 'OPEN'
    return 'WIN' if trade['net_pnl'] > 0 else 'LOSS' if trade['net_pnl'] < 0 else 'BE'


def main():
    models = {name: {r['signal_id']: r for r in read_rows(ROOT / 'matched_exits' / (name + '.jsonl.gz'))}
              for name in MODELS}
    rows = []
    totals = {}
    canonical = models['C_CANONICAL']
    for name, cases in models.items():
        if name == 'C_CANONICAL':
            continue
        subset = []
        for sid, baseline in canonical.items():
            other = cases.get(sid)
            row = {'signal_id': sid, 'trade_id': baseline['trade_id'], 'symbol': baseline['symbol'],
                   'entry': baseline['entry_interval_start'], 'model': name,
                   'canonical_result': result(baseline), 'diagnostic_result': result(other),
                   'canonical_exit': baseline['exit_time'], 'diagnostic_exit': other.get('exit_time') if other else None,
                   'canonical_reason': baseline['exit_reason'], 'diagnostic_reason': other.get('exit_reason') if other else None,
                   'canonical_net': baseline['net_pnl'], 'diagnostic_net': other.get('net_pnl') if other else None,
                   'net_delta': other['net_pnl'] - baseline['net_pnl'] if other and other['status'] == 'CLOSED' else None,
                   'canonical_fills': baseline['fills'], 'diagnostic_fills': other['fills'] if other else None,
                   'quantity_unchanged': other['quantity'] == baseline['quantity'] if other else None,
                   'entry_price_unchanged': other['actual_entry_after_slippage'] == baseline['actual_entry_after_slippage'] if other else None,
                   'trade_entry_allowed': False}
            rows.append(row)
            subset.append(row)
        common = [r for r in subset if r['net_delta'] is not None]
        totals[name] = {
            'all_entries': len(subset), 'common_closed': len(common),
            'transitions': dict(Counter(r['canonical_result'] + '_TO_' + r['diagnostic_result'] for r in subset)),
            'common_net_delta': sum(r['net_delta'] for r in common),
            'exit_time_changed': sum(r['canonical_exit'] != r['diagnostic_exit'] for r in common),
            'all_common_quantity_and_price_identical': all(r['quantity_unchanged'] and r['entry_price_unchanged'] for r in common)}
    write_csv(ROOT / 'exit_outcome_transitions.csv', rows)
    write_json(ROOT / 'exit_outcome_comparison.json', {'models': totals, 'trade_entry_allowed': False,
        'scope': 'Diagnostic independent exits on fixed entries; no shared NAV, optimal model selection or entry causal claims'})
    print(json.dumps(totals), flush=True)


if __name__ == '__main__':
    main()
