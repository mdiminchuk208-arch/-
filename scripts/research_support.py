"""Read-only research measurements for the immutable offline Strategy Engine."""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
import csv
from datetime import datetime, timedelta
import gzip
from hashlib import sha256
import json
from math import sqrt
from statistics import mean, stdev

from crypto_bot.data.models import MarketCandle
from crypto_bot.strategy.portfolio_statistics import trade_statistics


def as_time(value):
    return datetime.fromisoformat(value) if isinstance(value,str) else value


def check_baseline(repo):
    lock = json.loads((repo / 'data/reports/robustness_research/baseline_lock.json').read_text())
    for path, digest in lock['code_hashes'].items():
        if sha256((repo / path).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen strategy/config changed: ' + path)
    return lock


def read_compressed(path, minutes, *, begin=None, end=None):
    begin_ms=int(begin.timestamp()*1000) if begin is not None else None
    end_ms=int(end.timestamp()*1000) if end is not None else None
    result=[]
    with gzip.open(path, 'rt', newline='') as handle:
        for row in csv.DictReader(handle):
            stamp=int(row['open_time_ms'])
            if (begin_ms is not None and stamp<begin_ms) or (end_ms is not None and stamp+minutes*60000>end_ms):
                continue
            result.append(MarketCandle(row['exchange'], row['symbol'], row['interval'], stamp,
            *[float(row[k]) for k in ('open', 'high', 'low', 'close')],
            float(row['volume_base']) if row['volume_base'] else None,
            float(row['turnover_quote']) if row['turnover_quote'] else None,
            row['is_closed'] == '1').to_strategy_candle(minutes * 60000))
    return result


def regime(daily, when):
    """Only 31 preceding complete consecutive daily closes; no future quantiles."""
    end = bisect_right([c.close_time for c in daily], when)
    rows = daily[max(0, end - 31):end]
    if len(rows) < 31 or any(b.close_time-a.close_time != timedelta(days=1) for a,b in zip(rows,rows[1:])):
        return 'UNKNOWN', 'UNKNOWN'
    change = rows[-1].close / rows[0].close - 1
    returns = [b.close/a.close-1 for a,b in zip(rows,rows[1:])]
    volatility = stdev(returns)
    return ('BULL' if change > .1 else 'BEAR' if change < -.1 else 'SIDEWAYS',
            'HIGH' if volatility > .04 else 'LOW' if volatility < .02 else 'MEDIUM')


def drawdown_duration(curve, start, initial):
    peak = initial
    peak_time = start
    maximum = 0.0
    longest = 0.0
    underwater = False
    for row in curve:
        when = datetime.fromisoformat(row['timestamp']) if isinstance(row['timestamp'],str) else row['timestamp']
        value = row['equity']
        if underwater:
            longest = max(longest, (when-peak_time).total_seconds())
        if value >= peak:
            peak, peak_time = value, when
            underwater = False
        else:
            maximum = max(maximum, (peak-value)/peak)
            longest = max(longest, (when-peak_time).total_seconds())
            underwater = True
    return maximum, longest


def interval_union_seconds(intervals):
    end = None
    seconds = 0.0
    for begin, stop in sorted(intervals):
        if end is None or begin >= end:
            seconds += max(0.0, (stop-begin).total_seconds())
        elif stop > end:
            seconds += (stop-end).total_seconds()
        end = max(end, stop) if end is not None else stop
    return seconds


def performance(portfolio, observed, start, end):
    trades = list(portfolio.trades.values())
    closed = [t for t in trades if t['status']=='CLOSED']
    base = trade_statistics(closed)
    ready = {s.signal_id for s in observed if s.status=='READY_FOR_VIRTUAL_ENTRY'}
    setups = {s.signal_id for s in observed}
    base.update(setups=len(setups), ready=len(ready), entries=len(trades),
                ready_filled_rate=len(trades)/len(ready) if ready else None,
                open_trades=len(trades)-len(closed), initial_equity=portfolio.starting_balance,
                final_equity=portfolio.equity, equity_pnl=portfolio.equity-portfolio.starting_balance,
                realized_account_balance_pnl=portfolio.realized_pnl,
                unrealized_pnl=portfolio.unrealized_pnl, fees=portfolio.fees_paid,
                slippage_cost=portfolio.slippage_cost,
                long_entries=sum(t['direction']=='LONG' for t in trades),
                short_entries=sum(t['direction']=='SHORT' for t in trades),
                tp_sl_counts=dict(Counter(f['reason'] for t in trades for f in t['fills'])),
                admission_blocks=dict(Counter(d.reason for d in portfolio.journal if d.action=='VIRTUAL_ENTRY_BLOCKED')),
                trades_per_month=len(trades)/((end-start).total_seconds()/86400/30.4375))
    positive = [t['net_pnl'] for t in closed if t['net_pnl']>1e-9]
    negative = [-t['net_pnl'] for t in closed if t['net_pnl']< -1e-9]
    base['payoff_ratio'] = mean(positive)/mean(negative) if positive and negative else None
    base['gross_edge_before_fees'] = sum(t['gross_pnl'] for t in closed)
    base['fees_as_percent_gross_edge'] = 100*sum(t['fees_total'] for t in closed)/base['gross_edge_before_fees'] if base['gross_edge_before_fees']>0 else None
    dd, duration = drawdown_duration(portfolio.equity_curve,start,portfolio.starting_balance)
    base['max_drawdown_fraction'], base['max_drawdown_duration_seconds'] = dd, duration
    intervals = [(max(start,as_time(t['entry_interval_start'])),
                  min(end,as_time(t['exit_time'])) if t['status']=='CLOSED' else end) for t in trades]
    base['exposure_fraction_upper_bound'] = interval_union_seconds(intervals)/(end-start).total_seconds()
    base['exposure_policy'] = 'UNION_ENTRY_BAR_START_TO_EXIT_INCLUDES_UNKNOWN_PRE_TOUCH_PART_OF_ENTRY_BAR'
    base['average_holding_seconds_known_time_lower_bound'] = mean(
        (as_time(t['exit_time'])-as_time(t['entry_time'])).total_seconds() for t in closed) if closed else None
    # Full UTC day return sampling, including zero-return days. Partial endpoint
    # days are excluded rather than treated as complete daily observations.
    day_closes = {}
    for row in portfolio.equity_curve:
        when = datetime.fromisoformat(row['timestamp']) if isinstance(row['timestamp'],str) else row['timestamp']
        if when.hour==when.minute==when.second==when.microsecond==0:
            day_closes[when]=row['equity']
    if start.hour==start.minute==start.second==start.microsecond==0:
        day_closes[start]=portfolio.starting_balance
    daily = [day_closes[b]/day_closes[a]-1 for a,b in zip(sorted(day_closes),sorted(day_closes)[1:]) if b-a==timedelta(days=1)]
    base.update(daily_return_observations=len(daily), sharpe=None, sortino=None, calmar=None,
                inference_status='INSUFFICIENT_SAMPLE' if len(closed)<100 else 'ELIGIBLE_FOR_FURTHER_EDGE_ASSESSMENT')
    if len(daily)>=90 and len(closed)>=30:
        deviation = stdev(daily)
        downside = sqrt(mean(min(0,r)**2 for r in daily))
        base['sharpe'] = sqrt(365)*mean(daily)/deviation if deviation else None
        base['sortino'] = sqrt(365)*mean(daily)/downside if downside else None
        annual_return = (portfolio.equity/portfolio.starting_balance)**(365*86400/(end-start).total_seconds())-1 if portfolio.equity>0 else -1
        base['calmar'] = annual_return/dd if dd else None
        base['ratio_status'] = '365_DAY_UTC_SAMPLING_ZERO_RISK_FREE_RATE'
    else:
        base['ratio_status'] = 'WITHHELD_BELOW_90_DAILY_RETURNS_OR_30_CLOSED_TRADES'
    base['monte_carlo_status'] = 'ELIGIBLE' if len(closed)>=50 else 'WITHHELD_BELOW_50_COMPARABLE_CLOSED_TRADES'
    base['trade_entry_allowed'] = False
    base['by_direction']={side:trade_statistics(t for t in trades if t['direction']==side)
                          for side in ('LONG','SHORT')}
    base['by_symbol']={s:trade_statistics(t for t in trades if t['symbol']==s)
                       for s in sorted({s.symbol for s in observed})}
    return base
