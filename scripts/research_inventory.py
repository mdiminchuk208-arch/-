"""Completeness checks: retain every registered window and gap segment."""
from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
import gzip
import json
import shutil
from tempfile import TemporaryDirectory
from pathlib import Path

from run_historical_portfolio import canonical


def save_artifact_hashes(folder, recursive=False):
    paths=folder.rglob('*') if recursive else folder.iterdir()
    hashes={path.relative_to(folder).as_posix():sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file() and path.name not in ('artifact_hashes.json','fingerprint.sha256')}
    (folder/'artifact_hashes.json').write_text(canonical(hashes)+'\n')
    fingerprint=sha256(canonical(hashes).encode()).hexdigest()
    (folder/'fingerprint.sha256').write_text(fingerprint+'\n')
    return fingerprint


def verify_source_inputs(repo, source):
    for name,digest in source['input_hashes'].items():
        path=repo/'data/history/bybit'/name if 'execution_start' in source else repo/name
        assert sha256(path.read_bytes()).hexdigest()==digest,path


def verify_expected_fingerprint(folder, expected):
    """Require the recovered bytes to match the checkpoint, not just a new hash."""
    hashes=json.loads((folder/'artifact_hashes.json').read_text())
    assert all(sha256((folder/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),folder
    actual=sha256(canonical(hashes).encode()).hexdigest()
    assert actual==(folder/'fingerprint.sha256').read_text().strip(),folder
    if actual!=expected:
        raise ValueError(f'Recovery fingerprint mismatch: {folder}; expected={expected}; actual={actual}')
    return actual


def restore_checkpoint_schema(folder, expected, diagnostics):
    """Recover the historical audit schema only when it reproduces the old hash.

    Some original workers predated the diagnostic bos_level_price field. All
    execution artifacts must remain byte-identical. Keep the expanded audit and
    transformation receipt separately, outside the historical artifact set.
    """
    try:
        return verify_expected_fingerprint(folder,expected)
    except ValueError:
        pass
    name='target_availability_qualification_only.jsonl.gz'
    hashes=json.loads((folder/'artifact_hashes.json').read_text())
    if name not in hashes:
        return verify_expected_fingerprint(folder,expected)
    with gzip.open(folder/name,'rt') as reader:
        rows=[json.loads(line) for line in reader]
    if not rows or not all('bos_level_price' in row for row in rows):
        return verify_expected_fingerprint(folder,expected)
    for row in rows:
        row.pop('bos_level_price')
    diagnostics.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=diagnostics) as directory:
        candidate=Path(directory)/name
        with candidate.open('wb') as raw, gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as writer:
            for row in rows:
                writer.write((canonical(row)+'\n').encode())
        recovered=dict(hashes)
        recovered[name]=sha256(candidate.read_bytes()).hexdigest()
        if sha256(canonical(recovered).encode()).hexdigest()!=expected:
            return verify_expected_fingerprint(folder,expected)
        shutil.copyfile(folder/name,diagnostics/'target_availability_qualification_only.v2.jsonl.gz')
        receipt=dict(expected_fingerprint=expected,expanded_fingerprint=sha256(canonical(hashes).encode()).hexdigest(),
                     historical_schema='PRE_BOS_LEVEL_PRICE_DIAGNOSTIC',restored_audit_rows=len(rows),
                     expanded_audit_sha256=hashes[name],restored_audit_sha256=recovered[name],
                     unchanged_artifact_hashes={k:v for k,v in hashes.items() if k!=name},
                     source_config_inputs_and_execution_unchanged=True,trade_entry_allowed=False)
        (diagnostics/'schema_restoration.json').write_text(canonical(receipt)+'\n')
        candidate.replace(folder/name)
        (folder/'artifact_hashes.json').write_text(canonical(recovered)+'\n')
        (folder/'fingerprint.sha256').write_text(expected+'\n')
    return verify_expected_fingerprint(folder,expected)


def reusable_case(folder,context):
    """Resume only complete artifacts with identical frozen inputs/parameters."""
    required=('summary.json','artifact_hashes.json','fingerprint.sha256')
    if not all((folder/name).exists() for name in required):
        return None
    source=json.loads((folder/'summary.json').read_text())
    if any(canonical(source.get(key))!=canonical(value) for key,value in context.items()):
        raise ValueError('Existing case has different inputs or parameters: '+str(folder))
    hashes=json.loads((folder/'artifact_hashes.json').read_text())
    assert 'summary.json' in hashes,folder
    assert all(sha256((folder/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),folder
    assert (folder/'fingerprint.sha256').read_text().strip()==sha256(canonical(hashes).encode()).hexdigest(),folder
    return source


def registered_windows(split):
    windows=list(split['periods'])
    begin=datetime.fromisoformat(windows[0]['start'])+timedelta(days=90)
    end=datetime.fromisoformat(windows[-1]['end'])
    number=0
    while begin<end:
        windows.append(dict(name=f'WALK_{number:02}',start=begin.isoformat(),end=min(begin+timedelta(days=90),end).isoformat()))
        number+=1;begin+=timedelta(days=90)
    return windows


def complete_study(source,split,window_names=None,verify_files=True):
    if not (source/'results.json').exists() or not (source/'coverage_segments.json').exists():
        return False,dict(reason='MISSING_RESULTS_OR_COVERAGE')
    windows=[w for w in registered_windows(split) if not window_names or w['name'] in window_names]
    coverage=json.loads((source/'coverage_segments.json').read_text())
    segments=[tuple(datetime.fromisoformat(t) for t in pair) for pair in coverage['segments']]
    expected={(w['name'],number) for w in windows for number,(a,b) in enumerate(segments)
              if max(a,datetime.fromisoformat(w['start']))<min(b,datetime.fromisoformat(w['end']))}
    records=json.loads((source/'results.json').read_text())
    actual={(r['window'],r['segment']) for r in records}
    if expected!=actual or len(records)!=len(actual):
        return False,dict(reason='INCOMPLETE_OR_DUPLICATE_WINDOW_SEGMENTS',missing=sorted(expected-actual),extra=sorted(actual-expected))
    ledger=[]
    for row in records:
        if row['status']=='REPLAY_COMPLETE':
            folder=source/f"{row['window']}_SEGMENT_{row['segment']:02}"
            hashes=json.loads((folder/'artifact_hashes.json').read_text())
            if verify_files:
                assert all(sha256((folder/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),folder
            fingerprint=sha256(canonical(hashes).encode()).hexdigest()
            assert (folder/'fingerprint.sha256').read_text().strip()==fingerprint,folder
            ledger.append(dict(window=row['window'],segment=row['segment'],status=row['status'],fingerprint=fingerprint))
        else:
            assert row['status'] in ('INSUFFICIENT_CONTIGUOUS_WARMUP','NO_COMPLETE_EXECUTION_BAR'),row
            ledger.append({k:row[k] for k in ('window','segment','status')})
    return True,dict(registered_windows=len(windows),expected_window_segments=len(expected),
        retained_skipped_segments=sum(r['status']!='REPLAY_COMPLETE' for r in records),ledger=ledger,
        every_registered_segment_accounted_for=True)
