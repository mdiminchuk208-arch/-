"""Versioned, atomic JSON checkpoints for the offline virtual portfolio.

The digest detects incomplete writes and corruption, not malicious edits. No
pickle, import-by-name, credentials or exchange execution are used on restore.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
from math import isclose, isfinite
import os
from pathlib import Path
import tempfile

from crypto_bot.common.models import Direction
from crypto_bot.strategy.auto_levels import LevelEvidence
from crypto_bot.strategy.market_analysis import StructureAnalysisMode
from crypto_bot.strategy.replay import EngineMode, STRATEGY_VERSION, StrategySignal
from crypto_bot.strategy.trade_plan import PriceZone
from crypto_bot.strategy.virtual_portfolio import (
    Decision, SimulationPolicy, VirtualPortfolio, VirtualPosition,
)

SCHEMA_VERSION = 1
_RECORDS = {cls.__name__: cls for cls in (
    Decision, SimulationPolicy, VirtualPosition, StrategySignal, PriceZone, LevelEvidence,
)}
_ENUMS = {cls.__name__: cls for cls in (Direction, EngineMode, StructureAnalysisMode)}


def _encode(value):
    if isinstance(value, Enum):
        return {'$type': type(value).__name__, 'value': value.value}
    if isinstance(value, datetime):
        return {'$type': 'datetime', 'value': value.isoformat()}
    if isinstance(value, date):
        return {'$type': 'date', 'value': value.isoformat()}
    if isinstance(value, timedelta):
        return {'$type': 'timedelta', 'value': value.total_seconds()}
    if is_dataclass(value):
        return {'$type': type(value).__name__, 'fields': {
            f.name: _encode(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, (tuple, set)):
        return {'$type': type(value).__name__, 'items': [_encode(v) for v in
            (sorted(value) if isinstance(value, set) else value)]}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if isinstance(value, dict):
        if any(not isinstance(k, str) or k.startswith('$') for k in value):
            raise ValueError('checkpoint requires unambiguous string keys')
        return {k: _encode(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, (int, float)) and not isfinite(value):
            raise ValueError('nonfinite checkpoint value')
        return value
    raise ValueError(f'unsupported checkpoint type: {type(value).__name__}')


def _decode(value):
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if not isinstance(value, dict):
        if isinstance(value, (int, float)) and not isfinite(value):
            raise ValueError('nonfinite checkpoint value')
        return value
    kind = value.get('$type')
    if kind is None:
        return {k: _decode(v) for k, v in value.items()}
    if kind in _RECORDS:
        cls = _RECORDS[kind]
        data = value['fields']
        if set(data) != {f.name for f in fields(cls)}:
            raise ValueError('checkpoint record fields changed')
        for f in fields(cls):
            if not f.init and data[f.name] is not False:
                raise ValueError('real execution is forbidden')
        return cls(**{f.name: _decode(data[f.name]) for f in fields(cls) if f.init})
    if kind in _ENUMS:
        return _ENUMS[kind](value['value'])
    if kind == 'datetime':
        result = datetime.fromisoformat(value['value'])
        if result.utcoffset() is None:
            raise ValueError('checkpoint timestamps must have timezones')
        return result
    if kind == 'date':
        return date.fromisoformat(value['value'])
    if kind == 'timedelta':
        return timedelta(seconds=value['value'])
    if kind in ('tuple', 'set'):
        decoded = [_decode(v) for v in value['items']]
        return tuple(decoded) if kind == 'tuple' else set(decoded)
    raise ValueError('unknown checkpoint record type')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def snapshot(portfolio: VirtualPortfolio):
    state = _encode(vars(portfolio))
    state['mode'] = portfolio.mode.value
    return state


def save_checkpoint(portfolio: VirtualPortfolio, path: str | Path):
    envelope = dict(schema_version=SCHEMA_VERSION, strategy_version=STRATEGY_VERSION,
                    trade_entry_allowed=False, state=snapshot(portfolio))
    envelope['sha256'] = sha256(_canonical(envelope).encode()).hexdigest()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # An interruption leaves the previous complete checkpoint available.
    handle, temporary = tempfile.mkstemp(prefix=f'.{target.name}.', dir=target.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(_canonical(envelope) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_checkpoint(path: str | Path) -> VirtualPortfolio:
    try:
        envelope = json.loads(Path(path).read_text(encoding='utf-8'))
        digest = envelope.pop('sha256')
        if (envelope['schema_version'] != SCHEMA_VERSION or
                envelope['strategy_version'] != STRATEGY_VERSION or
                envelope['trade_entry_allowed'] is not False or
                digest != sha256(_canonical(envelope).encode()).hexdigest()):
            raise ValueError('checkpoint version, execution guard or digest mismatch')
        state = _decode(envelope['state'])
        state['mode'] = EngineMode(state['mode'])
        portfolio = VirtualPortfolio(equity=state['starting_balance'],
                                     mode=state['mode'], policy=state['policy'])
        if set(state) != set(vars(portfolio)):
            raise ValueError('checkpoint portfolio fields changed')
        portfolio.__dict__.update(state)
        _validate_state(portfolio)
        return portfolio
    except (KeyError, TypeError, AttributeError, OverflowError, ValueError) as exc:
        raise ValueError(f'invalid virtual portfolio checkpoint: {exc}') from exc


def _validate_state(p: VirtualPortfolio):
    if not isinstance(p.policy, SimulationPolicy) or p.trade_entry_allowed:
        raise ValueError('invalid virtual policy')
    if p.fees_paid < 0 or p.slippage_cost < 0 or p.equity_peak <= 0:
        raise ValueError('invalid accounting state')
    if p._last_close is None:
        if p.equity_curve or p._journal or p.positions or p.pending:
            raise ValueError('state requires an execution clock')
    elif (p._bar_duration is None or p._bar_duration.total_seconds() <= 0 or
          p._bar_duration.total_seconds() % 60 or
          not p.equity_curve or p.equity_curve[-1]['timestamp'] != p._last_close):
        raise ValueError('invalid checkpoint clock')
    for key, signal in p.pending.items():
        if p._last_close is None:
            raise ValueError('pending signal requires an execution clock')
        if (key != signal.signal_id or signal.mode != p.mode or
                signal.status != 'READY_FOR_VIRTUAL_ENTRY' or
                key in p.consumed_ids or key in p.terminal_ids or
                signal.event_time > p._last_close):
            raise ValueError('invalid pending signal state')
    for symbol, position in p.positions.items():
        if p._last_close is None:
            raise ValueError('open position requires an execution clock')
        signal = position.signal
        trade = p.trades[signal.signal_id]
        if (symbol != signal.symbol or signal.mode != p.mode or
                signal.signal_id not in p.consumed_ids or trade['status'] != 'OPEN' or
                not 0 < position.remaining_fraction <= 1 or position.quantity <= 0 or
                not 0 <= position.tp_stage <= 2 or position.entry_price <= 0 or
                position.stop_loss <= 0 or p.marks[symbol] <= 0 or
                position.entry_time > p._last_close):
            raise ValueError('invalid open position state')
    open_ids = {v.signal.signal_id for v in p.positions.values()}
    if open_ids != {key for key, trade in p.trades.items() if trade['status'] == 'OPEN'}:
        raise ValueError('open trade/position mismatch')
    if any(d.sequence != i + 1 or d.trade_entry_allowed for i, d in enumerate(p._journal)):
        raise ValueError('invalid decision journal')
    expected = sum(v.quantity * v.remaining_fraction *
                   (p.marks[symbol] - v.entry_price) *
                   (1 if v.signal.direction == Direction.LONG else -1)
                   for symbol, v in p.positions.items())
    if not isclose(expected, p.unrealized_pnl, rel_tol=1e-12, abs_tol=1e-9):
        raise ValueError('unrealized accounting mismatch')
