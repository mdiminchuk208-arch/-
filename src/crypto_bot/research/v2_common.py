"""Deterministic offline V2 artifacts and independent case metrics."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

BASELINE = 'dab8d254aaf4babc07659e3d03d14b269445767b'
BASE = Path('data/reports/source_permitted_physical_bybit_2026_10_10')
OUT = Path('data/reports/strategy_v2_2026_10_10')
Row = dict[str, Any]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def read_jsonl(path: Path) -> Iterator[Row]:
    with gzip.open(path, 'rt') as f:
        for line in f:
            yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as z:
        for row in rows:
            z.write((canonical(row) + '\n').encode())


def write_csv(path: Path, rows: list[Row]) -> None:
    fields = list(dict.fromkeys(k for r in rows for k in r))
    path.parent.mkdir(parents=True, exist_ok=True)
    def output(handle: Any) -> None:
        w = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for row in rows:
            w.writerow({k: canonical(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    if path.suffix == '.gz':
        with (path.open('wb') as raw,
              gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as z,
              io.TextIOWrapper(z, encoding='utf-8', newline='') as f):
            output(f)
    else:
        with path.open('w', newline='') as plain:
            output(plain)


def wilson(wins: int, n: int) -> list[float | None]:
    if not n:
        return [None, None]
    z = 1.959963984540054
    p = wins / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - half, center + half]


def metrics(rows: list[Row], months: float | None = None, cost_multiplier: float = 1.0) -> Row:
    values = [r['net_pnl'] - (cost_multiplier - 1) * (r['fees'] + r['slippage']) for r in rows]
    wins = [v for v in values if v > 0]
    losses = [-v for v in values if v < 0]
    n = len(values)
    win_sum, loss_sum = math.fsum(wins), math.fsum(losses)
    avg_win = win_sum / len(wins) if wins else None
    avg_loss = loss_sum / len(losses) if losses else None
    cumulative = peak = dd = 0.0
    ordered = sorted(zip(rows, values), key=lambda p: (p[0]['exit_time'], p[0]['physical_opportunity_id']))
    for _, value in ordered:
        cumulative += value
        peak = max(peak, cumulative)
        dd = max(dd, peak - cumulative)
    ci = wilson(len(wins), n)
    return {'CLOSED': n, 'WIN': len(wins), 'LOSS': len(losses), 'BE': n-len(wins)-len(losses),
            'WR': len(wins)/n if n else None, 'WR_CI_low': ci[0], 'WR_CI_high': ci[1],
            'PF': win_sum/loss_sum if loss_sum else None,
            'Expectancy': math.fsum(values)/n if n else None,
            'AvgR': math.fsum(v/r['risk_amount'] for r, v in zip(rows, values))/n if n else None,
            'NetPnL': math.fsum(values), 'GrossPnL': math.fsum(r['quote_gross_pnl'] for r in rows),
            'fees': math.fsum(r['fees'] for r in rows)*cost_multiplier,
            'slippage': math.fsum(r['slippage'] for r in rows)*cost_multiplier,
            'MaxDrawdown_case_sum': dd, 'AvgWin': avg_win, 'AvgLoss': avg_loss,
            'Payoff': avg_win/avg_loss if avg_win is not None and avg_loss else None,
            'Average_holding_seconds': math.fsum(r['holding_seconds'] for r in rows)/n if n else None,
            'trades_per_month': n/months if months else None, 'cost_multiplier': cost_multiplier}


def numerical_gate(m: Row) -> bool:
    return (m['CLOSED'] >= 200 and (m['WR'] or 0) >= .70 and (m['PF'] or 0) >= 1.5
            and (m['Expectancy'] or 0) > 0 and (m['AvgR'] or 0) > 0 and m['NetPnL'] > 0)


def seconds(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()
