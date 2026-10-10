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


def csv_ledger(path, trades):
    fields = ['trade_id', 'symbol', 'direction', 'status', 'source_setup', 'htf', 'ltf',
              'ready_time', 'entry_time', 'entry_interval_start', 'exit_time', 'exit_reason',
              'ready_time_yekaterinburg', 'entry_time_yekaterinburg', 'exit_time_yekaterinburg',
              'theoretical_entry', 'actual_entry_after_slippage', 'stop', 'targets', 'quantity',
              'risk_amount', 'result_R', 'gross_reference_pnl', 'fees_total', 'slippage_total',
              'net_pnl', 'holding_hours_upper_bound', 'anti_scalp_edge_cost_ratio', 'trade_entry_allowed']
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for t in trades:
            row = {k: t.get(k) for k in fields}
            row.update(gross_reference_pnl=t['gross_pnl']+t['slippage_total'],
                       holding_hours_upper_bound=(instant(t['exit_time'])-instant(t['entry_interval_start'])).total_seconds()/3600 if t['status']=='CLOSED' else None,
                       anti_scalp_edge_cost_ratio=t.get('anti_scalp', {}).get('edge_cost_ratio'),
                       targets=json.dumps(t['targets']), trade_entry_allowed=False)
            for key in ('ready_time', 'entry_time', 'exit_time'):
                row[key+'_yekaterinburg'] = instant(t[key]).astimezone(LOCAL_ZONE).isoformat() if t.get(key) else None
            writer.writerow(row)


def number(value, decimals=3):
    return '—' if value is None else f'{value:,.{decimals}f}'


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


def main():
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    old_path = REPO / 'data/reports/source_permitted_physical_bybit_2026_10_10/cohorts/SOURCE_PERMITTED_UNION/CANCEL_SOURCE_POI_INVALIDATION/cases.jsonl.gz'
    old_trades = [normalize_old(r) for r in read_rows(old_path)]
    data = {'old_independent_cases': {'statistics': closed_statistics(old_trades), 'breakdowns': breakdowns(old_trades)},
            'cohorts': {}, 'trade_entry_allowed': False}
    table = [('Old independent cases / full first FTA', data['old_independent_cases']['statistics'])]
    for cohort in ('bybit_2023_2025', 'native_bybit_2026'):
        data['cohorts'][cohort] = {'arms': {}}
        cohort_data = data['cohorts'][cohort]
        gate_events = []
        ready_physical = {'enabled': set(), 'disabled_cost_gate': set()}
        for arm, physical_set in ready_physical.items():
            for folder in sorted((COHORT_ROOTS[cohort] / 'detection').iterdir()):
                gate_events.extend(read_rows(folder / arm / 'anti_scalp_rejections.jsonl.gz') if arm == 'enabled' else [])
                physical_set.update(s['evidence']['physical_opportunity_id']
                                          for s in read_rows(folder / arm / 'signals.jsonl.gz'))
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
                         rates_denominator='SHARED_COMMON_COVERAGE_DAYS_INCLUDING_ZERO_TRADE_DAYS')
                arm_data[account] = {'statistics': m, 'breakdowns': breakdowns(trades)}
                closed_rows = [t for t in trades if t['status'] == 'CLOSED']
                arm_data[account]['exit_diagnostics'] = {
                    'terminal_reasons': dict(Counter(t['exit_reason'] for t in closed_rows)),
                    'TP1_reached_closed': sum(any(f['reason'] == 'TP1' for f in t['fills']) for t in closed_rows),
                    'TP3_reached_closed': sum(any(f['reason'] == 'TP3' for f in t['fills']) for t in closed_rows),
                    'holding_is_outcome_only': True}
                table.append((cohort+'/'+account+'/'+arm, m))
                csv_ledger(ANALYSIS / f'all_trades_{cohort}_{account}_{arm}.csv', trades)
                if account == 'independent' and arm == 'enabled':
                    closed = sorted((t for t in trades if t['status'] == 'CLOSED'),
                                    key=lambda t: (t['entry_interval_start'], t['ready_time'], t['signal_id']))
                    csv_ledger(ANALYSIS / f'first50_chronological_{cohort}.csv', closed[:50])
            cohort_data['arms'][arm] = arm_data
    overlay = json.loads((ANALYSIS / 'old_pre_entry_gate_summary.json').read_text())
    data['old_pre_entry_overlay'] = overlay
    write_json(ANALYSIS / 'medium_term_statistics.json', data)
    # Standard exported scientific figures, not a generated illustration.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
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
        axes[1].bar([i-.25, i, i+.25], [m['gross_pnl'], -m['fees']-m['slippage'], m['net_pnl']], width=.23,
                    color=['#4675a8', '#c26c40', '#447b50'])
    axes[1].set_xticks(range(len(labels)), labels)
    axes[1].set_ylabel('Independent-case sum USDT (different periods; not NAV)')
    axes[1].axhline(0, color='black', linewidth=.7)
    fig.savefig(ANALYSIS / 'holding_and_costs.svg')
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
        '\nAnti-Scalp rejection counters: '+json.dumps({c:v['anti_scalp'] for c,v in data['cohorts'].items()}, ensure_ascii=False),
        '\nСопоставление старых коротких cases (gate использовал только READY evidence): '+json.dumps(overlay, ensure_ascii=False),
        'Anti-Scalp ON/OFF сравнивается полным причинным replay. Отказ раннему плохому варианту может дать позже READY другому source-valid пути той же идеи; shared occupancy и margin тоже меняют дальнейшие входы. Поэтому ON не обязан уменьшать FILLED ровно на количество отказов. Logged path reasons, unique physical ideas и unique never-READY приведены раздельно; все arms требуют среднесрочный setup/context.',
        '## G. Holding до/после',
        'Время — верхняя граница от начала entry interval до известного exit CLOSE. Intrabar touch точнее OHLC не определяет. OPEN не включены в closed holding. Mean/median/p25/p75/p90/min/max и полный year/month/day breakdown сохранены в medium_term_statistics.json.',
        '### Старые independent cases', bins_table(data['old_independent_cases']['breakdowns']['holding_bins']),
        '### Matched 2026 medium independent cases', bins_table(matched['independent']['breakdowns']['holding_bins']),
        '### Primary 2023–25 medium shared portfolio', bins_table(primary['shared']['breakdowns']['holding_bins']),
        '\nPrimary holding summary: '+json.dumps(m['holding_hours'], ensure_ascii=False),
        '## H. Costs',
        'Gross — движение между reference prices до slippage. Канонический ledger gross уже включает slippage; отчёт добавляет его обратно ровно один раз. Gross − fees − slippage = Net проверяется на каждой CLOSED trade. Costs % gross profit uses sum of positive gross-reference trade P&L; undefined ratios are null. Turnover uses actual entry/partial exit fill notionals.',
        '\nPrimary costs: '+json.dumps({k:m[k] for k in ['gross_pnl','fees','slippage','net_pnl','cost_identity_residual','turnover','total_costs','costs_percent_gross_profit','costs_percent_turnover','average_cost_per_trade','average_gross_move_fraction','average_net_move_fraction']}, ensure_ascii=False),
        '\nShort <4h / medium ≥4h comparisons доступны для каждого cohort/account/filter. Holding — outcome; корреляция с costs не доказывает, что удержание само вызывает loss. Предвходные target distance, stop width и friction дают причинную интерпретацию.',
        '## I. Полный новый backtest',
        'Requested 2023-01-01..2026-01-01; actual primary BTC/ETH coverage до 2025-12-05 23:30 UTC, около 2.93 лет. Warmup 2022 не торгуется. Это pinned Bybit mirror: normalized H1/H4 — complete M15 aggregates; сохранены native comparison differences/provenance limits. Другие exchange prices не смешивались. Все данные уже development, OOS/70% WR claim отсутствует.',
        '\nPrimary shared NAV: '+json.dumps(primary['shared_NAV'], ensure_ascii=False),
        '\nВсе ENTERED сделки, включая OPEN: `data/reports/medium_term_2026_10_10/analysis/all_trades_*.csv`; source proofs, full journal и fills: `role_corrected_v2/{cohort}/detection` и `simulation`. LONG/SHORT, coin, setup, TF, year/month/day и все holding bins: `analysis/medium_term_statistics.json`. Audit/risk timestamps и календарные groups — UTC; человекочитаемые ready/entry/exit CSV дополнены Asia/Yekaterinburg (+05). Primary entry coverage: 2023-01-01 05:00..2025-12-06 04:30 +05.',
        '## J. Оставшиеся ограничения',
        'Funding/liquidation/tick intrabar path не моделируются. Cases и shared NAV нельзя складывать. Более длинный holding сам по себе не обещает edge. Старые source-valid losses, отклонённые новой horizon/cost policy, не объявляются задним числом source false positives. Сохранены QA failures и исправления: pending/main lifetime, RANGE terminal timestamp и actual H1 setup ownership. Финальные executions используют role_corrected_v2; native causal_final и primary compiled_primary сохранены как controls. READY reuse проверяет archived code 0b6bd4e, history SHA и все manifests; ускорение меняет только копирование targets и сканирование уже выбранных refinement paths.',
        'Поправки ownership по каждому signal/known_at сохранены в ownership_corrections.jsonl.gz и statistics JSON. Они уточняют момент выхода по исходному body rule и не исключают убыточные входы по будущим результатам. First50 chronological CLOSED — экспорт, не выбор лучшего поднабора; для оценки используется вся доступная история.',
        '\nДиагностика закрытий primary shared: '+json.dumps(primary['shared']['exit_diagnostics'], ensure_ascii=False),
        '\nДиагностика закрытий matched shared: '+json.dumps(matched['shared']['exit_diagnostics'], ensure_ascii=False),
        'edge_cost_ratio измеряет достаточность потенциального хода, но не вероятность достижения target. Source-valid идея может быстро получить SL или structural exit. Эти исходы остаются в оценке, включая короткие losses; новые thresholds по ним не выбирались.',
        '## K. Файлы',
        '`src/crypto_bot/strategy/anti_scalp.py`, `source_medium_term.py`; `src/crypto_bot/research/medium_statistics.py`; config/source_medium_term_policy.json; scripts/run_medium_term_research.py, run_compiled_medium_term.py, replay_medium_role_correction.py, verify_medium_term.py, verify_medium_artifacts.py, verify_medium_execution_parity.py, audit_old_medium_gate.py, report_medium_term.py; tests/test_medium_term.py; MEDIUM_TERM_RESEARCH_PROTOCOL.md, MEDIUM_TERM_COMPILATION_PROTOCOL.md, MEDIUM_TERM_ROLE_CORRECTION_PROTOCOL.md и MEDIUM_TERM_SOURCE_RECONSTRUCTION.md. Все старые artifacts/tests/reports/history сохранены.',
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
