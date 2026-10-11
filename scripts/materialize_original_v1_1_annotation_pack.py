"""Materialize a bounded blinded batch. Never expose candles after its decision."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_financial_data import ROOT, checksum, save

PACK=ROOT/'docs/original_v1_1_evidence_adapter_v2/BLINDED_QUALITATIVE_ANNOTATION_PACK'


def read_prefix(path,at):
    with gzip.open(path,'rt') as stream:
        for line in stream:
            row=json.loads(line)
            known=row.get('known_at')
            if type(known) is not int:
                raise ValueError('Missing known time')
            if known<=at:
                if row.get('completed_at',known)>at:
                    raise ValueError('Uncompleted/future prefix row')
                no_outcomes(row)
                yield row


def materialize(reference,root=PACK):
    no_outcomes(reference)
    at=reference['decision_at']; views={}; objects={}
    for tf,view in reference['views'].items():
        candles=list(read_prefix(root/view['candles_file'],at))
        if len(candles)!=view['completed_bar_count'] or view['cutoff']!=at:
            raise ValueError('Known-prefix view/count mismatch')
        views[tf]=candles
        objects[tf]=list(read_prefix(root/f'objects/{reference["symbol"]}_{tf}.jsonl.gz',at))
    result={'candidate':reference,'completed_candles':views,'structural_objects':objects,
            'annotation_protocol':'QUALITATIVE_EVIDENCE_ANNOTATION_PROTOCOL_v1.md',
            'states':['PASS','FAIL','UNKNOWN'],'trade_entry_allowed':False}
    no_outcomes(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--batch',type=int,help='1-based, chronological reference blocks of 100')
    group.add_argument('--candidate-id',help='Materialize one candidate lazily')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (args.batch is not None and args.batch<1) or args.output.exists():
        raise SystemExit('Positive batch and new output path required')
    lo=(args.batch-1)*100 if args.batch else 0; hi=lo+100; selected=[]
    with gzip.open(PACK/'candidates.jsonl.gz','rt') as f:
        for i,line in enumerate(f):
            r=json.loads(line)
            if (args.candidate_id and r['candidate_id']==args.candidate_id) or (args.batch and lo<=i<hi):
                selected.append(r)
            if (args.candidate_id and selected) or (args.batch and i>=hi):
                break
    if not selected:
        raise SystemExit('Batch outside annotation cohort')
    args.output.mkdir(parents=True)
    for ref in selected:
        save(args.output/(ref['candidate_id']+'.json'),materialize(ref))
    save(args.output/'receipt.json',{'batch':args.batch,'candidate_id':args.candidate_id,'candidates':len(selected),
        'pack_sha256':checksum(PACK/'candidates.jsonl.gz'),'ANNOTATION_NO_OUTCOME_LEAKAGE':'PASS',
        'trade_entry_allowed':False})


if __name__=='__main__':
    main()
