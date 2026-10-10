"""Outcome-free, causal source-plan and lifecycle contracts for frozen profile v1.

This consumes explicit source evidence; it is not an automatic OHLC interpretation
of qualitative geometry. Unknown evidence waits. No exchange or financial imports.
"""
from __future__ import annotations

import copy
import json
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

from original_strategy_spec_contract import available, predicate

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'docs/original_strategy_spec_v1_1'
UNIVERSE = (15, 60, 240, 1440)
ACTIVE = ('SFP', 'OB_CONSERVATIVE', 'BREAKER', 'STB_BTS',
          'RANGE_CONSERVATIVE', 'RANGE_RETURN_CHOCH')
OUTCOME_FIELDS = {'pnl', 'net_pnl', 'gross_pnl', 'winrate', 'holding_time',
                  'future_holding_time', 'profit_factor', 'future_return', 'outcome'}


def number(value):
    if isinstance(value, bool):
        raise TypeError('Boolean is not a price')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid numeric evidence') from exc
    if not result.is_finite():
        raise ValueError('Non-finite numeric evidence')
    return result


def encode(value):
    return format(value.normalize(), 'f')


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def forbid_outcomes(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in OUTCOME_FIELDS:
                raise ValueError('Future holding-time/P&L/outcome input forbidden')
            forbid_outcomes(item)
    elif isinstance(value, list):
        for item in value:
            forbid_outcomes(item)


def causal(record, case):
    return available(record, case['decision_at'], case['event'])


def fact(case, name):
    item = case.get('facts', {}).get(name)
    if not causal(item, case) or item.get('source_validated') is not True:
        return None
    return item.get('value') if type(item.get('value')) is bool else None


def zone(record, case):
    if not causal(record, case) or record.get('source_validated') is not True or not record.get('id'):
        return None
    low, high = number(record.get('low')), number(record.get('high'))
    return (low, high) if 0 < low < high else None


def sfp_valid(case, *, next_open=False):
    geometry = case.get('sfp', {})
    raid, old = geometry.get('raid'), geometry.get('old_level')
    if not causal(raid, case) or not causal(old, case):
        return None
    if old['known_at'] > raid['completed_at'] - case['setup_tf'] * 60:
        return None  # An old structural level must be known before pattern bar.
    low, high, close, level = (number(raid['low']), number(raid['high']),
                               number(raid['close']), number(old['price']))
    if not 0 < low <= close <= high:
        return False
    long = case['direction'] == 'LONG'
    formed = low < level < close if long else high > level > close
    if not next_open:
        return formed
    opening = geometry.get('next_open')
    if not available(opening, case['decision_at'], case['event'], completed=False):
        return None
    if any(k in opening for k in ('high', 'low', 'close', 'completed_at')):
        raise ValueError('next OPEN cannot contain future OHLC')
    if opening['known_at'] <= raid['completed_at']:
        raise ValueError('next OPEN must follow completed pattern')
    return formed and (number(opening['open']) > level if long else number(opening['open']) < level)


def quote(price, tick, *, up):
    return (price / tick).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR) * tick


def entry_price(case):
    bounds = zone(case.get('entry_poi'), case)
    if bounds is None:
        return None
    low, high = bounds
    tick = number(case['tick_size'])
    # STB midpoint is the selected source alternative; others use proximal edge.
    raw = (low + high) / 2 if case['branch'] == 'STB_BTS' else (
        high if case['direction'] == 'LONG' else low)
    result = quote(raw, tick, up=case['direction'] == 'SHORT')
    return result if low <= result <= high else None


def atr14(case):
    """Rolling mean of 14 TRs, including completed pattern bar, plus prior close.

    N11_ATR_SMA14 explicitly chooses SMA, not an inferred source smoothing rule.
    Every bar ends no later than pattern CLOSE. Exactly fifteen contiguous native
    bars are required so the first TR has its previous close without a seed guess.
    """
    bars = case.get('atr_bars', [])
    raid = case.get('sfp', {}).get('raid')
    if len(bars) != 15 or not causal(raid, case):
        return None
    duration = case['setup_tf'] * 60
    if not all(causal(b, case) and b.get('tf') == case['setup_tf'] for b in bars):
        return None
    if bars[-1]['completed_at'] != raid['completed_at']:
        return None
    total = Decimal(0)
    for i, bar in enumerate(bars):
        high, low, close = (number(bar[k]) for k in ('high', 'low', 'close'))
        if not 0 < low <= close <= high:
            return None
        if i:
            if bar['completed_at'] - bars[i - 1]['completed_at'] != duration:
                return None
            previous = number(bars[i - 1]['close'])
            total += max(high - low, abs(high - previous), abs(low - previous))
    if any(number(bars[-1][k]) != number(raid[k]) for k in ('high', 'low', 'close')):
        return None
    return total / 14 if total > 0 else None


def stop_price(case):
    anchor = case.get('stop_anchor')
    expected = {'OB_CONSERVATIVE': 'SOURCE_OB_EXTREME', 'BREAKER': 'RAID_IMPULSE_EXTREME',
                'SFP': 'SFP_PATTERN_EXTREME', 'STB_BTS': 'MANIPULATION_RAID_EXTREME',
                'RANGE_CONSERVATIVE': 'DEVIATION_INVALIDATION_EXTREME',
                'RANGE_RETURN_CHOCH': 'DEVIATION_INVALIDATION_EXTREME'}[case['branch']]
    if (not causal(anchor, case) or anchor.get('kind') != expected
            or anchor.get('unique') is not True or anchor.get('source_validated') is not True):
        return None
    raw = number(anchor['price'])
    tick = number(case['tick_size'])
    long = case['direction'] == 'LONG'
    if case['branch'] == 'SFP':
        raid = case.get('sfp', {}).get('raid')
        if not causal(raid, case) or raw != number(raid['low' if long else 'high']):
            return None
        atr = atr14(case)
        if atr is None:
            return None
        raw += -atr if long else atr
        return quote(raw, tick, up=not long)
    geometry = case.get('source_defining_zone')
    bounds = zone(geometry, case)
    if bounds is None or raw != bounds[0 if long else 1]:
        return None
    # Minimum representable price strictly beyond extreme; no %/ATR buffer.
    boundary = quote(raw, tick, up=not long)
    return boundary - tick if long and boundary >= raw else (
        boundary + tick if not long and boundary <= raw else boundary)


def target_plan(case, entry):
    tick = number(case['tick_size'])
    long = case['direction'] == 'LONG'
    if case['branch'].startswith('RANGE'):
        boundary = case.get('range_exit')
        if (not causal(boundary, case) or boundary.get('unique') is not True
                or boundary.get('source_validated') is not True):
            return None
        low, high = number(boundary['low']), number(boundary['high'])
        if not low < entry < high:
            return None
        raw = high if long else low
        target = quote(raw, tick, up=not long)
        if long and target >= raw:
            target -= tick
        elif not long and target <= raw:
            target += tick
        if not low < target < high:
            return None
        fta = boundary.get('source_exit_poi')
        if fta is not None:
            bounds = zone(fta, case)
            if bounds is None or fta.get('contextual') is not True or fta.get('opposing') is not True:
                return None
            fta_quote = quote(bounds[0 if long else 1], tick, up=long)
            if (not bounds[0] <= fta_quote <= bounds[1]
                    or not (fta_quote > entry if long else fta_quote < entry)):
                return None
            target = min(target, fta_quote) if long else max(target, fta_quote)
            if not low < target < high:
                return None
        selection = 'TECHNICAL_RESOLUTION_OPTIONAL_REMAINDER_DISABLED'
        ids = [boundary['id']] + ([fta['id']] if fta is not None else [])
        fractions = ['0.8', '0.2']
    else:
        candidates = []
        inventory = case.get('contextual_poi_inventory')
        if (not causal(inventory, case) or inventory.get('complete_for_known_prefix') is not True):
            return None
        for poi in case.get('contextual_pois', []):
            # POIs not yet known at decision cannot change the result.
            if type(poi.get('known_at')) is int and poi['known_at'] > case['decision_at']:
                continue
            if not causal(poi, case):
                return None
            if poi.get('opposing') is False or poi.get('contextual') is False:
                continue
            if poi.get('source_validated') is not True or poi.get('contextual') is not True or poi.get('opposing') is not True:
                return None
            bounds = zone(poi, case)
            if bounds is None:
                return None
            low, high = bounds
            # Inside an opposing zone, a profitable nearest FTA is not established.
            if low <= entry <= high:
                return None
            if (long and low > entry) or (not long and high < entry):
                raw = low if long else high
                target = quote(raw, tick, up=long)
                if low <= target <= high:
                    candidates.append((target, poi['id']))
                else:
                    return None
        if not candidates:
            return None
        target = min(p for p, _ in candidates) if long else max(p for p, _ in candidates)
        ids = sorted(i for p, i in candidates if p == target)
        selection = 'FULL_CONTEXTUAL_FTA_EXIT'
        fractions = ['1']
    if not (target > entry if long else target < entry):
        return None
    return {'kind': selection, 'price': encode(target), 'poi_ids': ids,
            'fractions_same_zone': fractions, 'total_fraction': '1', 'fixed_pre_entry': True}


def liquidity_decision(case):
    inventory = case.get('liquidity_inventory')
    if not causal(inventory, case) or inventory.get('complete_for_known_prefix') is not True:
        return 'WAIT_UNRESOLVED_LIQUIDITY_CONTEXT'
    unknown, swept = False, False
    for pool in case.get('liquidity', []):
        if type(pool.get('known_at')) is int and pool['known_at'] > case['decision_at']:
            continue
        if not causal(pool, case) or pool.get('source_validated') is not True:
            unknown = True
            continue
        role = pool.get('role')
        if role not in ('ADVERSE', 'TARGET_OR_FUEL', 'NEUTRAL'):
            unknown = True
        elif role == 'ADVERSE':
            sweep = pool.get('sweep')
            if not causal(sweep, case):
                return 'WAIT_SWEEP'
            swept = True
            refreshed = case.get('post_sweep_revalidation')
            if (not causal(refreshed, case) or refreshed.get('value') is not True
                    or refreshed.get('source_validated') is not True
                    or refreshed['known_at'] < sweep['known_at']):
                return 'WAIT_POST_SWEEP_REVALIDATION'
    if unknown:
        return 'WAIT_UNRESOLVED_LIQUIDITY_CONTEXT'
    return 'REVALIDATE_SOURCE' if swept else 'PASS'


def identity(case):
    names = ('context', 'formation', 'confirmation', 'poi')
    records = case.get('identity_evidence', {})
    if not case.get('symbol') or not all(causal(records.get(k), case) and records[k].get('id') for k in names):
        return None
    if not records['formation']['known_at'] <= records['confirmation']['known_at'] <= case['decision_at']:
        return None
    if (records['poi']['id'] != case.get('idea_poi_id')
            or case['entry_poi'].get('parent_poi_id') != records['poi']['id']):
        return None
    physical = digest([case['symbol'], records['context']['id'], records['poi']['id']])
    setup = digest([physical, case['direction'], records['formation']['id'], records['confirmation']['id']])
    ready_at = case['decision_at']  # First complete validation event, not early formation time.
    return {'physical_id': physical, 'setup_id': setup, 'ready_at': ready_at,
            'zone_id': digest([case['symbol'], records['context']['id'], records['poi']['id']]),
            'formation_key': digest([case['symbol'], records['context']['id'], records['formation']['id']])}


def load_tree():
    return json.loads((SPEC / 'ORIGINAL_STRATEGY_EXECUTABLE_DECISION_TREE_v1.json').read_text())


def evaluate(case, tree=None):
    """Produce an offline source ALLOW plan or explicit wait/reject. Never an order."""
    forbid_outcomes(case)
    if (type(case.get('decision_at')) is not int or case.get('event') not in ('OPEN', 'CLOSE')
            or case.get('mode') not in ('BACKTEST', 'SHADOW') or case.get('direction') not in ('LONG', 'SHORT')):
        raise ValueError('Explicit causal BACKTEST/SHADOW event required')
    tree = tree or load_tree()
    registry = json.loads((SPEC / 'original_strategy_rule_registry_v1_1.json').read_text())
    categories = {r['rule_id']: r['category'] for r in registry['rules']}
    result = {'status': 'WAIT', 'SOURCE_STRATEGY_DECISION': 'WAIT', 'trade_entry_allowed': False,
              'source_trace': [], 'resolution_ids': [f'U{i}' for i in range(1, 7)]}

    def end(status, *, allow=False):
        result['status'] = status
        result['SOURCE_STRATEGY_DECISION'] = 'ALLOW' if allow else ('REJECT' if status.startswith('REJECT') else 'WAIT')
        return result

    branch = case.get('branch')
    if branch not in tree['active_branches']:
        return end('REJECT_INACTIVE_PROFILE_BRANCH')
    if case.get('setup_tf') not in UNIVERSE:
        return end('REJECT_OUTSIDE_EXECUTABLE_UNIVERSE')
    metadata = case.get('instrument_metadata')
    if not causal(metadata, case) or metadata.get('tick_size') != case.get('tick_size'):
        return end('WAIT_UNRESOLVED_INSTRUMENT_METADATA')
    if number(case.get('tick_size')) <= 0:
        raise ValueError('Positive instrument tick_size required')
    if (branch in ('OB_CONSERVATIVE', 'SFP')
            and (case.get('trigger_tf') != 15 or case['trigger_tf'] >= case['setup_tf'])):
        return end('WAIT_NO_AVAILABLE_LOWER_TF')
    # Pure source predicates are separate from profile-selected path/normalization.
    for node in tree['source_nodes']:
        if node['branch_id'] != branch:
            continue
        if categories.get(node['rule_id']) != 'SOURCE_RULE':
            raise ValueError('Non-source rule injected into source predicate')
        if node['predicate'] in ('sfp_geometry', 'sfp_next_open'):
            value = sfp_valid(case, next_open=node['predicate'] == 'sfp_next_open')
        elif node['predicate'] in ('sfp_tf', 'conservative_tf'):
            value = predicate(case, node['predicate'])
        else:
            value = fact(case, node['predicate'])
        result['source_trace'].append({'rule_id': node['rule_id'], 'predicate': node['predicate'],
                                       'value': value, 'known_at': case['decision_at']})
        if value is not True:
            return end('WAIT_UNRESOLVED_SOURCE_GEOMETRY' if value is None else 'REJECT_SOURCE_CONDITION')
    if branch == 'SFP' and fact(case, 'ltf_bos_source_entry') is not True:
        return end('WAIT_SFP_LOWER_BOS_ENTRY_SEARCH')
    if branch.startswith('RANGE') and fact(case, 'range_reclaim_retest') is not True:
        return end('WAIT_RANGE_RECLAIM_RETEST')
    if branch == 'BREAKER' and fact(case, 'breaker_confirmation') is not True:
        return end('WAIT_BREAKER_CONFIRMATION')
    reaction = case.get('reaction')
    bos = case.get('bos')
    if branch in ('OB_CONSERVATIVE', 'SFP'):
        if (not causal(reaction, case) or not causal(bos, case) or bos.get('tf') != 15
                or not reaction['known_at'] <= bos['known_at'] <= case['decision_at']):
            return end('WAIT_CAUSAL_REACTION_BOS')
        if branch == 'SFP' and reaction['known_at'] < case['sfp']['next_open']['known_at']:
            return end('WAIT_CAUSAL_REACTION_BOS')
        formation = case.get('entry_poi', {}).get('formation_known_at')
        if (type(formation) is not int or formation < bos['known_at']
                or formation > case.get('entry_poi', {}).get('known_at', -1)):
            return end('WAIT_NEW_POI_AFTER_BOS')
    liquid = liquidity_decision(case)
    if liquid not in ('PASS', 'REVALIDATE_SOURCE'):
        return end(liquid)
    entry = entry_price(case)
    if entry is None:
        return end('WAIT_UNRESOLVED_ENTRY_GEOMETRY')
    stop = stop_price(case)
    if stop is None:
        return end('WAIT_UNRESOLVED_STOP_GEOMETRY')
    if not 0 < stop or not (stop < entry if case['direction'] == 'LONG' else stop > entry):
        return end('REJECT_STOP_GEOMETRY')
    clearance = case.get('facts', {}).get('sl_off_liquidity', {})
    if clearance.get('checked_price') != encode(stop):
        return end('WAIT_UNRESOLVED_STOP_LIQUIDITY')
    target = target_plan(case, entry)
    if target is None:
        return end('WAIT_UNRESOLVED_CONTEXTUAL_FTA')
    ids = identity(case)
    if ids is None:
        return end('WAIT_UNRESOLVED_SETUP_IDENTITY')
    zone_use = case.get('zone_first_test')
    if not causal(zone_use, case) or zone_use.get('value') is not True:
        return end('WAIT_FIRST_TEST_ONLY')
    result.update(identity=ids, plan={'branch': branch, 'direction': case['direction'],
        'entry': encode(entry), 'order_type': 'LIMIT_AFTER_KNOWN_CONFIRMATION',
        'stop': encode(stop), 'stop_policy': 'FIXED_INITIAL_PROTECTIVE_STOP',
        'target': target, 'known_at': case['decision_at'], 'pattern_tf': case['setup_tf'],
        'sfp_extreme': encode(number(case['stop_anchor']['price'])) if branch == 'SFP' else None,
        'project_overlays_applied': False})
    return end('SOURCE_ALLOW_PLAN_ONLY', allow=True)


def select_ideas(cases, state=None):
    """First complete causal idea; identical plans confluence; conflicts wait.

    Call with the whole same-event candidate set. No retrospectively cancelled
    fills: conflicts arriving later freeze new admission, retaining prior state.
    """
    state = copy.deepcopy(state or {'active': {}, 'used_zones': [], 'used_setups': [], 'used_formations': []})
    if cases:
        timestamps = {c.get('decision_at') for c in cases}
        events = {c.get('event') for c in cases}
        if len(timestamps) != 1 or len(events) != 1:
            raise ValueError('Complete same-event candidate batch required')
        now = cases[0]['decision_at']
        if type(now) is not int or now < state.get('last_event_at', now):
            raise ValueError('Physical-idea state cannot run backward in time')
        state['last_event_at'] = now
    decisions = [evaluate(c) for c in cases]
    groups = {}
    for decision in decisions:
        if decision['SOURCE_STRATEGY_DECISION'] == 'ALLOW':
            groups.setdefault(decision['identity']['physical_id'], []).append(decision)
    chosen = []
    for key in sorted(groups):
        batch = groups[key]
        existing = state['active'].get(key)

        def material(d):
            p = d['plan']
            # Entry/stop/target and manual invalidation; branch name is provenance.
            return [p['direction'], p['entry'], p['stop'], p['target']['price'],
                    p['sfp_extreme'], p['pattern_tf'] if p['sfp_extreme'] else None]

        comparisons = batch + ([existing] if existing else [])
        if len({digest(material(d)) for d in comparisons}) > 1:
            chosen.append({'status': 'WAIT_BRANCH_CONFLICT', 'physical_id': key,
                           'trade_entry_allowed': False})
            continue
        if existing:
            existing['confluence'] = sorted(set(existing['confluence']) | {d['plan']['branch'] for d in batch})
            chosen.append({'status': 'CONFLUENCE_ONLY', 'physical_id': key, 'trade_entry_allowed': False})
            continue
        # Same-event identical plans cannot have an outcome-based winner.
        first = min(batch, key=lambda d: (d['identity']['ready_at'], d['plan']['known_at'], d['plan']['branch']))
        ids = first['identity']
        if (ids['zone_id'] in state['used_zones'] or ids['setup_id'] in state['used_setups']
                or ids['formation_key'] in state['used_formations']):
            chosen.append({'status': 'WAIT_FIRST_TEST_ONLY', 'physical_id': key, 'trade_entry_allowed': False})
            continue
        first['confluence'] = sorted({d['plan']['branch'] for d in batch})
        first['physical_idea_selected'] = True
        state['active'][key] = copy.deepcopy(first)
        chosen.append(first)
    return {'decisions': decisions, 'selected': chosen, 'state': state, 'trade_entry_allowed': False}


def retire_idea(state, physical_id, *, zone_used):
    result = copy.deepcopy(state)
    idea = result['active'].pop(physical_id)
    result['used_setups'] = sorted(set(result['used_setups']) | {idea['identity']['setup_id']})
    result['used_formations'] = sorted(set(result['used_formations']) | {idea['identity']['formation_key']})
    if zone_used:
        result['used_zones'] = sorted(set(result['used_zones']) | {idea['identity']['zone_id']})
    return result


def new_position(source_result):
    if (source_result.get('SOURCE_STRATEGY_DECISION') != 'ALLOW'
            or source_result.get('physical_idea_selected') is not True):
        raise ValueError('Source ALLOW and physical-idea selection required')
    return {'state': 'PENDING_LIMIT', 'plan': copy.deepcopy(source_result['plan']),
            'last_event_at': source_result['plan']['known_at'], 'trade_entry_allowed': False}


def lifecycle(position, event):
    """Ordered public-price evidence only. Bar simultaneous touch waits, no P&L."""
    forbid_outcomes(event)
    result = copy.deepcopy(position)
    plan = result['plan']
    now = event.get('known_at')
    if type(now) is not int or now <= result['last_event_at'] or not event.get('evidence'):
        raise ValueError('Strictly later causal lifecycle event required')
    if event.get('requested_stop') not in (None, plan['stop']):
        raise ValueError('FIXED_INITIAL_PROTECTIVE_STOP: no BE/stop move')
    if result['state'] in ('CLOSED', 'CANCELLED', 'WAIT_INTRABAR_ORDER'):
        raise ValueError('Terminal position cannot be updated without new evidence resolution')
    result['last_event_at'] = now
    long = plan['direction'] == 'LONG'
    stop, target, entry = (number(plan[k] if k != 'target' else plan[k]['price']) for k in ('stop', 'target', 'entry'))
    if event.get('kind') == 'QUOTE':
        if any(k in event for k in ('high', 'low', 'close', 'completed_at')):
            raise ValueError('QUOTE event cannot contain future OHLC')
        price = number(event['price'])
        # Pending entry cannot assume fills if invalidation or target was already reached.
        if result['state'] == 'PENDING_LIMIT':
            if (price <= stop or price >= target) if long else (price >= stop or price <= target):
                result.update(state='CANCELLED', reason='PRE_FILL_PLAN_INVALIDATED')
            elif (price <= entry if long else price >= entry):
                result.update(state='OPEN', filled_at=now, fill_quote=encode(price))
        elif (price <= stop if long else price >= stop):
            result.update(state='CLOSED', reason='PROTECTIVE_STOP', closed_at=now)
        elif (price >= target if long else price <= target):
            result.update(state='CLOSED', reason=plan['target']['kind'], closed_at=now, closed_fraction='1')
    elif event.get('kind') == 'BAR_CLOSE':
        if (type(event.get('completed_at')) is not int or event['completed_at'] > now
                or event['completed_at'] <= position['last_event_at'] or event.get('tf') != plan['pattern_tf']):
            raise ValueError('Completed pattern timeframe bar required')
        if result['state'] == 'PENDING_LIMIT':
            result.update(state='WAIT_INTRABAR_ORDER', reason='NO_FILL_FROM_UNORDERED_OHLC')
        else:
            high, low, close = (number(event[k]) for k in ('high', 'low', 'close'))
            if not low <= close <= high:
                raise ValueError('Invalid bar geometry')
            stop_hit = low <= stop if long else high >= stop
            target_hit = high >= target if long else low <= target
            if stop_hit and target_hit:
                result.update(state='WAIT_INTRABAR_ORDER', reason='NO_ASSUMED_STOP_TARGET_ORDER')
            elif stop_hit or target_hit:
                result.update(state='CLOSED', reason='PROTECTIVE_STOP' if stop_hit else plan['target']['kind'], closed_at=now)
            elif plan['sfp_extreme'] is not None:
                extreme = number(plan['sfp_extreme'])
                if close < extreme if long else close > extreme:
                    result.update(state='CLOSED', reason='SFP_PATTERN_BODY_INVALIDATION', closed_at=now)
    else:
        raise ValueError('QUOTE or BAR_CLOSE evidence required')
    if result['state'] == 'CLOSED':
        result['closed_fraction'] = '1'
    return result
