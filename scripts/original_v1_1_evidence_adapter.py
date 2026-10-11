"""Causal RAW geometric proposals, never qualitative SOURCE labels or admission.

Enumeration conventions are preregistered separately from frozen U/N decisions.
Only externally supplied, explicitly validated evidence can complete a source case.
"""
from __future__ import annotations

import heapq
from hashlib import sha256

from original_strategy_executable_profile_v1 import evaluate, load_tree
from original_v1_1_financial_data import END, START, compact

VERSION = 'RAW_GEOMETRY_WITH_EXTERNAL_EVIDENCE_v1'
TREE = load_tree()  # Immutable frozen bytes are verified before every run/resume.


def proposal(symbol, tf, branch, side, bar, primitive, anchor):
    raw_id = sha256(compact([symbol, tf, branch, side, bar.end, primitive, anchor]).encode()).hexdigest()
    return {'candidate_id': raw_id, 'symbol': symbol, 'setup_tf': tf, 'branch': branch,
            'direction': side, 'decision_at': bar.end, 'event': 'CLOSE',
            'primitive': primitive, 'anchor': anchor, 'bar': bar.observed(tf),
            'raw_only': True, 'adapter_version': VERSION,
            'source_validated': False, 'trade_entry_allowed': False}


def enumerate_series(symbol, tf, bars):
    """Necessary observable proposals, NOT exhaustive discretionary setup detection.

    Last confirmed strict three-bar highs/lows are RAW reference levels only.
    Raid/reclaim proposes SFP; raid/full-range engulf proposes OB and STB/BTS;
    first later body-cross of a provisional engulf zone proposes Breaker;
    deviation/reclaim of a provisional last-swing bracket proposes both Range
    paths. Externality, impulse, trend, range endpoints, reaction/confirmation and
    source validity remain unlabelled. No percentage/ATR/tolerance cutoffs.
    """
    high, low = None, None
    long_zones, short_zones = [], []
    for i, bar in enumerate(bars):
        scored = START <= bar.start and bar.end <= END
        # Zones born at a prior completed bar; never use current future formation.
        broken = []
        while long_zones and long_zones[0][0] < -bar.close:
            _, zone_id = heapq.heappop(long_zones)
            broken.append(('SHORT', zone_id))
        while short_zones and short_zones[0][0] < bar.close:
            _, zone_id = heapq.heappop(short_zones)
            broken.append(('LONG', zone_id))
        if scored:
            for side, zid in broken:
                yield proposal(symbol, tf, 'BREAKER', side, bar, 'PROVISIONAL_ZONE_BODY_CROSS', zid)
        for side, ref in [('LONG', low), ('SHORT', high)]:
            if ref is None:
                continue
            level, ref_time = ref
            reclaim = bar.low < level < bar.close if side == 'LONG' else bar.high > level > bar.close
            if scored and reclaim:
                yield proposal(symbol, tf, 'SFP', side, bar, 'CONFIRMED_SWING_WICK_RAID_RECLAIM', ref_time)
            if i:
                previous = bars[i - 1]
                raid = previous.low < level if side == 'LONG' else previous.high > level
                engulf = bar.low <= previous.low and bar.high >= previous.high
                body_direction = bar.close > bar.open if side == 'LONG' else bar.close < bar.open
                opposite = previous.close < previous.open if side == 'LONG' else previous.close > previous.open
                if ref_time <= previous.start and raid and engulf and body_direction and opposite:
                    zid = f'{symbol}/{tf}/PROVISIONAL_OB/{side}/{previous.start}/{bar.end}'
                    if side == 'LONG':
                        heapq.heappush(long_zones, (-previous.low, zid))
                    else:
                        heapq.heappush(short_zones, (previous.high, zid))
                    if scored:
                        for branch in ('OB_CONSERVATIVE', 'STB_BTS'):
                            yield proposal(symbol, tf, branch, side, bar, 'RAID_FULL_RANGE_ENGULF', zid)
        if high is not None and low is not None and low[0] < high[0]:
            for side, deviation in [('LONG', bar.low < low[0] < bar.close < high[0]),
                                    ('SHORT', bar.high > high[0] > bar.close > low[0])]:
                if scored and deviation:
                    for branch in ('RANGE_CONSERVATIVE', 'RANGE_RETURN_CHOCH'):
                        yield proposal(symbol, tf, branch, side, bar, 'PROVISIONAL_SWING_BRACKET_DEVIATION_RECLAIM',
                                       [low[1], high[1]])
        # Confirm centre only after this right neighbour CLOSE. Future mutation
        # cannot change a reference already known before another pattern OPEN.
        if i >= 2:
            left, center = bars[i - 2], bars[i - 1]
            if center.high > left.high and center.high > bar.high:
                high = (center.high, bar.end)
            if center.low < left.low and center.low < bar.low:
                low = (center.low, bar.end)


def all_proposals(data):
    streams = [enumerate_series(symbol, tf, bars) for symbol, frames in data.items() for tf, bars in frames.items()]
    return heapq.merge(*streams, key=lambda r: (r['decision_at'], r['symbol'], r['setup_tf']))


def evidence_case(raw, catalog, mode='BACKTEST'):
    """Missing annotations remain missing; baseline engine fields never become proof."""
    record = catalog.get(raw['candidate_id'])
    if record is not None:
        raise ValueError('Current preregistration locks an empty historical annotation catalog; no new labels permitted')
    return {'branch': raw['branch'], 'symbol': raw['symbol'], 'direction': raw['direction'],
            'setup_tf': raw['setup_tf'], 'trigger_tf': 15, 'decision_at': raw['decision_at'],
            'event': raw['event'], 'mode': mode, 'instrument_metadata': None, 'tick_size': None,
            'facts': {}, 'liquidity': [], 'entry_poi': None, 'stop_anchor': None,
            'identity_evidence': {}, 'trade_entry_allowed': False}


def inspect_proposal(raw, catalog=None, mode='BACKTEST'):
    case = evidence_case(raw, catalog or {}, mode)
    result = evaluate(case, TREE)
    tree = TREE
    predicates = [n for n in tree['source_nodes'] if n['branch_id'] == raw['branch']]
    missing = ['CAUSAL_PUBLIC_TICK_METADATA', 'MEANINGFUL_LIQUIDITY_CLASSIFICATION',
               'UNIQUE_SOURCE_STOP_GEOMETRY', 'SOURCE_ENTRY_POI', 'CONTEXTUAL_FTA_INVENTORY',
               'CANONICAL_PHYSICAL_IDENTITY', 'FIRST_TEST_EVIDENCE']
    missing.extend(n['predicate'] for n in predicates if n['predicate'] not in
                   ('sfp_geometry', 'sfp_next_open', 'sfp_tf', 'conservative_tf'))
    if raw['branch'] == 'OB_CONSERVATIVE':
        missing.extend(['SMOOTH_APPROACH', 'REACTION_M15_BOS_NEW_POI'])
    elif raw['branch'] == 'BREAKER':
        missing.extend(['WHOLE_IMPULSE', 'BRANCH_CONFIRMATION', 'STRUCTURAL_ENDPOINTS'])
    elif raw['branch'].startswith('RANGE'):
        missing.extend(['RANGE_CLARITY', 'STRUCTURAL_ENDPOINTS', 'RECLAIM_RETURN_RETEST_CONFIRMATION'])
    elif raw['branch'] == 'SFP':
        missing.extend(['EXTERNAL_STRUCTURAL_LIQUIDITY', 'COMPLETED_SFP_AND_M15_BOS_SOURCE_ENTRY'])
    parallel = ['MISSING_QUALITATIVE_EVIDENCE', 'WAIT_UNRESOLVED_LIQUIDITY_CONTEXT', 'WAIT_UNRESOLVED_STOP_GEOMETRY']
    if raw['branch'] in ('SFP', 'OB_CONSERVATIVE') and raw['setup_tf'] == 15:
        parallel.append('WAIT_NO_AVAILABLE_LOWER_TF')
    return {'candidate_id': raw['candidate_id'], 'symbol': raw['symbol'], 'branch': raw['branch'],
            'direction': raw['direction'], 'setup_tf': raw['setup_tf'], 'decision_at': raw['decision_at'],
            'status': result['status'], 'SOURCE_STRATEGY_DECISION': result['SOURCE_STRATEGY_DECISION'],
            'evidence_complete': False, 'source_pass': False, 'source_result': result,
            'missing_evidence': sorted(set(missing)), 'parallel_blockers': sorted(set(parallel)),
            'rule_trace': [{'rule_id': n['rule_id'], 'predicate': n['predicate'],
                            'state': 'NOT_EVALUATED_AFTER_EARLIER_FROZEN_WAIT'} for n in predicates],
            'interpretation': 'Annotation absent does not imply setup absent; raw proposal is not a validated trade',
            'trade_entry_allowed': False}


BASELINE_BRANCH_MAP = {
    'OB_DIRECT_FIRST_TEST': 'OB_DIRECT', 'OB_DIRECT_INSIDE': 'OB_DIRECT',
    'OB_CONSERVATIVE_BOS_POI': 'OB_CONSERVATIVE', 'SFP_BOS_POI': 'SFP',
    'BREAKER_CONSERVATIVE_STOP': 'BREAKER', 'STB_BTS_HALF': 'STB_BTS',
    'STB_BTS_EDGE': 'STB_BTS', 'RANGE_AGGRESSIVE_EXTERNAL_POI': 'RANGE_AGGRESSIVE',
    'DEMAND_SUPPLY': 'DEMAND_SUPPLY_POI',
}


def baseline_probe(signal):
    """Secondary exact legacy event projection; no legacy admission/labels reused."""
    from original_v1_1_financial_data import stamp
    branch = BASELINE_BRANCH_MAP.get(signal['setup_type'])
    if branch is None:
        raise ValueError('Unregistered legacy branch mapping')
    raw = {'candidate_id': signal['signal_id'], 'branch': branch, 'symbol': signal['symbol'],
           'direction': signal['direction'], 'setup_tf': signal['evidence']['actual_setup_tf'],
           'decision_at': stamp(signal['known_at']), 'event': 'CLOSE'}
    result = evaluate(evidence_case(raw, {}), TREE)
    return {'signal_id': signal['signal_id'], 'symbol': signal['symbol'], 'legacy_style': signal['setup_type'],
            'profile_branch': branch, 'decision_at': raw['decision_at'],
            'v1_1_decision': result['SOURCE_STRATEGY_DECISION'], 'v1_1_reason': result['status'],
            'exact_fill_plan_matched': False, 'trade_entry_allowed': False}
