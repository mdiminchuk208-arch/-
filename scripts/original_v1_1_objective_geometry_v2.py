"""Causal price geometry. Exact primitives do not certify contextual SOURCE setups."""
from __future__ import annotations

import heapq
from bisect import bisect_right
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from original_strategy_executable_profile_v1 import digest, encode
from original_v1_1_financial_data import TFS, compact, validate_bars


def object_record(kind, symbol, tf, known_at, payload, rules, *, validated=False):
    """Identity depends on immutable causal content, never branch, labels or suffix."""
    return {'id': digest(['EVIDENCE_OBJECT_v2', kind, symbol, tf, known_at, payload]),
            'kind': kind, 'symbol': symbol, 'tf': tf, 'known_at': known_at,
            'completed_at': known_at, 'payload': payload, 'source_rule_ids': rules,
            'source_validated': validated, 'evidence': 'Exact completed-prefix geometry: ' + compact(payload)}


def source_known_at(o):
    return max(o['known_at'],o.get('source_attestation',{}).get('known_at',o['known_at']))


def source_structure(symbol, tf, swings, decision_at):
    """Explicit protected endpoints supplied by audited annotation; no swing owner guess."""
    if len(swings) != 4 or any(not s.get('source_validated') or s.get('protected_endpoint') is not True or source_known_at(s) > decision_at for s in swings):
        return None
    if [s['payload']['side'] for s in swings] not in (['LOW','HIGH','LOW','HIGH'], ['HIGH','LOW','HIGH','LOW']):
        return None
    if [s['known_at'] for s in swings] != sorted(s['known_at'] for s in swings):
        return None
    lows = [Decimal(s['payload']['price']) for s in swings if s['payload']['side'] == 'LOW']
    highs = [Decimal(s['payload']['price']) for s in swings if s['payload']['side'] == 'HIGH']
    side = 'LONG' if lows[1] > lows[0] and highs[1] > highs[0] else (
        'SHORT' if lows[1] < lows[0] and highs[1] < highs[0] else None)
    if side is None:
        return None
    return object_record('structure', symbol, tf, max(source_known_at(s) for s in swings),
                         {'swings': [s['id'] for s in swings], 'direction': side}, ['S_STRUCTURE'], validated=True)


def structure_break(structure, protected_level, bar, *, confirmation=False):
    """BOS breaks protected HL/LH; CONF uses explicitly new-structure key extreme."""
    if not structure or not structure.get('source_validated') or not protected_level.get('source_validated') or protected_level.get('protected_endpoint') is not True:
        return None
    if confirmation and structure.get('new_structure_after_BOS') is not True:
        return None
    if max(source_known_at(structure),source_known_at(protected_level)) > bar.start:
        return None
    trend = structure['payload']['direction']
    expected_side = ('HIGH' if trend == 'LONG' else 'LOW') if confirmation else ('LOW' if trend == 'LONG' else 'HIGH')
    if protected_level['payload']['side'] != expected_side:
        return None
    # Selection of the protected level and new-structure extreme must be attested.
    if protected_level['id'] not in structure['payload']['swings']:
        return None
    long = (trend == 'LONG') == confirmation
    price = Decimal(protected_level['payload']['price'])
    if not (bar.close > price if long else bar.close < price):
        return None
    return object_record('confirmation' if confirmation else 'BOS', structure['symbol'], structure['tf'], bar.end,
        {'structure_id': structure['id'], 'level_id': protected_level['id'], 'close': str(bar.close),
         'direction': 'LONG' if long else 'SHORT', 'bar_start': bar.start},
        ['S_CONF' if confirmation else 'S_BOS'], validated=True)


def dealing_geometry(origin, endpoint, *, range_selected=False):
    """No implicit endpoint selection or universal Fib requirement."""
    if not all(o.get('source_validated') for o in (origin, endpoint)):
        return None
    if origin.get('selected_source_endpoint') is not True or endpoint.get('selected_source_endpoint') is not True:
        return None
    if origin['symbol'] != endpoint['symbol'] or origin['tf'] != endpoint['tf'] or origin['known_at'] >= endpoint['known_at']:
        return None
    a, b = (Decimal(o['payload']['price']) for o in (origin, endpoint))
    if a == b:
        return None
    low, high = min(a, b), max(a, b)
    direction = 'LONG' if b > a else 'SHORT'
    retracements = [b - (b - a) * r for r in (Decimal('.705'), Decimal('.79'))]
    payload = {'origin_id': origin['id'], 'endpoint_id': endpoint['id'], 'low': encode(low),
        'high': encode(high), 'midpoint': encode((low+high)/2), 'direction': direction,
        'OTE_low': encode(min(retracements)), 'OTE_high': encode(max(retracements)),
        'discount': [encode(low), encode((low+high)/2)], 'premium': [encode((low+high)/2), encode(high)]}
    return object_record('range' if range_selected else 'impulse', origin['symbol'], origin['tf'], max(source_known_at(origin),source_known_at(endpoint)),
                         payload, ['S_PD', 'S_OTE', 'S_POOL_SCOPE'], validated=True)


def pool_scope(pool, dealing):
    if (not dealing or not dealing.get('source_validated') or source_known_at(pool) > source_known_at(dealing)
        or pool['tf']!=dealing['tf'] or pool['symbol']!=dealing['symbol']):
        return 'UNKNOWN'
    price = Decimal(pool['payload']['price'])
    return 'INTERNAL' if Decimal(dealing['payload']['low']) < price < Decimal(dealing['payload']['high']) else 'EXTERNAL'


def breaker_geometry(ob, break_bar, structure, whole_impulse):
    """No breaker promotion from an unvalidated provisional OB/body crossing."""
    if not ob.get('source_validated') or source_known_at(ob) > break_bar.start or not structure:
        return None
    if not structure.get('source_validated') or source_known_at(structure) > break_bar.end:
        return None
    if not whole_impulse or not whole_impulse.get('source_validated') or whole_impulse.get('value') is not True or whole_impulse.get('new_structure_extreme_proven') is not True:
        return None
    if (whole_impulse['known_at'] > break_bar.end or whole_impulse.get('completed_at', break_bar.end+1)>whole_impulse['known_at']
        or not {'interval_start','interval_end','low','high','evidence'}<=whole_impulse.keys()
        or not ob['known_at']<=whole_impulse['interval_start']<whole_impulse['interval_end']<=break_bar.end):
        return None
    if (not 0<Decimal(whole_impulse['low'])<=break_bar.low
        or not Decimal(whole_impulse['high'])>=break_bar.high
        or structure['payload'].get('direction')==ob['payload'].get('direction')):
        return None
    p = ob['payload']; long = p['direction'] == 'SHORT'
    if not (break_bar.close > Decimal(p['high']) if long else break_bar.close < Decimal(p['low'])):
        return None
    return object_record('breaker', ob['symbol'], ob['tf'], break_bar.end,
        {'prior_OB_id': ob['id'], 'structure_id': structure['id'], 'whole_impulse_evidence': whole_impulse['evidence'],
         'low': p['body_low'], 'high': p['body_high'], 'direction': 'LONG' if long else 'SHORT',
         'raid_impulse_low': whole_impulse['low'], 'raid_impulse_high': whole_impulse['high']},
        ['S_BREAKER_FORMATION', 'S_BREAKER_STOPS'], validated=True)


def range_deviation_geometry(dealing, bar, direction):
    """Exact conditional boundary raid/reclaim, never range-clarity inference."""
    if not dealing or not dealing.get('source_validated') or source_known_at(dealing)>bar.start:
        return None
    low,high=(Decimal(dealing['payload'][k]) for k in ('low','high'))
    reclaimed=low<bar.close<high
    raid=bar.low<low if direction=='LONG' else bar.high>high
    if not reclaimed or not raid:
        return None
    return object_record('formation',dealing['symbol'],dealing['tf'],bar.end,
        {'event':'range_deviation_reclaim','range_id':dealing['id'],'direction':direction,
         'bar_start':bar.start,'low':str(bar.low),'high':str(bar.high),'close':str(bar.close)},
        ['S_RANGE_DEVIATION'],validated=True)


def range_retest_geometry(dealing, deviation, bar, direction):
    if (not dealing or not deviation or not all(o.get('source_validated') for o in (dealing,deviation))
        or deviation['payload'].get('range_id')!=dealing['id']
        or max(source_known_at(dealing),source_known_at(deviation))>bar.start):
        return None
    low,high=(Decimal(dealing['payload'][k]) for k in ('low','high'))
    boundary=low if direction=='LONG' else high
    if not bar.low<=boundary<=bar.high or not low<bar.close<high:
        return None
    return object_record('confirmation',dealing['symbol'],dealing['tf'],bar.end,
        {'event':'range_boundary_return_retest','range_id':dealing['id'],'deviation_id':deviation['id'],
         'direction':direction,'bar_start':bar.start,'low':str(bar.low),'high':str(bar.high),'close':str(bar.close)},
        ['S_RANGE_CONSERVATIVE'],validated=True)


def refined_poi_geometry(original, new_source_poi, bos):
    """Refinement links original physical zone; no arbitrary substitute POI."""
    if not all(o and o.get('source_validated') for o in (original,new_source_poi,bos)):
        return None
    if (bos.get('tf')!=15 or new_source_poi.get('tf')!=15
        or original['symbol']!=new_source_poi['symbol'] or bos['symbol']!=original['symbol']
        or source_known_at(original)>source_known_at(bos)
        or source_known_at(new_source_poi)<source_known_at(bos)):
        return None
    p=new_source_poi['payload']; b=bos['payload']
    if not {'low','high','direction'}<=p.keys() or b.get('direction')!=p['direction']:
        return None
    return object_record('refined_POI',original['symbol'],15,source_known_at(new_source_poi),
        {'parent_poi_id':original['id'],'formation_id':new_source_poi['id'],'confirmation_id':bos['id'],
         'low':p['low'],'high':p['high'],'direction':p['direction'],
         'formation_known_at':new_source_poi['known_at']},['S_OB_CONS_TRIGGER','S_SFP_REFINE'],validated=True)



class ConsumedRegistry:
    """Only explicit first eligible test; unordered OHLC touch stays ambiguous."""
    def __init__(self):
        self.events = {}
        self.last_known_at = -1

    def test(self, poi_id, event_id, known_at, *, eligible, ordered):
        if known_at < self.last_known_at:
            raise ValueError('Consumption cannot run backward')
        self.last_known_at = known_at
        if eligible is None or not ordered:
            return {'state': 'UNKNOWN', 'reason': 'WAIT_FIRST_TEST_ONLY', 'known_at': known_at}
        if not eligible:
            return {'state': 'NOT_A_VALID_TEST', 'known_at': known_at}
        if poi_id in self.events:
            if self.events[poi_id]=={'event_id':event_id,'known_at':known_at}:
                return {'state':'FIRST_TEST','first_test_id':event_id,'known_at':known_at}
            return {'state': 'CONSUMED', 'first_test_id': self.events[poi_id]['event_id'], 'known_at': known_at}
        self.events[poi_id] = {'event_id': event_id, 'known_at': known_at}
        return {'state': 'FIRST_TEST', 'first_test_id': event_id, 'known_at': known_at}


class GeometryIndex:
    def __init__(self, symbol, tf, bars):
        validate_bars(bars, tf)
        self.symbol, self.tf, self.bars = symbol, tf, bars
        self.ends = [b.end for b in bars]
        self.by_id = {}
        self.events = defaultdict(list)
        self.references = {'HIGH': {}, 'LOW': {}}
        self.ob_alias = {}
        self.swing_events = {'HIGH': [], 'LOW': []}
        self._build()

    def add(self, kind, at, payload, rules, *, validated=False):
        obj = object_record(kind, self.symbol, self.tf, at, payload, rules, validated=validated)
        self.by_id[obj['id']] = obj
        self.events[at].append(obj['id'])
        return obj

    def _build(self):
        latest = {'HIGH': None, 'LOW': None}
        unswept = {'HIGH': [], 'LOW': []}
        for i, bar in enumerate(self.bars):
            for side in ('HIGH', 'LOW'):
                heap = unswept[side]
                while heap and ((-heap[0][0] > bar.low) if side == 'LOW' else (heap[0][0] < bar.high)):
                    _, pool_id = heapq.heappop(heap)
                    pool = self.by_id[pool_id]
                    if pool['known_at'] <= bar.start:
                        self.add('sweep', bar.end, {'pool_id': pool_id, 'bar_start': bar.start,
                            'low': str(bar.low), 'high': str(bar.high), 'close': str(bar.close)}, ['S_POOL_SCOPE'])
            # Raw-reference swings must predate this bar's OPEN.
            for direction, side in (('LONG','LOW'), ('SHORT','HIGH')):
                ref = latest[side]
                if ref is None or ref['known_at'] > bar.start:
                    continue
                level = Decimal(ref['payload']['price'])
                reclaim = bar.low < level < bar.close if direction == 'LONG' else bar.high > level > bar.close
                if reclaim:
                    self.add('SFP', bar.end, {'level_id': ref['id'], 'price': str(level), 'direction': direction,
                        'bar_start': bar.start, 'low': str(bar.low), 'high': str(bar.high), 'close': str(bar.close)}, ['S_SFP_FORMATION'])
                if i:
                    prev = self.bars[i-1]
                    raid = prev.low < level if direction == 'LONG' else prev.high > level
                    opposite = prev.close < prev.open if direction == 'LONG' else prev.close > prev.open
                    body = bar.close > bar.open if direction == 'LONG' else bar.close < bar.open
                    if ref['known_at'] <= prev.start and raid and opposite and body and bar.low <= prev.low and bar.high >= prev.high:
                        p = {'level_id': ref['id'], 'direction': direction, 'source_bar_start': prev.start,
                             'engulf_bar_start': bar.start, 'low': str(prev.low), 'high': str(prev.high),
                             'body_low': str(min(prev.open, prev.close)), 'body_high': str(max(prev.open, prev.close)),
                             'engulf_low': str(bar.low), 'engulf_high': str(bar.high)}
                        formation=self.add('formation',bar.end,{'direction':direction,'event':'raid_engulf','level_id':ref['id'],
                            'source_bar_start':prev.start,'engulf_bar_start':bar.start},['S_OB_FORMATION','S_STB_FORMATION'])
                        self.add('POI',bar.end,{'direction':direction,'low':str(prev.low),'high':str(prev.high),
                            'formation_id':formation['id']},['S_POI'])
                        ob = self.add('OB', bar.end, p, ['S_OB_FORMATION','S_OB_ZONE'])
                        self.add('STB', bar.end, p, ['S_STB_FORMATION','S_STB_ENTRY'])
                        alias = f'{self.symbol}/{self.tf}/PROVISIONAL_OB/{direction}/{prev.start}/{bar.end}'
                        self.ob_alias[alias] = ob['id']
            if i >= 2:
                a, b = self.bars[i-2:i]
                if a.high < bar.low:
                    self.add('FVG', bar.end, {'direction': 'LONG', 'low': str(a.high), 'high': str(bar.low),
                        'midpoint': encode((a.high+bar.low)/2), 'bar_starts': [a.start,b.start,bar.start]}, ['S_FVG'], validated=True)
                if a.low > bar.high:
                    self.add('FVG', bar.end, {'direction': 'SHORT', 'low': str(bar.high), 'high': str(a.low),
                        'midpoint': encode((bar.high+a.low)/2), 'bar_starts': [a.start,b.start,bar.start]}, ['S_FVG'], validated=True)
                for side, formed in [('HIGH', b.high>a.high and b.high>bar.high), ('LOW',b.low<a.low and b.low<bar.low)]:
                    if not formed:
                        continue
                    price = b.high if side == 'HIGH' else b.low
                    previous = latest[side]
                    classification = None if previous is None else (
                        ('HH' if price>Decimal(previous['payload']['price']) else 'LH' if price<Decimal(previous['payload']['price']) else 'EQH')
                        if side == 'HIGH' else ('HL' if price>Decimal(previous['payload']['price']) else 'LL' if price<Decimal(previous['payload']['price']) else 'EQL'))
                    swing = self.add('swing', bar.end, {'side': side, 'price': str(price), 'center_start': b.start,
                        'three_bar_starts': [a.start,b.start,bar.start], 'pair_classification': classification,
                        'protected_endpoint': 'UNKNOWN'}, ['S_SWING'], validated=True)
                    latest[side] = swing
                    self.references[side][bar.end] = swing['id']
                    self.swing_events[side].append((bar.end, swing['id']))
                    pool = self.add('liquidity_pool', bar.end, {'swing_id': swing['id'], 'side': side,
                        'price': str(price), 'meaningful': 'UNKNOWN', 'role': 'UNKNOWN', 'scope': 'UNKNOWN'}, ['S_POOL_SCOPE'])
                    heapq.heappush(unswept[side], ((-price if side=='LOW' else price), pool['id']))
                if latest['HIGH'] and latest['LOW'] and any(latest[k]['known_at']==bar.end for k in latest):
                    lo,hi=latest['LOW'],latest['HIGH']
                    if Decimal(lo['payload']['price'])<Decimal(hi['payload']['price']):
                        self.add('range',bar.end,{'low':lo['payload']['price'],'high':hi['payload']['price'],
                            'low_swing_id':lo['id'],'high_swing_id':hi['id'],'source_selected':False},['S_RANGE_FORMATION'])

    def event_objects(self, at, kind=None):
        return [self.by_id[k] for k in self.events.get(at, []) if kind is None or self.by_id[k]['kind']==kind]

    def prefix_objects(self, at):
        return sorted((o for o in self.by_id.values() if o['known_at']<=at), key=lambda o:(o['known_at'],o['id']))

    def bar_at(self, at):
        i = bisect_right(self.ends, at)-1
        return (i,self.bars[i]) if i>=0 else (None,None)

    def atr_bars(self, at):
        i, bar = self.bar_at(at)
        return [b.observed(self.tf) for b in self.bars[i-14:i+1]] if bar and bar.end==at and i>=14 else []

    def next_open(self, pattern_at, decision_at):
        """Conservative availability: archived OHLC exposes OPEN at that bar's CLOSE.

        No invented second delay. OPEN record has no later H/L/C; actual event
        time is retained separately. Frozen strict known_at>pattern_close holds.
        """
        i = bisect_right(self.ends,pattern_at)
        if i>=len(self.bars) or self.bars[i].start != pattern_at or self.bars[i].end>decision_at:
            return None
        b = self.bars[i]
        return {'open': str(b.open), 'known_at': b.end, 'actual_open_time': b.start,
                'evidence': 'Next native OPEN, conservatively observed at archived bar completion'}


def previous_levels(daily_bars, at):
    """Full completed UTC day/week/month only; partial first/last periods excluded."""
    completed = [b for b in daily_bars if b.end<=at]
    if not completed:
        return []
    instant = datetime.fromtimestamp(at, UTC)
    current = {'DAY': instant.strftime('%Y-%m-%d'), 'WEEK': instant.strftime('%G-%V'), 'MONTH': instant.strftime('%Y-%m')}
    groups = defaultdict(list)
    for b in completed:
        dt = datetime.fromtimestamp(b.start,UTC)
        for kind,key in [('DAY',dt.strftime('%Y-%m-%d')),('WEEK',dt.strftime('%G-%V')),('MONTH',dt.strftime('%Y-%m'))]:
            if key < current[kind]:
                groups[kind,key].append(b)
    result = []
    for kind in current:
        keys = [key for k,key in groups if k==kind]
        if not keys:
            continue
        group = groups[kind,max(keys)]; first = datetime.fromtimestamp(group[0].start,UTC)
        after = datetime.fromtimestamp(group[-1].end,UTC)
        full = kind=='DAY' or (kind=='WEEK' and len(group)==7 and first.weekday()==0 and after.weekday()==0) or (
            kind=='MONTH' and first.day==1 and after.day==1 and first.month != after.month)
        if full:
            result.append({'period':kind,'known_at':group[-1].end,'completed_at':group[-1].end,
                'high':str(max(b.high for b in group)),'low':str(min(b.low for b in group)),
                'evidence':'Complete previous UTC calendar period; S_PREVIOUS_LEVELS'})
    return result


def contextual_fta(objects, direction, at, *, annotated_complete=False, consumed=None):
    """All four TFs. Only validated POIs; completeness never inferred from empty list."""
    consumed = consumed or set()
    pois = []
    for o in objects:
        if source_known_at(o)>at or o['tf'] not in TFS or o['kind'] not in ('POI','OB','breaker','STB','FVG','refined_POI'):
            continue
        if not o.get('source_validated'):
            continue
        p=o['payload']
        if not {'low','high','direction'} <= p.keys():
            continue
        pois.append({'id':o['id'],'tf':o['tf'],'low':p['low'],'high':p['high'],
            'known_at':source_known_at(o),'completed_at':o['completed_at'],'source_validated':True,
            'source_type':o['kind'],'opposing':p['direction']!=direction,'contextual':p.get('contextual') is True and o['id'] not in consumed,
            'consumed':o['id'] in consumed,'evidence':o['evidence']})
    return {'contextual_pois':pois,'contextual_poi_inventory':{'known_at':at,'completed_at':at,
        'complete_for_known_prefix':annotated_complete,'evidence':'Explicit known-prefix contextual POI inventory attestation'}}
