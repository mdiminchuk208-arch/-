"""Material source distinctions, unknown propagation and offline causal boundary."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from original_strategy_spec_contract import (
    SPEC,
    adverse_state,
    conservative_tf,
    evaluate,
    exit_profile,
    load_contract,
    project_admission,
    protective_stop,
    sfp_body_invalid,
    synthetic_case,
)


class OriginalStrategySpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load_contract()
        cls.rules = json.loads((SPEC/'original_strategy_rule_registry_v1.json').read_text())['rules']

    def case(self,branch='SFP',direction='LONG'):
        return synthetic_case(branch,direction,self.tree)

    def test_source_rules_have_literal_original_evidence(self):
        documents = set()
        for rule in self.rules:
            if rule['category']=='SOURCE_RULE':
                self.assertTrue(rule['source_document'])
                self.assertTrue(rule['page_diagram'])
                for ref in rule['page_diagram']:
                    self.assertTrue(ref['literal_passage'])
                    self.assertTrue(ref['page_or_paragraph'])
                    self.assertEqual(len(ref['source_sha256']),64)
                    documents.add(ref['source_id'])
                self.assertTrue(rule['known_at_semantics'])
        self.assertEqual(len(documents),13)

    def test_source_tree_excludes_project_and_normalization_rules(self):
        category = {r['rule_id']:r['category'] for r in self.rules}
        for node in self.tree['nodes']:
            self.assertEqual(category[node['rule_id']],'SOURCE_RULE')
        mutated = copy.deepcopy(self.tree)
        start = mutated['branch_start_nodes']['SFP']
        next(node for node in mutated['nodes'] if node['node_id']==start)['rule_id']='P_FORMAL_OWNER'
        with self.assertRaisesRegex(ValueError,'injected'):
            evaluate(self.case(),mutated)

    def test_each_branch_has_long_short_examples_but_no_original_allow(self):
        for branch in self.tree['branch_start_nodes']:
            for side in ['LONG','SHORT']:
                with self.subTest(branch=branch,side=side):
                    result = evaluate(self.case(branch,side))
                    self.assertTrue(result['source_conditions_pass'])
                    expected = 'CONTRACT_UNRESOLVED' if self.tree['branch_roles'][branch]=='TRADE_SETUP' else 'COMPONENT_ONLY'
                    self.assertEqual(result['SOURCE_STRATEGY_DECISION'],expected)
                    self.assertFalse(result['trade_entry_allowed'])

    def test_lower_tf_valid_sfp_not_rejected_for_missing_owner(self):
        for tf in [1/60,1,3,5,15,30,60,180,240,1440,10080,43200]:
            case = self.case()
            case['setup_tf']=tf
            case['formal_H1_H4_owner']=False
            result = evaluate(case)
            self.assertTrue(result['source_conditions_pass'])
            other = copy.deepcopy(case)
            other['formal_H1_H4_owner']=True
            self.assertEqual(result,evaluate(other))

    def test_conservative_tf_lower_bounds_and_relative_role(self):
        for ht in [15,30,60,180,240,1440]:
            for lt in [1,3,5,15]:
                self.assertEqual(conservative_tf(ht,lt),lt<ht)
        self.assertFalse(conservative_tf(240,60))
        self.assertFalse(conservative_tf(15,15))
        self.assertFalse(conservative_tf(5,1))
        self.assertIsNone(conservative_tf(10080,5))

    def test_outside_documented_htf_range_unknown_not_absolute_d1_ban(self):
        case = self.case('OB_CONSERVATIVE')
        case['setup_tf']=10080
        result = evaluate(case)
        self.assertEqual(result['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')
        self.assertEqual(result['source_trace'][-1]['rule_id'],'S_OB_CONS_TF')

    def test_conservative_h1_trigger_is_source_fail(self):
        case = self.case('OB_CONSERVATIVE')
        case['setup_tf']=240
        case['trigger_tf']=60
        result = evaluate(case)
        self.assertEqual(result['SOURCE_STRATEGY_DECISION'],'REJECT')
        self.assertEqual(result['source_trace'][-1]['rule_id'],'S_OB_CONS_TF')

    def test_smooth_approach_unknown_cannot_be_silently_true(self):
        case = self.case('OB_CONSERVATIVE')
        del case['facts']['smooth_approach']
        result = evaluate(case)
        self.assertEqual(result['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')
        self.assertEqual(result['source_trace'][-1]['rule_id'],'S_OB_APPROACH')

    def test_required_context_failure_for_each_branch(self):
        for branch in self.tree['branch_start_nodes']:
            case = self.case(branch)
            case['facts']['market_context']['value']=False
            self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'REJECT')

    def test_sfp_wick_raid_without_reclaim_is_not_valid_pattern(self):
        for side in ['LONG','SHORT']:
            case = self.case(direction=side)
            case['sfp']['raid']['close']=99 if side=='LONG' else 101
            self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'REJECT')

    def test_sfp_next_open_must_remain_reclaimed(self):
        for side in ['LONG','SHORT']:
            case = self.case(direction=side)
            case['sfp']['next_open']['open']=99 if side=='LONG' else 101
            result = evaluate(case)
            self.assertEqual(result['SOURCE_STRATEGY_DECISION'],'REJECT')
            self.assertEqual(result['source_trace'][-1]['predicate'],'sfp_next_open')

    def test_future_native_next_open_is_unresolved(self):
        case = self.case()
        case['sfp']['next_open']['known_at']=101
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')

    def test_open_schema_cannot_use_future_ohlc(self):
        case = self.case()
        case['sfp']['next_open']['high']=1000
        with self.assertRaisesRegex(ValueError,'future OHLC'):
            evaluate(case)

    def test_named_fact_future_completion_produces_unknown(self):
        case = self.case('STB_BTS')
        case['facts']['stb_raid_absorption_structure']['completed_at']=101
        case['facts']['stb_raid_absorption_structure']['known_at']=80
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')

    def test_open_at_same_timestamp_requires_previous_close_phase(self):
        case = self.case('OB_DIRECT')
        case['event']='OPEN'
        case['facts']['ob_formation'].update(known_at=100,completed_at=100)
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')
        case['facts']['ob_formation']['phase']='PREVIOUS_CLOSE'
        self.assertTrue(evaluate(case)['source_conditions_pass'])

    def test_future_dependency_and_inconsistent_known_at_are_unknown(self):
        case = self.case('OB_CONSERVATIVE')
        fact = case['facts']['smooth_approach']
        fact['dependencies']=[{'known_at':101,'completed_at':101,'evidence':'future structural approach end'}]
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')
        del fact['dependencies']
        fact.update(known_at=70,completed_at=80)
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')

    def test_meaningful_adverse_waits_until_known_sweep(self):
        case = self.case()
        pool = case['liquidity'][0]
        pool['role']='ADVERSE'
        self.assertFalse(adverse_state(case))
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'REJECT')
        pool['sweep']={'known_at':101,'completed_at':101,'evidence':'future sweep'}
        self.assertFalse(adverse_state(case))
        pool['sweep'].update(known_at=99,completed_at=99)
        self.assertTrue(adverse_state(case))
        self.assertTrue(evaluate(case)['source_conditions_pass'])

    def test_target_fta_not_adverse_and_unknown_role_not_no_adverse(self):
        case = self.case()
        for role in ['TARGET','FTA','IRRELEVANT']:
            case['liquidity'][0]['role']=role
            self.assertTrue(adverse_state(case))
        case['liquidity'][0]['role']='OLD_CONTEXTUAL_POOL_UNPROVEN'
        self.assertIsNone(adverse_state(case))
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'UNRESOLVED')

    def test_fvg_neighbour_wick_gap_required_both_sides(self):
        for side in ['LONG','SHORT']:
            case = self.case('FVG_POI',side)
            self.assertTrue(evaluate(case)['source_conditions_pass'])
            case['fvg'][2]['low' if side=='LONG' else 'high']=100
            self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'REJECT')

    def test_ote_source_interval_not_universal_sfp_gate(self):
        case = self.case('OTE_CONFLUENCE')
        self.assertTrue(evaluate(case)['source_conditions_pass'])
        case['entry']=100
        self.assertEqual(evaluate(case)['SOURCE_STRATEGY_DECISION'],'REJECT')
        case['branch']='SFP'
        case['facts']=self.case()['facts']
        self.assertTrue(evaluate(case)['source_conditions_pass'])

    def test_range_and_fta_exit_components_keep_ambiguity(self):
        profile = exit_profile('RANGE_AGGRESSIVE')
        self.assertEqual(profile['first_fraction'],0.8)
        self.assertEqual(profile['optional_remainder'],0.2)
        self.assertIsNone(profile['remainder_rule'])
        self.assertEqual(exit_profile('OB_DIRECT')['status'],'UNRESOLVED')
        self.assertEqual(exit_profile('OB_DIRECT','FULL_FTA')['first_fraction'],1)
        self.assertIsNone(exit_profile('OB_DIRECT','PARTIAL_FTA')['first_fraction'])
        with self.assertRaises(ValueError):
            exit_profile('RANGE_AGGRESSIVE','FULL_FTA')

    def test_primary_stop_cannot_move_to_tp1_breakeven(self):
        self.assertEqual(protective_stop(96),96)
        with self.assertRaisesRegex(ValueError,'forbids'):
            protective_stop(96,requested_move=100)

    def test_sl_on_liquidity_level_fails_primary_rule(self):
        case = self.case('OB_DIRECT')
        case['facts']['sl_off_liquidity']['value']=False
        result = evaluate(case)
        self.assertEqual(result['SOURCE_STRATEGY_DECISION'],'REJECT')
        self.assertEqual(result['source_trace'][-1]['rule_id'],'S_SL_OFF_POOL')

    def test_native_sfp_body_invalid_exit_no_future_or_lower_tf(self):
        for side in ['LONG','SHORT']:
            case = self.case(direction=side)
            candle = {'close':95 if side=='LONG' else 105,'tf':60,'known_at':99,
                      'completed_at':99,'evidence':'native pattern chart CLOSE'}
            self.assertTrue(sfp_body_invalid(case,candle))
            candle['tf']=5
            self.assertIsNone(sfp_body_invalid(case,candle))
            candle['tf']=60
            candle['completed_at']=101
            self.assertIsNone(sfp_body_invalid(case,candle))

    def test_stop_source_conflict_is_retained_with_primary_scope(self):
        conflicts = json.loads((SPEC/'source_conflict_registry.json').read_text())['conflicts']
        conflict = next(c for c in conflicts if c['conflict_id']=='C_STOP_BE')
        self.assertEqual(conflict['status'],'PRIMARY_SCOPE_RESOLVED')
        self.assertIn('S_SUPPLEMENT_BE',conflict['rules'])
        self.assertTrue(any(r['rule_id']=='S_SUPPLEMENT_BE' for r in self.rules))
        self.assertNotIn('S_SUPPLEMENT_BE',{node['rule_id'] for node in self.tree['nodes']})

    def test_project_cost_owner_and_outcome_fields_never_source_filters(self):
        case = self.case('OB_DIRECT')
        result = evaluate(case)
        case.update(project_edge_cost_ratio=100,formal_H1_H4_owner=True,
                    future_duration_hours=0.01,future_net_pnl=-99999,future_win_rate=1)
        self.assertEqual(evaluate(case),result)
        self.assertEqual(project_admission(result)['admission'],'SOURCE_NOT_ALLOWED')

    def test_prefix_future_mutation_replay_and_mode_parity_all_branches(self):
        for branch in self.tree['branch_start_nodes']:
            for side in ['LONG','SHORT']:
                case = self.case(branch,side)
                # Only future facts/history/outcomes change; timestamps stay beyond cutoff.
                case['facts']['not_a_source_predicate']={'value':True,'known_at':200,'completed_at':200,'evidence':'future'}
                result = evaluate(case)
                prefix = copy.deepcopy(case)
                del prefix['facts']['not_a_source_predicate']
                self.assertEqual(result,evaluate(prefix))
                changed = copy.deepcopy(case)
                changed['facts']['not_a_source_predicate']['value']=False
                changed['future_candles']=[{'high':9999,'low':-9999,'close':0,'completed_at':200}]
                self.assertEqual(result,evaluate(changed))
                self.assertEqual(result,evaluate(json.loads(json.dumps(case))))
                shadow = copy.deepcopy(case)
                shadow['mode']='SHADOW'
                self.assertEqual(result,evaluate(shadow))

    def test_future_relevant_fact_cannot_flip_unknown_to_pass(self):
        case = self.case('OB_CONSERVATIVE')
        fact = case['facts']['smooth_approach']
        fact.update(known_at=200,completed_at=200,value=False)
        before = evaluate(case)
        fact['value']=True
        self.assertEqual(before,evaluate(case))
        del case['facts']['smooth_approach']
        self.assertEqual(before,evaluate(case))

    def test_unresolved_source_never_admitted_live_or_v1_allow(self):
        for branch in self.tree['branch_start_nodes']:
            result = evaluate(self.case(branch))
            self.assertFalse(project_admission(result)['trade_entry_allowed'])
        case = self.case()
        case['mode']='LIVE'
        with self.assertRaises(ValueError):
            evaluate(case)
        tree = copy.deepcopy(self.tree)
        tree['ALLOW_enabled']=True
        with self.assertRaisesRegex(ValueError,'frozen'):
            evaluate(self.case(),tree)


if __name__=='__main__':
    unittest.main()
