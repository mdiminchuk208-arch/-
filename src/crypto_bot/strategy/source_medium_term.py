"""Additive causal H1/H4 source engine with explicit macro ownership and costs.

Frozen primary-PDF detectors and the canonical portfolio remain unchanged.
See MEDIUM_TERM_RESEARCH_PROTOCOL.md for declared machine interpretations.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, replace

from crypto_bot.common.models import Direction
from crypto_bot.strategy.anti_scalp import AntiScalpPolicy, check_anti_scalp
from crypto_bot.strategy.replay import EngineMode, StrategySignal
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_pdf_native import (
    Raid,
    evidence_json,
    identity,
    pd_location,
    sign,
)
from crypto_bot.strategy.source_permitted import (
    Context,
    SourceContextZone,
    SourceEngine,
)
from crypto_bot.strategy.trade_plan import PriceZone
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio


class MediumTermEngine(SourceEngine):
    def __init__(self, symbol, series, policy, *, anti_scalp_enabled=True):
        super().__init__(symbol, series, policy)
        self.clock = policy['execution_clock']
        self.anti_scalp_enabled = anti_scalp_enabled
        self.cost_policy = AntiScalpPolicy(policy['fee_rate'], policy['slippage_fraction'],
                                          policy['minimum_edge_cost_ratio'])
        for tf, owner in series.items():
            owner.native_touch_clock = tf > self.clock
        self.lifecycle = []
        self.rejections = []
        self._retained = {}
        self._discovered = set()
        self._reject_ids = set()

    def _transition(self, idea, now, status, **details):
        self.lifecycle.append(dict(idea_id=idea, known_at=now, status=status,
                                   trade_entry_allowed=False, **details))

    def _macro_context(self, setup_tf, direction, now, countertrend):
        for tf in (240, 1440):
            if tf <= setup_tf or tf not in self.series:
                continue
            owner = self.series[tf]
            if owner.index < 0:
                continue
            structure = owner.structure
            ranges = [{'low': lo, 'high': hi, 'known_at': at, 'range_id': rid}
                      for lo, hi, at, rid in owner.range_bounds.values()
                      if at <= now and (rid not in owner.range_terminal or owner.range_terminal[rid] > now)]
            if structure and structure['known_at'] <= now and (countertrend or structure['direction'] == direction):
                return tf, {'structure': dict(structure), 'ranges': ranges,
                            'pools': [asdict(p) for p in owner.pools.values()],
                            'countertrend_delivery': countertrend,
                            'observed_at': owner.candles[owner.index].close_time}
            if countertrend and ranges:
                return tf, {'structure': None, 'ranges': ranges,
                            'pools': [asdict(p) for p in owner.pools.values()],
                            'countertrend_delivery': True,
                            'observed_at': owner.candles[owner.index].close_time}
        return None, None

    def _targets(self, direction, entry, now, range_zone=None):
        s = sign(direction)
        candidates = []
        for tf in (240, 1440):
            owner = self.series[tf]
            for z in owner.zones:
                if z.direction == direction or z.kind == 'RANGE_POI' or not z.fresh(now):
                    continue
                price = z.low if s == 1 else z.high
                if s * (price - entry) > 0:
                    candidates.append({'price': price, 'tf': tf, 'kind': z.kind,
                                           'known_at': z.known_at, 'source': asdict(z)})
            for p in owner.pools.values():
                if (p.classification == 'EXTERNAL' and p.side == ('high' if s == 1 else 'low')
                        and p.known_at <= now and s * (p.price - entry) > 0):
                    candidates.append({'price': p.price, 'tf': tf, 'kind': 'EXTERNAL_LIQUIDITY',
                                           'known_at': p.known_at, 'source': asdict(p)})
        if range_zone is not None:
            boundary = math.nextafter(range_zone.high if s == 1 else range_zone.low,
                                      range_zone.low if s == 1 else range_zone.high)
            if s * (boundary - entry) > 0:
                candidates.append({'price': boundary, 'tf': range_zone.confluence.get('native_pattern_tf', 240),
                                       'kind': 'SOURCE_RANGE_BOUNDARY', 'known_at': range_zone.known_at,
                                       'source': asdict(range_zone)})
        unique = []
        for c in sorted(candidates, key=lambda x: (s * x['price'], -x['tf'], x['kind'])):
            if not unique or c['price'] != unique[-1]['price']:
                unique.append(c)
        return unique[:3]

    def _emit(self, path_id, htf, ltf, parent, local, now, pid, visit, interaction,
              raid, confirmations=None, entry_tf=None, flow_override=None, range_zone=None):
        qtf = entry_tf or ltf
        setup_tf = qtf if parent is local else htf
        key = (path_id, htf, ltf, pid)
        if key in self._emitted or pid in self._retained:
            return
        if pid not in self._discovered:
            self._discovered.add(pid)
            self._transition(pid, now, 'DISCOVERED', setup_tf=htf, parent_id=parent.zone_id)
        main_valid = (htf in (60, 240) and (parent is not local or qtf in (60, 240))
                      and parent.known_at <= now and parent.invalidated_at is None
                      and (parent.structural_proof is not None or parent.kind in ('SFP', 'RANGE_POI')))
        path = self.paths[path_id]
        h = self.series[htf]
        direction, s = local.direction, sign(local.direction)
        flow = flow_override or self._active_flow(h, direction)
        if flow is None:
            self._attempt(key, now, 'WAIT_ACTIVE_MAIN_SOURCE_FLOW', path_id=path_id)
            return
        qs = self._quote_stop(path, local, raid, h if path_id == 'SFP_ATR_STOP' else self.series[qtf])
        if qs is None:
            self._attempt(key, now, 'WAIT_SOURCE_STOP_EVIDENCE', path_id=path_id)
            return
        entry, stop = qs
        if main_valid:
            # A refinement never removes the already-known main invalidator.
            invalidator = (parent.raid.extreme if parent.raid is not None
                           else parent.low if s == 1 else parent.high)
            main_distal = parent.low if s == 1 else parent.high
            main_stop = math.nextafter(min(invalidator, main_distal) if s == 1 else max(invalidator, main_distal),
                                       -math.inf if s == 1 else math.inf)
            stop = min(stop, main_stop) if s == 1 else max(stop, main_stop)
        countertrend = parent.kind in ('SFP', 'RANGE_POI')
        macro_tf, macro = self._macro_context(htf, direction, now, countertrend)
        target_evidence = self._targets(direction, entry, now, range_zone)
        first = target_evidence[0]['price'] if target_evidence else None
        scalp = check_anti_scalp(direction=direction, entry=entry, target=first,
                                 setup_tf=setup_tf, context_tf=macro_tf,
                                 main_setup_valid=main_valid, context_valid=macro is not None,
                                 target_known_before_entry=bool(target_evidence), policy=self.cost_policy)
        if not main_valid or macro is None or (self.anti_scalp_enabled and not scalp.allowed):
            rejection_id = identity(pid, path_id, scalp.reason)
            if rejection_id not in self._reject_ids:
                self._reject_ids.add(rejection_id)
                self.rejections.append(dict(signal_id=rejection_id, physical_opportunity_id=pid,
                                            known_at=now, path_id=path_id, setup_tf=htf,
                                            context_tf=macro_tf, entry=entry, target=first,
                                            **scalp.evidence()))
            self._attempt(key, now, scalp.reason, path_id=path_id, physical_opportunity_id=pid)
            return
        if len(target_evidence) < 3:
            self._attempt(key, now, 'WAIT_THREE_DISTINCT_REAL_MACRO_TARGETS', path_id=path_id)
            return
        pd_low, pd_high = parent.leg_low, parent.leg_high
        main_structure = flow.get('structure')
        if main_structure:
            pd_low, pd_high = sorted((main_structure['protected'], main_structure['extreme']))
        elif parent.kind == 'SFP':
            # A candle's raid/reclaim envelope is not a dealing range.
            dr = macro.get('structure')
            if dr:
                pd_low, pd_high = sorted((dr['protected'], dr['extreme']))
            elif macro['ranges']:
                actual_range = max(macro['ranges'], key=lambda r: r['known_at'])
                pd_low, pd_high = actual_range['low'], actual_range['high']
        pd_ok, ote, retracement = pd_location(direction, entry, pd_low, pd_high)
        if path_id in ('DEMAND_SUPPLY', 'STB_BTS_EDGE', 'STB_BTS_HALF') and not pd_ok:
            self._attempt(key, now, 'WAIT_SOURCE_REQUIRED_PD', path_id=path_id)
            return
        targets = tuple(x['price'] for x in target_evidence)
        current = self.series[qtf].candles[self.series[qtf].index].close
        if s * (entry - stop) <= 0 or s * (current - entry) <= 0 or s * (targets[0] - current) <= 0:
            self._attempt(key, now, 'WAIT_RESTING_QUOTE_AND_AHEAD_TARGET', path_id=path_id)
            return
        # Native source proofs are retained as typed formation evidence; a DS
        # reclaim/OB confirmation is never relabelled as a fabricated SFP/BOS.
        proof = (confirmations or {}).get('bos') or local.structural_proof or parent.structural_proof
        proof_time = proof.get('known_at') if proof else local.known_at
        if isinstance(proof_time, str):
            from datetime import datetime
            proof_time = datetime.fromisoformat(proof_time)
        raid_event_time = parent.confluence.get('next_open_time', raid.known_at) if parent.kind == 'SFP' else raid.known_at
        if proof_time is None or raid.known_at > proof_time or raid_event_time >= proof_time or proof_time > now:
            self._attempt(key, now, 'WAIT_CAUSAL_RAID_THEN_SOURCE_CONFIRMATION', path_id=path_id)
            return
        evidence = {'path_id': path_id, 'physical_opportunity_id': pid, 'setup_tf': setup_tf,
                        'actual_setup_tf': setup_tf, 'flow_owner_tf': htf,
                        'refinement_tf': qtf, 'execution_clock': self.clock, 'macro_context_tf': macro_tf,
                        'macro_context': macro, 'main_setup_valid': main_valid,
                        'htf_poi': asdict(parent), 'ltf_poi': asdict(local), 'liquidity_sweep': asdict(raid),
                        'order_flow': json.loads(evidence_json(flow)),
                        'premium_discount': {'low': pd_low, 'high': pd_high, 'allowed': pd_ok,
                                              'retracement': retracement, 'ote_confluence': ote},
                        'targets': target_evidence, 'anti_scalp': scalp.evidence(),
                        'anti_scalp_enabled': self.anti_scalp_enabled, 'source_citations': path['source_citations'],
                        'source_confirmation': proof, 'source_confirmation_known_at': proof_time,
                        'causal_raid_event_time': raid_event_time,
                        'source_confirmation_kind': proof.get('kind') if proof else 'SOURCE_POI_FORMATION',
                        'structural_thesis': dict(main_structure) if main_structure else None,
                        'exit_policy': 'TP40_30_30_CANONICAL_COST_ADJUSTED_BE',
                        'entry_zone_tf': qtf, 'htf_interaction_at': interaction, 'htf_visit_number': visit,
                        'stop_policy': 'SOURCE_STOP_INCLUDING_MAIN_SETUP_INVALIDATOR',
                        'classification': 'SOURCE_RULES_WITH_DECLARED_MEDIUM_AND_COST_POLICY'}
        sid = identity('MEDIUM', pid, path_id, htf, now, local.zone_id)
        signal = SourceSignal(sid, identity(*key), self.symbol, now, direction, htf, ltf,
                              path_id, parent.kind, entry, stop, targets, (.4, .3, .3), evidence)
        self.signals.append(signal)
        self._live_signals.append(signal)
        self._signal_refs[sid] = (parent, local, h, self.series[ltf], main_structure, raid)
        self._emitted.add(key)

    def _finalize_ready(self, start, now):
        rank = {path: i for i, path in enumerate(self.policy['entry_tie_precedence'])}
        offers = sorted(self.signals[start:], key=lambda s: (rank[s.setup_type], -s.htf, s.ltf, s.signal_id))
        selected, removed = [], set()
        for signal in offers:
            pid = signal.evidence['physical_opportunity_id']
            if pid in self._retained:
                removed.add(signal.signal_id)
                self.funnel['DUPLICATE_CAUSAL_PATH_ALIAS'] += 1
                continue
            self._retained[pid] = signal.signal_id
            selected.append(signal)
            self._transition(pid, now, 'QUALIFIED', path_id=signal.setup_type)
            self._transition(pid, now, 'READY', signal_id=signal.signal_id, path_id=signal.setup_type)
            self._attempt((signal.setup_type, signal.htf, signal.ltf, pid), now, 'READY',
                          path_id=signal.setup_type, physical_opportunity_id=pid)
        self.signals = self.signals[:start] + selected
        self._live_signals = [s for s in self._live_signals if s.signal_id not in removed]

    def _lifecycle(self, tf, c):
        now = c.close_time
        live = []
        for signal in self._live_signals:
            parent, local, h, _l, thesis, raid = self._signal_refs[signal.signal_id]
            reason = None
            if now > signal.known_at:
                pending_reason = None
                if tf == signal.evidence['entry_zone_tf'] and local.invalidated_at:
                    pending_reason = 'REFINEMENT_POI_BODY_INVALIDATED_PENDING_ONLY'
                if tf == self.clock and (c.high >= signal.targets[0] if signal.direction == 'LONG'
                                          else c.low <= signal.targets[0]):
                    pending_reason = 'MAIN_TARGET_CONSUMED_PENDING_ONLY'
                if tf in (240, 1440):
                    macro_tf, _macro = self._macro_context(signal.htf, signal.direction, now,
                                                         parent.kind in ('SFP', 'RANGE_POI'))
                    if macro_tf is None:
                        pending_reason = 'MACRO_CONTEXT_UNAVAILABLE_PENDING_ONLY'
                if pending_reason:
                    # Detection is independent of future fills: withdraw the
                    # pending quote, but retain main thesis watches for entered
                    # positions. No exit event is emitted for micro geometry.
                    self._cancel(signal, self.policy['primary_cancellation'], now, pending_reason,
                                 'SOURCE_ENTRY_LIFETIME_WITH_MEDIUM_OWNERSHIP', 'SW9/SW22')
            if now > signal.known_at:
                if tf == actual_setup_tf(signal) and parent.invalidated_at:
                    reason = 'MAIN_SOURCE_POI_BODY_INVALIDATED'
                elif tf == signal.htf and parent.kind == 'SFP' and sign(signal.direction) * (c.close - raid.extreme) <= 0:
                    reason = 'MAIN_SFP_BODY_INVALIDATION'
                elif tf == signal.htf and thesis and sign(signal.direction) * (c.close - thesis['protected']) <= 0:
                    reason = 'MAIN_PROTECTED_STRUCTURE_BODY_BREAK'
                elif (tf == signal.htf and parent.kind == 'RANGE_POI' and parent.range_id in h.range_terminal
                      and h.range_terminal[parent.range_id] <= now):
                    reason = 'MAIN_RANGE_EXHAUSTED'
            if reason:
                self._cancel(signal, self.policy['primary_cancellation'], now, reason,
                             'SOURCE_RULE_WITH_MAIN_TIMEFRAME_INTERPRETATION', 'SW5/SW9/SW22')
                self.exit_events.append({'signal_id': signal.signal_id, 'known_at': now,
                                             'reason': reason, 'price': c.close})
            else:
                live.append(signal)
        self._live_signals = live
        # SFP contexts are external to the native series zone registry.
        for context in self.contexts:
            z = context.poi
            if context.htf == tf and z.kind == 'SFP' and z.known_at < now and sign(z.direction) * (c.close - z.raid.extreme) <= 0:
                z.invalidated_at = now

    def _observe_sfp_open(self, c):
        for htf in (60, 240):
            h = self.series[htf]
            if h.index < 0 or h.candles[h.index].close_time != c.open_time:
                continue
            previous = h.candles[h.index]
            for raid in reversed(h.raids):
                if raid.candle_index != h.index:
                    break
                s = sign(raid.direction)
                classes = h.raid_classes.get((h.index, raid.direction), [])
                key = (htf, raid.candle_index, raid.direction)
                if key in self._sfp_seen or not any(p['classification'] == 'EXTERNAL' for p in classes):
                    continue
                if s * (previous.close - raid.price) <= 0 or s * (c.open - raid.price) <= 0:
                    continue
                self._sfp_seen.add(key)
                sfp = Raid(raid.direction, c.close_time, raid.price, raid.extreme,
                           raid.candle_index, raid.liquidity_ids, True)
                z = SourceContextZone(identity('MEDIUM_SFP', self.symbol, *key), 'SFP', raid.direction,
                                      previous.low, previous.high, previous.close_time, c.close_time,
                                      h.index, sfp, min(previous.low, raid.price), max(previous.high, raid.price),
                                      confluence={'next_real_open': c.open, 'next_open_time': c.open_time,
                                                      'observed_at': c.close_time, 'execution_clock': self.clock,
                                                      'native_pattern_tf': htf, 'source': 'DOC16 P0075–83'})
                pid = self.registry.assign(self.symbol, htf, z, 1, c.close_time)
                for hh, ll in self.policy['mappings']:
                    if hh == htf:
                        self.contexts.append(Context(hh, ll, z, c.close_time, 1, pid))

    def _touches(self, c):
        touches = []
        for tf, owner in self.series.items():
            if tf <= self.clock:
                continue
            watched = {z.zone_id: z for z in owner.zones}
            watched.update(owner.context_watches)
            for z in watched.values():
                if z.kind == 'RANGE_POI' or z.known_at > c.open_time or z.invalidated_at:
                    continue
                if c.low <= z.high and c.high >= z.low:
                    first = z.first_test is None
                    new_visit = z.last_native_test_at != c.open_time
                    if new_visit:
                        z.test_count += 1
                        z.visit_started_at = c.close_time
                    z.last_test = z.last_native_test_at = c.close_time
                    if first:
                        z.first_test = c.close_time
                    if first or (new_visit and z.kind == 'ORDER_BLOCK'):
                        touches.append((tf, z))
        return touches

    def advance(self, tf, index):
        super().advance(tf, index)
        if tf == self.clock and tf != 5:
            c = self.series[tf].candles[index]
            for htf, z in self._touches(c):
                if z.invalidated_at or z.kind == 'FVG':
                    continue
                for hh, ll in self.policy['mappings']:
                    if hh == htf:
                        visit = max(1, z.test_count)
                        pid = self.registry.assign(self.symbol, hh, z, visit, c.close_time)
                        self.contexts.append(Context(hh, ll, z, c.close_time, visit, pid))
            self._observe_sfp_open(c)

    def evaluate(self, now, changed_tfs):
        start = len(self.signals)
        for z, htf, ltf in self._pending_ranges:
            if z.invalidated_at is None:
                self._range_signal(z, htf, ltf, z, now, 'RANGE_CONSERVATIVE_RETEST')
        self._pending_ranges = []
        for htf, ltf in self.policy['mappings']:
            if ltf in changed_tfs:
                for q in self.direct_candidates[ltf].values():
                    self._direct(htf, ltf, q, now)
            if htf in changed_tfs:
                for q in self.direct_candidates[htf].values():
                    self._direct(htf, ltf, q, now, entry_tf=htf)
                self._range_aggressive(htf, now)
        for context in self.contexts:
            if context.ltf in changed_tfs and context.poi.kind != 'RANGE_POI':
                self._conservative(context, now)
        self._finalize_ready(start, now)


def actual_setup_tf(signal):
    e = signal.evidence
    if 'actual_setup_tf' in e:
        return e['actual_setup_tf']
    if e['htf_poi']['zone_id'] == e['ltf_poi']['zone_id']:
        return e['entry_zone_tf']
    return signal.htf


def portfolio_signal(signal, clock, mode=EngineMode.BACKTEST):
    """Typed source-proof adapter; legacy field names retain their real meaning
    in evidence. sfp_time is real raid observation, bos_time is real typed source
    confirmation (which can be a DS reclaim or OB formation, not a claimed BOS).
    """
    from datetime import datetime
    e = signal.evidence
    raid_at = e['causal_raid_event_time']
    proof_at = e['source_confirmation_known_at']
    raid_at = datetime.fromisoformat(raid_at) if isinstance(raid_at, str) else raid_at
    proof_at = datetime.fromisoformat(proof_at) if isinstance(proof_at, str) else proof_at
    return StrategySignal(signal.signal_id, signal.symbol, actual_setup_tf(signal), clock,
                          Direction.LONG if signal.direction == 'LONG' else Direction.SHORT,
                          signal.known_at, raid_at, proof_at, 'READY_FOR_VIRTUAL_ENTRY', 100,
                          ('ALL_REGISTERED_SOURCE_AND_MEDIUM_GATES_PASSED',),
                          entry_zone=PriceZone(signal.entry, signal.entry), optimal_entry=signal.entry,
                          stop_loss=signal.stop, targets=signal.targets, mode=mode,
                          entry_policy='REAL_SOURCE_RESTING_QUOTE', score_policy='BINARY_GATES_NOT_FITTED_QUALITY_SCORE',
                          entry_geometry_ready_time=signal.known_at, levels_known_at=signal.known_at,
                          source_qualification_known_at=signal.known_at,
                          source_poi_kind=signal.poi_type, source_entry_path=signal.setup_type,
                          source_qualification_evidence=(evidence_json(e),))


class MediumTermPortfolio(VirtualPortfolio):
    def __init__(self, *, anti_scalp_enabled=True, **kwargs):
        super().__init__(**kwargs)
        self.anti_scalp_enabled = anti_scalp_enabled
        self.source_signals = {}
        self.anti_scalp_admission_rejections = []

    def _admit(self, signal, candle, *, intrabar=False):
        source = self.source_signals[signal.signal_id]
        e = source.evidence
        s = sign(source.direction)
        if intrabar:
            if not (s * (candle.open - signal.optimal_entry) > 0
                    and candle.low <= signal.optimal_entry <= candle.high):
                return False
        elif not (signal.entry_zone.low <= candle.open <= signal.entry_zone.high
                  and s * (candle.open - signal.optimal_entry) <= 0):
            return super()._admit(signal, candle, intrabar=False)
        # A resting quote is the pre-entry reference; no future HIGH/LOW or
        # duration is passed to the decision. OPEN is observable before entry.
        reference = signal.optimal_entry if intrabar else candle.open
        d = check_anti_scalp(direction=source.direction, entry=reference, target=source.targets[0],
                             setup_tf=actual_setup_tf(source), context_tf=e['macro_context_tf'],
                             main_setup_valid=e['main_setup_valid'], context_valid=True,
                             target_known_before_entry=source.known_at <= candle.open_time,
                             policy=AntiScalpPolicy(self.policy.fee_fraction, self.policy.slippage_fraction,
                                                    e['anti_scalp']['minimum_edge_cost_ratio']))
        if self.anti_scalp_enabled and not d.allowed:
            self.anti_scalp_admission_rejections.append(dict(signal_id=signal.signal_id,
                                                            known_at=candle.open_time, **d.evidence()))
            self._log(candle.open_time, signal, 'VIRTUAL_ENTRY_BLOCKED', d.reason)
            self.consumed_ids.add(signal.signal_id)
            return True
        return super()._admit(signal, candle, intrabar=intrabar)

    def source_step(self, bars, signals=(), cancellations=(), exit_events=()):
        updates = []
        for s in signals:
            self.source_signals[s.signal_id] = s
            updates.append(portfolio_signal(s, int((bars[s.symbol].close_time - bars[s.symbol].open_time).total_seconds() / 60), self.mode))
        for c in cancellations:
            s = self.source_signals.get(c['signal_id'])
            if s is not None and s.signal_id in self.pending:
                original = portfolio_signal(s, self.pending[s.signal_id].ltf_minutes, self.mode)
                updates.append(replace(original, event_time=c['known_at'], status='INVALIDATED',
                                       invalidation_reasons=(c['reason'],)))
        super().step(bars, updates)
        for event in exit_events:
            s = self.source_signals.get(event['signal_id'])
            if s is None:
                continue
            position = self.positions.get(s.symbol)
            if position is not None and position.signal.signal_id == s.signal_id:
                self._close_fraction(position, position.remaining_fraction, event['price'],
                                     event['known_at'], 'STRUCTURAL_' + event['reason'])
        # Structural exits occur at this observable CLOSE; update the same NAV
        # record rather than funding an earlier same-bar OPEN admission.
        if self.equity_curve:
            self.equity_peak = max(self.equity_peak, self.equity)
            dd = max(0, (self.equity_peak - self.equity) / self.equity_peak)
            self.max_drawdown = max(self.max_drawdown, dd)
            self.equity_curve[-1].update(balance=self.balance, equity=self.equity,
                                          unrealized_pnl=self.unrealized_pnl, realized_pnl=self.realized_pnl,
                                          fees_paid=self.fees_paid, slippage_cost=self.slippage_cost,
                                          open_positions=len(self.positions), drawdown=dd,
                                          drawdown_absolute=self.equity_peak-self.equity,
                                          aggregate_stop_risk=self.aggregate_stop_risk,
                                          allocated_margin=self.allocated_margin,
                                          available_equity=self.available_equity)
        for s in signals:
            if s.signal_id in self.trades:
                self.trades[s.signal_id]['source_setup'] = s.setup_type
