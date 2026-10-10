"""Bounded-memory scheduling of the unchanged source selection and replay rules."""
from __future__ import annotations

import gc
import json
from collections import Counter, defaultdict

from run_source_permitted_bybit import (
    REPO,
    case_stats,
    digest,
    instant,
    read_rows,
    write_json,
    write_rows,
)

from crypto_bot.data.storage import read_klines_csv
from crypto_bot.strategy.source_engine import SourceSignal
from crypto_bot.strategy.source_permitted import select_union
from crypto_bot.strategy.source_permitted_cases import replay_case
from crypto_bot.strategy.source_portfolio import SourceRiskPolicy


def hydrate(rows):
    return [SourceSignal(**{**r, 'known_at': instant(r['known_at']),
                           'targets': tuple(r['targets']), 'fractions': tuple(r['fractions'])}) for r in rows]


def rank(r, policy):
    return (instant(r['known_at']), policy['entry_tie_precedence'].index(r['path_id']),
            -r['htf'], r['ltf'], policy['symbol_priority'].index(r['symbol']), r['signal_id'])


def definitions(policy):
    return {'SOURCE_PERMITTED_UNION': None, **{n: set(p) for n, p in policy['family_cohorts'].items()},
            **{p['path_id']: {p['path_id']} for p in policy['paths']}}


def execute(output, policy):
    groups = definitions(policy); selected = {name: [] for name in groups}
    duplicates = {name: [] for name in groups}; counts = Counter(); signal_rank = {}
    # No replay, price outcomes or case statuses are read during this phase.
    for symbol in policy['symbol_priority']:
        sigs = hydrate(read_rows(output / 'segments' / symbol / 'signals.jsonl.gz'))
        for s in sigs:
            signal_rank[s.signal_id] = (s.known_at, policy['entry_tie_precedence'].index(s.evidence['path_id']),
                -s.htf, s.ltf, policy['symbol_priority'].index(s.symbol), s.signal_id)
        for name, paths in groups.items():
            allowed = sigs if paths is None else [s for s in sigs if s.evidence['path_id'] in paths]
            kept, dup = select_union(allowed, policy); counts[name] += len(allowed)
            selected[name].extend({'signal_id': s.signal_id, 'physical_opportunity_id': s.evidence['physical_opportunity_id'],
                'known_at': s.known_at, 'path_id': s.evidence['path_id'], 'symbol': s.symbol,
                'htf': s.htf, 'ltf': s.ltf} for s in kept)
            duplicates[name].extend(dup)
        del sigs, allowed, kept
        gc.collect()
    for name, rows in selected.items():
        rows.sort(key=lambda r: rank(r, policy))
        assert len({r['physical_opportunity_id'] for r in rows}) == len(rows)
        write_rows(output / 'selections' / f'{name}.jsonl.gz',
            ({k: r[k] for k in ('signal_id', 'physical_opportunity_id', 'known_at', 'path_id')} for r in rows))
        duplicates[name].sort(key=lambda r: signal_rank[r['signal_id']])
        write_rows(output / 'selections' / f'{name}_duplicates.jsonl.gz', duplicates[name])
    write_json(output / 'pre_execution_selection_receipt.json', {
        'selection_uses_future_outcomes': False, 'selection_rule': policy['selection'],
        'path_precedence': policy['entry_tie_precedence'], 'primary_cancellation': policy['primary_cancellation'],
        'selection_sha256': {p.relative_to(output).as_posix(): digest(p) for p in (output / 'selections').glob('*')},
        'bounded_memory_scheduling': 'SYMBOL_NAMESPACED_SELECTION_THEN_GLOBAL_READY_MERGE_BEFORE_ALL_REPLAY',
        'trade_entry_allowed': False})
    del duplicates
    risk = SourceRiskPolicy(initial_equity=policy['case_reference_equity'], risk_fraction=policy['risk_fraction'],
                            fee_rate=policy['fee_rate'], slippage_fraction=policy['slippage_fraction'])
    controlled = []
    for symbol in policy['symbol_priority']:
        seg = output / 'segments' / symbol
        sigs = {s.signal_id: s for s in hydrate(read_rows(seg / 'signals.jsonl.gz'))}
        candles = [c.to_strategy_candle(300000) for c in read_klines_csv(REPO / f'data/history/bybit/{symbol}/5.csv')]
        cancels, exits = defaultdict(list), defaultdict(list)
        for r in read_rows(seg / 'cancellations.jsonl.gz'): cancels[r['signal_id']].append(r)
        for r in read_rows(seg / 'exit_events.jsonl.gz'): exits[r['signal_id']].append(r)
        cache = {}
        for name, records in selected.items():
            for cohort in policy['cancellation_cohorts']:
                trades, decisions = [], []
                for record in records:
                    if record['symbol'] != symbol: continue
                    sid = record['signal_id']; key = (sid, cohort)
                    if key not in cache:
                        a = replay_case(sigs[sid], candles, cancels[sid], exits[sid], risk, cohort)
                        cache[key] = (a.trades, a.decisions)
                    ts, ds = cache[key]; trades.extend(ts); decisions.extend(ds)
                target = output / 'execution_segments' / symbol / name / cohort
                target.mkdir(parents=True, exist_ok=True)
                write_rows(target / 'cases.jsonl.gz', trades)
                write_rows(target / 'case_decisions.jsonl.gz', decisions)
        for r in json.loads((seg / 'old9_cancel_audit.json').read_text()):
            original = r['old_signal']; e = original['evidence']
            s = hydrate([{**original, 'evidence': {**e, 'path_id': 'OB_ULTRA_CONSERVATIVE_CONF',
                            'physical_opportunity_id': 'OLD9:' + original['signal_id']}}])[0]
            events = [{**r['strict_cancel'], 'cohort': 'CANCEL_STRICT_STRUCTURE'}]
            if r['source_cancel']: events.append(r['source_cancel'])
            for cohort in policy['cancellation_cohorts']:
                a = replay_case(s, candles, events, (), risk, cohort)
                controlled.append({'old_signal_id': s.signal_id, 'cancellation_cohort': cohort,
                                   'cases': a.trades, 'decisions': a.decisions})
        del sigs, candles, cache, trades, decisions, cancels, exits
        gc.collect()
        print(symbol + ' bounded source execution COMPLETE', flush=True)
    summaries = {}
    for name, records in selected.items():
        for cohort in policy['cancellation_cohorts']:
            trades, decisions = [], []
            for symbol in policy['symbol_priority']:
                p = output / 'execution_segments' / symbol / name / cohort
                trades.extend(read_rows(p / 'cases.jsonl.gz')); decisions.extend(read_rows(p / 'case_decisions.jsonl.gz'))
            trades.sort(key=lambda t: (instant(t['entry_interval_start']), instant(t['ready_time']),
                -t['htf'], t['ltf'], policy['symbol_priority'].index(t['symbol']), t['signal_id']))
            closed = [t for t in trades if t['status'] == 'CLOSED']; primary = closed[:50]
            target = output / 'cohorts' / name / cohort; target.mkdir(parents=True, exist_ok=True)
            write_rows(target / 'cases.jsonl.gz', trades); write_rows(target / 'primary_cases.jsonl.gz', primary)
            write_rows(target / 'case_decisions.jsonl.gz', decisions)
            breakdown = {}
            for dimension in ('path', 'setup', 'POI', 'direction', 'symbol', 'mapping'):
                parts = defaultdict(list)
                for t in primary:
                    key = t['path_id'] if dimension == 'path' else next(p['setup_family'] for p in policy['paths'] if p['path_id'] == t['path_id']) if dimension == 'setup' else t['poi_type'] if dimension == 'POI' else f'{t["htf"]}/{t["ltf"]}' if dimension == 'mapping' else t[dimension]
                    parts[key].append(t)
                breakdown[dimension] = {k: case_stats(v) for k, v in parts.items()}
            summary = {'cohort': name, 'cancellation_cohort': cohort, 'READY': len(records),
                'raw_variant_READY': counts[name], 'FILLED': len(trades), 'CLOSED': len(closed),
                'OPEN': len(trades)-len(closed), 'PENDING': sum(r['reason']=='PENDING_RIGHT_CENSORED' for r in decisions),
                'primary_closed_count': len(primary), 'primary': case_stats(primary), 'all_closed': case_stats(closed),
                'breakdowns': breakdown, 'decisions': dict(Counter(r['reason'] for r in decisions)),
                'shared_capital': False, 'trade_entry_allowed': False}
            write_json(target / 'summary.json', summary); summaries[f'{name}/{cohort}'] = summary
            del trades, decisions, closed, primary, parts
            gc.collect()
    write_json(output / 'controlled_old9_execution.json', controlled)
    write_json(output / 'summary.json', {'status': 'COMPLETE_FULL_NATIVE_SOURCE_PERMITTED_REPLAY',
        'native_series': 40, 'candles': 993575, 'paths': len(policy['paths']), 'cohorts': summaries,
        'primary': summaries['SOURCE_PERMITTED_UNION/' + policy['primary_cancellation']],
        'trade_entry_allowed': False})
