"""Primary-source SFP validity and pending lifecycle from closed native bars."""
from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import replace
from datetime import datetime

from crypto_bot.strategy.source_pdf_native import evidence_json, sign


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value,str) else value


def repair_sfp_candidates(signals,native):
    """No PnL inputs: qualify at READY, then reconstruct legitimate body events.

    A BOS breaks an old opposite protected level; that price is not a newly
    confirmed HL/LH. SFP uses its actual native pattern/body and entry-POI idea.
    Each future cancellation is only usable at its actual CLOSE.
    """
    close_times={k:[c.close_time for c in cs] for k,cs in native.items()}
    patterns,local_bodies={},{}
    passed,qualification,cancellations=[],[],[]
    for r in signals:
        if not r.evidence['path_id'].startswith('SFP_'):
            passed.append(r)
            continue
        e=json.loads(evidence_json(r.evidence));p=e['htf_poi'];q=e['ltf_poi'];s=sign(r.direction)
        pattern_key=(r.symbol,r.htf,p['zone_id'])
        if pattern_key not in patterns:
            key=(r.symbol,r.htf);first=bisect_right(close_times[key],instant(p['known_at']))
            extreme=p['raid']['extreme']
            patterns[pattern_key]=next((c.close_time for c in native[key][first:]
                                       if s*(c.close-extreme)<=0),None)
        invalid=patterns[pattern_key]
        if invalid is not None and invalid<=r.known_at:
            qualification.append({'signal_id':r.signal_id,'known_at':r.known_at,
                'source_body_invalidation_known_at':invalid,'status':'REJECT_SFP_INVALID_BEFORE_READY',
                'source':'SW12 p13; DOC16 P0075–87','PnL_used':False,'trade_entry_allowed':False})
            continue
        qualification.append({'signal_id':r.signal_id,'known_at':r.known_at,
            'source_body_invalidation_known_at':None,'status':'PASS_SFP_VALID_AT_READY',
            'source':'SW12 p13; DOC16 P0075–87','PnL_used':False,'trade_entry_allowed':False})
        e['former_BOS_broken_level_not_new_protected_key']=e.get('structural_thesis')
        e['structural_thesis']=None
        e['sfp_validity_at_READY']='NATIVE_PATTERN_BODY_NOT_INVALIDATED; NO_NEW_KEY_FABRICATED_FROM_BOS'
        passed.append(replace(r,evidence=e))
        local_key=(r.symbol,e['entry_zone_tf'],q['zone_id'],r.known_at)
        if local_key not in local_bodies:
            key=(r.symbol,e['entry_zone_tf']);first=bisect_right(close_times[key],r.known_at)
            boundary=q['low'] if s==1 else q['high']
            local_bodies[local_key]=next((c.close_time for c in native[key][first:]
                                        if s*(c.close-boundary)<0),None)
        events=[(t,reason) for t,reason in (
            (local_bodies[local_key],'ENTRY_POI_NATIVE_BODY_INVALIDATED'),
            (invalid,'SFP_PATTERN_NATIVE_BODY_INVALIDATED')) if t is not None]
        if events:
            when,reason=min(events,key=lambda x:(x[0],x[1]))
            cancellations.append({'signal_id':r.signal_id,'cohort':'CANCEL_SOURCE_POI_INVALIDATION',
                'known_at':when,'reason':reason,'classification':'SOURCE_RULE_WITH_NATIVE_BODY_INTERPRETATION',
                'source':'SW9 p2–10; DOC16 P0075–87; SW12 p13','trade_entry_allowed':False})
    return passed,qualification,cancellations
