"""Inspect staged research files without printing secret values or changing history."""
from __future__ import annotations

import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from research_support import check_baseline


def inspect():
    repo=Path(__file__).resolve().parents[1];lock=check_baseline(repo)
    names=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMR','-z'],cwd=repo).decode().split('\0')
    rules={
        'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
        'github_token':rb'\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b',
        'aws_key':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        'secret_assignment':rb'(?i)(?:api[_ -]?key|api[_ -]?secret|access[_ -]?token|password|credentials)\s*[=:]\s*[\x22\x27]([A-Za-z0-9_+/.=-]{20,})[\x22\x27]',
        'credential_url':rb'https?://[^\s/@:]{2,}:[^\s/@]{5,}@',
        'signed_download_url':rb'https?://[^\s\x22\x27]+[?&]X-Amz-Signature=',
    }
    patterns={name:re.compile(rule) for name,rule in rules.items()}
    candidates={'private_key':(b'PRIVATE KEY',),'github_token':(b'ghp_',b'gho_',b'ghu_',b'ghs_',b'ghr_',b'github_pat_'),
        'aws_key':(b'AKIA',b'ASIA'),'secret_assignment':(b'api',b'access',b'password',b'credentials'),
        'credential_url':(b'://',),'signed_download_url':(b'X-Amz-Signature=',)}
    manifest=[];hits=[];checked={}
    for name in sorted(n for n in names if n and not n.endswith('/research_publication_scan.json')):
        path=repo/name
        assert path.stat().st_size<100_000_000,name
        blob=path.read_bytes()
        stored_sha=sha256(blob).hexdigest()
        if stored_sha not in checked:
            logical_sha=sha256();logical_size=0
            with (gzip.open(path,'rb') if path.suffix=='.gz' else path.open('rb')) as reader:
                tail=b''
                while block:=reader.read(1024*1024):
                    logical_sha.update(block);logical_size+=len(block)
                    sample=tail+block;lower=sample.lower()
                    for kind,pattern in patterns.items():
                        probe=lower if kind=='secret_assignment' else sample
                        if any(token in probe for token in candidates[kind]) and pattern.search(sample):
                            hits.append(dict(path=name,kind=kind))
                    tail=block[-512:]
            checked[stored_sha]=(logical_size,logical_sha.hexdigest())
        logical_size,logical_digest=checked[stored_sha]
        staged=subprocess.check_output(['git','show',':'+name],cwd=repo)
        assert sha256(blob).digest()==sha256(staged).digest(),('file changed after staging',name)
        manifest.append(dict(path=name,stored_bytes=len(blob),stored_sha256=stored_sha,
                             logical_bytes=logical_size,logical_sha256=logical_digest))
    assert not hits,hits
    removed=subprocess.check_output(['git','diff',lock['baseline_commit'],'--name-only','--diff-filter=D'],cwd=repo).decode()
    assert not removed,removed
    excluded={'.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','node_modules','.research_cache'}
    for name in subprocess.check_output(['git','ls-files','-z'],cwd=repo).decode().split('\0'):
        if name:
            path=Path(name)
            assert not any(part in excluded for part in path.parts),name
            assert path.name not in ('.env','credentials.json','token.json','id_rsa','id_ed25519'),name
    target=repo/'data/reports/robustness_research/research_publication_scan.json'
    target.write_text(json.dumps(dict(files=manifest,changed_files_scanned=len(manifest),
        logical_bytes_covered=sum(r['logical_bytes'] for r in manifest),
        unique_logical_bytes_scanned=sum(r[0] for r in checked.values()),unique_stored_sha256=len(checked),
        sha_identical_file_reuse=len(manifest)-len(checked),patterns=list(rules),secret_matches=0,
        baseline_guard='PASS',protected_source_config_files=len(lock['code_hashes']),removed_base_paths=0,
        excluded_generated_directories=sorted(excluded),trade_entry_allowed=False),indent=2,sort_keys=True)+'\n')
    print('Staged files/content/secret scan PASS:',len(manifest),'files; baseline guard',len(lock['code_hashes']),'PASS')


if __name__=='__main__':inspect()
