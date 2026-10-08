"""Explain every real READY that did not become a virtual fill.

The first withdrawal/admission block after an actual queued READY is the terminal
entry reason. A later HTF invalidation must not replace this earlier cause.
Deferrals are observations, not immediate terminal rejections of a resting limit.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def audit(root):
    signals=[json.loads(line) for line in (root/'signals.jsonl').read_text().splitlines()]
    ready={s['signal_id']:s for s in signals if s['status']=='READY_FOR_VIRTUAL_ENTRY'}
    trades={t['signal_id']:t for line in (root/'trades.jsonl').read_text().splitlines() if (t:=json.loads(line))}
    records={key:dict(signal_id=key,symbol=s['symbol'],direction=s['direction'],
        entry_zone=s['entry_zone'],limit_price=s['optimal_entry'],ready_time=s['event_time'],
        deferrals=0,first_deferral=None,first_terminal=None,terminal_reason=None) for key,s in ready.items()}
    pending=set()
    for line in (root/'decisions.jsonl').read_text().splitlines():
        d=json.loads(line);key=d['signal_id']
        if key not in records:continue
        record=records[key]
        if d['action']=='SETUP_READY':pending.add(key)
        elif d['action']=='VIRTUAL_ENTRY_DEFERRED':
            record['deferrals']+=1
            if record['first_deferral'] is None:record['first_deferral']=d
        elif key in pending and d['action'] in ('SETUP_WAITING','SETUP_INVALIDATED','SETUP_REJECTED','VIRTUAL_ENTRY_BLOCKED'):
            if record['first_terminal'] is None:
                record['first_terminal']=d
                reason=d['reason']
                record['terminal_reason']=('LIMIT_NOT_FILLED_BEFORE_OB_FIRST_TEST_CONSUMED'
                    if 'OB_FIRST_TEST_ALREADY_CONSUMED' in reason else
                    'ENTRY_LEVEL_EVIDENCE_WITHDRAWN' if d['action']=='SETUP_WAITING' else reason)
            pending.discard(key)
        elif d['action']=='VIRTUAL_ENTRY':pending.discard(key)
    for key,record in records.items():
        if key in trades:
            record['terminal_reason']='VIRTUAL_TRADE_'+trades[key]['status']
        elif record['terminal_reason'] is None:
            record['terminal_reason']='PRICE_NOT_FILLED_BEFORE_DATA_END'
    return dict(ready=len(records),entries=len(trades),
                counts=dict(Counter(r['terminal_reason'] for r in records.values())),
                records=list(records.values()),trade_entry_allowed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--funnel',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    result=audit(args.run);by_id={r['signal_id']:r for r in result['records']}
    rows=json.loads((args.funnel/'setup_first_rejections.json').read_text())
    for row in rows:
        if row['first_reject_stage']=='virtual entry':
            row['first_rejection']=by_id[row['signal_id']]['terminal_reason']
            row['entry_first_terminal']=by_id[row['signal_id']]['first_terminal']
    reasons=Counter(r['first_rejection'] for r in rows)
    (args.output/'entry_audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (args.output/'setup_first_rejections.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n')
    (args.output/'funnel.json').write_bytes((args.funnel/'funnel.json').read_bytes())
    summary=json.loads((args.funnel/'summary.json').read_text());summary['rejections']=dict(reasons)
    summary['entry_policy']='FIRST_WITHDRAWAL_OR_ADMISSION_BLOCK_AFTER_QUEUED_READY_LATER_INVALIDATION_CANNOT_REPLACE_IT'
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(result['counts'])


if __name__=='__main__':main()
