"""Validate/freeze an outcome-free spec and archive-scoped immutable audit tree."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha1, sha256
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from original_strategy_spec_contract import (
    SPEC,
    evaluate,
    load_contract,
    synthetic_case,
)

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO/'data/reports/original_strategy_spec_v1_2026_10_11'
AUDIT = REPO/'data/reports/source_fidelity_2026_10_11'
AUDIT_COMMIT = 'c2d1e8cfb94637caaf150bb9c508cb011c3e85ba'
BASELINE = '19404ec0f4a7dd39b93c76240b6ad605278f0646'
MANIFEST = SPEC/'freeze_manifest.json'
CODE = ['ORIGINAL_STRATEGY_SPEC_PROTOCOL.md','scripts/build_original_strategy_spec_v1.py',
        'scripts/original_strategy_spec_contract.py','scripts/verify_original_strategy_spec_v1.py',
        'tests/test_original_strategy_spec_v1.py']
SOURCE_ROOT = REPO/'data/source_materials/original_strategy_spec_v1_2026_10_11'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def git_tree(commit):
    raw = subprocess.check_output(['git','ls-tree','-rz',commit],cwd=REPO)
    result = {}
    for line in raw.split(b'\0'):
        if not line:
            continue
        metadata,name = line.split(b'\t',1)
        mode,kind,oid = metadata.decode().split()
        assert kind=='blob'
        result[name.decode()]={'mode':mode,'git_blob':oid}
    return result


def archived_audit():
    tree = git_tree(AUDIT_COMMIT)
    baseline = git_tree(BASELINE)
    assert set(baseline)<=set(tree)
    assert all(tree[name]==blob for name,blob in baseline.items())
    for name,blob in tree.items():
        path = REPO/name
        payload = str(path.readlink()).encode() if blob['mode']=='120000' else path.read_bytes()
        actual = sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload,usedforsecurity=False).hexdigest()
        assert actual==blob['git_blob'], ('Archived baseline/audit file changed',name)
    delivery = json.loads((AUDIT/'delivery_manifest.json').read_text())
    delivery_path = str((AUDIT/'delivery_manifest.json').relative_to(REPO))
    expected = set(tree)-set(baseline)-{delivery_path}
    assert expected==set(delivery['artifacts'])
    dependencies = {}
    for section in ('artifacts','source_dependencies'):
        for name,value in delivery[section].items():
            assert digest(REPO/name)==value, ('Audit sealed dependency changed',name)
            dependencies[name]=value
    return {'audit_commit':AUDIT_COMMIT,'baseline_commit':BASELINE,'audit_tree_blobs':len(tree),
            'baseline_blobs':len(baseline),'audit_manifest_artifacts':len(expected),
            'Git_blob_identity':'PASS','archived_delivery_membership':'PASS',
            'verification_scope':'Membership at immutable c2d1 tree; later additive spec files allowed, old manifest not rewritten'},dependencies


def validate(*,write=False):
    rules = json.loads((SPEC/'original_strategy_rule_registry_v1.json').read_text())['rules']
    mapping = {r['rule_id']:r for r in rules}
    assert len(mapping)==len(rules)
    assert {r['category'] for r in rules}=={'SOURCE_RULE','PROJECT_POLICY','TECHNICAL_NORMALIZATION'}
    sources = {}
    for rule in rules:
        assert rule['applicability'] in ('mandatory','optional','context-dependent')
        for field in ('literal_meaning','executable_interpretation','confidence','known_at_semantics'):
            assert rule[field]
        for dependency in rule.get('normalization_dependencies',[]):
            assert mapping[dependency]['category']=='TECHNICAL_NORMALIZATION'
        if rule['category'] != 'SOURCE_RULE':
            assert not rule['source_document'] and not rule['page_diagram']
            continue
        assert rule['page_diagram']
        for ref in rule['page_diagram']:
            assert digest(REPO/ref['source_document'])==ref['source_sha256']
            assert digest(REPO/ref['text'])==ref['text_sha256']
            text = (REPO/ref['text']).read_text()
            if ref['source_id'].startswith('SW'):
                chunks = re.split(r'===== \w+ PAGE (\d+) =====',text)
                units = {int(chunks[i]):chunks[i+1].strip() for i in range(1,len(chunks),2)}
            else:
                text = text.split('PART word/document.xml\n',1)[1].split('\nPART ',1)[0]
                units = {int(m.group(1)):m.group(2) for m in re.finditer(r'^P(\d+) (.*)$',text,re.MULTILINE)}
            passage = '\n'.join(units[i] for i in range(ref['first'],ref['last']+1))
            assert passage==ref['literal_passage'], ('Literal source citation mismatch',rule['rule_id'])
            sources[ref['source_id']]=ref['source_sha256']
    assert len(sources)==13
    tree = load_contract()
    nodes = {n['node_id']:n for n in tree['nodes']}
    assert len(nodes)==len(tree['nodes'])
    referenced = set()
    terminals = {'SOURCE_CONDITIONS_PASS','SOURCE_REJECT','SOURCE_UNRESOLVED'}
    for node in nodes.values():
        rule = mapping[node['rule_id']]
        assert rule['category']=='SOURCE_RULE'
        assert node['source_citation']==rule['page_diagram']
        assert node['known_at']
        for status in ['PASS','FAIL','UNKNOWN']:
            assert node[status] in nodes or node[status] in terminals
        referenced.add(node['rule_id'])
    assert not tree['ALLOW_enabled'] and tree['verdict']=='NOT_IDENTIFIABLE'
    assert 'P_FORMAL_OWNER' not in referenced and 'S_SUPPLEMENT_BE' not in referenced
    branches = json.loads((SPEC/'branch_contracts.json').read_text())['branches']
    assert set(tree['branch_start_nodes'])=={b['branch_id'] for b in branches}
    examples = []
    for branch in branches:
        assert len(branch['stages'])==11
        for rid in branch['source_rules']:
            assert mapping[rid]['category']=='SOURCE_RULE'
        for support in branch['stage_source_support'].values():
            for item in support:
                assert item['rule_id'] in branch['source_rules']
                refs = mapping[item['rule_id']]['page_diagram']
                expected = [{field:ref[field] for field in
                             ('source_id','page_or_paragraph','source_document','source_sha256')} for ref in refs]
                assert item['citations']==expected
        for side in ['LONG','SHORT']:
            example = synthetic_case(branch['branch_id'],side,tree)
            outcome = evaluate(example,tree)
            assert outcome['source_conditions_pass'] and not outcome['trade_entry_allowed']
            examples.append({'input':example,'result':outcome})
    conflicts = json.loads((SPEC/'source_conflict_registry.json').read_text())['conflicts']
    conflict_ids = {c['conflict_id'] for c in conflicts}
    assert all(set(r['conflicts'])<=conflict_ids for r in rules)
    for name in ['EXIT','STOP_BREAKEVEN','BRANCH_PRIORITY','TF_MAPPING','ADVERSE_LIQUIDITY','RE_ENTRY']:
        text = (SPEC/f'RESOLVER_{name}.md').read_text()
        for section in ['Relevant source passages','Все диаграммы','Приоритет','Конфликты','Deterministic','Known_at']:
            assert section in text
    anchors = json.loads((REPORT/'diagram_anchor_index.json').read_text())
    assert len({a['sha256'] for a in anchors})==122
    old_visual = json.loads((AUDIT/'source_visual_review/media_review_manifest.json').read_text())
    assert {a['sha256'] for a in anchors}==set(old_visual['references'])
    for name in CODE:
        text = (REPO/name).read_text()
        assert not re.search(r'^(?:from|import) (?:sklearn|crypto_bot|ccxt|requests|httpx)',text,re.MULTILINE)
    archive,dependencies = archived_audit()
    receipt = {'status':'PASS','verdict':'NOT_IDENTIFIABLE','source_documents':13,
               'rules':len(rules),'source_rules':sum(r['category']=='SOURCE_RULE' for r in rules),
               'project_policies':sum(r['category']=='PROJECT_POLICY' for r in rules),
               'technical_normalizations':sum(r['category']=='TECHNICAL_NORMALIZATION' for r in rules),
               'source_tree_nodes':len(nodes),'branches_and_components':len(branches),
               'synthetic_long_short_examples':len(examples),'diagram_inline_anchors':len(anchors),
               'unique_docx_diagrams':122,'literal_source_citation_validation':'PASS',
               'source_registry_tree_consistency':'PASS','conflicts_not_hidden':'PASS',
               'immutable_previous_stage':archive,'trade_entry_allowed':False,
               'production_changes':False,'financial_backtest_started':False}
    if write:
        if MANIFEST.exists():
            raise ValueError('Frozen spec cannot rewrite validation output; use --resume-existing')
        save(REPORT/'synthetic_LONG_SHORT_examples.json',examples)
        save(REPORT/'qa/validation_receipt.json',receipt)
    return receipt,dependencies


def artifacts():
    names = set(CODE)
    for root in [SPEC,REPORT,SOURCE_ROOT]:
        names.update(str(p.relative_to(REPO)) for p in root.rglob('*') if p.is_file() and p!=MANIFEST)
    assert not any('__pycache__' in name for name in names)
    return sorted(names)


def freeze():
    if MANIFEST.exists():
        raise ValueError('Completed freeze exists; use --resume-existing')
    receipt,dependencies = validate()
    names = artifacts()
    save(MANIFEST, {'status':'FROZEN_NOT_IDENTIFIABLE','version':1,'verdict':'NOT_IDENTIFIABLE',
        'registered_at_UTC':datetime.now(UTC).isoformat(),'audit_commit':AUDIT_COMMIT,'baseline':BASELINE,
        'branch':'medium-term-source-research','pre_freeze_HEAD':subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'artifacts':{name:digest(REPO/name) for name in names},'immutable_audit_dependencies':dependencies,
        'new_outcomes_viewed':False,'profitability_backtest_started':False,'trade_entry_allowed':False,
        'production_integration':False,'QA':receipt,
        'membership_scope':'Explicit spec/evidence namespace and five producer/test files; self-manifest excluded',
        'next_step':'Resolve material questions; create and freeze a NEW spec version before implementation/backtest'})
    print('SPEC_FROZEN',len(names),'artifacts; NOT_IDENTIFIABLE; financial backtest disabled')


def resume():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest['status']=='FROZEN_NOT_IDENTIFIABLE' and not manifest['trade_entry_allowed']
    assert set(artifacts())==set(manifest['artifacts']), 'Frozen spec namespace membership changed'
    for section in ['artifacts','immutable_audit_dependencies']:
        for name,expected in manifest[section].items():
            assert digest(REPO/name)==expected, ('Frozen checksum changed',name)
    receipt,_ = validate()
    assert receipt==manifest['QA']
    print('VERIFIED_RESUME ORIGINAL_STRATEGY_SPEC_v1',len(manifest['artifacts']),
          'artifacts; immutable audit+baseline PASS; NOT_IDENTIFIABLE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--validate',action='store_true')
    group.add_argument('--freeze',action='store_true')
    group.add_argument('--resume-existing',action='store_true')
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.resume_existing:
        resume()
    else:
        receipt,_ = validate(write=True)
        print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    main()
