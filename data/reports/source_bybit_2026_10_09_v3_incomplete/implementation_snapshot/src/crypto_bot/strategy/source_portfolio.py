"""Sequential paper account with declared source exits; no exchange adapter."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite

from crypto_bot.common.models import Candle
from crypto_bot.strategy.source_engine import SourceSignal, sign


@dataclass(frozen=True)
class SourceRiskPolicy:
    initial_equity: float = 1170.0
    risk_fraction: float = 0.02
    fee_rate: float = 0.0006
    slippage_fraction: float = 0.0002
    # Project admission cap, preserving the prior isolated3x virtual budget.
    max_notional_equity: float = 3.0

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in asdict(self).values()):
            raise ValueError('nonfinite risk policy')
        if self.initial_equity <= 0 or not 0 < self.risk_fraction <= 0.02:
            raise ValueError('source validation risk must not exceed2%')
        if not 0 <= self.fee_rate < 0.1 or not 0 <= self.slippage_fraction < 0.1 or self.max_notional_equity <= 0:
            raise ValueError('invalid virtual costs/budget')


class SourcePortfolio:
    def __init__(self, policy: SourceRiskPolicy | None = None, *, mode: str = 'BACKTEST'):
        if mode not in ('BACKTEST', 'SHADOW'):
            raise ValueError('only BACKTEST/SHADOW')
        self.policy = policy or SourceRiskPolicy()
        self.mode = mode
        self.cash = self.policy.initial_equity
        self.pending: SourceSignal | None = None
        self.position: dict | None = None
        self.trades: list[dict] = []
        self.decisions: list[dict] = []
        self.equity: list[dict] = []
        self.last_mark: float | None = None

    def offer(self, signal: SourceSignal) -> bool:
        if self.pending is not None or self.position is not None:
            self.decisions.append({'signal_id': signal.signal_id, 'known_at': signal.known_at,
                                   'reason': 'ONE_SEQUENTIAL_ACCOUNT_BUSY', 'trade_entry_allowed': False})
            return False
        self.pending = signal
        self.decisions.append({'signal_id': signal.signal_id, 'known_at': signal.known_at,
                               'reason': 'VIRTUAL_LIMIT_PENDING', 'trade_entry_allowed': False})
        return True

    def cancel(self, signal_id: str, now: datetime, reason: str) -> None:
        if self.pending is not None and self.pending.signal_id == signal_id:
            self.pending = None
            self.decisions.append({'signal_id': signal_id, 'known_at': now, 'reason': 'CANCEL_' + reason,
                                   'trade_entry_allowed': False})

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
        if not isfinite(unit_risk) or unit_risk <= 0 or s * (signal.targets[0] * (1 - s * p.slippage_fraction) - entry) <= p.fee_rate * (entry + signal.targets[0]):
            self.cancel(signal.signal_id, c.open_time, 'COST_GEOMETRY')
            return False
        risk = self.cash * p.risk_fraction
        qty = risk / unit_risk
        if self.cash <= 0 or qty * entry > self.cash * p.max_notional_equity:
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

    def _exit(self, reference: float, fraction: float, now: datetime, reason: str) -> None:
        t, p = self.position, self.policy
        if t is None:
            raise ValueError('no virtual position')
        s = sign(t['direction'])
        qty = min(t['remaining'], t['quantity'] * fraction)
        price = reference * (1 - s * p.slippage_fraction)
        gross = s * (price - t['entry']) * qty
        quote_gross = s * (reference - t['entry_reference']) * qty
        fee = qty * price * p.fee_rate
        slip = qty * abs(price - reference)
        self.cash += gross - fee
        t['gross_pnl'] += gross
        t['quote_gross_pnl'] += quote_gross
        t['net_pnl'] += gross - fee
        t['fees'] += fee
        t['slippage'] += slip
        t['remaining'] -= qty
        t['fills'].append({'known_at': now, 'reference': reference, 'price': price, 'quantity': qty,
                           'gross_pnl': gross, 'exit_fee': fee, 'slippage': slip, 'reason': reason,
                           'trade_entry_allowed': False})
        if t['remaining'] <= t['quantity'] * 1e-12:
            t['status'] = 'CLOSED'
            t['exit_time'] = now
            t['exit_price'] = price
            t['exit_reason'] = reason
            t['result_R'] = t['net_pnl'] / t['risk_amount']
            t['result'] = 'WIN' if t['net_pnl'] > 1e-10 else 'LOSS' if t['net_pnl'] < -1e-10 else 'BE'
            t['holding_seconds'] = (now - t['entry_interval_start']).total_seconds()
            t['balance_after'] = self.cash
            self.position = None

    def on_bar(self, symbol: str, c: Candle) -> None:
        if not c.is_closed:
            raise ValueError('execution requires completed real candles')
        entered = False
        if self.pending is not None and self.pending.symbol == symbol and self.pending.known_at <= c.open_time:
            entered = self._entry(self.pending, c)
        t = self.position
        if t is None or t['symbol'] != symbol:
            return
        s = sign(t['direction'])
        self.last_mark = c.close
        # Stops dominate OHLC ambiguities. Gaps fill worse at OPEN. On the entry
        # bar favourable movement before the fill is unknown: only CLOSE proves it.
        stop_hit = c.low <= t['stop'] if s == 1 else c.high >= t['stop']
        if stop_hit:
            reference = min(c.open, t['stop']) if s == 1 else max(c.open, t['stop'])
            self._exit(reference, t['remaining'] / t['quantity'], c.close_time, 'ORIGINAL_SL_STOP_FIRST')
            return
        favourable = c.close if entered else c.high if s == 1 else c.low
        while self.position is not None and t['next_target'] < len(t['targets']):
            n = t['next_target']
            target = t['targets'][n]
            if s * (favourable - target) < 0:
                break
            t['next_target'] += 1
            self._exit(target, t['fractions'][n], c.close_time, 'SOURCE_TARGET_' + str(n + 1))

    def mark(self, now: datetime) -> None:
        unrealized = 0.0
        if self.position is not None and self.last_mark is not None:
            t = self.position
            unrealized = sign(t['direction']) * (self.last_mark - t['entry']) * t['remaining']
            # Liquidation-cost NAV, marked but never force-closed at endpoint.
            unrealized -= t['remaining'] * self.last_mark * self.policy.fee_rate
        self.equity.append({'known_at': now, 'cash': self.cash, 'equity': self.cash + unrealized,
                            'trade_entry_allowed': False})
