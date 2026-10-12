"""Integrity-only audit of four frozen local native M15 sources."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path('/workspace/-')
START = 1760313600
END = 1791849600
STEP = 900
# Captured retrieval-clock snapshot. Replay this snapshot without moving the gap window.
NOW = int(datetime.fromisoformat('2026-10-12T18:10:50+00:00').timestamp())
CLOSED_END = min(END, NOW // STEP * STEP)


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace('+00:00', 'Z')


def file_audit(path, symbol):
    raw = path.read_bytes()
    handle = gzip.open(path, 'rt', newline='') if path.suffix == '.gz' else path.open('rt', newline='')
    times = []
    invalid_rows = []
    values = {}
    identity = Counter()
    with handle as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        for line, row in enumerate(reader, 2):
            identity[(row.get('exchange'), row.get('symbol'), row.get('interval'), row.get('is_closed'))] += 1
            try:
                milliseconds = int(row['open_time_ms'])
                if milliseconds % (STEP * 1000):
                    raise ValueError('off M15 grid')
                ts = milliseconds // 1000
                o, h, l, c, v, turnover = (Decimal(row[k]) for k in ('open', 'high', 'low', 'close', 'volume_base', 'turnover_quote'))
                if not all(x.is_finite() for x in (o,h,l,c,v,turnover)) or min(o,h,l,c) <= 0 or v < 0 or turnover < 0 or h < max(o,l,c) or l > min(o,h,c):
                    raise ValueError('invalid OHLCV')
                times.append(ts)
                if START <= ts < END:
                    values[ts] = tuple((o,h,l,c,v,turnover))
            except (ValueError, KeyError, InvalidOperation) as error:
                invalid_rows.append({'line':line,'reason':str(error)})
    counts = Counter(times)
    unique = set(times)
    interval = {t for t in unique if START <= t < CLOSED_END}
    missing = sorted(set(range(START,CLOSED_END,STEP)) - interval)
    runs = []
    for ts in missing:
        if runs and runs[-1][1] == ts:
            runs[-1][1] = ts + STEP
            runs[-1][2] += 1
        else:
            runs.append([ts,ts+STEP,1])
    return ({
        'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes':len(raw),
        'columns':columns, 'rows':len(times), 'first_open':iso(min(times)) if times else None,
        'last_open':iso(max(times)) if times else None,
        'identity_counts': [{'exchange':k[0],'symbol':k[1],'interval':k[2],'is_closed':k[3],'count':v} for k,v in sorted(identity.items())],
        'invalid_rows':invalid_rows[:10], 'invalid_row_count':len(invalid_rows),
        'duplicate_timestamp_count':sum(c-1 for c in counts.values() if c>1),
        'closed_window_present_count':len(interval), 'closed_window_missing_count':len(missing),
        'closed_window_missing_runs':[{'start':iso(a),'end_exclusive':iso(b),'bars':n} for a,b,n in runs],
        'future_window_row_count':sum(1 for t in unique if CLOSED_END <= t < END),
        'source_order_strict_ascending':all(a < b for a,b in zip(times,times[1:])),
    }, values)


out = {'audit_time_utc':iso(NOW), 'warmup_start':iso(START), 'illustrative_end_exclusive':iso(END),
       'closed_window_end_exclusive':iso(CLOSED_END), 'closed_expected_bars':(CLOSED_END-START)//STEP,
       'unfinished_remaining_bars':(END-CLOSED_END)//STEP, 'sources':{}, 'overlap':{}}
for symbol in ('BTCUSDT','ETHUSDT'):
    mirror = ROOT / f'data/history/public_research/bybit_mirror/{symbol}/15.csv.gz'
    native = ROOT / f'data/history/bybit/{symbol}/15.csv'
    a, av = file_audit(mirror, symbol)
    b, bv = file_audit(native, symbol)
    shared = sorted(set(av)&set(bv))
    conflicts = []
    for ts in shared:
        if av[ts] != bv[ts]:
            conflicts.append({'open':iso(ts),'public':[str(x) for x in av[ts]],'native':[str(x) for x in bv[ts]]})
    out['sources'][symbol] = {'public':a,'native':b}
    out['overlap'][symbol] = {'shared_open_count':len(shared),'exact_decimal_ohlcv_conflict_count':len(conflicts),
                              'conflicts':conflicts[:10], 'comparison_scope':'open,high,low,close,volume_base,turnover_quote'}
    # Combined continuity checks count only actual native/public M15 observations.
    public_times = set(av)
    native_times = set(bv)
    available = (public_times | native_times) & set(range(START,CLOSED_END,STEP))
    missing = sorted(set(range(START,CLOSED_END,STEP)) - available)
    runs = []
    for ts in missing:
        if runs and runs[-1][1] == ts:
            runs[-1][1] = ts + STEP
            runs[-1][2] += 1
        else:
            runs.append([ts,ts+STEP,1])
    out['sources'][symbol]['combined_closed'] = {'present_bars':len(available), 'missing_bars':len(missing),
        'missing_runs':[{'start':iso(a),'end_exclusive':iso(b),'bars':n} for a,b,n in runs]}

print(json.dumps(out, indent=2))
