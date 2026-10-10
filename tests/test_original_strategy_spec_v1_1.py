"""Pre-outcome profile resolutions, causal evidence and lifecycle regression."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from original_strategy_executable_profile_v1 import (
    ACTIVE,
    SPEC,
    atr14,
    evaluate,
    lifecycle,
    load_tree,
    new_position,
    retire_idea,
    select_ideas,
)


def record(**kwargs):
    return {'known_at': 50000, 'completed_at': 50000, 'evidence': 'SYNTHETIC explicit source annotation',
            'source_validated': True, **kwargs}


def synthetic_case(branch='OB_CONSERVATIVE', direction='LONG'):
    """Annotated contract fixture, NOT a strategy trade or historical detector."""
    tree = load_tree()
    case = {'symbol': 'SYNTHETIC', 'branch': branch, 'direction': direction, 'mode': 'BACKTEST',
            'event': 'CLOSE', 'decision_at': 60000, 'setup_tf': 60, 'trigger_tf': 15, 'tick_size': '0.1',
            'idea_poi_id': 'source-poi-1',
            'instrument_metadata': record(tick_size='0.1'),
            'facts': {n['predicate']: record(value=True) for n in tree['source_nodes'] if n['branch_id'] == branch}}
    case['facts'].update({p: record(value=True) for p in ('ltf_bos_source_entry', 'range_reclaim_retest', 'breaker_confirmation')})
    case['entry_poi'] = record(id='entry-poi-1', parent_poi_id='source-poi-1', low='99', high='101', formation_known_at=54000,
                               known_at=55000, completed_at=55000)
    case['source_defining_zone'] = record(id='source-poi-1', low='95', high='105')
    case['reaction'] = record(known_at=52500, completed_at=52500)
    case['bos'] = record(known_at=53000, completed_at=53000, tf=15)
    kinds = {'OB_CONSERVATIVE': 'SOURCE_OB_EXTREME', 'BREAKER': 'RAID_IMPULSE_EXTREME',
             'SFP': 'SFP_PATTERN_EXTREME', 'STB_BTS': 'MANIPULATION_RAID_EXTREME',
             'RANGE_CONSERVATIVE': 'DEVIATION_INVALIDATION_EXTREME',
             'RANGE_RETURN_CHOCH': 'DEVIATION_INVALIDATION_EXTREME'}
    case['stop_anchor'] = record(kind=kinds[branch], price='95' if direction == 'LONG' else '105', unique=True)
    case['contextual_poi_inventory'] = record(complete_for_known_prefix=True)
    case['contextual_pois'] = [
        record(id='near-m15', low='108', high='110', tf=15, contextual=True, opposing=True),
        record(id='far-h4', low='118', high='120', tf=240, contextual=True, opposing=True)] if direction == 'LONG' else [
        record(id='near-m15', low='90', high='92', tf=15, contextual=True, opposing=True),
        record(id='far-h4', low='80', high='82', tf=240, contextual=True, opposing=True)]
    case['range_exit'] = record(id='range-1', low='85', high='115', unique=True)
    case['liquidity_inventory'] = record(complete_for_known_prefix=True)
    case['liquidity'] = [record(role='TARGET_OR_FUEL')]
    case['zone_first_test'] = record(value=True)
    case['facts']['sl_off_liquidity']['checked_price'] = '94.9' if direction == 'LONG' else '105.1'
    case['identity_evidence'] = {k: record(id=v) for k, v in
                                 [('context', 'context-origin-1'), ('formation', 'formation-1'),
                                  ('confirmation', 'confirmation-1'), ('poi', 'source-poi-1')]}
    if branch == 'SFP':
        case['facts']['sl_off_liquidity']['checked_price'] = '91.8' if direction == 'LONG' else '108.2'
        raid = record(low='96' if direction == 'LONG' else '98', high='102' if direction == 'LONG' else '104',
                      close='101' if direction == 'LONG' else '99', known_at=50400, completed_at=50400)
        case['sfp'] = {'raid': raid, 'old_level': record(price='100', known_at=20000, completed_at=20000),
                       'next_open': {'open': '101' if direction == 'LONG' else '99', 'known_at': 50401,
                                     'evidence': 'next OPEN only'}}
        case['stop_anchor']['price'] = raid['low' if direction == 'LONG' else 'high']
        case['atr_bars'] = [record(high='102', low='98', close='100', tf=60,
                                  completed_at=3600 * (i + 1), known_at=3600 * (i + 1)) for i in range(15)]
        case['atr_bars'][-1].update(raid, tf=60)
        # 15 native bars ending at50400, starting at0, not54000.
        for i, bar in enumerate(case['atr_bars']):
            bar.update(completed_at=i * 3600, known_at=i * 3600)
    return case


class OriginalExecutableProfileTests(unittest.TestCase):
    def case(self, branch='OB_CONSERVATIVE', side='LONG'):
        return synthetic_case(branch, side)

    def position(self, branch='OB_CONSERVATIVE', side='LONG'):
        selected = select_ideas([self.case(branch, side)])['selected'][0]
        return new_position(selected)

    def test_all_active_branches_long_short_allow_plan_only(self):
        for b in ACTIVE:
            for d in ('LONG', 'SHORT'):
                with self.subTest(branch=b, direction=d):
                    result = evaluate(self.case(b, d))
                    self.assertEqual(result['SOURCE_STRATEGY_DECISION'], 'ALLOW')
                    self.assertFalse(result['trade_entry_allowed'])
                    self.assertFalse(result['plan']['project_overlays_applied'])

    def test_user_selections_never_promoted_source(self):
        rules = json.loads((SPEC / 'original_strategy_rule_registry_v1_1.json').read_text())['rules']
        for r in rules:
            if r['rule_id'].startswith('U'):
                self.assertEqual(r['category'], 'USER_RESOLUTION_PRE_BACKTEST')
                self.assertFalse(r['selection_is_source_rule'])
        self.assertEqual(sum(r['category'] == 'SOURCE_RULE' for r in rules), 53)

    def test_source_tree_policy_injection_rejected(self):
        t = load_tree()
        next(n for n in t['source_nodes'] if n['branch_id'] == 'OB_CONSERVATIVE')['rule_id'] = 'P_ANTI_SCALP'
        with self.assertRaisesRegex(ValueError, 'Non-source'):
            evaluate(self.case(), t)

    def test_original_v1_verdict_preserved(self):
        old = SPEC.parent / 'original_strategy_spec_v1'
        self.assertEqual(json.loads((old / 'IDENTIFIABILITY_VERDICT.json').read_text())['verdict'], 'NOT_IDENTIFIABLE')
        new = json.loads((SPEC / 'IDENTIFIABILITY_VERDICT.json').read_text())
        self.assertFalse(new['EXACT_ORIGINAL_IDENTIFIABLE'])
        self.assertFalse(new['automatic_ohlc_qualitative_detector_identifiable'])

    def test_full_fta_nearest_price_across_context_tfs(self):
        for d, p in [('LONG', '108'), ('SHORT', '92')]:
            result = evaluate(self.case(side=d))
            self.assertEqual(result['plan']['target']['price'], p)
            self.assertEqual(result['plan']['target']['poi_ids'], ['near-m15'])
            self.assertEqual(result['plan']['target']['total_fraction'], '1')

    def test_future_poi_cannot_beat_nearest_known_target(self):
        c = self.case()
        before = evaluate(c)
        c['contextual_pois'].append(record(id='future', low='102', high='103', known_at=60001,
                                         completed_at=60001, contextual=True, opposing=True))
        self.assertEqual(before, evaluate(c))
        c['contextual_pois'][-1]['low'] = '-1000'
        self.assertEqual(before, evaluate(c))

    def test_incomplete_or_unknown_context_inventory_waits(self):
        for field in ('contextual_poi_inventory', 'liquidity_inventory'):
            c = self.case()
            c[field]['complete_for_known_prefix'] = False
            self.assertEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'WAIT')
        c = self.case()
        c['contextual_pois'][0]['contextual'] = None
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_CONTEXTUAL_FTA')

    def test_range_80_20_close_same_inside_zone(self):
        for d, p in [('LONG', '114.9'), ('SHORT', '85.1')]:
            t = evaluate(self.case('RANGE_CONSERVATIVE', d))['plan']['target']
            self.assertEqual(t['price'], p)
            self.assertEqual(t['fractions_same_zone'], ['0.8', '0.2'])
            self.assertEqual(t['kind'], 'TECHNICAL_RESOLUTION_OPTIONAL_REMAINDER_DISABLED')

    def test_range_source_defined_nearer_fta_same_80_20_zone(self):
        for d, price in [('LONG', '108'), ('SHORT', '92')]:
            c = self.case('RANGE_CONSERVATIVE', d)
            c['range_exit']['source_exit_poi'] = c['contextual_pois'][0]
            plan = evaluate(c)['plan']['target']
            self.assertEqual(plan['price'], price)
            self.assertEqual(plan['fractions_same_zone'], ['0.8', '0.2'])

    def test_initial_branch_stop_extreme_no_percent_buffer(self):
        for b in set(ACTIVE) - {'SFP'}:
            self.assertEqual(evaluate(self.case(b))['plan']['stop'], '94.9')
            self.assertEqual(evaluate(self.case(b, 'SHORT'))['plan']['stop'], '105.1')

    def test_nonunique_or_inconsistent_stop_waits(self):
        for edit in ('unique', 'price'):
            c = self.case()
            c['stop_anchor'][edit] = False if edit == 'unique' else '97'
            self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_STOP_GEOMETRY')

    def test_sfp_atr14_known_pattern_bars_and_outward_rounding(self):
        c = self.case('SFP')
        self.assertEqual(atr14(c), Decimal(58) / 14)
        self.assertEqual(evaluate(c)['plan']['stop'], '91.8')
        c = self.case('SFP', 'SHORT')
        self.assertEqual(evaluate(c)['plan']['stop'], '108.2')

    def test_future_wrong_tf_or_noncontiguous_atr_waits(self):
        for field, val in [('known_at', 60001), ('completed_at', 99999), ('tf', 15)]:
            c = self.case('SFP')
            c['atr_bars'][5][field] = val
            self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_STOP_GEOMETRY')

    def test_atr_cannot_substitute_later_nonpattern_bar(self):
        c = self.case('SFP')
        c['atr_bars'][-1].update(completed_at=54000, known_at=54000)
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_STOP_GEOMETRY')

    def test_sfp_no_automatic_market_entry(self):
        c = self.case('SFP')
        del c['facts']['ltf_bos_source_entry']
        self.assertEqual(evaluate(c)['status'], 'WAIT_SFP_LOWER_BOS_ENTRY_SEARCH')

    def test_ob_causal_reaction_bos_new_poi_order(self):
        c = self.case()
        c['reaction']['known_at'] = 54000
        self.assertEqual(evaluate(c)['status'], 'WAIT_CAUSAL_REACTION_BOS')
        c = self.case()
        c['entry_poi']['formation_known_at'] = 52000
        self.assertEqual(evaluate(c)['status'], 'WAIT_NEW_POI_AFTER_BOS')

    def test_sfp_refinement_cannot_precede_formation(self):
        c = self.case('SFP')
        c['reaction'].update(known_at=50000, completed_at=50000)
        self.assertEqual(evaluate(c)['status'], 'WAIT_CAUSAL_REACTION_BOS')

    def test_inactive_source_permitted_alternatives_not_admitted(self):
        for b in ('OB_DIRECT', 'RANGE_AGGRESSIVE', 'FVG_POI', 'OTE_CONFLUENCE'):
            c = self.case()
            c['branch'] = b
            self.assertEqual(evaluate(c)['status'], 'REJECT_INACTIVE_PROFILE_BRANCH')

    def test_tf_roles_without_mandatory_owner_or_alignment(self):
        c = self.case('STB_BTS')
        before = evaluate(c)
        c.update(formal_H1_H4_owner=False, d1_trend='SHORT', h4_trend='SHORT', h1_owner=False)
        self.assertEqual(before, evaluate(c))
        c['facts']['trend_aligned']['value'] = False
        self.assertEqual(evaluate(c)['status'], 'REJECT_SOURCE_CONDITION')

    def test_medium_scan_and_strict_m15_refinement_bounds(self):
        for tf in (15, 60, 240, 1440):
            c = self.case()
            c['setup_tf'] = tf
            expected = 'WAIT_NO_AVAILABLE_LOWER_TF' if tf == 15 else 'SOURCE_ALLOW_PLAN_ONLY'
            self.assertEqual(evaluate(c)['status'], expected)
        for tf in (1, 5, 30, 10080):
            c = self.case()
            c['setup_tf'] = tf
            self.assertEqual(evaluate(c)['status'], 'REJECT_OUTSIDE_EXECUTABLE_UNIVERSE')
        c = self.case()
        c['trigger_tf'] = 5
        self.assertEqual(evaluate(c)['status'], 'WAIT_NO_AVAILABLE_LOWER_TF')

    def test_unknown_liquidity_is_not_pass(self):
        for value in ('UNKNOWN', 'OLD751_FLAG'):
            c = self.case()
            c['liquidity'][0]['role'] = value
            self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_LIQUIDITY_CONTEXT')

    def test_adverse_wait_sweep_future_sweep_not_clear(self):
        c = self.case()
        p = c['liquidity'][0]
        p['role'] = 'ADVERSE'
        self.assertEqual(evaluate(c)['status'], 'WAIT_SWEEP')
        p['sweep'] = record(known_at=60001, completed_at=60001)
        self.assertEqual(evaluate(c)['status'], 'WAIT_SWEEP')

    def test_sweep_requires_full_revalidation_not_auto_entry(self):
        c = self.case()
        c['liquidity'][0].update(role='ADVERSE', sweep=record(known_at=56000, completed_at=56000))
        self.assertEqual(evaluate(c)['status'], 'WAIT_POST_SWEEP_REVALIDATION')
        c['post_sweep_revalidation'] = record(value=True, known_at=57000, completed_at=57000)
        c['facts']['smooth_approach']['value'] = False
        self.assertEqual(evaluate(c)['status'], 'REJECT_SOURCE_CONDITION')
        c['facts']['smooth_approach']['value'] = True
        self.assertEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'ALLOW')

    def test_target_fuel_neutral_not_blanket_adverse(self):
        for role in ('NEUTRAL', 'TARGET_OR_FUEL'):
            c = self.case()
            c['liquidity'][0]['role'] = role
            self.assertEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'ALLOW')

    def test_qualitative_missing_and_future_dependency_wait(self):
        c = self.case()
        del c['facts']['smooth_approach']
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_SOURCE_GEOMETRY')
        c = self.case()
        c['facts']['smooth_approach']['dependencies'] = [record(known_at=60001, completed_at=60001)]
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_SOURCE_GEOMETRY')

    def test_first_test_no_reuse_and_new_source_identity(self):
        c = self.case()
        out = select_ideas([c])
        key = out['selected'][0]['identity']['physical_id']
        state = retire_idea(out['state'], key, zone_used=True)
        self.assertEqual(select_ideas([c], state)['selected'][0]['status'], 'WAIT_FIRST_TEST_ONLY')
        new = copy.deepcopy(c)
        new['idea_poi_id'] = 'new-source-poi'
        new['entry_poi'].update(id='new-entry-poi', parent_poi_id='new-source-poi')
        for k in ('formation', 'confirmation', 'poi'):
            new['identity_evidence'][k]['id'] = 'new-' + k
        new['identity_evidence']['poi']['id'] = 'new-source-poi'
        self.assertEqual(select_ideas([new], state)['selected'][0]['SOURCE_STRATEGY_DECISION'], 'ALLOW')

    def test_zone_first_test_annotation_cannot_be_false(self):
        c = self.case()
        c['zone_first_test']['value'] = False
        self.assertEqual(evaluate(c)['status'], 'WAIT_FIRST_TEST_ONLY')

    def test_stop_liquidity_clearance_must_cover_computed_stop(self):
        c = self.case()
        c['facts']['sl_off_liquidity']['checked_price'] = '95'
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_STOP_LIQUIDITY')

    def test_cannot_relabel_used_formation_as_new_poi(self):
        c = self.case()
        out = select_ideas([c])
        key = out['selected'][0]['identity']['physical_id']
        state = retire_idea(out['state'], key, zone_used=True)
        c['idea_poi_id'] = 'relabelled-poi'
        c['entry_poi']['parent_poi_id'] = 'relabelled-poi'
        c['identity_evidence']['poi']['id'] = 'relabelled-poi'
        self.assertEqual(select_ideas([c], state)['selected'][0]['status'], 'WAIT_FIRST_TEST_ONLY')

    def test_sfp_old_level_must_be_known_before_raid_bar(self):
        c = self.case('SFP')
        c['sfp']['old_level'].update(known_at=50000, completed_at=50000)
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_SOURCE_GEOMETRY')

    def test_source_false_and_future_completion_do_not_allow(self):
        for field, value in [('value', False), ('known_at', 60001), ('completed_at', 60001)]:
            c = self.case()
            c['facts']['ob_formation'][field] = value
            self.assertNotEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'ALLOW')

    def test_material_conflict_no_branch_priority_and_order_invariance(self):
        a = self.case()
        b = self.case('BREAKER')
        b['source_defining_zone']['low'] = '94'
        b['stop_anchor']['price'] = '94'
        b['facts']['sl_off_liquidity']['checked_price'] = '93.9'
        self.assertEqual(select_ideas([a, b])['selected'][0]['status'], 'WAIT_BRANCH_CONFLICT')
        self.assertEqual(select_ideas([a, b])['state'], select_ideas([b, a])['state'])

    def test_direction_conflict_same_physical_poi_waits(self):
        self.assertEqual(select_ideas([self.case(), self.case(side='SHORT')])['selected'][0]['status'], 'WAIT_BRANCH_CONFLICT')

    def test_same_idea_two_branches_confluence_one_position(self):
        out = select_ideas([self.case(), self.case('BREAKER')])
        self.assertEqual(len(out['state']['active']), 1)
        self.assertEqual(out['selected'][0]['confluence'], ['BREAKER', 'OB_CONSERVATIVE'])
        again = select_ideas([self.case('BREAKER')], out['state'])
        self.assertEqual(again['selected'][0]['status'], 'CONFLUENCE_ONLY')

    def test_later_conflict_preserves_prior_active_state(self):
        state = select_ideas([self.case()])['state']
        c = self.case('BREAKER')
        c['source_defining_zone']['low'] = '94'
        c['stop_anchor']['price'] = '94'
        c['facts']['sl_off_liquidity']['checked_price'] = '93.9'
        out = select_ideas([c], state)
        self.assertEqual(out['selected'][0]['status'], 'WAIT_BRANCH_CONFLICT')
        self.assertEqual(out['state'], state)

    def test_physical_batch_cannot_mix_events_or_run_backward(self):
        a, b = self.case(), self.case('BREAKER')
        b['decision_at'] = 60001
        with self.assertRaisesRegex(ValueError, 'same-event'):
            select_ideas([a, b])
        state = select_ideas([a])['state']
        a['decision_at'] = 59999
        with self.assertRaisesRegex(ValueError, 'backward'):
            select_ideas([a], state)

    def test_policy_overlays_not_original_input(self):
        c = self.case()
        old = evaluate(c)
        c.update(project_edge_cost_ratio=0, project_total_risk=99, canonical_exit=[40, 30, 30], cost_adjusted_be=True)
        self.assertEqual(old, evaluate(c))

    def test_future_holding_pnl_inputs_forbidden_recursively(self):
        for key in ('pnl', 'future_holding_time', 'winrate'):
            c = self.case()
            c['facts']['smooth_approach'][key] = 1
            with self.assertRaisesRegex(ValueError, 'forbidden'):
                evaluate(c)

    def test_live_or_private_mode_not_supported(self):
        c = self.case()
        c['mode'] = 'LIVE'
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_prefix_future_mutation_and_deterministic_replay_all_branches(self):
        for b in ACTIVE:
            for d in ('LONG', 'SHORT'):
                c = self.case(b, d)
                expected = evaluate(c)
                suffix = record(id='future-zone', role='ADVERSE', known_at=99999, completed_at=99999)
                c['liquidity'].append(suffix)
                c['contextual_pois'].append(copy.deepcopy(suffix))
                suffix['role'] = 'UNKNOWN'
                self.assertEqual(expected, evaluate(c))
                self.assertEqual(evaluate(c), evaluate(json.loads(json.dumps(c))))
                c['mode'] = 'SHADOW'
                self.assertEqual(expected, evaluate(c))

    def test_known_at_completed_open_phase_contract(self):
        c = self.case()
        c['event'] = 'OPEN'
        c['facts']['ob_formation'].update(known_at=60000, completed_at=60000)
        self.assertEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'WAIT')
        c['facts']['ob_formation']['phase'] = 'PREVIOUS_CLOSE'
        self.assertEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'ALLOW')

    def test_decimal_quotes_not_lexical_geometry_or_nonfinite(self):
        c = self.case('SFP')
        self.assertEqual(evaluate(c)['SOURCE_STRATEGY_DECISION'], 'ALLOW')
        c['tick_size'] = 'NaN'
        c['instrument_metadata']['tick_size'] = 'NaN'
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_tick_metadata_must_be_known_before_entry(self):
        c = self.case()
        c['instrument_metadata'].update(known_at=60001, completed_at=60001)
        self.assertEqual(evaluate(c)['status'], 'WAIT_UNRESOLVED_INSTRUMENT_METADATA')

    def test_fta_tie_preserves_all_ids(self):
        c = self.case()
        t = copy.deepcopy(c['contextual_pois'][0])
        t['id'] = 'same-price'
        c['contextual_pois'].append(t)
        self.assertEqual(evaluate(c)['plan']['target']['poi_ids'], ['near-m15', 'same-price'])

    def test_lifecycle_plan_does_not_mean_filled(self):
        p = self.position()
        self.assertEqual(p['state'], 'PENDING_LIMIT')
        p = lifecycle(p, {'kind': 'QUOTE', 'known_at': 60001, 'price': '102', 'evidence': 'synthetic quote'})
        self.assertEqual(p['state'], 'PENDING_LIMIT')

    def test_candidate_plan_cannot_skip_physical_idea_selection(self):
        with self.assertRaisesRegex(ValueError, 'physical-idea'):
            new_position(evaluate(self.case()))

    def test_lifecycle_full_target_and_stop_fixed_long_short(self):
        for d in ('LONG', 'SHORT'):
            p = self.position(side=d)
            p = lifecycle(p, {'kind': 'QUOTE', 'known_at': 60001, 'price': '100', 'evidence': 'synthetic quote'})
            self.assertEqual(p['state'], 'OPEN')
            with self.assertRaisesRegex(ValueError, 'no BE'):
                lifecycle(p, {'kind': 'QUOTE', 'known_at': 60002, 'price': '102', 'requested_stop': '100', 'evidence': 'quote'})
            p = lifecycle(p, {'kind': 'QUOTE', 'known_at': 60002, 'price': p['plan']['target']['price'], 'evidence': 'quote'})
            self.assertEqual(p['state'], 'CLOSED')
            self.assertEqual(p['closed_fraction'], '1')

    def test_sfp_manual_body_close_pattern_tf_only(self):
        for d in ('LONG', 'SHORT'):
            p = self.position('SFP', d)
            p = lifecycle(p, {'kind': 'QUOTE', 'known_at': 60001, 'price': '100', 'evidence': 'quote'})
            bar = {'kind': 'BAR_CLOSE', 'known_at': 63000, 'completed_at': 63000, 'tf': 60,
                   'high': '102' if d == 'LONG' else '106', 'low': '94' if d == 'LONG' else '98',
                   'close': '95' if d == 'LONG' else '105', 'evidence': 'synthetic completed body'}
            self.assertEqual(lifecycle(p, bar)['reason'], 'SFP_PATTERN_BODY_INVALIDATION')
            bar['tf'] = 15
            with self.assertRaises(ValueError):
                lifecycle(p, bar)

    def test_unordered_bar_no_assumed_fill_or_stop_target_order(self):
        p = self.position()
        bar = {'kind': 'BAR_CLOSE', 'known_at': 63000, 'completed_at': 63000, 'tf': 60,
               'high': '120', 'low': '90', 'close': '100', 'evidence': 'synthetic ambiguous bar'}
        self.assertEqual(lifecycle(p, bar)['state'], 'WAIT_INTRABAR_ORDER')
        p = lifecycle(p, {'kind': 'QUOTE', 'known_at': 60001, 'price': '100', 'evidence': 'quote'})
        self.assertEqual(lifecycle(p, bar)['state'], 'WAIT_INTRABAR_ORDER')

    def test_future_bar_and_backward_quote_rejected(self):
        p = self.position()
        with self.assertRaises(ValueError):
            lifecycle(p, {'kind': 'QUOTE', 'known_at': 59999, 'price': '100', 'evidence': 'quote'})
        with self.assertRaises(ValueError):
            lifecycle(p, {'kind': 'BAR_CLOSE', 'known_at': 63000, 'completed_at': 63001, 'tf': 60, 'evidence': 'future'})


if __name__ == '__main__':
    unittest.main()
