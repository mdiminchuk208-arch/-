"""Fetch immutable, SHA-verified PUBLIC Git LFS candles; never use exchange keys.

Requires a pointer-only public mirror clone. LFS action URLs are transient and
never logged or retained; provenance stores immutable repository paths and SHA.
Uses inherited HTTPS proxy/CA settings. No third-party repository code is run.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import urllib.request

REPOSITORY = 'Speirsy11/crypto-dataset'
COMMIT = 'f1a95659f3cdd655b3ce7cbb1300e8fc944723bb'
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT', 'ADAUSDT')


def pointer_inventory(clone: Path):
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', COMMIT], cwd=clone)
    selected = []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        name = raw_name.decode()
        match = re.fullmatch(r'data/interval_id=5m/symbol_id=([^/]+)/year=(\d+)/month=(\d+)/[^/]+\.parquet', name)
        if match and match[1] in SYMBOLS and int(match[2]) < 2026:
            blob = metadata.decode().split()[2]
            selected.append((name, blob))
    payload = ''.join(blob + '\n' for _, blob in selected).encode()
    result = subprocess.run(['git', 'cat-file', '--batch'], cwd=clone, input=payload,
                            stdout=subprocess.PIPE, check=True).stdout
    cursor = 0
    objects = []
    for path, blob in selected:
        end = result.index(b'\n', cursor)
        oid, kind, size = result[cursor:end].decode().split()
        assert oid == blob and kind == 'blob'
        cursor = end + 1
        pointer = result[cursor:cursor + int(size)].decode()
        cursor += int(size) + 1
        assert pointer.startswith('version https://git-lfs.github.com/spec/v1\n')
        digest = re.search(r'oid sha256:([a-f0-9]{64})', pointer)
        byte_size = re.search(r'size (\d+)', pointer)
        assert digest is not None and byte_size is not None
        objects.append(dict(path=path, git_blob=blob, oid=digest[1], size=int(byte_size[1])))
    assert objects
    return objects


def fetch_batch(batch, destination):
    endpoint = f'https://github.com/{REPOSITORY}.git/info/lfs/objects/batch'
    data = json.dumps(dict(operation='download', transfers=['basic'],
                           objects=[dict(oid=x['oid'], size=x['size']) for x in batch])).encode()
    request = urllib.request.Request(endpoint, data=data, headers={
        'Content-Type': 'application/vnd.git-lfs+json', 'Accept': 'application/vnd.git-lfs+json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        objects = {x['oid']: x for x in json.load(response)['objects']}
    records = []
    for item in batch:
        target = destination / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            content = target.read_bytes()
        else:
            action = objects[item['oid']].get('actions', {}).get('download')
            if action is None:
                raise RuntimeError(f'Public LFS object unavailable: {item["path"]}')
            request = urllib.request.Request(action['href'], headers=action.get('header', {}))
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    content = response.read()
            except Exception as exc:
                # Signed storage URLs must not appear in exception output.
                raise RuntimeError(f'Public object fetch failed: {item["path"]}; {type(exc).__name__}') from None
        if len(content) != item['size'] or sha256(content).hexdigest() != item['oid']:
            raise ValueError(f'Public object SHA/size mismatch: {item["path"]}')
        if content[:4] != b'PAR1' or content[-4:] != b'PAR1':
            raise ValueError(f'Not an actual Parquet object: {item["path"]}')
        if not target.exists():
            temporary = target.with_suffix('.tmp')
            temporary.write_bytes(content)
            temporary.replace(target)
        records.append(dict(item, source=f'https://github.com/{REPOSITORY}/blob/{COMMIT}/{item["path"]}',
                            exchange='BINANCE', instrument='UNVERIFIED_BINANCE_MARKET_TYPE', repository_commit=COMMIT,
                            sha256=item['oid'], sha_verified=True))
    print(f'Verified {len(records)} public Parquet objects', flush=True)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pointer-clone', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    inventory = pointer_inventory(args.pointer_clone)
    batches = [inventory[i:i + 24] for i in range(0, len(inventory), 24)]
    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for result in executor.map(lambda batch: fetch_batch(batch, args.destination), batches):
            records.extend(result)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(dict(repository=REPOSITORY, commit=COMMIT,
        exchange='BINANCE', instrument='UNVERIFIED_BINANCE_MARKET_TYPE', requested_symbols=list(SYMBOLS),
        missing_priority_symbols=['LINKUSDT', 'AVAXUSDT', 'LTCUSDT'], files=records,
        total_bytes=sum(x['size'] for x in records), synthetic_data=False,
        exchange_credentials_used=False, trade_entry_allowed=False), indent=2, sort_keys=True) + '\n')
    print('Complete:', len(records), 'verified files', sum(x['size'] for x in records), 'bytes')


if __name__ == '__main__':
    main()
