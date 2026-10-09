"""Report corrected independent cases, intermediate defects and separate portfolio."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_cases_bybit import read_rows, stats, write_json


def fmt(value):
    return 'N/A' if value is None else f'{value:.6f}' if isinstance(value, float) else str(value)


def legacy(repo):
    rows = []
    for name in ('limit_15_5', 'limit_60_5', 'final_60_15', 'final_240_5', 'final_240_15', 'final_240_60'):
        p = repo / 'data/reports/historical_blocker_investigation/stage3' / name / 'trades.jsonl'
        rows.extend(json.loads(v) for v in p.read_text().splitlines() if json.loads(v).get('status') == 'CLOSED')
    assert len(rows) == len({v['trade_id'] for v in rows}) == 7
    pnl = [t['net_pnl'] for t in rows]
    r = [t['result_R'] for t in rows]
    return rows, {'CLOSED': len(rows), 'Wins': sum(v > 0 for v in pnl), 'Losses': sum(v < 0 for v in pnl),
                  'WinRate': sum(v > 0 for v in pnl) / len(rows),
                  'ProfitFactor': sum(v for v in pnl if v > 0) / -sum(v for v in pnl if v < 0),
                  'Expectancy': statistics.mean(pnl), 'AvgR': statistics.mean(r), 'MedianR': statistics.median(r),
                  'NetPnL': sum(pnl), 'Fees': sum(t['fees_total'] for t in rows),
                  'Slippage': sum(t['slippage_total'] for t in rows), 'MaxDrawdown': None}


def report(folder, destination):
    repo = destination.parent
    case = json.loads((folder / 'case_summary.json').read_text())
    portfolio = json.loads((folder / 'summary.json').read_text())
    any_tf = json.loads((folder / 'any_tf_summary.json').read_text())
    intermediate = json.loads((repo / 'data/reports/source_bybit_2026_10_09_final/summary.json').read_text())
    primary = read_rows(folder / 'primary_cases.jsonl.gz')
    policy = json.loads((folder / 'run_lock.json').read_text())['policy']
    old, old_stats = legacy(repo)
    audits = []
    for symbol in policy['symbol_priority']:
        audits.extend(json.loads((folder / 'segments' / symbol / 'intermediate_audit.json').read_text()))
    assert len(audits) == 13
    assert all(set(a['snapshots']) == {'ready_time', 'entry_interval_start'} for a in audits)
    audits.sort(key=lambda row: row['old_trade']['entry_interval_start'])
    n = len(primary)
    prefix = folder.relative_to(repo).as_posix()
    lines = ['# Corrected Bybit source trade-case validation', '',
             f'Primary: **{n} unique FILLED + CLOSED trade cases**. Full strict replay: '
             f"{case['CLOSED']} CLOSED, {case['FILLED']} FILLED, {case['OPEN_CENSORED']} OPEN, {case['PENDING_CENSORED']} PENDING censored. "
             + (f"**MAX CLOSED = {case['CLOSED']} under the registered corrected machine policy**; target50 was not reached." if n < 50 else 'The first50 are retained including every loss.'), '',
             '**BACKTEST/SHADOW only; trade_entry_allowed=false; LIVE/private API/orders prohibited.**', '',
             'The five newly uploaded files are Windows shortcuts, byte-identical to the old archive links, not PDF contents. '
             'Eight available DOCX originals and their diagrams were read previously; available Range, D/S, Smart Money Trader2 '
             'and Liquidity texts were checked for this correction. Missing SW5/9/11/12/22 contents cannot be newly read or '
             'promoted from SECONDARY_SOURCE to SOURCE_RULE. This result validates a declared machine interpretation of '
             'available originals and explicit user requirements, not the complete discretionary methodology. '
             '[Attachment receipt](data/source_materials/correction_2026_10_09/attachment_receipt.json).', '',
             'Pre-outcome registration: `363fa01`; corrected implementation/tests and deterministic choices: `2b09acb`, '
             'both published before any corrected outcomes. [Correction protocol](SOURCE_CORRECTION_PROTOCOL.md) and '
             '[source registry](SOURCE_RECONSTRUCTION_2026_10_09.md) distinguish evidence and interpretations. '
             'No outcome-based threshold, symbol, period, entry, stop or exit selection occurred. Frozen studies were not rerun.', '',
             '## Corrected behavior and sample semantics', '',
             'STRICT_CONSERVATIVE mappings:15/5,60/5,60/15,240/5,240/15. 240/60 belongs only to ANY_TF research. '
             'Each unique physical opportunity is deduplicated before outcomes; first available READY wins, deterministic ties '
             'prefer higherHTF/lowerLTF/fixed symbol priority. Alias/mapping duplicates do not manufacture sample size. '
             'Each retained READY receives an independent case with reference1170USDT and planned risk23.4USDT(2%), including '
             'base entry/SL friction. It is independent of other symbols, account occupancy, compounding and3x portfolio budget. '
             'Case PnLs are descriptive sums of independent exposures, never shared-capital NAV or portfolio drawdown.', '',
             'Primary consists of first50 CLOSED cases by actual filled entry interval start, with READY/tie order. '
             'OPEN cases are excluded from CLOSED metrics and explicitly right-censored, not forced closed. '
             'All later cases/closures remain in the full artifacts. This complete40-series dataset (993575 candles,10symbols, '
             'native5/15/60/240m) was checked against saved SHA/count/identity/order/alignment/OHLC requirements. '
             'All January–September2026 history is already-inspected DEVELOPMENT, never OOS.', '',
             'Range now requires a fresh causal external typed POI actually interacted with on deviation, a separate native '
             'close accepting inside the Range, and a later boundary retest. SFP alone cannot create RANGE_POI. '
             'D/S is a separate last opposite move detector, permits multiple candles and no FVG, requires forming-move old '
             'liquidity raid/full absorption/structure/freshness/P-D. Failed OB no longer becomes D/S. '
             'Order Flow stores HH/HL or LL/LH sequence, reclaimed structural liquidity/key test, subsequent body break, '
             'separate CONF and fresh global HTF destination. Global destination test, including smaller native candle '
             'observation, invalidates it; trend alone cannot authorize READY.', '',
             'Local quote/SL choices were fixed by type: OB proximal boundary/full wick extreme; Breaker proximal boundary/'
             'conservative breaking-sweep extreme; STB/BTS midpoint/full manipulation wick; D/S midpoint/full last move wick; '
             'FVG midpoint/reaction raid within an independently proven context. All entries require reaction raid→body BOS→'
             'new structure→distinct CONF→fresh local POI. Liquidity role evidence spans the whole active structural leg '
             'and adverse equal pools, including pools beyond SL. Cause/destination/against/unrelated roles are recorded.', '',
             'Non-Range full FTA is a declared interpretation; Range80% inside opposite boundary plus optional20% to a '
             'pre-entry external FTA, otherwise remainder inside. Original technical SL throughout, no automatic BE. '
             'This additive policy does not change frozen canonical40/30/30 or cost-adjusted BE afterTP1. '
             'Fee.06% and slippage.02% per side are project assumptions. Funding/spread/ticks are unavailable. '
             'Stop-first OHLC ambiguity, entry-bar favorable target CLOSE proof and adverse gap fills remain conservative. '
             'Intrabar fill times are5m intervals known at close. MAE shown is a post-entry-bar OHLC upper bound; entry-bar '
             'extrema may precede unknown fill and are excluded. Entry-bar closures therefore have N/A true MAE.', '',
             '## OLD7 / flawed fc61f3513 / corrected cases', '',
             'OLD7 spans six independent mapping accounts; fc61f35 used one sequential account with flawed source rules. '
             'Neither is a matched causal performance comparison. The previous13-trade report remains '
             '[verbatim](data/reports/source_bybit_fc61f35_intermediate/report.md), with its original artifacts.', '',
             '| Metric | OLD7 descriptive | fc61f35 intermediate13 | Corrected primary cases |', '|---|---:|---:|---:|']
    keys = ('CLOSED', 'Wins', 'Losses', 'WinRate', 'ProfitFactor', 'Expectancy', 'AvgR', 'MedianR', 'NetPnL', 'Fees', 'Slippage', 'MaxDrawdown')
    for k in keys:
        lines.append('| ' + k + ' | ' + ' | '.join(fmt(m.get(k)) for m in (old_stats, intermediate['primary'], case['primary'])) + ' |')
    lines += ['', 'N/A case drawdown reflects independent cases, not absent losses. Portfolio NAV drawdown appears separately.', '',
              '## Re-audit of all13 intermediate closures', '',
              '| Symbol | Direction | Mapping | Old HTF/local POI | Old result/PnL | Classification | Reasons at old cutoff |',
              '|---|---|---|---|---|---|---|']
    for a in audits:
        t = a['old_trade']
        lines.append(f"| {t['symbol']} | {t['direction']} | {t['htf']}/{t['ltf']} | {t['poi_type']}/{t['evidence']['ltf_poi']['kind']} | {t['result']} {fmt(t['net_pnl'])} | {a['classification']} | {'; '.join(a['reasons'])} |")
    counts = Counter(a['classification'] for a in audits)
    lines += ['', f'Audit counts: `{dict(counts)}`. '
              f"Exact old entries remaining eligible under corrected machine policy: {sum(a['remaining_in_corrected_sample'] for a in audits)}. "
              'This does not declare the discretionary opportunities unprofitable or impossible; it tests the old executable '
              'entry/stop/scope/evidence contract. Every per-symbol intermediate_audit.json retains complete old ledger rows '
              'and independent current-prefix snapshots at old READY and entry start. Missing originals remain uncertain.', '',
              '### Five former RANGE losses: causal external POI', '',
              '| Signal | Mapping | External POI existed and interacted before old deviation? | Verdict |', '|---|---|---|---|']
    range_rows = [a for a in audits if a['old_trade']['poi_type'] == 'RANGE_POI']
    for a in range_rows:
        t = a['old_trade']
        external = a['snapshots']['ready_time']['range_external_poi_candidates']
        lines.append(f"| {t['signal_id']} | {t['htf']}/{t['ltf']} | {'; '.join(z['zone_id'] for z in external) if external else 'NO causal qualifying external POI'} | {a['classification']} |")
    lines += ['', '## Primary case ledger', '',
              '| # | Symbol | L/S | Mapping | Setup | HTF/local POI | READY | Fill interval start | Entry | SL | Targets | Exit | Result | NetPnL | R | Fees | Slippage | Post-entry-bar MAE R bound |',
              '|---:|---|---|---|---|---|---|---|---:|---:|---|---|---|---:|---:|---:|---:|---:|']
    for i, t in enumerate(primary, 1):
        mae = None if t['entry_time'] == t['exit_time'] else t['max_adverse_excursion_R']
        fields = [i, t['symbol'], t['direction'], f"{t['htf']}/{t['ltf']}", t['setup_type'],
                  f"{t['poi_type']}/{t['evidence']['ltf_poi']['kind']}", t['ready_time'], t['entry_interval_start'],
                  t['entry'], t['stop'], t['targets'], t['exit_time'], t['result'], t['net_pnl'], t['result_R'], t['fees'], t['slippage'], mae]
        lines.append('| ' + ' | '.join(fmt(v) for v in fields) + ' |')
    lines += ['', '## Primary breakdown (including zero groups)', '']
    for dim, raw in case['primary_breakdown'].items():
        groups = dict(raw)
        expected = policy['symbol_priority'] if dim == 'symbol' else [f'{h}/{l}' for h, l in policy['mappings']] if dim == 'mapping' else ['LONG', 'SHORT'] if dim == 'direction' else ['HTF_POI_LTF_RAID_BOS_CONF', 'RANGE_DEVIATION'] if dim == 'setup_type' else ['ORDER_BLOCK', 'BREAKER', 'DEMAND', 'SUPPLY', 'STB', 'BTS', 'FVG', 'RANGE_POI']
        for key in expected:
            groups.setdefault(key, stats([]))
        lines += [f'### {dim}', '', '| Group | CLOSED | Wins | Losses | WR | PF | Expectancy | AvgR | MedianR | NetPnL |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for key, values in groups.items():
            fields = ('CLOSED', 'Wins', 'Losses', 'WinRate', 'ProfitFactor', 'Expectancy', 'AvgR', 'MedianR', 'NetPnL')
            lines.append('| ' + key + ' | ' + ' | '.join(fmt(values[k]) for k in fields) + ' |')
        lines.append('')
    lines += ['## Complete-case funnel and censoring', '',
              '```json', json.dumps({k: v for k, v in case.items() if k not in ('primary_breakdown', 'primary', 'all_closed')}, indent=2), '```', '',
              'Full strict CLOSED metrics, beyond the primary first50:', '', '```json', json.dumps(case['all_closed'], indent=2), '```', '',
              '## Separate PORTFOLIO_SIMULATION', '',
              'Same deduplicated strict signals, one pending/open account, current-equity2% risk and3x virtual notional cap. '
              'This is a capital/occupancy experiment, excluded from primary strategy-quality cases.', '',
              '```json', json.dumps({k: portfolio[k] for k in ('funnel', 'primary', 'admission_decisions', 'final_cash', 'final_equity')}, indent=2), '```', '',
              '## Separate ANY_TF 240/60 research', '',
              'Excluded from the strict primary sample and portfolio. Independent development cases only.', '',
              '```json', json.dumps({k: any_tf[k] for k in ('READY', 'unique_opportunities', 'FILLED', 'CLOSED', 'OPEN_CENSORED', 'all_closed')}, indent=2), '```', '',
              '## QA and reproduction', '',
              f'Run: `python scripts/run_source_cases_bybit.py --output {prefix}`. Existing segments/results require '
              '`--resume-existing`: exact implementation/policy/input/artifact set and hashes or fail closed. '
              'Completed verification returns VERIFIED_COMPLETE_NO_MUTATION.', '',
              'QA receipts/logs: `data/reports/source_case_qa_2026_10_09`. Compileall, targeted/full suite, RuffE9/F, mypy, '
              'real native prefix and future mutation, source evidence timestamps, scope/dedup/risk/cost ledger and safety checks '
              'are recorded there. Existing source scripts/tests/canonical strategy and prior historical artifacts are retained. '
              'No frozen research rerun. Original PDF reading/source certification remains blocked by actual shortcut uploads.', '',
              'No robust-edge or LIVE-readiness conclusion follows from this already-inspected development sample. '
              'Numerical Range impulse/midpoint, exact-only equal pools and missing Advanced/Pro text limit source completeness.', '']
    destination.write_text('\n'.join(lines))
    write_json(folder / 'comparison.json', {'old7_descriptive': old_stats, 'fc61f35_intermediate13': intermediate['primary'],
                                           'corrected_primary': case['primary'], 'intermediate_audit_counts': dict(counts),
                                           'old_ranges': len(range_rows), 'capital_pooling': False, 'trade_entry_allowed': False})
    return case['primary']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--report', type=Path, default=Path('SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md'))
    args = p.parse_args()
    print(json.dumps(report(args.input.resolve(), args.report.resolve()), indent=2))
