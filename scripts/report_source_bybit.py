"""Render the first sequential50 sample and evidence audit from completed replay."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_bybit import read_rows, stats, write_json


def fmt(value, digits=4):
    return 'N/A' if value is None else f'{value:.{digits}f}' if isinstance(value, float) else str(value)


def report(folder, destination):
    summary = json.loads((folder / 'summary.json').read_text())
    primary = read_rows(folder / 'primary_trades.jsonl.gz')
    all_trades = read_rows(folder / 'trades.jsonl.gz')
    policy = json.loads((folder / 'run_lock.json').read_text())['policy']
    prefix = folder.relative_to(destination.parent).as_posix()
    legacy_folders = ('limit_15_5', 'limit_60_5', 'final_60_15', 'final_240_5', 'final_240_15', 'final_240_60')
    old = []
    old_funnel = Counter()
    old_mapping = []
    for name in legacy_folders:
        p = destination.parent / 'data/reports/historical_blocker_investigation/stage3' / name
        s = json.loads((p / 'summary.json').read_text())
        old.extend(json.loads(line) for line in (p / 'trades.jsonl').read_text().splitlines() if json.loads(line).get('status') == 'CLOSED')
        f = s['funnel']
        old_funnel['Setups'] += f['unique_setups']
        old_funnel['READY'] += f['ever_status_unique_setup_counts'].get('READY_FOR_VIRTUAL_ENTRY', 0)
        old_funnel['Entries'] += f['entries']
        old_mapping.append({'mapping': f"{s['htf_minutes']}/{s['ltf_minutes']}", 'summary_path': str(p.relative_to(destination.parent)),
                            'portfolio': s['portfolio'], 'execution_start': s['execution_start'], 'execution_end': s['execution_end']})
    if len({t['trade_id'] for t in old}) != len(old) or len(old) != 7:
        raise ValueError('legacy sample must be seven unique original cases')
    old_pnl = [t['net_pnl'] for t in old]
    old_metrics = {'Closed': len(old), 'Wins': sum(v > 0 for v in old_pnl), 'Losses': sum(v < 0 for v in old_pnl),
                   'WinRate': sum(v > 0 for v in old_pnl) / len(old),
                   'PF': sum(v for v in old_pnl if v > 0) / -sum(v for v in old_pnl if v < 0),
                   'Expectancy': statistics.mean(old_pnl), 'Avg R': statistics.mean(t['result_R'] for t in old),
                   'Max DD': 'N/A: six independent capitals'}
    audits = []
    for symbol in policy['symbol_priority']:
        audits.extend(json.loads((folder / 'segments' / symbol / 'old_loss_audit.json').read_text()))
    for row in audits:
        if set(row['snapshots']) != {'ready_time', 'entry_interval_start'}:
            raise ValueError('missing exact historical old-loss cutoffs')
    write_json(folder / 'old_vs_new.json', {'old_metrics_descriptive_seven_cases': old_metrics,
                                            'old_funnel': dict(old_funnel), 'old_independent_mapping_results': old_mapping,
                                            'new_primary': summary['primary'], 'old_losses': audits,
                                            'capital_pooling': False, 'trade_entry_allowed': False})
    n = summary['primary']['CLOSED']
    lines = ['# Source-aligned Bybit validation: completed historical replay', '',
             f"**CLOSED = {n}** in the primary first50 sample. Entire native dataset replay completed: "
             f"{summary['funnel']['CLOSED']} CLOSED, {summary['funnel']['entries']} entries, "
             f"{summary['funnel']['open_censored']} endpoint OPEN. " + (f'MAX CLOSED = {n} under this fixed machine policy.' if n < 50 else ''), '',
             '**BACKTEST only; trade_entry_allowed=false. LIVE/private API disabled.**', '',
             'This is a deterministic source reconstruction with explicitly declared machine interpretations, '
             'not certification of the unavailable Advanced/Pro/risk chapters or prospective profitability. '
             'Sources and policy were committed before new PnL; parameters were not fitted. '
             'Every available closure enters the sample in order, including losses, up to the target50. One account, at most one position/order; '
             'no overlapping research cases or independent capitals are pooled. Chronological observations can still be correlated.', '',
             '## Source audit and code changes', '',
             'The complete supplied ZIP contains eight actual DOCX, no actual PDF. Read every text and122 unique embedded diagrams '
             '(195 references). SW5, SW7, SW9, SW11, SW12 and SW22 contain shortcuts only. '
             'The original archive, full text, OCR and SHA manifest are preserved. '
             '[Registered source matrix](SOURCE_RECONSTRUCTION_2026_10_09.md) separates SOURCE_RULE, '
             'SOURCE_INTERPRETATION, PROJECT_OVERLAY and RESEARCH_PARAMETER.', '',
             'Implemented typed ORDER_BLOCK, BREAKER, DEMAND, SUPPLY, STB/BTS with MANIPULATION provenance, '
             'FVG/IMB and RANGE_POI. Source conservative structure keeps BOS distinct from subsequent new structure/CONF. '
             'Liquidity tracks BSL/SSL, confirmed structural and exact EQH/EQL pools, internal/external context, '
             'completed UTC PDH/PDL and source Range boundary raids. A contextual adverse pool must be swept before entry. '
             'Order Flow stores directional structure, raid and destination POI evidence with known_at/invalidation. '
             'P/D is enforced on the selected path; OTE is reported as confluence, not a trigger. '
             'D/S must be fresh; repeated OB has a separate confirmation contract based on secondary source material, '
             'and primary HTF contexts use first tests.', '',
             'Conservative chain: first HTF POI interaction → LTF raid → BOS → new structure → CONF → fresh local POI limit. '
             'No gap-only HTF permission, .6 displacement ratio, mandatory OTE, Score admission or three-gap target prerequisite. '
             'FTA is the nearest available opposing qualified POI. Non-Range full exit at FTA is a declared machine convention. '
             'Range80% exits inside the opposite edge/earlier FTA and20% uses a pre-entry external FTA when available; '
             'the optional remainder otherwise closes inside, with80/20 accounting. No automatic BE, original technical SL remains.', '',
             'Risk is fixed2% including planned base SL costs; initial equity1170 USDT. Fee0.06% and slippage0.02% per side. '
             'Prior3x isolated virtual notional budget is a PROJECT_OVERLAY; it can block tight-stop sizing. '
             'Funding, actual spread/order book and exchange fills are unavailable and not invented. '
             'Stops dominate OHLC ambiguity; entry-bar target touches require favourable CLOSE proof; '
             'gap stops can lose more than the planned2%. Intrabar fill time is a5m interval known at close.', '',
             'Machine limitations: near-equal liquidity has no supplied numeric tolerance, so exact equality is the proven subset; '
             'qualitative Range impulse/midpoint uses the registered BOS proxy/.08 research tolerance. '
             'Manipulation/STB/BTS aliases are not counted as independent setups. '
             'The60m LTF mapping is labelled any-TF interpretation, outside the secondary1–15m conservative preference. '
             'Missing modules limit literal source certification and detector completeness.', '',
             'Prior interrupted and superseded runs are retained with exact implementation snapshots and QA reasons. '
             'QA corrected the OB origin-candle raid, middle-candle Breaker linkage, true Range P/D bounds, '
             'tested-zone lifecycle observation, broken-LTF limit cancellation and same-zone alias duplication. '
             'The final run follows these corrections. No period, symbol or threshold was selected from PnL.', '',
             '## OLD five losses', '',
             'Old decisions below are reconstructed from the last saved signal available before entry and current native-history '
             'prefix state at both the old READY and entry-interval start. Old replay used rolling contexts; '
             'new source tape uses the complete causal prefix. REJECT/WAIT describes the implemented source policy, '
             'not a claim that an unavailable discretionary chapter proves the market could never support another trade.', '']
    for a in audits:
        t, s = a['old_trade'], a['old_signal']
        before = a['snapshots']['ready_time']
        entry = a['snapshots']['entry_interval_start']
        lines += [f"### {t['symbol']} {t['htf']}/{t['ltf']} {t['direction']} — `{t['signal_id']}`", '',
                  'OLD ENGINE ALLOWED TRADE BECAUSE: ' + ', '.join(s['reasons']) +
                  f"; Score={s['score']}; entry={fmt(t['theoretical_entry'])}, SL={fmt(t['stop'])}, targets={t['targets']}. "
                  'The automatic .6/1.0 impulse and three fresh gap targets satisfied the research overlay; '
                  'causal active OF/adverse-liquidity/P-D were not certified by that READY.', '',
                  f"SOURCE STRATEGY WOULD: **{before['source_strategy_would']} at READY; {entry['source_strategy_would']} before entry**.", '',
                  'REASON: ' + '; '.join(before['reasons']) + '.', '',
                  f"At READY: HTF={before['htf_trend']}, LTF={before['ltf_trend']}, "
                  f"adverse pools={len(before['liquidity_against'])}, "
                  f"typed HTF POI={before['htf_poi']['kind'] if before['htf_poi'] else 'NONE PROVEN'}, "
                  f"local POI={before['ltf_poi']['kind'] if before['ltf_poi'] else 'NONE PROVEN'}, "
                  f"local first test={before['ltf_poi']['first_test'] if before['ltf_poi'] else 'UNKNOWN'}, "
                  f"P/D+OTE={before['pd_ote']}, FTA candidates={len(before['fta'])}, "
                  f"stop valid behind local POI={before['stop_behind_local_zone']}. "
                  f"Before entry blockers: {'; '.join(entry['reasons'])}.", '']
    lines += [f"Full timestamps, BOS/CONF/protected levels, POI freshness, actual pool prices and source evidence: "
              f"[{prefix}/old_vs_new.json]({prefix}/old_vs_new.json).", '',
              '## Dataset and exact funnel', '',
              'All40 native Bybit series and993,575 original candles were read, with stored SHA, identity, '
              'alignment and contiguous chronology validated. All10 fixed symbols and all6 mappings were evaluated. '
              'No Binance or newly fetched data enters this test. Entire saved coverage was processed; '
              'this2026 history was already inspected DEVELOPMENT, never relabelled OOS. '
              'Signals use closed native bars; execution uses the saved5m history.', '',
              '| Stage | Full dataset count |', '|---|---:|']
    for field in ('source_contexts', 'setups', 'qualified_structure', 'liquidity_passed', 'poi_passed', 'order_flow_passed', 'pd_passed', 'READY', 'entries', 'CLOSED', 'open_censored', 'pending_censored'):
        lines.append(f"| {field} | {summary['funnel'].get(field, 0)} |")
    lines += ['', 'Source contexts count qualified first POI interactions across all4 TFs, including5m context. '
              'Mapped setups are separate unique contexts per HTF/LTF, not independent trades. '
              'Gate counts mean ever passed per setup; latest reasons and cancellations remain in each segment. '
              'The full CLOSED count and first50 sample are distinct.', '',
              '| Virtual admission decision | Count |', '|---|---:|']
    for reason, count in sorted(summary['admission_decisions'].items()):
        lines.append(f'| {reason} | {count} |')
    lines += ['', '## First chronological CLOSED trades', '',
              '| # | Symbol | Entry interval start → CLOSED UTC | Side | HTF/LTF | Setup / HTF POI | Sweep level / known_at | Entry | SL | FTA/targets | Exit | R | Net USDT | Result |',
              '|---:|---|---|---|---|---|---|---:|---:|---|---|---:|---:|---|']
    for i, t in enumerate(primary, 1):
        raid = t['evidence']['liquidity_sweep']
        lines.append(f"| {i} | {t['symbol']} | {t['entry_interval_start']} → {t['exit_time']} | {t['direction']} | "
                     f"{t['htf']}/{t['ltf']} | {t['setup_type']} / {t['poi_type']} | {fmt(raid['price'])} / {raid['known_at']} | "
                     f"{fmt(t['entry'])} | {fmt(t['stop'])} | {','.join(fmt(v) for v in t['targets'])} | "
                     f"{t['exit_reason']} @{fmt(t['exit_price'])} | {fmt(t['result_R'])} | {fmt(t['net_pnl'])} | {t['result']} |")
    lines += ['', f'Every fill, cost, fraction, exact quote, source timestamps and causal evidence: '
              f'[{prefix}/primary_trades.jsonl.gz]({prefix}/primary_trades.jsonl.gz).', '',
              '## Primary statistics', '', '| Metric | First chronological sample |', '|---|---:|']
    for key, value in summary['primary'].items():
        lines.append(f'| {key} | {fmt(value)} |')
    lines += ['', 'GrossPnL is before fees and slippage; GrossAfterSlippageBeforeFees uses actual simulated prices. '
              'Net = GrossPnL − Fees − Slippage. AvgLoss is positive loss magnitude; expectancy is net USDT/trade. '
              'MaxDrawdown uses the account5m marked NAV through the last primary closure, including open exposure and estimated exit fees. '
              'Group drawdown is undefined because these groups do not own separate capitals. '
              'Undefined ratios are N/A rather than infinity.', '',
              '## Censored endpoint', '',
              f"Final cash={fmt(summary['final_cash'])} USDT; marked NAV={fmt(summary['final_equity'])} USDT. "
              'Closed-trade statistics exclude fees/unrealized PnL of the endpoint OPEN position; '
              'cash/NAV above include them. The position is retained, not force-closed to increase CLOSED.', '']
    for t in all_trades:
        if t['status'] == 'OPEN':
            lines += [f"OPEN: {t['symbol']} {t['direction']} {t['htf']}/{t['ltf']}, entry={t['entry_time']} "
                      f"@{fmt(t['entry'])}, SL={fmt(t['stop'])}, targets={t['targets']}, planned risk={fmt(t['risk_amount'])} USDT.", '']
    breakdown = dict(summary['primary_breakdown'])
    ltf_groups = {}
    for t in primary:
        ltf_groups.setdefault(t['evidence']['ltf_poi']['kind'], []).append(t)
    breakdown['entry_ltf_poi_type'] = {key: stats(rows) for key, rows in ltf_groups.items()}
    lines += ['## Primary breakdown', '', 'POI type denotes the HTF context; entry_ltf_poi_type describes the actual local entry zone. '
              'Zero groups remain visible; manipulation aliases do not become separate trades.', '']
    for dimension, original_groups in breakdown.items():
        groups = dict(original_groups)
        expected = (policy['symbol_priority'] if dimension == 'symbol' else
                    [f'{h}/{l}' for h, l in policy['mappings']] if dimension == 'mapping' else
                    ['HTF_POI_LTF_RAID_BOS_CONF', 'RANGE_DEVIATION'] if dimension == 'setup_type' else
                    ['ORDER_BLOCK', 'BREAKER', 'DEMAND', 'SUPPLY', 'STB', 'BTS', 'FVG', 'RANGE_POI']
                    if dimension in ('poi_type', 'entry_ltf_poi_type') else ['LONG', 'SHORT'])
        for key in expected:
            groups.setdefault(key, stats([]))
        lines += [f'### {dimension}', '', '| Group | CLOSED | Wins | Losses | WinRate | PF | Expectancy | AvgR | NetPnL | Fees | Slippage | Avg holding seconds |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for key, values in groups.items():
            fields = ('CLOSED', 'Wins', 'Losses', 'WinRate', 'ProfitFactor', 'Expectancy', 'AvgR', 'NetPnL', 'Fees', 'Slippage', 'AvgHoldingSeconds')
            lines.append('| ' + key + ' | ' + ' | '.join(fmt(values[f]) for f in fields) + ' |')
        lines.append('')
    lines += ['## OLD vs NEW', '',
              'OLD contains seven unique development closures from six independent mapping accounts, solely a descriptive '
              'trade-case comparison. NEW contains the first sequential50 closures of one registered account. '
              'Different detections, coverage edges, costs/exit paths and occupancy make this a software comparison, '
              'not an isolated causal estimate of strategy improvement. Old capital/NAV is never summed.', '',
              '| Metric | OLD research engine | NEW source engine |', '|---|---:|---:|']
    new_values = {'Setups': summary['funnel'].get('setups', 0), 'READY': summary['funnel'].get('READY', 0),
                  'Entries': summary['funnel']['entries'], 'Closed': n, 'Wins': summary['primary']['Wins'],
                  'Losses': summary['primary']['Losses'], 'WinRate': summary['primary']['WinRate'],
                  'PF': summary['primary']['ProfitFactor'], 'Expectancy': summary['primary']['Expectancy'],
                  'Avg R': summary['primary']['AvgR'], 'Max DD': summary['primary']['MaxDrawdown']}
    for key in new_values:
        lines.append(f'| {key} | {fmt(old_funnel[key] if key in old_funnel else old_metrics[key])} | {fmt(new_values[key])} |')
    lines += ['', 'Setups/READY/Entries above cover the complete respective runs; NEW Closed/performance describe '
              'the registered first50 sample. Full NEW performance is retained in summary.json. '
              'OLD5 losses do not enter the new ledger merely by changing exits: the same quotes lack an emitted '
              'matching source entry chain or are rejected/waiting as listed above.', '',
              '## Independent OLD mapping drawdowns', '',
              '| Mapping | CLOSED | Max NAV drawdown |', '|---|---:|---:|']
    for row in old_mapping:
        p = row['portfolio']
        lines.append(f"| {row['mapping']} | {p['completed_trades']} | {fmt(p['max_drawdown'] * 100)}% |")
    lines += ['', 'Each OLD row owns its original1170 USDT account; these drawdowns are not summed.', '',
              '## QA and reproducibility', '',
              f'Run: `python scripts/run_source_bybit.py --output {prefix}`. '
              'Verify/reuse: add `--resume-existing`; it checks code/policy/input hashes, all10 segment manifests '
              'and all completed output hashes, then returns VERIFIED_COMPLETE_NO_MUTATION. Corruption or changes fail closed.', '',
              'Compileall, targeted tests, full suite, Ruff E9/F, mypy and safety/evidence audit receipts '
              'are saved under `data/reports/source_bybit_qa_final_2026_10_09`. '
              'Frozen strategy code/config and old historical artifacts were preserved; costly frozen studies were not rerun.', '',
              'This available chronological sample is descriptive development validation. It does not establish robust edge, '
              'prospective performance or LIVE readiness. No parameter or exit variant is selected from this table.', '']
    destination.write_text('\n'.join(lines))
    return summary['primary']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=Path('SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md'))
    args = parser.parse_args()
    print(json.dumps(report(args.input.resolve(), args.report.resolve()), indent=2))
