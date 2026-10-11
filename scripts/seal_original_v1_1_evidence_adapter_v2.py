"""Audit evidence-only delivery, causal archives and reproducible pre-financial seal."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import subprocess
from collections import Counter
from hashlib import sha256
from pathlib import Path

from original_v1_1_evidence_adapter_v2 import no_outcomes
from original_v1_1_financial_data import ROOT, checksum, compact, load_market, save
from original_v1_1_objective_geometry_v2 import GeometryIndex, object_record
from run_original_v1_1_evidence_adapter_v2 import DEST, verify_parents

CODE=[f'scripts/{s}.py' for s in ('original_v1_1_objective_geometry_v2','original_v1_1_evidence_adapter_v2',
      'run_original_v1_1_evidence_adapter_v2','materialize_original_v1_1_annotation_pack',
      'build_original_v1_1_evidence_adapter_v2_docs','seal_original_v1_1_evidence_adapter_v2')]
CODE+=['tests/test_original_v1_1_evidence_adapter_v2.py',
       'scripts/original_v1_1_financial_data.py','scripts/original_v1_1_evidence_adapter.py']
PREREG=ROOT/'original_v1_1_financial_backtest_preregistration.json'
PREREG_SHA='881c789d937474892896ecac887f0f7848e68890b12c7cc343931f8b746dabc2'


def stream(path):
    with gzip.open(path,'rt') as f:
        for line in f:
            yield json.loads(line)


def validate(replay):
    if (DEST/'freeze_manifest.json').exists():
        raise ValueError('Frozen namespace; use --resume-existing')
    parents=verify_parents()
    assert checksum(PREREG)==PREREG_SHA
    inherited=json.loads(PREREG.read_text())['preoutcome_dependencies']
    for name,expected in inherited.items():
        assert checksum(ROOT/name)==expected
    # Compare EVERY objective output, including compressed archive bytes.
    outputs=[p for p in replay.rglob('*') if p.is_file()]
    if not outputs:
        raise ValueError('Completed replay required')
    equality={}
    for p in outputs:
        relative=p.relative_to(replay); actual=DEST/relative
        if not actual.is_file() or checksum(actual)!=checksum(p):
            raise ValueError('Replay difference '+str(relative))
        equality[str(relative)]=checksum(p)
    required=['EVIDENCE_FUNNEL.json','OBJECTIVE_EVIDENCE_CASES.jsonl.gz','OLD880_EVIDENCE_RECHECK.csv',
              'DATASET_VERIFICATION.json','PARENT_INVARIANCE.json','BREAKDOWNS.csv',
              'BLINDED_QUALITATIVE_ANNOTATION_PACK/candidates.jsonl.gz',
              'BLINDED_QUALITATIVE_ANNOTATION_PACK/BATCHING.json']
    if not all(r in equality for r in required) or len(equality)!=26:
        raise ValueError('Incomplete objective replay '+str(len(equality)))
    funnel=json.loads((DEST/'EVIDENCE_FUNNEL.json').read_text())
    records=Counter(); decisions=Counter(); gaps=Counter(); known_ok=0
    for row in stream(DEST/'OBJECTIVE_EVIDENCE_CASES.jsonl.gz'):
        no_outcomes(row)
        if row['trade_entry_allowed'] is not False or row['formation_at']>row['decision_at']:
            raise ValueError('Unsafe/noncausal case')
        records[row['category']]+=1; decisions[row['SOURCE_STRATEGY_DECISION']]+=1; gaps.update(row['missing_evidence']);known_ok+=1
    assert known_ok==176365 and records['QUALITATIVE_REQUIRED']==funnel['QUALITATIVE_REQUIRED']
    assert records['UNKNOWN']==funnel['REMAINING_UNKNOWN'] and not records['EVIDENCE_COMPLETE']
    pack=DEST/'BLINDED_QUALITATIVE_ANNOTATION_PACK'
    pack_rows=0
    for row in stream(pack/'candidates.jsonl.gz'):
        no_outcomes(row); pack_rows+=1
        assert all(v['cutoff']==row['decision_at'] and (v['last_completed_at'] is None or v['last_completed_at']<=row['decision_at']) for v in row['views'].values())
    assert pack_rows==funnel['QUALITATIVE_REQUIRED']
    object_count=0; candle_count=0
    for p in (pack/'objects').glob('*.gz'):
        last=-1
        for row in stream(p):
            no_outcomes(row); object_count+=1
            assert row['completed_at']<=row['known_at'] and last<=row['known_at']
            assert row['id']==object_record(row['kind'],row['symbol'],row['tf'],row['known_at'],row['payload'],row['source_rule_ids'])['id']
            last=row['known_at']
    for p in (pack/'candles').glob('*.gz'):
        last=-1
        for row in stream(p):
            no_outcomes(row); candle_count+=1
            assert row['open_time']<row['completed_at']<=row['known_at'] and last<row['completed_at']
            last=row['completed_at']
    data,_audit=load_market(); prefix_results=[]
    # Actual-history prefix identity check for EACH of the eight series.
    for symbol,frames in data.items():
        for tf,bars in frames.items():
            subset=bars[:len(bars)//2]; cutoff=subset[-1].end
            index=GeometryIndex(symbol,tf,subset)
            actual=index.prefix_objects(cutoff)
            old=[]
            for row in stream(pack/f'objects/{symbol}_{tf}.jsonl.gz'):
                if row['known_at']>cutoff:
                    break
                old.append(row)
            assert actual==old
            prefix_results.append({'symbol':symbol,'tf':tf,'cutoff':cutoff,'objects':len(actual),
                                   'sha256':sha256(compact(actual).encode()).hexdigest(),'status':'PASS'})
    with (DEST/'EVIDENCE_CAPABILITY_MATRIX.csv').open() as f:
        matrix=list(csv.DictReader(f))
    source=json.loads((ROOT/'docs/original_strategy_spec_v1_1/original_strategy_rule_registry_v1_1.json').read_text())
    source_ids={r['rule_id'] for r in source['rules'] if r['category']=='SOURCE_RULE'}
    assert all(set(filter(None,r['source_rule_ids'].split('|')))<=source_ids for r in matrix)
    tests=(DEST/'qa/full_unittest.log').read_text()
    match=re.search(r'Ran (\d+) tests',tests)
    assert match and int(match[1])>=748 and '\nOK\n' in tests and 'FAILED (' not in tests
    assert 'All checks passed!' in (DEST/'qa/ruff.log').read_text()
    assert 'Success: no issues found' in (DEST/'qa/mypy.log').read_text()
    assert not (DEST/'qa/compile.log').read_text().strip()
    receipt={'status':'PASS','tests':int(match[1]),'existing_tests':683,'new_tests':int(match[1])-683,
        'parents':parents,'first_preregistration_sha256':PREREG_SHA,
        'first_preregistration_dependencies':inherited,'dataset_hashes':'PASS','actual_history_prefix_checks':prefix_results,
        'complete_objective_replay_artifacts':equality,'replay_sha256_equality':'PASS',
        'objective_case_count':known_ok,'frozen_decisions':dict(decisions),'object_records_checked':object_count,
        'completed_candles_checked':candle_count,'blinded_candidates':pack_rows,'capability_matrix_rows':len(matrix),
        'SOURCE_REGISTRY_CONSISTENCY':'PASS','ANNOTATION_NO_OUTCOME_LEAKAGE':'PASS',
        'known_at_and_completion':'PASS','prefix_and_future_mutation':'PASS',
        'canonical_ID_stability':'PASS','BACKTEST_SHADOW_parity':'PASS (all six synthetic assembled source branches; causal evidence mode tests)',
        'historical_metadata_effective_dates':'PASS (unknown intervals preserved; no historical period fabricated)',
        'old_labels_imported_as_SOURCE':False,'financial_outcome_computation_in_objective_run':False,
        'trade_entry_allowed':False,'live_private_API_or_production':False,
        'code_sha256':{n:checksum(ROOT/n) for n in CODE},'READY_FOR_SECOND_FINANCIAL_BACKTEST':False}
    save(DEST/'QA_RECEIPT.json',receipt)
    print('Evidence QA PASS',receipt['tests'],'tests',len(equality),'replay artifacts',object_count,'causal objects')
    return receipt


def seal():
    path=DEST/'freeze_manifest.json'
    if path.exists():
        raise ValueError('Already frozen')
    receipt=json.loads((DEST/'QA_RECEIPT.json').read_text())
    assert receipt['status']=='PASS'
    for name,expected in receipt['code_sha256'].items():
        assert checksum(ROOT/name)==expected
    artifacts={str(p.relative_to(ROOT)):checksum(p) for p in DEST.rglob('*') if p.is_file() and p!=path}
    artifacts.update({n:checksum(ROOT/n) for n in CODE})
    artifacts.update(receipt['first_preregistration_dependencies'])
    artifacts[str(PREREG.relative_to(ROOT))]=PREREG_SHA
    assert all((ROOT/n).stat().st_size<100*1024*1024 for n in artifacts)
    save(path,{'version':'2','name':'SOURCE_FAITHFUL_HISTORICAL_EVIDENCE_ADAPTER_v2',
        'status':'PRE_FINANCIAL_EVIDENCE_FREEZE','parent_result_commit':'a49c40eda1191354ce936994455119c79010baf7',
        'strategy_commit':'43e9d7addcd427650ff856dd1fa99f78ee5c06f7','branch':'medium-term-source-research',
        'strategy_manifest_sha256':'dca962ff1f829887d0787a6329112e77f4ce714023bee85f666ed37843f2ecbb',
        'artifacts':dict(sorted(artifacts.items())),'QA_tests':receipt['tests'],'QA':'PASS',
        'second_financial_backtest_started':False,'financial_outcomes_computed':False,
        'trade_entry_allowed':False,'READY_FOR_SECOND_FINANCIAL_BACKTEST':False,
        'stop_boundary':'STOP; another financial run needs a separate explicit user command'})
    print('PRE_FINANCIAL_EVIDENCE_FREEZE',len(artifacts),'artifacts',checksum(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--validate',type=Path,help='completed objective replay directory')
    group.add_argument('--seal',action='store_true')
    args=parser.parse_args()
    if args.validate:
        validate(args.validate)
    else:
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
        if branch!='medium-term-source-research':
            raise ValueError('Research branch required')
        seal()


if __name__=='__main__':
    main()
