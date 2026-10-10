"""Produce A–M report, full ledgers, holding/cost tables and exported charts."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

from crypto_bot.research.medium_statistics import breakdowns, closed_statistics, instant
from crypto_bot.strategy.anti_scalp import check_anti_scalp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_medium_term_research import REPO, ROOT, digest, read_rows, seal, write_json

COHORT_ROOTS = {c: ROOT / 'role_corrected_v2' / c
                for c in ('bybit_2023_2025', 'native_bybit_2026')}
ANALYSIS = ROOT / 'analysis'
LOCAL_ZONE = ZoneInfo('Asia/Yekaterinburg')


def normalize_old(row):
    return {**row, 'fees_total': row['fees'], 'slippage_total': row['slippage'],
            'actual_entry_after_slippage': row['entry'], 'theoretical_entry': row['entry_reference'],
            'source_setup': row['path_id']}


def csv_ledger(path, trades, sources=None):
    fields = ['trade_id', 'symbol', 'direction', 'status', 'source_setup', 'htf', 'ltf',
              'ready_time', 'entry_time', 'entry_interval_start', 'exit_time', 'exit_reason',
              'ready_time_yekaterinburg', 'entry_time_yekaterinburg', 'exit_time_yekaterinburg',
              'entry_interval_start_yekaterinburg',
              'theoretical_entry', 'actual_entry_after_slippage', 'stop', 'targets', 'quantity',
              'risk_amount', 'result_R', 'gross_reference_pnl', 'fees_total', 'slippage_total',
              'net_pnl', 'holding_hours_upper_bound', 'anti_scalp_edge_cost_ratio', 'trade_entry_allowed']
    fields += ['ready_edge_cost_ratio', 'expected_gross_move_per_unit', 'estimated_round_trip_cost_per_unit',
               'source_refinement_tf', 'macro_context_tf', 'flow_owner_tf', 'physical_opportunity_id',
               'pnl_is_final', 'realized_gross_after_slippage', 'net_pnl_basis']
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for t in trades:
            row = {k: t.get(k) for k in fields}
            row.update(gross_reference_pnl=t['gross_pnl']+t['slippage_total'] if t['status']=='CLOSED' else None,
                       holding_hours_upper_bound=(instant(t['exit_time'])-instant(t['entry_interval_start'])).total_seconds()/3600 if t['status']=='CLOSED' else None,
                       anti_scalp_edge_cost_ratio=t.get('anti_scalp', {}).get('edge_cost_ratio'),
                       targets=json.dumps(t['targets']), trade_entry_allowed=False)
            row.update(pnl_is_final=t['status']=='CLOSED', realized_gross_after_slippage=t['gross_pnl'],
                       net_pnl_basis='CLOSED_TOTAL' if t['status']=='CLOSED' else 'OPEN_PARTIAL_CASHFLOWS_NOT_MARKED')
            for key in ('ready_time', 'entry_time', 'exit_time', 'entry_interval_start'):
                row[key+'_yekaterinburg'] = instant(t[key]).astimezone(LOCAL_ZONE).isoformat() if t.get(key) else None
            source = (sources or {}).get(t['signal_id'])
            if source:
                e = source['evidence']
                decision = check_anti_scalp(direction=t['direction'], entry=t['theoretical_entry'], target=t['targets'][0],
                                           setup_tf=e['actual_setup_tf'], context_tf=e['macro_context_tf'],
                                           main_setup_valid=e['main_setup_valid'], context_valid=True,
                                           target_known_before_entry=instant(source['known_at']) <= instant(t['entry_interval_start']))
                row.update(anti_scalp_edge_cost_ratio=decision.edge_cost_ratio,
                           ready_edge_cost_ratio=e['anti_scalp']['edge_cost_ratio'],
                           expected_gross_move_per_unit=decision.expected_gross_move,
                           estimated_round_trip_cost_per_unit=decision.estimated_round_trip_cost,
                           source_refinement_tf=e['entry_zone_tf'], macro_context_tf=e['macro_context_tf'],
                           flow_owner_tf=e['flow_owner_tf'], physical_opportunity_id=e['physical_opportunity_id'])
            writer.writerow(row)


def number(value, decimals=3):
    return '—' if value is None else f'{value:,.{decimals}f}'


def csv_breakdowns(path, details):
    fields = ['dimension', 'group', 'total_trades', 'wins', 'losses', 'win_rate', 'profit_factor',
              'expectancy', 'average_R', 'average_planned_RR', 'gross_pnl', 'fees', 'slippage',
              'net_pnl', 'turnover', 'average_cost_per_trade', 'holding_mean_h', 'holding_median_h',
              'holding_p25_h', 'holding_p75_h', 'holding_p90_h', 'holding_min_h', 'holding_max_h']
    sections = {'holding': details['holding_bins'], **details['groups'],
                'horizon': {'short_<4h': details['short'], 'medium_>=4h': details['medium']}}
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for dimension, groups in sections.items():
            for group, m in groups.items():
                row = {k: m.get(k) for k in fields}
                row.update(dimension=dimension, group=group)
                row.update({'holding_'+k+'_h': v for k, v in m['holding_hours'].items()})
                writer.writerow(row)


def group_table(groups):
    lines = ['| Group (UTC for calendar) | CLOSED | WIN/LOSS | WR | PF | Exp | Avg R | Planned RR | Gross | Fees | Slip | Net |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label, m in groups.items():
        lines.append(f"| {label} | {m['total_trades']} | {m['wins']}/{m['losses']} | {number(100*m['win_rate'] if m['win_rate'] is not None else None)}% | {number(m['profit_factor'])} | {number(m['expectancy'])} | {number(m['average_R'])} | {number(m['average_planned_RR'])} | {number(m['gross_pnl'])} | {number(m['fees'])} | {number(m['slippage'])} | {number(m['net_pnl'])} |")
    return '\n'.join(lines)


def metrics_table(rows):
    lines = ['| Cohort / account / filter | CLOSED | WIN/LOSS | WR | PF | Exp | Avg R | Gross | Fees | Slip | Net | Mean/median h |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label, m in rows:
        lines.append(f"| {label} | {m['total_trades']} | {m['wins']}/{m['losses']} | {number(100*m['win_rate'] if m['win_rate'] is not None else None)}% | {number(m['profit_factor'])} | {number(m['expectancy'])} | {number(m['average_R'])} | {number(m['gross_pnl'])} | {number(m['fees'])} | {number(m['slippage'])} | {number(m['net_pnl'])} | {number(m['holding_hours']['mean'])}/{number(m['holding_hours']['median'])} |")
    return '\n'.join(lines)


def bins_table(bins):
    lines = ['| Holding | n | WR | Gross | Fees | Slip | Net | PF | Exp | Avg R | Planned RR |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label, m in bins.items():
        lines.append(f"| {label} | {m['total_trades']} | {number(100*m['win_rate'] if m['win_rate'] is not None else None)}% | {number(m['gross_pnl'])} | {number(m['fees'])} | {number(m['slippage'])} | {number(m['net_pnl'])} | {number(m['profit_factor'])} | {number(m['expectancy'])} | {number(m['average_R'])} | {number(m['average_planned_RR'])} |")
    return '\n'.join(lines)


def filter_effect_table(cohorts):
    lines = ['| Cohort / account | FILLED OFF → ON | CLOSED OFF → ON | Δ FILLED | Net OFF → ON |',
             '|---|---:|---:|---:|---:|']
    for cohort, data in cohorts.items():
        for account in ('independent', 'shared'):
            before = data['arms']['disabled_cost_gate'][account]['statistics']
            after = data['arms']['enabled'][account]['statistics']
            lines.append(f"| {cohort}/{account} | {before['all_FILLED']} → {after['all_FILLED']} | {before['total_trades']} → {after['total_trades']} | {after['all_FILLED']-before['all_FILLED']:+d} | {number(before['net_pnl'])} → {number(after['net_pnl'])} |")
    return '\n'.join(lines)


def anti_scalp_counts_table(cohorts):
    reasons = ('NO_HTF_CONTEXT', 'TARGET_TOO_CLOSE', 'POOR_EDGE_COST_RATIO')
    lines = ['| Cohort / counting basis | Total | NO_HTF_CONTEXT | TARGET_TOO_CLOSE | POOR_EDGE_COST_RATIO |',
             '|---|---:|---:|---:|---:|']
    for cohort, data in cohorts.items():
        gate = data['anti_scalp']
        for basis, key in [('path/reason decisions', 'path_reason_counts'),
                           ('unique ideas never READY / final reason', 'exclusive_final_reason_counts_never_READY')]:
            counts = [gate[key].get('REJECTED_SCALP_'+reason, 0) for reason in reasons]
            lines.append('| '+cohort+'/'+basis+' | '+str(sum(counts))+' | '+' | '.join(map(str, counts))+' |')
    return '\n'.join(lines)


def main():
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    old_path = REPO / 'data/reports/source_permitted_physical_bybit_2026_10_10/cohorts/SOURCE_PERMITTED_UNION/CANCEL_SOURCE_POI_INVALIDATION/cases.jsonl.gz'
    old_trades = [normalize_old(r) for r in read_rows(old_path)]
    data = {'old_independent_cases': {'statistics': closed_statistics(old_trades), 'breakdowns': breakdowns(old_trades)},
            'cohorts': {}, 'trade_entry_allowed': False}
    table = [('Old independent cases / full first FTA', data['old_independent_cases']['statistics'])]
    csv_breakdowns(ANALYSIS / 'breakdowns_old_independent.csv', data['old_independent_cases']['breakdowns'])
    for cohort in ('bybit_2023_2025', 'native_bybit_2026'):
        data['cohorts'][cohort] = {'arms': {}}
        cohort_data = data['cohorts'][cohort]
        gate_events = []
        ready_physical = {'enabled': set(), 'disabled_cost_gate': set()}
        source_maps = {'enabled': {}, 'disabled_cost_gate': {}}
        for arm, physical_set in ready_physical.items():
            for folder in sorted((COHORT_ROOTS[cohort] / 'detection').iterdir()):
                gate_events.extend(read_rows(folder / arm / 'anti_scalp_rejections.jsonl.gz') if arm == 'enabled' else [])
                records = read_rows(folder / arm / 'signals.jsonl.gz')
                physical_set.update(s['evidence']['physical_opportunity_id'] for s in records)
                source_maps[arm].update({s['signal_id']: s for s in records})
        last_reject_by_id = {}
        for r in sorted(gate_events, key=lambda r: (r['known_at'], r['signal_id'])):
            if r['physical_opportunity_id'] not in ready_physical['enabled']:
                last_reject_by_id[r['physical_opportunity_id']] = r
        cohort_data['anti_scalp'] = {'logged_path_reason_decisions': len(gate_events),
                                     'unique_physical_opportunities_with_rejection': len({r['physical_opportunity_id'] for r in gate_events}),
                                     'unique_rejected_and_never_READY': len(last_reject_by_id),
                                     'exclusive_final_reason_counts_never_READY': dict(Counter(r['reason'] for r in last_reject_by_id.values())),
                                     'path_reason_counts': dict(Counter(r['reason'] for r in gate_events)),
                                     'cost_gate_removed_READY_physical_ids': len(ready_physical['disabled_cost_gate'] - ready_physical['enabled']),
                                     'cost_gate_removed_READY_ids': sorted(ready_physical['disabled_cost_gate'] - ready_physical['enabled']),
                                     'all_arms_require_valid_medium_setup_and_context': True}
        cohort_data['setup_ownership'] = {
            'correction_events': [r for folder in sorted((COHORT_ROOTS[cohort] / 'detection').iterdir())
                                  for r in read_rows(folder / 'ownership_corrections.jsonl.gz')],
            'READY_geometry_and_physical_identity_unchanged': True}
        for arm in ('enabled', 'disabled_cost_gate'):
            folder = COHORT_ROOTS[cohort] / 'simulation' / arm
            arm_data = {'manifest': json.loads((folder / 'manifest.json').read_text()),
                        'shared_NAV': json.loads((folder / 'shared_summary.json').read_text()),
                        'coverage': json.loads((folder / 'coverage.json').read_text())}
            funnel, paths = Counter(), Counter()
            for detected in sorted((COHORT_ROOTS[cohort] / 'detection').iterdir()):
                f = json.loads((detected / arm / 'funnel.json').read_text())
                funnel.update(f['funnel'])
                paths.update(f['paths'])
            arm_data['detection_funnel'] = dict(funnel)
            arm_data['READY_paths'] = dict(paths)
            lifecycle = read_rows(folder / 'execution_lifecycle.jsonl.gz')
            arm_data['terminal_unfilled_statuses'] = dict(Counter(r['status'] for r in lifecycle
                                                                  if r['status'] not in ('ENTERED', 'CLOSED', 'CENSORED_OPEN')))
            arm_data['independent_admission_blocks'] = dict(Counter(r['reason'] for r in read_rows(folder / 'case_admission_blocks.jsonl.gz')))
            arm_data['shared_admission_anti_scalp_rejections'] = dict(Counter(r['reason'] for r in read_rows(folder / 'admission_anti_scalp_rejections.jsonl.gz')))
            for account, name in [('independent', 'independent_cases.jsonl.gz'), ('shared', 'shared_trades.jsonl.gz')]:
                trades = read_rows(folder / name)
                m = closed_statistics(trades)
                start, end = instant(arm_data['coverage']['shared_start']), instant(arm_data['coverage']['shared_end'])
                days = (end-start).total_seconds()/86400
                m.update(all_FILLED=len(trades), OPEN=sum(t['status']=='OPEN' for t in trades),
                         trades_per_year=m['total_trades']/days*365.25,
                         trades_per_month=m['total_trades']/days*30.4375,
                         trades_per_day=m['total_trades']/days,
                         entries_per_year=len(trades)/days*365.25,
                         entries_per_month=len(trades)/days*30.4375,
                         entries_per_day=len(trades)/days,
                         total_trades_basis='CLOSED_ONLY; all_FILLED includes OPEN',
                         rates_denominator='SHARED_COMMON_COVERAGE_DAYS_INCLUDING_ZERO_TRADE_DAYS')
                arm_data[account] = {'statistics': m, 'breakdowns': breakdowns(trades)}
                csv_breakdowns(ANALYSIS / f'breakdowns_{cohort}_{account}_{arm}.csv', arm_data[account]['breakdowns'])
                closed_rows = [t for t in trades if t['status'] == 'CLOSED']
                arm_data[account]['exit_diagnostics'] = {
                    'terminal_reasons': dict(Counter(t['exit_reason'] for t in closed_rows)),
                    'TP1_reached_closed': sum(any(f['reason'] == 'TP1' for f in t['fills']) for t in closed_rows),
                    'TP3_reached_closed': sum(any(f['reason'] == 'TP3' for f in t['fills']) for t in closed_rows),
                    'holding_is_outcome_only': True}
                table.append((cohort+'/'+account+'/'+arm, m))
                csv_ledger(ANALYSIS / f'all_trades_{cohort}_{account}_{arm}.csv', trades, source_maps[arm])
                if account == 'independent' and arm == 'enabled':
                    closed = sorted((t for t in trades if t['status'] == 'CLOSED'),
                                    key=lambda t: (t['entry_interval_start'], t['ready_time'], t['signal_id']))
                    csv_ledger(ANALYSIS / f'first50_chronological_{cohort}.csv', closed[:50], source_maps[arm])
            cohort_data['arms'][arm] = arm_data
    overlay = json.loads((ANALYSIS / 'old_pre_entry_gate_summary.json').read_text())
    data['old_pre_entry_overlay'] = overlay
    write_json(ANALYSIS / 'medium_term_statistics.json', data)
    # Standard exported scientific figures, not a generated illustration.
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['svg.hashsalt'] = 'medium-term-source-2026-10-10'
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    labels = ['Old cases', '2026 medium', '2023–25 medium']
    selections = [data['old_independent_cases'], data['cohorts']['native_bybit_2026']['arms']['enabled']['independent'],
                  data['cohorts']['bybit_2023_2025']['arms']['enabled']['independent']]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for label, selected in zip(labels, selections):
        bins = selected['breakdowns']['holding_bins']
        total = selected['statistics']['total_trades']
        axes[0].plot(list(bins), [100*v['total_trades']/total if total else 0 for v in bins.values()], marker='o', label=label)
    axes[0].set(xlabel='Observed holding duration (upper bound)', ylabel='% closed cases')
    axes[0].legend()
    for i, selected in enumerate(selections):
        m = selected['statistics']
        count = m['total_trades'] or 1
        axes[1].bar([i-.25, i, i+.25], [m['gross_pnl']/count, (-m['fees']-m['slippage'])/count, m['net_pnl']/count], width=.23,
                    color=['#4675a8', '#c26c40', '#447b50'])
    axes[1].set_xticks(range(len(labels)), labels)
    axes[1].set_ylabel('Independent-case mean USDT/trade (not NAV)')
    axes[1].set_title('Gross / costs / net; different periods and budget policies')
    axes[1].legend(handles=[Patch(color=color, label=label) for color, label in
                            [('#4675a8', 'Gross before friction'),
                             ('#c26c40', 'Fees + slippage (deduction)'), ('#447b50', 'Net')]])
    axes[1].axhline(0, color='black', linewidth=.7)
    fig.savefig(ANALYSIS / 'holding_and_costs.svg', metadata={'Date': None})
    fig.savefig(ANALYSIS / 'holding_and_costs.png', dpi=170)
    plt.close(fig)
    primary = data['cohorts']['bybit_2023_2025']['arms']['enabled']
    matched = data['cohorts']['native_bybit_2026']['arms']['enabled']
    m = primary['shared']['statistics']
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    qa = json.loads((ROOT / 'qa/final_qa_receipt.json').read_text())
    lines = [
        '# Среднесрочная Strategy Engine + Anti-Scalp: итоговый отчёт',
        'Все суммы ниже относятся к виртуальному BACKTEST. `trade_entry_allowed=false`.',
        '## A. Почему было 16 333 CLOSED',
        'Это независимые source cases на десяти монетах и шести TF mappings. 8 720 использовали M15/M5; 4 361 H1/M5; 2 086 H4/M5; 728 H1/M15; 389 H4/M15; 49 H4/H1. Каждая идея получала отдельный reference budget, без shared occupancy. Median 65 минут; 7 675 случаев <1h. Сам счётчик не доказывает скальпинг.',
        '## B. Конкретные короткие допущения',
        '`source_permitted._direct`: локальный non-OB мог стать самостоятельной идеей; `_conservative`: micro BOS/new POI; `_emit`: локальный SL и первая FTA mapping; `source_permitted_cases`: полный FTA exit без TP40/30/30/BE и shared notional budget. Max holding, timeout, forced EOF exit и minimum holding отсутствовали. Канонический VirtualPortfolio уже имел TP40/30/30, BE и risk guards; его правила сохранены.',
        '## C. Изменения',
        'Добавлен отдельный MediumTermEngine: H1/H4 ownership, реальный macro context, main structural stop, три distinct pre-known macro targets, immutable physical path selection, корректные causal timestamps. Anti-Scalp проверяет nearest FTA до READY и admission: gross/cost >=3; все четыре costs включены. Порог — инженерная policy, зафиксированная до результатов, не PDF rule. Фиксированных процентных TP и фильтра по будущему holding нет.',
        'Owner flow и owner setup разделены: H1 POI внутри H4 flow инвалидируется по фактическому H1 CLOSE; H4 сохраняет собственную protected thesis. READY IDs/geometry и выбор пути сохранены. На границе primary периода READY из завершённого warmup CLOSE ставится в pending до первого разрешённого OPEN. Risk-blocked unfilled — REJECTED_ADMISSION, а не EOF censoring.',
        '## D. Timeframe roles',
        'D1/H4: context, dealing range, structure/liquidity. H4/H1: setup. H1/M15: refinement. Primary execution clock M15 — реальных M5 в mirror нет. Matched native execution clock M5 — только наблюдение/исполнение, без M5 идей. D1 — полные UTC дни реальных bars, без interpolation.',
        '## E. Lifecycle',
        'DISCOVERED → QUALIFIED → READY → ENTERED → CLOSED/INVALIDATED/EXPIRED. Quotes aliases не создают отдельные trades. OB повторяется только с новой causal reaction; D/S fresh. Исчезновение entry POI/context и потребление target снимают pending quote. Main body/structure/range причина завершает entered idea. Нет timer cooldown/TTL/minimum holding/forced close; OPEN и unfilled end cases censored.',
        '## F. Funnel и количество',
        'Independent-case и shared-account результаты разделены; новая notional cap также влияет на admissibility, поэтому падение count не приписывается одному TF/Anti-Scalp.',
        metrics_table(table),
        '\nPrimary independent funnel: '+json.dumps({k:primary['manifest'][k] for k in ('READY','FILLED','CLOSED','shared_FILLED','shared_CLOSED')}, ensure_ascii=False),
        '\nMatched independent funnel: '+json.dumps({k:matched['manifest'][k] for k in ('READY','FILLED','CLOSED','shared_FILLED','shared_CLOSED')}, ensure_ascii=False),
        '\nПричины до READY (счётчики causal path/reason, не уникальных trades): '+json.dumps({c:{a:v['detection_funnel'] for a,v in d['arms'].items()} for c,d in data['cohorts'].items()}, ensure_ascii=False),
        '\nНезаполненные READY: '+json.dumps({c:{a:v['terminal_unfilled_statuses'] for a,v in d['arms'].items()} for c,d in data['cohorts'].items()}, ensure_ascii=False),
        '\nAnti-Scalp rejection counters:', anti_scalp_counts_table(data['cohorts']),
        '\nПолные counters и идентификаторы cost-gate exclusions: '+json.dumps({c:v['anti_scalp'] for c,v in data['cohorts'].items()}, ensure_ascii=False),
        '\nВлияние cost gate на полный replay; Net только CLOSED:', filter_effect_table(data['cohorts']),
        '\nСопоставление старых коротких cases (gate использовал только READY evidence): '+json.dumps(overlay, ensure_ascii=False),
        'Anti-Scalp ON/OFF сравнивается полным причинным replay. Отказ раннему плохому варианту может дать позже READY другому source-valid пути той же идеи; shared occupancy и margin тоже меняют дальнейшие входы. Поэтому ON не обязан уменьшать FILLED ровно на количество отказов. Logged path reasons, unique physical ideas и unique never-READY приведены раздельно; все arms требуют среднесрочный setup/context.',
        '## G. Holding до/после',
        'Время — верхняя граница от начала entry interval до известного exit CLOSE. entry_time обозначает CLOSE, на котором виртуальный fill стал наблюдаемым; точный intrabar touch OHLC не определяет. OPEN не включены в closed holding. Mean/median/p25/p75/p90/min/max и полный year/month/day breakdown сохранены в medium_term_statistics.json.',
        '\nPrimary shared frequency, включая нулевые дни: '+json.dumps({k:m[k] for k in ['all_FILLED','OPEN','trades_per_year','trades_per_month','trades_per_day','entries_per_year','entries_per_month','entries_per_day','total_trades_basis','rates_denominator']}, ensure_ascii=False),
        '### Старые independent cases', bins_table(data['old_independent_cases']['breakdowns']['holding_bins']),
        '### Matched 2026 medium independent cases', bins_table(matched['independent']['breakdowns']['holding_bins']),
        '### Primary 2023–25 medium shared portfolio', bins_table(primary['shared']['breakdowns']['holding_bins']),
        '\nPrimary holding summary: '+json.dumps(m['holding_hours'], ensure_ascii=False),
        '## H. Costs',
        'Gross — движение между reference prices до slippage. Канонический ledger gross уже включает slippage; отчёт добавляет его обратно ровно один раз. Gross − fees − slippage = Net проверяется на каждой CLOSED trade. Costs % gross profit uses sum of positive gross-reference trade P&L; undefined ratios are null. Turnover uses actual entry/partial exit fill notionals.',
        '\nPrimary costs: '+json.dumps({k:m[k] for k in ['gross_pnl','fees','slippage','net_pnl','cost_identity_residual','turnover','total_costs','costs_percent_gross_profit','costs_percent_turnover','average_cost_per_trade','average_gross_move_fraction','average_net_move_fraction']}, ensure_ascii=False),
        '\nShort <4h / medium ≥4h comparisons доступны для каждого cohort/account/filter. Holding — outcome; корреляция с costs не доказывает, что удержание само вызывает loss. Предвходные target distance, stop width и friction дают причинную интерпретацию.',
        metrics_table([(label+'/'+horizon, selected['breakdowns'][horizon])
                       for label, selected in [('Old independent', data['old_independent_cases']),
                                               ('Matched medium independent', matched['independent']),
                                               ('Primary medium shared', primary['shared'])]
                       for horizon in ('short', 'medium')]),
        '## I. Полный новый backtest',
        'Requested 2023-01-01..2026-01-01; actual primary BTC/ETH coverage до 2025-12-05 23:30 UTC, около 2.93 лет. Warmup 2022 не торгуется. Это pinned Bybit mirror: normalized H1/H4 — complete M15 aggregates; сохранены native comparison differences/provenance limits. Другие exchange prices не смешивались. Все данные уже development, OOS/70% WR claim отсутствует.',
        '\nPrimary shared NAV: '+json.dumps(primary['shared_NAV'], ensure_ascii=False),
        '\nPrimary shared results by direction', group_table(primary['shared']['breakdowns']['groups']['direction']),
        '\nPrimary shared results by coin', group_table(primary['shared']['breakdowns']['groups']['coin']),
        '\nPrimary shared results by setup', group_table(primary['shared']['breakdowns']['groups']['setup']),
        '\nPrimary shared results by actual setup TF / execution clock', group_table(primary['shared']['breakdowns']['groups']['timeframe']),
        '\nPrimary shared results by year', group_table(primary['shared']['breakdowns']['groups']['year']),
        '\nPrimary shared results by month', group_table(primary['shared']['breakdowns']['groups']['month']),
        '\nВсе ENTERED сделки, включая OPEN: `data/reports/medium_term_2026_10_10/analysis/all_trades_*.csv`; source proofs, full journal и fills: `role_corrected_v2/{cohort}/detection` и `simulation`. LONG/SHORT, coin, setup, TF, year/month/day и все holding bins: `analysis/medium_term_statistics.json`. Audit/risk timestamps и календарные groups — UTC; year/month/day groups основаны на entry_interval_start. Человекочитаемые ready/entry/exit и начало entry interval в CSV дополнены Asia/Yekaterinburg (+05). Primary entry coverage: 2023-01-01 05:00..2025-12-06 04:30 +05.',
        '## J. Оставшиеся ограничения',
        'Funding/liquidation/tick intrabar path не моделируются. Cases и shared NAV нельзя складывать. Более длинный holding сам по себе не обещает edge. Старые source-valid losses, отклонённые новой horizon/cost policy, не объявляются задним числом source false positives. Сохранены QA failures и исправления: pending/main lifetime, RANGE terminal timestamp и actual H1 setup ownership. Финальные executions используют role_corrected_v2; native causal_final и primary compiled_primary сохранены как controls. READY reuse проверяет archived code 0b6bd4e, history SHA и все manifests; ускорение меняет только копирование targets и сканирование уже выбранных refinement paths.',
        'Поправки ownership по каждому signal/known_at сохранены в ownership_corrections.jsonl.gz и statistics JSON. Они уточняют момент выхода по исходному body rule и не исключают убыточные входы по будущим результатам. First50 chronological CLOSED — экспорт, не выбор лучшего поднабора; для оценки используется вся доступная история.',
        '\nДиагностика закрытий primary shared: '+json.dumps(primary['shared']['exit_diagnostics'], ensure_ascii=False),
        '\nДиагностика закрытий matched shared: '+json.dumps(matched['shared']['exit_diagnostics'], ensure_ascii=False),
        'edge_cost_ratio измеряет достаточность потенциального хода, но не вероятность достижения target. Source-valid идея может быстро получить SL или structural exit. Эти исходы остаются в оценке, включая короткие losses; новые thresholds по ним не выбирались.',
        '## K. Файлы',
        '`src/crypto_bot/strategy/anti_scalp.py`, `source_medium_term.py`; `src/crypto_bot/research/medium_statistics.py`; config/source_medium_term_policy.json; scripts/run_medium_term_research.py, run_compiled_medium_term.py, replay_medium_role_correction.py, verify_medium_term.py, verify_medium_artifacts.py, verify_medium_execution_parity.py, audit_old_medium_gate.py, report_medium_term.py, build_medium_qa_receipt.py; tests/test_medium_term.py; MEDIUM_TERM_RESEARCH_PROTOCOL.md, MEDIUM_TERM_COMPILATION_PROTOCOL.md, MEDIUM_TERM_ROLE_CORRECTION_PROTOCOL.md и MEDIUM_TERM_SOURCE_RECONSTRUCTION.md. Воспроизводимая настройка среды: scripts/cloud_environment_install.sh и CLOUD_ENVIRONMENT_SETUP.md. Все старые artifacts/tests/reports/history сохранены.',
        '## L. Commit',
        f'Исходный код до результатов: c754eb0; эквивалентный compiler: 0b6bd4e; role correction зарегистрирован до corrected P&L: 7ef3605. HEAD при генерации отчёта: {head}; ветка medium-term-source-research. Финальный artifact commit сообщается после sealing. Force push не использовался; main baseline dab8d25 сохранён.',
        '## M. Tests / QA', json.dumps(qa, ensure_ascii=False, indent=2),
        '\n![Holding and costs](data/reports/medium_term_2026_10_10/analysis/holding_and_costs.png)',
    ]
    (REPO / 'MEDIUM_TERM_BYBIT_REPORT.md').write_text('\n\n'.join(lines)+'\n')
    dependency_hashes = {str(p.relative_to(REPO)): digest(p) for p in [Path(__file__), old_path,
                        ROOT / 'qa/final_qa_receipt.json', ANALYSIS / 'old_pre_entry_gate_summary.json']}
    for cohort in data['cohorts']:
        for arm in ('enabled', 'disabled_cost_gate'):
            p = COHORT_ROOTS[cohort] / 'simulation' / arm / 'manifest.json'
            dependency_hashes[str(p.relative_to(REPO))] = digest(p)
    seal(ANALYSIS, digest(REPO / 'MEDIUM_TERM_BYBIT_REPORT.md'), {'dependencies': dependency_hashes,
                                                               'report_sha256': digest(REPO / 'MEDIUM_TERM_BYBIT_REPORT.md')})
    print(metrics_table(table))


if __name__ == '__main__':
    main()
