"""Objective evidence run, deterministic replay and hash-only resume. No execution."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from itertools import zip_longest
from pathlib import Path

from original_strategy_executable_profile_v1 import ACTIVE, load_tree
from original_v1_1_evidence_adapter import all_proposals
from original_v1_1_evidence_adapter_v2 import (
    VERSION,
    blinded_reference,
    inspect,
    no_outcomes,
    summarize,
)
from original_v1_1_financial_data import (
    BASE,
    END,
    OUT,
    ROOT,
    checksum,
    compact,
    load_market,
    save,
    write_csv,
    write_rows,
)
from original_v1_1_objective_geometry_v2 import GeometryIndex, previous_levels

DEST = ROOT / 'docs/original_v1_1_evidence_adapter_v2'
FIRST_MANIFEST_SHA = '68d2e80fd295154526df9998ad34f36f45cfdcb1c62b886519abe1de97bc51e5'


def parent_checksum(path):
    """Hash original bytes or lossless archived CSV, no parsing/monetary calculation."""
    if path.is_file():
        return checksum(path)
    compressed=path.with_suffix(path.suffix+'.gz')
    if path.suffix!='.csv' or not compressed.is_file():
        raise FileNotFoundError(path)
    hashed=sha256()
    with gzip.open(compressed,'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            hashed.update(chunk)
    return hashed.hexdigest()


def verify_parents():
    receipt={}
    for path,sha in [(ROOT/'docs/original_strategy_spec_v1_1/freeze_manifest.json',
                      'dca962ff1f829887d0787a6329112e77f4ce714023bee85f666ed37843f2ecbb'),
                     (OUT/'result_manifest.json',FIRST_MANIFEST_SHA),
                     (ROOT/'docs/original_strategy_spec_v1/freeze_manifest.json',
                      'db8bdb8d800a48c75ec3884a1da1cece7f47da4db8cc561d12e46c8d0f168aec')]:
        if checksum(path)!=sha:
            raise ValueError('Frozen parent manifest changed '+str(path))
        manifest=json.loads(path.read_text())
        for filename,expected in manifest['artifacts'].items():
            if parent_checksum(ROOT/filename)!=expected:
                raise ValueError('Frozen artifact changed '+filename)
        receipt[str(path.relative_to(ROOT))]={'sha256':sha,'verified_artifacts':len(manifest['artifacts'])}
    return receipt


def old880(indices, metadata, tree, raw_lookup):
    with (OUT/'result/baseline880_source_decisions.csv').open() as f:
        # Outcome-free roster only. No trading outcomes or legacy evidence labels read.
        roster=[{k:r[k] for k in ('signal_id','symbol','legacy_style','profile_branch','decision_at')} for r in csv.DictReader(f)]
    wanted={r['signal_id'] for r in roster}; signals={}
    for symbol in indices:
        with gzip.open(BASE/f'detection/{symbol}/enabled/signals.jsonl.gz','rt') as f:
            for line in f:
                r=json.loads(line)
                if r['signal_id'] in wanted:
                    # Explicit identity/time projection: all machine evidence discarded.
                    signals[r['signal_id']]={'direction':r['direction'],'tf':r['evidence']['actual_setup_tf']}
    output=[]
    for old in roster:
        signal=signals[old['signal_id']]; at=int(old['decision_at']); branch=old['profile_branch']
        key=(old['symbol'],signal['tf'],branch,signal['direction'],at)
        matches=raw_lookup.get(key,[])
        status='REJECT_INACTIVE_PROFILE_BRANCH' if branch not in ACTIVE else 'UNKNOWN'
        details=None
        # Legacy id does not validate geometry. Match only exact causal raw event.
        if branch in ACTIVE:
            if len(matches)==1:
                raw={**matches[0],'candidate_id':old['signal_id'],'decision_at':at}
                details=inspect(raw,indices[old['symbol']][signal['tf']],metadata,tree)
                status=details['category']
            else:
                status='UNKNOWN'
        output.append({**old,'direction':signal['direction'],'setup_tf':signal['tf'],
            'status':status,'objective_geometry_pass':details['objective_geometry_pass'] if details else False,
            'frozen_status':details['frozen_status'] if details else ('REJECT_INACTIVE_PROFILE_BRANCH' if branch not in ACTIVE else 'WAIT_UNRESOLVED_INSTRUMENT_METADATA'),
            'raw_event_match_count':len(matches),'missing_evidence':details['missing_evidence'] if details else (['LEGACY_EVENT_SOURCE_GEOMETRY_UNPROVEN','HISTORICAL_INSTRUMENT_METADATA'] if branch in ACTIVE else []),
            'outcomes_used':False,'trade_entry_allowed':False})
    assert len(output)==880 and len({r['signal_id'] for r in output})==880
    return output


def run(output, *, replay=False):
    parents=verify_parents()
    metadata=json.loads((DEST/'HISTORICAL_INSTRUMENT_METADATA_v1.json').read_text())
    data,audit=load_market(); tree=load_tree()
    indices={s:{tf:GeometryIndex(s,tf,bars) for tf,bars in frames.items()} for s,frames in data.items()}
    rows=[]; packs=[]; raw_lookup=defaultdict(list); raw_digest=sha256(); initial_unknown=0
    # Regenerate the frozen RAW convention exactly, not historical source labels.
    with gzip.open(OUT/'result/all_raw_proposals.jsonl.gz','rt') as oldstream:
        for number,(raw,oldline) in enumerate(zip_longest(all_proposals(data),oldstream),1):
            if raw is None or oldline is None or raw!=json.loads(oldline):
                raise ValueError('Frozen raw cohort mismatch')
            raw_digest.update((compact(raw)+'\n').encode())
            raw_lookup[(raw['symbol'],raw['setup_tf'],raw['branch'],raw['direction'],raw['decision_at'])].append(raw)
            initial=raw['decision_at']; index=indices[raw['symbol']][raw['setup_tf']]
            # Fixed pre-outcome follow-up for next OPEN, not retrospective readiness.
            # One native bar completion is the earliest this archive exposes it.
            decision=initial
            if raw['branch']=='SFP':
                nxt=index.next_open(initial,END)
                if nxt is not None:
                    decision=nxt['known_at']
                initial_unknown+=1
            candidate={**raw,'formation_at':initial,'decision_at':decision}
            result=inspect(candidate,index,metadata,tree)
            rows.append(result)
            if result['category']=='QUALITATIVE_REQUIRED':
                packs.append(blinded_reference(candidate,result,indices[raw['symbol']]))
            if number%20000==0:
                print('Objective evidence',number,flush=True)
    assert len(rows)==176365
    output.mkdir(parents=True,exist_ok=True)
    write_rows(output/'OBJECTIVE_EVIDENCE_CASES.jsonl.gz',rows)
    write_rows(output/'BLINDED_QUALITATIVE_ANNOTATION_PACK/candidates.jsonl.gz',packs)
    object_counts=Counter()
    for symbol,frames in indices.items():
        for tf,index in frames.items():
            prefix=index.prefix_objects(END)
            write_rows(output/f'BLINDED_QUALITATIVE_ANNOTATION_PACK/objects/{symbol}_{tf}.jsonl.gz',prefix)
            write_rows(output/f'BLINDED_QUALITATIVE_ANNOTATION_PACK/candles/{symbol}_{tf}.jsonl.gz',
                       [b.observed(tf) for b in index.bars])
            object_counts.update(o['kind'] for o in prefix)
        write_rows(output/f'BLINDED_QUALITATIVE_ANNOTATION_PACK/previous_levels/{symbol}.jsonl.gz',
            ({'decision_at':b.end,'levels':previous_levels(data[symbol][1440],b.end)} for b in data[symbol][1440]))
    old=old880(indices,metadata,tree,raw_lookup)
    write_csv(output/'OLD880_EVIDENCE_RECHECK.csv',old,list(old[0]))
    funnel=summarize(rows)
    funnel.update(version=VERSION,initial_SFP_next_open_unavailable=initial_unknown,
        SFP_followup_policy='Next native completion exposes archived OPEN; no H/L/C used to evaluate next OPEN predicate',
        raw_cohort_sha256=raw_digest.hexdigest(),objective_objects=dict(object_counts),
        old880_counts=dict(Counter(r['status'] for r in old)),old880_metadata_WAIT=sum(r['frozen_status']=='WAIT_UNRESOLVED_INSTRUMENT_METADATA' for r in old),
        metadata_verified_periods=sum(r['verification_status']=='VERIFIED_HISTORICAL' for r in metadata['records']),
        historical_qualitative_annotations_loaded=0,ANNOTATION_NO_OUTCOME_LEAKAGE='PASS')
    breakdown=[]
    for axis in ('symbol','direction','setup_tf','branch','year'):
        groups=defaultdict(list)
        for row in rows:
            key=datetime.fromtimestamp(row['formation_at'],UTC).year if axis=='year' else row[axis]
            groups[str(key)].append(row)
        for value,group in sorted(groups.items()):
            stats=summarize(group)
            breakdown.append({'axis':axis,'value':value,**{k:stats[k] for k in ('RAW_PROPOSALS','OBJECTIVE_GEOMETRY_PASS',
                'OBJECTIVE_SOURCE_FAIL','QUALITATIVE_REQUIRED','EVIDENCE_COMPLETE','SOURCE_DECISION_READY','REMAINING_UNKNOWN')}})
    save(output/'EVIDENCE_FUNNEL.json',funnel)
    write_csv(output/'BREAKDOWNS.csv',breakdown,list(breakdown[0]))
    save(output/'DATASET_VERIFICATION.json',audit)
    save(output/'PARENT_INVARIANCE.json',parents)
    save(output/'BLINDED_QUALITATIVE_ANNOTATION_PACK/BATCHING.json',{
        'exact_candidates':len(packs),'batch_size':100,'batches':(len(packs)+99)//100,
        'last_batch_size':len(packs)%100 or (100 if packs else 0),
        'ordering':'formation_at,symbol,setup_tf,original frozen RAW stream order',
        'scope':'100 is annotation transport batch size, NOT strategy rule',
        'materializer':'scripts/materialize_original_v1_1_annotation_pack.py',
        'annotation_states':['PASS','FAIL','UNKNOWN'],'historical_annotations_supplied':0,
        'view':'complete available known-prefix; no fixed trading lookback','trade_entry_allowed':False})
    for r in packs:
        no_outcomes(r)
        assert all(v['last_completed_at'] is None or v['last_completed_at']<=r['decision_at'] for v in r['views'].values())
    print(compact({k:funnel[k] for k in ('RAW_PROPOSALS','OBJECTIVE_GEOMETRY_PASS','OBJECTIVE_SOURCE_FAIL',
        'QUALITATIVE_REQUIRED','EVIDENCE_COMPLETE','REMAINING_UNKNOWN','old880_counts')}),flush=True)
    return funnel


def verify_freeze(root):
    manifest=json.loads((root/'freeze_manifest.json').read_text())
    namespace=str(root.relative_to(ROOT))+'/'
    declared={n for n in manifest['artifacts'] if n.startswith(namespace)}
    actual={str(p.relative_to(ROOT)) for p in root.rglob('*') if p.is_file() and p.name!='freeze_manifest.json'}
    if declared!=actual:
        raise ValueError('Frozen adapter namespace membership changed')
    for path,expected in manifest['artifacts'].items():
        if checksum(ROOT/path)!=expected:
            raise ValueError('Adapter artifact changed '+path)
    verify_parents(); load_market()
    print('VERIFIED_RESUME evidence adapter v2',len(manifest['artifacts']),'artifacts; no financial computation')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume-existing',action='store_true')
    parser.add_argument('--replay-output',type=Path)
    args=parser.parse_args()
    if args.resume_existing:
        verify_freeze(DEST)
    elif args.replay_output:
        run(args.replay_output,replay=True)
    else:
        if (DEST/'EVIDENCE_FUNNEL.json').exists():
            raise SystemExit('Existing run preserved; use --resume-existing or --replay-output')
        run(DEST)


if __name__=='__main__':
    main()
