"""Read-only completed-bar state at baseline READY/rejections/pre-entry OPEN."""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_medium_term import MediumTermEngine
from crypto_bot.strategy.source_pdf_native import evidence_json, liquidity_roles
from crypto_bot.strategy.source_permitted import SourceSeries

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_medium_term_research import (
    digest,
    load_data,
    read_rows,
    resume,
    seal,
    write_json,
    write_rows,
)

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'data/reports/source_fidelity_2026_10_11'
BASE = REPO / 'data/reports/medium_term_2026_10_10/role_corrected_v2/bybit_2023_2025'


def population():
    signals, events, discovered = {}, [], {}
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        p = BASE / 'detection' / symbol / 'enabled'
        signals.update({r['signal_id']: r for r in read_rows(p / 'signals.jsonl.gz')})
        events.extend({**r, 'symbol': symbol} for r in read_rows(p / 'anti_scalp_rejections.jsonl.gz'))
        discovered.update({r['idea_id']: {**r, 'symbol': symbol} for r in
                           read_rows(p / 'setup_lifecycle.jsonl.gz') if r['status'] == 'DISCOVERED'})
    ready = {r['evidence']['physical_opportunity_id'] for r in signals.values()}
    last = {}
    for r in sorted(events, key=lambda r: (r['known_at'], r['signal_id'])):
        if r['physical_opportunity_id'] not in ready:
            last[r['physical_opportunity_id']] = r
    rejections = [dict(r, discovery=discovered[r['physical_opportunity_id']])
                  for r in last.values() if r['reason'] == 'REJECTED_SCALP_NO_HTF_CONTEXT']
    trades = read_rows(BASE / 'simulation/enabled/shared_trades.jsonl.gz')
    assert len(rejections) == 3680
    assert len(trades) == 880 and sum(t['net_pnl'] < 0 for t in trades) == 542
    return signals, trades, rejections


def requests_for(symbol):
    signals, trades, rejected = population()
    requests = defaultdict(list)
    for t in trades:
        if t['symbol'] != symbol:
            continue
        signal = signals[t['signal_id']]
        for stage, at in [('READY', signal['known_at']), ('PRE_ENTRY', t['entry_interval_start'])]:
            requests[datetime.fromisoformat(at)].append({'stage': stage, 'id': t['signal_id'],
                'direction': t['direction'], 'entry': signal['entry'], 'htf': signal['htf'],
                'ltf': signal['evidence']['entry_zone_tf'], 'parent': signal['evidence']['htf_poi'],
                'setup_tf': signal['evidence']['actual_setup_tf']})
    for r in rejected:
        if r['symbol'] != symbol:
            continue
        requests[datetime.fromisoformat(r['known_at'])].append({'stage': 'NO_HTF_CONTEXT',
            'id': r['physical_opportunity_id'], 'rejection': r})
    return requests


def source_snapshot(engine, req, at):
    result = {'id': req['id'], 'stage': req['stage'], 'known_at': at,
              'symbol': engine.symbol, 'trade_entry_allowed': False}
    states = {}
    for tf, owner in engine.series.items():
        ranges = [{'low': lo, 'high': hi, 'known_at': known, 'range_id': rid}
                  for lo, hi, known, rid in owner.range_bounds.values()
                  if known <= at and (rid not in owner.range_terminal or owner.range_terminal[rid] > at)]
        states[tf] = {'completed_at': owner.candles[owner.index].close_time if owner.index >= 0 else None,
                      'structure': owner.structure, 'bos': owner.bos, 'conf': owner.conf,
                      'flow': owner.flow, 'active_ranges': ranges}
    result['timeframe_states'] = states
    if req['stage'] == 'NO_HTF_CONTEXT':
        r = req['rejection']
        parent_id = r['discovery']['parent_id']
        matches = [{'tf': tf, 'zone': asdict(owner.zone_registry[parent_id])}
                   for tf, owner in engine.series.items() if parent_id in owner.zone_registry]
        result.update(rejection=r, first_discovery_parent_matches=matches,
                      parent_match_limit='PHYSICAL_ALIAS_CAN_HAVE_DIFFERENT_LAST_PATH_PARENT')
        return result
    h, l = engine.series[req['htf']], engine.series[req['ltf']]
    target = h.target(req['direction'], req['entry'], at)
    result['old_source_fta'] = asdict(target) if target else None
    from types import SimpleNamespace
    parent = SimpleNamespace(**req['parent'])
    roles = liquidity_roles(h, l, parent, req['direction'], req['entry'], at)
    result['adverse_liquidity'] = [r for r in roles if r['role'] == 'AGAINST_SETUP']
    result['liquidity_interpretation'] = 'EXISTING_SOURCE_PDF_NATIVE_CONTEXTUAL_POOL_RULE'
    return result


def replay(data, symbol, requests, policy, *, cutoff=None):
    owners = {}
    for tf, candles in data.items():
        print(symbol, 'analyze', tf, len(candles), flush=True)
        report = analyze_market(candles, timeframe_minutes=tf)
        ranges = analyze_ranges(candles, report, params=RangeDetectionParams(
            midpoint_tolerance_fraction=policy['range_midpoint_tolerance']))
        owners[tf] = SourceSeries(symbol, tf, candles, report, ranges)
    engine = MediumTermEngine(symbol, owners, policy)
    snapshots, last_log = [], time.monotonic()
    merged = heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(cs)]
                          for tf, cs in data.items()])
    for at, rows in itertools.groupby(merged, key=lambda r: r[0]):
        if cutoff is not None and at > cutoff:
            break
        for _, _, tf, i in rows:
            engine.advance(tf, i)
        # Deliberately no evaluate/offer: source state cannot be affected by P&L.
        for request in requests.get(at, ()):
            # Snapshot mutable BOS/CONF/flow maps now, before any future bar.
            snapshots.append(json.loads(evidence_json(source_snapshot(engine, request, at))))
        if time.monotonic() - last_log > 40:
            print(symbol, at.isoformat(), 'snapshots', len(snapshots), flush=True)
            last_log = time.monotonic()
    assert len(snapshots) == sum(len(rs) for at, rs in requests.items() if cutoff is None or at <= cutoff)
    return snapshots


def dependencies(symbol):
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    paths = list((REPO / 'src').rglob('*.py')) + [Path(__file__),
        REPO / 'scripts/run_medium_term_research.py', REPO / 'scripts/research_support.py',
        REPO / 'SOURCE_FIDELITY_AUDIT_PROTOCOL.md', REPO / 'config/source_medium_term_policy.json',
        BASE / 'detection' / symbol / 'manifest.json', BASE / 'simulation/enabled/manifest.json']
    paths.extend(REPO / f'data/history/public_research/bybit_mirror/{symbol}/{tf}.csv.gz' for tf in (15, 60, 240))
    lock = {'baseline': '19404ec0f4a7dd39b93c76240b6ad605278f0646', 'symbol': symbol,
            'dependencies': {str(p.relative_to(REPO)): digest(p) for p in sorted(set(paths))},
            'trade_entry_allowed': False}
    return policy, lock, sha256(evidence_json(lock).encode()).hexdigest()


def audit_symbol(symbol, use_resume):
    policy, lock, fp = dependencies(symbol)
    folder = ROOT / 'state' / symbol
    if resume(folder, fp, use_resume):
        return
    data, audits = load_data('bybit_2023_2025', symbol, policy)
    snapshots = replay(data, symbol, requests_for(symbol), policy)
    folder.mkdir(parents=True)
    write_json(folder / 'dependency_lock.json', lock)
    write_json(folder / 'dataset_audit.json', audits)
    write_rows(folder / 'snapshots.jsonl.gz', snapshots)
    seal(folder, fp, {'symbol': symbol, 'snapshots': len(snapshots),
                     'mode': 'SOURCE_AUDIT_NO_TRADE_GENERATION'})
    print('STATE_AUDIT_COMPLETE', symbol, len(snapshots), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume-existing', action='store_true')
    args = parser.parse_args()
    with ProcessPoolExecutor(max_workers=2) as pool:
        list(pool.map(audit_symbol, ('BTCUSDT', 'ETHUSDT'), itertools.repeat(args.resume_existing)))


if __name__ == '__main__':
    main()
