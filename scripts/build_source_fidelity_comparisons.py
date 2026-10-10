"""Read-only cohort/selection/account-policy comparison; no fitting or tuning."""
from __future__ import annotations

import json
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itertools

from audit_source_fidelity_exits import statistics as matched_statistics
from audit_source_fidelity_state import BASE, REPO, ROOT, population
from run_medium_term_research import read_rows, write_json

from crypto_bot.research.v2_common import write_csv


def statistics(rows):
    annotated = []
    for row in rows:
        value = dict(row)
        value['MFE_R'] = row.get('MFE_R', row['MFE'] * row['quantity'] / row['risk_amount'])
        value['MAE_R'] = row.get('MAE_R', row['MAE'] * row['quantity'] / row['risk_amount'])
        annotated.append(value)
    return matched_statistics(annotated)


def old_tree(row, model):
    node = 0
    path = []
    while model['children_left'][node] != -1:
        name = model['features'][model['feature'][node]]
        value = struct.unpack('f', struct.pack('f', row[name]))[0]
        left = value <= model['threshold'][node]
        path.append({'feature': name, 'value': value, 'threshold': model['threshold'][node],
                     'condition': '<=' if left else '>'})
        node = model['children_left'][node] if left else model['children_right'][node]
    return node, model['probability_WIN'][node] >= .55, path


def feature_triplet(signal, targets, fractions):
    # Same pure planned-risk equations as archived v2_features.features.
    s = 1 if signal['direction'] == 'LONG' else -1
    entry, stop = signal['entry'], signal['stop']
    fee, slip = .0006, .0002
    fill, stop_fill = entry * (1 + s * slip), stop * (1 - s * slip)
    unit_risk = s * (fill - stop_fill) + fee * (fill + stop_fill)
    quantity = 23.4 / unit_risk
    gross = quantity * math.fsum(f * s * (t - entry) for f, t in zip(fractions, targets, strict=True))
    fees = quantity * fee * (fill + math.fsum(f * t * (1 - s * slip)
                                           for f, t in zip(fractions, targets, strict=True)))
    slippage = quantity * (abs(fill - entry) + math.fsum(f * abs(t * (1 - s * slip) - t)
                                                      for f, t in zip(fractions, targets, strict=True)))
    return {'gross_target_R': gross / 23.4, 'friction_R': (fees + slippage) / 23.4,
            'net_target_R': (gross - fees - slippage) / 23.4}


def main():
    signals, trades, _ = population()
    old = json.loads((ROOT / 'old_tree_reconstruction.json').read_text())
    rows = []
    for t in trades:
        signal = signals[t['signal_id']]
        for name, targets, fractions in [
            ('CURRENT_WEIGHTED_PLAN', signal['targets'], signal['fractions']),
            ('FULL_CURRENT_FIRST_TARGET', signal['targets'][:1], [1.])]:
            feature = feature_triplet(signal, targets, fractions)
            leaf, admitted, path = old_tree(feature, old['model'])
            rows.append({'signal_id': t['signal_id'], 'trade_id': t['trade_id'],
                         'symbol': t['symbol'], 'entry': t['entry_interval_start'],
                         'feature_plan': name, **feature, 'leaf': leaf, 'admitted': admitted,
                         'conditions': path, 'baseline_result': 'WIN' if t['net_pnl'] > 0 else 'LOSS',
                         'baseline_net_pnl': t['net_pnl'], 'trade_entry_allowed': False})
    write_csv(ROOT / 'frozen_meta_tree_on_880.csv', rows)
    projections = {}
    for name in ('CURRENT_WEIGHTED_PLAN', 'FULL_CURRENT_FIRST_TARGET'):
        subset = [r for r in rows if r['feature_plan'] == name]
        projections[name] = dict(Counter(
            ('ADMITTED_' if r['admitted'] else 'REJECTED_') + r['baseline_result'] for r in subset))
    off = read_rows(BASE / 'simulation/disabled_cost_gate/shared_trades.jsonl.gz')
    on_map, off_map = ({t['signal_id']: t for t in group} for group in (trades, off))
    changes = []
    for sid in sorted(set(on_map) | set(off_map)):
        a, b = on_map.get(sid), off_map.get(sid)
        changes.append({'signal_id': sid, 'ON_FILLED': bool(a), 'OFF_FILLED': bool(b),
                        'ON_result': ('WIN' if a['net_pnl'] > 0 else 'LOSS') if a else None,
                        'OFF_result': ('WIN' if b['net_pnl'] > 0 else 'LOSS') if b else None,
                        'ON_net': a['net_pnl'] if a else None, 'OFF_net': b['net_pnl'] if b else None})
    write_csv(ROOT / 'cost_gate_ON_OFF_actual_entries.csv', changes)
    native = REPO / 'data/reports/medium_term_2026_10_10/role_corrected_v2/native_bybit_2026'
    native_ind = read_rows(native / 'simulation/enabled/independent_cases.jsonl.gz')
    primary_ind = read_rows(BASE / 'simulation/enabled/independent_cases.jsonl.gz')
    independent_map = {t['signal_id']: t for t in primary_ind}
    assert on_map.keys() <= independent_map.keys()
    assert all(independent_map[sid]['net_pnl'] * t['net_pnl'] > 0 for sid, t in on_map.items())
    journal = read_rows(BASE / 'simulation/enabled/shared_journal.jsonl.gz')
    reasons = defaultdict(set)
    for event in journal:
        if event.get('reason') in {'DAILY_LOSS_LIMIT_LATCHED', 'ISOLATED_MARGIN_BUDGET', 'PREVIOUS_POSITION_STILL_OPEN'}:
            reasons[event['signal_id']].add(event['reason'])
    capital_rows = [
        {'signal_id': t['signal_id'], 'symbol': t['symbol'], 'entry': t['entry_interval_start'],
         'INDEPENDENT_result': 'WIN' if t['net_pnl'] > 0 else 'LOSS',
         'SHARED_FILLED': t['signal_id'] in on_map, 'admission_reasons': sorted(reasons[t['signal_id']]),
         'independent_net': t['net_pnl'], 'shared_net': on_map.get(t['signal_id'], {}).get('net_pnl')}
        for t in primary_ind]
    write_csv(ROOT / 'capital_admission_2352_to_880.csv', capital_rows)
    chain = [
        ('OLD_META_TEST_SELECTED', old['admitted_TEST']['WR']),
        ('OLD_TEST_UNFILTERED_INDEPENDENT', old['baseline_TEST']['WR']),
        ('CURRENT_NATIVE_FULL_INDEPENDENT', statistics(native_ind)['win_rate']),
        ('CURRENT_PRIMARY_INDEPENDENT', statistics(primary_ind)['win_rate']),
        ('CURRENT_PRIMARY_SHARED', statistics(trades)['win_rate'])]
    decomposition = [{'from': a[0], 'to': b[0], 'from_WR': a[1], 'to_WR': b[1],
                      'difference_percentage_points': 100 * (a[1] - b[1]),
                      'identification': ('EXACT_SAME_TEST_FROZEN_LEAF_SELECTION' if i == 0 else
                                         'EXACT_SAME_COHORT_SHARED_ADMISSION_SUBSET_NO_COMMON_RESULT_FLIPS' if i == 3 else
                                         'DESCRIPTIVE_COMBINED_SCOPE_CHANGE_NOT_SINGLE_CAUSAL_EFFECT')}
                     for i, (a, b) in enumerate(itertools.pairwise(chain))]
    write_csv(ROOT / 'winrate_decomposition.csv', decomposition)
    groups = defaultdict(list)
    for t in trades:
        signal = signals[t['signal_id']]
        for axis, value in [('symbol', t['symbol']), ('direction', t['direction']),
                            ('setup_branch', signal['setup_type']),
                            ('year', t['entry_interval_start'][:4]),
                            ('mapping', str(signal['htf']) + '/' + str(signal['ltf']))]:
            groups[(axis, value)].append(t)
    write_csv(ROOT / 'baseline_C_breakdowns.csv', [
        {'axis': axis, 'value': value, **statistics(ts)} for (axis, value), ts in sorted(groups.items())])
    shared = json.loads((BASE / 'simulation/enabled/shared_summary.json').read_text())
    variants = [
        {'variant': 'A_EXACT_ORIGINAL', 'status': 'NOT_IDENTIFIABLE_FROM_AVAILABLE_SOURCES',
         'signals': None, 'READY': None, 'FILLED': None, 'CLOSED': None, 'trade_entry_allowed': False},
        {'variant': 'B_EXACT_ORIGINAL_PLUS_NON_METHOD_ALTERING_ANTI_SCALP',
         'status': 'DEPENDENT_ON_UNIDENTIFIABLE_A', 'signals': None, 'READY': None,
         'FILLED': None, 'CLOSED': None, 'trade_entry_allowed': False},
        {'variant': 'C_FROZEN_19404EC', 'status': 'VERIFIED_RESUME_EXISTING',
         'signals': len(signals), 'READY': len(signals), 'FILLED': 880, 'CLOSED': 880,
         **statistics(trades), 'max_drawdown_fraction': shared['max_drawdown_fraction'],
         'trade_entry_allowed': False}]
    write_csv(ROOT / 'strategy_variant_A_B_C.csv', variants)
    write_json(ROOT / 'comparison_summary.json', {
        'frozen_tree_current_880_feature_projections': projections,
        'projection_limit': 'Fixed old fitted numerical tree on current planned quotes; not original educational ALLOW or an executed portfolio variant',
        'old_TEST_exact_rejected': {'WIN': 588, 'LOSS': 2382, 'CLOSED': 2970},
        'winrate_chain': decomposition,
        'total_difference_percentage_points': 100 * (chain[0][1] - chain[-1][1]),
        'cost_gate_ON': statistics(trades), 'cost_gate_OFF': statistics(off),
        'capital_admission_removed': dict(Counter(r['INDEPENDENT_result'] for r in capital_rows if not r['SHARED_FILLED'])),
        'capital_admission_common_result_flips': 0,
        'cost_gate_changed_entry_results': {
            'ON_only': dict(Counter('WIN' if on_map[s]['net_pnl'] > 0 else 'LOSS' for s in on_map.keys() - off_map.keys())),
            'OFF_only': dict(Counter('WIN' if off_map[s]['net_pnl'] > 0 else 'LOSS' for s in off_map.keys() - on_map.keys()))},
        'cost_gate_entry_membership': {'common': len(on_map.keys() & off_map.keys()),
                                     'ON_only': len(on_map.keys() - off_map.keys()),
                                     'OFF_only': len(off_map.keys() - on_map.keys()),
                                     'common_result_flips': sum(a['net_pnl'] * off_map[sid]['net_pnl'] < 0
                                                                for sid, a in on_map.items() if sid in off_map)},
        'strategy_variants': variants, 'trade_entry_allowed': False})
    print('COMPARISONS_COMPLETE', projections, flush=True)


if __name__ == '__main__':
    main()
