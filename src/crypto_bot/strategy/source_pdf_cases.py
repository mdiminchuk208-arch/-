"""Independent paper trade cases; costs and source fills without shared occupancy."""
from __future__ import annotations
from datetime import datetime, timedelta
from bisect import bisect_left
from math import isfinite
from typing import Sequence
from crypto_bot.common.models import Candle
from crypto_bot.strategy.source_engine import SourceSignal, sign
from crypto_bot.strategy.source_portfolio import SourcePortfolio


class SourceTradeCase(SourcePortfolio):
    """One immutable opportunity per reference account, never shared capital."""
    def _entry(self, signal: SourceSignal, c: Candle) -> bool:
        s, p = sign(signal.direction), self.policy
        # Order existed at OPEN; favourable gaps receive the resting limit quote,
        # not invented price improvement. Invalid open beyond SL/FTA cannot fill.
        if s * (c.open - signal.stop) <= 0 or s * (signal.targets[0] - c.open) <= 0:
            self.cancel(signal.signal_id, c.open_time, 'OPEN_OUTSIDE_SL_FTA')
            return False
        crossed = c.open <= signal.entry or c.low <= signal.entry if s == 1 else c.open >= signal.entry or c.high >= signal.entry
        if not crossed:
            return False
        entry = signal.entry * (1 + s * p.slippage_fraction)
        stop_fill = signal.stop * (1 - s * p.slippage_fraction)
        unit_risk = s * (entry - stop_fill) + p.fee_rate * (entry + stop_fill)
        if not isfinite(unit_risk) or unit_risk <= 0:
            self.cancel(signal.signal_id, c.open_time, 'COST_GEOMETRY')
            return False
        risk = self.cash * p.risk_fraction
        qty = risk / unit_risk
        if self.cash <= 0:
            self.cancel(signal.signal_id, c.open_time, 'ISOLATED_VIRTUAL_BUDGET')
            return False
        entry_fee = qty * entry * p.fee_rate
        trade = {'trade_id': signal.signal_id, 'signal_id': signal.signal_id, 'symbol': signal.symbol,
                 'direction': signal.direction, 'htf': signal.htf, 'ltf': signal.ltf,
                 'setup_type': signal.setup_type, 'poi_type': signal.poi_type,
                 'ready_time': signal.known_at, 'entry_time': c.close_time,
                 'entry_interval_start': c.open_time, 'entry_interval_end': c.close_time,
                 'entry_time_precision': 'BAR_INTERVAL_KNOWN_AT_CLOSE',
                 'entry_reference': signal.entry, 'entry': entry, 'stop': signal.stop,
                 'targets': list(signal.targets), 'fractions': list(signal.fractions),
                 'quantity': qty, 'remaining': qty, 'risk_amount': risk, 'initial_equity': self.cash,
                 'fees': entry_fee, 'slippage': qty * abs(entry - signal.entry),
                 'gross_pnl': 0.0, 'quote_gross_pnl': 0.0, 'net_pnl': -entry_fee, 'fills': [],
                 'status': 'OPEN', 'next_target': 0, 'evidence': signal.evidence,
                 'exit_policy': signal.evidence['exit_policy'], 'trade_entry_allowed': False}
        self.cash -= entry_fee
        self.pending = None
        self.position = trade
        self.trades.append(trade)
        return True


def opportunity_key(signal: SourceSignal) -> dict:
    h = signal.evidence['htf_poi']
    end = datetime.fromisoformat(signal.evidence.get('htf_interaction_at', h['first_test'])) if isinstance(signal.evidence.get('htf_interaction_at', h['first_test']), str) else signal.evidence.get('htf_interaction_at', h['first_test'])
    start = end - timedelta(minutes=signal.htf)
    local = signal.evidence['ltf_poi']
    return {'symbol': signal.symbol, 'direction': signal.direction, 'reaction_start': start,
            'reaction_end': end, 'htf_low': h['low'], 'htf_high': h['high'],
            'htf_zone_id': h['zone_id'], 'local_low': local['low'], 'local_high': local['high']}


def same_opportunity(a: dict, b: dict) -> bool:
    if a['symbol'] != b['symbol'] or a['direction'] != b['direction']:
        return False
    reaction = max(a['reaction_start'], b['reaction_start']) < min(a['reaction_end'], b['reaction_end'])
    htf = max(a['htf_low'], b['htf_low']) <= min(a['htf_high'], b['htf_high'])
    local = max(a['local_low'], b['local_low']) <= min(a['local_high'], b['local_high'])
    return reaction and htf and (local or a['htf_zone_id'] == b['htf_zone_id'])


def deduplicate_cases(signals: list[SourceSignal], symbols: list[str]) -> tuple[list[SourceSignal], list[dict]]:
    ordered = sorted(signals, key=lambda s: (s.known_at, -s.htf, s.ltf, symbols.index(s.symbol), s.signal_id))
    accepted: list[SourceSignal] = []
    evidence: list[tuple[dict, str]] = []
    duplicates = []
    for signal in ordered:
        key = opportunity_key(signal)
        prior = next((sid for old, sid in evidence if same_opportunity(key, old)), None)
        if prior is None:
            accepted.append(signal)
            evidence.append((key, signal.signal_id))
        else:
            duplicates.append({'signal_id': signal.signal_id, 'retained_signal_id': prior,
                               'known_at': signal.known_at, 'reason': 'SAME_PHYSICAL_REACTION_OPPORTUNITY',
                               'opportunity': key, 'trade_entry_allowed': False})
    return accepted, duplicates


def replay_case(signal: SourceSignal, candles: Sequence[Candle], cancellations: Sequence[dict], policy=None):
    account = SourceTradeCase(policy)
    account.offer(signal)
    cancels = sorted(cancellations, key=lambda row: row['known_at'])
    cursor = 0
    mae = 0.0
    first = bisect_left(candles, signal.known_at, key=lambda c: c.open_time)
    last = None
    for c in candles[first:]:
        while cursor < len(cancels):
            row = cancels[cursor]
            when = datetime.fromisoformat(row['known_at']) if isinstance(row['known_at'], str) else row['known_at']
            if when > c.open_time:
                break
            account.cancel(signal.signal_id, when, row['reason'])
            cursor += 1
        if account.pending is None and account.position is None:
            break
        if account.position is not None:
            t = account.position
            price = c.low if signal.direction == 'LONG' else c.high
            mae = max(mae, max(0.0, sign(signal.direction) * (t['entry'] - price)) * t['quantity'] / t['risk_amount'])
        account.on_bar(signal.symbol, c)
        last = c.close_time
        if account.trades and account.position is None:
            break
    if last is not None:
        account.mark(last)
    for t in account.trades:
        t['max_adverse_excursion_R'] = mae
        t['mae_semantics'] = 'POST_ENTRY_BAR_OHLC_UPPER_BOUND_ENTRY_BAR_EXCLUDED'
        t['validation_mode'] = 'SOURCE_TRADE_CASE_VALIDATION'
        t['reference_equity_not_shared_capital'] = account.policy.initial_equity
    if account.pending is not None:
        account.decisions.append({'signal_id': signal.signal_id, 'known_at': last or signal.known_at,
                                 'reason': 'PENDING_RIGHT_CENSORED', 'trade_entry_allowed': False})
    return account
