"""Causal primary-source paths, immutable physical union and lifecycle evidence.

This additive experiment leaves the strict/canonical detectors untouched.
See SOURCE_PERMITTED_PROTOCOL.md and config/source_permitted_policy.json.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from crypto_bot.strategy.market_analysis import MarketEventKind as K
from crypto_bot.strategy.market_analysis import TrendState
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_pdf_native import (
    Raid,
    Zone,
    evidence_json,
    identity,
    liquidity_roles,
    pd_location,
    poi_entry_policy,
    sign,
)
from crypto_bot.strategy.source_pdf_native import (
    SourceEngine as NativeClock,
)
from crypto_bot.strategy.source_pdf_native import (
    SourceSeries as StrictSeries,
)


def outside(price, direction):
    return math.nextafter(price, -math.inf if direction == 'LONG' else math.inf)


def impulse_direction(series):
    proofs = ([series.structure] if series.structure else []) + list(series.bos.values())
    latest = max(proofs, key=lambda p: p['known_at'], default=None)
    return latest['direction'] if latest else None


class SourceSeries(StrictSeries):
    """Source formation without compulsory future CONF or a wick-close OB gate."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deferred = []
        self.flow_audit = []
        self.atr_values = []
        self._true_ranges = []
        self.raid_classes = {}
        ranges=args[4] if len(args)>4 else kwargs.get('ranges')
        self.range_terminal={identity(self.symbol,self.tf,r.first_boundary_time,r.first_boundary_price,
                                     r.second_boundary_time,r.second_boundary_price):r.status_time
                             for r in (ranges.ranges if ranges else ())
                             if r.status.value in ('INVALIDATED_INTERNAL_STRUCTURE','RETIRED_LIQUIDITY_EXHAUSTED')}
        if ranges is None:
            self.range_terminal={}

    def _qualify(self, zone, proof):
        selected = proof
        if zone.kind in ('ORDER_BLOCK', 'STB', 'BTS'):
            candidates = [p for p in (self.bos.get(zone.direction), self.conf.get(zone.direction))
                          if p and zone.raid and p['known_at'] >= zone.raid.known_at]
            if zone.kind == 'ORDER_BLOCK':
                candidates = [p for p in candidates if p['kind'] in
                              (K.BULLISH_STRUCTURE_BROKEN_BOS.value, K.BEARISH_STRUCTURE_BROKEN_BOS.value)]
            selected = min(candidates, key=lambda p: p['known_at'], default=None)
            if selected is None:
                self.deferred.append(zone)
                return
        selected = dict(selected)
        selected['source_break_known_at']=selected['known_at']
        # Qualification is observed now, never backdated to a previous BOS.
        selected['known_at'] = self.candles[self.index].close_time
        super()._qualify(zone, selected)

    def _order_blocks(self, c):
        if self.index < 1:
            return
        origin = self.index - 1
        ob = self.candles[origin]
        for direction in ('LONG', 'SHORT'):
            s = sign(direction)
            raid = next((r for r in reversed(self.raids)
                         if r.candle_index == origin and r.direction == direction), None)
            engulf = s * (ob.close - ob.open) < 0 and s * (c.close - c.open) > 0
            engulf = engulf and (c.open <= ob.close and c.close > ob.open if s == 1
                                 else c.open >= ob.close and c.close < ob.open)
            if raid is None or not engulf or ('ORDER_BLOCK', origin) in self.origins:
                continue
            self.origins.add(('ORDER_BLOCK', origin))
            z = self._zone('ORDER_BLOCK', direction, ob.low, ob.high, c.close_time, origin, raid)
            z.confluence = {'engulfing_candle': {'open_time': c.open_time, 'known_at': c.close_time,
                                               'low': c.low, 'high': c.high},
                            'full_wick_close_strict_subset': c.close > ob.high if s == 1 else c.close < ob.low}
            self.pending.append(z)

    def _update_flow(self, c, proofs):
        now = c.close_time
        if self.flow and self.flow.get('invalidated_at') is None:
            f = self.flow
            dest = self.zone_registry.get(f['destination_poi']['zone_id'])
            reason = ('GLOBAL_DESTINATION_TESTED_OR_INVALIDATED' if dest is None or not dest.fresh(now)
                      else 'FROZEN_HTF_PROTECTED_THESIS_BODY_BREAK'
                      if sign(f['direction']) * (c.close - f['structure']['protected']) <= 0 else None)
            if reason:
                f['invalidated_at'], f['invalidation_reason'] = now, reason
                self.counts['flow_invalidations'] += 1
        for p in proofs:
            if p['kind'] in (K.BULLISH_STRUCTURE_CONFIRMED.value, K.BEARISH_STRUCTURE_CONFIRMED.value,
                             K.BULLISH_CONF_CONFIRMED.value, K.BEARISH_CONF_CONFIRMED.value):
                keys = self.structural_key_history[p['direction']]
                if not keys or (keys[-1]['protected'], keys[-1]['extreme']) != (p['protected'], p['extreme']):
                    keys.append(dict(p))
        if self.flow and self.flow.get('invalidated_at') is None:
            return
        direction = self.structure['direction'] if self.structure else None
        if direction is None:
            return
        s = sign(direction)
        keys = self.structural_key_history[direction]
        reason = None
        cause = None
        destination = None
        if len(keys) < 2:
            reason = 'OF_WAIT_TWO_CAUSAL_KEY_PAIRS'
        elif any(s * (keys[-1][k] - keys[-2][k]) <= 0 for k in ('protected', 'extreme')):
            reason = 'OF_KEY_PAIRS_NOT_HH_HL_OR_LL_LH'
        else:
            cause = next((r for r in reversed(self.raids)
                          if r.direction == direction and r.known_at >= keys[-2]['known_at']
                          and r.known_at <= now and s * (c.close - r.price) > 0), None)
            if cause is None:
                reason = 'OF_WAIT_REAL_LIQUIDITY_WORK_IN_KEY_LEG'
            else:
                destination = self.target(direction, c.close, now, global_only=True)
                if destination is None:
                    reason = 'OF_WAIT_FRESH_GLOBAL_TYPED_DESTINATION'
        if proofs or (self.raids and self.raids[-1].known_at == now):
            self.flow_audit.append({'known_at': now, 'direction': direction, 'reason': reason or 'OF_AVAILABLE',
                                    'classification': 'SOURCE_INTERPRETATION',
                                    'source': 'SW22 p5–6', 'key_pairs': keys[-2:],
                                    'liquidity_work': asdict(cause) if cause else None})
        if reason:
            self.counts[reason] += 1
            return
        f = {'flow_id': identity(self.symbol, self.tf, direction, now, destination.zone_id),
             'direction': direction, 'known_at': now, 'structure': dict(self.structure),
             'sequence': {'structural_keys': keys[-2:]}, 'liquidity_work': asdict(cause),
             'destination_poi': asdict(destination), 'invalidated_at': None,
             'classification': 'SOURCE_INTERPRETATION', 'source': 'SW22 p5–6',
             'extra_post_raid_body_break_required': False}
        self.flow = f
        self.flow_history.append(f)
        self.counts['active_flow_generations'] += 1

    def advance(self, index):
        old_pools = dict(self.pools)
        self.deferred = []
        touched, events = super().advance(index)
        self.pending.extend(z for z in self.deferred if z not in self.pending)
        now = self.candles[index].close_time
        for z in list(self.pending):
            if z.invalidated_at:
                continue
            if z.kind in ('DEMAND', 'SUPPLY'):
                proof = {'kind': 'DS_OLD_RAID_LAST_MOVE_RECLAIM', 'direction': z.direction,
                         'known_at': now, 'protected': z.low if z.direction == 'LONG' else z.high,
                         'extreme': z.high if z.direction == 'LONG' else z.low}
                super()._qualify(z, proof)
                self.pending.remove(z)
            elif z.kind in ('ORDER_BLOCK', 'STB', 'BTS'):
                before = len(self.zones)
                self._qualify(z, {})
                if len(self.zones) != before:
                    self.pending.remove(z)
        c = self.candles[index]
        previous = self.candles[index - 1].close if index else c.open
        tr = max(c.high - c.low, abs(c.high - previous), abs(c.low - previous))
        self._true_ranges.append(tr)
        value = (sum(self._true_ranges[:14]) / 14 if index == 13 else
                 (self.atr_values[-1] * 13 + tr) / 14 if index >= 14 else None)
        self.atr_values.append(value)
        for r in reversed(self.raids):
            if r.candle_index != index:
                break
            self.raid_classes[(r.candle_index,r.direction)] = [asdict(old_pools[k]) for k in r.liquidity_ids if k in old_pools]
        for q in self.zones:
            if q.kind=='FVG' and q.formed_at==now and q.structural_proof is None:
                bos=self.bos.get(q.direction)
                if bos and bos['known_at']<=now:
                    q.structural_proof=dict(bos)
        self._update_flow(c, [])
        return touched, events


class PhysicalRegistry:
    """Assign once using already-known context, before execution or future touch."""
    def __init__(self):
        self.anchors = defaultdict(list)
        self.assignments = {}

    def assign(self, symbol, tf, z, visit, known_at):
        key = (symbol, tf, z.range_id or z.zone_id, visit, z.direction)
        if z.kind=='RANGE_POI':
            return identity('PHYSICAL_RANGE',*key)
        if key in self.assignments:
            return self.assignments[key]
        end = z.raid.known_at if z.raid else z.formed_at
        start = end - timedelta(minutes=tf)
        anchor = {'symbol': symbol, 'direction': z.direction, 'raid_start': start, 'raid_end': end,
                  'low': z.low, 'high': z.high, 'visit': visit, 'known_at': known_at}
        prior = next((p for p in self.anchors[(symbol, z.direction)]
                      if p['visit'] == visit and p['known_at'] <= known_at
                      and max(p['raid_start'], start) < min(p['raid_end'], end)
                      and max(p['low'], z.low) <= min(p['high'], z.high)), None)
        pid = prior['physical_opportunity_id'] if prior else identity('PHYSICAL', *key)
        if prior is None:
            self.anchors[(symbol, z.direction)].append({**anchor, 'physical_opportunity_id': pid})
        self.assignments[key] = pid
        return pid


@dataclass
class SourceContextZone(Zone):
    """Actual SFP/range context geometry, never a fabricated candle or OB."""
    def __post_init__(self):
        if not 0 < self.low < self.high or self.known_at < self.formed_at:
            raise ValueError('invalid causal source context')
        sign(self.direction)


@dataclass
class Context:
    htf: int
    ltf: int
    poi: Zone
    interaction_at: datetime
    visit: int
    physical_id: str
    stages: set = field(default_factory=set)
    latest_reason: str = 'WAIT_BOS_NEW_POI'


class SourceEngine:
    def __init__(self, symbol, series, policy):
        if policy['trade_entry_allowed'] is not False or policy['mode'] not in ('BACKTEST', 'SHADOW'):
            raise ValueError('offline policy required')
        self.symbol, self.series, self.policy = symbol, series, policy
        for tf, owner in series.items():
            owner.native_touch_clock = tf > 5
        self.registry = PhysicalRegistry()
        self.contexts = []
        self.signals = []
        self.cancellations = []
        self.exit_events = []
        self.attempts = []
        self.funnel = Counter()
        self._emitted = set()
        self._cancelled = set()
        self._attempt_state = {}
        self._new_zones = {tf: set() for tf in series}
        self.direct_candidates = {tf: {} for tf in series}
        self._signal_refs = {}
        self._sfp_seen = set()
        self._range_offers = set()
        self._live_signals = []
        self._atr_watches = []
        self._pending_ranges = []
        self.paths = {r['path_id']: r for r in policy['paths']}

    def _attempt(self, key, now, reason, **detail):
        if self._attempt_state.get(key) == reason:
            return
        self._attempt_state[key] = reason
        self.attempts.append({'context_id': identity(*key), 'known_at': now, 'reason': reason,
                              'classification': 'SOURCE_INTERPRETATION', **detail})
        self.funnel[reason] += 1

    def _active_flow(self, owner, direction):
        f = owner.flow
        return f if f and f['direction'] == direction and f.get('invalidated_at') is None else None

    def _cancel(self, signal, cohort, now, reason, classification, source):
        key = (signal.signal_id, cohort)
        if key in self._cancelled or now <= signal.known_at:
            return
        self._cancelled.add(key)
        self.cancellations.append({'signal_id': signal.signal_id, 'cohort': cohort,
                                   'known_at': now, 'reason': reason,
                                   'classification': classification, 'source': source,
                                   'trade_entry_allowed': False})

    def _quote_stop(self, path, local, raid, owner):
        direction, s = local.direction, sign(local.direction)
        edge = local.high if s == 1 else local.low
        quote = edge if path['quote'] == 'EDGE' else (local.low + local.high) / 2
        distal = local.low if s == 1 else local.high
        stop = outside(distal, direction)
        if path['quote'] == 'TYPE':
            quote, stop, _, _ = poi_entry_policy(local, raid)
        elif path['quote']=='BOUNDARY':
            quote=local.confluence['fixed_boundary_quote']
        if path['stop'] == 'ENGULFING_EXTREME':
            engulf = local.confluence.get('engulfing_candle')
            if engulf is None:
                return None
            stop = outside(engulf['low'] if s == 1 else engulf['high'], direction)
        elif path['stop'] in ('SWEEPING_IMPULSE_EXTREME', 'DEVIATION_EXTREME', 'SFP_EXTREME'):
            value = min(distal, raid.extreme, local.stop_extreme or distal) if s == 1 else max(distal, raid.extreme, local.stop_extreme or distal)
            stop = outside(value, direction)
        elif path['stop'] == 'ATR14_BEYOND_SFP':
            if raid.candle_index >= len(owner.atr_values):
                return None
            atr = owner.atr_values[raid.candle_index]
            if atr is None:
                return None
            stop = raid.extreme - s * atr
        return quote, stop

    def _emit(self, path_id, htf, ltf, parent, local, now, pid, visit, interaction,
              raid, confirmations=None, entry_tf=None, flow_override=None, range_zone=None):
        key = (path_id, htf, ltf, pid)
        if key in self._emitted:
            return
        h, l = self.series[htf], self.series[ltf]
        path = self.paths[path_id]
        s, direction = sign(local.direction), local.direction
        quote_stop = self._quote_stop(path, local, raid, h if path_id=='SFP_ATR_STOP' else self.series[entry_tf or ltf])
        if quote_stop is None:
            self._attempt(key, now, 'WAIT_SOURCE_STOP_EVIDENCE', path_id=path_id)
            return
        entry, stop = quote_stop
        flow = flow_override or self._active_flow(h, direction)
        if flow is None:
            self._attempt(key, now, 'WAIT_ACTIVE_SOURCE_ORDER_FLOW', path_id=path_id, htf=htf, ltf=ltf)
            return
        pd_low,pd_high=parent.leg_low,parent.leg_high
        if flow.get('structure'):
            pd_low,pd_high=sorted((flow['structure']['protected'],flow['structure']['extreme']))
        good_pd, ote, retracement = pd_location(direction, entry,pd_low,pd_high)
        if path_id in ('DEMAND_SUPPLY','STB_BTS_EDGE','STB_BTS_HALF') and not good_pd:
            self._attempt(key, now, 'WAIT_SOURCE_REQUIRED_PD', path_id=path_id)
            return
        destination = h.target(direction, entry, now)
        if destination is None and range_zone is None:
            self._attempt(key, now, 'WAIT_SOURCE_FIRST_HTF_FTA', path_id=path_id)
            return
        targets = (destination.low if s == 1 else destination.high,) if destination else ()
        fractions = (1.0,)
        exit_policy = 'FULL_SOURCE_HTF_FTA'
        if range_zone is not None:
            boundary = math.nextafter(range_zone.high if s == 1 else range_zone.low,
                                      range_zone.low if s == 1 else range_zone.high)
            remainder = targets[0] if targets and s*(targets[0]-boundary)>0 else boundary
            first = min(boundary, targets[0]) if targets and s==1 else max(boundary,targets[0]) if targets else boundary
            targets, fractions, exit_policy = (first,remainder),(0.8,0.2),'RANGE80_INSIDE20_OPTIONAL_FTA'
        current = self.series[entry_tf or ltf].candles[self.series[entry_tf or ltf].index].close
        if s*(entry-stop)<=0 or s*(current-entry)<=0 or s*(targets[0]-current)<=0:
            self._attempt(key, now, 'WAIT_RESTING_QUOTE_AND_AHEAD_TARGET', path_id=path_id)
            return
        # Snapshot source evidence at READY. No future zone state leaks into it.
        thesis = flow.get('structure') or (confirmations or {}).get('bos')
        thesis_tf=htf if flow.get('structure') else ltf
        evidence = {'path_id':path_id,'physical_opportunity_id':pid,
                    'htf_poi':asdict(parent),'ltf_poi':asdict(local),'entry_zone_tf':entry_tf or ltf,
                    'liquidity_sweep':asdict(raid),'order_flow':json.loads(evidence_json(flow)),
                    'premium_discount':{'low':pd_low,'high':pd_high,
                                        'retracement':retracement,'allowed':good_pd,'ote_confluence':ote},
                    'liquidity_roles':liquidity_roles(h,l,parent,direction,entry,now),
                    'fta':asdict(destination) if destination else {'kind':'RANGE_BOUNDARY','known_at':range_zone.known_at},
                    'exit_policy':exit_policy,'source_citations':path['source_citations'],
                    'entry_policy':path['quote'],'stop_policy':path['stop'],
                    'confirmation_policy':path['confirmation'],'confirmations':confirmations or {},
                    'structural_thesis':dict(thesis) if thesis else None,'thesis_tf':thesis_tf,
                    'htf_interaction_at':interaction,'htf_visit_number':visit,
                    'classification':'SOURCE_RULE_WITH_DECLARED_MACHINE_INTERPRETATIONS',
                    'cancellation_cohorts':self.policy['cancellation_cohorts']}
        sid = identity(pid,path_id,htf,ltf,now,local.zone_id)
        signal = SourceSignal(sid,identity(*key),self.symbol,now,direction,htf,ltf,
                              path_id,parent.kind,entry,stop,targets,fractions,evidence)
        self.signals.append(signal)
        self._live_signals.append(signal)
        if path_id=='SFP_ATR_STOP':self._atr_watches.append(signal)
        self._signal_refs[sid] = (parent,local,h,l,dict(thesis) if thesis else None,raid)
        self._emitted.add(key)
        self._attempt(key,now,'READY',path_id=path_id,physical_opportunity_id=pid)

    def _parents(self, owner, local, entry_tf, now):
        q_open=self.series[entry_tf].candles[local.origin_index].open_time
        options={z.zone_id:z for z in owner.zones}
        options.update(owner.context_watches)
        return sorted((z for z in options.values()
                       if z.kind!='RANGE_POI' and z.direction==local.direction
                       and z.invalidated_at is None and z.known_at<=q_open
                       and z.low<=local.high and z.high>=local.low
                       and (z.kind=='ORDER_BLOCK' or z.test_count<=1)),
                      key=lambda z:(z.known_at,z.kind!='FVG',z.zone_id),reverse=True)

    def _direct(self, htf, ltf, local, now, *, entry_tf=None):
        qtf=entry_tf or ltf
        owner=self.series[htf]
        if not local.fresh(now) or local.raid is None:
            return
        if local.kind=='ORDER_BLOCK':
            ids=['OB_DIRECT_FIRST_TEST','OB_DIRECT_INSIDE','OB_DIRECT_ENGULFING_STOP','OB_DIRECT_INSIDE_ENGULFING_STOP']
        elif local.kind in ('STB','BTS'):
            ids=['STB_BTS_EDGE','STB_BTS_HALF']
        elif local.kind=='BREAKER':
            ids=['BREAKER_CONSERVATIVE_STOP','BREAKER_AGGRESSIVE_STOP']
        elif local.kind in ('DEMAND','SUPPLY'):
            ids=['DEMAND_SUPPLY']
        else:
            return
        if impulse_direction(self.series[qtf])!=local.direction:
            self._attempt((local.zone_id,htf,ltf),now,'WAIT_SOURCE_STRUCTURAL_IMPULSE',poi_type=local.kind)
            return
        parents=self._parents(owner,local,qtf,now) if qtf!=htf else []
        if qtf==htf:
            higher=[tf for tf in self.series if tf>htf]
            outer=self._parents(self.series[min(higher)],local,qtf,now) if higher else []
            if local.kind=='ORDER_BLOCK' and not outer:
                self._attempt((local.zone_id,htf,ltf,'HTF_DIRECT'),now,'WAIT_PREEXISTING_HIGHER_NATIVE_POI')
                return
            parent=local
        elif parents:
            parent=parents[0]
        elif local.kind=='ORDER_BLOCK':
            self._attempt((local.zone_id,htf,ltf),now,'WAIT_OB_INSIDE_PREEXISTING_HTF_POI')
            return
        else:
            # SW22 / independent D/S do not state a universal nested HTF-POI gate.
            parent=local
        visit=max(1,parent.test_count)
        if parent.kind=='ORDER_BLOCK' and visit>1:
            bos=self.series[qtf].bos.get(local.direction)
            if bos is None or bos['known_at']<parent.visit_started_at or local.formed_at<parent.visit_started_at:
                return
        anchor_tf=htf if parent is not local or qtf==htf else qtf
        pid=self.registry.assign(self.symbol,anchor_tf,parent,visit,now)
        for path in ids:
            self._emit(path,htf,ltf,parent,local,now,pid,visit,parent.visit_started_at,
                       local.raid,entry_tf=qtf)

    def _conservative(self, context, now):
        l,z=self.series[context.ltf],context.poi
        if z.invalidated_at or z.test_count>context.visit:
            return
        bos=l.bos.get(z.direction)
        if bos is None or bos['known_at']<context.interaction_at:
            context.latest_reason='WAIT_CAUSAL_LTF_BOS_AFTER_REACTION'
            return
        locals_=[q for q in l.zones if q.kind!='RANGE_POI' and q.direction==z.direction
                 and q.fresh(now) and q.formed_at>=context.interaction_at and q.known_at>=bos['known_at']
                 and q.structural_proof and q.structural_proof.get('direction')==z.direction
                 and (q.kind!='ORDER_BLOCK' or q.low<=z.high and q.high>=z.low)]
        if not locals_:
            context.latest_reason='WAIT_NEW_LOCAL_POI_AFTER_BOS'
            return
        local=max(locals_,key=lambda q:(q.known_at,q.kind!='FVG',q.zone_id))
        raid=next((r for r in reversed(l.raids) if r.direction==z.direction
                   and context.interaction_at<=r.known_at<=bos['known_at']),z.raid)
        if raid is None:
            return
        proof={'bos':dict(bos),'reaction_at':context.interaction_at}
        context.stages.add('BOS_POI')
        if z.kind=='SFP':
            # SW9 explicitly allows a countertrend LTF transition to first HTF FTA.
            direction=z.direction
            f={'flow_id':identity('SFP_DELIVERY',context.physical_id),
                'direction':direction,'known_at':bos['known_at'],'liquidity_work':asdict(z.raid),
                'structural_break':dict(bos),'source':'DOC16 P0075–87; SW9 p13',
                'classification':'SOURCE_INTERPRETATION_COUNTERTREND_REACTION','invalidated_at':None,
                'local_flow_confluence':json.loads(evidence_json(self._active_flow(l,direction)))}
            for path in ('SFP_BOS_POI','SFP_ATR_STOP'):
                self._emit(path,context.htf,context.ltf,z,local,now,context.physical_id,
                           context.visit,context.interaction_at,z.raid,proof,flow_override=f)
            return
        self._emit('OB_CONSERVATIVE_BOS_POI',context.htf,context.ltf,z,local,now,
                   context.physical_id,context.visit,context.interaction_at,raid,proof)
        conf=l.conf.get(z.direction)
        structure=conf.get('new_structure') if conf else None
        if conf and structure and bos['known_at']<structure['known_at']<=conf['known_at']<=now:
            proof.update(new_structure=dict(structure),conf=dict(conf))
            context.stages.add('CONF')
            self._emit('OB_ULTRA_CONSERVATIVE_CONF',context.htf,context.ltf,z,local,now,
                       context.physical_id,context.visit,context.interaction_at,raid,proof)

    def _range_signal(self,z,htf,ltf,local,now,path):
        direction=z.direction
        pid=self.registry.assign(self.symbol,htf,z,1,now)
        f={'flow_id':identity('RANGE_DELIVERY',pid),'direction':direction,'known_at':now,
           'liquidity_work':asdict(z.raid) if z.raid else None,
           'destination_poi':{'kind':'RANGE_BOUNDARY','low':z.low,'high':z.high,'known_at':z.known_at},
           'classification':'SOURCE_INTERPRETATION_RANGE_DELIVERY',
           'source':'DOC06 P0087–94, P0111–129','invalidated_at':None}
        raid=z.raid or local.raid
        if raid is None:
            return
        if path=='RANGE_CONSERVATIVE_RETEST':
            # Native boundary limit is outside neither geometry nor the source.
            quote=z.low if direction=='LONG' else z.high
            local=SourceContextZone(identity(z.zone_id,'BOUNDARY'), 'RANGE_POI',direction,
                z.low,z.high,z.formed_at,z.known_at,z.origin_index,z.raid,z.low,z.high,
                structural_proof=z.structural_proof)
            local.confluence['fixed_boundary_quote']=quote
        self._emit(path,htf,ltf,z,local,now,pid,1,z.range_retest_at or z.known_at,
                   raid,flow_override=f,range_zone=z,entry_tf=htf)

    def _range_aggressive(self,htf,now):
        h=self.series[htf]
        for (low,high,known,rid) in h.range_bounds.values():
            if known>now or h.range_terminal.get(rid,now+timedelta(days=1))<=now:
                continue
            for direction in ('LONG','SHORT'):
                key=(htf,rid,direction)
                if key in self._range_offers:
                    continue
                external=[q for q in h.zones if q.kind not in ('FVG','RANGE_POI')
                          and q.direction==direction and q.fresh(now) and q.raid
                          and (q.high<low if direction=='LONG' else q.low>high)]
                if not external:
                    continue
                q=max(external,key=lambda q:(q.high if direction=='LONG' else -q.low,q.zone_id))
                z=SourceContextZone(identity(rid,direction,'RANGE'), 'RANGE_POI',direction,
                    low,high,known,known,q.origin_index,None,low,high,range_id=rid,
                    external_poi=asdict(q),confluence={'execution_condition':'QUOTE_OUTSIDE_RANGE_IMPLIES_ACTUAL_DEVIATION_AT_FILL'})
                previous=len(self.signals)
                for hh,ll in self.policy['mappings']:
                    if hh==htf:
                        self._range_signal(z,hh,ll,q,now,'RANGE_AGGRESSIVE_EXTERNAL_POI')
                if len(self.signals)>previous:
                    self._range_offers.add(key)

    def _observe_sfp_open(self,c):
        for htf,h in self.series.items():
            if htf<=5 or h.index<0 or h.candles[h.index].close_time!=c.open_time:
                continue
            previous=h.candles[h.index]
            for raid in reversed(h.raids):
                if raid.candle_index!=h.index:
                    break
                s=sign(raid.direction)
                classes=getattr(h,'raid_classes',{}).get((h.index,raid.direction),[])
                if not any(p['classification']=='EXTERNAL' for p in classes):
                    continue
                if s*(previous.close-raid.price)<=0 or s*(c.open-raid.price)<=0:
                    continue
                key=(htf,raid.candle_index,raid.direction)
                if key in self._sfp_seen:
                    continue
                self._sfp_seen.add(key)
                sfp=Raid(raid.direction,c.close_time,raid.price,raid.extreme,raid.candle_index,raid.liquidity_ids,True)
                z=SourceContextZone(identity('SFP',self.symbol,*key),'SFP',raid.direction,
                    previous.low,previous.high,previous.close_time,c.close_time,h.index,sfp,
                    min(previous.low,raid.price),max(previous.high,raid.price),
                    confluence={'next_real_5m_open':c.open,'next_open_time':c.open_time,
                                'source':'DOC16 P0075–83','native_pattern_tf':htf})
                pid=self.registry.assign(self.symbol,htf,z,1,c.close_time)
                for hh,ll in self.policy['mappings']:
                    if hh==htf:
                        self.contexts.append(Context(hh,ll,z,c.close_time,1,pid))

    def _lifecycle(self,tf,c):
        now=c.close_time
        live=[]
        for signal in self._live_signals:
            parent,local,h,l,thesis,raid=self._signal_refs[signal.signal_id]
            if now<=signal.known_at:
                live.append(signal)
                continue
            s=sign(signal.direction)
            if ((signal.signal_id,'CANCEL_STRICT_STRUCTURE') not in self._cancelled
                and tf==signal.ltf and l.trend != (TrendState.BULLISH if s==1 else TrendState.BEARISH)):
                self._cancel(signal,'CANCEL_STRICT_STRUCTURE',now,'GENERIC_LTF_STRUCTURE_BROKEN',
                             'SOURCE_INTERPRETATION','strict d46646f; SW5 conservative subset')
            fta=signal.evidence['fta']
            fta_known=datetime.fromisoformat(fta['known_at']) if isinstance(fta['known_at'],str) else fta['known_at']
            if (tf==5 and fta.get('low') is not None and fta.get('high') is not None
                and fta_known<=c.open_time
                and c.low<=fta['high'] and c.high>=fta['low']):
                self._cancel(signal,'CANCEL_STRICT_STRUCTURE',now,'STRICT_FIRST_HTF_FTA_TESTED',
                             'SOURCE_INTERPRETATION','strict d46646f FTA lifetime subset; SW9 p11–16')
            reason=None
            source='SOURCE_INTERPRETATION'
            citation='Source-specific idea/POI lifecycle'
            if parent.invalidated_at or local.invalidated_at:
                reason='ENTRY_OR_PARENT_POI_BODY_INVALIDATED'
                citation='SW9 p2–10; DOC18 P0010–12; SW22 p2–4'
            elif parent.kind=='RANGE_POI' and h.range_terminal.get(parent.range_id,now+timedelta(days=1))<=now:
                reason='CAUSAL_RANGE_INTERNAL_STRUCTURE_OR_LIQUIDITY_EXHAUSTION'
                citation='DOC06 P0062–71; DOC19 P0123–126'
            elif tf==signal.evidence['thesis_tf'] and thesis and s*(c.close-thesis['protected'])<=0:
                reason='FROZEN_HTF_STRUCTURAL_THESIS_BODY_BREAK'
                citation='SW5 p3–5; SW22 p6'
            elif parent.kind=='SFP' and tf==signal.htf and s*(c.close-raid.extreme)<=0:
                reason='SFP_BODY_CLOSE_INVALIDATION'
                citation='SW12 p13'
                source='SOURCE_RULE'
            f=signal.evidence['order_flow']
            if reason is None and f.get('destination_poi',{}).get('zone_id'):
                destination=h.zone_registry.get(f['destination_poi']['zone_id'])
                if destination is None or destination.first_test is not None and destination.first_test<=now:
                    reason='FIXED_GLOBAL_DESTINATION_TESTED'
                    citation='SW22 p6'
                    source='SOURCE_RULE_WITH_NATIVE_TOUCH_INTERPRETATION'
                elif h.flow and h.flow['direction']!=signal.direction:
                    reason='OBJECTIVE_HTF_ORDER_FLOW_DIRECTION_CHANGE'
                    citation='SW22 p5–6'
            if reason:
                for cohort in self.policy['cancellation_cohorts']:
                    self._cancel(signal,cohort,now,reason,source,citation)
            if (signal.signal_id,self.policy['primary_cancellation']) not in self._cancelled:
                live.append(signal)
        self._live_signals=live

    def advance(self,tf,index):
        series=self.series[tf]
        watches={z.zone_id:z for z in self.direct_candidates[tf].values()}
        watches.update({c.poi.zone_id:c.poi for c in self.contexts if c.htf==tf and c.poi.kind not in ('SFP',)
                        and c.poi.invalidated_at is None})
        for signal in self._live_signals:
            parent,local,_h,_l,_,_=self._signal_refs[signal.signal_id]
            if self.series[tf].zone_registry.get(parent.zone_id) is parent:watches[parent.zone_id]=parent
            if signal.evidence['entry_zone_tf']==tf:watches[local.zone_id]=local
        series.context_watches=watches
        touched,_events=series.advance(index)
        c=series.candles[index]
        now=c.close_time
        touches=[(tf,z) for z in touched]
        if tf==5:
            touches.extend(NativeClock._native_touches(self,c))
            self._observe_sfp_open(c)
        for owner in self.series.values():
            f=owner.flow
            if f and f.get('invalidated_at') is None:
                destination=owner.zone_registry.get(f['destination_poi']['zone_id'])
                if destination and destination.first_test and destination.first_test<=now:
                    f['invalidated_at'],f['invalidation_reason']=now,'ACTUAL_NATIVE_GLOBAL_DESTINATION_TEST'
        for htf,z in touches:
            if z.invalidated_at or z.kind=='FVG':
                # Fresh gaps may support local OBs, but have no independent raid reaction.
                continue
            for hh,ll in self.policy['mappings']:
                if hh!=htf:continue
                visit=max(1,z.test_count)
                pid=self.registry.assign(self.symbol,hh,z,visit,now)
                self.contexts.append(Context(hh,ll,z,now,visit,pid))
                if z.kind=='RANGE_POI':
                    self._pending_ranges.append((z,hh,ll))
        for q in series.zones:
            if q.zone_id not in self._new_zones[tf]:
                self._new_zones[tf].add(q.zone_id)
                if q.kind not in ('FVG','RANGE_POI'):
                    self.direct_candidates[tf][q.zone_id]=q
        self._lifecycle(tf,c)
        atr_live=[]
        for signal in self._atr_watches:
            raid=self._signal_refs[signal.signal_id][-1]
            if now>signal.known_at and tf==signal.htf and sign(signal.direction)*(c.close-raid.extreme)<=0:
                self.exit_events.append({'signal_id':signal.signal_id,'known_at':now,
                                         'reason':'SFP_PATTERN_BODY_CLOSE_INVALIDATION','price':c.close,'source':'SW12 p13'})
            else:
                atr_live.append(signal)
        self._atr_watches=atr_live
        for owner_tf in self.direct_candidates:
            self.direct_candidates[owner_tf]={k:q for k,q in self.direct_candidates[owner_tf].items()
                                              if q.invalidated_at is None and q.first_test is None}
        self.contexts=[ctx for ctx in self.contexts if ctx.poi.invalidated_at is None
                       and ctx.poi.test_count<=ctx.visit]

    def evaluate(self,now,changed_tfs):
        """Admit only after all native bars at this CLOSE, including 5m tests."""
        for z,htf,ltf in self._pending_ranges:
            if z.invalidated_at is None:
                self._range_signal(z,htf,ltf,z,now,'RANGE_CONSERVATIVE_RETEST')
        self._pending_ranges=[]
        for htf,ltf in self.policy.get('direct_mappings',self.policy['mappings']):
            if htf not in self.series or ltf not in self.series:continue
            if ltf in changed_tfs:
                for q in self.direct_candidates[ltf].values():
                    self._direct(htf,ltf,q,now)
            if htf in changed_tfs and ltf==5:
                for q in self.direct_candidates[htf].values():
                    self._direct(htf,ltf,q,now,entry_tf=htf)
        for tf in changed_tfs:
            if tf>5:self._range_aggressive(tf,now)
        for context in self.contexts:
            if context.ltf in changed_tfs and context.poi.kind!='RANGE_POI':
                self._conservative(context,now)

    def finish(self):
        return {'symbol':self.symbol,'funnel':dict(self.funnel),
                'paths':dict(Counter(s.evidence['path_id'] for s in self.signals)),
                'latest_context_blockers':dict(Counter(c.latest_reason for c in self.contexts)),
                'series':{str(tf):dict(s.counts) for tf,s in self.series.items()},
                'trade_entry_allowed':False}


def select_union(signals,policy):
    """Selection uses immutable READY evidence, never fills or future outcomes."""
    priority={p:i for i,p in enumerate(policy['entry_tie_precedence'])}
    ordered=sorted(signals,key=lambda s:(s.known_at,priority[s.evidence['path_id']],-s.htf,s.ltf,
                                        policy['symbol_priority'].index(s.symbol),s.signal_id))
    selected,duplicate=[],[]
    retained={}
    for signal in ordered:
        pid=signal.evidence['physical_opportunity_id']
        if pid not in retained:
            retained[pid]=signal.signal_id
            selected.append(signal)
        else:
            duplicate.append({'signal_id':signal.signal_id,'physical_opportunity_id':pid,
                              'retained_signal_id':retained[pid],'known_at':signal.known_at,
                              'reason':'ONE_PHYSICAL_OPPORTUNITY_IMMUTABLE_CAUSAL_SELECTION'})
    return selected,duplicate
