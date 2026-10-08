"""Offline ablation accounting. Never used to decide causal market events."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from enum import Enum
import hashlib
import json

from crypto_bot.strategy.market_analysis import MarketEventKind

BOS_KINDS = {MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS}
SFP_KINDS = {MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED, MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED}


def plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def stable_key(*parts):
    return json.dumps(plain(parts), ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def bos_key(event):
    return stable_key(event.kind, event.event_time, event.level_price)


def range_key(item):
    return stable_key(item.impulse_direction, item.first_boundary_time, item.first_boundary_price,
                      item.second_boundary_time, item.second_boundary_price)


def sfp_key(event, range_keys):
    return stable_key(event.kind, event.event_time, event.liquidity_origin or 'STRUCTURAL_SWING',
                      event.level_price, event.sfp_pattern_extreme_price,
                      range_keys[event.range_id] if event.range_id is not None else None)


def market_fingerprint(report):
    """Legacy compatibility: compare all causal payloads except explanatory prose/new fields."""
    payload = {}
    for name in ('events', 'levels', 'sweep_episodes', 'trend_state_segments', 'structure_transition_diagnostics'):
        rows = []
        for obj in getattr(report, name):
            row = asdict(obj)
            row.pop('recovery_transition_ids', None)
            row.pop('note', None)
            rows.append(row)
        payload[name] = rows
    payload['final_trend'] = report.final_trend
    raw = json.dumps(plain(payload), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def bos_records(report, *, start=None, end=None):
    out = {}
    for event in report.events:
        if event.kind not in BOS_KINDS or (start is not None and event.event_time < start) or (end is not None and event.event_time > end):
            continue
        out[bos_key(event)] = {
            'time': event.event_time, 'kind': event.kind, 'level_price': event.level_price,
            'close': event.price, 'recovery_transition_ids': event.recovery_transition_ids,
        }
    return plain(out)


def range_records(report, *, validated=False, start=None, end=None):
    out = {}
    for item in report.ranges:
        when = item.midpoint_reaction_time if validated else item.second_boundary_time
        if when is None or (start is not None and when < start) or (end is not None and when > end):
            continue
        out[range_key(item)] = plain({
            'time': when, 'impulse_bos_time': item.impulse_bos_time,
            'status': item.status, 'status_time': item.status_time,
            'midpoint_reaction_time': item.midpoint_reaction_time,
            'upper_boundary_state': item.upper_boundary_state,
            'lower_boundary_state': item.lower_boundary_state,
            'recovery_transition_ids': item.recovery_transition_ids,
            'invalidating_recovery_transition_ids': item.invalidating_recovery_transition_ids,
        })
    return out


def sfp_records(report, ranges=None, *, range_only=True, start=None, end=None):
    rkeys = {r.range_id: range_key(r) for r in ranges.ranges} if ranges is not None else {}
    return {sfp_key(e, rkeys): plain({
        'time': e.event_time, 'kind': e.kind, 'level_price': e.level_price,
        'range_key': rkeys.get(e.range_id), 'recovery_transition_ids': e.recovery_transition_ids,
    }) for e in report.events if e.kind in SFP_KINDS
        and (not range_only or e.liquidity_origin == 'RANGE_BOUNDARY')
        and (start is None or e.event_time >= start) and (end is None or e.event_time <= end)}


def mtf_records(report, ranges):
    rkeys = {r.range_id: range_key(r) for r in ranges.ranges}
    contexts = {}
    candidate_keys = {}
    for c in report.candidates:
        key = stable_key(c.htf_sfp_kind, c.htf_sfp_event_time, c.htf_liquidity_origin,
                         c.htf_level_price, c.sfp_invalidation_price, rkeys.get(c.htf_range_id))
        candidate_keys[c.candidate_id] = key
        contexts[key] = plain({
            'time': c.htf_sfp_event_time, 'origin': c.htf_liquidity_origin,
            'status': c.status, 'bos_time': c.ltf_bos_event_time,
            'bos_level': c.ltf_bos_level_price, 'invalidation_time': c.sfp_invalidation_event_time,
            'htf_recovery_transition_ids': c.htf_recovery_transition_ids,
            'ltf_recovery_transition_ids': c.ltf_recovery_transition_ids,
            'entry_search_allowed': c.entry_search_allowed, 'trade_entry_allowed': c.trade_entry_allowed,
        })
    opportunities = {}
    for o in report.opportunities:
        key = stable_key(o.expected_direction, o.ltf_bos_event_time, o.ltf_bos_level_price)
        opportunities[key] = plain({
            'time': o.ltf_bos_event_time, 'contexts': sorted(candidate_keys[cid] for cid in o.candidate_ids),
            'htf_recovery_transition_ids': o.htf_recovery_transition_ids,
            'ltf_recovery_transition_ids': o.ltf_recovery_transition_ids,
            'entry_search_allowed': o.entry_search_allowed, 'trade_entry_allowed': o.trade_entry_allowed,
        })
    return contexts, opportunities


def has_recovery(record):
    return any(value for key, value in record.items() if 'recovery' in key)


def comparison(source, technical):
    """Presence differences and common-object behavior changes are separate from ancestry.

    ``entry_search_allowed`` is a diagnostic gate rather than object behavior, so its
    changes are reported separately instead of being hidden inside ``COMMON``.
    """
    a, b = set(source), set(technical)
    common = a & b
    def behavior(row):
        return {
            k: v
            for k, v in row.items()
            if 'recovery' not in k and k not in {'entry_search_allowed', 'analysis_mode'}
        }
    changed = {key for key in common if behavior(source[key]) != behavior(technical[key])}
    entry_search_changed = {
        key for key in common
        if source[key].get('entry_search_allowed') != technical[key].get('entry_search_allowed')
    }
    rows = []
    for key in sorted(a | b):
        category = (
            'TECHNICAL_ONLY' if key not in a
            else 'SOURCE_ONLY' if key not in b
            else 'COMMON_CHANGED' if key in changed
            else 'COMMON_ENTRY_SEARCH_CHANGED' if key in entry_search_changed
            else 'COMMON'
        )
        rows.append({'key': key, 'category': category, 'source': source.get(key), 'technical': technical.get(key)})
    return {
        'source_count': len(a), 'technical_count': len(b), 'common_count': len(common),
        'source_only_count': len(a-b), 'technical_only_count': len(b-a),
        'common_changed_count': len(changed),
        'entry_search_changed_count': len(entry_search_changed),
        'technical_with_recovery_ancestry_count': sum(has_recovery(r) for r in technical.values()),
        'rows': rows,
    }
