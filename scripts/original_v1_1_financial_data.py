"""Read immutable baseline-C Bybit prices only; no admission/outcome imports."""
from __future__ import annotations

import csv
import gzip
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/reports/original_v1_1_first_financial_backtest_2026_10_11'
PRE = OUT / 'preregistration'
START = 1672531200  # 2023-01-01 UTC, same baseline C.
WARMUP = 1640995200  # 2022-01-01 UTC.
END = 1764977400  # 2025-12-05 23:30 UTC; asserted against archived dataset audit.
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
TFS = (15, 60, 240, 1440)
BASE = ROOT / 'data/reports/medium_term_2026_10_10/role_corrected_v2/bybit_2023_2025'
STRATEGY_COMMIT = '43e9d7addcd427650ff856dd1fa99f78ee5c06f7'
STRATEGY_MANIFEST = ROOT / 'docs/original_strategy_spec_v1_1/freeze_manifest.json'
STRATEGY_SHA = 'dca962ff1f829887d0787a6329112e77f4ce714023bee85f666ed37843f2ecbb'


def stamp(value):
    return int(datetime.fromisoformat(value).timestamp())


def iso(value):
    return datetime.fromtimestamp(value, UTC).isoformat()


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as stream:
        for row in rows:
            stream.write((compact(row) + '\n').encode())


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: compact(row[k]) if isinstance(row.get(k), (list, dict)) else row.get(k) for k in fields})


@dataclass(frozen=True)
class Bar:
    start: int
    end: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def observed(self, tf):
        return {'open': str(self.open), 'high': str(self.high), 'low': str(self.low), 'close': str(self.close),
                'open_time': self.start, 'completed_at': self.end, 'known_at': self.end, 'tf': tf,
                'evidence': 'Verified public Bybit completed OHLC; no qualitative SOURCE validation implied'}


def validate_bars(bars, tf):
    if not bars:
        raise ValueError('Empty baseline series')
    previous = None
    for b in bars:
        if (b.end - b.start != tf * 60 or b.start % (tf * 60)
                or previous is not None and b.start != previous.end
                or not all(v.is_finite() for v in (b.open, b.high, b.low, b.close))
                or not 0 < b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high):
            raise ValueError('Invalid/discontinuous/unclosed public bars')
        previous = b


def load_native(symbol, tf):
    path = ROOT / f'data/history/public_research/bybit_mirror/{symbol}/{tf}.csv.gz'
    bars = []
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for r in csv.DictReader(stream):
            start = int(r['open_time_ms']) // 1000
            end = start + tf * 60
            if start < WARMUP or end > END:
                continue
            if r['exchange'] != 'BYBIT' or r['symbol'] != symbol or int(r['interval']) != tf or r['is_closed'] != '1':
                raise ValueError('Wrong/unclosed dataset record')
            bars.append(Bar(start, end, *(Decimal(r[k]) for k in ('open', 'high', 'low', 'close'))))
    validate_bars(bars, tf)
    return bars, path


def daily(m15):
    result = []
    for i in range(0, len(m15), 96):
        group = m15[i:i + 96]
        if len(group) == 96 and group[0].start % 86400 == 0 and group[-1].end - group[0].start == 86400:
            result.append(Bar(group[0].start, group[-1].end, group[0].open,
                              max(b.high for b in group), min(b.low for b in group), group[-1].close))
    validate_bars(result, 1440)
    return result


def load_market():
    """Match every native hash and D1 content to the baseline-C dataset audits."""
    assert iso(END) == '2025-12-05T23:30:00+00:00'
    data, records = {}, []
    for symbol in SYMBOLS:
        audit = json.loads((BASE / 'detection' / symbol / 'dataset_audit.json').read_text())
        data[symbol] = {}
        for tf in (15, 60, 240):
            bars, path = load_native(symbol, tf)
            expected = next(r for r in audit if r['tf'] == tf)
            assert checksum(path) == expected['sha256'] and len(bars) == expected['candles']
            assert iso(bars[0].start) == expected['start'] and iso(bars[-1].end) == expected['end']
            data[symbol][tf] = bars
            records.append({'symbol': symbol, 'tf': tf, 'path': str(path.relative_to(ROOT)),
                'sha256': checksum(path), 'warmup_bars': len(bars),
                'trading_bars': sum(b.start >= START for b in bars), 'gaps': 0,
                'warmup_start': iso(bars[0].start), 'available_end': iso(bars[-1].end)})
        bars = daily(data[symbol][15])
        p = ROOT / f'data/reports/medium_term_2026_10_10/compiled_primary/bybit_2023_2025/detection/{symbol}/derived_D1.jsonl.gz'
        original = read_rows(p)
        assert len(original) == len(bars)
        for b, row in zip(bars, original, strict=True):
            assert row['is_closed'] and b.start == stamp(row['open_time']) and b.end == stamp(row['close_time'])
            assert all(getattr(b, k) == Decimal(str(row[k])) for k in ('open', 'high', 'low', 'close'))
        canonical = [{**{k: float(getattr(b, k)) for k in ('open', 'high', 'low', 'close')},
                      'open_time': iso(b.start), 'close_time': iso(b.end), 'is_closed': True} for b in bars]
        content_hash = sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        expected = next(r for r in audit if r['tf'] == 1440)
        assert content_hash == expected['candle_content_sha256']
        data[symbol][1440] = bars
        records.append({'symbol': symbol, 'tf': 1440, 'path': str(p.relative_to(ROOT)), 'sha256': checksum(p),
            'derived_from_tf': 15, 'candle_content_sha256': content_hash, 'warmup_bars': len(bars),
            'trading_bars': sum(b.start >= START for b in bars), 'gaps': 0,
            'warmup_start': iso(bars[0].start), 'available_end': iso(bars[-1].end), 'excluded_partial_days': 1})
    return data, {'exchange': 'BYBIT', 'symbols': list(SYMBOLS), 'timeframes': list(TFS),
        'exact_trading_interval': [iso(START), iso(END)], 'warmup_start': iso(WARMUP),
        'bars_in_trading_interval': sum(r['trading_bars'] for r in records),
        'series': records, 'baseline_C_native_hash_and_D1_content_equality': 'PASS',
        'interval_convention': 'native OPEN >= start and native CLOSE <= end; warmup never creates scored trades'}
