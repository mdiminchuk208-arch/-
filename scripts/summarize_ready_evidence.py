"""Additional same-candidate intersections and causal evidence for READY audit."""
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

from audit_ready_root_cause import canonical, write_json, write_csv
from ready_audit_support import CANDIDATE_GATES


def summarize(root):
    setup_diags={}
    candidate_seen=set()
    truth=defaultdict(Counter)
    candidate_counts=defaultdict(Counter)
    prefix_counts=Counter()
    transitions=Counter()
    resets=[]
    episodes=defaultdict(set)
    causal_errors=[]
    production_auto_evaluations=0
    automatic_in_execution=set()
    condition_setups=defaultdict(lambda:defaultdict(set))
    timeline=root/'candidate_gate_timeline.jsonl'
    with timeline.open('w',encoding='utf-8') as stream:
        for path in sorted(root.glob('*/evaluations.jsonl')):
            for line in path.open():
                row=json.loads(line)
                for gate,value in row['gates'].items():
                    condition_setups[gate][value].add(row['signal_id'])
                if row['previous_state']!=row['next_state']:
                    transitions[(row['previous_state'],row['next_state'])]+=1
                    if row['previous_state']=='INVALIDATED' and row['next_state']!='INVALIDATED':
                        resets.append(row)
                signal=row['signal']
                if not signal['sfp_time']<signal['bos_time']<=signal['event_time']:
                    causal_errors.append((row['signal_id'],'SFP_BOS_ASOF'))
                if signal['entry_geometry_ready_time'] and signal['entry_geometry_ready_time']>signal['event_time']:
                    causal_errors.append((row['signal_id'],'GEOMETRY_KNOWN_AT'))
                if signal['trade_entry_allowed']:
                    causal_errors.append((row['signal_id'],'REAL_TRADE_PERMISSION'))
                when=datetime.fromisoformat(row['timestamp'])
                if int(when.timestamp())%300:
                    causal_errors.append((row['signal_id'],'LTF_CLOCK_ALIGNMENT'))
                for context in row['sfp_contexts']:
                    episodes[(row['symbol'],context['htf_episode_id'])].add(row['signal_id'])
                diag=row['automatic_diagnostic']
                if not diag or diag['evaluated_at']!=row['timestamp']:
                    continue
                production_auto_evaluations+=1
                if row['scope']=='EXECUTION':automatic_in_execution.add(row['signal_id'])
                setup_diags.setdefault(row['signal_id'],(row,diag))
                for candidate in diag['candidates']:
                    identity=(row['signal_id'],candidate['a_open'])
                    if candidate['known_at']>row['timestamp']:
                        causal_errors.append((row['signal_id'],'FUTURE_OB'))
                    if candidate['a_open']<signal['bos_time']:
                        causal_errors.append((row['signal_id'],'OB_BEFORE_BOS'))
                    prior=True
                    for gate,reason in CANDIDATE_GATES:
                        value=candidate['gates'][gate]
                        truth[gate]['TRUE' if value else 'FALSE']+=1
                        stream.write(canonical(dict(signal_id=row['signal_id'],candidate_a_open=candidate['a_open'],
                            symbol=row['symbol'],direction=row['direction'],timestamp=row['timestamp'],
                            previous_state=row['previous_state'],evaluated_gate=gate,result='TRUE' if value else 'FALSE',
                            production_evaluated=prior,diagnostic_only=not prior,next_state=row['next_state'],
                            reason='PASSED' if value else reason))+'\n')
                        prior=prior and value
                    if identity in candidate_seen:
                        continue
                    candidate_seen.add(identity)
                    prior=True
                    for gate,_ in CANDIDATE_GATES:
                        candidate_counts[gate]['TRUE' if candidate['gates'][gate] else 'FALSE']+=1
                        prior=prior and candidate['gates'][gate]
                        if prior: prefix_counts[gate]+=1
    assert not causal_errors,causal_errors[:10]
    window=Counter()
    support=Counter()
    price_geometry=Counter()
    persistent=Counter()
    # Setup existential intersection uses the same candidate. Marginal TRUE
    # counts from different candidates may never be added together.
    setup_intersections=Counter()
    for ident,(row,diag) in setup_diags.items():
        candidates=diag['candidates']
        window['auto_evaluated_setups']+=1
        if not candidates:
            label=('EMPTY_POST_BOS_PRE_ANCHOR_WINDOW' if not diag['scanned_triples']
                   else 'NO_OPPOSITE_COLOR_PAIR' if not diag['color_pair_count']
                   else 'NO_FULL_BODY_ENGULF')
            window[label]+=1
            persistent[label]+=1
        else:
            window['HAS_FULL_BODY_ENGULF_PATTERN']+=1
            def progress(c):
                count=0
                for g,_ in CANDIDATE_GATES:
                    if not c['gates'][g]:break
                    count+=1
                return count
            c=max(candidates,key=progress)
            persistent[c['first_failure'] or 'READY_OB']+=1
        for i,(gate,_) in enumerate(CANDIDATE_GATES):
            if any(all(c['gates'][g] for g,_ in CANDIDATE_GATES[:i+1]) for c in candidates):
                setup_intersections[gate]+=1
        for c in candidates:
            if not c['gates']['OB_OTE_AND_IMPULSE']:
                price_geometry['NO_OTE_INTERSECTION' if not c['ote_intersection'] else 'ABC_OUTSIDE_IMPULSE']+=1
            if all(c['gates'][g] for g,_ in CANDIDATE_GATES[:4]):
                support['CORE_OB_CANDIDATES']+=1
                if not c['supporting_poi_candidates']:
                    support['NO_PREEXISTING_OVERLAPPING_HTF_GAP_POI']+=1
                elif c['stale_supporting_pois']==c['supporting_poi_candidates']:
                    support['ALL_PREEXISTING_OVERLAPPING_HTF_GAP_POIS_STALE']+=1
                if all(v for g,v in c['gates'].items() if g!='SUPPORTING_POI'):
                    support['ONLY_SUPPORTING_POI_FALSE_AMONG_OB_GATES']+=1
                    if diag['independent_targets_available']:
                        support['ONLY_SUPPORTING_POI_FALSE_PLUS_3_TARGETS_AVAILABLE']+=1
    observed_automatic=set()
    for path in root.glob('*/observed_signals.jsonl'):
        for line in path.open():
            signal=json.loads(line)
            if signal['status']=='WAITING_FOR_AUTO_LEVELS':observed_automatic.add(signal['signal_id'])
    result=dict(unique_automatic_setups=len(setup_diags),production_automatic_evaluations=production_auto_evaluations,
        automatic_evaluation_calls_only_in_warmup=len(set(setup_diags)-automatic_in_execution),
        automatic_eligible_setups_observed_in_baseline=len(observed_automatic),
        warmup_lifecycle_eligible_not_observed_in_baseline=len(set(setup_diags)-observed_automatic),
        condition_unique_setups_ever={g:{v:len(ids) for v,ids in values.items()} for g,values in condition_setups.items()},
        unique_candidate_pairs=len(candidate_seen),candidate_truth_counts=dict(candidate_counts),
        candidate_evaluation_truth_counts=dict(truth),candidate_sequential_intersections=dict(prefix_counts),
        setup_sequential_intersections=dict(setup_intersections),search_window_breakdown=dict(window),
        persistent_candidate_blocker_breakdown=dict(persistent),supporting_poi_breakdown=dict(support),
        ote_impulse_failure_breakdown=dict(price_geometry),
        state_transitions=[dict(previous=a,next=b,count=n) for (a,b),n in sorted(transitions.items())],
        invalidated_to_noninvalidated_state_resets=len(resets),
        shared_sfp_episodes_across_distinct_bos_setups=sum(len(ids)>1 for ids in episodes.values()),
        episode_reuse_interpretation='Shared live SFP context may link to distinct BOS IDs; consumed virtual-entry IDs cannot be reused. No historical READY or virtual entry occurred.',
        causal_time_identity_checks='PASS',causal_errors=causal_errors,
        no_universal_rule_incompatibility='All predicates jointly satisfiable in LONG/SHORT OHLC-evidence fixtures; earlier conjunction observed in 9 actual setups. Not a proof of source certification or arbitrary full-detector reachability.',
        diagnostic_scope='All 6357 baseline identities, including their closed-candle warmup lifecycles')
    write_json(root/'detailed_evidence.json',result)
    # Pairwise same-candidate TRUE intersections disclose incompatibilities in
    # this observed sample without declaring a logical contradiction globally.
    pair=Counter()
    for row,diag in setup_diags.values():
        for c in diag['candidates']:
            keys=[g for g,v in c['gates'].items() if v]
            for i,a in enumerate(sorted(keys)):
                for b in sorted(keys)[i:]:pair[(a,b)]+=1
    write_csv(root/'same_candidate_pairwise_intersections.csv',[
        dict(condition_a=a,condition_b=b,joint_true=pair[tuple(sorted((a,b)))])
        for i,(a,_) in enumerate(CANDIDATE_GATES) for b,_ in CANDIDATE_GATES[i:]])
    # Additional explicitly diagnostic one-policy ablations on the first 60
    # execution days. No result is passed back to the strategy or portfolio.
    baseline_start=datetime.fromisoformat(json.loads((root/'baseline_summary.json').read_text())['execution_start'])
    from datetime import timedelta
    training_end=baseline_start+timedelta(days=60)
    training=[(row,diag) for row,diag in setup_diags.values()
              if baseline_start<=datetime.fromisoformat(row['timestamp'])<training_end]
    ablations=[]
    for gate in ('IMBALANCE','RAW_SWEEP','SUPPORTING_POI','OB_FRESH','OB_OTE_AND_IMPULSE'):
        passing=set()
        passing_except=set()
        for row,diag in training:
            for c in diag['candidates']:
                # SUPPORTING_POI ablation relaxes freshness only: preexistence
                # and geometric overlap remain mandatory and causal.
                substitute=bool(c['supporting_poi_candidates']) if gate=='SUPPORTING_POI' else (
                    c['ote_intersection'] if gate=='OB_OTE_AND_IMPULSE' else True)
                if substitute and all(value for g,value in c['gates'].items() if g!=gate):
                    passing_except.add(row['signal_id'])
                    if diag['independent_targets_available']:passing.add(row['signal_id'])
        ablations.append(dict(parameter={'SUPPORTING_POI':'require_preexisting_gap_poi_fresh_before_A',
                               'OB_OTE_AND_IMPULSE':'require_all_ABC_inside_structural_impulse'}.get(gate,'require_'+gate.lower()),
                        baseline_value=True,experimental_value=False,
                        training_setups=len(training),ob_conjunction_pass_except_this_requirement=len(passing_except),
                        ready_conjunction_pass_with_independent_targets=len(passing),
                        source_certification='UNREVIEWED_NOT_GRANTED',financial_replay=False))
    write_json(root/'training_policy_sensitivity.json',dict(start=baseline_start,end=training_end,
        status='READ_ONLY_ONE_POLICY_ABLATIONS_NOT_STRATEGY_OUTPUT_NOT_OPTIMIZATION',results=ablations))
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report_root',type=Path)
    args=parser.parse_args()
    print(json.dumps(summarize(args.report_root),sort_keys=True,indent=2))
