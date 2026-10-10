"""Seal all verified full40 detector segments after interrupted aggregation."""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from run_source_permitted_bybit import REPO, digest, verify_manifest, write_json

from crypto_bot.strategy.source_pdf_native import evidence_json


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--input', type=Path, required=True)
    a = p.parse_args(); root = a.input.resolve()
    if (root / 'manifest.json').exists(): raise ValueError('retain existing complete manifest')
    lock = json.loads((root / 'run_lock.json').read_text())
    for name, h in lock['implementation'].items(): assert digest(REPO / name) == h, name
    for name, r in lock['inputs'].items(): assert digest(REPO / name) == r['sha256'], name
    assert len(lock['inputs']) == 40 and sum(r['candles'] for r in lock['inputs'].values()) == 993575
    code_hash = sha256(evidence_json(lock['implementation']).encode()).hexdigest()
    for symbol in lock['policy']['symbol_priority']:
        native = {str(tf): lock['inputs'][f'data/history/bybit/{symbol}/{tf}.csv'] for tf in lock['policy']['native_timeframes']}
        fp = sha256(evidence_json({'code': code_hash, 'inputs': native, 'symbol': symbol}).encode()).hexdigest()
        verify_manifest(root / 'segments' / symbol, fp)
    assert not list((root / 'selections').glob('*')), 'preserve partial aggregation; require review of its distinct scope'
    artifacts = {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}
    write_json(root / 'manifest.json', {'status': 'COMPLETE', 'scope': 'FULL40_DETECTOR_CORPUS_ONLY',
        'provisional_context_execution': 'INTERRUPTED_BY_32_GIB_OOM_BEFORE_OUTCOMES; NOT_CERTIFIED',
        'primary_execution_root': 'data/reports/source_permitted_physical_bybit_2026_10_10',
        'code_hash': code_hash, 'sealer_sha256': digest(Path(__file__)),
        'artifacts': artifacts, 'trade_entry_allowed': False})
    print('COMPLETE: 40 native series, 993575 bars, 10 verified detector manifests. No detector rerun.')


if __name__ == '__main__': main()
