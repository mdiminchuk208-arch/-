"""Deterministic isolated-margin simulation; no exchange or order integration.

An already available limit can fill at a later OPEN or actual wick touch.
Closed OHLC bars have unknown intrabar order: an old stop wins ties, then
TP1/BE wins over higher TPs. On an intrabar entry only the subsequent CLOSE
proves favourable movement; the whole bar HIGH/LOW cannot establish a profit.
Fees and slippage apply to every partial exit. Funding/liquidation are not modelled.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Mapping, Sequence

from crypto_bot.common.models import Candle, Direction
from crypto_bot.strategy.market_analysis import StructureAnalysisMode
from crypto_bot.strategy.replay import EngineMode, StrategySignal


@dataclass(frozen=True)
class SimulationPolicy:
    risk_fraction: float = 0.02
    max_total_risk: float = 0.06
    daily_loss_limit: float = 0.04
    leverage: float = 3.0
    margin_mode: str = "Isolated"
    fee_fraction: float = 0.0006
    slippage_fraction: float = 0.0002
    reentry_min_score: int = 75
    resting_limit_entries: bool = True

    def __post_init__(self):
        values = (self.risk_fraction, self.max_total_risk, self.daily_loss_limit,
                  self.leverage, self.fee_fraction, self.slippage_fraction)
        if not all(isfinite(v) for v in values):
            raise ValueError("simulation policy values must be finite")
        if not 0.02 <= self.risk_fraction <= 0.05 or not 0 < self.max_total_risk <= 0.06:
            raise ValueError("risk must be 2%-5%; portfolio cap must be at most 6%")
        if self.risk_fraction > self.max_total_risk or not 0 < self.daily_loss_limit < 1:
            raise ValueError("invalid risk or daily loss budget")
        if not 1 <= self.leverage <= 5 or self.margin_mode != "Isolated":
            raise ValueError("only Isolated leverage in [1, 5] is supported")
        if not 0 <= self.fee_fraction < 0.1 or not 0 <= self.slippage_fraction < 0.1:
            raise ValueError("invalid fees/slippage")
        if not isinstance(self.reentry_min_score, int) or not 75 <= self.reentry_min_score <= 100:
            raise ValueError("reentry score must be at least 75")
        if type(self.resting_limit_entries) is not bool:
            raise ValueError("resting_limit_entries must be boolean")


@dataclass(frozen=True)
class Decision:
    sequence: int
    time: datetime
    symbol: str
    signal_id: str
    action: str
    reason: str
    quantity: float = 0.0
    price: float | None = None
    net_pnl: float = 0.0
    reference_price: float | None = None
    gross_pnl: float = 0.0
    entry_fee_allocation: float = 0.0
    exit_fee: float = 0.0
    slippage_cost: float = 0.0
    balance_change: float = 0.0
    trade_entry_allowed: bool = field(default=False, init=False)


@dataclass
class VirtualPosition:
    signal: StrategySignal
    entry_time: datetime
    entry_price: float
    quantity: float
    remaining_fraction: float
    stop_loss: float
    tp_stage: int = 0
    entry_fee: float = 0.0


class VirtualPortfolio:
    """Use the same state machine in BACKTEST and SHADOW; admissions are virtual.

    Supply all execution-symbol bars for each timestamp in one batch to avoid
    using one symbol's candle-close PnL for another symbol's same-open risk guard.
    Risk day is UTC, daily limit is latched until the next UTC day. Re-entry is
    only on a new signal after completion, with score >=75.
    """
    def __init__(self, *, equity: float = 10000.0, policy: SimulationPolicy | None = None,
                 mode: EngineMode | str = EngineMode.BACKTEST):
        if not isfinite(equity) or equity <= 0:
            raise ValueError("equity must be finite and positive")
        self.mode, self.policy = EngineMode(mode), policy or SimulationPolicy()
        self.starting_balance = self.balance = equity
        self.unrealized_pnl = self.fees_paid = self.slippage_cost = 0.0
        self.equity_peak = self.lowest_equity = equity
        self.max_drawdown = 0.0
        self.status = "ACTIVE"
        self.marks: dict[str, float] = {}
        self.trades: dict[str, dict] = {}
        self.equity_curve: list[dict] = []
        self.positions: dict[str, VirtualPosition] = {}
        self.pending: dict[str, StrategySignal] = {}
        self.completed_symbols: set[str] = set()
        self.consumed_ids: set[str] = set()
        self.terminal_ids: set[str] = set()
        self._journal: list[Decision] = []
        self._last_close: datetime | None = None
        self._bar_duration: timedelta | None = None
        self._day = None
        self._day_start_equity = equity
        self._day_start_balance = equity
        self._daily_blocked = False
        self.replay_context: dict = {}

    @property
    def trade_entry_allowed(self):
        return False

    def snapshot(self):
        from crypto_bot.strategy.checkpoint import snapshot
        return snapshot(self)

    @property
    def last_close(self):
        return self._last_close

    def save_checkpoint(self, path):
        from crypto_bot.strategy.checkpoint import save_checkpoint
        save_checkpoint(self, path)

    @classmethod
    def load_checkpoint(cls, path):
        from crypto_bot.strategy.checkpoint import load_checkpoint
        return load_checkpoint(path)

    @property
    def equity(self):
        return self.balance + self.unrealized_pnl

    @property
    def realized_pnl(self):
        return self.balance - self.starting_balance

    @property
    def allocated_margin(self):
        return sum(p.quantity * p.remaining_fraction * p.entry_price / self.policy.leverage
                   for p in self.positions.values())

    @property
    def available_equity(self):
        return self.equity - self.allocated_margin

    @property
    def aggregate_stop_risk(self):
        return sum(p.quantity * p.remaining_fraction * self._loss_per_unit(
            p.entry_price, p.stop_loss, p.signal.direction) for p in self.positions.values())

    @property
    def daily_realized_pnl(self):
        return self.balance - self._day_start_balance

    def _mark(self, prices):
        self.marks.update(prices)
        self.unrealized_pnl = sum(p.quantity * p.remaining_fraction *
            (1 if p.signal.direction == Direction.LONG else -1) *
            (self.marks[p.signal.symbol] - p.entry_price) for p in self.positions.values())
        if self.equity <= 0 or self.balance <= 0:
            self.status = "BANKRUPT"

    def _check_daily_loss(self):
        if self.daily_realized_pnl <= -self._day_start_equity * self.policy.daily_loss_limit:
            self._daily_blocked = True

    @property
    def journal(self):
        return tuple(self._journal)

    def _log(self, when, signal, action, reason, quantity=0.0, price=None, pnl=0.0, **costs):
        self._journal.append(Decision(len(self._journal) + 1, when, signal.symbol,
                                      signal.signal_id, action, reason, quantity, price, pnl, **costs))

    def _exit_price(self, reference, direction):
        sign = 1 if direction == Direction.LONG else -1
        return reference * (1 - sign * self.policy.slippage_fraction)

    def _loss_per_unit(self, entry, stop, direction):
        sign = 1 if direction == Direction.LONG else -1
        exit_price = self._exit_price(stop, direction)
        return max(0.0, sign * (entry - exit_price) + self.policy.fee_fraction * (entry + exit_price))

    def _breakeven(self, position):
        f, s, entry = self.policy.fee_fraction, self.policy.slippage_fraction, position.entry_price
        if position.signal.direction == Direction.LONG:
            return entry * (1 + f) / ((1 - f) * (1 - s))
        return entry * (1 - f) / ((1 + f) * (1 + s))

    def _close_fraction(self, position, fraction, reference, when, reason):
        self._roll_day(when)
        quantity = position.quantity * fraction
        exit_price = self._exit_price(reference, position.signal.direction)
        sign = 1 if position.signal.direction == Direction.LONG else -1
        gross = quantity * sign * (exit_price - position.entry_price)
        entry_allocation = position.entry_fee * fraction
        exit_fee = quantity * exit_price * self.policy.fee_fraction
        slip = quantity * abs(reference - exit_price)
        pnl = gross - entry_allocation - exit_fee
        self.balance += gross - exit_fee  # Entry fee was charged once, at admission.
        self.fees_paid += exit_fee
        self.slippage_cost += slip
        position.remaining_fraction = max(0.0, position.remaining_fraction - fraction)
        self._log(when, position.signal, "VIRTUAL_EXIT", reason, quantity, exit_price, pnl,
                  reference_price=reference, gross_pnl=gross, entry_fee_allocation=entry_allocation,
                  exit_fee=exit_fee, slippage_cost=slip, balance_change=gross - exit_fee)
        trade = self.trades[position.signal.signal_id]
        trade['fills'].append(asdict(self._journal[-1]))
        trade['gross_pnl'] += gross
        trade['net_pnl'] += pnl
        trade['fees_total'] += exit_fee
        trade['slippage_total'] += slip
        if reason.startswith('STOP'):
            trade['adverse_gap'] = reference != position.stop_loss
        self._check_daily_loss()
        if position.remaining_fraction < 1e-12:
            self.positions.pop(position.signal.symbol)
            self.completed_symbols.add(position.signal.symbol)
            trade.update(status='CLOSED', exit_time=when, exit_reason=reason,
                         duration_seconds=(when - position.entry_time).total_seconds(),
                         result_R=trade['net_pnl'] / trade['risk_amount'])
        self._mark({})
        trade['max_equity_during_trade'] = max(trade['max_equity_during_trade'], self.equity)
        if trade['status'] == 'CLOSED':
            trade['balance_after_trade'] = self.balance
            trade['equity_after_trade'] = self.equity

    def _manage(self, position, candle):
        long = position.signal.direction == Direction.LONG
        stop_hit = candle.low <= position.stop_loss if long else candle.high >= position.stop_loss
        if stop_hit:
            reference = min(position.stop_loss, candle.open) if long else max(position.stop_loss, candle.open)
            self._close_fraction(position, position.remaining_fraction, reference, candle.close_time, "STOP_FIRST_CONSERVATIVE")
            return
        for stage, fraction in enumerate((0.4, 0.3, 0.3)):
            if stage < position.tp_stage:
                continue
            target = position.signal.targets[stage]
            hit = candle.high >= target if long else candle.low <= target
            if not hit:
                break
            self._close_fraction(position, fraction, target, candle.close_time, f"TP{stage + 1}")
            position.tp_stage = stage + 1
            if stage == 0:
                position.stop_loss = self._breakeven(position)
                self.trades[position.signal.signal_id]['new_breakeven'] = position.stop_loss
                self._log(candle.close_time, position.signal, "VIRTUAL_STOP_UPDATE", "BREAKEVEN_WITH_FEES_AND_SLIPPAGE", price=position.stop_loss)
                be_hit = candle.low <= position.stop_loss if long else candle.high >= position.stop_loss
                if be_hit:
                    self._close_fraction(position, position.remaining_fraction, position.stop_loss,
                                         candle.close_time, "BREAKEVEN_SAME_BAR_CONSERVATIVE")
                    return

    def _roll_day(self, when):
        day = when.astimezone(timezone.utc).date()
        if day != self._day:
            self._day, self._day_start_equity, self._daily_blocked = day, self.equity, False
            self._day_start_balance = self.balance

    def _admit(self, signal, candle, *, intrabar=False):
        sign = 1 if signal.direction == Direction.LONG else -1
        reference, when = candle.open, candle.open_time
        if intrabar:
            # A resting buy approaches its quote from above; a sell from below.
            # Gap-through opens outside the approved zone cannot be reinterpreted
            # as a fill from the opposite side. No signal from this close is used.
            if not (sign * (candle.open - signal.optimal_entry) > 0
                    and candle.low <= signal.optimal_entry <= candle.high):
                return False
            reference, when = signal.optimal_entry, candle.close_time
        elif not (signal.entry_zone.low <= candle.open <= signal.entry_zone.high
                  and (not self.policy.resting_limit_entries or sign * (candle.open - signal.optimal_entry) <= 0)):
            self._log(when, signal, 'VIRTUAL_ENTRY_DEFERRED', 'NEXT_OPEN_OUTSIDE_ENTRY_ZONE_OR_LIMIT')
            return False
        reason = None
        if signal.symbol in self.positions:
            reason = "PREVIOUS_POSITION_STILL_OPEN"
        elif self._daily_blocked:
            reason = "DAILY_LOSS_LIMIT_LATCHED"
        elif signal.symbol in self.completed_symbols and signal.score < self.policy.reentry_min_score:
            reason = "REENTRY_SCORE_BELOW_75"
        elif self.status != 'ACTIVE' or self.equity <= 0:
            reason = "EQUITY_EXHAUSTED"
        if reason:
            self._log(when, signal, "VIRTUAL_ENTRY_BLOCKED", reason)
            self.consumed_ids.add(signal.signal_id)
            return True
        entry = reference * (1 + sign * self.policy.slippage_fraction)
        # Costs must not shift the fill across the stop or first target.
        if not (sign * (entry - signal.stop_loss) > 0 and sign * (signal.targets[0] - entry) > 0):
            self._log(when, signal, "VIRTUAL_ENTRY_BLOCKED", "COST_ADJUSTED_FILL_GEOMETRY")
            self.consumed_ids.add(signal.signal_id)
            return True
        target_exit = self._exit_price(signal.targets[0], signal.direction)
        first_target_net = sign * (target_exit - entry) - self.policy.fee_fraction * (entry + target_exit)
        if first_target_net <= 0:
            # Otherwise the calculated BE stop lies beyond TP1 and could be
            # falsely filled at a price outside the bar after TP1 is hit.
            self._log(when, signal, "VIRTUAL_ENTRY_BLOCKED", "TP1_NOT_POSITIVE_AFTER_COSTS")
            self.consumed_ids.add(signal.signal_id)
            return True
        risk = self.equity * self.policy.risk_fraction
        quantity = risk / self._loss_per_unit(entry, signal.stop_loss, signal.direction)
        if not isfinite(quantity) or quantity <= 0:
            self._log(when, signal, 'VIRTUAL_ENTRY_BLOCKED', 'INVALID_QUANTITY')
            self.consumed_ids.add(signal.signal_id)
            return True
        existing_risk, margin = self.aggregate_stop_risk, self.allocated_margin
        entry_fee = quantity * entry * self.policy.fee_fraction
        entry_slip = quantity * abs(entry - reference)
        equity_after_cost = self.equity - entry_fee - entry_slip
        if existing_risk + risk > equity_after_cost * self.policy.max_total_risk + 1e-9:
            reason = "TOTAL_RISK_CAP_6_PERCENT"
        elif margin + quantity * entry / self.policy.leverage > equity_after_cost:
            reason = "ISOLATED_MARGIN_BUDGET"
        if reason:
            self._log(when, signal, "VIRTUAL_ENTRY_BLOCKED", reason)
        else:
            initial_equity = self.equity
            self.positions[signal.symbol] = VirtualPosition(signal, when, entry, quantity, 1.0, signal.stop_loss,
                                                          entry_fee=entry_fee)
            self.balance -= entry_fee
            self.fees_paid += entry_fee
            self.slippage_cost += entry_slip
            # The pre-entry OPEN is not a post-entry mark and cannot create
            # imaginary profits for the next symbol's risk budget.
            self._mark({signal.symbol: reference})
            self._check_daily_loss()
            self.trades[signal.signal_id] = dict(
                trade_id=signal.signal_id, signal_id=signal.signal_id, symbol=signal.symbol,
                direction=signal.direction.name, htf=signal.htf_minutes, ltf=signal.ltf_minutes,
                setup=signal.level_policy, score=signal.score, signal_time=signal.event_time,
                ready_time=max(signal.entry_geometry_ready_time, signal.levels_known_at),
                entry_time=when, theoretical_entry=reference,
                fill_model='RESTING_LIMIT_TOUCH' if intrabar else 'NEXT_OPEN',
                entry_time_precision='BAR_INTERVAL_KNOWN_AT_CLOSE' if intrabar else 'EXACT_OPEN',
                entry_interval_start=candle.open_time, entry_interval_end=candle.close_time,
                actual_entry_after_slippage=entry, entry_zone=asdict(signal.entry_zone),
                stop=signal.stop_loss, targets=list(signal.targets), initial_equity=initial_equity,
                risk_percent=self.policy.risk_fraction, risk_amount=risk,
                stop_distance=abs(entry - signal.stop_loss), stop_percent=abs(entry - signal.stop_loss)/entry,
                quantity=quantity, notional=quantity*entry, leverage=self.policy.leverage,
                required_margin=quantity*entry/self.policy.leverage,
                aggregate_risk_before=existing_risk, aggregate_risk_after=self.aggregate_stop_risk,
                aggregate_risk_fraction_after=self.aggregate_stop_risk/self.equity,
                entry_fee=entry_fee, fees_total=entry_fee, slippage_total=entry_slip,
                gross_pnl=0.0, net_pnl=0.0, fills=[], new_breakeven=None, status='OPEN',
                result_R=None, MFE=0.0, MAE=0.0,
                excursion_policy=('ENTRY_BAR_CLOSE_ONLY_FAVOURABLE_FULL_ADVERSE_ENVELOPE' if intrabar
                                  else 'FULL_CLOSED_BAR_ENVELOPE_ORDER_UNKNOWN'),
                max_equity_during_trade=self.equity, adverse_gap=False,
            )
            self._log(when, signal, "VIRTUAL_ENTRY", "RESTING_LIMIT_ACTUAL_TOUCH" if intrabar else "NEXT_OPEN_INSIDE_ENTRY_ZONE", quantity, entry,
                      -entry_fee, reference_price=reference, slippage_cost=entry_slip, balance_change=-entry_fee)
        self.consumed_ids.add(signal.signal_id)
        return True

    @staticmethod
    def _validate_signal(signal, close_time, bars, mode):
        if signal.status not in {'WAITING_FOR_ENTRY_GEOMETRY','REJECTED_ENTRY_GEOMETRY',
                'SOURCE_CONTEXT_BLOCKED','WAITING_FOR_SOURCE_LEVELS','WAITING_FOR_AUTO_LEVELS',
                'READY_FOR_VIRTUAL_ENTRY','INVALIDATED'}:
            raise ValueError('invalid signal state')
        if signal.event_time.utcoffset() is None or signal.sfp_time.utcoffset() is None or signal.bos_time.utcoffset() is None:
            raise ValueError("signal timestamps must be timezone-aware")
        if not signal.sfp_time < signal.bos_time <= signal.event_time or signal.event_time != close_time:
            raise ValueError("signals must be causal and submitted at their observation close")
        if signal.symbol not in bars or signal.ltf_minutes != int((bars[signal.symbol].close_time - bars[signal.symbol].open_time).total_seconds() / 60):
            raise ValueError("signal symbol/timeframe must match execution bar")
        if EngineMode(signal.mode) != mode or signal.analysis_mode != StructureAnalysisMode.SOURCE_CONSERVATIVE or signal.trade_entry_allowed:
            raise ValueError("only safe source-conservative signals in the portfolio mode are accepted")
        if signal.direction not in (Direction.LONG, Direction.SHORT) or not isinstance(signal.score, int) or not 0 <= signal.score <= 100:
            raise ValueError("invalid signal direction/score")
        for timestamp in (signal.entry_geometry_ready_time, signal.levels_known_at):
            if timestamp is not None and (timestamp.utcoffset() is None or timestamp > signal.event_time):
                raise ValueError("entry references cannot be available in the future")
        if signal.status == "READY_FOR_VIRTUAL_ENTRY":
            if signal.entry_zone is None or signal.stop_loss is None or len(signal.targets) != 3:
                raise ValueError("ready signal requires entry zone, SL and three targets")
            if signal.entry_geometry_ready_time is None or signal.levels_known_at is None:
                raise ValueError("ready signal requires geometry and level availability timestamps")
            if signal.entry_geometry_ready_time < signal.bos_time:
                raise ValueError("entry geometry cannot precede BOS")
            if (signal.optimal_entry is None or not isfinite(signal.optimal_entry) or
                    not signal.entry_zone.low <= signal.optimal_entry <= signal.entry_zone.high):
                raise ValueError('optimal entry must lie inside the entry zone')
            prices = (signal.stop_loss, *signal.targets)
            if not all(isfinite(v) and v > 0 for v in prices):
                raise ValueError("ready prices must be finite and positive")
            sign = 1 if signal.direction == Direction.LONG else -1
            values = tuple(sign * v for v in (signal.stop_loss, signal.entry_zone.low if sign == 1 else signal.entry_zone.high,
                                             signal.entry_zone.high if sign == 1 else signal.entry_zone.low, *signal.targets))
            if not values[0] < values[1] <= values[2] < values[3] < values[4] < values[5]:
                raise ValueError("ready signal stop/entry/target geometry is invalid")

    def step(self, bars: Mapping[str, Candle], signals: Sequence[StrategySignal] = ()):
        if not bars:
            raise ValueError("execution batch cannot be empty")
        first = next(iter(bars.values()))
        for candle in bars.values():
            if not candle.is_closed or candle.low <= 0 or (candle.open_time, candle.close_time) != (first.open_time, first.close_time):
                raise ValueError("batch must contain closed positive-price bars of the same interval")
        if self._last_close is not None and first.open_time != self._last_close:
            raise ValueError("execution batches must be contiguous and cannot be replayed")
        duration = first.close_time - first.open_time
        if duration.total_seconds()%60:
            raise ValueError('execution requires a whole-minute timeframe')
        if self._bar_duration is not None and duration != self._bar_duration:
            raise ValueError("execution timeframe cannot change within a replay")
        if set(self.positions) - set(bars):
            raise ValueError("every open position requires a bar in each batch")
        for signal in signals:
            self._validate_signal(signal, first.close_time, bars, self.mode)
        unique: dict[str, StrategySignal] = {}
        for signal in signals:
            if signal.signal_id in unique and unique[signal.signal_id] != signal:
                raise ValueError('conflicting signal states in one execution batch')
            unique[signal.signal_id] = signal
        duplicates = len(signals) - len(unique)
        signals = tuple(unique.values())
        self._mark({symbol: c.open for symbol, c in bars.items()})
        self._roll_day(first.open_time)
        # All admissions precede every same-bar exit. No foreign symbol's future
        # close profit funds risk. OPEN fills precede interval-ambiguous touches.
        for key, signal in sorted(tuple(self.pending.items()), key=lambda item: (item[1].symbol, item[0])):
            if signal.symbol in bars and self._admit(signal, bars[signal.symbol]):
                self.pending.pop(key)
        intrabar_ids = set()
        if self.policy.resting_limit_entries:
            for key, signal in sorted(tuple(self.pending.items()), key=lambda item: (item[1].symbol, item[0])):
                if signal.symbol in bars and self._admit(signal, bars[signal.symbol], intrabar=True):
                    self.pending.pop(key)
                    if key in self.trades:
                        intrabar_ids.add(key)
        for symbol in sorted(tuple(self.positions)):
            position, candle = self.positions[symbol], bars[symbol]
            if position.signal.signal_id in intrabar_ids:
                # This is a conservative management envelope, not invented market
                # data. CLOSE is provably after the touch; profitable extremes
                # may have preceded it. An adverse crossing after a proper-side
                # approach remains possible and wins all ambiguous outcomes.
                long = position.signal.direction == Direction.LONG
                candle = replace(candle, open=position.entry_price,
                    high=max(position.entry_price, candle.close) if long else max(candle.high, position.entry_price),
                    low=min(candle.low, position.entry_price) if long else min(position.entry_price, candle.close))
            trade = self.trades[position.signal.signal_id]
            sign = 1 if position.signal.direction == Direction.LONG else -1
            trade['MFE'] = max(trade['MFE'], sign * ((candle.high if sign == 1 else candle.low) - position.entry_price))
            trade['MAE'] = max(trade['MAE'], -sign * ((candle.low if sign == 1 else candle.high) - position.entry_price))
            self._manage(position, candle)
        self._mark({symbol: c.close for symbol, c in bars.items()})
        self.equity_peak = max(self.equity_peak, self.equity)
        self.lowest_equity = min(self.lowest_equity, self.equity)
        dd = max(0.0, (self.equity_peak - self.equity) / self.equity_peak)
        self.max_drawdown = max(self.max_drawdown, dd)
        for position in self.positions.values():
            trade = self.trades[position.signal.signal_id]
            trade['max_equity_during_trade'] = max(trade['max_equity_during_trade'], self.equity)
        self.equity_curve.append(dict(timestamp=first.close_time, starting_balance=self.starting_balance,
            balance=self.balance, realized_pnl=self.realized_pnl, unrealized_pnl=self.unrealized_pnl,
            equity=self.equity, equity_peak=self.equity_peak, drawdown=dd,
            drawdown_absolute=self.equity_peak-self.equity, open_positions=len(self.positions),
            allocated_margin=self.allocated_margin, available_equity=self.available_equity,
            aggregate_stop_risk=self.aggregate_stop_risk, daily_realized_pnl=self.daily_realized_pnl,
            fees_paid=self.fees_paid, slippage_cost=self.slippage_cost, status=self.status,
            trade_entry_allowed=False))
        for signal in signals:
            if signal.status in ("INVALIDATED", "REJECTED_ENTRY_GEOMETRY", "SOURCE_CONTEXT_BLOCKED"):
                self.terminal_ids.add(signal.signal_id)
                self.pending.pop(signal.signal_id, None)
                action = "SETUP_INVALIDATED" if signal.status == "INVALIDATED" else "SETUP_REJECTED"
                self._log(first.close_time, signal, action,
                          '|'.join(signal.invalidation_reasons) or '|'.join(signal.reasons))
            elif signal.signal_id in self.terminal_ids or signal.signal_id in self.consumed_ids:
                self._log(first.close_time, signal, 'SETUP_IGNORED',
                          'TERMINAL_SETUP_ID' if signal.signal_id in self.terminal_ids else 'CONSUMED_SETUP_ID')
                continue
            elif signal.status == "READY_FOR_VIRTUAL_ENTRY":
                self.pending[signal.signal_id] = signal
                self._log(first.close_time, signal, "SETUP_READY", '|'.join(signal.reasons))
            else:
                # A formerly ready setup can lose its automatic POI evidence.
                # Withdraw it at this close before another next-open admission.
                self.pending.pop(signal.signal_id, None)
                reason = '|'.join((signal.status, *signal.level_blocking_reasons))
                self._log(first.close_time, signal, "SETUP_WAITING", reason)
        if duplicates:
            # Exact duplicates have one state transition and an explicit receipt.
            for signal in signals:
                self._log(first.close_time, signal, 'BATCH_DEDUPLICATED', f'{duplicates}_IDENTICAL_UPDATES_REMOVED')
        self._last_close = first.close_time
        self._bar_duration = duration
        return self.journal
