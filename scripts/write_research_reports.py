"""Render completed registered tables without selecting a parameter or exit."""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from research_support import check_baseline
from summarize_robustness_research import MAPPINGS, PERIODS

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'data/reports/robustness_research'


def read_csv(name):
    with (REPORT/name).open(newline='') as handle:return list(csv.DictReader(handle))


def number(value,percent=False):
    if value is None or value=='':return '—'
    try:return f'{float(value)*100:.2f}%' if percent else f'{float(value):.4f}'
    except (TypeError,ValueError):return str(value).replace('|',';')


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',
        *['| '+' | '.join(str(v).replace('|',';') for v in row)+' |' for row in rows]])+'\n'


def link(name):
    return f'[{name}](data/reports/robustness_research/{name})'


def write():
    lock=check_baseline(ROOT)
    inventory=json.loads((REPORT/'research_completion_inventory.json').read_text())
    generated=json.loads((REPORT/'table_generation_receipt.json').read_text())
    assert inventory['complete'] and generated['complete'],'Incomplete runs are never a final report'
    timestamp=datetime.now(ZoneInfo('Asia/Yekaterinburg')).isoformat()
    canonical=read_csv('canonical_window_metrics.csv')
    primary=[r for r in canonical if r['window'] in PERIODS and r['status']=='REPLAY_COMPLETE']
    mc=json.loads((REPORT/'monte_carlo_sample_gate.json').read_text())
    assert all(r['unique_comparable_closed']<100 for r in mc),'Sufficient samples require a fresh substantive verdict assessment'
    verdict='INSUFFICIENT SAMPLE'
    text=[f'# Frozen Strategy Engine: robustness research\n\n{verdict}. Отчёт сформирован {timestamp} (Asia/Yekaterinburg). Рыночные timestamps — UTC.\n',
        f'Canonical `{lock["baseline_commit"]}`, policy `0.4.21-causal-limit.3`, все 57 source/config SHA неизменны. '
        'TP 40/30/30, исходный SL, cost-adjusted BE после TP1, входы и risk model сохранены. '
        'Ни один исследовательский вариант не выбран. BACKTEST/SHADOW virtual only; trade_entry_allowed=false; LIVE отключён.\n',
        '## DATA\n\nИстория 2026 Bybit остаётся DEVELOPMENT: 27 974 setups → 40 READY → 7 entries → 7 CLOSED. '
        'Добавлены публичные зеркала, а не синтетические свечи. Прямые Bybit/Binance endpoints и официальные archives фактически проверены: proxy HTTP 403; '
        'GitHub/raw/public Git LFS доступны. Binance market type не подтверждён upstream endpoint, поэтому этот cohort не назван derivatives или spot. '
        'Он не объединяется с Bybit.\n']
    data=[]
    for cohort in MAPPINGS:
        manifest=json.loads((REPORT/f'{cohort}_dataset_manifest.json').read_text())
        for s in manifest['series']:
            data.append([cohort,s['symbol'],s['timeframe_minutes'],s['start'],s['end_exclusive'],s['candles'],s['sha256']])
    text += [f'34 series, {sum(int(r[5]) for r in data):,} сохранённых candles, включая производные TF; это не число независимых наблюдений. '
             'LINK/AVAX/LTC отсутствуют в новых найденных mirrors, их прежняя development-история сохранена. '
             'Binance: 628 public Git LFS Parquet objects, все size/SHA проверены; 5m bars с source_rows≠5 исключены; '
             '15/60/240m получены только из полных UTC-aligned bins. Разрывы не заполнялись. '
             'Bybit: исходные 15m и согласованные complete aggregates; 202 расхождения с отдельно сохранёнными native HTF '
             'не замаскированы и полностью перечислены в '+link('bybit_htf_independent_check.json')+'.\n',
             table(['COHORT','SYMBOL','TF MIN','START','END EXCLUSIVE','CANDLES','STORED SHA256'],data),
             'Source repositories, pinned commits, URLs, raw/logical SHA и exclusions: '+link('bybit_dataset_manifest.json')+'; '+link('binance_dataset_manifest.json')+'.\n',
             '## SAMPLE / IS-OOS\n\nПравила и chronological splits зафиксированы до внешних результатов. '
             '2026 исключён из external primary. Новая более ранняя история — retrospective frozen-rule holdout, не prospective OOS. '
             'Ни в REFERENCE, ни в VALIDATION параметры не обучались и не подбирались.\n']
    split_rows=[]
    for cohort in MAPPINGS:
        for w in json.loads((REPORT/f'{cohort}_temporal_split.json').read_text())['periods']:
            split_rows.append([cohort,w['name'],w['start'],w['end']])
    text.append(table(['COHORT','PERIOD','START','END'],split_rows))
    funnel=[]
    for cohort,mappings in MAPPINGS.items():
        for htf,ltf in mappings:
            for period in PERIODS:
                subset=[r for r in primary if (r['cohort'],int(r['htf']),int(r['ltf']),r['window'])==(cohort,htf,ltf,period)]
                sums={k:sum(int(r[k]) for r in subset) for k in ('setups','ready','entries','completed_trades','long_entries','short_entries')}
                funnel.append([cohort,f'{htf}/{ltf}',period,*[sums[k] for k in ('setups','ready','entries','completed_trades','long_entries','short_entries')],
                    number(sums['entries']/sums['ready'],True) if sums['ready'] else '—'])
    text += [table(['COHORT','MAPPING','PERIOD','OBSERVED SETUPS','READY','ENTRIES','CLOSED','LONG','SHORT','FILL RATE'],funnel),
        'Setups/READY — наблюдаемые состояния каждого replay, включая уже известные warmup states. '
        'Сумма строк не означает global unique setups. Walk replays пересекаются с primary periods и не увеличивают независимый sample. '
        'Bybit 5m отсутствует: 15/5, 60/5, 240/5 для этого нового cohort UNAVAILABLE, не нулевой результат стратегии.\n',
        '## PERFORMANCE / MAPPING\n\nКаждый mapping/period/continuous segment начинает самостоятельный virtual portfolio с 1170. '
        'PnL независимых капиталов не суммируется в один account. Все нулевые сегменты сохранены в '+link('canonical_window_metrics.csv')+'. '
        'Ниже только сегменты с entries; max DD — mark-to-market NAV, поэтому TP1→BE прибыльная сделка может иметь существенную просадку от unrealized peak.\n']
    active=[r for r in primary if int(r['entries'])]
    text.append(table(['COHORT','MAP','PERIOD/SEG','CLOSED/OPEN','WIN RATE','PF','EXPECTANCY','AVG R','MEDIAN R','MAX DD','NET CLOSED PNL','EQUITY PNL'],
        [[r['cohort'],f"{r['htf']}/{r['ltf']}",f"{r['window']}/{r['segment']}",f"{r['completed_trades']}/{r['open_trades']}",
          number(r['win_rate'],True),number(r['profit_factor']),number(r['expectancy']),number(r['average_R']),number(r['median_R']),
          number(r['max_drawdown_fraction'],True),number(r['net_pnl']),number(r['equity_pnl'])] for r in active]))
    text += ['Полные costs, gross edge, payoff, drawdown duration, losing streak, union exposure, holding time, monthly frequency, '
             'unrealized/realized account PnL — в CSV. Gross profit/loss в trade_statistics означает положительные/отрицательные **net** исходы; '
             'gross_edge_before_fees выделен отдельно. Fees as % gross edge не определён при неположительном gross edge. '
             'Exposure от начала entry bar является upper bound, holding от известного entry close — lower bound для intrabar fills. '
             'В конце окна/gap open trades цензурируются, не закрываются искусственно.\n',
        '## LONG/SHORT / SYMBOL / REGIME\n\n'+link('performance_groups.csv')+' содержит каждый symbol, оба направления и causal entry regime/volatility buckets, '
        'включая группы с нулевым sample. Subgroup DD — realized contribution, не fictitious separate full account NAV. '
        'Классификация использует только 31 preceding complete consecutive UTC daily closes: 30-day return ±10%, '
        'daily σ <2% / 2–4% / >4%. Недостаток history/gaps → UNKNOWN. Derived 1D — research label, не новый strategy input. '
        'Покрытие режимов по календарю: '+link('causal_regime_calendar_coverage.csv')+'. Наличие рыночного режима не означает достаточное число сделок в нём.\n',
        '## READY → FILL\n\nDevelopment 33 unfilled: 17 OB first test consumed before limit touch, 11 isolated margin, '
        '4 first-terminal target evidence withdrawals, 1 data-end censor. Это exclusive first-outcome ledger; '
        '8 ever-observed target withdrawals из прежнего audit не добавляются как ещё 8 независимых отказов. '
        'На первом OB touch цена могла не дойти до executable quote; hindsight fill не создаётся. '
        'При cost-aware risk 2% и leverage 3x узкий stop может требовать margin больше account equity. '
        'Fresh target может быть реально затронут до limit fill и поэтому withdrawn. '
        'Сохраняются exact quote/SL/target audits, и эти естественные outcomes не исправлялись ради входов. '
        'Полный ledger '+link('development_fill_frequency.json')+'; external groups '+link('fill_frequency_groups.csv')+'.\n',
        '## WALK-FORWARD\n\n90 calendar days reference → 90 evaluation, step 90; final partial retained. '
        '18 Bybit windows/mapping и 21 Binance windows/mapping, вместе с period runs и всеми gap segments. '
        'Insufficient warmup/no execution segments присутствуют явно. Все window fingerprints/SHA проверены: '+link('research_completion_inventory.json')+'. '
        'Анализ использует до 90 preceding days context при минимум 576 LTF warmup bars; это расширенный input context, '
        'а не новое значение trading threshold. Сравнение с прежним development replay на ином количестве warmup bars не является matched parameter test.\n',
        '## COST / PARAMETER SENSITIVITY\n\nЗначения перечислены до результатов в [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md). '
        'Structural one-at-a-time: только фиксированный Binance60/5 VALIDATION. Costs/risk/reentry: все 9 доступных cohort/mappings, '
        'VALIDATION/HOLDOUT и walk windows. Base fee .0006/slippage .0002, stress1.5x/2x. '
        'Initial READY Score=100; 75→80 — reentry-only, не новый фильтр source setup. '
        'Свежесть BODY/exclusive wick относится только к POI, original OB touch semantics неизменны. '
        'Все результаты '+link('registered_sensitivity_metrics.csv')+'. Никакого best-value selection.\n']
    structural=[r for r in read_csv('registered_sensitivity_metrics.csv') if r['category']=='structural_sensitivity']
    text.append(table(['VARIANT','SETUPS','READY','ENTRIES','CLOSED','NET PNL','MAX DD'],
        [[r['experiment'],r['setups'],r['ready'],r['entries'],r['completed_trades'],number(r['net_pnl']),number(r['max_drawdown_fraction'],True)] for r in structural]))
    qualification=json.loads((REPORT/'target_availability_qualification.json').read_text())
    text.append(table(['MIN TARGETS','QUALIFIED OB CASES','ENOUGH DISTINCT OPPOSING POIS','MEANING'],
        [[r['minimum_targets'],r['qualified_ob_cases'],r['qualified_ob_cases_with_sufficient_distinct_opposing_pois'],'QUALIFICATION ONLY; NOT READY/ENTRIES'] for r in qualification]))
    text += ['Fixed three-TP contract исключает честное execution сравнение с двумя/четырьмя targets без нового exit model. '
             'Поэтому этот counterfactual не выдаётся за сделки и не hardcodes READY.\n',
        '## CAUSALITY / EXECUTION\n\n'+link('external_real_causality_parity.json')+': actual canonical READY reproduced; '
        'full/prefix/future-mutated/repeat/SHADOW и ускоренные варианты дают одинаковые 633 прошлых signals. '
        'BACKTEST/SHADOW одинаковы по реальным trade/decisions/NAV. '+link('research_adapter_equivalence.json')+': '
        'optimized/full-reader common coverage совпадает; immutable source/config guard PASS. '
        'Все actual fills/availability/partial fees/accounting/entry-bar conservative semantics проверены в '+link('external_execution_audit.json')+'. '
        'BASE_VERIFY cost replay и exit A точно воспроизводят saved canonical trades/journal/equity для каждого case. '
        'Exit paired real entries дополнительно проверяют 7 variants BACKTEST/SHADOW и nonvacuous future-prefix там, где actual TP1 был.\n',
        '## LIMITATIONS / VERDICT\n\n'+verdict+'. До ≥100 comparable closed trades/mapping нет положительного edge verdict. '
        'Sharpe/Sortino/Calmar withheld при <90 full daily returns или <30 closed trades; 365-day UTC sampling, RF=0. '
        'Monte Carlo sample gates: '+link('monte_carlo_sample_gate.json')+'. Пересекающиеся walk windows и отдельные mapping/cohorts '
        'не объединены для достижения порога.\n',
        'Public mirror integrity подтверждена source object SHA, но это не independent exchange authenticity certification. '
        'Binance instrument ambiguity и Bybit native HTF discrepancies ограничивают переносимость вывода на Bybit execution. '
        'Baseline содержит явно обозначенные BACKTEST_PARAMETER POI/displacement/target normalizations, '
        'а не source-approved геометрию всех блоков. Прежние source audits сохранены в HISTORICAL_PIPELINE_FINAL_REPORT.md. '
        'Fee/slippage model сохранён; funding, order-book queue и реальные fills этой virtual проверкой не измерены. '
        'Мало закрытых сделок и post-TP1 episodes: нельзя отделить устойчивый edge от случайности, '
        'выбрать profitable symbol/параметр или менять baseline по этим данным. '
        'Практическая жизнеспособность не доказана; LIVE запрещён.\n',
        '## TESTS / GIT\n\nКоманды и результаты '+link('stable_stage_checks.json')+'. '
        'Frozen rollback tag `research-baseline-2026-10-08` → starting canonical commit. '
        'Repository `mdiminchuk208-arch/-`, branch `main`; commits опубликованы обычным push без force. '
        'Итоговый commit и content-equivalence ZIP receipt сообщаются после публикации, чтобы не создавать self-referential commit hash.\n']
    (ROOT/'ROBUSTNESS_RESEARCH_REPORT.md').write_text('\n'.join(text))
    write_exit(timestamp)
    print('Complete research reports generated; verdict',verdict)


def write_exit(timestamp):
    rows=read_csv('exit_management_metrics.csv')
    active=[r for r in rows if int(r['entries'])]
    text=[f'# Controlled exit management research\n\nINSUFFICIENT SAMPLE. {timestamp} (Asia/Yekaterinburg); market timestamps UTC.\n',
        'Canonical TP1=40%, TP2=30%, TP3=30%; исходный SL и cost-adjusted breakeven после TP1 **не менялись**. '
        'Эксперименты зарегистрированы в [EXIT_RESEARCH_PROTOCOL.md](EXIT_RESEARCH_PROTOCOL.md), commit `c2fdce0`, до alternative exit runs. '
        'Ни один кандидат не выбран по текущему PnL.\n',
        '## Dataset and pairing\n\nПрежние Bybit2026 7 closed trades — DEVELOPMENT, 6 независимых mapping portfolios. '
        'New cohorts сохраняют frozen REFERENCE/VALIDATION/retrospective HOLDOUT periods. '
        'Часть их canonical outcomes уже была просмотрена до exit protocol; не называем весь этот dataset untouched exit validation. '
        'Отдельно заранее зарезервирован BTC-only Binance60/5 2019Q4: 395 observed setups → 0 READY → 0 entries. '
        'Reserve сохранён, но не даёт exit observations. Это calendar-selected retrospective reserve, не prospective OOS.\n',
        'Full portfolio variants получают одинаковые incoming frozen signals/entry/risk rules. '
        'Exit cash/occupancy может изменить будущие admissions; это feedback, не изменение входов. '
        'Paired actual-entry replay использует actual earlier READY, исходные entry equity/quote/quantity/risk и original inherited admission. '
        'Реальные сигналы не hardcoded и новые сделки не выдуманы. '
        'Paired DD — индивидуальный trade NAV; full portfolio DD — отдельный 1170 account, эти величины не объединяются.\n',
        '## Fixed variants\n\nA40/30/30, B30/30/40, C25/25/50, D25/35/40 держат original immediate cost-adjusted BE после TP1. '
        'Отдельные A timing variants: later favourable completed LTF close → next-bar BE; '
        'original SL through TP1, BE after TP2; structural trailing using newly formed and SOURCE_CONSERVATIVE-confirmed protective LTF swing after TP1. '
        'Structural rule — declared experimental normalization, не source-approved replacement. '
        'Confirmation/ratchet исполняется с next bar, никакого retroactive stop на свече подтверждения. '
        'Same-bar OHLC ambiguity сохраняет pessimistic stop-first priority. Fractional exits оплачивают costs пропорционально original quantity.\n',
        '## Results\n\nВсе active independent portfolio cases перечислены отдельно. TRADES означает CLOSED; '
        'open/censored entries и TP rates приведены в полном CSV. Значения PnL/AvgWin/AvgLoss/expectancy — USDT; '
        'max DD — full account mark-to-market NAV. Undefined PF/mean при отсутствии denominator отображается «—», не infinity. '
        'Zero-entry cases присутствуют для всех 7 variants в '+link('exit_management_metrics.csv')+'.\n']
    groups=defaultdict(list)
    for r in active:groups[(r['study'],r['case'])].append(r)
    for (study,case),cases in sorted(groups.items()):
        role=cases[0]['role'];text.append(f'### {study} / {case} — {role}\n')
        text.append(table(['EXIT VARIANT','TRADES','WIN RATE','AVG WIN','AVG LOSS','EXPECTANCY','PF','MAX DD','NET PNL'],
            [[r['variant'],r['completed_trades'],number(r['win_rate'],True),number(r['average_win']),number(r['average_loss']),
              number(r['expectancy']),number(r['profit_factor']),number(r['max_drawdown_fraction'],True),number(r['net_pnl'])] for r in cases]))
    follow=read_csv('post_be_follow.csv')
    text += ['## TP / BE / costs\n\n'+link('exit_management_metrics.csv')+' содержит mean/median R, losing streak, '
        'TP1/2/3 hit rate, post-TP1 BE exits, fees/slippage, realized and equity PnL. '
        'Hit rate denominator — entries; censored open trades не объявлены неудачами. '
        '«После BE потом дошло до target» — price path counterfactual, не доказанный profit. '
        'Exit-bar wick chronology неизвестна: только close доказывает движение после intrabar BE; subsequent bars идут stop-first. '
        '30-day follow clipped contiguous original endpoint; right-censoring и ambiguity сохранены.\n']
    text.append(table(['STUDY','SIGNAL','LATER TP2 TOUCH','LATER TP3 TOUCH','TP2 BEFORE ORIGINAL SL','TP3 BEFORE ORIGINAL SL','RIGHT CENSORED','AMBIGUOUS TP2/TP3'],
        [[r['study'],r['signal_id'],r['later_tp2_price_touch'],r['later_tp3_price_touch'],r['tp2_before_original_sl_stop_first'],
          r['tp3_before_original_sl_stop_first'],r['follow_right_censored'],f"{r['tp2_same_bar_order_ambiguous']}/{r['tp3_same_bar_order_ambiguous']}"] for r in follow]))
    text += [link('paired_exit_actual_entries.csv')+' сохраняет цены/количество/risk/costs/fills для matched experiments. '
        'Case JSON `paired_actual_entries.json` проверяет real BACKTEST/SHADOW, `exit_real_causality.json` — '
        'future-prefix для actual TP1 case либо явно NO_CANONICAL_TP1_EVENT; vacuous check не называется доказательством exit path. '\
        'Baseline A exact trades/decisions/NAV подтверждён на всех saved canonical cases.\n',
        '## Answers\n\n1. **Является ли 40/30/30 экономически слабым?** По имеющейся выборке это не установлено. '
        'Веса сами по себе не определяют expectancy: важны реальные target distances, probabilities, remaining-stop outcomes и costs. '
        'Отрицательная observed expectancy малых cases описывает dataset, а не доказывает intrinsically weak allocation.\n\n'
        '2. **Основная проблема win rate или маленький AvgWin?** В development оба фактора присутствуют: '
        '5 SL losses и только 2 TP1→BE winners среди 7 closed replay instances. '
        'Но это разные mapping portfolios; pooled PnL и устойчивый global win rate не утверждаются. '
        'Внутри 240/60 N=2: win rate 50%, AvgWin11.1659 против AvgLoss23.6233; observed expectancy−6.2287. '
        'Descriptive break-even win rate ≈67.91%, но две сделки не оценивают истинную вероятность.\n\n'
        '3. **Слишком рано ли BE?** Недостаточно post-TP1 episodes и незавершённых 30-day observations. '
        'Таблица later target touches не превращается в profit без original SL/cost/ordering checks. '
        'Более прибыльный structural outcome одной уже использованной сделки не доказывает, что early BE ошибочен.\n\n'
        '4. **Какой вариант устойчивее OOS?** Никакой не подтверждён достаточным untouched sample. '
        'Main retrospective holdout partly unblinded для exit research; separate preregistered reserve имеет 0 entries. '
        'В случаях SL до TP1 все 7 variants закономерно совпадают и не дают сравнительного exit evidence.\n\n'
        '5. **Достаточна ли выборка для изменения canonical?** Нет: gate ≥100 comparable OOS closed trades/mapping и '
        '≥30 post-TP1 events не достигнут. Требуется отдельный ещё не использованный период с достаточными actual admitted trades '
        'и подтверждением costs/causality. До этого baseline40/30/30 остаётся неизменным.\n',
        '## Safety and publication\n\ntrade_entry_allowed=false; LIVE/private API/credentials/real orders отключены. '
        'No entry rule changes; no optimization or candidate selection. Canonical rollback остаётся доступен. '
        'Полные tests/lint/mypy/guards — '+link('stable_stage_checks.json')+'. '
        'Reports/scripts/diagnostics/history сохраняются в GitHub main; ZIP content correspondence проверяется после final push.\n']
    (ROOT/'EXIT_MANAGEMENT_RESEARCH_REPORT.md').write_text('\n'.join(text))


if __name__=='__main__':write()
