"""Validate, freeze and verifiably resume an outcome-free executable profile."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha1, sha256

from original_strategy_executable_profile_v1 import (
    ACTIVE,
    ROOT,
    SPEC,
    evaluate,
    load_tree,
)
from verify_original_strategy_spec_v1 import (
    AUDIT_COMMIT,
    git_tree,
)
from verify_original_strategy_spec_v1 import MANIFEST as OLD_MANIFEST
from verify_original_strategy_spec_v1 import (
    resume as old_resume,
)

REPORT = ROOT / 'data/reports/original_strategy_spec_v1_1_2026_10_11'
REQUEST = ROOT / 'data/source_materials/original_strategy_spec_v1_1_2026_10_11'
MANIFEST = SPEC / 'freeze_manifest.json'
CODE = ['scripts/build_original_strategy_spec_v1_1.py', 'scripts/original_strategy_executable_profile_v1.py',
        'scripts/verify_original_strategy_spec_v1_1.py', 'tests/test_original_strategy_spec_v1_1.py']


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def artifact_names():
    names = set(CODE)
    for root in (SPEC, REPORT, REQUEST):
        names.update(str(p.relative_to(ROOT)) for p in root.rglob('*') if p.is_file() and p != MANIFEST)
    assert not any('__pycache__' in name for name in names)
    return sorted(names)


def immutable_parent():
    # Archive-scoped verifier checks all17851 archived audit/baseline Git blobs.
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        old_resume()
    parent_commit = '37cca859f700dc11e5741b964338e24d08f7a10f'
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', parent_commit, 'HEAD'], cwd=ROOT)
    parent_tree, audit_tree = git_tree(parent_commit), git_tree(AUDIT_COMMIT)
    assert all(parent_tree[name] == blob for name, blob in audit_tree.items())
    additions = set(parent_tree) - set(audit_tree)
    for name in additions:
        data = (ROOT / name).read_bytes()
        assert sha1(b'blob ' + str(len(data)).encode() + b'\0' + data, usedforsecurity=False).hexdigest() == parent_tree[name]['git_blob']
    return {'frozen_commit': '37cca859f700dc11e5741b964338e24d08f7a10f',
            'v1_manifest_sha256': checksum(OLD_MANIFEST), 'v1_artifacts': len(read(OLD_MANIFEST)['artifacts']),
            'verification': captured.getvalue().strip(), 'frozen_parent_additions': len(additions), 'status': 'PASS'}


def validate():
    parent = immutable_parent()
    old = read(SPEC.parent / 'original_strategy_spec_v1/original_strategy_rule_registry_v1.json')['rules']
    rules = read(SPEC / 'original_strategy_rule_registry_v1_1.json')['rules']
    lookup = {r['rule_id']: r for r in rules}
    assert len(lookup) == len(rules)
    for rule in old:
        assert lookup[rule['rule_id']] == rule, ('Inherited v1 record changed', rule['rule_id'])
    decisions = read(SPEC / 'user_resolution_registry.json')['decisions']
    assert {r['rule_id'] for r in decisions} == {f'U{i}' for i in range(1, 7)}
    for d in decisions:
        assert d == lookup[d['rule_id']] and d['category'] == 'USER_RESOLUTION_PRE_BACKTEST'
        assert not d['selection_is_source_rule'] and not d['outcomes_used']
        assert checksum(ROOT / d['authority']) == d['authority_sha256']
        assert all(lookup[r]['category'] == 'SOURCE_RULE' for r in d['source_support_rule_ids'])
        assert d['source_citations'] == [ref for rid in d['source_support_rule_ids'] for ref in lookup[rid]['page_diagram']]
    normals = read(SPEC / 'technical_normalization_registry.json')['profile_resolutions']
    for n in normals:
        assert n == lookup[n['rule_id']] and n['category'] == 'TECHNICAL_NORMALIZATION'
        assert n['registration'] == 'TECHNICAL_NORMALIZATION_PRE_BACKTEST'
        assert not n['source_claim'] and not n['outcomes_used'] and n['rationale']
    tree = load_tree()
    assert set(tree['active_branches']) == set(ACTIVE)
    for node in tree['source_nodes']:
        assert lookup[node['rule_id']]['category'] == 'SOURCE_RULE'
        assert node['source_citation'] == lookup[node['rule_id']]['page_diagram']
        assert not any(k in node for k in ('PASS', 'FAIL', 'UNKNOWN'))
    for node in tree['resolution_nodes']:
        assert all(lookup[r]['category'] != 'SOURCE_RULE' for r in node['rule_ids'])
    policies = read(SPEC / 'project_policy_registry.json')
    assert not policies['applied_inside_original']
    assert policies['rules'] == [r for r in old if r['category'] == 'PROJECT_POLICY']
    conflicts = read(SPEC / 'source_conflict_registry.json')
    assert conflicts['inherited_conflicts'] == read(SPEC.parent / 'original_strategy_spec_v1/source_conflict_registry.json')
    verdict = read(SPEC / 'IDENTIFIABILITY_VERDICT.json')
    assert verdict['EXECUTABLE_PROFILE_IDENTIFIABLE'] and not verdict['EXACT_ORIGINAL_IDENTIFIABLE']
    assert not verdict['automatic_ohlc_qualitative_detector_identifiable'] and verdict['remaining_evidence_limits']
    assert not verdict['trade_entry_allowed'] and not verdict['profitability_backtest_started']
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_original_strategy_spec_v1_1 import synthetic_case
    examples = []
    for branch in ACTIVE:
        for direction in ('LONG', 'SHORT'):
            case = synthetic_case(branch, direction)
            outcome = evaluate(case)
            assert outcome['SOURCE_STRATEGY_DECISION'] == 'ALLOW' and not outcome['trade_entry_allowed']
            examples.append({'kind': 'SYNTHETIC_CONTRACT_ONLY_NOT_TRADE', 'input': case, 'result': outcome})
    for name in CODE:
        text = (ROOT / name).read_text()
        assert not re.search(r'^(?:from|import) (?:sklearn|crypto_bot|ccxt|requests|httpx)', text, re.MULTILINE)
    qa = read(REPORT / 'qa/check_receipt.json')
    for check in qa['checks']:
        assert check['exit_code'] == 0, check
        assert checksum(ROOT / check['log']) == check['sha256'], check
    full = (ROOT / next(x['log'] for x in qa['checks'] if x['name'] == 'full_unittest')).read_text()
    focus = (ROOT / next(x['log'] for x in qa['checks'] if x['name'] == 'profile_unittest')).read_text()
    # Existing regression tests flush harmless captured stdout after unittest OK.
    assert re.search(r'Ran \d+ tests[^\n]*\n\nOK(?:\n|$)', full)
    assert re.search(r'Ran \d+ tests[^\n]*\n\nOK(?:\n|$)', focus)
    full_count = int(re.search(r'Ran (\d+) tests', full).group(1))
    focus_count = int(re.search(r'Ran (\d+) tests', focus).group(1))
    assert full_count == 611 + focus_count
    return {'status': 'PASS', 'parent': parent, 'source_rules': 53, 'inherited_rules': len(old),
            'user_resolutions': len(decisions), 'new_technical_normalizations': len(normals),
            'active_branches': len(ACTIVE), 'source_nodes': len(tree['source_nodes']),
            'synthetic_long_short_contracts': len(examples), 'full_tests': full_count, 'profile_tests': focus_count,
            'source_citation_consistency': 'PASS', 'v1_audit_baseline_immutability': 'PASS',
            'EXACT_ORIGINAL_IDENTIFIABLE': False, 'EXECUTABLE_PROFILE_IDENTIFIABLE': True,
            'identifiability_scope': verdict['identifiability_scope'], 'financial_backtest_started': False,
            'trade_entry_allowed': False}, examples


def validate_write():
    if MANIFEST.exists():
        raise ValueError('Frozen namespace cannot rewrite QA; use --resume-existing')
    receipt, examples = validate()
    save(REPORT / 'qa/validation_receipt.json', receipt)
    save(REPORT / 'synthetic_LONG_SHORT_contract_examples.json', examples)
    return receipt


def freeze():
    if MANIFEST.exists():
        raise ValueError('Existing freeze cannot be overwritten')
    receipt, _ = validate()
    assert receipt == read(REPORT / 'qa/validation_receipt.json')
    save(MANIFEST, {'version': '1.1', 'profile': 'ORIGINAL_STRATEGY_EXECUTABLE_PROFILE_v1',
        'status': 'FROZEN_PRE_OUTCOME', 'registered_at_UTC': datetime.now(UTC).isoformat(),
        'pre_freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'branch': 'medium-term-source-research', 'parent': receipt['parent'],
        'artifacts': {n: checksum(ROOT / n) for n in artifact_names()}, 'QA': receipt,
        'EXECUTABLE_PROFILE_IDENTIFIABLE': True, 'EXACT_ORIGINAL_IDENTIFIABLE': False,
        'outcomes_viewed_for_decisions': False, 'profitability_backtest_started': False,
        'trade_entry_allowed': False, 'production_integration': False,
        'next_step': 'STOP. Separate subsequent user instruction required before financial backtest.'})
    print('FROZEN_PRE_OUTCOME', checksum(MANIFEST), len(read(MANIFEST)['artifacts']), 'artifacts')


def resume():
    sealed = read(MANIFEST)
    assert sealed['status'] == 'FROZEN_PRE_OUTCOME' and not sealed['trade_entry_allowed']
    assert set(artifact_names()) == set(sealed['artifacts']), 'Frozen v1.1 namespace membership changed'
    for name, digest in sealed['artifacts'].items():
        assert checksum(ROOT / name) == digest, ('Frozen v1.1 artifact changed', name)
    receipt, _ = validate()
    assert receipt == sealed['QA']
    print('VERIFIED_RESUME v1.1; SHA256', checksum(MANIFEST), 'QA', receipt['full_tests'],
          'tests; v1/audit/baseline unchanged; financial_backtest_started=false')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--validate', action='store_true')
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--resume-existing', action='store_true')
    args = parser.parse_args()
    if args.resume_existing:
        resume()
    elif args.freeze:
        freeze()
    else:
        print(json.dumps(validate_write(), ensure_ascii=False))


if __name__ == '__main__':
    main()
