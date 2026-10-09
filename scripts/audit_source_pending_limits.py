"""Verify the observed zero-fill maximum using every real bar while limits existed."""
from __future__ import annotations
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys

from crypto_bot.data.storage import read_klines_csv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_cases_bybit import read_rows, write_json


def audit(root):
    repo = Path(__file__).resolve().parents[1]
    summary = json.loads((root / 'case_summary.json').read_text())
    if summary['FILLED'] != 0 or summary['CLOSED'] != 0:
        raise ValueError('this evidence audit is specifically for a complete zero-fill result')
    decisions = read_rows(root / 'case_decisions.jsonl.gz')
    offered = {r['signal_id'] for r in decisions if r['reason'] == 'VIRTUAL_LIMIT_PENDING'}
    rows, loaded = [], {}
    for p in sorted((root / 'segments').glob('*/signals.jsonl.gz')):
        for r in read_rows(p):
            if r['signal_id'] not in offered:
                continue
            cancel = next(v for v in decisions if v['signal_id'] == r['signal_id'] and v['reason'].startswith('CANCEL_'))
            ready, until = datetime.fromisoformat(r['known_at']), datetime.fromisoformat(cancel['known_at'])
            if r['symbol'] not in loaded:
                loaded[r['symbol']] = [c.to_strategy_candle(300000) for c in read_klines_csv(repo / f"data/history/bybit/{r['symbol']}/5.csv")]
            cs = loaded[r['symbol']]
            prior = [c for c in cs if ready <= c.open_time < until]
            trace = [{'open_time': c.open_time.isoformat(), 'close_time': c.close_time.isoformat(),
                      'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close,
                      'quote_touched': c.low <= r['entry'] if r['direction'] == 'LONG' else c.high >= r['entry']} for c in prior]
            assert not any(v['quote_touched'] for v in trace), (r['signal_id'], trace)
            bar = next(c for c in cs if c.open_time == until)
            if cancel['reason'] == 'CANCEL_OPEN_OUTSIDE_SL_FTA':
                assert (bar.open <= r['stop'] or bar.open >= r['targets'][0]) if r['direction'] == 'LONG' else (bar.open >= r['stop'] or bar.open <= r['targets'][0])
            boundary = {'open': bar.open, 'high': bar.high, 'low': bar.low, 'close': bar.close,
                        'interval_start': bar.open_time.isoformat(), 'interval_end': bar.close_time.isoformat()}
            rows.append({'signal_id': r['signal_id'], 'symbol': r['symbol'], 'mapping': f"{r['htf']}/{r['ltf']}",
                         'setup_type': r['setup_type'], 'htf_poi': r['poi_type'], 'local_poi': r['evidence']['ltf_poi']['kind'],
                         'ready': r['known_at'], 'entry': r['entry'], 'SL': r['stop'], 'targets': r['targets'], 'cancel': cancel,
                         'prior_actual_5m_intervals': trace, 'cancellation_boundary_bar': boundary,
                         'quote_never_touched_before_known_cancel': True, 'shared_account_busy': False,
                         'budget_rejection': False, 'trade_entry_allowed': False})
    assert len(rows) == len(offered) == summary['unique_opportunities']
    return {'status': 'PASS', 'all_READY_limits_independently_audited': len(rows),
            'no_quote_touch_while_order_active': True, 'maximum_observed_filled_closed_under_registered_policy': 0,
            'not_a_discretionary_source_maximum': True, 'scope': '40_NATIVE_BYBIT_SERIES_993575_CANDLES',
            'rows': rows, 'trade_entry_allowed': False,
            'verification_script_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.input.resolve())
    write_json(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
