"""Restore two oversized CSV exports byte-for-byte; no strategy/accounting imports."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path

OUT = Path('data/reports/original_v1_1_first_financial_backtest_2026_10_11')
NAMES = ('all_candidates.csv', 'all_WAIT.csv')


def checksum(path):
    digest = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def restore(root, verify_only=False):
    manifest = json.loads((root / OUT / 'result_manifest.json').read_text())
    assert manifest['status'] == 'FIRST_RESULT_FROZEN'
    for name in NAMES:
        target = root / OUT / 'result' / name
        archive = target.with_name(target.name + '.gz')
        expected = manifest['artifacts'][str(target.relative_to(root))]
        assert checksum(archive) == manifest['artifacts'][str(archive.relative_to(root))]
        if target.exists():
            assert checksum(target) == expected, 'Existing export differs; never overwrite'
        digest = sha256()
        count = 0
        temporary = None
        try:
            if not target.exists() and not verify_only:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as created:
                    temporary = Path(created.name)
            with gzip.open(archive, 'rb') as source:
                output = temporary.open('wb') if temporary else None
                try:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(block)
                        count += len(block)
                        if output:
                            output.write(block)
                finally:
                    if output:
                        output.close()
            assert digest.hexdigest() == expected, 'Decompressed export hash mismatch'
            if temporary:
                assert not target.exists(), 'Concurrent existing export; never overwrite'
                os.replace(temporary, target)
                temporary = None
            print('VERIFIED_CSV_ARCHIVE', name, count, 'bytes', expected,
                  'present=' + str(target.exists()))
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    restore(args.repository_root.resolve(), args.verify_only)


if __name__ == '__main__':
    main()
