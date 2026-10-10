"""Verified full40 source detection reuse and causal global physical execution."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_pdf_native import evidence_json
from crypto_bot.strategy.source_physical import canonical_physical_signals
from crypto_bot.strategy.source_sfp_lifecycle import repair_sfp_candidates

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_source_permitted_bybit import (
    REPO,
    SEGMENT_FILES,
    digest,
    execute,
    instant,
    read_rows,
    verify_manifest,
    write_json,
    write_rows,
)


def verify_base(folder):
    m=verify_manifest(folder)
    lock=json.loads((folder/'run_lock.json').read_text())
    for name,h in lock['implementation'].items():
        if digest(REPO/name)!=h:raise ValueError('base detector implementation differs: '+name)
    for name,row in lock['inputs'].items():
        if digest(REPO/name)!=row['sha256']:raise ValueError('native data differs: '+name)
    for symbol in lock['policy']['symbol_priority']:
        verify_manifest(folder/'segments'/symbol)
    if len(lock['inputs'])!=40 or sum(v['candles'] for v in lock['inputs'].values())!=993575:
        raise ValueError('verified complete full40 required')
    return m,lock


def normalize_detection(source,output,policy):
    raw=[]
    for symbol in policy['symbol_priority']:
        for r in read_rows(source/'segments'/symbol/'signals.jsonl.gz'):
            raw.append(SourceSignal(**{**r,'known_at':instant(r['known_at']),
                                        'targets':tuple(r['targets']),'fractions':tuple(r['fractions'])}))
    native={(symbol,tf):[c.to_strategy_candle(tf*60000) for c in
             read_klines_csv(REPO/f'data/history/bybit/{symbol}/{tf}.csv')]
            for symbol in policy['symbol_priority'] for tf in policy['native_timeframes']}
    qualified,qualification,body_cancellations=repair_sfp_candidates(raw,native)
    signals,claims=canonical_physical_signals(qualified,policy)
    write_rows(output/'source_qualification.jsonl.gz',qualification)
    write_rows(output/'physical_claims.jsonl.gz',claims)
    by_id={r.signal_id:r for r in signals}
    segment_files=list(SEGMENT_FILES)+['physical_claims.jsonl.gz']
    for symbol in policy['symbol_priority']:
        base=source/'segments'/symbol;target=output/'segments'/symbol
        if target.exists():
            m=verify_manifest(target)
            if m['base_segment_manifest_sha256']!=digest(base/'manifest.json'):
                raise ValueError('different source segment receipt')
            continue
        target.mkdir(parents=True)
        # Preserve native detector ordering; only evidence identity fields change.
        ordered=[by_id[r['signal_id']] for r in read_rows(base/'signals.jsonl.gz') if r['signal_id'] in by_id]
        write_rows(target/'signals.jsonl.gz',(asdict(r) for r in ordered))
        sfp_ids={r.signal_id for r in ordered if r.evidence['path_id'].startswith('SFP_')}
        cancels=[r for r in read_rows(base/'cancellations.jsonl.gz') if r['signal_id'] in by_id
                 and not(r['signal_id'] in sfp_ids and r['cohort']=='CANCEL_SOURCE_POI_INVALIDATION')]
        cancels.extend(r for r in body_cancellations if r['signal_id'] in sfp_ids)
        cancels.sort(key=lambda r:(instant(r['known_at']),r['signal_id'],r['cohort']))
        write_rows(target/'cancellations.jsonl.gz',cancels)
        write_rows(target/'physical_claims.jsonl.gz',(r for r in claims if by_id[r['signal_id']].symbol==symbol))
        for name in SEGMENT_FILES:
            if name not in ('signals.jsonl.gz','cancellations.jsonl.gz'):shutil.copyfile(base/name,target/name)
        write_json(target/'manifest.json',{'status':'COMPLETE','base_segment_manifest_sha256':digest(base/'manifest.json'),
            'native_source_candidate_trade_fields_unchanged':True,'causal_SFP_qualification_and_body_lifecycle_repaired':True,
            'artifacts':{n:digest(target/n) for n in segment_files},'trade_entry_allowed':False})
    write_json(output/'physical_normalization_receipt.json',{'raw_candidate_READY':len(raw),'source_valid_READY':len(qualified),
        'canonical_physical_IDs':len({r.evidence['physical_opportunity_id'] for r in signals}),
        'signal_ids_quotes_stops_targets_known_at_unchanged':True,
        'SFP_primary_lifecycle':'NATIVE_PATTERN_AND_POI_BODY; NO_FABRICATED_NEW_KEY_FROM_OLD_BOS_LEVEL',
        'global_assignment_before_family_filtering':True,'future_outcomes_used':False,
        'base_complete_manifest_sha256':digest(source/'manifest.json'),
        'alias_claims_sha256':digest(output/'physical_claims.jsonl.gz'),'trade_entry_allowed':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume-existing',action='store_true');a=p.parse_args()
    source,output=a.source.resolve(),a.output.resolve()
    if source==output:raise ValueError('retain detector root; require separate physical root')
    base,lock=verify_base(source)
    names=['PHYSICAL_SOURCE_UNION_PROTOCOL.md','src/crypto_bot/strategy/source_physical.py',
           'scripts/run_source_permitted_physical_union.py','tests/test_source_physical.py',
           'SFP_SOURCE_LIFECYCLE_CORRECTION.md','src/crypto_bot/strategy/source_sfp_lifecycle.py',
           'tests/test_source_sfp_lifecycle.py']
    request={**lock,'implementation':{**lock['implementation'],**{n:digest(REPO/n) for n in names}},
             'base_detector':{'path':source.relative_to(REPO).as_posix(),
                              'manifest_sha256':digest(source/'manifest.json'),
                              'run_lock_sha256':digest(source/'run_lock.json'),
                              'verified_artifacts':len(base['artifacts'])},'trade_entry_allowed':False}
    code_hash=sha256(evidence_json(request['implementation']).encode()).hexdigest()
    if output.exists() and not a.resume_existing:raise ValueError('existing output needs exact --resume-existing')
    if (output/'run_lock.json').exists() and json.loads((output/'run_lock.json').read_text())!=request:
        raise ValueError('physical run lock differs; preserve root')
    if (output/'manifest.json').exists():
        verify_manifest(output)
        print(json.dumps({'resume':'VERIFIED_COMPLETE_NO_MUTATION','source_native_series':40,
                          'source_candles':993575,'physical_artifacts':len(verify_manifest(output)['artifacts']),
                          'trade_entry_allowed':False},indent=2));return
    output.mkdir(parents=True,exist_ok=True);write_json(output/'run_lock.json',request)
    normalize_detection(source,output,lock['policy'])
    (output/'selections').mkdir(parents=True,exist_ok=True)
    execute(output,lock['policy'])
    artifacts={p.relative_to(output).as_posix():digest(p) for p in sorted(output.rglob('*'))
               if p.is_file() and p!=output/'manifest.json'}
    write_json(output/'manifest.json',{'status':'COMPLETE','code_hash':code_hash,'artifacts':artifacts,
                                     'base_manifest_sha256':digest(source/'manifest.json'),'trade_entry_allowed':False})
    s=json.loads((output/'summary.json').read_text())['primary']
    print(json.dumps({'primary':'SOURCE_PERMITTED_UNION','READY':s['READY'],'FILLED':s['FILLED'],
                      'CLOSED':s['CLOSED'],'first50':s['primary'],'trade_entry_allowed':False},indent=2),flush=True)


if __name__=='__main__':main()
