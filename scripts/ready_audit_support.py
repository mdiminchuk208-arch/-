"""Read-only gate diagnostics; never used to qualify signals or orders.

Predicates are evaluated on the SAME A/B/C candidate. Later predicates can be
diagnosed independently, but a failure above them still prevents qualification.
The caller compares this model with the unmodified production detector.
"""
from bisect import bisect_right
from dataclasses import asdict

from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import _seeds, _overlap
from crypto_bot.strategy.market_analysis import MarketEventKind, TrendState


CANDIDATE_GATES = (
    ('AGGRESSION', 'AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET'),
    ('IMBALANCE', 'DIRECTIONAL_IMBALANCE_NOT_CONFIRMED'),
    ('OB_OTE_AND_IMPULSE', 'OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE'),
    ('RAW_SWEEP', 'RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND'),
    ('SUPPORTING_POI', 'FRESH_PREEXISTING_HTF_POI_NOT_FOUND'),
    ('TREND_ALIGNMENT', 'ORDER_BLOCK_ASSESSMENT_BLOCKED'),
    ('OB_FRESH', 'OB_FIRST_TEST_ALREADY_CONSUMED'),
    ('STOP_GEOMETRY', 'OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE'),
)


class GateInspector:
    def __init__(self):
        self.seeds = ()
        self.htf_length = 0
        self.touch_cache = {}

    def inspect(self, htf, ltf, htf_report, ltf_report, opportunity, *, as_of, policy):
        # Input is always a closed-candle prefix. Cache contains no future facts.
        if any(c.close_time>as_of or not c.is_closed for c in (*htf,*ltf)):
            raise ValueError('diagnostics require a closed causal prefix')
        if len(htf) != self.htf_length:
            self.seeds = _seeds(htf)
            self.htf_length = len(htf)
        closes = [c.close_time for c in ltf]
        hcloses = [c.close_time for c in htf]

        def fresh(seed, cutoff):
            key = (seed.known_at, seed.zone.low, seed.zone.high)
            cached = self.touch_cache.get(key)
            if cached is not None and cached <= cutoff:
                return False
            for history, times in ((ltf, closes), (htf, hcloses)):
                for i in range(bisect_right(times, seed.known_at), bisect_right(times, cutoff)):
                    c = history[i]
                    if _overlap(c.low, c.high, seed.zone):
                        self.touch_cache[key] = min(c.close_time, cached) if cached else c.close_time
                        return False
            return True

        opp = opportunity
        levels = {l.level_id: l for l in ltf_report.levels}
        anchor = levels[opp.entry_anchor_level_id]
        transition = next(t for t in ltf_report.structure_transition_diagnostics
                          if t.transition_id == opp.entry_geometry_transition_id)
        long = opp.expected_direction == Direction.LONG
        from crypto_bot.strategy.trade_plan import PriceZone
        zone = PriceZone(opp.entry_zone_low, opp.entry_zone_high)
        lo, hi = sorted((opp.impulse_start_price, opp.impulse_end_price))
        sweep_kind = MarketEventKind.LOW_LIQUIDITY_TAKEN if long else MarketEventKind.HIGH_LIQUIDITY_TAKEN
        sweep_events = {}
        for event in ltf_report.events:
            if event.kind == sweep_kind:
                sweep_events.setdefault(event.candle_index, []).append(event)
        candidates, failures = [], set()
        color_pair_count, scanned_triples = 0, 0
        for index in range(opp.ltf_bos_candle_index + 2, min(anchor.swing_index, len(ltf) - 1)):
            scanned_triples += 1
            a, b, c = ltf[index - 1:index + 2]
            first_body, body = abs(a.close-a.open), abs(b.close-b.open)
            colors = (a.close<a.open and b.close>b.open) if long else (a.close>a.open and b.close<b.open)
            engulf = min(b.open,b.close)<=min(a.open,a.close) and max(b.open,b.close)>=max(a.open,a.close) and body>first_body
            color_pair_count += int(colors)
            if a.open_time < opp.ltf_bos_event_time or not (colors and engulf):
                continue
            sweeps = [e for e in sweep_events.get(index-1, ()) if e.event_time==a.close_time
                      and e.level_id in levels and levels[e.level_id].confirmed_time<=a.open_time
                      and levels[e.level_id].side==('low' if long else 'high')
                      and e.level_price==levels[e.level_id].price
                      and (a.low<e.level_price if long else a.high>e.level_price)]
            supporting = [s for s in self.seeds if s.direction==opp.expected_direction
                          and s.known_at<=a.open_time and _overlap(a.low,a.high,s.zone)]
            late_supporting = [s for s in self.seeds if s.direction==opp.expected_direction
                              and a.open_time<s.known_at<=as_of and _overlap(a.low,a.high,s.zone)]
            fresh_support = [s for s in supporting if fresh(s,a.open_time)]
            first_touch = next((d.close_time for d in ltf[index+2:] if d.low<=a.high and d.high>=a.low), None)
            stop = a.low if long else a.high
            truth = dict(
                AGGRESSION=body/(b.high-b.low)>=policy.min_body_fraction and body>=policy.min_engulf_body_ratio*first_body,
                IMBALANCE=c.low>a.high if long else c.high<a.low,
                OB_OTE_AND_IMPULSE=_overlap(a.low,a.high,zone) and all(lo<=d.low and d.high<=hi for d in (a,b,c)),
                RAW_SWEEP=bool(sweeps), SUPPORTING_POI=bool(fresh_support),
                TREND_ALIGNMENT=transition.resolved_trend==(TrendState.BULLISH if long else TrendState.BEARISH),
                OB_FRESH=first_touch is None,
                STOP_GEOMETRY=stop<zone.low if long else stop>zone.high,
            )
            first_failure = next((reason for gate,reason in CANDIDATE_GATES if not truth[gate]),None)
            failures.add('NO_ELIGIBLE_POST_BOS_OB')
            if first_failure:
                failures.add(first_failure)
            candidates.append(dict(
                b_index=index, known_at=c.close_time, a_open=a.open_time,
                bars=[asdict(d) for d in (a,b,c)], ob_zone=dict(low=a.low,high=a.high), stop=stop,
                body_fraction=body/(b.high-b.low), body_ratio=body/first_body,
                ote_intersection=_overlap(a.low,a.high,zone), inside_impulse=all(lo<=d.low and d.high<=hi for d in (a,b,c)),
                gates=truth, first_failure=first_failure, raw_sweep_events=[asdict(e) for e in sweeps],
                supporting_poi_candidates=len(supporting), stale_supporting_pois=len(supporting)-len(fresh_support),
                preexisting_supporting_poi_evidence=[asdict(s) for s in supporting],
                later_supporting_poi_evidence=[asdict(s) for s in late_supporting],
                fresh_supporting_pois=[asdict(s) for s in fresh_support], first_retest=first_touch,
            ))
        valid = [c for c in candidates if all(c['gates'].values())]
        # Independent target diagnosis, not qualification when no OB exists.
        opposing = [s for s in self.seeds if s.direction!=opp.expected_direction
                    and (s.zone.low>zone.high if long else s.zone.high<zone.low)]
        fresh_opposing = [s for s in opposing if fresh(s,as_of)]
        fresh_opposing.sort(key=lambda s:(s.zone.low,s.zone.high,s.known_at) if long
                            else (-s.zone.high,-s.zone.low,s.known_at))
        selected = []
        for seed in fresh_opposing:
            if not any(_overlap(seed.zone.low,seed.zone.high,x.zone) for x in selected):
                selected.append(seed)
            if len(selected)==3:
                break
        reasons = (() if len(selected)==3 else ('THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND',)) if valid else tuple(sorted(failures or {'NO_POST_BOS_OB_PATTERN'}))
        return dict(candidates=candidates, qualified_ob_count=len(valid),
                    scanned_triples=scanned_triples, color_pair_count=color_pair_count,
                    candidate_scan_start=opp.ltf_bos_candle_index+2, candidate_scan_end_exclusive=min(anchor.swing_index,len(ltf)-1),
                    anchor_swing_time=anchor.swing_time, anchor_confirmed_time=anchor.confirmed_time,
                    impulse_low=lo,impulse_high=hi, predicted_reasons=reasons,
                    predicted_ready=bool(valid) and len(selected)==3,
                    opposing_poi_count=len(opposing), stale_opposing_poi_count=len(opposing)-len(fresh_opposing),
                    selected_targets=[asdict(s) for s in selected],
                    independent_targets_available=len(selected)==3,
                    support_policy='HTF_THREE_CANDLE_GAP_POI_BACKTEST_PARAMETER')
