"""Indexed offline replay of the existing, causal source-conservative signals.

Structural events are append-only products of analyze_market. Their *knowledge*
time is the close of their indexed candle, including SFP events labelled OPEN.
Only resolved transitions and confirmed levels are exposed to signal construction.
Range events use the same causal automatic boundary proof as reference snapshots.
This index never accepts manual reviews or promotes future range outcomes.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict, Counter
from dataclasses import replace
from heapq import heappush, heappop

from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import AutoLevelPolicy, FreshnessIndex, derive_automatic_levels, ob_impulse_window
from crypto_bot.strategy.market_analysis import analyze_market, MarketEventKind, TrendState, LiquidityState
from crypto_bot.strategy.mtf_sfp import (link_sfp_formations_to_ltf_bos,
    MtfSfpStatus, cluster_entry_search_opportunities, _attach_entry_geometry)
from crypto_bot.strategy.replay import EngineMode, opportunity_key, signals_from_opportunities
from crypto_bot.strategy.range_engine import augment_market_report_with_range_sfps
from crypto_bot.strategy.trade_plan import PriceZone


def _validate_series(candles, minutes):
    for i, candle in enumerate(candles):
        if (not candle.is_closed or candle.low <= 0 or
            (candle.close_time-candle.open_time).total_seconds() != minutes*60 or
            (i and candle.open_time != candles[i-1].close_time)):
            raise ValueError('historical index requires contiguous positive closed candles')


def indexed_signal_updates(histories, *, symbol, htf_minutes=60, ltf_minutes=5,
                           mode='BACKTEST', auto_level_policy=None):
    """Return changes only, equivalent to evaluate_snapshot's signal state changes.

Indexing the entire offline input is permitted solely for append-only structural
facts. Future invalidations, context links, transition resolutions, OB touches and
POIs must each wait for their own observation close. No price/fill selection uses
future information. Tests compare every close with independent prefix analysis.
"""
    mode = EngineMode(mode)
    if not 0 < ltf_minutes < htf_minutes:
        raise ValueError('0 < LTF < HTF required')
    if auto_level_policy is not None and not isinstance(auto_level_policy, AutoLevelPolicy):
        raise ValueError('automatic levels require an AutoLevelPolicy')
    ltf, htf = tuple(histories[ltf_minutes]), tuple(histories[htf_minutes])
    _validate_series(ltf, ltf_minutes)
    _validate_series(htf, htf_minutes)
    if not ltf or not htf:
        raise ValueError('both historical timeframes are required')
    lr = analyze_market(ltf, timeframe_minutes=ltf_minutes)
    hr = analyze_market(htf, timeframe_minutes=htf_minutes)
    lr, lrange = augment_market_report_with_range_sfps(ltf, lr)
    hr, hrange = augment_market_report_with_range_sfps(htf, hr)
    mtf = link_sfp_formations_to_ltf_bos(hr, lr, htf_minutes=htf_minutes,
        ltf_minutes=ltf_minutes, ltf_observation_start=ltf[0].open_time,
        ltf_observation_end=ltf[-1].close_time)
    confirmed = [c for c in mtf.candidates if c.status == MtfSfpStatus.LTF_BOS_CONFIRMED]
    groups = defaultdict(list)
    for c in confirmed:
        key = (c.ltf_bos_event_time, c.expected_direction.value, c.ltf_bos_level_price)
        groups[key].append(c)
    transitions = {(t.bos_index, t.bos_time): t for t in lr.structure_transition_diagnostics}
    levels = {level.level_id: level for level in lr.levels}
    raw_by_index = defaultdict(list)
    for event in lr.events:
        if event.kind in (MarketEventKind.LOW_LIQUIDITY_TAKEN, MarketEventKind.HIGH_LIQUIDITY_TAKEN):
            raw_by_index[event.candle_index].append(event)
    bos_events = {(e.candle_index, e.event_time): e for e in lr.events if e.kind in (
        MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS)}
    ltf_closes, htf_closes = [c.close_time for c in ltf], [c.close_time for c in htf]
    freshness = FreshnessIndex((htf, ltf)) if auto_level_policy is not None else None
    # Every schedule entry represents a fact observed at that close, not an entry.
    queue, scheduled, counter, current_time = [], set(), 0, None
    def schedule(when, key):
        nonlocal counter
        if current_time is not None and when <= current_time:
            return  # A newly discovered watch cannot rewind the observation clock.
        if when > ltf[-1].close_time or (when, key) in scheduled:
            return
        if when not in close_indices:
            return
        scheduled.add((when, key))
        counter += 1
        heappush(queue, (when, counter, key))
    close_indices = {when: i for i, when in enumerate(ltf_closes)}
    for key, contexts in groups.items():
        for c in contexts:
            schedule(max(htf[c.htf_sfp_candle_index].close_time, c.ltf_bos_event_time), key)
            if c.sfp_invalidation_event_time is not None:
                schedule(c.sfp_invalidation_event_time, key)
        t = transitions.get((contexts[0].ltf_bos_candle_index, contexts[0].ltf_bos_event_time))
        if t is not None and t.resolved_time is not None:
            schedule(t.resolved_time, key)
    cached_auto, watches, signatures, updates = {}, {}, {}, []
    automatic_evaluations = 0
    while queue:
        as_of, _, key = heappop(queue)
        current_time = as_of
        contexts = groups[key]
        available = []
        for c in contexts:
            if max(htf[c.htf_sfp_candle_index].close_time, c.ltf_bos_event_time) > as_of:
                continue
            if c.sfp_invalidation_event_time is not None and c.sfp_invalidation_event_time > as_of:
                c = replace(c, sfp_invalidation_event_time=None, sfp_invalidation_candle_index=None,
                            sfp_invalidation_close_price=None)
            available.append(c)
        if not available:
            continue
        n, nh = bisect_right(ltf_closes, as_of), bisect_right(htf_closes, as_of)
        bos_index = available[0].ltf_bos_candle_index
        transition = transitions.get((bos_index, available[0].ltf_bos_event_time))
        visible_transition = (transition if transition is not None and
            transition.resolved_time is not None and transition.resolved_time <= as_of else None)
        needed = {available[0].ltf_bos_level_id}
        visible_events = [bos_events[(bos_index, available[0].ltf_bos_event_time)]]
        if visible_transition is not None:
            needed.update(x for x in (visible_transition.selected_anchor_level_id,
                                     visible_transition.selected_correction_level_id) if x is not None)
            anchor = levels.get(visible_transition.selected_anchor_level_id)
            if anchor is not None:
                adverse = 'low' if available[0].expected_direction == Direction.LONG else 'high'
                origins = [level for level in lr.levels if level.side == adverse
                           and level.price == visible_transition.broken_extreme_price
                           and level.swing_index <= bos_index and level.confirmed_index <= bos_index]
                origin = max(origins, key=lambda level:(level.swing_index,level.confirmed_index,level.level_id)) if origins else None
                if origin is not None:
                    needed.add(origin.level_id)
                for index in range(origin.swing_index if origin is not None else bos_index+1, anchor.swing_index+1):
                    visible_events.extend(raw_by_index[index])
                needed.update(e.level_id for e in visible_events)
        # Only fields read by the shared geometry/detector are included. Lifecycle
        # values of these immutable price references are not consumed by either.
        relevant_levels = tuple(replace(levels[i], liquidity_state=LiquidityState.ACTIVE,
            liquidity_taken_index=None, liquidity_resolved_index=None, bos_broken_index=None,
            sweep_episode_id=None) for i in sorted(needed) if levels[i].confirmed_index < n)
        prefix_report = replace(lr, candle_count=n, levels=relevant_levels,
            events=tuple(e for e in visible_events if e.candle_index < n), sweep_episodes=(),
            structure_transition_diagnostics=(visible_transition,) if visible_transition else (),
            trend_state_segments=(), final_trend=TrendState.UNKNOWN)
        htf_report = replace(hr, candle_count=nh, levels=(), events=(), sweep_episodes=(),
            structure_transition_diagnostics=(), trend_state_segments=(), final_trend=TrendState.UNKNOWN)
        candidates, opportunities = cluster_entry_search_opportunities(available)
        opportunities = _attach_entry_geometry(opportunities, prefix_report)
        opp = opportunities[0]
        ident = opportunity_key(symbol, htf_minutes, ltf_minutes, opp)
        invalid = all(c.sfp_invalidation_event_time is not None for c in available)
        result_map = {}
        if auto_level_policy is not None and opp.entry_search_allowed and opp.entry_geometry_ready_time is not None and not invalid:
            if key not in watches:
                touched = []
                for index in ob_impulse_window(prefix_report, opp, n) or ():
                    a, b, c = ltf[index-1:index+2]
                    colors = ((a.close < a.open and b.close > b.open) if opp.expected_direction == Direction.LONG
                              else (a.close > a.open and b.close < b.open))
                    if not colors or not (min(b.open,b.close) <= min(a.open,a.close) and
                        max(b.open,b.close) >= max(a.open,a.close) and abs(b.close-b.open) > abs(a.close-a.open)):
                        continue
                    # A broad watch is conservative: a false-positive watch only
                    # recalculates unchanged blockers; it never admits a position.
                    known_at = max(c.close_time, opp.ltf_bos_event_time)
                    touch = next((d.close_time for d in ltf[index+2:]
                                  if d.close_time > known_at and d.low <= a.high and d.high >= a.low), None)
                    if touch is not None:
                        touched.append(touch)
                        schedule(touch, key)
                watches[key] = touched
            if key not in cached_auto or as_of in watches[key] or cached_auto[key].evidence:
                cached_auto[key] = derive_automatic_levels(htf[:nh], ltf[:n], htf_report,
                    prefix_report, opp, as_of=as_of, policy=auto_level_policy, freshness_index=freshness)
                automatic_evaluations += 1
            result_map[ident] = cached_auto[key]
            if cached_auto[key].evidence:
                # A missing target cannot become fresh on an unchanged history.
                # Reconsider newly CLOSED HTF seeds, OB first touches (above),
                # and the selected targets' first future touches. A watch only
                # schedules observation at its own close; it never admits early.
                if nh < len(htf):
                    schedule(htf[nh].close_time, key)
                if freshness is not None:
                    for evidence in cached_auto[key].evidence:
                        if evidence.kind.startswith('TARGET_POI_'):
                            touch = freshness.first_touch(PriceZone(*evidence.prices), as_of, ltf[-1].close_time)
                            if touch is not None:
                                schedule(touch, key)
        signals = signals_from_opportunities(opportunities, {c.candidate_id:c for c in candidates},
            htf_report, prefix_report, htf[:nh], ltf[:n], symbol=symbol, as_of=as_of,
            htf_minutes=htf_minutes, ltf_minutes=ltf_minutes, mode=mode,
            auto_level_policy=auto_level_policy, automatic_results=result_map)
        for signal in signals:
            signature = replace(signal, event_time=ltf[0].close_time)
            if signatures.get(signal.signal_id) != signature:
                updates.append(signal)
                signatures[signal.signal_id] = signature
    updates.sort(key=lambda s:(s.event_time, s.bos_time, s.direction.value, s.signal_id))
    metadata = dict(structure_events={str(ltf_minutes):dict(Counter(e.kind.value for e in lr.events)),
                                     str(htf_minutes):dict(Counter(e.kind.value for e in hr.events))},
                    sfp_bos_links=len(confirmed), automatic_evaluations=automatic_evaluations,
                    range_episodes={str(ltf_minutes):dict(Counter(e.status for e in lrange.sweep_episodes)),
                                    str(htf_minutes):dict(Counter(e.status for e in hrange.sweep_episodes))},
                    range_sfp_events={str(ltf_minutes):lrange.sfp_formation_count,
                                      str(htf_minutes):hrange.sfp_formation_count},
                    index_policy='CANDLE_CLOSE_KNOWLEDGE_GATES_CAUSAL_AUTOMATIC_RANGE')
    return tuple(updates), metadata
