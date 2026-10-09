"""Render complete primary-PDF case results, comparisons and source audit."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_source_pdf_native_bybit import read_rows, write_json


def fmt(v):
    if v is None:
        return 'N/A'
    if isinstance(v, float):
        return f'{v:.8g}'
    return str(v)


def render(root: Path, output: Path):
    repo = Path(__file__).resolve().parents[1]
    case = json.loads((root / 'case_summary.json').read_text())
    portfolio = json.loads((root / 'summary.json').read_text())
    any_tf = json.loads((root / 'any_tf_summary.json').read_text())
    lock = json.loads((root / 'run_lock.json').read_text())
    signals, setups, audits, original = [], [], [], []
    for symbol in lock['policy']['symbol_priority']:
        folder = root / 'segments' / symbol
        signals.extend(read_rows(folder / 'signals.jsonl.gz'))
        setups.extend(read_rows(folder / 'setup_outcomes.jsonl.gz'))
        audits.extend(json.loads((folder / 'intermediate_audit.json').read_text()))
        original.extend(json.loads((folder / 'old_loss_audit.json').read_text()))
    strict = [r for r in setups if [r['htf'], r['ltf']] in lock['policy']['mappings']]
    funnel = Counter(stage for row in strict for stage in row['stages'])
    primary = read_rows(root / 'primary_cases.jsonl.gz')
    trades = read_rows(root / 'cases.jsonl.gz')
    decisions = read_rows(root / 'case_decisions.jsonl.gz')
    fc = json.loads((repo / 'data/reports/source_bybit_2026_10_09_final/summary.json').read_text())
    prev = json.loads((repo / 'data/reports/source_cases_bybit_2026_10_09/case_summary.json').read_text())
    prefix = root.relative_to(repo).as_posix()
    initial_pdf = json.loads((repo / 'data/reports/source_pdf_bybit_2026_10_09/case_summary.json').read_text())
    old74_signals = [r for p in (repo / 'data/reports/source_cases_bybit_2026_10_09/segments').glob('*/signals.jsonl.gz') for r in read_rows(p)]
    initial_signals = [r for p in (repo / 'data/reports/source_pdf_bybit_2026_10_09/segments').glob('*/signals.jsonl.gz') for r in read_rows(p)]
    lines = ['# Bybit SOURCE_TRADE_CASE_VALIDATION — первичные PDF', '',
             f"Полный replay завершён: **{case['READY']} READY → {case['FILLED']} FILLED → {case['CLOSED']} CLOSED**. "
             f"Уникальных opportunities: {case['unique_opportunities']}; дубликатов: {case['duplicates']}. "
             f"Основная выборка: {len(primary)} первых уникальных закрытых сделок по хронологии entry.", '',
             'Прочитаны все 54 страницы SW5 (9), SW9 (16), SW11 (8), SW12 (15), SW22 (6): весь текст и все схемы. '
             '[Оригиналы, полный текст и SHA256](data/source_materials/primary_pdf_2026_10_09/manifest.json); '
             '[постраничная source reconstruction](SOURCE_PDF_PROTOCOL.md) и [native timing correction](SOURCE_PDF_NATIVE_PROTOCOL.md). '
             'Первичные SOURCE_RULE отделены от численной машинной интерпретации и выбранных допустимых вариантов. '
             'Source protocol опубликован в `18eb8bb`, первоначальная PDF реализация — в `63ab3ae`. '
             'Первый PDF replay (9 READY /0FILLED/0CLOSED) сохранён; native timing correction и 504 tests '
             'опубликованы в `cbcd30a` до текущих outcomes. Этот этап уже знает результат первоначального PDF '
             'прогона, поэтому не выдаётся за полностью слепое исследование.', '',
             'Все 40 сохранённых native Bybit серий / 993575 свечей проверены по SHA, count, identity и alignment; '
             '10 символов, 5m/15m/60m/240m. Это ранее просмотренная история 2026 DEVELOPMENT, не OOS. '
             'Нет интерполяции, синтетических свечей, LIVE/private API. `trade_entry_allowed=false`.', '',
             'Основные mappings: 15/5,60/5,60/15,240/5,240/15. Каждый уникальный READY получает отдельный '
             'reference account 1170 USDT, риск 23.4 USDT (2%) с учётом базовых затрат. Общая занятость и '
             'portfolio budget не подавляют trade cases. Dedup выполняется до fills/outcomes: первый READY, '
             'затем higher HTF/lower LTF/fixed symbol priority/ID. Разные визиты OB различаются. '
             'Все CLOSED сверх первых 50 и все OPEN сохранены; endpoint не закрывает сделку принудительно.', '',
             '## Новый funnel', '', '| Этап — строго пять mappings | Количество |', '|---|---:|']
    for name in ('setups','qualified_structure','liquidity_passed','poi_passed','order_flow_passed','pd_passed','READY'):
        lines.append(f'| {name} | {funnel[name]} |')
    for name in ('unique_opportunities','duplicates','FILLED','CLOSED','OPEN_CENSORED','PENDING_CENSORED'):
        lines.append(f'| {name} | {case[name]} |')
    lines += ['', 'Source_contexts считаются на TF до разветвления по mappings и могут включать 240/60; '
              'таблица выше вычислена непосредственно по строгим setup artifacts. Стадии являются accumulated '
              'ever-passed counters; отменённые setups остаются в funnel.', '',
              '## WIN/LOSS и результаты', '',
              '| Метрика | fc61f35: старый последовательный portfolio | 74a6f8d: cases без PDF | Первоначальный PDF / HTF close | Исправленный native PDF cases |',
              '|---|---:|---:|---:|---:|']
    for name in ('READY','FILLED'):
        values = [fc['funnel']['READY' if name=='READY' else 'entries'],prev[name],initial_pdf[name],case[name]]
        lines.append('| '+name+' | '+' | '.join(fmt(v) for v in values)+' |')
    for key in ('CLOSED','Wins','Losses','BE','WinRate','ProfitFactor','Expectancy','AvgR','MedianR','NetPnL','Fees','Slippage'):
        values = [fc['primary'].get(key), prev['primary'].get(key), initial_pdf['primary'].get(key), case['primary'].get(key)]
        if key=='WinRate': values=[v*100 if v is not None else None for v in values]
        lines.append('| '+key+(' (%)' if key=='WinRate' else '')+' | '+' | '.join(fmt(v) for v in values)+' |')
    lines += ['', 'PF = сумма положительных net PnL / абсолютная сумма отрицательных net PnL. '
              'Expectancy = средний net PnL на CLOSED, Avg R = средний net PnL / первоначальный planned risk. '
              'WIN/LOSS определяется net PnL после затрат. N/A означает неопределённую метрику. '
              'Сумма независимых case PnL не является NAV общего торгового счёта; portfolio DD к ней не применяется. '
              'fc61f35 и новый результат имеют разные admission/entry/exit contracts, поэтому разницу нельзя '
              'приписывать только качеству стратегии. 0 CLOSED в 74a6f8d не было окончательной оценкой метода.', '',
              '## Все FILLED trade cases', '',
              '| # | ID | Symbol | L/S | HTF/LTF | HTF/local POI | READY | Fill interval start | Entry | SL | Targets/fractions | Exit | Status/result | Net PnL | R | Fees | Slippage |',
              '|---:|---|---|---|---|---|---|---|---:|---:|---|---|---|---:|---:|---:|---:|']
    for i,t in enumerate(trades,1):
        fields=[i,t['signal_id'],t['symbol'],t['direction'],f"{t['htf']}/{t['ltf']}",
                f"{t['poi_type']}/{t['evidence']['ltf_poi']['kind']}",t['ready_time'],t['entry_interval_start'],
                t['entry'],t['stop'],f"{t['targets']} / {t['fractions']}",t.get('exit_time'),
                t.get('result',t['status']),t['net_pnl'],t.get('result_R'),t['fees'],t['slippage']]
        lines.append('| '+' | '.join(fmt(v) for v in fields)+' |')
    if not trades: lines += ['', 'FILLED trade cases отсутствуют; WIN/LOSS выборки нет.']
    lines += ['', f'[Полные сделки со всеми fills и source snapshots]({prefix}/cases.jsonl.gz); '
              f'[первые 50 или фактическое меньшее число]({prefix}/primary_cases.jsonl.gz); '
              f'[все решения/отмены]({prefix}/case_decisions.jsonl.gz).', '',
              'Комиссия 0.06% и slippage 0.02% на каждую сторону — фиксированные project assumptions. '
              'Funding, spread, tick sizes и market impact недоступны и не моделируются. Время fill — '
              'интервал реальной 5m свечи, известный на CLOSE. Stop-first при неоднозначном OHLC, '
              'favorable entry-bar TP требует CLOSE proof; adverse gap исполняется по OPEN. '
              'Истинный intrabar MAE неизвестен: сохранён только OHLC upper bound после entry bar; '
              'для закрытия в entry bar MAE — N/A.', '',
              '## Все READY и исполнение лимитов', '',
              '| ID | Symbol | Mapping | Visit | HTF/local POI | READY | Quote | SL | Targets | Execution decisions |',
              '|---|---|---|---:|---|---|---:|---:|---|---|']
    for r in sorted(signals,key=lambda r:(r['known_at'],r['signal_id'])):
        if [r['htf'],r['ltf']] not in lock['policy']['mappings']:continue
        ds=[f"{d['known_at']}: {d['reason']}" for d in decisions if d['signal_id']==r['signal_id']]
        fields=[r['signal_id'],r['symbol'],f"{r['htf']}/{r['ltf']}",r['evidence']['htf_visit_number'],
                f"{r['poi_type']}/{r['evidence']['ltf_poi']['kind']}",r['known_at'],r['entry'],r['stop'],r['targets'],'; '.join(ds)]
        lines.append('| '+' | '.join(fmt(v) for v in fields)+' |')
    lines += ['', 'Все 9 active limits независимо прослежены по фактическим native 5m свечам. '
              'Quote не достигнут до причинной отмены: 6 сломов подтверждённой LTF структуры, '
              '2 теста глобальной цели и 1 прекращение Order Flow. '
              '[Все проверенные интервалы и source cancellations](data/reports/source_pdf_native_qa_2026_10_09/execution_audit.json).', '',
              '## Что изменилось относительно fc61f35 и 74a6f8d', '',
              '- Уже известная HTF POI теперь наблюдается на CLOSED native 5m, без ожидания HTF close '
              '(SW9 p4–6), без формирования/чтения незакрытой HTF свечи. Один визит не пересчитывается на HTF close. '
              'FTA уже позади текущего LTF close блокирует READY; first test FTA наблюдается по native 5m.',
              '- STB/BTS: полный key-to-sweep диапазон и его полное поглощение по SW22 p2–4; quote .5 '
              'и SL вне всей манипуляции заменяют single sweep candle proxy.',
              '- OB: реальное снятие ликвидности исходной свечой и немедленное поглощение по SW9 p2; '
              'IMB — confluence, численное body dominance не выдается за PDF. LTF OB должен пересекать HTF POI.',
              '- SW9 p3: повторный OB теперь возможен только отдельным визитом с новой LTF цепочкой; '
              'D/S остаётся свежим первым тестом. Dedup использует фактический визит.',
              '- Order Flow: ключевые structural pairs вместо последних произвольных внутренних swings; '
              'подтверждённое continuation может создать flow. Цель заморожена до её теста, без переназначения '
              'на следующем CONF (SW22 p5–6).',
              '- FTA: первая противоположная HTF POI по SW9 p16; случайный близкий LTF FVG больше не '
              'определяет обязательный выход. Технический SL находится вне wick boundary.',
              '- Дальние исторические equal pools вне текущего structural leg не считаются универсальным '
              'блокером; meaningful liquidity внутри leg, в том числе ниже SL, учитывается.',
              '- SW11 подтверждает planned risk/SL/TP и .25–2%; SW12 не добавляет обязательных RSI/volume/ATR '
              'сигналов. Численные альтернативы не выбирались по новому PnL.',
              '- Из fc61f35 уже ранее исправлены Range external POI/reclaim/retest, независимый D/S без '
              'failed-OB fallback и полный causal LTF chain; они сохранены. Новый код изолирован от canonical.', '',
              'Три прежних READY 74a6f8d ниже сопоставлены с новыми READY того же symbol/mapping '
              'и UTC-дня. Это сопоставление эпизодов, без объявления их одинаковыми opportunities.', '',
              '| 74a6f8d ID / symbol / mapping | Old READY / quote / SL / targets | Native PDF READY того же дня / quote / SL / targets |',
              '|---|---|---|']
    for old in sorted(old74_signals, key=lambda r:(r['known_at'],r['signal_id'])):
        nearby = [r for r in signals if (r['symbol'],r['htf'],r['ltf'],r['known_at'][:10]) ==
                  (old['symbol'],old['htf'],old['ltf'],old['known_at'][:10])]
        desc = '; '.join(f"{r['known_at']} / {fmt(r['entry'])} / {fmt(r['stop'])} / {r['targets']}" for r in nearby) or 'NONE'
        lines.append(f"| {old['signal_id']} / {old['symbol']} / {old['htf']}/{old['ltf']} | "
                     f"{old['known_at']} / {fmt(old['entry'])} / {fmt(old['stop'])} / {old['targets']} | {desc} |")
    lines += ['', 'Native timing correction сохранила 9 READY и их времена, но исправила clock HTF '
              'взаимодействий и свежесть FTA. Например, у ETH 2026-04-04 первая цель изменена с '
              '2055.41 (уже протестирована native 5m) на свежую 2103.1. Новые fills/CLOSED не появились. '
              'Этап зарегистрирован после исходных PDF outcomes и потому имеет явно указанную contamination.', '',
              '## Старые losses: source audit без отбора по PnL', '',
              'Проверены все 13 fc61f35 CLOSED, включая WIN, на точных old READY и entry cutoffs. '
              'FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION означает непрохождение данной зарегистрированной '
              'source реконструкции; это не доказательство невозможности всех discretionary вариантов. '
              'Отличающиеся допустимые quote/SL и исключённый 240/60 сами по себе не доказывают source false positive. '
              'Из 11 прежних LOSS: **10 false positives данной source реализации**, '
              'DOGE 240/15 `c1bc1cb68a185d4492c8b9e6` — UNCERTAIN_OR_DIFFERENT_PERMITTED_VARIANT. '
              'Из 2 WIN: один также false positive, один остаётся uncertain; положительный PnL '
              'не заменяет source proof.', '',
              '| Old ID | Symbol/mapping | Old result/PnL | Audit | Hard reasons | Other contract differences |',
              '|---|---|---|---|---|---|']
    for row in sorted(audits,key=lambda a:a['old_trade']['entry_interval_start']):
        t=row['old_trade'];hard=row['hard_source_reasons'];other=[r for r in row['reasons'] if r not in hard]
        fields=[t['signal_id'],f"{t['symbol']} {t['htf']}/{t['ltf']}",f"{t['result']} {fmt(t['net_pnl'])}",
                row['classification'],'; '.join(hard),'; '.join(other)]
        lines.append('| '+' | '.join(fmt(v) for v in fields)+' |')
    lines += ['', 'Наиболее конкретный source defect прежних Range losses: необходимо доказать существовавшую '
              'до deviation внешнюю typed POI и её фактическое взаимодействие, а SFP-only не разрешает вход '
              '(сохранённый SW10). Ниже приведены фактические кандидаты новой реконструкции.', '',
              '| Old Range loss ID | External POI candidates at old cutoff |', '|---|---|']
    range_rows=[a for a in audits if a['old_trade']['poi_type']=='RANGE_POI' and a['old_trade']['net_pnl']<0]
    for row in range_rows:
        candidates=row['snapshots']['ready_time']['range_external_poi_candidates']
        lines.append(f"| {row['old_trade']['signal_id']} | {', '.join(z['zone_id'] for z in candidates) if candidates else 'NONE'} |")
    lines += ['', 'Отсутствие flow/POI в машинной реконструкции ограничено её объявленным способом выбора '
              'ключей и зон. Нельзя считать каждый старый LOSS автоматически ошибкой. Исходные пять losses '
              'OLD7 также сохранены и независимо проверены на READY/entry; verdict WAIT не превращается в '
              'подтверждённый false positive.', '',
              '| Original OLD7 loss | Mapping | PnL | READY verdict/reasons | Entry verdict/reasons |', '|---|---|---:|---|---|']
    for row in original:
        t=row['old_trade'];a=row['snapshots']['ready_time'];b=row['snapshots']['entry_interval_start']
        fields=[t['symbol'],f"{t['htf']}/{t['ltf']}",t['net_pnl'],
                a['source_strategy_would']+': '+'; '.join(a['reasons']),b['source_strategy_would']+': '+'; '.join(b['reasons'])]
        lines.append('| '+' | '.join(fmt(v) for v in fields)+' |')
    lines += ['', '## Отдельные diagnostics и незавершённые setups', '',
              f"ANY_TF 240/60: {any_tf['READY']} READY / {any_tf['FILLED']} FILLED / {any_tf['CLOSED']} CLOSED. "
              'Не включён в primary.', '',
              f"Однопозиционный portfolio: {portfolio['funnel'].get('entries',0)} entries / "
              f"{portfolio['funnel'].get('CLOSED',0)} CLOSED, realized net {fmt(portfolio['all_closed']['NetPnL'])}, "
              f"final NAV {fmt(portfolio['final_equity'])}; это отдельный результат с budget/occupancy.", '',
              '| Последний blocker/setup outcome, strict mappings | Количество |', '|---|---:|']
    for k,v in Counter(r['latest_reason'] for r in strict).most_common():lines.append(f'| {k} | {v} |')
    lines += ['', '## QA, сохранность и границы вывода', '',
              'До текущих outcomes: 504 tests PASS, compileall PASS, Ruff E9/F PASS, mypy PASS; '
              '[pre-outcome registration](data/reports/source_pdf_native_qa_2026_10_09/pre_outcome_registration.json). '
              'Для итогового причинного/ledger/hash/resume QA см. '
              '[QA receipt](data/reports/source_pdf_native_qa_2026_10_09/delivery_receipt.json). '
              'Итоговые 504 tests / compileall / Ruff E9F / mypy PASS. Nonempty prefix SOL: '
              '67570 реальных native свечей, 1 READY, 1799 flows, 102 Range audits — exact full/prefix match '
              'и future mutation всех 4 TF PASS. Все 9 READY имеют причинные timestamps и свежие '
              'FTA/global targets по независимому native OHLC check. 93 core artifact hashes, '
              '27 implementation files и все 40 inputs проверены. Verified COMPLETE resume '
              'не изменил ни одного файла. '
              'Прежние scripts/tests/исторические артефакты сохранены; отчёт 74a6f8d '
              '[сохранён дословно](data/reports/source_cases_74a6f8d_intermediate/report.md). '
              'Canonical TP40/30/30, текущий SL и cost-adjusted BE после TP1 не изменены.', '',
              'Полный replay исчерпывает всю доступную проверенную Bybit историю для зафиксированной реализации. '
              f"Получено {case['CLOSED']} уникальных CLOSED; {'цель первых 50 достигнута' if len(primary)==50 else 'цель 50 не достигнута'}. "
              'Это фактический максимум данной policy на этих данных, а не доказанный максимум всех '
              'допустимых source вариантов. PDF задают качественные POI, варианты SL/входа, но не полный '
              'единственный вычислимый алгоритм. Все такие решения объявлены заранее. '
              'Разреженная DEVELOPMENT выборка не подтверждает edge или LIVE readiness.', '']
    output.write_text('\n'.join(lines))
    loss_audits = [r for r in audits if r['old_trade']['result']=='LOSS']
    timing_comparison = []
    for old in initial_signals:
        match = [r for r in signals if (r['symbol'],r['htf'],r['ltf'],r['known_at'],r['evidence']['htf_poi']['zone_id'],r['evidence']['ltf_poi']['zone_id']) ==
                 (old['symbol'],old['htf'],old['ltf'],old['known_at'],old['evidence']['htf_poi']['zone_id'],old['evidence']['ltf_poi']['zone_id'])]
        timing_comparison.append({'initial_signal_id':old['signal_id'], 'native_signal_ids':[r['signal_id'] for r in match],
                                  'old_interaction':old['evidence']['htf_interaction_at'],
                                  'native_interactions':[r['evidence']['htf_interaction_at'] for r in match],
                                  'old_targets':old['targets'],'native_targets':[r['targets'] for r in match]})
    comparison={'fc61f35':fc['primary'],'74a6f8d':prev['primary'],'primary_pdf':case,
                'initial_pdf_closed_htf':initial_pdf,'strict_setup_funnel':dict(funnel),'old13_audit_counts':dict(Counter(a['classification'] for a in audits)),
                'old11_loss_audit_counts':dict(Counter(a['classification'] for a in loss_audits)),
                'pdf_native_timing_comparison':timing_comparison,
                'old_range_loss_ids_without_reconstructed_external_poi':[a['old_trade']['signal_id'] for a in range_rows if not a['snapshots']['ready_time']['range_external_poi_candidates']],
                'trade_entry_allowed':False}
    write_json(root/'comparison.json',comparison)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md'))
    a=p.parse_args();render(a.input.resolve(),a.output.resolve())
