"""Holding and friction accounting for closed cases, distinct from account NAV."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean

from crypto_bot.strategy.portfolio_statistics import trade_statistics

BINS = (('<1h', 0, 3600), ('1–4h', 3600, 14400), ('4–12h', 14400, 43200),
        ('12–24h', 43200, 86400), ('1–3d', 86400, 259200),
        ('3–7d', 259200, 604800), ('7+d', 604800, float('inf')))


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def holding_seconds(trade):
    if trade['status'] != 'CLOSED':
        return None
    return (instant(trade['exit_time']) - instant(trade['entry_interval_start'])).total_seconds()


def quantile(values, q):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * q
    lo = int(index)
    hi = min(lo+1, len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(index-lo)


def closed_statistics(trades, *, gross_includes_slippage=True):
    trades = [t for t in trades if t['status'] == 'CLOSED']
    base = trade_statistics(trades)
    costs = []
    gross_moves, net_moves, planned_rr = [], [], []
    gross, fees, slip, turnover, positive_gross = 0., 0., 0., 0., 0.
    for t in trades:
        f, s = t['fees_total'], t['slippage_total']
        g = t['gross_pnl'] + (s if gross_includes_slippage else 0.)
        if abs(g-f-s-t['net_pnl']) > 1e-7 * max(1., abs(g), f, s):
            raise ValueError('Gross-reference minus fees minus slippage mismatch')
        gross += g
        fees += f
        slip += s
        positive_gross += max(0., g)
        costs.append(f+s)
        entry = t.get('theoretical_entry', t.get('entry_quote', t.get('entry_price')))
        qty = t['quantity']
        fill_turnover = qty*t['actual_entry_after_slippage'] + sum(x['quantity']*x['price'] for x in t['fills'])
        turnover += fill_turnover
        gross_moves.append(g/(qty*entry) if qty*entry else 0.)
        net_moves.append(t['net_pnl']/(qty*entry) if qty*entry else 0.)
        targets = t.get('targets', [])
        if len(targets) == 3 and entry != t['stop']:
            planned_rr.append(sum(fraction*abs(price-entry) for fraction, price in zip((.4, .3, .3), targets))/abs(entry-t['stop']))
    hours = [holding_seconds(t)/3600 for t in trades]
    base.update(total_trades=len(trades), gross_pnl=gross, fees=fees, slippage=slip,
                cost_identity_residual=gross-fees-slip-base['net_pnl'], turnover=turnover,
                total_costs=fees+slip,
                costs_percent_gross_profit=100*(fees+slip)/positive_gross if positive_gross else None,
                costs_percent_turnover=100*(fees+slip)/turnover if turnover else None,
                average_cost_per_trade=mean(costs) if costs else None,
                average_gross_move_fraction=mean(gross_moves) if gross_moves else None,
                average_net_move_fraction=mean(net_moves) if net_moves else None,
                average_planned_RR=mean(planned_rr) if planned_rr else None,
                holding_hours={'mean': mean(hours) if hours else None,
                               'median': quantile(hours, .5), 'p25': quantile(hours, .25),
                               'p75': quantile(hours, .75), 'p90': quantile(hours, .9),
                               'min': min(hours) if hours else None, 'max': max(hours) if hours else None},
                holding_definition='ENTRY_INTERVAL_START_TO_EXIT_KNOWN_CLOSE_UPPER_BOUND',
                trade_entry_allowed=False)
    return base


def breakdowns(trades, *, gross_includes_slippage=True):
    trades = [t for t in trades if t['status'] == 'CLOSED']
    calculate = lambda rows: closed_statistics(rows, gross_includes_slippage=gross_includes_slippage)
    bins = {name: calculate([t for t in trades if lower <= holding_seconds(t) < upper])
            for name, lower, upper in BINS}
    groups = {}
    for name, key in [('direction', lambda t: t['direction']), ('coin', lambda t: t['symbol']),
                      ('setup', lambda t: t.get('source_setup', t.get('setup_type', t.get('setup')))),
                      ('timeframe', lambda t: str(t['htf'])+'/'+str(t['ltf'])),
                      ('year', lambda t: str(instant(t['entry_interval_start']).year)),
                      ('month', lambda t: instant(t['entry_interval_start']).strftime('%Y-%m')),
                      ('day', lambda t: instant(t['entry_interval_start']).strftime('%Y-%m-%d'))]:
        buckets = defaultdict(list)
        for t in trades:
            buckets[key(t)].append(t)
        groups[name] = {k: calculate(v) for k, v in sorted(buckets.items())}
    return {'holding_bins': bins, 'groups': groups,
            'short': calculate([t for t in trades if holding_seconds(t) < 4*3600]),
            'medium': calculate([t for t in trades if holding_seconds(t) >= 4*3600])}
