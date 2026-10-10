"""Apply the new gate to old READY snapshots; duration is descriptive only."""
from __future__ import annotations

import heapq
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from crypto_bot.strategy.anti_scalp import check_anti_scalp
from crypto_bot.strategy.market_analysis import analyze_market
from crypto_bot.strategy.range_engine import RangeDetectionParams, analyze_ranges
from crypto_bot.strategy.source_medium_term import MediumTermEngine
from crypto_bot.strategy.source_permitted import SourceSeries

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_medium_term_research import (
    REPO,
    ROOT,
    load_data,
    read_rows,
    write_json,
    write_rows,
)


def main():
    policy = json.loads((REPO / 'config/source_medium_term_policy.json').read_text())
    old = REPO / 'data/reports/source_permitted_physical_bybit_2026_10_10'
    selected_ids = {r['signal_id'] for r in read_rows(old / 'selections/SOURCE_PERMITTED_UNION.jsonl.gz')}
    signals = {r['signal_id']: r for symbol in policy['symbol_priority']
               for r in read_rows(old / 'segments' / symbol / 'signals.jsonl.gz')
               if r['signal_id'] in selected_ids}
    cases = read_rows(old / 'cohorts/SOURCE_PERMITTED_UNION/CANCEL_SOURCE_POI_INVALIDATION/cases.jsonl.gz')
    decisions = []
    for symbol in policy['symbol_priority']:
        rows = sorted([r for r in cases if r['symbol'] == symbol], key=lambda r: (r['ready_time'], r['signal_id']))
        data, _ = load_data('native_bybit_2026', symbol, policy)
        owners = {}
        for tf in (240, 1440):
            report = analyze_market(data[tf], timeframe_minutes=tf)
            ranges = analyze_ranges(data[tf], report, params=RangeDetectionParams(
                midpoint_tolerance_fraction=policy['range_midpoint_tolerance']))
            owners[tf] = SourceSeries(symbol, tf, data[tf], report, ranges)
        e = MediumTermEngine(symbol, owners, policy)
        events = iter(heapq.merge(*[[(c.close_time, -tf, tf, i) for i, c in enumerate(data[tf])]
                                    for tf in (240, 1440)]))
        next_event = next(events, None)
        for case in rows:
            signal = signals[case['signal_id']]
            at = datetime.fromisoformat(signal['known_at'])
            while next_event is not None and next_event[0] <= at:
                _, _, tf, i = next_event
                owners[tf].advance(i)
                next_event = next(events, None)
            evidence = signal['evidence']
            parent, local = evidence['htf_poi'], evidence['ltf_poi']
            qtf = evidence['entry_zone_tf']
            valid = (signal['htf'] in (60, 240) and (parent['zone_id'] != local['zone_id'] or qtf >= 60)
                     and (parent['structural_proof'] is not None or parent['kind'] in ('SFP', 'RANGE_POI')))
            macro_tf, macro = e._macro_context(signal['htf'], signal['direction'], at,
                                                parent['kind'] in ('SFP', 'RANGE_POI'))
            # Only original READY quote/targets and causally replayed context.
            # Actual entry/fill, exit, holding, P&L and result are NOT gate inputs.
            d = check_anti_scalp(direction=signal['direction'], entry=signal['entry'],
                                 target=signal['targets'][0], setup_tf=signal['htf'], context_tf=macro_tf,
                                 main_setup_valid=valid, context_valid=macro is not None,
                                 target_known_before_entry=True)
            decisions.append(dict(signal_id=signal['signal_id'], symbol=symbol, known_at=at,
                                  main_setup_valid=valid, macro_context_tf=macro_tf,
                                  original_ready_quote=signal['entry'], original_structural_target=signal['targets'][0],
                                  **d.evidence()))
        print('OLD_PRE_ENTRY_OVERLAY', symbol, len(rows), flush=True)
    by_id = {r['signal_id']: r for r in decisions}
    closed = [r for r in cases if r['status'] == 'CLOSED']
    summary = {'gate_counts_all_filled': dict(Counter(r['reason'] for r in decisions)),
               'total_old_FILLED': len(cases), 'total_old_CLOSED': len(closed),
               'pre_entry_features_only': True, 'holding_used_only_after_decision': True,
               'uses_old_structural_target_not_new_retargeted_trades': True,
               'trade_entry_allowed': False}
    for hours in (1, 4):
        short = [r for r in closed if r['holding_seconds'] < hours*3600]
        rejected = [r for r in short if not by_id[r['signal_id']]['allowed']]
        summary[f'old_under_{hours}h'] = {'total': len(short), 'gate_rejected': len(rejected),
                                        'reason_counts': dict(Counter(by_id[r['signal_id']]['reason'] for r in rejected)),
                                        'rejected_old_losses': sum(r['net_pnl'] < 0 for r in rejected)}
    write_rows(ROOT / 'analysis/old_pre_entry_gate_decisions.jsonl.gz', decisions)
    write_json(ROOT / 'analysis/old_pre_entry_gate_summary.json', summary)


if __name__ == '__main__':
    main()
