"""Preregistered process-local sensitivity; never edits the frozen source tree."""
from __future__ import annotations

from bisect import bisect_right
from contextlib import contextmanager
from dataclasses import replace

from crypto_bot.common.models import Direction
from crypto_bot.strategy import auto_levels, historical_replay, trade_plan
from crypto_bot.strategy.auto_levels import AutoLevelPolicy


STRUCTURAL_VARIANTS = {
    'BASE': {},
    'AGGRESSION_055': {'min_body_fraction': .55},
    'AGGRESSION_065': {'min_body_fraction': .65},
    'ENGULF_105': {'min_engulf_body_ratio': 1.05},
    'FRESH_EXCLUSIVE_WICK': {'touch': 'EXCLUSIVE_WICK'},
    'FRESH_BODY': {'touch': 'BODY'},
    'OTE_SHALLOW_0700': {'shallow': .700},
    'OTE_SHALLOW_0710': {'shallow': .710},
    'OTE_DEEP_0785': {'deep': .785},
    'OTE_DEEP_0795': {'deep': .795},
    'LIMIT_INTERIOR_MIDPOINT': {'midpoint': True},
}


def touch_variant(index, zone, after, cutoff, semantics):
    begin,end=bisect_right(index.closes,after),bisect_right(index.closes,cutoff)
    def find(node,left,right):
        if right<=begin or end<=left:
            return None
        # Wick bounds conservatively enclose bodies too. Aggregates are read
        # only for nodes wholly inside the historical query, as in baseline.
        if begin<=left and right<=end and (index.lows[node]>zone.high or index.highs[node]<zone.low):
            return None
        if right-left==1:
            candle=index.candles[left]
            low,high=(sorted((candle.open,candle.close)) if semantics=='BODY' else (candle.low,candle.high))
            touches=(low<zone.high and high>zone.low if semantics=='EXCLUSIVE_WICK' else low<=zone.high and high>=zone.low)
            return candle.close_time if touches else None
        middle=(left+right)//2
        first=find(2*node,left,middle)
        return first if first is not None else find(2*node+1,middle,right)
    return find(1,0,index.capacity) if begin<end else None


@contextmanager
def isolated_variant(name, target_audit=None):
    """All patches restored even on failure; OB touch semantics stay unchanged."""
    variant=STRUCTURAL_VARIANTS[name]
    old_shallow,old_deep=trade_plan.OTE_SHALLOW,trade_plan.OTE_DEEP
    old_touch=auto_levels._TouchIndex.first_touch
    old_derive=historical_replay.derive_automatic_levels
    try:
        trade_plan.OTE_SHALLOW=variant.get('shallow',old_shallow)
        trade_plan.OTE_DEEP=variant.get('deep',old_deep)
        if 'touch' in variant:
            def touch(self,zone,after,cutoff):
                return touch_variant(self,zone,after,cutoff,variant['touch'])
            auto_levels._TouchIndex.first_touch=touch
        if variant.get('midpoint') or target_audit is not None:
            def derive(htf,ltf,hr,lr,opp,**kwargs):
                result=old_derive(htf,ltf,hr,lr,opp,**kwargs)
                if target_audit is not None and any(e.kind=='LTF_OB' for e in result.evidence):
                    direction=opp.expected_direction
                    zone=trade_plan.PriceZone(opp.entry_zone_low,opp.entry_zone_high)
                    index=kwargs['freshness_index']
                    selected=[]
                    seeds=[s for s in auto_levels._seeds(htf) if s.direction!=direction
                           and (s.zone.low>zone.high if direction==Direction.LONG else s.zone.high<zone.low)
                           and index.is_fresh(s,kwargs['as_of'])]
                    seeds.sort(key=lambda s:(s.zone.low,s.zone.high,s.known_at) if direction==Direction.LONG
                               else (-s.zone.high,-s.zone.low,s.known_at))
                    for seed in seeds:
                        if not any(auto_levels._overlap(seed.zone.low,seed.zone.high,s.zone) for s in selected):
                            selected.append(seed)
                    target_audit.append(dict(bos_time=opp.ltf_bos_event_time,direction=direction.name,
                        as_of=kwargs['as_of'],qualified_ob=True,distinct_fresh_opposing_pois=len(selected),
                        source_result=result.status,qualification_only=True))
                if variant.get('midpoint') and result.status=='READY':
                    z=result.execution_zone
                    result=replace(result,entry_reference=(z.low+z.high)/2,
                                   entry_policy='RESEARCH_ONLY_OB_OTE_INTERIOR_MIDPOINT')
                return result
            historical_replay.derive_automatic_levels=derive
        yield AutoLevelPolicy(**{k:variant[k] for k in ('min_body_fraction','min_engulf_body_ratio') if k in variant})
    finally:
        trade_plan.OTE_SHALLOW,trade_plan.OTE_DEEP=old_shallow,old_deep
        auto_levels._TouchIndex.first_touch=old_touch
        historical_replay.derive_automatic_levels=old_derive
