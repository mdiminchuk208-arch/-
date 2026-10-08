"""Read-only, exhaustive first-rejection and original OB/POI window audit.

Consumes retained pre-fix evaluations; never changes signals or qualifies trades.
The baseline journal defines the execution scope, including its warmup collapse.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv


STAGES = ('SETUP', 'STRUCTURE', 'BOS', 'ENTRY GEOMETRY', 'OB candidate', 'valid OB', 'HTF POI',
          'preexisting POI', 'fresh POI', 'supporting POI', 'SL', 'targets',
          'R:R', 'Score', 'READY', 'virtual entry')
VALID_GATES = ('AGGRESSION', 'IMBALANCE', 'OB_OTE_AND_IMPULSE', 'RAW_SWEEP')


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=Path('data/reports/historical_portfolio'))
    parser.add_argument('--evaluations', type=Path,
                        default=Path('data/reports/ready_root_cause/verified_audit'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, default=Path('data/history/bybit'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads((args.evaluations / 'baseline_summary.json').read_text())
    # Retained audit observed_signals is byte-equivalent to the frozen baseline.
    signals = []
    for symbol in summary['symbols']:
        signals.extend(json.loads(line) for line in
                       (args.evaluations / symbol / 'observed_signals.jsonl').read_text().splitlines())
    by_id = defaultdict(list)
    for signal in signals:
        by_id[signal['signal_id']].append(signal)
    eligible = {key for key, rows in by_id.items()
                if any(row['status'] == 'WAITING_FOR_AUTO_LEVELS' for row in rows)}
    no_pattern = {key for key, rows in by_id.items()
                  if any('NO_POST_BOS_OB_PATTERN' in row['level_blocking_reasons'] for row in rows)}
    no_pattern_breakdown = Counter()
    best = {}
    poi_ids = set()
    ranks = Counter()
    reasons = Counter()
    start = datetime.fromisoformat(summary['warmup_start'])
    end = datetime.fromisoformat(summary['execution_end'])
    with (args.output / 'original_ob_no_pattern.jsonl').open('w') as ob_stream, \
            (args.output / 'original_nine_poi.jsonl').open('w') as poi_stream:
        for symbol in summary['symbols']:
            tf = summary['ltf_minutes']
            candles = [c for row in read_klines_csv(args.data_root / symbol / f'{tf}.csv')
                       if start <= (c := row.to_strategy_candle(tf * 60000)).open_time
                       and c.close_time <= end]
            written = set()
            with (args.evaluations / symbol / 'evaluations.jsonl').open() as evaluations:
                for line in evaluations:
                    row = json.loads(line)
                    key = row['signal_id']
                    if key not in eligible or row['next_state'] != 'WAITING_FOR_AUTO_LEVELS':
                        continue
                    diag = row['automatic_diagnostic']
                    if not diag:
                        continue
                    if key in no_pattern and key not in written:
                        written.add(key)
                        opp = row['opportunity']
                        triples = []
                        begin = diag['candidate_scan_start']
                        finish = diag['candidate_scan_end_exclusive']
                        long = row['direction'] == 'LONG'
                        for index in range(begin, finish):
                            a, b, c = candles[index - 1:index + 2]
                            colors = (a.close < a.open and b.close > b.open) if long else \
                                     (a.close > a.open and b.close < b.open)
                            engulf = (min(b.open, b.close) <= min(a.open, a.close)
                                      and max(b.open, b.close) >= max(a.open, a.close)
                                      and abs(b.close - b.open) > abs(a.close - a.open))
                            triples.append(dict(a_index=index-1, b_index=index, c_index=index+1,
                                                a_open=a.open_time.isoformat(),
                                                ohlc=[[d.open, d.high, d.low, d.close] for d in (a, b, c)],
                                                opposite_colors=colors, body_engulf=engulf,
                                                rejection='OPPOSITE_COLORS' if not colors else 'BODY_ENGULF'))
                        cause = ('EMPTY_POST_BOS_PRE_ANCHOR_WINDOW' if not triples else
                                 'NO_OPPOSITE_COLORS' if not any(t['opposite_colors'] for t in triples)
                                 else 'NO_FULL_BODY_ENGULF')
                        no_pattern_breakdown[cause] += 1
                        record = dict(signal_id=key, symbol=symbol, direction=row['direction'],
                                      setup_timestamp=row['signal']['sfp_time'],
                                      evaluated_at=row['timestamp'], bos_timestamp=opp['ltf_bos_event_time'],
                                      bos_index=opp['ltf_bos_candle_index'], bos_kind=opp['ltf_bos_kind'],
                                      protected_level_id=opp['ltf_bos_level_id'],
                                      protected_price=opp['ltf_bos_level_price'],
                                      impulse_start=opp['impulse_start_price'], impulse_end=opp['impulse_end_price'],
                                      anchor_time=diag['anchor_swing_time'], scan_start=begin,
                                      scan_end_exclusive=finish, candidates_found=len(diag['candidates']),
                                      first_rejection=cause, considered_triples=triples,
                                      htf_minutes=summary['htf_minutes'], ltf_minutes=tf)
                        ob_stream.write(json.dumps(record, sort_keys=True)+'\n')
                    candidate_best = (4, -1, 'NO_OB_CANDIDATE', None)
                    for candidate in diag['candidates']:
                        rank, depth, cause = 5, 0, candidate['first_failure']
                        for gate in VALID_GATES:
                            if not candidate['gates'][gate]:
                                break
                            depth += 1
                        else:
                            rank = 6
                            pre = candidate['preexisting_supporting_poi_evidence']
                            late = candidate['later_supporting_poi_evidence']
                            if pre or late:
                                rank = 7
                            if pre:
                                rank = 8
                            if candidate['gates']['SUPPORTING_POI']:
                                rank = 10
                                if candidate['gates']['OB_FRESH'] and candidate['gates']['STOP_GEOMETRY']:
                                    rank = 11
                                    if diag['independent_targets_available']:
                                        rank = 12
                            if key not in poi_ids:
                                poi_ids.add(key)
                                poi_stream.write(json.dumps(dict(signal_id=key, symbol=symbol,
                                    direction=row['direction'], setup_timestamp=row['signal']['sfp_time'],
                                    bos_timestamp=row['opportunity']['ltf_bos_event_time'],
                                    htf_minutes=summary['htf_minutes'], ltf_minutes=tf,
                                    evaluated_at=row['timestamp'], candidate=candidate), sort_keys=True)+'\n')
                        if (rank, depth) > candidate_best[:2]:
                            candidate_best = (rank, depth, cause, candidate['a_open'])
                    if key not in best or candidate_best[:2] > best[key][:2]:
                        best[key] = candidate_best
            print(symbol, 'OB no-pattern audited:', len(written), flush=True)
    outcomes = []
    for key, rows in sorted(by_id.items()):
        row = max(rows, key=lambda r:r['event_time'])
        if key in best:
            rank, _, cause, a_open = best[key]
        else:
            rank, cause, a_open = 3, 'GEOMETRY_NOT_RESOLVED_BEFORE_CONTEXT_END', None
        ranks[rank] += 1
        reasons[cause] += 1
        outcomes.append(dict(signal_id=key, symbol=row['symbol'], direction=row['direction'],
                             passed_stages=list(STAGES[:rank]), first_reject_stage=STAGES[rank],
                             first_rejection=cause, candidate_a_open=a_open,
                             final_signal_status=row['status']))
    count = len(by_id)
    funnel = []
    for index, stage in enumerate(STAGES):
        entered = sum(n for rank,n in ranks.items() if rank >= index)
        passed = sum(n for rank,n in ranks.items() if rank > index)
        funnel.append(dict(stage=stage, input=entered, passed=passed, reject=entered-passed,
                           pass_rate=passed/entered if entered else None))
    assert sum(item['reject'] for item in funnel) == count
    assert sum(no_pattern_breakdown.values()) == len(no_pattern)
    write(args.output / 'funnel.json', funnel)
    write(args.output / 'setup_first_rejections.json', outcomes)
    write(args.output / 'summary.json', dict(setups=count, execution_auto_eligible=len(eligible),
          no_post_bos_ob_pattern=len(no_pattern), no_pattern_breakdown=dict(no_pattern_breakdown),
          reached_supporting_poi_audits=len(poi_ids), rejection_counts=dict(reasons),
          policy='ONE_FIRST_REJECTION_PER_SETUP_BEST_SINGLE_CANDIDATE_EVER_WHILE_ALIVE',
          scope='FROZEN_EXECUTION_JOURNAL_DIAGNOSTICS_MAY_HAVE_BEEN_CACHED_IN_WARMUP',
          score_gate='NO_NEW_SCORE_THRESHOLD_RR_AND_SCORE_UNREACHED_IN_BASELINE'))


if __name__ == '__main__':
    main()
