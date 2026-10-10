"""Independent prefix/future-mutation and preserved-baseline verification."""
from __future__ import annotations

import heapq
import itertools
import json
import subprocess
import sys
from dataclasses import asdict, replace
from hashlib import sha1
from pathlib import Path

from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_medium_term import MediumTermEngine
from crypto_bot.strategy.source_permitted import SourceSeries

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_medium_term_research import ROOT, load_data, write_json, write_rows


def first_difference(a, b, path='root'):
    if type(a) is not type(b):
        return path, str(a)[:500], str(b)[:500]
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return path, list(a), list(b)
        for key in a:
            if a[key] != b[key]:
                return first_difference(a[key], b[key], path+'.'+str(key))
    elif isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return path+'.length', len(a), len(b)
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return first_difference(x, y, path+'['+str(i)+']')
    else:
        return path, str(a)[:1000], str(b)[:1000]

REPO = Path(__file__).resolve().parents[1]


def replay(data, policy, cutoff):
    series = {}
    for tf, candles in data.items():
        report = analyze_market(candles, timeframe_minutes=tf)
        ranges = analyze_ranges(candles, report, params=RangeDetectionParams(
            midpoint_tolerance_fraction=policy['range_midpoint_tolerance']))
        series[tf] = SourceSeries('BTCUSDT', tf, candles, report, ranges)
    e = MediumTermEngine('BTCUSDT', series, policy)
    events = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(cs)]
                          for tf, cs in data.items()])
    for at, rows in itertools.groupby(events, key=lambda r: r[0]):
        if at > cutoff:
            break
        rows = list(rows)
        for _, _, tf, i in rows:
            e.advance(tf, i)
        if policy['execution_clock'] in [r[2] for r in rows]:
            e.evaluate(at, [r[2] for r in rows])
    return {'signals': [asdict(s) for s in e.signals], 'cancellations': e.cancellations,
            'exit_events': e.exit_events, 'rejections': e.rejections,
            'lifecycle': e.lifecycle}


def known_times(value):
    from datetime import datetime
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('known_at', 'observed_at', 'source_break_known_at', 'source_confirmation_known_at') and item is not None:
                yield datetime.fromisoformat(item) if isinstance(item, str) else item
            yield from known_times(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from known_times(item)


def preserved_baseline():
    failures, checked = [], 0
    for row in subprocess.check_output(['git', 'ls-tree', '-rz', 'dab8d254aaf4babc07659e3d03d14b269445767b'], cwd=REPO).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        expected = meta.split()[-1].decode()
        path = REPO / name.decode()
        raw = path.read_bytes()
        actual = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        checked += 1
        if actual != expected:
            failures.append(str(path.relative_to(REPO)))
    if failures:
        raise ValueError('Frozen baseline mutation: ' + ','.join(failures))
    return {'baseline_commit': 'dab8d254aaf4babc07659e3d03d14b269445767b',
            'all_tracked_baseline_blobs_unchanged': checked, 'status': 'PASS'}


def main():
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    data, _ = load_data('bybit_2023_2025', 'BTCUSDT', policy)
    upper = data[15][9000].close_time
    data = {tf: [c for c in cs if c.close_time <= upper] for tf, cs in data.items()}
    receipt = {'baseline': preserved_baseline(), 'checks': [], 'trade_entry_allowed': False}
    for index in (2000, 5000, 8000):
        cut = data[15][index].close_time
        truncated = {tf: [c for c in cs if c.close_time <= cut] for tf, cs in data.items()}
        modified = {tf: [c if c.close_time <= cut else replace(c, open=c.open*1.23,
                                                             high=c.high*1.23, low=c.low*1.23, close=c.close*1.23)
                         for c in cs] for tf, cs in data.items()}
        full, prefix, mutated = replay(data, policy, cut), replay(truncated, policy, cut), replay(modified, policy, cut)
        if full != prefix or full != mutated:
            for label, snapshot in [('full', full), ('prefix', prefix), ('mutated', mutated)]:
                write_rows(ROOT / 'qa/prefix_failure' / (str(index)+'_'+label+'.jsonl.gz'), [snapshot])
            print('DIFFERENCE', first_difference(full, prefix), first_difference(full, mutated), flush=True)
            raise ValueError('Prefix/future mutation parity failed at ' + cut.isoformat())
        known = 0
        for s in full['signals']:
            if s['htf'] not in (60, 240) or s['evidence']['macro_context_tf'] not in (240, 1440):
                raise ValueError('Invalid TF ownership')
            for at in known_times(s['evidence']):
                if at > s['known_at']:
                    raise ValueError('Future source evidence leakage')
                known += 1
        receipt['checks'].append({'cutoff': cut, 'prefix': 'PASS', 'future_mutation': 'PASS',
                                  'signals_compared': len(full['signals']), 'known_timestamps_checked': known,
                                  'all_native_TFs_and_complete_D1': True})
        print('PREFIX_FUTURE_PASS', cut.isoformat(), len(full['signals']), known, flush=True)
    write_json(ROOT / 'qa/causality_and_baseline_receipt.json', receipt)


if __name__ == '__main__':
    main()
