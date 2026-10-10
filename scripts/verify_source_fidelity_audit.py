"""Independent immutable-input, causal-state and matched-exit audit checks."""
from __future__ import annotations

import argparse
import compileall
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_source_fidelity_state import REPO, ROOT, replay
from run_medium_term_research import (
    complete_aggregate,
    digest,
    evidence_json,
    load_data,
    read_rows,
    resume,
    write_json,
)

ARCHIVED_STATE_CODE = '6eaf3d6'


def verify_state_resume():
    """Verify the precise committed producer, rather than rebasing a lock."""
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        folder = ROOT / 'state' / symbol
        lock = json.loads((folder / 'dependency_lock.json').read_text())
        for name, expected in lock['dependencies'].items():
            if name == 'scripts/audit_source_fidelity_state.py':
                raw = subprocess.check_output(['git', 'show', ARCHIVED_STATE_CODE + ':' + name], cwd=REPO)
                actual = sha256(raw).hexdigest()
            else:
                actual = digest(REPO / name)
            assert actual == expected, ('State dependency mismatch', name)
        fingerprint = sha256(evidence_json(lock).encode()).hexdigest()
        assert resume(folder, fingerprint, True)


def prefix_future():
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    raw, _ = load_data('bybit_2023_2025', 'BTCUSDT', policy)
    clock = raw[15][:9000]
    end = clock[-1].close_time
    data = {tf: [c for c in cs if c.close_time <= end] for tf, cs in raw.items()}
    cuts = [clock[i].close_time for i in (2000, 5000, 8000)]
    requests = defaultdict(list)
    for i, at in enumerate(cuts):
        requests[at].append({'id': 'QA_' + str(i), 'stage': 'NO_HTF_CONTEXT',
                             'rejection': {'discovery': {'parent_id': 'NO_SUCH_PARENT'}}})
    full = replay(data, 'BTCUSDT', requests, policy)
    for i, cut in enumerate(cuts):
        prefix = {tf: [c for c in cs if c.close_time <= cut] for tf, cs in data.items()}
        expected = [s for s in full if datetime.fromisoformat(s['known_at']) <= cut]
        actual = replay(prefix, 'BTCUSDT', requests, policy, cutoff=cut)
        assert actual == expected, ('State prefix mismatch', i)
        mutated = {tf: [c if c.close_time <= cut else replace(
            c, open=c.open * 1.31, high=c.high * 1.31, low=c.low * 1.31, close=c.close * 1.31)
                       for c in cs] for tf, cs in data.items()}
        actual = replay(mutated, 'BTCUSDT', requests, policy, cutoff=cut)
        assert actual == expected, ('State future mutation mismatch', i)
    # Same aggregation contract as the frozen research loader: full 96-bar UTC days.
    daily, _ = complete_aggregate(clock, 1440)
    for day in daily:
        constituents = [c for c in clock if day.open_time <= c.open_time < day.close_time]
        assert len(constituents) == 96
        assert day.open_time.hour == 0 and day.open_time.minute == 0
        assert day.open == constituents[0].open and day.close == constituents[-1].close
        assert day.high == max(c.high for c in constituents)
        assert day.low == min(c.low for c in constituents)
    write_json(ROOT / 'qa/state_prefix_receipt.json', {
        'prefix_consistency': 'PASS', 'future_mutation': 'PASS', 'cuts': cuts,
        'samples': len(full), 'bars_M15': len(clock), 'D1_complete_days_checked': len(daily),
        'scope': 'Real-history completed-state snapshots, not a new entry strategy',
        'trade_entry_allowed': False})


def baseline_and_known_times():
    lock = json.loads((ROOT / 'baseline_lock.json').read_text())
    modified = []
    for name, expected in lock['git_blobs'].items():
        path = REPO / name
        if not path.is_file():
            modified.append(name)
            continue
        raw = path.read_bytes()
        from hashlib import sha1
        actual = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual != expected:
            modified.append(name)
    assert not modified, modified
    counts = defaultdict(int)

    def visit(value, at):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {'known_at', 'formed_at', 'completed_at', 'confirmed_at',
                           'first_test_at', 'last_test_at', 'invalidated_at', 'first_test',
                           'last_test', 'last_native_test_at', 'full_absorption_at',
                           'source_break_known_at'} and isinstance(item, str):
                    stamp = datetime.fromisoformat(item)
                    assert stamp <= at, ('Future state evidence', key, item, at)
                    counts[key] += 1
                else:
                    visit(item, at)
        elif isinstance(value, list):
            for item in value:
                visit(item, at)
    n = 0
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        for row in read_rows(ROOT / 'state' / symbol / 'snapshots.jsonl.gz'):
            visit(row, datetime.fromisoformat(row['known_at']))
            assert row['trade_entry_allowed'] is False
            n += 1
    assert n == 5440
    assert compileall.compile_dir(REPO / 'src', quiet=1)
    assert compileall.compile_dir(REPO / 'scripts', quiet=1)
    assert compileall.compile_dir(REPO / 'tests', quiet=1)
    write_json(ROOT / 'qa/immutable_and_known_times_receipt.json', {
        'baseline_commit': lock['commit'], 'baseline_blobs_checked': len(lock['git_blobs']),
        'baseline_file_identity': 'PASS', 'state_snapshots': n, 'known_times_checks': dict(counts),
        'known_times': 'PASS', 'compileall': 'PASS', 'trade_entry_allowed': False})


def exit_history():
    from audit_source_fidelity_exits import MODELS, exit_spec, simulate_fixed_trade
    from audit_source_fidelity_state import BASE, population
    from run_medium_term_research import deserialize_signal
    signals, trades, _ = population()
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    clocks = {symbol: load_data('bybit_2023_2025', symbol, policy)[0][15]
              for symbol in ('BTCUSDT', 'ETHUSDT')}
    index = {symbol: {c.open_time: i for i, c in enumerate(cs)} for symbol, cs in clocks.items()}
    snapshots = {r['id']: r for symbol in clocks for r in read_rows(
        ROOT / 'state' / symbol / 'snapshots.jsonl.gz') if r['stage'] == 'PRE_ENTRY'}
    events = defaultdict(list)
    for symbol in clocks:
        for event in read_rows(BASE / 'detection' / symbol / 'enabled/exit_events.jsonl.gz'):
            events[event['signal_id']].append(event)
    # Outcome-independent chronological decimation spanning the entire cohort.
    selected = sorted(trades, key=lambda t: (t['entry_interval_start'], t['signal_id']))[::40]
    checks = 0
    for trade in selected:
        signal = deserialize_signal(signals[trade['signal_id']])
        start = index[trade['symbol']][datetime.fromisoformat(trade['entry_interval_start'])]
        bars = clocks[trade['symbol']][start:start + 64]
        cut = bars[min(7, len(bars) - 1)].close_time
        prefix = [c for c in bars if c.close_time <= cut]
        mutated = [c if c.close_time <= cut else replace(
            c, open=c.open * 1.47, high=c.high * 1.47, low=c.low * 1.47, close=c.close * 1.47)
                   for c in bars]
        for model in MODELS:
            spec = exit_spec(signal, snapshots[trade['signal_id']], model)
            if spec is None:
                continue
            kwargs = {'model': model, 'target_prices': spec[0], 'fractions': spec[1], 'cutoff': cut}
            a = simulate_fixed_trade(trade, signal, bars, events[signal.signal_id], **kwargs)
            b = simulate_fixed_trade(trade, signal, prefix, events[signal.signal_id], **kwargs)
            c = simulate_fixed_trade(trade, signal, mutated, events[signal.signal_id], mode='SHADOW', **kwargs)
            assert a == b == c, (signal.signal_id, model)
            checks += 1
    write_json(ROOT / 'qa/matched_exit_history_causality.json', {
        'prefix_consistency': 'PASS', 'future_mutation': 'PASS', 'BACKTEST_SHADOW': 'PASS',
        'chronologically_selected_entry_cases': len(selected), 'defined_model_checks': checks,
        'selection': 'Every 40th entry in chronological order; no outcome selection',
        'trade_entry_allowed': False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['prefix', 'resume-existing', 'baseline', 'exits'])
    args = p.parse_args()
    {'prefix': prefix_future, 'resume-existing': verify_state_resume,
     'baseline': baseline_and_known_times, 'exits': exit_history}[args.stage]()


if __name__ == '__main__':
    main()
