"""Validate public mirror candles and retain complete UTC aggregates/provenance.

Never interpolate gaps or disaggregate a higher timeframe into synthetic prices.
Compressed CSV is deterministic; canonical data/strategy source stays unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path

from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import CSV_FIELDS


def aggregate(candles, source_minutes, target_minutes):
    if target_minutes < source_minutes or target_minutes % source_minutes:
        raise ValueError('Cannot invent smaller-timeframe candles')
    step = source_minutes * 60000
    duration = target_minutes * 60000
    expected = target_minutes // source_minutes
    groups = {}
    previous = None
    for candle in candles:
        if candle.open_time_ms % step or previous is not None and candle.open_time_ms <= previous:
            raise ValueError('Nonaligned, duplicated or unordered source candle')
        previous = candle.open_time_ms
        groups.setdefault(candle.open_time_ms // duration * duration, []).append(candle)
    output = []
    rejected = []
    for start, rows in groups.items():
        if [c.open_time_ms for c in rows] != [start + i * step for i in range(expected)]:
            rejected.append(dict(open_time_ms=start, source_rows=len(rows), expected=expected))
            continue
        first, last = rows[0], rows[-1]
        output.append(MarketCandle(first.exchange, first.symbol, str(target_minutes), start,
            first.open, max(c.high for c in rows), min(c.low for c in rows), last.close,
            sum(c.volume_base for c in rows) if all(c.volume_base is not None for c in rows) else None,
            sum(c.turnover_quote for c in rows) if all(c.turnover_quote is not None for c in rows) else None,
            True))
    return output, rejected


def write_compressed(candles, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    logical_hash = sha256()
    with path.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as zipped:
        handle = io.TextIOWrapper(zipped, encoding='utf-8', newline='')
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for candle in candles:
            row = asdict(candle)
            row['is_closed'] = '1'
            writer.writerow(row)
        handle.flush()
    with gzip.open(path, 'rb') as reader:
        while block := reader.read(1024 * 1024):
            logical_hash.update(block)
    step = int(candles[0].interval) * 60000
    gaps = Counter(b.open_time_ms - a.open_time_ms for a, b in zip(candles, candles[1:])
                   if b.open_time_ms - a.open_time_ms != step)
    return dict(path=str(path), symbol=candles[0].symbol, exchange=candles[0].exchange,
        timeframe_minutes=int(candles[0].interval), candles=len(candles),
        start=datetime.fromtimestamp(candles[0].open_time_ms / 1000, timezone.utc).isoformat(),
        end_exclusive=datetime.fromtimestamp((candles[-1].open_time_ms + step) / 1000, timezone.utc).isoformat(),
        stored_bytes=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest(),
        csv_sha256=logical_hash.hexdigest(), gaps=dict(gaps), gap_interpolation=False)


def bybit(root):
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        path = root / f'bybit_{symbol[:3].lower()}_15'
        with path.open() as handle:
            candles = [MarketCandle('BYBIT', symbol, '15', int(row['timestamp']),
                *[float(row[k]) for k in ('open', 'high', 'low', 'close', 'volume', 'turnover')])
                for row in csv.DictReader(handle)]
        yield symbol, candles, dict(exchange='BYBIT', instrument='USDT_LINEAR_PERPETUAL',
            repository='mestoness/btc-eth-candles-history',
            commit='9ca04178df06ce649f00779a49e11094fe5b1c70',
            source_url='https://github.com/mestoness/btc-eth-candles-history/blob/9ca04178df06ce649f00779a49e11094fe5b1c70/' + symbol + '_15.csv',
            source_sha256=sha256(path.read_bytes()).hexdigest())


def binance(root, manifest):
    import pyarrow.parquet as pq  # type: ignore[import-untyped]  # Optional library has no typing marker.
    by_symbol = {}
    for record in manifest['files']:
        symbol = record['path'].split('/symbol_id=')[1].split('/')[0]
        by_symbol.setdefault(symbol, []).append(record)
    for symbol, records in sorted(by_symbol.items()):
        candles = []
        excluded = []
        for record in sorted(records, key=lambda x: x['path']):
            path = root / record['path']
            assert sha256(path.read_bytes()).hexdigest() == record['sha256']
            table = pq.ParquetFile(path).read().to_pydict()
            for i, when in enumerate(table['timestamp']):
                if table['symbol'][i] != symbol or table['interval'][i] != '5m':
                    raise ValueError('Source partition identity mismatch')
                timestamp = int(when.timestamp() * 1000)
                if when.utcoffset().total_seconds() != 0 or when.second or when.microsecond or timestamp % 300000:
                    raise ValueError('Source is not aligned UTC five-minute data')
                if table['source_rows'][i] != 5:
                    excluded.append(dict(open_time_ms=timestamp, source_rows=table['source_rows'][i], expected=5))
                    continue
                candles.append(MarketCandle('BINANCE', symbol, '5', timestamp,
                    *[float(table[k][i]) for k in ('open', 'high', 'low', 'close', 'volume')]))
        yield symbol, candles, dict(exchange='BINANCE', instrument='UNVERIFIED_BINANCE_MARKET_TYPE',
            repository=manifest['repository'], commit=manifest['commit'],
            source_files=records, incomplete_source_bars_excluded=excluded,
            market_type_not_asserted_without_upstream_endpoint_evidence=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['bybit', 'binance'], required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    source = bybit(args.source_root) if args.kind == 'bybit' else binance(
        args.source_root, json.loads(args.source_manifest.read_text()))
    result = []
    for symbol, candles, provenance in source:
        source_minutes = int(candles[0].interval)
        for target in (5, 15, 60, 240):
            if target < source_minutes:
                continue
            output, rejected = aggregate(candles, source_minutes, target)
            metadata = write_compressed(output, args.output_root / symbol / f'{target}.csv.gz')
            metadata.update(provenance=provenance, incomplete_aggregate_bars_excluded=rejected)
            result.append(metadata)
            print(symbol, target, len(output), 'complete real bars;', len(rejected), 'incomplete bins', flush=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(dict(kind=args.kind, series=result, synthetic_data=False,
        trade_entry_allowed=False), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
