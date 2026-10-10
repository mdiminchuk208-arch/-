"""Build READY-only features and sequester chronological test labels."""
from __future__ import annotations

import copy
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from crypto_bot.research.v2_common import (
    BASE,
    BASELINE,
    OUT,
    canonical,
    digest,
    read_jsonl,
    seconds,
    write_csv,
    write_json,
    write_jsonl,
)
from crypto_bot.research.v2_features import (
    FeatureContext,
    NativeSeries,
    features,
    load_native,
)


def verify() -> dict[str, Any]:
    lock = json.loads((BASE/'run_lock.json').read_text())
    manifest = json.loads((BASE/'manifest.json').read_text())
    assert manifest['status'] == 'COMPLETE'
    checked = {}
    for kind, mapping, root in [('artifacts', manifest['artifacts'], BASE),
                                ('implementation', lock['implementation'], Path('.')),
                                ('inputs', lock['inputs'], Path('.'))]:
        for path, value in mapping.items():
            expected = value['sha256'] if isinstance(value, dict) else value
            assert digest(root/path) == expected, path
        checked[kind] = len(mapping)
    checked['dataset_candles'] = sum(r['candles'] for r in lock['inputs'].values())
    assert checked['inputs'] == 40 and checked['dataset_candles'] == 993575
    result = {'status': 'PASS', 'baseline': BASELINE, 'checks': checked,
              'root_manifest_sha256': digest(BASE/'manifest.json'), 'dataset_hashes': lock['inputs'],
              'trade_entry_allowed': False}
    write_json(OUT/'baseline_verification.json', result)
    return lock


def labels() -> list[dict[str, Any]]:
    rows = []
    for r in read_jsonl(BASE/'cohorts/SOURCE_PERMITTED_UNION/CANCEL_SOURCE_POI_INVALIDATION/cases.jsonl.gz'):
        rows.append({k: r.get(k) for k in [
            'physical_opportunity_id', 'signal_id', 'symbol', 'status', 'ready_time',
            'entry_interval_start', 'entry_interval_end', 'exit_time', 'result', 'result_R',
            'net_pnl', 'quote_gross_pnl', 'gross_pnl', 'fees', 'slippage', 'risk_amount',
            'holding_seconds', 'quantity', 'entry', 'entry_reference', 'exit_reason']})
    assert len(rows) == 16351 and len({r['physical_opportunity_id'] for r in rows}) == len(rows)
    return rows


def partition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    closed = sorted((r for r in rows if r['status'] == 'CLOSED'),
                    key=lambda r: (r['ready_time'], r['physical_opportunity_id']))
    assert len(closed) == 16333
    validation = closed[int(len(closed)*.6)]['ready_time']
    test = closed[int(len(closed)*.8)]['ready_time']
    for r in rows:
        t = r['ready_time']
        r['split'] = 'TRAIN' if t < validation else 'VALIDATION' if t < test else 'TEST'
        boundary = validation if r['split'] == 'TRAIN' else test if r['split'] == 'VALIDATION' else None
        r['label_eligible'] = r['status'] == 'CLOSED' and (boundary is None or r['exit_time'] < boundary)
        r['purge_reason'] = ('RIGHT_CENSORED_OPEN' if r['status'] != 'CLOSED' else
                             'EXIT_NOT_KNOWN_BEFORE_NEXT_SPLIT' if not r['label_eligible'] else None)
        assert r['ready_time'] <= r['entry_interval_start']
    result = {'order': 'ORIGINAL_READY_THEN_PHYSICAL_ID; TIMESTAMP_TIES_TOGETHER',
              'ratio_requested': [.6, .2, .2], 'validation_first_READY': validation,
              'test_first_READY': test, 'all_CLOSED': len(closed), 'all_OPEN': len(rows)-len(closed),
              'split_CLOSED_counts': dict(Counter(r['split'] for r in closed)),
              'eligible_CLOSED_counts': dict(Counter(r['split'] for r in rows if r['label_eligible'])),
              'purged_counts': dict(Counter(r['split'] for r in rows if r['status']=='CLOSED' and not r['label_eligible'])),
              'cutoff_policy': 'TRAIN_EXIT_STRICTLY_BEFORE_VALIDATION_READY; VALIDATION_EXIT_STRICTLY_BEFORE_TEST_READY',
              'provenance': 'PREVIOUSLY_INSPECTED_DEVELOPMENT; V2_SPECIFIC_TEST; NOT_UNTOUCHED_MARKET_OOS',
              'trade_entry_allowed': False}
    return result


def future_qa(signal: dict[str, Any], ctx: FeatureContext, policy: dict[str, Any]) -> dict[str, Any]:
    cutoff = seconds(signal['known_at'])
    variants = [r for vs in ctx.variants.values() for r in vs]
    flows = [r for vs in ctx.flows.values() for r in vs]
    ranges = [r for vs in ctx.ranges.values() for r in vs]
    expected = features(signal, ctx, policy)
    pref_native = {tf: NativeSeries([r for r in ns.rows if r['close_time'] <= cutoff], tf)
                   for tf, ns in ctx.native.items()}
    pref_flows = [copy.deepcopy(r) for r in flows if seconds(r['known_at']) <= cutoff]
    for r in pref_flows:
        if r.get('invalidated_at') and seconds(r['invalidated_at']) > cutoff:
            r['invalidated_at'] = None
    pref_variants = [r for r in variants if seconds(r['known_at']) <= cutoff]
    pref_ranges = [r for r in ranges if seconds(r['known_at']) <= cutoff]
    prefix = FeatureContext(pref_native, pref_variants, pref_flows, pref_ranges, ctx.family)
    assert canonical(features(signal, prefix, policy)) == canonical(expected)
    mutated_native = {tf: NativeSeries([r if r['close_time'] <= cutoff else
                       {**r, 'high': r['high']*100, 'low': r['low']*.001,
                        'open': r['open']*10, 'close': r['close']*10} for r in ns.rows], tf)
                      for tf, ns in ctx.native.items()}
    mutated_flows = copy.deepcopy(flows)
    for r in mutated_flows:
        if seconds(r['known_at']) > cutoff:
            r['direction'] = 'SHORT' if r['direction']=='LONG' else 'LONG'
            r['destination_poi']['low'] *= .01
        if r.get('invalidated_at') and seconds(r['invalidated_at']) > cutoff:
            r['invalidated_at'] = '2099-01-01T00:00:00+00:00'
    mutated_variants = copy.deepcopy(variants)
    for r in mutated_variants:
        if seconds(r['known_at']) > cutoff:
            r['path_id'] = 'BREAKER_CONSERVATIVE_STOP'
    mutated_ranges = copy.deepcopy(ranges)
    for r in mutated_ranges:
        if seconds(r['known_at']) > cutoff:
            r['high'] *= 100
            r['low'] *= .001
    mutation = FeatureContext(mutated_native, mutated_variants, mutated_flows, mutated_ranges, ctx.family)
    assert canonical(features(signal, mutation, policy)) == canonical(expected)
    return {'signal_id': signal['signal_id'], 'symbol': signal['symbol'], 'path_id': signal['evidence']['path_id'],
            'cutoff': signal['known_at'], 'prefix_equality': 'PASS', 'four_TF_future_mutation': 'PASS',
            'future_flow_invalidation_mutation': 'PASS', 'future_family_witness_mutation': 'PASS',
            'future_range_event_mutation': 'PASS'}


def main() -> None:
    assert not (OUT/'split.json').exists(), 'Immutable completed feature stage; use a new root for a new study.'
    lock = verify(); policy = lock['policy']
    cases = labels(); split = partition(cases)
    by_id = {r['signal_id']: r for r in cases}
    family = {r['path_id']: r['setup_family'] for r in policy['paths']}
    result = []; qa = []
    for symbol in policy['symbol_priority']:
        selected = {}; variants = []
        for r in read_jsonl(BASE/f'segments/{symbol}/signals.jsonl.gz'):
            e = r['evidence']
            variants.append({'signal_id': r['signal_id'], 'known_at': r['known_at'],
                             'physical_opportunity_id': e['physical_opportunity_id'], 'path_id': e['path_id']})
            if r['signal_id'] in by_id:
                selected[r['signal_id']] = r
        flows = list(read_jsonl(BASE/f'segments/{symbol}/flow_history.jsonl.gz'))
        # Range audit contains mutable nested POIs. Use only immutable event facts.
        ranges = [{k: r[k] for k in ['tf', 'direction', 'known_at', 'range_id', 'low', 'high']}
                  for r in read_jsonl(BASE/f'segments/{symbol}/range_audit.jsonl.gz')]
        ctx = FeatureContext(load_native(symbol), variants, flows, ranges, family)
        witnesses = {}
        for sid, r in sorted(selected.items(), key=lambda kv: (kv[1]['known_at'], kv[0])):
            row = features(r, ctx, policy); case = by_id[sid]
            assert row['physical_opportunity_id'] == case['physical_opportunity_id']
            assert math_close(row['expected_quantity'], case['quantity'])
            assert math_close(row['entry_after_slippage'], case['entry'])
            row['split'] = case['split']; row['label_eligible'] = case['label_eligible']
            row['status'] = case['status']
            result.append(row)
            witnesses.setdefault((r['evidence']['path_id'], case['split']), r)
        for r in witnesses.values():
            qa.append(future_qa(r, ctx, policy))
        print(symbol, 'source_variants', len(variants), 'filled_features', len(selected),
              'prefix_future_checks', len(witnesses), flush=True)
    assert len(result) == len(cases)
    result.sort(key=lambda r: (r['READY'], r['physical_opportunity_id']))
    write_jsonl(OUT/'features.jsonl.gz', result)
    write_csv(OUT/'strategy_v2_feature_table.csv.gz', [r for r in result if r['status']=='CLOSED'])
    write_csv(OUT/'strategy_v2_open_feature_table.csv.gz', [r for r in result if r['status']!='CLOSED'])
    for name in ['TRAIN', 'VALIDATION', 'TEST']:
        write_jsonl(OUT/f'labels_{name}.jsonl.gz', (r for r in cases if r['split']==name))
        write_jsonl(OUT/f'features_{name}.jsonl.gz', (r for r in result if r['split']==name))
    split['partitions'] = {p.name: digest(p) for p in OUT.glob('*_*.jsonl.gz')}
    split['feature_rows'] = len(result)
    split['builder_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    write_json(OUT/'split.json', split)
    write_json(OUT/'strategy_v2_leakage_audit.json', {
        'status': 'PASS_FEATURE_EXTRACTION', 'feature_cutoff': 'ORIGINAL_READY',
        'features_built_from': 'ORIGINAL_SIGNAL_PLUS_CAUSAL_NATIVE_CONTEXT; NO_CASE_ARGUMENT',
        'known_at_recursive_audit': 'PASS_ALL_16351', 'physical_dedup': 'PASS_16351_DISTINCT',
        'quantity_and_expected_entry_original_parity': 'PASS_ALL_16351',
        'prefix_and_future_checks': qa, 'split': split,
        'forbidden_inputs': ['status', 'label_eligible', 'split', 'physical_opportunity_id', 'signal_id',
                             'symbol', 'hour', 'weekday', 'session', 'month', 'mapping', 'direction',
                             'entry_interval_start', 'entry_interval_end', 'exit_time', 'net_pnl', 'fees',
                             'slippage', 'result', 'result_R', 'holding_seconds', 'READY_to_fill'],
        'test_labels_opened_for_selection': False, 'trade_entry_allowed': False})


def math_close(a: float, b: float) -> bool:
    return abs(a-b) <= 1e-10*max(1, abs(a), abs(b))


if __name__ == '__main__':
    main()
