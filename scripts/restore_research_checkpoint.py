"""Recover only missing frozen checkpoint cases and require their original hashes."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from research_inventory import restore_checkpoint_schema
from research_support import check_baseline
from run_historical_portfolio import canonical
from run_robustness_research import study


def restore(workers):
    repo=Path(__file__).resolve().parents[1]
    report=repo/'data/reports/robustness_research'
    lock=check_baseline(repo)
    expected=json.loads((report/'resume_original_case_fingerprints.json').read_text())
    for cohort in ('bybit','binance'):
        manifest=json.loads((report/f'{cohort}_dataset_manifest.json').read_text())
        for row in manifest['series']:
            assert sha256((repo/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
    groups=defaultdict(list)
    for name in expected:
        _,mapping,label=name.split('/')
        window,number=label.rsplit('_SEGMENT_',1)
        groups[(mapping,window)].append(int(number))

    def receipt():
        cases=[]
        for name,digest in expected.items():
            folder=report/name
            if (folder/'artifact_hashes.json').exists():
                actual=restore_checkpoint_schema(folder,digest,report/'restoration_diagnostics'/name)
                source=json.loads((folder/'summary.json').read_text())
                for path,input_digest in source['input_hashes'].items():
                    assert sha256((repo/path).read_bytes()).hexdigest()==input_digest,path
                assert source['baseline_commit']==lock['baseline_commit'],name
                cases.append(dict(case=name,status='RESTORED_EXACT',expected_fingerprint=digest,
                                  actual_fingerprint=actual,input_hashes=source['input_hashes']))
            else:
                cases.append(dict(case=name,status='MISSING',expected_fingerprint=digest))
        complete=all(row['status']=='RESTORED_EXACT' for row in cases)
        payload=dict(complete=complete,verified_at_utc=datetime.now(timezone.utc),cases=cases,
                     protected_source_config_hashes=lock['code_hashes'],
                     no_saved_stage_replayed=True,trade_entry_allowed=False)
        (report/'checkpoint_restoration_receipt.json').write_text(canonical(payload)+'\n')
        return complete

    receipt()
    for (mapping,window),numbers in sorted(groups.items()):
        cohort,htf,ltf=mapping.split('_')
        missing=[n for n in numbers if not (report/'canonical'/mapping/f'{window}_SEGMENT_{n:02}'/'artifact_hashes.json').exists()]
        if not missing:
            continue
        split=json.loads((report/f'{cohort}_temporal_split.json').read_text())
        study(cohort,repo/f'data/history/public_research/{cohort}_mirror',split,int(htf),int(ltf),
              report/'canonical'/mapping,workers=workers,windows=[window],resume_existing=True,
              segment_numbers=missing,expected_fingerprints=expected)
        receipt()
    assert receipt(),'Incomplete checkpoint recovery'
    print('All',len(expected),'original checkpoint fingerprints reproduced exactly',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.workers<1:
        parser.error('workers must be positive')
    restore(args.workers)
