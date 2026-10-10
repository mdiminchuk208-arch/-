"""Render frozen V2 measurements, robustness and retained negative findings."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from crypto_bot.research.v2_common import (
    BASE,
    BASELINE,
    OUT,
    Row,
    digest,
    metrics,
    read_jsonl,
    write_csv,
    write_json,
)
from crypto_bot.research.v2_rules import SCOPES, scope_mask

ZONE=ZoneInfo('Asia/Yekaterinburg')


def load_csv(path: Path) -> list[Row]:
    with path.open() as f:return list(csv.DictReader(f))


def number(value: object, digits: int = 5) -> str:
    if value in (None,''):return 'N/A'
    try:return f'{float(value):.{digits}f}'
    except (ValueError,TypeError):return str(value)


def table(fields: list[str],rows: list[Row],digits: int = 5) -> str:
    result=['| '+' | '.join(fields)+' |','|'+'|'.join('---' for _ in fields)+'|']
    for row in rows:
        result.append('| '+' | '.join(number(row.get(k),digits).replace('|','/') for k in fields)+' |')
    return '\n'.join(result)


def show_metrics(names: list[str],rows: list[Row]) -> str:
    items=[]
    for r in rows:
        items.append({**r,'WR %':100*float(r['WR']) if r.get('WR') not in (None,'') else None,
                      'CI 95%':f"[{100*float(r['WR_CI_low']):.2f}; {100*float(r['WR_CI_high']):.2f}]" if r.get('WR_CI_low') not in (None,'') else 'N/A'})
    return table(names,items)


def describe_tree(model: Row,threshold: float) -> list[Row]:
    result=[]
    def visit(node: int,path: list[Row]) -> None:
        left=model['children_left'][node]
        if left<0:
            result.append({'node':node,'admitted':model['probability_WIN'][node]>=threshold,
                'TRAIN_WIN_probability':model['probability_WIN'][node],'TRAIN_leaf_samples':model['node_samples'][node],
                'conditions':path})
            return
        condition={'feature':model['features'][model['feature'][node]],'threshold':model['threshold'][node]}
        visit(left,[*path,{**condition,'operator':'<='}])
        visit(model['children_right'][node],[*path,{**condition,'operator':'>'}])
    visit(0,[])
    return result


def main() -> None:
    summary=json.loads((OUT/'TEST_summary.json').read_text())
    rules=json.loads((OUT/'strategy_v2_final_rules.json').read_text())
    split=json.loads((OUT/'split.json').read_text())
    features=list(read_jsonl(OUT/'features.jsonl.gz'))
    labels={r['signal_id']:r for part in ['TRAIN','VALIDATION','TEST'] for r in read_jsonl(OUT/f'labels_{part}.jsonl.gz')}
    closed=[r for r in features if r['status']=='CLOSED']
    scopes=[];representatives=[]
    for split_name in ['FULL_CLOSED_DESCRIPTIVE','TRAIN','VALIDATION','TEST']:
        x=[r for r in closed if split_name=='FULL_CLOSED_DESCRIPTIVE' or (r['split']==split_name and r['label_eligible'])]
        for scope in SCOPES:
            mask=scope_mask(x,scope)
            scopes.append({'split':split_name,'scope':scope,**metrics([labels[r['signal_id']] for r,k in zip(x,mask) if k])})
        for path in sorted({r['path_id'] for r in closed}):
            representatives.append({'split':split_name,'path_id':path,
                                    **metrics([labels[r['signal_id']] for r in x if r['path_id']==path])})
    write_csv(OUT/'strategy_v2_core_confluence_union_metrics.csv',scopes)
    write_csv(OUT/'strategy_v2_representative_path_metrics.csv',representatives)
    # Old standalone path ledgers are reference only, never additional V2 cases.
    standalone=[]
    for path in ['BREAKER_CONSERVATIVE_STOP','RANGE_AGGRESSIVE_EXTERNAL_POI','SFP_BOS_POI']:
        x=[r for r in read_jsonl(BASE/f'cohorts/{path}/CANCEL_SOURCE_POI_INVALIDATION/cases.jsonl.gz') if r['status']=='CLOSED']
        standalone.append({'path_id':path,'scope':'ORIGINAL_STANDALONE_PATH_REFERENCE_NOT_UNION',**metrics(x)})
    write_csv(OUT/'strategy_v2_old_standalone_reference.csv',standalone)
    analysis=load_csv(OUT/'strategy_v2_win_loss_feature_analysis.csv')
    important={'friction_R','net_target_R','gross_target_R','liquidity_swept_count','macro_flow_aligned',
               'sweep_ATR','displacement_ATR','zone_age_bars','structure_age_bars','PD_allowed','OTE',
               'first_test','entry_POI_kind','HTF','physical_family_count','strong_range_context'}
    lifts=[]
    for scope in ['ALL','CORE_A','CORE_B','CORE_C']:
        floor=30 if scope=='CORE_B' else 100 if scope in ['CORE_A','CORE_C'] else 200
        for field in sorted(important):
            options=[r for r in analysis if r['scope']==scope and r['feature']==field and
                     int(r['CLOSED'])>=floor and r['WR_lift_absolute'] and r['bin']!='MISSING']
            if options:
                best=max(options,key=lambda r:(float(r['WR_lift_absolute']),int(r['CLOSED'])))
                lifts.append({**best,'minimum_descriptive_sample':floor,
                              'claim':'TRAIN_DESCRIPTIVE_ONLY; NOT_INDEPENDENT_VALIDATION'})
    write_csv(OUT/'strategy_v2_strongest_TRAIN_feature_lifts.csv',lifts)
    oos=load_csv(OUT/'strategy_v2_oos_results.csv');stress=load_csv(OUT/'strategy_v2_oos_friction_stress.csv')
    breakdown=load_csv(OUT/'strategy_v2_oos_breakdowns.csv');stability=load_csv(OUT/'strategy_v2_frozen_period_stability.csv')
    validation=load_csv(OUT/'strategy_v2_validation_results.csv')
    p=summary['primary_TEST_metrics'];meta=next(r for r in oos if r['candidate_name']=='BEST_META')
    admitted_leaves=[]
    for model in rules['models']:
        if model['model_id']==rules['final_candidates']['BEST_META']['rule']['model_id']:
            admitted_leaves=describe_tree(model,rules['final_candidates']['BEST_META']['rule']['threshold'])
    write_json(OUT/'strategy_v2_frozen_tree_explanation.json',{
        'model_id':rules['final_candidates']['BEST_META']['rule']['model_id'],
        'threshold':rules['final_candidates']['BEST_META']['rule']['threshold'],'leaves':admitted_leaves,
        'rules_changed':False,'explanation_of_already_frozen_JSON_only':True})
    plot_names=['Baseline','A+ / TOP','Primary SFP','Frozen tree']
    plotted=[summary['baseline_TEST_metrics'],next(r for r in oos if r['candidate_name']=='A_PLUS'),p,meta]
    fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    xs=list(range(4));wr=[100*float(r['WR']) for r in plotted]
    low=[wr[i]-100*float(r['WR_CI_low']) for i,r in enumerate(plotted)]
    high=[100*float(r['WR_CI_high'])-wr[i] for i,r in enumerate(plotted)]
    axes[0].errorbar(xs,wr,yerr=[low,high],fmt='o',capsize=5,color='#24557b')
    axes[0].axhline(70,color='#b13b31',ls='--',label='70% target')
    axes[0].set(xticks=xs,xticklabels=plot_names,ylabel='Win rate (%) / Wilson 95% CI',ylim=(0,85))
    axes[0].legend();axes[0].grid(axis='y',alpha=.2)
    pf=[float(r['PF']) for r in plotted]
    axes[1].bar(xs,pf,color=['#879cae','#537d98','#38658c','#86a3ab'])
    axes[1].axhline(1.5,color='#b13b31',ls='--',label='PF 1.5 target')
    axes[1].set(xticks=xs,xticklabels=plot_names,ylabel='Profit factor after fees/slippage',ylim=(0,1.7))
    axes[1].legend();axes[1].grid(axis='y',alpha=.2)
    fig.suptitle('V2 chronological development TEST — rules frozen before one evaluation')
    fig.savefig(OUT/'strategy_v2_test_metrics.png',dpi=180)
    fig.savefig(OUT/'strategy_v2_test_metrics.svg',metadata={'Date':None})
    plt.close(fig)
    def local(t: str) -> str:
        from datetime import datetime
        return datetime.fromisoformat(t).astimezone(ZONE).isoformat()
    train_attempts=json.loads((OUT/'train_search_receipt.json').read_text())['attempt_count']
    val_attempts=json.loads((OUT/'validation_selection_receipt.json').read_text())['validation_attempts']
    report=[]
    report.append('# Strategy V2 — High Precision: измеренный результат\n')
    report.append('**Цель не подтверждена.** Все 16 333 CLOSED использованы в полной таблице; '
        'TRAIN/VALIDATION поиск завершён, модели заморожены, TEST открыт ровно один раз. '
        f'Лучший заранее замороженный meta-кандидат по точности: WR **{100*float(meta["WR"]):.2f}%**, '
        f'PF **{float(meta["PF"]):.4f}**, expectancy **{float(meta["Expectancy"]):+.5f} USDT**, '
        f'Net PnL **{float(meta["NetPnL"]):+.5f} USDT**, **{meta["CLOSED"]} CLOSED**. '
        f'Недостаёт **{100*(.70-float(meta["WR"])):.2f} п.п.** до 70%; PF существенно ниже 1.5. '
        'Это не замена основного кандидата после TEST: primary выбран на VALIDATION и остаётся прежним.\n')
    report.append(f'Frozen primary `{rules["primary_name"]}`: WR **{100*p["WR"]:.2f}%**, '
        f'PF **{p["PF"]:.4f}**, expectancy **{p["Expectancy"]:+.5f}**, '
        f'AvgR **{p["AvgR"]:+.6f}**, Net **{p["NetPnL"]:+.5f}** на {p["CLOSED"]} CLOSED. '
        'Положительный результат VALIDATION не сохранился.\n')
    report.append('## Baseline и происхождение TEST\n')
    report.append(f'Baseline `{BASELINE}` сохранён побайтно: QA проверила **16 851 Git blobs**, '
        'включая все старые source, tests, scripts, reports и исторические данные. '
        'Рабочая ветка `strategy-v2-70wr-research`; main не изменён и автоматического merge нет. '
        'Canonical TP 40/30/30, SL и cost-adjusted BE после TP1 не менялись. '
        'V2 фильтрует уже зафиксированные source-case входы и source-case выходы, '
        'не переносит эту политику в canonical engine. `trade_entry_allowed=false`.\n')
    report.append('Вся история Bybit 2026 уже изучалась до V2, включая общий ledger и агрегаты. '
        'Поэтому этот TEST — отложенная хронологическая проверка для V2 внутри DEVELOPMENT, '
        'а не новая нетронутая история и не prospective OOS. Даже успешные численные оценки '
        'не могли бы устранить это ограничение. Файлы `*_oos_*` именованы по заданию; '
        'каждая строка содержит явную provenance-метку.\n')
    report.append(show_metrics(['CLOSED','WIN','LOSS','WR %','PF','Expectancy','AvgR','GrossPnL','fees','slippage','NetPnL'],
                               [summary['baseline_all_16333_CLOSED']])+'\n')
    report.append('Raw Gross PnL **+11 576.96193 USDT** уничтожается расходами: '
        'fees **91 180.15562**, slippage **30 393.38567**. '
        'Это сумма независимых кейсов с reference equity $1170 и фиксированным риском $23.4; '
        'не доходность одного счёта. Объёмы, margin occupancy, funding и рыночная ёмкость '
        'здесь не превращены в доказанный portfolio результат. OHLC остаётся пессимистической моделью.\n')
    report.append('## Chronological split и предотвращение leakage\n')
    report.append(f'По original READY и physical ID: 9 799 / 3 267 / 3 267 CLOSED; '
        f'VALIDATION начинается **{local(split["validation_first_READY"])}**, '
        f'TEST — **{local(split["test_first_READY"])}**. Timestamp ties не разделяются. '
        '103 TRAIN и 54 VALIDATION сделки имеют exit после следующего cutoff и исключены '
        'из обучения/выбора. Они сохранены в полной таблице. После purge: '
        '**9 696 / 3 213 / 3 267**. Все 18 OPEN принадлежат TEST и остались censored, '
        'без принудительного закрытия. Прогнозы рассчитаны и для них.\n')
    report.append('Каждый predictor известен на READY: native ATR14 Wilder использует только завершённые '
        'native свечи; макро HTF flow отделён от контртрендового SFP reaction flow. '
        'Время READY→fill и actual fill candle deviation находятся только в диагностике. '
        'Имена монет, mapping, календарные даты, session/hour/weekday и trade IDs не входят '
        'в правила или design matrix. Missing остаётся None в таблице; median imputation '
        'meta-моделей обучен исключительно на TRAIN.\n')
    report.append('Ожидаемые затраты вычислены из original entry, исходного SL, predeclared targets '
        'и allocations (включая Range 80/20), fee=0.0006 и slippage=0.0002 на сторону. '
        '`gross_target_R = quantity * weighted_quote_target_payout / planned_risk`; '
        '`friction_R = (expected_fee + expected_slippage) / planned_risk`; '
        '`net_target_R = gross_target_R - friction_R`. Price-distance `target_SL_ratio` хранится '
        'отдельно. `*_pct` — доли цены (для процентов умножить на 100). '
        'Realized costs не использованы как predictors.\n')
    report.append('## TRAIN: признаки, CORE A/B/C и confluence\n')
    report.append(f'Заранее зарегистрированы {train_attempts:,} TRAIN попыток (включая нулевые и провалы), '
        f'затем {val_attempts} VALIDATION оценок; TEST не участвовал в этом поиске. '
        'Имеются полные WIN/LOSS квантильные distributions и по каждому признаку/bin '
        'sample/WIN/LOSS/WR/PF/expectancy/AvgR/net/lift. Число сравнений велико; '
        'TRAIN lift — описание, не статистическое доказательство нового edge.\n')
    report.append(show_metrics(['scope','CLOSED','WIN','LOSS','WR %','PF','Expectancy','AvgR','NetPnL'],
                               [r for r in scopes if r['split']=='TRAIN'])+'\n')
    report.append('Различайте старые standalone path cohorts и один union: standalone выбирает '
        'свою заявку после своего READY; V2 сохраняет только самый ранний исходный union quote. '
        'Принадлежность CORE считается только по qualified path, уже известному к этому READY. '
        'Нельзя переносить альтернативное исполнение или более позднее подтверждение в прошлую сделку.\n')
    report.append(show_metrics(['path_id','CLOSED','WR %','PF','Expectancy','NetPnL'],standalone)+'\n')
    report.append('Во всём original physical union: CORE A membership **1605**, CORE B **325**, '
        'CORE C **9994** CLOSED. Первичный representative path Breaker **1527**, '
        'Range aggressive **320**, SFP BOS **8634**. Отличие от старых 1920/734 — '
        'causal representative selection и дедупликация, а не утраченные строки истории.\n')
    report.append('Breaker+SFP до исходного READY найдено лишь **23** CLOSED opportunities; '
        'Breaker+Range family — **5**. Это реальные пересечения одного physical ID; '
        'суммировать standalone WR или зачислять будущий Breaker к раннему SFP запрещено. '
        'Recent Range deviation context — отдельный причинный контекст, не вторая physical setup-family. '
        'CORE B и редкие confluence не достигают TRAIN floor 600; они подробно исследованы '
        'описательно, но не выбраны в финал посредством ослабления sample gate.\n')
    for scope in ['ALL','CORE_A','CORE_B','CORE_C']:
        relevant=[r for r in lifts if r['scope']==scope]
        relevant.sort(key=lambda r:float(r['WR_lift_absolute']),reverse=True)
        report.append(f'### {scope}: наиболее сильные TRAIN bins\n')
        report.append(table(['feature','bin','CLOSED','WR','PF','Expectancy','AvgR','WR_lift_absolute'],relevant[:8])+'\n')
    report.append('Fresh first-test, native touch, flow alignment и swept pools проверены как признаки, '
        'а не предположены источником edge. Постоянный first-test внутри конкретного пути не может '
        'различать WIN и LOSS. Столбцы unmatched swept roles остаются неизвестной классификацией; '
        'IDs разных TF не смешиваются для external/internal count. Полный TRAIN analysis показывает '
        'и отрицательные lift.\n')
    report.append('Наиболее высокий precision meta-фильтра объясняется **короткими целями и низкой '
        'предварительной friction**, а не несколькими семействами. Это увеличивает WR, но уменьшает '
        'прибыль на WIN. В TEST frozen tree AvgWin **11.10726**, AvgLoss **23.15705**, '
        'Payoff **0.47965**; наблюдаемый break-even WR около **67.58%**. '
        'WR 67.68% оставляет почти нулевой запас после расходов.\n')
    report.append('## Замороженные финальные правила\n')
    report.append('Primary: qualified **SFP_BOS_POI membership к original READY**, '
        '**friction_R <= 0.15**, **sweep_ATR >= 0.1**. Три основных условия. '
        'ENTRY/SL/targets/exits неизменны.\n')
    report.append('Meta: TRAIN-only `TREE_D3_L200`, threshold probability **0.55**, максимум '
        '7 внутренних узлов / 3 условий на путь. Допущен только один сохранённый leaf:\n')
    for leaf in admitted_leaves:
        if leaf['admitted']:
            report.append('```json\n'+json.dumps(leaf,indent=2)+'\n```\n')
    report.append('Оставшиеся листья, logistic coefficients, TRAIN medians/means/stds и все 7 моделей '
        'сохранены в JSON. Никакого refit на VALIDATION или TEST нет.\n')
    score_config=json.loads((OUT/'strategy_v2_confluence_score.json').read_text())
    report.append('Семь компонентов confluence score: Breaker; strong Range context; macro alignment; '
        '2+ swept pools; fresh first-test; net_target_R>=1; friction_R<=0.15. '
        f'VALIDATION выбрала `{score_config["chosen_profile"]}`: веса '
        f'`{score_config["chosen_weights"]}`. A threshold **1**, A+ **7**, TOP **7**. '
        'A+/TOP совпали: данных для оправданной более строгой TOP границы не оказалось. '
        'Название tier не означает доказанное A+ качество. Веса — эксперимент, не SOURCE_RULE.\n')
    report.append('Правила и 16 425 label-free predictions зафиксированы в commit '
        '**e569909** до TEST; TEST-open receipt ссылается на полный SHA commit. '
        'Четыре уникальные политики под пятью требуемыми названиями; результаты A+/TOP '
        'не суммируются. Primary не заменён деревом по более приятному TEST результату.\n')
    report.append('## VALIDATION → единственный TEST\n')
    selected_validation=[{**r,'candidate_name':name} for name,candidate in rules['final_candidates'].items()
                         for r in validation if r['candidate_id']==candidate['candidate_id']]
    report.append(show_metrics(['candidate_name','CLOSED','WIN','LOSS','WR %','PF','Expectancy','AvgR','NetPnL'],
                               selected_validation)+'\n')
    report.append(show_metrics(['candidate_name','CLOSED','WIN','LOSS','BE','WR %','CI 95%','PF','Expectancy','AvgR','NetPnL'],oos)+'\n')
    report.append(table(['candidate_name','GrossPnL','fees','slippage','MaxDrawdown_case_sum','AvgWin','AvgLoss',
                         'Payoff','Average_holding_seconds','trades_per_month','censored_OPEN_admitted'],oos)+'\n')
    report.append('Drawdown — realized case-sum в exit chronology, а не NAV shared account. '
        'Trades/month делит число CLOSED по READY-выборке на общий интервал TEST **1.60529 месяца**; '
        'не предполагает одновременную реализуемость всех позиций. Wilson CI имеет номинальные '
        'binomial 95%; корреляция пересекающихся сделок/монет может делать его оптимистичным. '
        'Нижняя граница tree CI 62.16% выше baseline, но точечный WR ниже цели и PF не проходит.\n')
    report.append('![TEST WR и PF](data/reports/strategy_v2_2026_10_10/strategy_v2_test_metrics.png)\n')
    report.append('## Устойчивость без повторного выбора\n')
    report.append('Ниже primary и заранее замороженный meta. Полные LONG/SHORT, symbol, mapping, '
        'HTF/LTF, family, month, weekday и session сохранены для каждого кандидата, включая нулевые '
        'и убыточные группы. Leave-one-group-out — диагностика, не удаление монет из rules.\n')
    for dimension in ['direction','symbol','mapping','month','setup_family']:
        report.append(f'### TEST: {dimension}\n')
        report.append(show_metrics(['candidate_name','value','CLOSED','WIN','LOSS','WR %','PF','Expectancy','NetPnL'],
            [r for r in breakdown if r['dimension']==dimension and r['candidate_name'] in ['BEST_DETERMINISTIC','BEST_META']])+'\n')
    report.append('### TRAIN/VALIDATION chronological stability\n')
    report.append(show_metrics(['candidate_name','split','period','CLOSED','WR %','PF','Expectancy','NetPnL'],
        [r for r in stability if r['candidate_name'] in ['BEST_DETERMINISTIC','BEST_META']])+'\n')
    report.append('### Friction stress: те же frozen trades\n')
    report.append(show_metrics(['candidate_name','cost_multiplier','CLOSED','WR %','PF','Expectancy','AvgR','NetPnL'],
        [r for r in stress if r['candidate_name'] in ['BEST_DETERMINISTIC','BEST_META']])+'\n')
    report.append('При 1.5x/2x friction не меняются quote, qty, stop, target или fill chronology; '
        'это paired ledger stress, не новая execution simulation. Слабый плюс дерева не переживает '
        'увеличение расходов. Убыточные LONG/SHORT/месяцы/монеты показаны и не вырезаны. '
        'Ни один кандидат не получает verdict устойчивой стратегии.\n')
    report.append('## QA и воспроизведение\n')
    report.append('**556 tests PASS**, compileall PASS, mypy **50 source files PASS**. Ruff: '
        '**555 inherited diagnostics, 0 новых**, полный список точно равен baseline. '
        'Независимая QA: 40 SHA / 993 575 native candles; 16 851 baseline Git blobs; '
        '16 351 causal expected-cost/quantity checks; 16 333 actual-cost/R ledgers; '
        '**243 реальных prefix/future checks** по native четырём TF, future macro invalidations, '
        'Range events и family witnesses; label/identity mutation не меняет frozen predictions. '
        'Каждый TEST metric перепроверен fsum; Wilson — SciPy; drawdown — Decimal. '
        'Timestamp ties, 103/54 purges и physical uniqueness прошли.\n')
    report.append('Первый unit-test запуск имел ошибочную вручную записанную ожидаемую Wilson upper '
        'constant; исправлен только тест, формула CI не менялась. Failed log сохранён рядом с '
        'финальным PASS. После TEST ни rules, ни models, ни frozen implementation не менялись.\n')
    report.append('```bash\n'
        '/workspace/crypto-bot-venv/bin/python scripts/evaluate_strategy_v2.py resume-existing\n'
        '/workspace/crypto-bot-venv/bin/python scripts/verify_strategy_v2.py\n'
        '```\n')
    report.append('Resume проверяет commit freeze и каждый SHA уже готового TEST без пересчёта/выбора. '
        'Fresh reproduction требует нового output root: completed stage guards запрещают перезаписать '
        'TRAIN shortlist, VALIDATION rules, freeze и TEST-open receipt. Все сохранённые скрипты и '
        'README continuation объясняют последовательность build → train → validation → freeze → commit → test.\n')
    report.append('Основные артефакты в `data/reports/strategy_v2_2026_10_10/`: '
        '`strategy_v2_feature_table.csv.gz` (все 16 333 CLOSED, predictors), '
        '`strategy_v2_feature_outcome_table.csv.gz` (тот же flat ledger с diagnostic READY→fill '
        'и явно помеченными outcome_*), `strategy_v2_win_loss_feature_analysis.csv`, '
        '`strategy_v2_candidates.json`, `strategy_v2_validation_results.csv`, '
        '`strategy_v2_oos_results.csv`, `strategy_v2_final_rules.json`, '
        '`strategy_v2_confluence_score.json`, `strategy_v2_leakage_audit.json`, '
        '`strategy_v2_final_leakage_audit.json`, `strategy_v2_qa_receipt.json`. '
        'Все OOS выбранные сделки и полные breakdown/period/stress/LOO CSV сохранены.\n')
    report.append('Следующая объективная проверка возможна на новой истории под неизменным freeze, '
        'а не перебором этого TEST. Здесь исчерпан зарегистрированный полный проход, '
        'включая deterministic grids и интерпретируемые meta-filters. LIVE/private API/orders '
        'не использовались; `trade_entry_allowed=false`.\n')
    report.append('TARGET_70_NOT_CONFIRMED\n')
    content='\n'.join(report)
    Path('STRATEGY_V2_70WR_ANALYSIS.md').write_text(content)
    (OUT/'report.md').write_text(content)
    write_json(OUT/'report_receipt.json',{'status':'COMPLETE','root_report_sha256':digest(Path('STRATEGY_V2_70WR_ANALYSIS.md')),
        'copy_sha256':digest(OUT/'report.md'),'renderer_sha256':digest(Path(__file__)),
        'verdict':'TARGET_70_NOT_CONFIRMED','rules_sha256':digest(OUT/'strategy_v2_final_rules.json'),
        'test_summary_sha256':digest(OUT/'TEST_summary.json'),'trade_entry_allowed':False})
    print('Report complete, full diagnostics retained; no rules changed')


if __name__=='__main__':main()
