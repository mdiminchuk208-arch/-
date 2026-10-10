"""Causal global physical IDs, independent of quote, stop and future execution."""
from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from dataclasses import replace
from datetime import datetime, timedelta

from crypto_bot.strategy.source_pdf_native import evidence_json


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value,str) else value


def canonical_physical_signals(signals, policy):
    """Assign once in READY chronology; never merge/rewrite a past assignment.

    Local-zone first test is shared across parent/pattern/range contexts. Known
    native formation aliases share a representative when both their time and
    price intervals overlap. Existing HTF-context aliases remain effective.
    Global assignment precedes family filtering and every execution outcome.
    """
    rank={p:i for i,p in enumerate(policy['entry_tie_precedence'])}
    ordered=sorted(signals,key=lambda r:(r.known_at,rank[r.evidence['path_id']],-r.htf,r.ltf,
                                       policy['symbol_priority'].index(r.symbol),r.signal_id))
    locals_,contexts,anchors={}, {}, {}
    end_keys,max_width={},{}
    result,claims=[],[]
    for r in ordered:
        e=json.loads(evidence_json(r.evidence));q=e['ltf_poi'];tf=e['entry_zone_tf']
        old=e['physical_opportunity_id'];context=(r.symbol,r.direction,old)
        local=(r.symbol,r.direction,tf,q['zone_id'])
        raid=q.get('raid');end=instant(raid['known_at'] if raid else q['formed_at'])
        start=end-timedelta(minutes=tf*(3 if q['kind']=='FVG' else 1))
        namespace=(r.symbol,r.direction)
        keys=end_keys.get(namespace,[])
        lower=bisect_right(keys,start)
        upper=bisect_left(keys,end+max_width.get(namespace,timedelta(0)))
        nearby=sorted(anchors.get(namespace,[])[lower:upper],key=lambda a:a['causal_order'])
        prior=next((a for a in nearby
                    if ((q['kind']=='RANGE_POI' and a['kind']=='RANGE_POI' and r.entry==a['boundary'])
                        or (q['kind']!='RANGE_POI' and a['kind']!='RANGE_POI'))
                    and max(start,a['start'])<min(end,a['end'])
                    and max(q['low'],a['low'])<=min(q['high'],a['high'])),None)
        if local in locals_:
            pid=locals_[local];reason='SAME_NATIVE_LOCAL_ZONE_FIRST_TEST'
        elif context in contexts:
            pid=contexts[context];reason='SAME_ALREADY_KNOWN_HTF_PHYSICAL_CONTEXT'
        elif prior:
            pid=prior['physical_opportunity_id'];reason='KNOWN_NATIVE_FORMATION_TIME_PRICE_ALIAS'
        else:
            pid=old;reason='FIRST_CAUSAL_READY_PHYSICAL_REPRESENTATIVE'
        locals_.setdefault(local,pid);contexts.setdefault(context,pid)
        if not prior:
            records=anchors.setdefault(namespace,[]);keys=end_keys.setdefault(namespace,[])
            position=bisect_right(keys,end)
            records.insert(position,{'start':start,'end':end,'low':q['low'],
                'high':q['high'],'kind':q['kind'],'boundary':r.entry,
                'known_at':r.known_at,'physical_opportunity_id':pid,'causal_order':len(claims)})
            keys.insert(position,end)
            max_width[namespace]=max(max_width.get(namespace,timedelta(0)),end-start)
        e['physical_context_id']=old
        e['physical_opportunity_id']=pid
        e['physical_identity_known_at']=r.known_at.isoformat()
        e['physical_identity_rule']='FIRST_CAUSAL_READY_GLOBAL_LOCAL_ZONE_AND_KNOWN_FORMATION_ALIAS'
        result.append(replace(r,evidence=e))
        claims.append({'signal_id':r.signal_id,'known_at':r.known_at,'physical_context_id':old,
                      'physical_opportunity_id':pid,'entry_zone_tf':tf,'entry_zone_id':q['zone_id'],
                      'reason':reason,'past_IDs_rewritten':False,'future_outcomes_used':False,
                      'trade_entry_allowed':False})
    return result,claims
