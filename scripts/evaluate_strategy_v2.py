"""Commit label-free TEST predictions, then open TEST once under frozen rules."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from research_strategy_v2 import model_probability

from crypto_bot.research.v2_common import (
    OUT,
    Row,
    canonical,
    digest,
    metrics,
    numerical_gate,
    read_jsonl,
    seconds,
    write_csv,
    write_json,
    write_jsonl,
)
from crypto_bot.research.v2_rules import candidate_mask, score


def probability_or_mask(rows: list[Row], rule: Row, models: dict[str, Row]) -> tuple[Any, Any]:
    if rule['kind']=='META':
        probability=model_probability(rows,models[rule['model_id']])
        return probability,probability>=rule['threshold']
    if rule['kind']=='SCORE':
        values=score(rows,rule['profile'])
        return values,values>=rule['threshold']
    mask=candidate_mask(rows,rule)
    return mask.astype(float),mask


def freeze() -> None:
    assert not (OUT/'freeze_receipt.json').exists(), 'Final freeze already exists'
    rules=json.loads((OUT/'strategy_v2_final_rules.json').read_text())
    rows=list(read_jsonl(OUT/'features_TEST.jsonl.gz'))
    models={m['model_id']:m for m in rules['models']}
    predictions=[]
    for name,r in rules['final_candidates'].items():
        values,mask=probability_or_mask(rows,r['rule'],models)
        # Changing every diagnostic/outcome-looking field cannot change predictions.
        changed=[{**r,'symbol':'MUTATED','direction':'MUTATED','status':'WIN','label_eligible':False,
                  'net_pnl':1e99,'fees':0,'slippage':0,'result':'WIN','exit_time':'2099-01-01',
                  'month':'1900-01','physical_opportunity_id':'MUTATED','signal_id':'MUTATED',
                  'READY_to_fill':0} for r in rows]
        alternate,alternate_mask=probability_or_mask(changed,r['rule'],models)
        assert np.array_equal(mask,alternate_mask) and np.array_equal(values,alternate)
        for r,v,k in zip(rows,values,mask):
            predictions.append({'candidate_name':name,'candidate_id':rules['final_candidates'][name]['candidate_id'],
                                'signal_id':r['signal_id'],'physical_opportunity_id':r['physical_opportunity_id'],
                                'admitted':bool(k),'score_or_probability':float(v),'trade_entry_allowed':False})
    write_jsonl(OUT/'frozen_TEST_predictions.jsonl.gz',predictions)
    paths=[*sorted(Path('src/crypto_bot/research').glob('*.py')),
           Path('scripts/research_strategy_v2.py'),Path('scripts/evaluate_strategy_v2.py'),
           Path('scripts/build_strategy_v2_features.py'),Path('STRATEGY_V2_RESEARCH_PROTOCOL.md'),
           OUT/'strategy_v2_final_rules.json',OUT/'validation_selection_receipt.json',OUT/'split.json',
           OUT/'features_TEST.jsonl.gz',OUT/'labels_TEST.jsonl.gz',OUT/'frozen_TEST_predictions.jsonl.gz']
    write_json(OUT/'freeze_receipt.json',{
        'status':'FROZEN_TEST_PREDICTIONS_BEFORE_LABEL_OPENING','TEST_labels_read':False,
        'hashes':{str(p):digest(p) for p in paths},'prediction_rows':len(predictions),
        'test_feature_rows_including_OPEN':len(rows),'label_and_identity_mutation_predictions':'PASS_ALL_FINAL_CANDIDATES',
        'preregistration_commit':'7fd0eb1a64595336f3be1c74306e935bb8bf3fa0',
        'train_search_commit':'1550e01','frozen_at_UTC':datetime.now(UTC).isoformat(),
        'primary_name':rules['primary_name'],'trade_entry_allowed':False})
    print('FROZEN',len(predictions),'predictions, labels unopened; commit before evaluate',flush=True)


def verify_freeze() -> tuple[Row,str]:
    receipt=json.loads((OUT/'freeze_receipt.json').read_text())
    for path,expected in receipt['hashes'].items():
        assert digest(Path(path))==expected,path
    # Last commit touching the freeze receipt must contain all identical frozen artifacts.
    commit=subprocess.check_output(['git','log','-1','--format=%H','--',str(OUT/'freeze_receipt.json')],text=True).strip()
    assert commit, 'Freeze must be committed BEFORE opening TEST'
    for path,expected in {**receipt['hashes'],str(OUT/'freeze_receipt.json'):digest(OUT/'freeze_receipt.json')}.items():
        stored=subprocess.check_output(['git','show',f'{commit}:{path}'])
        assert hashlib.sha256(stored).hexdigest()==expected,(commit,path)
    return receipt,commit


def months(rows: list[Row]) -> float:
    return (max(seconds(r['READY']) for r in rows)-min(seconds(r['READY']) for r in rows))/86400/30.4375


def test() -> None:
    _,commit=verify_freeze()
    opening=OUT/'TEST_opening_receipt.json'
    assert not opening.exists(), 'TEST has already been opened; only --resume-existing verification allowed'
    write_json(opening,{'status':'TEST_OPENED_ONCE_AFTER_COMMITTED_FREEZE','freeze_commit':commit,
                        'opened_at_UTC':datetime.now(UTC).isoformat(),'rule_selection_allowed':False,
                        'labels_sha256':digest(OUT/'labels_TEST.jsonl.gz'),'trade_entry_allowed':False})
    rules=json.loads((OUT/'strategy_v2_final_rules.json').read_text())
    features=list(read_jsonl(OUT/'features_TEST.jsonl.gz'))
    labels={r['signal_id']:r for r in read_jsonl(OUT/'labels_TEST.jsonl.gz') if r['status']=='CLOSED'}
    fs={r['signal_id']:r for r in features}
    selected: dict[str,list[Row]]=defaultdict(list)
    open_admitted: dict[str,int]=defaultdict(int)
    for p in read_jsonl(OUT/'frozen_TEST_predictions.jsonl.gz'):
        if p['admitted']:
            if p['signal_id'] in labels:
                selected[p['candidate_name']].append(labels[p['signal_id']])
            else:open_admitted[p['candidate_name']]+=1
    duration=months(features);output=[];breakdown=[];stress=[];loo=[];case_rows=[]
    for name in rules['final_candidates']:
        chosen=selected[name]
        assert len({r['physical_opportunity_id'] for r in chosen})==len(chosen)
        m=metrics(chosen,duration)
        output.append({'candidate_name':name,'candidate_id':rules['final_candidates'][name]['candidate_id'],
                       'is_frozen_primary':name==rules['primary_name'],**m,
                       'numerical_target_gate':numerical_gate(m),'censored_OPEN_admitted':open_admitted[name],
                       'provenance':'V2_SPECIFIC_DEVELOPMENT_TEST_NOT_UNTOUCHED_MARKET_OOS'})
        for multiplier in [1.,1.5,2.]:
            stress.append({'candidate_name':name,**metrics(chosen,duration,multiplier)})
        for dimension in ['direction','symbol','mapping','HTF','LTF','setup_family','month','session','weekday']:
            values=sorted({r[dimension] for r in features},key=str)
            for value in values:
                group=[r for r in chosen if fs[r['signal_id']][dimension]==value]
                breakdown.append({'candidate_name':name,'dimension':dimension,'value':value,**metrics(group)})
                if name==rules['primary_name'] and dimension in ['direction','symbol','mapping','month']:
                    other=[r for r in chosen if fs[r['signal_id']][dimension]!=value]
                    loo.append({'candidate_name':name,'excluded_dimension':dimension,'excluded_value':value,**metrics(other)})
        for r in chosen:
            case_rows.append({'candidate_name':name,**fs[r['signal_id']],**{f'outcome_{k}':v for k,v in r.items()}})
    baseline=metrics(list(labels.values()),duration)
    write_csv(OUT/'strategy_v2_oos_results.csv',output)
    write_csv(OUT/'strategy_v2_oos_breakdowns.csv',breakdown)
    write_csv(OUT/'strategy_v2_oos_friction_stress.csv',stress)
    write_csv(OUT/'strategy_v2_oos_leave_one_group_out.csv',loo)
    write_csv(OUT/'strategy_v2_oos_selected_cases.csv.gz',case_rows)
    # Describe TRAIN/VALIDATION stability under exactly the same frozen rules.
    models={m['model_id']:m for m in rules['models']};stability=[]
    for split,parts in [('TRAIN',3),('VALIDATION',2)]:
        lf={r['signal_id']:r for r in read_jsonl(OUT/f'labels_{split}.jsonl.gz') if r['label_eligible']}
        x=[r for r in read_jsonl(OUT/f'features_{split}.jsonl.gz') if r['signal_id'] in lf]
        timestamps=sorted(r['READY'] for r in x)
        boundaries=[timestamps[int(len(timestamps)*i/parts)] for i in range(1,parts)]
        for name,r in rules['final_candidates'].items():
            _,mask=probability_or_mask(x,r['rule'],models)
            for part in range(parts):
                chosen=[lf[t['signal_id']] for t,k in zip(x,mask) if k and
                        (part==0 or t['READY']>=boundaries[part-1]) and
                        (part==parts-1 or t['READY']<boundaries[part])]
                stability.append({'candidate_name':name,'split':split,'period':part+1,**metrics(chosen)})
    write_csv(OUT/'strategy_v2_frozen_period_stability.csv',stability)
    # All 16,333 are retained in the complete feature/label companion table.
    all_labels=[r for split in ['TRAIN','VALIDATION','TEST'] for r in read_jsonl(OUT/f'labels_{split}.jsonl.gz')]
    all_features={r['signal_id']:r for r in read_jsonl(OUT/'features.jsonl.gz')}
    flat=[]
    for l in sorted(all_labels,key=lambda r:(r['ready_time'],r['physical_opportunity_id'])):
        if l['status']!='CLOSED':continue
        flat.append({**all_features[l['signal_id']],
                     'diagnostic_READY_to_fill_interval_start_seconds':seconds(l['entry_interval_start'])-seconds(l['ready_time']),
                     'diagnostic_READY_to_fill_known_seconds':seconds(l['entry_interval_end'])-seconds(l['ready_time']),
                     **{f'outcome_{k}':v for k,v in l.items()}})
    write_csv(OUT/'strategy_v2_feature_outcome_table.csv.gz',flat)
    full_baseline=metrics([r for r in all_labels if r['status']=='CLOSED'])
    primary=next(r for r in output if r['candidate_name']==rules['primary_name'])
    verdict='TARGET_70_NOT_CONFIRMED'  # All supplied history is previously inspected DEVELOPMENT.
    summary={'verdict':verdict,'frozen_primary':rules['primary_name'],'primary_TEST_metrics':primary,
             'baseline_TEST_metrics':baseline,'baseline_all_16333_CLOSED':full_baseline,
             'numerical_gate':primary['numerical_target_gate'],'untouched_OOS_provenance_gate':False,
             'target_gap_percentage_points':100*(.70-(primary['WR'] or 0)),
             'TEST_CLOSED_available':len(labels),'TEST_OPEN':len(features)-len(labels),
             'TEST_months_observed':duration,'rules_selected_using':'VALIDATION_ONLY_BEFORE_COMMITTED_FREEZE',
             'limitations':['ALREADY_INSPECTED_2026_DEVELOPMENT','INDEPENDENT_CASES_NOT_SHARED_PORTFOLIO',
                            'CLOSED_SAMPLE_REQUESTED; OPEN_CENSORED_RETAINED','OHLC_MODEL_NOT_REAL_TICK_EXECUTION',
                            'MULTIPLE_TRAIN_AND_VALIDATION_SEARCH; NO_POST_TEST_TUNING'],
             'trade_entry_allowed':False}
    write_json(OUT/'TEST_summary.json',summary)
    artifacts={str(p.relative_to(OUT)):digest(p) for p in OUT.glob('strategy_v2_oos*')}
    artifacts.update({p:digest(OUT/p) for p in ['TEST_summary.json','TEST_opening_receipt.json',
                      'strategy_v2_feature_outcome_table.csv.gz','strategy_v2_frozen_period_stability.csv']})
    write_json(OUT/'TEST_completion_manifest.json',{'status':'COMPLETE_SINGLE_FROZEN_TEST',
        'freeze_commit':commit,'artifacts':artifacts,'test_open_count':1,'trade_entry_allowed':False})
    print(canonical(summary),flush=True)


def resume() -> None:
    verify_freeze()
    manifest=json.loads((OUT/'TEST_completion_manifest.json').read_text())
    assert manifest['status']=='COMPLETE_SINGLE_FROZEN_TEST'
    for path,expected in manifest['artifacts'].items():assert digest(OUT/path)==expected,path
    print('VERIFIED_EXISTING_SINGLE_TEST; NO_EVALUATION; NO_RULE_SELECTION; NO_ARTIFACT_MUTATION')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','test','resume-existing'])
    args=parser.parse_args()
    {'freeze':freeze,'test':test,'resume-existing':resume}[args.stage]()
