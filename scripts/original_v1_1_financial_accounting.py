"""Accounting normalization only; cannot admit a source trade or choose an exit."""
from __future__ import annotations

from decimal import Decimal
from statistics import mean, median

EQUITY = Decimal(1170)
RISK = Decimal('0.02')
FEE = Decimal('0.0006')
SLIPPAGE = Decimal('0.0002')


def cash(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Nonfinite accounting input')
    return result


def fixed_risk_quantity(entry, initial_stop, known_equity=EQUITY):
    distance = abs(cash(entry) - cash(initial_stop))
    if distance <= 0 or cash(known_equity) <= 0:
        raise ValueError('Undefined accounting size; never a source rejection')
    return cash(known_equity) * RISK / distance


def money(direction, entry, exit_price, quantity):
    """Reference-price gross; costs explicit debits, preserving frozen LIMIT quote.

    Entry/exit fee6bps each and slippage2bps each are declared modeled costs,
    not measured historical fills/fees. Funding unavailable and excluded.
    """
    if direction not in ('LONG', 'SHORT'):
        raise ValueError('LONG/SHORT required')
    entry, exit_price, quantity = map(cash, (entry, exit_price, quantity))
    if min(entry, exit_price, quantity) <= 0:
        raise ValueError('Positive prices/quantity required')
    sign = 1 if direction == 'LONG' else -1
    gross = sign * quantity * (exit_price - entry)
    entry_fee, exit_fee = quantity * entry * FEE, quantity * exit_price * FEE
    entry_slip, exit_slip = quantity * entry * SLIPPAGE, quantity * exit_price * SLIPPAGE
    fees, slip = entry_fee + exit_fee, entry_slip + exit_slip
    net = gross - fees - slip
    return {k: float(v) for k, v in {'gross_pnl': gross, 'entry_fee': entry_fee, 'exit_fee': exit_fee,
            'fees': fees, 'entry_slippage': entry_slip, 'exit_slippage': exit_slip,
            'slippage': slip, 'net_pnl': net}.items()}


def drawdown(curve):
    peak = cash(curve[0]['equity']) if curve else EQUITY
    absolute, fraction = Decimal(0), Decimal(0)
    for row in curve:
        value = cash(row['equity'])
        peak = max(peak, value)
        absolute = max(absolute, peak - value)
        if peak > 0:
            fraction = max(fraction, (peak - value) / peak)
    return float(absolute), float(fraction)


def metrics(trades, curve, view):
    closed = [t for t in trades if t['status'] == 'CLOSED']
    open_cases = [t for t in trades if t['status'] != 'CLOSED']
    wins = [t for t in closed if t['net_pnl'] > 0]
    losses = [t for t in closed if t['net_pnl'] < 0]
    positive = sum(cash(t['net_pnl']) for t in wins)
    negative = sum(-cash(t['net_pnl']) for t in losses)
    gross = sum((cash(t['gross_pnl']) for t in closed), Decimal(0))
    fees = sum((cash(t['fees']) for t in closed), Decimal(0))
    slip = sum((cash(t['slippage']) for t in closed), Decimal(0))
    net = sum((cash(t['net_pnl']) for t in closed), Decimal(0))
    assert abs(gross - fees - slip - net) < Decimal('0.00000001')
    average_win = float(positive / len(wins)) if wins else None
    average_loss = float(negative / len(losses)) if losses else None
    r_values = [t['net_pnl'] / t['initial_risk'] for t in closed]
    holds = [t['exit_at'] - t['entry_at'] for t in closed]
    streak = longest = 0
    for t in sorted(closed, key=lambda t: (t['exit_at'], t['candidate_id'])):
        streak = streak + 1 if t['net_pnl'] < 0 else 0
        longest = max(longest, streak)
    dd, dd_fraction = drawdown(curve)
    payoff = average_win / average_loss if average_win is not None and average_loss else None
    return {'view': view, 'closed': len(closed), 'open_censored': len(open_cases), 'filled': len(trades),
        'WIN': len(wins), 'LOSS': len(losses), 'ZERO': len(closed) - len(wins) - len(losses),
        'win_rate_percent': 100 * len(wins) / len(closed) if closed else None,
        'gross_pnl': float(gross), 'fees': float(fees), 'slippage': float(slip), 'net_pnl': float(net),
        'financial_identity': 'PASS', 'profit_factor': float(positive / negative) if negative else None,
        'profit_factor_status': 'DEFINED' if negative else ('NO_TRADES' if not closed else 'NO_LOSS_DENOMINATOR'),
        'expectancy': float(net / len(closed)) if closed else None,
        'average_R': mean(r_values) if r_values else None, 'median_R': median(r_values) if r_values else None,
        'average_win': average_win, 'average_loss_magnitude': average_loss, 'payoff_ratio': payoff,
        'breakeven_WR_percent': 100 / (1 + payoff) if payoff is not None else None,
        'max_drawdown': dd, 'max_drawdown_fraction': dd_fraction, 'max_loss_streak': longest,
        'average_holding_seconds': mean(holds) if holds else None,
        'median_holding_seconds': median(holds) if holds else None,
        'initial_equity': float(EQUITY), 'final_equity': curve[-1]['equity'] if curve else float(EQUITY),
        'funding': None, 'funding_treatment': 'UNAVAILABLE_EXCLUDED_NOT_ASSERTED_ZERO',
        'trade_entry_allowed': False, 'execution_costs_are_model_assumptions': True,
        'performance_identifiable': bool(closed)}
