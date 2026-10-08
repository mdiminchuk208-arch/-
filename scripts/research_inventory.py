"""Completeness checks: retain every registered window and gap segment."""
from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
import json

from run_historical_portfolio import canonical


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
