"""Read-only source qualification, native body proof and global identity QA."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import asdict, replace
from math import isclose
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_pdf_native import evidence_json, sign
from crypto_bot.strategy.source_physical import canonical_physical_signals
from crypto_bot.strategy.source_sfp_lifecycle import repair_sfp_candidates

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_permitted_bybit import REPO, digest, instant, read_rows, write_json
from run_source_permitted_physical_union import verify_base


def signals(rows):
    return [SourceSignal(**{**r, 'known_at': instant(r['known_at']),
                           'targets': tuple(r['targets']), 'fractions': tuple(r['fractions'])})
            for r in rows]


def native_data(policy, symbols):
    return {(symbol, tf): [c.to_strategy_candle(tf * 60000) for c in
                           read_klines_csv(REPO / f'data/history/bybit/{symbol}/{tf}.csv')]
            for symbol in symbols for tf in policy['native_timeframes']}


def ordered(rows):
    return sorted(rows, key=lambda r: r['signal_id'])


def native_case_formation(final, policy, native, valid):
    """Independently reconcile native OHLC formations and all frozen ATR stops."""
    primary = read_rows(final / 'cohorts/SOURCE_PERMITTED_UNION' /
                        policy['primary_cancellation'] / 'primary_cases.jsonl.gz')
    checked = Counter(); atrs = {}
    atr_count = 0
    for r in valid.values():
        if r['evidence']['path_id'] != 'SFP_ATR_STOP':
            continue
        key = (r['symbol'], r['htf']); p = r['evidence']['htf_poi']
        if key not in atrs:
            ranges = []; values = []
            for i, c in enumerate(native[key]):
                previous = native[key][i-1].close if i else c.open
                ranges.append(max(c.high-c.low, abs(c.high-previous), abs(c.low-previous)))
                values.append(sum(ranges[:14])/14 if i == 13 else
                              (values[-1]*13+ranges[-1])/14 if i >= 14 else None)
            atrs[key] = values
        frozen = atrs[key][p['origin_index']]
        assert frozen is not None
        expected = p['raid']['extreme']-sign(r['direction'])*frozen
        assert isclose(r['stop'], expected, rel_tol=1e-12)
        atr_count += 1
    for t in primary:
        e = t['evidence']; q = e['ltf_poi']; s = sign(t['direction'])
        cs = native[(t['symbol'], e['entry_zone_tf'])]
        if q['kind'] == 'FVG':
            a, c = cs[q['origin_index']], cs[q['origin_index']+2]
            low, high = (a.high, c.low) if s == 1 else (c.high, a.low)
            assert low < high and (q['low'], q['high']) == (low, high)
            assert instant(q['formed_at']) == c.close_time
            checked['native_three_candle_FVG'] += 1
        elif q['kind'] == 'ORDER_BLOCK':
            a = cs[q['origin_index']]; c = cs[q['origin_index']+1]
            assert (q['low'], q['high']) == (a.low, a.high)
            assert s*(a.close-a.open) < 0 and s*(c.close-c.open) > 0
            assert (c.open <= a.close and c.close > a.open) if s == 1 else (
                c.open >= a.close and c.close < a.open)
            raid = q['raid']
            assert raid['candle_index'] == q['origin_index']
            assert raid['extreme'] == (a.low if s == 1 else a.high)
            assert s*(raid['extreme']-raid['price']) < 0
            checked['native_raid_body_engulf_full_wick_OB'] += 1
        if t['path_id'].startswith('SFP_'):
            p = e['htf_poi']; pattern = native[(t['symbol'], t['htf'])][p['origin_index']]
            raid = p['raid']; assert (p['low'], p['high']) == (pattern.low, pattern.high)
            assert raid['extreme'] == (pattern.low if s == 1 else pattern.high)
            assert s*(raid['extreme']-raid['price']) < 0 and s*(pattern.close-raid['price']) > 0
            opens = [c.open_time for c in native[(t['symbol'], 5)]]
            following = native[(t['symbol'], 5)][bisect_left(opens, pattern.close_time)]
            assert following.open_time == pattern.close_time
            # DOC16 P0082–83 requires the reclaimed side of the swept level;
            # it does not require OPEN inside the SFP candle's entire wick.
            assert s*(following.open-raid['price']) > 0
            assert p['confluence']['next_real_5m_open'] == following.open
            assert instant(p['known_at']) == following.close_time
            assert instant(e['confirmations']['bos']['known_at']) > following.close_time
            checked['native_SFP_raid_reclaim_next_OPEN_and_post_reaction_BOS'] += 1
    return {'status': 'PASS', 'primary_cases': len(primary), 'native_primary_formation_checks': dict(checked),
            'all_source_valid_ATR_stops_independently_recomputed': atr_count,
            'ATR_method': '14_NATIVE_TR_SEED_THEN_WILDER_RMA_AT_FROZEN_PATTERN_INDEX',
            'trade_entry_allowed': False}


def prefix_check(base, final, policy, cache):
    with gzip.open(cache, 'rt') as f:
        saved = json.load(f)
    assert saved['run_lock_sha256'] == digest(base / 'run_lock.json')
    cutoff = instant(saved['cutoff']); symbol = saved['symbol']
    raw = signals(saved['observations']['signals'])
    full_native = native_data(policy, [symbol])
    prefix_native = {k: [c for c in cs if c.close_time <= cutoff] for k, cs in full_native.items()}
    mutated_native = {k: cs + [replace(c, open=c.open * 2, high=c.high * 2,
                                      low=c.low * .5, close=c.close * 2)
                               for c in full_native[k] if c.close_time > cutoff][:8]
                      for k, cs in prefix_native.items()}
    qualified, proof, cancellations = repair_sfp_candidates(raw, prefix_native)
    altered, mutated_proof, mutated_cancellations = repair_sfp_candidates(raw, mutated_native)
    mapped, claims = canonical_physical_signals(qualified, policy)
    mutated_mapped, mutated_claims = canonical_physical_signals(altered, policy)
    assert evidence_json([asdict(r) for r in mapped]) == evidence_json([asdict(r) for r in mutated_mapped])
    assert evidence_json(proof) == evidence_json(mutated_proof)
    assert evidence_json(claims) == evidence_json(mutated_claims)
    assert evidence_json(cancellations) == evidence_json(
        [r for r in mutated_cancellations if r['known_at'] <= cutoff])
    if final is not None:
        full = [r for r in read_rows(final / 'segments' / symbol / 'signals.jsonl.gz')
                if instant(r['known_at']) <= cutoff]
        assert evidence_json(ordered(full)) == evidence_json(ordered([asdict(r) for r in mapped]))
        full_proof = [r for r in read_rows(final / 'source_qualification.jsonl.gz')
                      if r['signal_id'] in {s.signal_id for s in raw}]
        assert evidence_json(ordered(full_proof)) == evidence_json(ordered(proof))
        ids = {s.signal_id for s in qualified if s.evidence['path_id'].startswith('SFP_')}
        full_cancels = [r for r in read_rows(final / 'segments' / symbol / 'cancellations.jsonl.gz')
                        if r['signal_id'] in ids and r['cohort'] == policy['primary_cancellation']
                        and instant(r['known_at']) <= cutoff]
        assert evidence_json(ordered(full_cancels)) == evidence_json(ordered(cancellations))
    return {'status': 'PASS', 'fixed_cutoff': cutoff.isoformat(), 'symbol': symbol,
            'raw_candidate_READY': len(raw), 'source_valid_READY': len(qualified),
            'physical_IDs': len({r.evidence['physical_opportunity_id'] for r in mapped}),
            'source_paths': dict(Counter(r.evidence['path_id'] for r in mapped)),
            'native_prefix_candles': sum(len(cs) for cs in prefix_native.values()),
            'qualification': dict(Counter(r['status'] for r in proof)),
            'actual_body_cancellations_known_in_prefix': len(cancellations),
            'four_TF_future_mutation': 'PASS',
            'final_full_history_prefix_parity': 'PASS' if final is not None else 'PENDING_FINAL_ROOT',
            'cache_sha256': digest(cache), 'trade_entry_allowed': False}


def full_check(base, final, policy):
    raw_rows = [r for symbol in policy['symbol_priority'] for r in
                read_rows(base / 'segments' / symbol / 'signals.jsonl.gz')]
    final_rows = [r for symbol in policy['symbol_priority'] for r in
                  read_rows(final / 'segments' / symbol / 'signals.jsonl.gz')]
    raw = {r['signal_id']: r for r in raw_rows}; valid = {r['signal_id']: r for r in final_rows}
    proof = {r['signal_id']: r for r in read_rows(final / 'source_qualification.jsonl.gz')}
    native = native_data(policy, policy['symbol_priority'])
    times = {k: [c.close_time for c in cs] for k, cs in native.items()}
    first_pattern_body = {}
    for sid, r in raw.items():
        is_sfp = r['evidence']['path_id'].startswith('SFP_')
        if not is_sfp:
            assert sid in valid and sid not in proof
            continue
        e = r['evidence']; p = e['htf_poi']; s = sign(r['direction'])
        key = (r['symbol'], r['htf']); pk = (*key, p['zone_id'])
        if pk not in first_pattern_body:
            start = bisect_right(times[key], instant(p['known_at']))
            first_pattern_body[pk] = next((c for c in native[key][start:]
                                           if s * (c.close - p['raid']['extreme']) <= 0), None)
        broken = first_pattern_body[pk]; ready = instant(r['known_at'])
        expected_valid = broken is None or broken.close_time > ready
        assert (sid in valid) == expected_valid
        assert proof[sid]['PnL_used'] is False and proof[sid]['trade_entry_allowed'] is False
        if not expected_valid:
            assert proof[sid]['status'] == 'REJECT_SFP_INVALID_BEFORE_READY'
            assert instant(proof[sid]['source_body_invalidation_known_at']) == broken.close_time
        else:
            assert proof[sid]['status'] == 'PASS_SFP_VALID_AT_READY'
            assert proof[sid]['source_body_invalidation_known_at'] is None
    assert set(valid) <= set(raw)
    identity_keys = ('physical_opportunity_id', 'physical_context_id', 'physical_identity_known_at',
                     'physical_identity_rule')
    sfp_keys = ('structural_thesis', 'former_BOS_broken_level_not_new_protected_key', 'sfp_validity_at_READY')
    for sid, r in valid.items():
        original = raw[sid]
        assert {k: v for k, v in r.items() if k != 'evidence'} == {
            k: v for k, v in original.items() if k != 'evidence'}
        allowed = identity_keys + (sfp_keys if r['evidence']['path_id'].startswith('SFP_') else ())
        assert {k: v for k, v in r['evidence'].items() if k not in allowed} == {
            k: v for k, v in original['evidence'].items() if k not in allowed}
        assert instant(r['evidence']['physical_identity_known_at']) == instant(r['known_at'])
        assert r['evidence']['physical_context_id'] == original['evidence']['physical_opportunity_id']
        if r['evidence']['path_id'].startswith('SFP_'):
            assert r['evidence']['structural_thesis'] is None
            assert r['evidence']['former_BOS_broken_level_not_new_protected_key'] == original['evidence']['structural_thesis']
    body_count = 0
    for symbol in policy['symbol_priority']:
        old_strict = [r for r in read_rows(base / 'segments' / symbol / 'cancellations.jsonl.gz')
                      if r['signal_id'] in valid and r['cohort'] == 'CANCEL_STRICT_STRUCTURE']
        events = read_rows(final / 'segments' / symbol / 'cancellations.jsonl.gz')
        assert ordered(old_strict) == ordered([r for r in events if r['cohort'] == 'CANCEL_STRICT_STRUCTURE'])
        for event in events:
            r = valid[event['signal_id']]; e = r['evidence']
            if not (e['path_id'].startswith('SFP_') and event['cohort'] == policy['primary_cancellation']):
                continue
            at = instant(event['known_at']); s = sign(r['direction'])
            assert at > instant(r['known_at'])
            if event['reason'] == 'SFP_PATTERN_NATIVE_BODY_INVALIDATED':
                pk = (symbol, r['htf'], e['htf_poi']['zone_id'])
                assert first_pattern_body[pk].close_time == at
            else:
                assert event['reason'] == 'ENTRY_POI_NATIVE_BODY_INVALIDATED'
                key = (symbol, e['entry_zone_tf']); q = e['ltf_poi']
                start = bisect_right(times[key], instant(r['known_at']))
                boundary = q['low'] if s == 1 else q['high']
                first = next(c for c in native[key][start:] if s * (c.close - boundary) < 0)
                assert first.close_time == at
            body_count += 1
    selected = read_rows(final / 'selections/SOURCE_PERMITTED_UNION.jsonl.gz')
    local_zones = [(valid[r['signal_id']]['symbol'], valid[r['signal_id']]['direction'],
                    valid[r['signal_id']]['evidence']['entry_zone_tf'],
                    valid[r['signal_id']]['evidence']['ltf_poi']['zone_id']) for r in selected]
    assert len(local_zones) == len(set(local_zones))
    qualified, reproduced_proof, _ = repair_sfp_candidates(signals(raw_rows), native)
    mapped, claims = canonical_physical_signals(qualified, policy)
    assert len(mapped) == len(valid)
    for r in mapped:
        assert evidence_json(asdict(r)) == evidence_json(valid[r.signal_id])
    assert evidence_json(ordered(reproduced_proof)) == evidence_json(ordered(list(proof.values())))
    assert evidence_json(claims) == evidence_json(read_rows(final / 'physical_claims.jsonl.gz'))
    return {'status': 'PASS', 'raw_candidate_READY': len(raw), 'source_valid_READY': len(valid),
            'qualification': dict(Counter(r['status'] for r in proof.values())),
            'primary_native_SFP_body_events': body_count, 'native_source_trade_fields_unchanged': 'PASS',
            'strict_control_preserved': 'PASS', 'one_local_first_test_per_physical_union': 'PASS',
            'global_physical_claim_reconstruction': 'PASS', 'future_outcomes_used': False,
            'native_formation': native_case_formation(final, policy, native, valid),
            'trade_entry_allowed': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True); p.add_argument('--final', type=Path)
    p.add_argument('--prefix-cache', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); base = a.base.resolve(); final = a.final.resolve() if a.final else None
    lock = json.loads((base / 'run_lock.json').read_text())
    result = {'prefix': prefix_check(base, final, lock['policy'], a.prefix_cache), 'trade_entry_allowed': False}
    if final is not None:
        verify_base(base)
        result['full'] = full_check(base, final, lock['policy'])
    result['verifier_sha256'] = digest(Path(__file__))
    write_json(a.output, result); print(json.dumps(result, indent=2))
