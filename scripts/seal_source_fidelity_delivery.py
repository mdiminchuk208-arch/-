"""Seal or strictly verify the complete additive source-fidelity delivery."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_source_fidelity_state import REPO, ROOT
from run_medium_term_research import digest, evidence_json, resume, write_json
from verify_source_fidelity_audit import verify_state_resume

from crypto_bot.research.v2_common import write_csv
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio

BASELINE = '19404ec0f4a7dd39b93c76240b6ad605278f0646'
MANIFEST = ROOT / 'delivery_manifest.json'


def additions():
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', BASELINE], cwd=REPO)
    original = {row.split(b'\t', 1)[1].decode() for row in tree.split(b'\0') if row}
    listed = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=REPO)
    current = {row.decode() for row in listed.split(b'\0') if row}
    return sorted(current - original)


def nested_proofs():
    verify_state_resume()
    folder = ROOT / 'matched_exits'
    lock = json.loads((folder / 'run_lock.json').read_text())
    for name, expected in lock['dependencies'].items():
        assert digest(REPO / name) == expected, ('Matched exit dependency changed', name)
    fingerprint = sha256(evidence_json(lock).encode()).hexdigest()
    assert resume(folder, fingerprint, True)
    assert VirtualPortfolio(mode='BACKTEST').trade_entry_allowed is False
    assert VirtualPortfolio(mode='SHADOW').trade_entry_allowed is False


def seal_delivery():
    if MANIFEST.exists():
        raise ValueError('Completed delivery exists; use --resume-existing, never overwrite it')
    nested_proofs()
    changes = set(additions())
    changes.update(str(p.relative_to(REPO)) for p in (MANIFEST, ROOT / 'changed_files.csv'))
    write_csv(ROOT / 'changed_files.csv', [{'status': 'A', 'path': name} for name in sorted(changes)])
    inventory = json.loads((ROOT / 'source_inventory.json').read_text())
    sources = {name: digest(REPO / name) for material in inventory['materials']
               for name in (material['original'], material['text'])}
    for name in ['data/source_materials/cryptology_2026_10_09/cryptology.zip',
                 'data/source_materials/cryptology_2026_10_09/ocr_manifest.json',
                 'RESEARCH_PROTOCOL.md', 'EXIT_RESEARCH_PROTOCOL.md']:
        sources[name] = digest(REPO / name)
    for path in sorted((REPO / 'data/source_materials/cryptology_2026_10_09/diagram_ocr').glob('*.txt')):
        sources[str(path.relative_to(REPO))] = digest(path)
    artifact_names = sorted(changes - {str(MANIFEST.relative_to(REPO))})
    assert all((REPO / name).is_file() for name in artifact_names)
    write_json(MANIFEST, {
        'status': 'COMPLETE', 'baseline': BASELINE, 'branch': 'medium-term-source-research',
        'sealed_at_UTC': datetime.now(UTC),
        'checkpoint_before_final_delivery': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'artifacts': {name: digest(REPO / name) for name in artifact_names},
        'source_dependencies': sources, 'source_documents': 13,
        'strict_membership': 'Every Git-visible addition relative to immutable baseline, except this self manifest',
        'baseline_identity_receipt': digest(ROOT / 'qa/immutable_and_known_times_receipt.json'),
        'nested_state_and_matched_exit_proofs': 'PASS', 'production_changes': False,
        'exact_strategy_A_B': 'UNIDENTIFIABLE_CONTRACT_GAPS_PRESERVED', 'trade_entry_allowed': False})
    print('DELIVERY_SEALED', len(artifact_names), 'artifacts', flush=True)


def verify_delivery():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest['status'] == 'COMPLETE' and manifest['trade_entry_allowed'] is False
    actual = set(additions()) - {str(MANIFEST.relative_to(REPO))}
    assert actual == set(manifest['artifacts']), 'Delivery artifact membership changed'
    for section in ('artifacts', 'source_dependencies'):
        for name, expected in manifest[section].items():
            assert digest(REPO / name) == expected, ('Delivery checksum changed', name)
    nested_proofs()
    print('VERIFIED_RESUME SOURCE_FIDELITY_DELIVERY', len(actual), 'artifacts', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--seal', action='store_true')
    action.add_argument('--resume-existing', action='store_true')
    args = parser.parse_args()
    (verify_delivery if args.resume_existing else seal_delivery)()


if __name__ == '__main__':
    main()
