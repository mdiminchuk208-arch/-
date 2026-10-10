"""Build a new outcome-free profile namespace from frozen v1, never rewrite v1."""
from __future__ import annotations

import copy
import csv
import json
from hashlib import sha256

from original_strategy_executable_profile_v1 import ACTIVE, ROOT, SPEC

OLD = ROOT / 'docs/original_strategy_spec_v1'
REPORT = ROOT / 'data/reports/original_strategy_spec_v1_1_2026_10_11'
REQUEST = ROOT / 'data/source_materials/original_strategy_spec_v1_1_2026_10_11/user_request.txt'
RESOLUTIONS = [
    ('U1', 'EXIT', ['S_FTA', 'S_FTA_EXIT_OPTIONS', 'S_RANGE_EXIT'],
     ('FULL_CONTEXTUAL_FTA_EXIT: 100% at nearest known opposing contextual POI, all eligible TF. '
     'Range: source80% inside opposite boundary and remaining20% in same zone; optional breakout remainder disabled.')),
    ('U2', 'STOP', ['S_STOP_FIXED', 'S_OB_DIRECT_STOP', 'S_BREAKER_STOPS', 'S_SFP_STOP', 'S_SFP_BODY_EXIT'],
     ('FIXED_INITIAL_PROTECTIVE_STOP; OB source extreme; Breaker raid/impulse extreme; SFP ATR14 from pattern extreme; '
     'STB manipulation raid; Range deviation/invalidation; nonunique anchor WAIT_UNRESOLVED_STOP_GEOMETRY. No TP1→BE.')),
    ('U3', 'ENTRY_BRANCH', ['S_OB_CONS_TRIGGER', 'S_SFP_REFINE', 'S_RANGE_CONSERVATIVE', 'S_STB_ENTRY', 'S_BREAKER_FORMATION'],
     ('OB reaction→M15 BOS→new POI; SFP completed pattern→M15 BOS→source entry search; '
     'Range reclaim/return/retest; STB0.5; confirmed Breaker/conservative SL. '
     'First complete physical idea, others confluence; material conflict WAIT_BRANCH_CONFLICT; no fitted priority.')),
    ('U4', 'TIMEFRAMES', ['S_FRACTAL', 'S_SFP_TF', 'S_OB_CONS_TF', 'S_MEDIUM_PREFERENCE'],
     ('Scan M15/H1/H4/D1. D1 global, H4 local/context, H1 primary, M15 refinement and supported setups. '
     'No mandatory ladder/formal owner/all-TF trend alignment. Conservative refinement only M15, strictly lower; '
     'M15 OB/SFP needing lower refinement waits, not a source prohibition. No M1/M5 in this executable profile.')),
    ('U5', 'LIQUIDITY_GEOMETRY', ['S_ADVERSE_BLOCK', 'S_ADVERSE_WAIT', 'S_EQ_STRUCTURE', 'S_POOL_SCOPE', 'S_OB_APPROACH'],
     ('ADVERSE→WAIT_SWEEP; TARGET_OR_FUEL/NEUTRAL not blockers; UNKNOWN→WAIT_UNRESOLVED_LIQUIDITY_CONTEXT. '
     'After sweep revalidate, no auto entry. No old751 blanket filter, no loss deletion or hidden thresholds. '
     'Qualitative geometry requires explicit causal source evidence; insufficient evidence UNKNOWN/WAIT.')),
    ('U6', 'REENTRY', ['S_OB_FIRST_TEST', 'S_SND_FORMATION'],
     ('FIRST_TEST_ONLY. Consumed OB/POI cannot be reused. New formation+confirmation+new POI identity '
     'and full validation only; no cooldown/random90%/retry count.')),
]
NORMALIZATIONS = [
    ('N11_ENTRY', ('Proximal entry edge for source new-POI/Breaker/Range retest; STB midpoint. '
     'Round inside POI to instrument tick. Selects one source-permitted limit price, never a market fill.'),
     'Smallest explicit quote convention; no optimized intrazone offset.', ['U3']),
    ('N11_TARGET', ('Non-Range opposing POI proximal edge, first along direction; tied price preserves all IDs. '
     'Range target smallest tick strictly inside opposite source boundary, or nearer explicit source-defined '
     'contextual FTA supplied by Range exit evidence; both80/20 at that same price.'),
     'Minimum representable inside distance; no fitted near-boundary percentage.', ['U1']),
    ('N11_STOP_TICK', ('Non-SFP strictly beyond source extreme by minimum representable tick; '
     'SFP ATR stop round outward to tick, no extra percentage buffer. Instrument tick metadata must be causally known.'),
     'An extreme is not a tradable strictly-beyond price without tick convention.', ['U2']),
    ('N11_ATR_SMA14', ('SMA of14 True Ranges, 15 contiguous completed pattern-TF bars ending at raid CLOSE. '
     'Previous close included; latestOHLC equals pattern. ATR frozen before confirmation and entry.'),
     'Request fixes14 bars but not smoother; rolling mean avoids recursive seed/warmup assumptions.', ['U2']),
    ('N11_BODY_TF', 'SFP manual body invalidation uses completed pattern-TF CLOSE only, strict beyond extreme.',
     'Source does not exhaustively arbitrate all candle TF; pattern-TF convention stated explicitly.', ['U2', 'U4']),
    ('N11_IDENTITY', ('SHA256(symbol, contextual structural origin ID, original idea POI canonical ID) physical key; '
     'setup key adds direction, formation and confirmation IDs. Evidence adapters must use stable canonical source IDs. '
     'Refined entry POI references parent idea POI. Consumed zone and formation cannot be relabelled as new setup. '
     'First complete validation event owns plan; no branch token in identity.'),
     'Prevents duplicate branch trades without lifetime symbol ban or time cooldown.', ['U3', 'U6']),
    ('N11_BATCH', ('Evaluate complete same-event branch set; conflict before tie selection. '
     'Equivalent plans use earliest validation event; lexical branch label only labels identical-plan provenance. '
     'Later conflict blocks new admission and preserves previously observed state.'),
     'Total deterministic ordering of equivalent plans, not financial branch ranking.', ['U3']),
    ('N11_EVIDENCE', ('Typed source_validated causal annotations supply meaningful liquidity, tilt, smooth approach, '
     'whole impulse, range clarity, protected endpoints and branch confirmation. Missing/future/nonunique evidence waits. '
     'No quantitative qualitative classifier claimed. Inventory attestation covers known prefix only.'),
     'User explicitly requires WAIT rather than materially arbitrary thresholds.', ['U5']),
    ('N11_EVENTS', ('Strictly ordered causal quotes drive synthetic limit/SL/FTA lifecycle. '
     'Bar simultaneous touches or unobserved fill ordering WAIT_INTRABAR_ORDER; no assumed SL-first/TP-first.'),
     'Causal lifecycle contract, not an exchange fill model; monetary costs outside source.', ['U1', 'U2', 'U3']),
    ('N11_SOURCE_SCOPE', ('Primary setup-specific SW9/SW12 contracts retain v1 source hierarchy. '
     'DOC19 stronger OB/Breaker IMB and DOC20 BE alternatives stay visible and inactive; not universal AND gates.'),
     'Resolve profile scope explicitly without claiming the historical original unique.', ['U3', 'U5']),
]


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    path = SPEC / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n' if not isinstance(value, str) else value,
                    encoding='utf-8')


def build():
    if (SPEC / 'freeze_manifest.json').exists():
        raise ValueError('Frozen v1.1 cannot be rebuilt; use verifier --resume-existing')
    SPEC.mkdir(parents=True, exist_ok=True)
    rules = read(OLD / 'original_strategy_rule_registry_v1.json')['rules']
    mapping = {r['rule_id']: r for r in rules}
    inherited = copy.deepcopy(rules)
    decisions = []
    request_hash = sha256(REQUEST.read_bytes()).hexdigest()
    for rid, name, source_ids, text in RESOLUTIONS:
        decisions.append({'rule_id': rid, 'category': 'USER_RESOLUTION_PRE_BACKTEST', 'group': name,
            'decision': text, 'source_support_rule_ids': source_ids,
            'source_citations': [ref for s in source_ids for ref in mapping[s]['page_diagram']],
            'authority': str(REQUEST.relative_to(ROOT)), 'authority_sha256': request_hash,
            'selection_is_source_rule': False, 'outcomes_used': False, 'registration': 'PRE_BACKTEST'})
    normals = [{'rule_id': rid, 'category': 'TECHNICAL_NORMALIZATION',
                'registration': 'TECHNICAL_NORMALIZATION_PRE_BACKTEST', 'decision': text,
                'rationale': reason, 'resolves': resolves, 'outcomes_used': False,
                'source_claim': False} for rid, text, reason, resolves in NORMALIZATIONS]
    write('original_strategy_rule_registry_v1_1.json', {'version': '1.1', 'rules': inherited + decisions + normals,
          'inherited_source_rules_unchanged': True, 'no_source_selection_promotion': True})
    write('user_resolution_registry.json', {'decisions': decisions})
    write('project_policy_registry.json', {'rules': [r for r in inherited if r['category'] == 'PROJECT_POLICY'],
          'applied_inside_original': False, 'boundary': 'SOURCE→PROJECT_ADMISSION→RISK→MANAGEMENT→EXECUTION'})
    write('technical_normalization_registry.json', {'inherited_unresolved_records':
          [r for r in inherited if r['category'] == 'TECHNICAL_NORMALIZATION'],
          'profile_resolutions': normals, 'inherited_gaps_not_relabelled_source': True})
    write('source_conflict_registry.json', {'inherited_conflicts': read(OLD / 'source_conflict_registry.json'),
          'executable_scope': 'N11_SOURCE_SCOPE', 'exact_original_verdict': 'NOT_IDENTIFIABLE',
          'profile_conflict_behavior': 'WAIT_BRANCH_CONFLICT', 'source_alternatives_deleted': False})
    alternatives = read(OLD / 'source_permitted_variants.json')
    write('source_permitted_variants.json', {'frozen_v1_alternatives': alternatives,
          'profile_inactive': ['OB_DIRECT', 'RANGE_AGGRESSIVE', 'PARTIAL_FTA', 'RANGE_BREAKOUT_REMAINDER',
                               'STB_EDGE', 'BREAKER_AGGRESSIVE_STOP', 'REPEAT_SAME_ZONE'], 'outcome_comparison': False})
    old_tree = read(OLD / 'ORIGINAL_STRATEGY_DECISION_TREE_v1.json')
    implemented = {'no_adverse_proven', 'source_plan_complete', 'fixed_stop_plan',
                   'fta_plan', 'range_exit_plan', 'ob_test_eligible'}
    source_nodes = [n for n in old_tree['nodes'] if n['branch_id'] in ACTIVE and n['predicate'] not in implemented]
    stages = [
        ('PROFILE_SCOPE', ['U3', 'U4', 'N11_STOP_TICK'], 'REJECT_INACTIVE_PROFILE_BRANCH / REJECT_OUTSIDE_EXECUTABLE_UNIVERSE / WAIT_UNRESOLVED_INSTRUMENT_METADATA'),
        ('SOURCE_EVIDENCE', ['N11_EVIDENCE', 'N11_SOURCE_SCOPE'], 'REJECT_SOURCE_CONDITION / WAIT_UNRESOLVED_SOURCE_GEOMETRY'),
        ('CONFIRMED_PATH', ['U3', 'U4'], 'WAIT_NO_AVAILABLE_LOWER_TF / WAIT_SFP_LOWER_BOS_ENTRY_SEARCH / WAIT_RANGE_RECLAIM_RETEST / WAIT_BREAKER_CONFIRMATION / WAIT_CAUSAL_REACTION_BOS / WAIT_NEW_POI_AFTER_BOS'),
        ('LIQUIDITY', ['U5'], 'WAIT_SWEEP / WAIT_UNRESOLVED_LIQUIDITY_CONTEXT / WAIT_POST_SWEEP_REVALIDATION'),
        ('ENTRY', ['U3', 'N11_ENTRY'], 'WAIT_UNRESOLVED_ENTRY_GEOMETRY'),
        ('STOP', ['U2', 'N11_STOP_TICK', 'N11_ATR_SMA14'], 'WAIT_UNRESOLVED_STOP_GEOMETRY / REJECT_STOP_GEOMETRY / WAIT_UNRESOLVED_STOP_LIQUIDITY'),
        ('TARGET', ['U1', 'N11_TARGET'], 'WAIT_UNRESOLVED_CONTEXTUAL_FTA'),
        ('IDENTITY_FIRST_TEST', ['U6', 'N11_IDENTITY'], 'WAIT_UNRESOLVED_SETUP_IDENTITY / WAIT_FIRST_TEST_ONLY'),
        ('PHYSICAL_IDEA', ['U3', 'N11_BATCH'], 'WAIT_BRANCH_CONFLICT / CONFLUENCE_ONLY'),
        ('ALLOW_PLAN', ['U1', 'U2', 'U3'], 'SOURCE_ALLOW_PLAN_ONLY'),
    ]
    tree = {'version': '1.1', 'active_branches': list(ACTIVE), 'source_nodes': source_nodes,
            'source_nodes_scope': 'These preserved v1 nodes supply predicates/citations only; legacy edge fields omitted.',
            'resolution_nodes': [{'node_id': name, 'rule_ids': ids, 'failure': fail,
                 'failure_statuses': fail.split(' / '), 'known_at': 'All evidence/dependencies completed and known before decision; OPEN previous-CLOSE phase explicit',
                 'PASS': stages[i + 1][0] if i + 1 < len(stages) else 'PROJECT_ADMISSION_REQUIRED'}
                 for i, (name, ids, fail) in enumerate(stages)],
            'EXACT_ORIGINAL_IDENTIFIABLE': False, 'EXECUTABLE_PROFILE_IDENTIFIABLE': True,
            'trade_entry_allowed': False, 'ALLOW_means': 'Source plan only; project/execution admission never enabled'}
    for node in source_nodes:
        for field in ('PASS', 'FAIL', 'UNKNOWN', 'next'):
            node.pop(field, None)
    write('ORIGINAL_STRATEGY_EXECUTABLE_DECISION_TREE_v1.json', tree)
    write('ORIGINAL_STRATEGY_EXECUTABLE_DECISION_TREE_v1.md', '# Executable decision tree v1\n\n'
          + '\n'.join(f'{i + 1}. {name}: {", ".join(ids)}; failure `{fail}`.' for i, (name, ids, fail) in enumerate(stages))
          + '\n\nSource predicates use SOURCE_RULE citations only. Resolution steps explicitly reference U/N records. '
          'evaluate supplies candidate ALLOW plans; select_ideas is mandatory before activating a physical idea. '
          'Candidate ALLOW does not bypass PHYSICAL_IDEA conflict/first-test checks. '
          'ALLOW is a source plan, `trade_entry_allowed=false`. Lifecycle: PENDING_LIMIT→OPEN→CLOSED, '
          'or CANCELLED/WAIT_INTRABAR_ORDER. No monetary outputs.\n')
    contracts = read(OLD / 'branch_contracts.json')
    for branch in contracts['branches']:
        bid = branch['branch_id']
        branch['frozen_v1_status'] = branch['status']
        branch['profile_status'] = 'ACTIVE_CAUSAL_EVIDENCE_CONTRACT' if bid in ACTIVE else 'INACTIVE_OR_COMPONENT_ONLY'
        branch['source_stage_descriptions_are_unmodified_v1_evidence'] = True
        branch['resolution_dependencies'] = [d['rule_id'] for d in decisions]
        if bid in ACTIVE:
            branch['entry'] = 'STB midpoint' if bid == 'STB_BTS' else 'Source new/retest POI proximal edge'
            branch['stop'] = next(d['decision'] for d in decisions if d['rule_id'] == 'U2')
            branch['target'] = 'Range80+20 same inside zone' if bid.startswith('RANGE') else 'Nearest opposing contextual FTA100%'
            branch['unknown_geometry'] = 'WAIT, never silent PASS'
        write(f'branch_contracts/{bid}.md', f'# {bid} executable contract\n\n'
              f'Status: {branch["profile_status"]}. See branch_contracts.json for preserved11 source stages/citations.\n\n'
              + ('Entry: ' + branch['entry'] + '. Stop: U2. Target: ' + branch['target'] + '.\n\n' if bid in ACTIVE else '')
              + 'No independent component trade is invented. U1–U6 are user decisions, not SOURCE_RULE.\n')
    write('branch_contracts.json', contracts)
    decisions_text = '# User resolution decisions — PRE_BACKTEST\n\n'
    for item in decisions:
        decisions_text += f'## {item["rule_id"]} — {item["group"]}\n\nCategory: USER_RESOLUTION_PRE_BACKTEST.\n\n{item["decision"]}\n\n'
        decisions_text += 'Source permits/supports: ' + ', '.join(item['source_support_rule_ids']) + '; selection is user authority.\n\n'
        write(f'RESOLVER_{item["group"]}.md', '# ' + item['group'] + '\n\n' + item['decision'] + '\n\n'
              + 'Authority: USER_RESOLUTION_PRE_BACKTEST ' + item['rule_id'] + '. Source alternatives preserved.\n\n'
              + '\n'.join(f'- {ref["source_id"]} {ref["page_or_paragraph"]}; originalSHA256 {ref["source_sha256"]}.'
                          for ref in item['source_citations']) + '\n')
    write('USER_RESOLUTION_DECISIONS.md', decisions_text + f'Full request SHA256: `{request_hash}`.\n')
    with (SPEC / 'SOURCE_VS_RESOLUTION_MATRIX.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['resolution_id', 'group', 'classification', 'source_rules', 'selected_executable_behavior'])
        for d in decisions:
            writer.writerow([d['rule_id'], d['group'], d['category'], ';'.join(d['source_support_rule_ids']), d['decision']])
        for n in normals:
            writer.writerow([n['rule_id'], ';'.join(n['resolves']), n['registration'], '', n['decision']])
    write('TF_ROLE_MATRIX.csv', 'TF,minutes,role,scan,universal_gate\n'
          'M15,15,refinement_and_branch_supported_setup,true,false\nH1,60,primary_medium_term,true,false\n'
          'H4,240,local_structure_context_POI,true,false\nD1,1440,global_context,true,false\n'
          'M1,1,source_permitted_other_profile,false,false\nM5,5,source_permitted_other_profile,false,false\n')
    limits = ['No unique automatic source algorithm for meaningful liquidity/smooth approach/whole impulse/range clarity/structural endpoints.',
              'Without explicit causal source-validated evidence these cases WAIT; no inferred boolean annotations from the old engine.',
              'Canonical POI/context/formation IDs and complete contextual inventory require a source-faithful adapter; no historical performance validation done.',
              'OHLC simultaneous event order unresolved: WAIT_INTRABAR_ORDER; no exchange fill realism claimed.']
    write('IDENTIFIABILITY_VERDICT.json', {'EXACT_ORIGINAL_IDENTIFIABLE': False,
          'exact_original_verdict': 'NOT_IDENTIFIABLE', 'EXECUTABLE_PROFILE_IDENTIFIABLE': True,
          'identifiability_scope': 'Deterministic conditional causal-evidence admission + price plan + ordered-event lifecycle. '
              'Not an identifiable automatic qualitative OHLC detector or exact historical original.',
          'source_faithful_executable_profile_frozen_before_outcome': True,
          'blocking_profile_choice_ambiguities': [], 'remaining_evidence_limits': limits,
          'automatic_ohlc_qualitative_detector_identifiable': False, 'production_integration': False,
          'profitability_backtest_started': False, 'trade_entry_allowed': False})
    write('ORIGINAL_STRATEGY_SPEC_v1_1.md', '# ORIGINAL_STRATEGY_SPEC v1.1\n\n'
          'Source-faithful executable profile frozen before outcome. Frozen v1 remains NOT_IDENTIFIABLE. '
          'Exact historical original remains NOT_IDENTIFIABLE. User choices do not become SOURCE_RULE.\n\n'
          + decisions_text + '\n## Registered machine conventions\n\n'
          + '\n'.join(f'- {rid}: {text} Rationale: {reason}' for rid, text, reason, _ in NORMALIZATIONS)
          + '\n\n## Explicit limits\n\n' + '\n'.join('- ' + x for x in limits) + '\n')
    write('ORIGINAL_STRATEGY_EXECUTABLE_PROFILE_v1.md', '# ORIGINAL_STRATEGY_EXECUTABLE_PROFILE v1\n\n'
          'Executable admission is deterministic on a declared causal-evidence schema. '
          'It is not an automatic qualitative detector: absent evidence waits. No financial/backtest runner imports.\n\n'
          'Primary universe M15/H1/H4/D1; active SFP, confirmed OB, Breaker, STB/BTS, two conservative Range descriptions. '
          'Same physical Range descriptions are confluence, not duplicate trades. M15 SFP/OB cannot refine to a strictly lower '
          'available TF and therefore WAIT_NO_AVAILABLE_LOWER_TF. This is profile coverage, not a source SFP prohibition.\n\n'
          'A SOURCE ALLOW constructs entry/initialSL/causalFTA or Range exit. It does not admit execution. '
          'Project anti-scalp ratio3, totalrisk6%, daily/correlation/leverage, canonical40/30/30, costBE, exchange safety remain '
          'outside Original. Production canonical code is untouched.\n\n'
          'Evidence schema: see executable_evidence_schema.md; implementation scripts/original_strategy_executable_profile_v1.py. '
          'Before first financial run a separate instruction is required.\n')
    write('executable_evidence_schema.md', '# Causal evidence schema\n\n'
          'Prices are positive decimal strings; instrument_metadata is timestamped public metadata whose tick_size '
          'must match the selected tick_size, not a tuned threshold. '
          'decision_at integer UTC seconds; OPEN/CLOSE with previous-close phase at same OPEN timestamp; '
          'mode BACKTEST/SHADOW only. Every structural/qualitative record has evidence, known_at, completed_at, '
          'optional recursive dependencies and source_validated=true; known_at≥completed_at and ≤decision_at. '
          'Source citations come from immutable rule registry; boolean facts are explicit supplied annotations, never detector proof.\n\n'
          'entry_poi low/high/id plus formation_known_at; branch stop_anchor kind/price/unique. SFP: raid, old_level, '
          'Range range_exit has source low/high boundaries and optional causal source_exit_poi for a nearer source-defined FTA. '
          'next_open containing only open/known_at, ATR15 contiguous candles. '
          'reaction→M15bos→newpoi chronological chain. source-specific facts must be source_validated. '
          'contextual_poi_inventory and liquidity_inventory attest complete_for_known_prefix; lists may contain future '
          'records, which are not accessed before known_at. No hidden H4/D1-only target selection.\n\n'
          'identity_evidence contains context/formation/confirmation/poi canonical IDs and timestamps. '
          'poi is original physical idea POI; entry_poi.parent_poi_id references it. '
          'sl_off_liquidity.checked_price must exactly match computed initial stop, not a different candidate quote. '
          'IDs must denote same physical objects across branches, never branch-specific serials; adapter is responsible. '
          'zone_first_test explicit causal unused-zone evidence plus persistent used zone/setup state. '
          'Caller passes all same-event source candidates to select_ideas before any lifecycle position is activated. '
          'Candidate ALLOW from evaluate is not a substitute for physical-idea selection.\n\n'
          'Liquidity roles ADVERSE/TARGET_OR_FUEL/NEUTRAL/UNKNOWN; known sweep requires explicit full source revalidation '
          'attestation and re-evaluation, no automatic entry. Whole impulse/smooth/tilt/endpoints without proof UNKNOWN.\n\n'
          'Lifecycle: explicit ordered QUOTE events or completed pattern-TF BAR_CLOSE; monetary outcomes and '
          'future holding duration forbidden recursively. Unordered OHLC does not invent limit fills.\n')
    write('REPRODUCIBILITY.md', '# Reproducibility\n\n'
          'Before freeze: build_original_strategy_spec_v1_1.py; unittest discover; verifier --validate; verifier --freeze. '
          'After freeze use only `python scripts/verify_original_strategy_spec_v1_1.py --resume-existing`. '
          'Verifier checks v1 resume, c2d1/archive baseline, SHA256 membership and source/resolution separation. '
          'All frozen paths immutable; subsequent QA receipts can be additive outside namespace. No financial run command.\n')
    print('BUILT v1.1; six user resolutions; no outcomes read')


if __name__ == '__main__':
    build()
