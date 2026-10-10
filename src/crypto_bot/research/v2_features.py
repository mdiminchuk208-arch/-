"""Pure READY-time features. Deliberately accepts no trade outcome or fill."""
from __future__ import annotations

import csv
import math
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from crypto_bot.research.v2_common import Row, canonical, seconds

ZONE = ZoneInfo('Asia/Yekaterinburg')
CORE_A = 'BREAKER_CONSERVATIVE_STOP'
CORE_B = 'RANGE_AGGRESSIVE_EXTERNAL_POI'
CORE_C = 'SFP_BOS_POI'


class NativeSeries:
    def __init__(self, rows: list[Row], tf: int):
        self.rows = rows
        self.tf = tf
        self.times = [r['close_time'] for r in rows]
        self.atrs: list[float | None] = []
        seed: list[float] = []
        previous = rows[0]['open'] if rows else 0
        atr: float | None = None
        for r in rows:
            tr = max(r['high']-r['low'], abs(r['high']-previous), abs(r['low']-previous))
            seed.append(tr)
            if len(seed) == 14:
                atr = math.fsum(seed)/14
            elif len(seed) > 14 and atr is not None:
                atr = (13*atr + tr)/14
            self.atrs.append(atr)
            previous = r['close']

    def at(self, cutoff: float) -> tuple[Row | None, float | None]:
        i = bisect_right(self.times, cutoff)-1
        return (self.rows[i], self.atrs[i]) if i >= 0 else (None, None)


def load_native(symbol: str) -> dict[int, NativeSeries]:
    result = {}
    for tf in [5, 15, 60, 240]:
        rows = []
        with Path(f'data/history/bybit/{symbol}/{tf}.csv').open() as f:
            for r in csv.DictReader(f):
                assert r['is_closed'] == '1'
                rows.append({'close_time': int(r['open_time_ms'])/1000+tf*60,
                             **{k: float(r[k]) for k in ['open', 'high', 'low', 'close']}})
        result[tf] = NativeSeries(rows, tf)
    return result


def known_audit(value: Any, cutoff: float, prefix: str = '') -> list[str]:
    errors = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ('known_at', 'formed_at', 'first_test', 'last_test', 'last_native_test_at',
                     'full_absorption_at', 'source_break_known_at') and isinstance(v, str) and seconds(v) > cutoff:
                errors.append(prefix+'.'+k)
            errors.extend(known_audit(v, cutoff, prefix+'.'+k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            errors.extend(known_audit(v, cutoff, f'{prefix}[{i}]'))
    return errors


class FeatureContext:
    def __init__(self, native: dict[int, NativeSeries], variants: list[Row],
                 flows: list[Row], ranges: list[Row], family: dict[str, str]):
        self.native = native
        self.family = family
        self.variants: dict[str, list[Row]] = defaultdict(list)
        for r in variants:
            self.variants[r['physical_opportunity_id']].append(r)
        self.flows: dict[int, list[Row]] = defaultdict(list)
        self.ranges: dict[tuple[int, str], list[Row]] = defaultdict(list)
        for r in flows:
            self.flows[r['tf']].append(r)
        for r in ranges:
            self.ranges[(r['tf'], r['direction'])].append(r)
        for records in [*self.flows.values(), *self.ranges.values()]:
            records.sort(key=lambda r: seconds(r['known_at']))
        self.flow_times = {k: [seconds(r['known_at']) for r in v] for k, v in self.flows.items()}
        self.range_times = {k: [seconds(r['known_at']) for r in v] for k, v in self.ranges.items()}

    def macro(self, tf: int, cutoff: float) -> tuple[Row | None, Row | None]:
        values = self.flows.get(tf, [])
        last = bisect_right(self.flow_times.get(tf, []), cutoff)
        structure = next((r.get('structure') for r in reversed(values[:last])
                          if r.get('structure') and seconds(r['structure']['known_at']) <= cutoff), None)
        active = next((r for r in reversed(values[:last]) if not r.get('invalidated_at')
                       or seconds(r['invalidated_at']) > cutoff), None)
        return active, structure

    def range_context(self, tf: int, direction: str, cutoff: float) -> Row | None:
        key = (tf, direction)
        i = bisect_right(self.range_times.get(key, []), cutoff)-1
        if i < 0:
            return None
        r = self.ranges[key][i]
        return r if cutoff-seconds(r['known_at']) <= 4*tf*60 else None


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    return numerator/denominator if numerator is not None and denominator else None


def age(cutoff: float, item: Row | None, field: str = 'known_at') -> float | None:
    return cutoff-seconds(item[field]) if item and item.get(field) else None


def features(signal: Row, ctx: FeatureContext, policy: Row) -> Row:
    """Outcome-independent extraction; signal is original immutable READY snapshot."""
    cutoff = seconds(signal['known_at'])
    e = signal['evidence']; q = e['ltf_poi']; p = e['htf_poi']; pd = e['premium_discount']
    assert not known_audit(e, cutoff), known_audit(e, cutoff)
    tf = e['entry_zone_tf']; s = 1 if signal['direction'] == 'LONG' else -1
    entry, stop = signal['entry'], signal['stop']
    slip, fee = policy['slippage_fraction'], policy['fee_rate']
    planned_risk = policy['case_reference_equity']*policy['risk_fraction']
    entry_fill = entry*(1+s*slip); stop_fill = stop*(1-s*slip)
    unit_risk = s*(entry_fill-stop_fill)+fee*(entry_fill+stop_fill)
    qty = planned_risk/unit_risk
    expected_fee = qty*fee*(entry_fill+math.fsum(f*t*(1-s*slip)
                          for f, t in zip(signal['fractions'], signal['targets'], strict=True)))
    expected_slip = qty*(abs(entry_fill-entry)+math.fsum(f*abs(t*(1-s*slip)-t)
                           for f, t in zip(signal['fractions'], signal['targets'], strict=True)))
    gross_target = qty*math.fsum(f*s*(t-entry) for f, t in
                                zip(signal['fractions'], signal['targets'], strict=True))
    friction_r = (expected_fee+expected_slip)/planned_risk
    gross_r = gross_target/planned_risk
    bar, atr = ctx.native[tf].at(cutoff)
    _, htf_atr = ctx.native[signal['htf']].at(cutoff)
    macro, htf_structure = ctx.macro(signal['htf'], cutoff)
    recent_range = ctx.range_context(signal['htf'], signal['direction'], cutoff)
    pid = e['physical_opportunity_id']
    witnesses = sorted([r for r in ctx.variants[pid] if seconds(r['known_at']) <= cutoff],
                       key=lambda r: (r['known_at'], r['signal_id']))
    paths = sorted({r['path_id'] for r in witnesses})
    families = sorted({ctx.family[path] for path in paths})
    # Quote/stop variants inside OB and conservative/aggressive Breaker share one family.
    independent = sorted({'OB' if f.startswith('OB_') else f for f in families})
    independent = sorted(set(independent))
    sweep = e.get('liquidity_sweep') or {}
    roles = [r for r in e.get('liquidity_roles', []) if seconds(r['known_at']) <= cutoff]
    pools = set(sweep.get('liquidity_ids', []))
    raid_tf = (signal['htf'] if sweep and (sweep == p.get('raid') or
               sweep == (p.get('external_poi') or {}).get('raid')) else
               tf if sweep == q.get('raid') else None)
    swept_roles = [r for r in roles if r['pool_id'] in pools and r['timeframe'] == raid_tf]
    bos = e.get('confirmations', {}).get('bos') or q.get('structural_proof')
    if bos and 'BOS' not in bos['kind']:
        bos = None
    proof = q.get('structural_proof') or e.get('structural_thesis')
    bos_bar, _ = ctx.native[tf].at(seconds(bos['known_at'])) if bos else (None, None)
    displacement = abs(bos_bar['close']-bos_bar['open']) if bos_bar else None
    sweep_size = abs(sweep['extreme']-sweep['price']) if sweep else None
    pd_mid = (pd['high']+pd['low'])/2
    local_age = age(cutoff, q); proof_age = age(cutoff, proof)
    destination = (macro or {}).get('destination_poi')
    destination_price = (destination['low'] if s == 1 else destination['high']) if destination else None
    flow = e.get('order_flow') or {}
    core_a, core_b, core_c = CORE_A in paths, CORE_B in paths, CORE_C in paths
    fresh = q['test_count'] == 0 and (not q.get('first_test') or seconds(q['first_test']) >= cutoff)
    strong_range = 'RANGE' in independent or recent_range is not None
    stamp = datetime.fromtimestamp(cutoff, ZONE)
    width = q['high']-q['low']; sl_distance = s*(entry-stop)
    fta = e.get('fta') or {}
    row: Row = {
        'physical_opportunity_id': pid, 'signal_id': signal['signal_id'], 'path_id': e['path_id'],
        'setup_family': ctx.family[e['path_id']], 'symbol': signal['symbol'], 'direction': signal['direction'],
        'mapping': f"{signal['htf']}/{signal['ltf']}", 'HTF': signal['htf'], 'LTF': signal['ltf'],
        'entry_zone_tf': tf, 'READY': signal['known_at'], 'feature_cutoff': signal['known_at'],
        'htf_structure_direction': htf_structure.get('direction') if htf_structure else None,
        'htf_structure_kind': htf_structure.get('kind') if htf_structure else None,
        'htf_structure_known_at': htf_structure.get('known_at') if htf_structure else None,
        'htf_structure_provenance': 'LAST_KNOWN_FLOW_HISTORY_STRUCTURE',
        'htf_flow_direction': macro.get('direction') if macro else None,
        'htf_flow_classification': macro.get('classification') if macro else None,
        'htf_flow_known_at': macro.get('known_at') if macro else None,
        'macro_flow_aligned': int(macro['direction'] == signal['direction']) if macro else None,
        'signal_flow_direction': flow.get('direction'), 'signal_flow_classification': flow.get('classification'),
        'global_POI_kind': p['kind'], 'global_POI_age_seconds': age(cutoff, p),
        'destination_POI_id': destination.get('zone_id') if destination else None,
        'destination_POI_kind': destination.get('kind') if destination else None,
        'destination_distance': s*(destination_price-entry) if destination_price else None,
        'destination_distance_R': ratio(s*(destination_price-entry), sl_distance) if destination_price else None,
        'liquidity_raid_present': int(bool(sweep)), 'SFP': int(sweep.get('sfp', False)),
        'liquidity_swept_count': len(pools), 'external_swept_count': sum(r['classification']=='EXTERNAL' for r in swept_roles),
        'internal_swept_count': sum(r['classification']=='INTERNAL' for r in swept_roles),
        'swept_pool_role_unmatched_count': len(pools-{r['pool_id'] for r in swept_roles}),
        'sweep_size': sweep_size, 'sweep_ATR': ratio(sweep_size, atr),
        'sweep_range': ratio(sweep_size, p['high']-p['low']),
        'adverse_liquidity_count': sum(r['role']=='AGAINST_SETUP' for r in roles),
        'EQH_count': sum(r['origin']=='EQH' for r in roles), 'EQL_count': sum(r['origin']=='EQL' for r in roles),
        'HTF_POI_kind': p['kind'], 'entry_POI_kind': q['kind'], 'freshness': int(fresh),
        'first_test': int(fresh), 'test_count': q['test_count'], 'zone_age_seconds': local_age,
        'zone_age_bars': ratio(local_age, tf*60), 'formation_age_seconds': age(cutoff, q, 'formed_at'),
        'POI_width': width, 'POI_width_pct': width/entry, 'POI_width_SL': ratio(width, sl_distance),
        'native_touch': int(q.get('native_touch_clock', False)),
        'true_external_POI': int(bool(p.get('external_poi')) and (entry<p['low'] if s==1 else entry>p['high'])),
        'manipulation_alias': int('MANIPULATION' in q.get('aliases', [])),
        **{f'entry_is_{k}': int(q['kind'] in kinds) for k, kinds in {
            'STB_BTS': ['STB', 'BTS'], 'OB': ['ORDER_BLOCK'], 'Breaker': ['BREAKER'],
            'Demand_Supply': ['DEMAND', 'SUPPLY'], 'FVG': ['FVG'], 'Range': ['RANGE_POI']}.items()},
        'structural_proof_kind': proof.get('kind') if proof else None, 'BOS_present': int(bool(bos)),
        'CONF_present': int('CONF' in (proof or {}).get('kind', '')),
        'protected_level': proof.get('protected') if proof else None,
        'displacement_size': displacement, 'displacement_ATR': ratio(displacement, atr),
        'raid_to_BOS_seconds': seconds(bos['known_at'])-seconds(sweep['known_at']) if bos and sweep else None,
        'BOS_to_POI_seconds': seconds(q['known_at'])-seconds(bos['known_at']) if bos else None,
        'POI_to_READY_seconds': local_age, 'structure_age_bars': ratio(proof_age, tf*60),
        'structural_confirmation_count': len(flow.get('sequence', {}).get('structural_keys', []))+int(bool(bos)),
        'PD_allowed': int(pd['allowed']), 'retracement': pd['retracement'],
        'OTE': int(pd['ote_confluence']), 'EQ_relation': 'BELOW' if entry<pd_mid else 'ABOVE' if entry>pd_mid else 'AT',
        'PD_position': ratio(entry-pd['low'], pd['high']-pd['low']),
        'SFP_range_position': ratio(entry-p['low'], p['high']-p['low']) if sweep.get('sfp') else None,
        'entry_reference': entry, 'entry_after_slippage': entry_fill, 'original_SL': stop,
        'SL_distance': sl_distance, 'SL_distance_pct': sl_distance/entry, 'SL_ATR': ratio(sl_distance, atr),
        'native_ATR': atr, 'native_HTF_ATR': htf_atr, 'ATR_known_at': bar['close_time'] if bar else None,
        'target_price': signal['targets'][0], 'targets': signal['targets'], 'target_fractions': signal['fractions'],
        'FTA_distance': s*(signal['targets'][0]-entry), 'FTA_kind': fta.get('kind'),
        'target_distance_pct': s*(signal['targets'][0]-entry)/entry,
        'gross_target_R': gross_r, 'expected_target_R': gross_r-friction_r,
        'target_SL_ratio': ratio(math.fsum(f*s*(t-entry) for f,t in
                              zip(signal['fractions'], signal['targets'], strict=True)), sl_distance),
        'planned_risk': planned_risk, 'expected_quantity': qty, 'expected_fee': expected_fee,
        'expected_slippage': expected_slip, 'expected_total_friction': expected_fee+expected_slip,
        'friction_R': friction_r, 'net_target_R': gross_r-friction_r,
        'hour': stamp.hour, 'weekday': stamp.weekday(), 'month': stamp.strftime('%Y-%m'),
        'session': 'ASIA' if 0<=datetime.fromtimestamp(cutoff, ZoneInfo('UTC')).hour<8 else
                   'EUROPE' if datetime.fromtimestamp(cutoff, ZoneInfo('UTC')).hour<16 else 'AMERICAS',
        'core_breaker': int(core_a), 'core_range': int(core_b), 'core_sfp': int(core_c),
        'physical_family_count': len(independent), 'physical_families': independent, 'available_paths': paths,
        'confluence_witnesses': [{'signal_id': r['signal_id'], 'path_id': r['path_id'],
                                 'known_at': r['known_at']} for r in witnesses],
        'breaker_sfp_confluence': int(core_a and 'SFP' in independent),
        'breaker_range_confluence': int(core_a and 'RANGE' in independent),
        'recent_range_context': int(recent_range is not None), 'strong_range_context': int(strong_range),
        'range_context_known_at': recent_range.get('known_at') if recent_range else None,
        'range_context_age_bars': ratio(age(cutoff, recent_range), signal['htf']*60),
        'range_context_width': recent_range['high']-recent_range['low'] if recent_range else None,
        'trade_entry_allowed': False}
    if recent_range:
        rb, _ = ctx.native[signal['htf']].at(seconds(recent_range['known_at']))
        boundary = recent_range['low'] if s==1 else recent_range['high']
        row['range_reclaim_distance_width'] = ratio(s*(rb['close']-boundary), recent_range['high']-recent_range['low']) if rb else None
        row['range_opposite_boundary_distance'] = s*((recent_range['high'] if s==1 else recent_range['low'])-entry)
    else:
        row['range_reclaim_distance_width'] = row['range_opposite_boundary_distance'] = None
    # The entire return is independent of fills, outcome, future context and private APIs.
    canonical(row)
    return row
