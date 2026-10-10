"""Independent completed-research audit; never selects or changes V2 rules."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path

import numpy as np
from evaluate_strategy_v2 import probability_or_mask, verify_freeze
from scipy.stats import binomtest

from crypto_bot.research.v2_common import (
    BASE,
    BASELINE,
    OUT,
    Row,
    canonical,
    digest,
    read_jsonl,
    seconds,
    write_json,
)


def close(a: float, b: float, name: str) -> None:
    assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(name,a,b)


def audit_baseline() -> Row:
    listing=subprocess.check_output(['git','ls-tree','-rz',BASELINE]).split(b'\0')
    count=0;total=0
    for record in listing:
        if not record:continue
        metadata,name=record.split(b'\t',1);mode,kind,oid=metadata.decode().split()
        assert kind=='blob',kind
        path=Path(os.fsdecode(name))
        assert path.exists(),str(path)
        size=path.stat().st_size
        h=hashlib.sha1()
        if mode=='120000':
            data=os.readlink(path).encode();h.update(f'blob {len(data)}\0'.encode());h.update(data)
        else:
            h.update(f'blob {size}\0'.encode())
            with path.open('rb') as f:
                for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
        assert h.hexdigest()==oid,str(path)
        count+=1;total+=size
    return {'status':'PASS','baseline_commit':BASELINE,'unchanged_Git_blobs':count,
            'bytes_independently_hashed':total,'all_old_source_tests_scripts_reports_and_history_unchanged':True}


def main() -> None:
    receipt,freeze_commit=verify_freeze()
    opening=json.loads((OUT/'TEST_opening_receipt.json').read_text())
    assert opening['freeze_commit']==freeze_commit
    complete=json.loads((OUT/'TEST_completion_manifest.json').read_text())
    assert complete['test_open_count']==1
    for path,expected in complete['artifacts'].items():assert digest(OUT/path)==expected,path
    split=json.loads((OUT/'split.json').read_text())
    for path,expected in split['partitions'].items():assert digest(OUT/path)==expected,path
    lock=json.loads((BASE/'run_lock.json').read_text());native_count=0
    for path,input_ in lock['inputs'].items():
        assert digest(Path(path))==input_['sha256'],path
        with Path(path).open() as f:n=sum(1 for _ in csv.DictReader(f))
        assert n==input_['candles'],path
        native_count+=n
    assert native_count==993575
    features=list(read_jsonl(OUT/'features.jsonl.gz'));fs={r['signal_id']:r for r in features}
    assert len(features)==len(fs)==len({r['physical_opportunity_id'] for r in features})==16351
    labels=[r for part in ['TRAIN','VALIDATION','TEST'] for r in read_jsonl(OUT/f'labels_{part}.jsonl.gz')]
    lf={r['signal_id']:r for r in labels};assert set(lf)==set(fs)
    closed=[r for r in labels if r['status']=='CLOSED'];assert len(closed)==16333
    tie_splits={};purge=Counter();expected_cost=0
    for f in features:
        l=lf[f['signal_id']];ready=f['READY'];tie_splits.setdefault(ready,f['split'])
        assert tie_splits[ready]==f['split']
        expected='TRAIN' if ready<split['validation_first_READY'] else 'VALIDATION' if ready<split['test_first_READY'] else 'TEST'
        assert f['split']==l['split']==expected and ready<=l['entry_interval_start']
        boundary=split['validation_first_READY'] if expected=='TRAIN' else split['test_first_READY'] if expected=='VALIDATION' else None
        eligible=l['status']=='CLOSED' and (boundary is None or l['exit_time']<boundary)
        assert eligible==l['label_eligible']==f['label_eligible']
        if l['status']=='CLOSED' and not eligible:purge[expected]+=1
        assert not f['trade_entry_allowed']
        for k in ['htf_flow_known_at','htf_structure_known_at','range_context_known_at']:
            assert f[k] is None or f[k]<=ready,(k,ready)
        for w in f['confluence_witnesses']:assert w['known_at']<=ready
        assert f['ATR_known_at']<=seconds(ready)
        assert f['external_swept_count']+f['internal_swept_count']<=f['liquidity_swept_count']
        s=1 if f['direction']=='LONG' else -1;q=f['expected_quantity']
        fee=lock['policy']['fee_rate'];slip=lock['policy']['slippage_fraction'];risk=f['planned_risk']
        entry_fill=f['entry_reference']*(1+s*slip)
        expected_net=math.fsum(fr*(s*(t*(1-s*slip)-entry_fill)-fee*(entry_fill+t*(1-s*slip)))
                              for fr,t in zip(f['target_fractions'],f['targets'],strict=True))*q
        close(expected_net/risk,f['net_target_R'],'causal_expected_net_target_R')
        friction=q*(abs(entry_fill-f['entry_reference'])+entry_fill*fee+
                    math.fsum(fr*(abs(t*(1-s*slip)-t)+t*(1-s*slip)*fee)
                              for fr,t in zip(f['target_fractions'],f['targets'],strict=True)))
        close(friction/risk,f['friction_R'],'causal_expected_friction_R')
        close(q,l['quantity'],'original_quantity');close(entry_fill,l['entry'],'original_entry')
        close(f['gross_target_R']-f['friction_R'],f['net_target_R'],'same_planned_risk_denominator')
        expected_cost+=1
    assert dict(purge)==split['purged_counts']
    for l in closed:
        close(l['quote_gross_pnl']-l['fees']-l['slippage'],l['net_pnl'],'actual_original_cost_ledger')
        close(l['net_pnl']/l['risk_amount'],l['result_R'],'original_R')
        assert l['result']==('WIN' if l['net_pnl']>0 else 'LOSS' if l['net_pnl']<0 else 'BE')
    rules=json.loads((OUT/'strategy_v2_final_rules.json').read_text())
    models={m['model_id']:m for m in rules['models']}
    test_features=list(read_jsonl(OUT/'features_TEST.jsonl.gz'))
    predictions=list(read_jsonl(OUT/'frozen_TEST_predictions.jsonl.gz'))
    results={r['candidate_name']:r for r in csv.DictReader((OUT/'strategy_v2_oos_results.csv').open())}
    independents=[]
    for name,candidate in rules['final_candidates'].items():
        pp=[r for r in predictions if r['candidate_name']==name]
        assert len(pp)==len(test_features) and len({r['signal_id'] for r in pp})==len(pp)
        values,mask=probability_or_mask(test_features,candidate['rule'],models)
        assert [bool(v) for v in mask]==[r['admitted'] for r in pp]
        assert np.array_equal(values,np.array([r['score_or_probability'] for r in pp]))
        selected=[lf[r['signal_id']] for r in pp if r['admitted'] and lf[r['signal_id']]['status']=='CLOSED']
        assert len({r['physical_opportunity_id'] for r in selected})==len(selected)
        vals=[r['net_pnl'] for r in selected];wins=[v for v in vals if v>0];losses=[-v for v in vals if v<0]
        n=len(vals);actual=results[name]
        assert n==int(actual['CLOSED']) and len(wins)==int(actual['WIN']) and len(losses)==int(actual['LOSS'])
        close(len(wins)/n,float(actual['WR']),'independent_WR')
        close(math.fsum(wins)/math.fsum(losses),float(actual['PF']),'independent_PF')
        close(math.fsum(vals),float(actual['NetPnL']),'independent_net')
        close(math.fsum(vals)/n,float(actual['Expectancy']),'independent_expectancy')
        close(math.fsum(r['net_pnl']/r['risk_amount'] for r in selected)/n,float(actual['AvgR']),'independent_R')
        ci=binomtest(len(wins),n).proportion_ci(confidence_level=.95,method='wilson')
        close(ci.low,float(actual['WR_CI_low']),'independent_scipy_Wilson_low')
        close(ci.high,float(actual['WR_CI_high']),'independent_scipy_Wilson_high')
        total=peak=drawdown=Decimal(0)
        for r in sorted(selected,key=lambda r:(r['exit_time'],r['physical_opportunity_id'])):
            total+=Decimal(str(r['net_pnl']));peak=max(peak,total);drawdown=max(drawdown,peak-total)
        close(float(drawdown),float(actual['MaxDrawdown_case_sum']),'independent_decimal_drawdown')
        independents.append({'candidate_name':name,'CLOSED':n,'WIN':len(wins),'LOSS':len(losses),
                             'NetPnL_fsum':math.fsum(vals),'Wilson_scipy':[ci.low,ci.high],
                             'MaxDrawdown_decimal':float(drawdown),'status':'PASS'})
    current=canonical(rules)
    stored=json.loads(subprocess.check_output(['git','show',f'{freeze_commit}:{OUT}/strategy_v2_final_rules.json']))
    assert current==canonical(stored)
    leakage=json.loads((OUT/'strategy_v2_leakage_audit.json').read_text())
    baseline=audit_baseline()
    write_json(OUT/'strategy_v2_independent_metric_audit.json',{'status':'PASS','candidates':independents})
    write_json(OUT/'strategy_v2_final_leakage_audit.json',{
        'status':'PASS','frozen_commit':freeze_commit,'original_feature_audit_sha256':digest(OUT/'strategy_v2_leakage_audit.json'),
        'real_native_prefix_and_future_mutation_checks':len(leakage['prefix_and_future_checks']),
        'prediction_label_identity_mutation':receipt['label_and_identity_mutation_predictions'],
        'chronological_split_ties_and_purge':'PASS_ALL_16351','purged_counts':dict(purge),
        'same_physical_pre_READY_confluence':'PASS_ALL_WITNESSES','causal_ATR_CLOSE':'PASS_ALL_16351',
        'TRAIN_VALIDATION_selection_access':'SEPARATE_PARTITION_FILES; TRAIN_MINER_REJECTS_TEST',
        'one_time_TEST_after_committed_rules_and_predictions':'PASS','post_TEST_rule_or_model_changes':False,
        'CLOSED_conditioning_limit':'REQUESTED_ALL_CLOSED_ANALYSIS; ALL_18_OPEN_RETAINED_AND_PREDICTED',
        'OOS_provenance':'V2_SPECIFIC_DEVELOPMENT_TEST; PREVIOUSLY_INSPECTED_HISTORY; NOT_FRESH_OOS',
        'trade_entry_allowed':False})
    write_json(OUT/'strategy_v2_core_qa_receipt.json',{
        'status':'PASS_INDEPENDENT_CAUSAL_DATA_LEDGER_METRICS_AND_BASELINE_AUDIT',
        'baseline':baseline,'native_dataset_series':40,'native_candles':native_count,
        'distinct_physical_feature_rows':len(features),'CLOSED':len(closed),'censored_OPEN':18,
        'causal_expected_cost_and_quantity_checks':expected_cost,'realized_cost_and_R_checks':len(closed),
        'independent_frozen_TEST_candidate_metrics':independents,'frozen_rules_unchanged':True,
        'single_test_opening':True,'trade_entry_allowed':False})
    print('PASS',len(features),'causal cost checks;',len(closed),'ledger checks;',
          baseline['unchanged_Git_blobs'],'baseline files unchanged;',len(independents),'candidate metrics')


if __name__=='__main__':main()
