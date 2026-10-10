"""TRAIN search and VALIDATION selection. This script never opens TEST labels."""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from crypto_bot.research.v2_common import (
    OUT,
    Row,
    canonical,
    digest,
    metrics,
    numerical_gate,
    read_jsonl,
    write_csv,
    write_json,
)
from crypto_bot.research.v2_rules import (
    EXTENSIONS,
    FRICTION,
    GROSS_TARGET,
    LOGISTIC_FEATURES,
    NET_TARGET,
    SCOPES,
    SCORE_FEATURES,
    SCORE_PROFILES,
    TREE_FEATURES,
    candidate_mask,
    column,
    condition_mask,
    design,
    rule_id,
    scope_mask,
)


def partition(name: str) -> tuple[list[Row], list[Row]]:
    assert name in ('TRAIN', 'VALIDATION'), 'TEST labels forbidden in discovery process'
    labels = {r['signal_id']: r for r in read_jsonl(OUT/f'labels_{name}.jsonl.gz') if r['label_eligible']}
    rows = [r for r in read_jsonl(OUT/f'features_{name}.jsonl.gz') if r['signal_id'] in labels]
    assert all(r['split']==name for r in rows)
    return rows, [labels[r['signal_id']] for r in rows]


def rank(m: Row) -> tuple[Any, ...]:
    return (numerical_gate(m), (m['Expectancy'] or 0)>0, m['WR'] or 0,
            m['Expectancy'] if m['Expectancy'] is not None else -1e99, m['PF'] or 0, m['CLOSED'])


def fast_metrics(mask: Any, labels: list[Row], arrays: dict[str, Any]) -> Row:
    n = int(mask.sum())
    net = arrays['net'][mask]; positive = net[net>0].sum(); negative = -net[net<0].sum()
    wins, losses = int((net>0).sum()), int((net<0).sum())
    return {'CLOSED': n, 'WIN': wins, 'LOSS': losses, 'BE': n-wins-losses,
            'WR': wins/n if n else None, 'PF': float(positive/negative) if negative else None,
            'Expectancy': float(net.mean()) if n else None,
            'AvgR': float(arrays['R'][mask].mean()) if n else None, 'NetPnL': float(net.sum()),
            'GrossPnL': float(arrays['gross'][mask].sum()), 'fees': float(arrays['fees'][mask].sum()),
            'slippage': float(arrays['slippage'][mask].sum())}


def feature_analysis(rows: list[Row], labels: list[Row]) -> None:
    excluded = {'physical_opportunity_id', 'signal_id', 'READY', 'feature_cutoff', 'trade_entry_allowed',
                'status', 'split', 'label_eligible', 'confluence_witnesses', 'available_paths', 'physical_families',
                'targets', 'target_fractions', 'ATR_known_at'}
    fields = [k for k in rows[0] if k not in excluded and not k.endswith(('_known_at', '_id'))]
    output = []; distributions = []
    scopes = ['ALL', 'CORE_A', 'CORE_B', 'CORE_C']
    for field in fields:
        numeric = all(r.get(field) is None or isinstance(r.get(field), (float, int)) for r in rows)
        if numeric:
            x = column(rows, field); finite = x[np.isfinite(x)]
            edges = sorted({float(v) for v in np.quantile(finite, [.2,.4,.6,.8])}) if len(finite) else []
            if len(set(finite)) <= 8:
                bins = [(str(v), x==v) for v in sorted(set(finite))]
            else:
                bins = [(f'({a},{b}]', (x>a)&(x<=b)) for a,b in
                        zip([-np.inf,*edges], [*edges,np.inf])]
            bins.append(('MISSING', ~np.isfinite(x)))
        else:
            values = [r.get(field) for r in rows]
            bins = [(str(v), np.array([x==v for x in values])) for v in sorted(set(values), key=str)]
        for scope in scopes:
            base_mask = scope_mask(rows, scope)
            base_labels = [r for r, keep in zip(labels, base_mask) if keep]
            baseline = metrics(base_labels)
            for bin_name, bin_mask in bins:
                mask = base_mask & bin_mask
                m = metrics([r for r, keep in zip(labels, mask) if keep])
                output.append({'scope': scope, 'feature': field, 'bin': bin_name, **m,
                    'WR_lift_absolute': m['WR']-baseline['WR'] if m['WR'] is not None and baseline['WR'] is not None else None,
                    'WR_lift_ratio': m['WR']/baseline['WR'] if m['WR'] is not None and baseline['WR'] else None,
                    'Expectancy_lift': m['Expectancy']-baseline['Expectancy'] if m['Expectancy'] is not None and baseline['Expectancy'] is not None else None})
            if numeric:
                for outcome in ['WIN', 'LOSS']:
                    sample = np.array([r[field] for r,l,keep in zip(rows,labels,base_mask)
                                       if keep and l['result']==outcome and r.get(field) is not None], dtype=float)
                    distributions.append({'scope':scope,'feature':field,'outcome':outcome,'sample_size':len(sample),
                        'mean':float(sample.mean()) if len(sample) else None,
                        **{f'q{q}':float(np.quantile(sample,q/100)) if len(sample) else None for q in [5,25,50,75,95]}})
    write_csv(OUT/'strategy_v2_win_loss_feature_analysis.csv', output)
    write_csv(OUT/'strategy_v2_win_loss_distributions.csv', distributions)
    write_json(OUT/'feature_analysis_definition.json', {
        'fit_split':'TRAIN_ONLY_PURGED', 'numeric_bins':'TRAIN_ONLY_QUINTILES_OR_DISTINCT_LOW_CARDINALITY',
        'identity_fields_excluded': sorted(excluded), 'time_and_symbol':'DESCRIPTIVE_ROBUSTNESS_ONLY_NOT_CANDIDATE_INPUTS',
        'missing':'SEPARATE_BIN; UNKNOWN_NEVER_ASSUMED_FAVOURABLE', 'p_values':'NOT_USED; OVERLAPPING_CASES_AND_MULTIPLE_SEARCH',
        'baseline_by_scope':{s:metrics([l for l,k in zip(labels,scope_mask(rows,s)) if k]) for s in SCOPES}})


def train() -> None:
    assert not (OUT/'train_shortlist.json').exists(), 'TRAIN stage already sealed'
    rows, labels = partition('TRAIN')
    arrays = {'net':np.array([r['net_pnl'] for r in labels]),'R':np.array([r['result_R'] for r in labels]),
              'gross':np.array([r['quote_gross_pnl'] for r in labels]),
              'fees':np.array([r['fees'] for r in labels]),'slippage':np.array([r['slippage'] for r in labels])}
    feature_analysis(rows, labels)
    conditions = [*[("friction_R", "<=", v) for v in FRICTION],
                  *[("net_target_R", ">=", v) for v in NET_TARGET],
                  *[("gross_target_R", ">=", v) for v in GROSS_TARGET], *EXTENSIONS]
    masks = {canonical(c): condition_mask(rows,c) for c in conditions}
    results = []; selected = []; controls = {}
    for scope in SCOPES:
        scope_results = []; original = scope_mask(rows,scope)
        for f,n,g in itertools.product([None,*FRICTION],[None,*NET_TARGET],[None,*GROSS_TARGET]):
            base_conditions = [c for c in [('friction_R','<=',f),('net_target_R','>=',n),
                                         ('gross_target_R','>=',g)] if c[2] is not None]
            base_mask = original.copy()
            for c in base_conditions:
                base_mask &= masks[canonical(c)]
            for extension in [None,*EXTENSIONS]:
                cs = base_conditions+[extension] if extension is not None else base_conditions
                mask = base_mask & masks[canonical(extension)] if extension is not None else base_mask
                rule = {'kind':'RULE','scope':scope,'conditions':[list(c) for c in cs]}
                rid = rule_id(rule); m = fast_metrics(mask, labels, arrays)
                r = {'candidate_id':rid,'scope':scope,'rule':rule,**m,'TRAIN_sample_floor':m['CLOSED']>=600}
                scope_results.append(r)
                if extension is None and len(cs)<=1:
                    controls[rid]=r
        eligible = [r for r in scope_results if r['TRAIN_sample_floor']]
        eligible.sort(key=lambda r:(rank(r),r['candidate_id']), reverse=True)
        selected.extend(eligible[:20]); results.extend(scope_results)
        print('TRAIN',scope,'attempts',len(scope_results),'eligible',len(eligible),
              'best', {k:eligible[0][k] for k in ['CLOSED','WR','PF','Expectancy']} if eligible else None,flush=True)
    scores = []
    for profile, weights in SCORE_PROFILES.items():
        for threshold in range(sum(weights)+1):
            rule = {'kind':'SCORE','profile':profile,'threshold':threshold}
            mask = candidate_mask(rows,rule)
            scores.append({'candidate_id':rule_id(rule),'scope':'CONFLUENCE_SCORE','rule':rule,
                           **fast_metrics(mask,labels,arrays)})
    unique = {r['candidate_id']:r for r in [*selected,*controls.values(),*scores]}
    write_csv(OUT/'strategy_v2_train_search_results.csv.gz', results+scores)
    write_json(OUT/'train_shortlist.json', sorted(unique.values(),key=lambda r:r['candidate_id']))
    write_json(OUT/'strategy_v2_candidates.json', {
        'registered_grids':{'friction_R':FRICTION,'net_target_R':NET_TARGET,'gross_target_R':GROSS_TARGET},
        'all_attempt_count':len(results)+len(scores),'TRAIN_shortlist_count':len(unique),
        'shortlist':sorted(unique.values(),key=lambda r:r['candidate_id']),
        'train_only_selection':True,'test_access':False,'trade_entry_allowed':False})
    write_json(OUT/'train_search_receipt.json', {
        'status':'SEALED_TRAIN_SEARCH','TRAIN_eligible_CLOSED':len(rows),'TEST_access':False,
        'VALIDATION_access':False,'input_hashes':{p:digest(OUT/p) for p in ['features_TRAIN.jsonl.gz','labels_TRAIN.jsonl.gz']},
        'shortlist_sha256':digest(OUT/'train_shortlist.json'),'train_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'attempt_count':len(results)+len(scores),'selection_policy':'REGISTERED_TOP20_PER_SCOPE_PLUS_CONTROLS_AND_SCORES',
        'trade_entry_allowed':False})


def prepare(rows: list[Row], fields: list[str], impute: list[float] | None = None) -> tuple[Any,list[float]]:
    x = design(rows, fields)
    if impute is None:
        impute = [float(np.median(col[np.isfinite(col)])) if np.isfinite(col).any() else 0.
                  for col in x.T]
    x = np.where(np.isfinite(x),x,np.array(impute))
    return x,impute


def fit_meta(rows: list[Row], labels: list[Row]) -> list[Row]:
    y = np.array([r['net_pnl']>0 for r in labels],dtype=int)
    models = []
    x, impute = prepare(rows,LOGISTIC_FEATURES)
    mean,std=x.mean(axis=0),x.std(axis=0);std=np.where(std==0,1.,std)
    model = LogisticRegression(C=1,random_state=70,max_iter=2000).fit((x-mean)/std,y)
    models.append({'model_id':'LOGISTIC_C1','kind':'LOGISTIC','features':LOGISTIC_FEATURES,
                   'impute':impute,'mean':mean.tolist(),'std':std.tolist(),'coef':model.coef_[0].tolist(),
                   'intercept':float(model.intercept_[0]),'iterations':int(model.n_iter_[0]),
                   'fit_split':'TRAIN_ONLY_PURGED','class_weight':None})
    x, impute = prepare(rows,TREE_FEATURES)
    for depth,leaf in itertools.product([1,2,3],[100,200]):
        tree = DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,random_state=70).fit(x,y)
        t=tree.tree_
        models.append({'model_id':f'TREE_D{depth}_L{leaf}','kind':'TREE','features':TREE_FEATURES,'impute':impute,
            'depth':depth,'min_samples_leaf':leaf,'children_left':t.children_left.tolist(),
            'children_right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),
            'probability_WIN':[float(v[0][1]/sum(v[0])) for v in t.value],
            'node_samples':t.n_node_samples.tolist(),'internal_condition_count':int((t.children_left>=0).sum()),
            'fit_split':'TRAIN_ONLY_PURGED'})
    return models


def model_probability(rows: list[Row], model: Row) -> Any:
    x,_=prepare(rows,model['features'],model['impute'])
    if model['kind']=='LOGISTIC':
        z=((x-np.array(model['mean']))/np.array(model['std']))@np.array(model['coef'])+model['intercept']
        return 1/(1+np.exp(-np.clip(z,-700,700)))
    result=[]
    for r in x:
        node=0
        while model['children_left'][node]>=0:
            node=(model['children_left'][node] if r[model['feature'][node]]<=model['threshold'][node]
                  else model['children_right'][node])
        result.append(model['probability_WIN'][node])
    return np.array(result)


def validation() -> None:
    assert not (OUT/'strategy_v2_final_rules.json').exists(), 'VALIDATION stage already sealed'
    train_rows, train_labels = partition('TRAIN'); rows,labels=partition('VALIDATION')
    shortlist=json.loads((OUT/'train_shortlist.json').read_text())
    receipt=json.loads((OUT/'train_search_receipt.json').read_text())
    assert digest(OUT/'train_shortlist.json')==receipt['shortlist_sha256']
    attempted=[]; eligible=[]
    for r in shortlist:
        rule=r['rule'];mask=candidate_mask(rows,rule);m=metrics([l for l,k in zip(labels,mask) if k])
        record={'candidate_id':r['candidate_id'],'kind':rule['kind'],'rule':rule,
                'TRAIN_CLOSED':r['CLOSED'],'TRAIN_WR':r['WR'],'TRAIN_PF':r['PF'],**m,
                'eligible':r['CLOSED']>=600 and m['CLOSED']>=200}
        attempted.append(record)
        if record['eligible']:eligible.append(record)
    deterministic=sorted(eligible,key=lambda r:(rank(r),r['candidate_id']),reverse=True)
    best_det=deterministic[0]
    models=[];meta_results=[]
    if not numerical_gate(best_det):
        models=fit_meta(train_rows,train_labels)
        for model in models:
            tp=model_probability(train_rows,model);vp=model_probability(rows,model)
            for threshold in [.30,.40,.50,.55,.60,.65,.70,.75,.80,.85,.90,.95]:
                rule={'kind':'META','model_id':model['model_id'],'threshold':threshold}
                tr=metrics([l for l,k in zip(train_labels,tp>=threshold) if k])
                m=metrics([l for l,k in zip(labels,vp>=threshold) if k])
                r={'candidate_id':rule_id(rule),'kind':'META','rule':rule,
                    'TRAIN_CLOSED':tr['CLOSED'],'TRAIN_WR':tr['WR'],'TRAIN_PF':tr['PF'],**m,
                    'eligible':tr['CLOSED']>=600 and m['CLOSED']>=200}
                meta_results.append(r)
        write_json(OUT/'strategy_v2_fitted_meta_models.json',models)
    eligible_meta=sorted((r for r in meta_results if r['eligible']),key=lambda r:(rank(r),r['candidate_id']),reverse=True)
    best_meta=eligible_meta[0] if eligible_meta else None
    # A/A+/TOP share one profile and are nested. No TEST measurement enters the choice.
    score_rows=[r for r in eligible if r['kind']=='SCORE']
    top=max(score_rows,key=lambda r:(rank(r),r['candidate_id']))
    profile=top['rule']['profile'];upper=top['rule']['threshold'];tiers={}
    previous=0
    for tier,floor in [('A',400),('A_PLUS',300),('TOP',200)]:
        possibilities=[r for r in score_rows if r['rule']['profile']==profile and
                       previous<=r['rule']['threshold']<=upper and r['CLOSED']>=floor]
        chosen=max(possibilities,key=lambda r:(rank(r),r['candidate_id'])) if possibilities else next(
            r for r in score_rows if r['rule']['profile']==profile and r['rule']['threshold']==0)
        tiers[tier]=chosen;previous=chosen['rule']['threshold']
    final={'BEST_DETERMINISTIC':best_det,**({'BEST_META':best_meta} if best_meta else {}),**tiers}
    primary=max(['BEST_DETERMINISTIC',*(['BEST_META'] if best_meta else [])],
                key=lambda k:(rank(final[k]),final[k]['candidate_id']))
    write_csv(OUT/'strategy_v2_validation_results.csv',attempted+meta_results)
    write_json(OUT/'strategy_v2_confluence_score.json',{
        'components':SCORE_FEATURES,'profiles_attempted':SCORE_PROFILES,'chosen_profile':profile,
        'chosen_weights':SCORE_PROFILES[profile],'tiers':{k:v['rule'] for k,v in tiers.items()},
        'selection_split':'VALIDATION_ONLY','maximum_components':7,'trade_entry_allowed':False})
    write_json(OUT/'strategy_v2_final_rules.json',{
        'status':'FROZEN_BEFORE_TEST','primary_name':primary,'final_candidates':final,
        'models':models,'final_count':len(final),'unique_rules':len({r['candidate_id'] for r in final.values()}),
        'baseline_unchanged':True,'new_exit_or_entry_prices':False,'trade_entry_allowed':False,
        'TRAIN_floor':600,'VALIDATION_floor':200,'TEST_floor':200,'fit_on_validation':False,
        'test_label_access':False,'selection_rank':'JOINT_GATE; POSITIVE_EXPECTANCY; WR; EXPECTANCY; PF; N; ID',
        'provenance':'V2_SPECIFIC_HELD_OUT_DEVELOPMENT_NOT_UNTOUCHED_MARKET_OOS'})
    print('VALIDATION best deterministic',canonical({k:best_det[k] for k in ['rule','CLOSED','WR','PF','Expectancy']}))
    print('VALIDATION best meta',canonical({k:best_meta[k] for k in ['rule','CLOSED','WR','PF','Expectancy']}) if best_meta else None)
    print('PRIMARY',primary,'TEST_NOT_OPENED',flush=True)
    write_json(OUT/'validation_selection_receipt.json',{
        'status':'FROZEN_VALIDATION_SELECTION_TEST_UNOPENED','TEST_access':False,
        'TRAIN_access_for_model_fit':bool(models),'input_hashes':{p:digest(OUT/p) for p in
            ['features_TRAIN.jsonl.gz','labels_TRAIN.jsonl.gz','features_VALIDATION.jsonl.gz','labels_VALIDATION.jsonl.gz']},
        'final_rules_sha256':digest(OUT/'strategy_v2_final_rules.json'),'validation_attempts':len(attempted)+len(meta_results),
        'final_primary':primary,'trade_entry_allowed':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['train','validation'])
    args=parser.parse_args()
    train() if args.stage=='train' else validation()
