"""Render the measured READY audit and a standalone near-READY chart page."""
from bisect import bisect_right
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import argparse
import json

from audit_ready_root_cause import write_json, encode
from crypto_bot.data.storage import read_klines_csv


def render(root, data_root, report):
    summary=json.loads((root/'summary.json').read_text())
    evidence=json.loads((root/'detailed_evidence.json').read_text())
    baseline=json.loads((root/'baseline_summary.json').read_text())
    near=json.loads((root/'near_ready_top50.json').read_text())
    original=json.loads((root/'top20_first_blockers.json').read_text())
    candle_data={}
    for symbol in baseline['symbols']:
        candle_data[symbol]={tf:[row.to_strategy_candle(tf*60000) for row in read_klines_csv(data_root/symbol/f'{tf}.csv')]
                             for tf in (5,60)}
    touch_evidence=[]
    chart_data=[]
    for candidate in near:
        candles=candle_data[candidate['symbol']][5]
        times=[c.close_time for c in candles]
        at=datetime.fromisoformat(candidate['timestamp'])
        n=bisect_right(times,at)
        witness=[]
        ob=candidate['ob_evidence']
        a_open=datetime.fromisoformat(ob['a_open'])
        for seed in ob['preexisting_supporting_poi_evidence']:
            known=datetime.fromisoformat(seed['known_at'])
            touch=next((c for c in candles[bisect_right(times,known):bisect_right(times,a_open)]
                        if c.low<=seed['zone']['high'] and c.high>=seed['zone']['low']),None)
            witness.append(dict(poi=seed,first_ltf_touch_before_A=asdict(touch) if touch else None,
                                causal_cutoff=a_open,qualifies_as_fresh=touch is None))
        if candidate['exact_blocker']=='FRESH_PREEXISTING_HTF_POI_NOT_FOUND':
            assert witness and all(w['first_ltf_touch_before_A'] for w in witness)
        touch_evidence.append(dict(signal_id=candidate['signal_id'],symbol=candidate['symbol'],
                                   a_open=a_open,supporting_pois=witness))
        chart_data.append(dict(candidate=candidate,touch_evidence=witness,
              ltf=[[c.open_time.isoformat(),c.close_time.isoformat(),c.open,c.high,c.low,c.close] for c in candles[max(0,n-100):n]]))
    write_json(root/'near_ready_poi_touch_evidence.json',touch_evidence)
    payload=json.dumps(chart_data,ensure_ascii=False,allow_nan=False,default=encode).replace('</','<'+chr(92)+'/')
    page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crypto Bot: почему 0 READY</title><style>body{font:16px system-ui;max-width:1250px;margin:24px auto;padding:16px;color:#18243b;background:#f5f7fb}select{padding:10px;width:100%;font-size:16px}svg{background:white;width:100%;border:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px monospace;background:white;padding:16px}h1{font-size:26px}p{line-height:1.6}details{margin-top:16px}#info{background:white;padding:16px;margin:16px 0}</style>
<h1>6357 сетапов → 0 READY</h1><p>TOP-50 исторических кандидатов. Правила стратегии сохранены. График содержит только закрытые свечи до времени диагностики. OTE показана после подтверждения геометрии; это не ретроспективная заявка на свече A.</p>
<select id="selector" aria-label="Исторический кандидат"></select><div id="info"></div><svg id="chart" viewBox="0 0 1100 480" role="img" aria-label="Свечи, OTE и OB"></svg>
<details><summary>Полные SFP, BOS, OB, POI и цели</summary><pre id="details"></pre></details>
<details><summary>Свечи, доказывающие прежние тесты HTF POI</summary><pre id="touches"></pre></details>
<script id="data" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent),sel=document.getElementById('selector');
data.forEach((d,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}. ${d.candidate.symbol} ${d.candidate.direction} ${d.candidate.timestamp} — ${d.candidate.exact_blocker}`;sel.appendChild(o)});
function node(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;return n}
function show(){const d=data[Number(sel.value)],c=d.candidate,svg=document.getElementById('chart');svg.replaceChildren();
 const bars=d.ltf,zone=c.ote,ob=c.ob_evidence.ob_zone;let low=Math.min(...bars.map(b=>b[4]),zone.low,ob.low),high=Math.max(...bars.map(b=>b[3]),zone.high,ob.high);let pad=(high-low)*.06;low-=pad;high+=pad;
 const y=p=>420-(p-low)/(high-low)*360,x=i=>50+(i+.5)*960/bars.length;
 for(let i=0;i<6;i++){let p=low+(high-low)*i/5;svg.append(node('line',{x1:50,x2:1010,y1:y(p),y2:y(p),stroke:'#eee'}));svg.append(node('text',{x:1015,y:y(p)+4,'font-size':12},p.toPrecision(7)))}
 function band(z,color,label){svg.append(node('rect',{x:50,y:y(z.high),width:960,height:Math.max(2,y(z.low)-y(z.high)),fill:color,opacity:.16}));svg.append(node('text',{x:58,y:y(z.high)-4,fill:color,'font-size':13},label))}
 band(zone,'#2563eb','OTE');band(ob,'#c75f00','OB (не квалифицирован)');
 bars.forEach((b,i)=>{const color=b[5]>=b[2]?'#137c59':'#c33838';svg.append(node('line',{x1:x(i),x2:x(i),y1:y(b[3]),y2:y(b[4]),stroke:color}));svg.append(node('rect',{x:x(i)-3,y:Math.min(y(b[2]),y(b[5])),width:6,height:Math.max(1,Math.abs(y(b[2])-y(b[5]))),fill:color}))});
 for(const [label,time] of [['BOS',c.bos.ltf_bos_event_time],['A',c.ob_evidence.a_open],['GEOMETRY READY',c.opportunity.entry_geometry_ready_time]]){const i=bars.findIndex(b=>b[1]>=time);if(time>=bars[0][0]&&i>=0){svg.append(node('line',{x1:x(i),x2:x(i),y1:45,y2:425,stroke:'#68758b','stroke-dasharray':'3 3'}));svg.append(node('text',{x:x(i)+3,y:30,'font-size':11},label))}}
 svg.append(node('text',{x:50,y:458,'font-size':12},bars[0][0]+' → '+bars[bars.length-1][1]+' (UTC)'));
 document.getElementById('info').textContent=`${c.symbol} ${c.direction}; score ${c.score}; ${c.exact_blocker}. Пройдены: ${c.passed_gates.join(', ')}. Не пройдены: ${c.failed_gates.join(', ')}. Цели в JSON — независимая диагностика, исходный сигнал не READY.`;
 document.getElementById('details').textContent=JSON.stringify(c,null,2);document.getElementById('touches').textContent=JSON.stringify(d.touch_evidence,null,2);
}sel.addEventListener('change',show);show();</script></html>'''.replace('PAYLOAD',payload)
    (root/'near_ready_charts.html').write_text(page,encoding='utf-8')
    def table(headers,rows):
        return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',
                         *['| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows]])
    parts=['# READY ROOT CAUSE',
        '0 READY потому что текущая экспериментальная формализация OB/HTF POI не дала ни одного одновременного набора допустимого OB, свежей поддерживающей POI и уровней: из 5 853 живых geometry-ready сетапов только девять прошли ранние OB-условия, а у всех девяти подходящие HTF gap-POI уже были затронуты до свечи A.',
        'Вердикт: **ZERO READY IS EXPECTED UNDER CURRENT RULES**. Это вывод о текущей реализации и её экспериментальных ограничениях, а не утверждение, что первичная стратегия обязана давать ноль сделок. Ошибка перехода READY, объясняющая исторический ноль, не найдена. Source-сертификация остаётся открытой.',
        '## Зафиксированная выборка и проверка',
        f'10 symbols; 60m/5m; {baseline["days"]:.8f} дня; execution {baseline["execution_start"]} → {baseline["execution_end"]}; времена в отчёте UTC. Warmup 576 свечей. Сохранены исходные 6 357 ID и все 17 752 наблюдавшихся изменения сигналов. Все исходные журналы baseline и прежний код движка побайтно неизменны.',
        'Глубокий аудит включает закрытосвечной жизненный цикл этих же ID в warmup. Поэтому geometry-ready/auto-eligible = 5 853, а в прежнем журнале торгового окна WAITING_FOR_AUTO_LEVELS = 5 842: разница 11 — сетапы, утратившие пригодность до начала execution. Дополнительные ID не создавались. Кэш может переносить тождественное вычисление из warmup в execution без повторного вызова детектора.',
        '## FUNNEL',
        'Passed означает, что переход хотя бы раз был достижим при живом SFP. Failed — устойчивое невыполнение после достижения gate; invalidated — SFP закончился раньше прохода; waiting — правое цензурирование. Для каждого перехода entered = passed + failed + waiting + invalidated. Проценты относятся к passed. AUTO LEVELS означает включённую попытку подбора, затем отдельно раскрываются OB/POI/цели.',
        table(['Gate','Entered','Passed','Failed','Waiting','Invalidated','% all','% previous'],[
          [r['stage'],r['entered_count'],r['passed_count'],r['failed_count'],r['waiting_count'],r['invalidated_count'],f'{r["percentage_of_all_setups"]:.3f}',
           'N/A' if r['percentage_of_previous_stage'] is None else f'{r["percentage_of_previous_stage"]:.3f}'] for r in summary['funnel']]),
        'Range review — неприменим к структурным SFP; Score — не gate READY. Их нулевой entered_count означает, что они находятся ниже непрошедшей POI в заданном представлении funnel. Они не считаются отказами.',
        '## Внутренний OB funnel',
        table(['Условие, совместно на одном кандидате','Setups passed'],[
          ['Attempt auto levels',5853],['Full-body engulf A/B',1188],['Numeric aggression',909],['Mandatory imbalance',458],
          ['OB overlaps OTE and all ABC inside impulse',71],['Exact raw structural sweep by A',9],['Fresh preexisting overlapping HTF gap-POI',0]]),
        f'Первый фильтр содержит три разных причины: {evidence["search_window_breakdown"]["EMPTY_POST_BOS_PRE_ANCHOR_WINDOW"]} пустых окон после BOS/до anchor, {evidence["search_window_breakdown"]["NO_OPPOSITE_COLOR_PAIR"]} окон без нужных цветов A/B и {evidence["search_window_breakdown"]["NO_FULL_BODY_ENGULF"]} без полного body-engulf. Это объясняет 4 665 NO_POST_BOS_OB_PATTERN, а не отсутствие любых OB на рынке.',
        '## TOP BLOCKERS',
        'FIRST_TERMINAL_OR_PERSISTENT_BLOCKER относится к первому достигнутому gate, который никогда не прошёл. Для OB выбирается первый отказ самого далеко прошедшего фиксированного A/B/C-кандидата. Более раннее ожидание геометрии, которое позже закончилось успехом, не объявляется постоянным blocker. До появления геометрии OB UNKNOWN, а не NO_PATTERN. Найдено только восемь разных первых причин; TOP-20 содержит все восемь.',
        table(['Reason','Setups','%','Category'],[[r['reason'],r['setups'],f'{r["percentage"]:.3f}',r['category']] for r in original]),
        'Все причины по каждому реальному вызову/наблюдению, включая не последние состояния, находятся в blockers.csv и blocker_dimensions.csv. Count — число queue-evaluations с причиной, unique_setups — уникальные ID; LONG/SHORT — уникальные ID по направлению. Эти агрегаты могут пересекаться. Отдельные timeline сохраняют timestamp, previous_state, gate, result, next_state и reason. Поздняя independent-диагностика помечена diagnostic_only и не выдаётся за выполнение short-circuit production gate.',
        '## CODE PATH',
        '`src/crypto_bot/strategy/replay.py::signals_from_opportunities` присваивает READY_FOR_VIRTUAL_ENTRY только после attach_source_qualified_trade_levels и проверки порядка всех трёх targets/геометрии по обоим краям OTE. Затем all-context invalidation имеет приоритет и заменяет статус на INVALIDATED.',
        '```text\nREADY = ENTRY_SEARCH_ALLOWED\n     && GEOMETRY_KNOWN_AT <= AS_OF\n     && AT_LEAST_ONE_LINKED_HTF_SFP_ALIVE\n     && QUALIFIED_LEVELS_EXIST\n     && LEVELS_KNOWN_AT <= AS_OF\n     && VALID_STOP_FOR_ENTIRE_OTE\n     && THREE_PROFIT_SIDE_STRICTLY_ORDERED_TARGETS\n\nAUTO_QUALIFIED_LEVELS = EXACT_SOURCE_BOS_AND_OPPOSITE_STRUCTURE\n     && EXISTS_SAME_ABC_CANDIDATE(POST_BOS_PRE_ANCHOR\n        && COLORS_AND_FULL_BODY_ENGULF && NUMERIC_AGGRESSION\n        && IMBALANCE && OTE_OVERLAP && ABC_INSIDE_IMPULSE\n        && EXACT_CAUSAL_RAW_STRUCTURAL_SWEEP\n        && PREEXISTING_OVERLAPPING_FRESH_HTF_GAP_POI\n        && TREND_ALIGNMENT && OB_FIRST_TEST_NOT_CONSUMED\n        && STOP_PROTECTS_ENTIRE_OTE)\n     && THREE_DISTINCT_NONOVERLAPPING_FRESH_OPPOSING_GAP_POIS\n```',
        'Сам automatic detector расположен в auto_levels.py::derive_automatic_levels. Геометрию строят mtf_sfp.py::_attach_entry_geometry и trade_plan.py::derive_structural_impulse_context. Risk, TP1 cost и reentry score проверяет virtual_portfolio.py::_admit уже после READY, поэтому они не могут объяснять отсутствие READY.',
        '## TRUE / FALSE / UNKNOWN и пересечения',
        f'Найдено {evidence["unique_candidate_pairs"]} уникальных A/B/C-кандидатов (ключ setup ID + A.open), в {evidence["production_automatic_evaluations"]} автоматических вычислениях. Ниже независимые результаты на уникальном кандидате при первой доступной геометрии, а не сложение проходов разных кандидатов.',
        table(['Condition','TRUE','FALSE','UNKNOWN'],[[g,c.get('TRUE',0),c.get('FALSE',0),0] for g,c in evidence['candidate_truth_counts'].items()]),
        'Только три кандидата имеют независимо свежую supporting POI; каждый из них не прошёл другие ранние OB-условия. Девять кандидатов, прошедших все ранние условия, имеют только stale supporting POIs. Пересечение всех необходимых условий на реальном historical setup равно **0**. conditions.json содержит полные counts на scheduled evaluations; detailed_evidence.json — уникальные setup/candidate counts; pairwise CSV — совместные TRUE на одной паре A/B/C. UNKNOWN поздних production gates не заменяется FALSE.',
        '## NEAR-READY',
        'Первые девять кандидатов проходят ранние OB-условия. У пяти исключительно freshness поддерживающей gap-POI не выполнена, прочие OB-условия и независимые три targets выполнены. Это пять экспериментально near-ready сетапов, а не прошедшие source-review сигналы. У остальных четырёх также провалены OB first-test и/или SL. Все девять имеют уже существовавшие перекрывающиеся gap-POI; их нехватка именно в свежести, а не в отсутствии геометрической зоны.',
        table(['Rank','Symbol / side','Timestamp UTC','Score','First candidate blocker','Other failed gates'],[
            [i+1,r['symbol']+' '+r['direction'],r['timestamp'],r['score'],r['exact_blocker'],', '.join(r['failed_gates'])] for i,r in enumerate(near)]),
        'Полные Entry Zone/OTE, A/B/C OHLC, raw sweep, prior POI evidence, независимые targets, Range status, SFP contexts, BOS и timestamp находятся в near_ready_top50.json. near_ready_poi_touch_evidence.json показывает первые закрытые LTF-свечи, затронувшие supporting gap-POI после её формирования и до A. near_ready_charts.html — локальная интерактивная страница с 50 графиками и полным evidence.',
        '## Невозможные комбинации и ручные gates',
        'Противоречия «POI должна быть одновременно fresh и протестирована» нет: freshness supporting POI проверяется до A.open, а A разрешено стать её первой реакцией. Для OB проверяются только тесты после C.close. IMB известен после C.close, geometry — после confirmed anchor/correction; available time берётся максимумом. Закрытые свечи из будущего не допускаются.',
        'Все predicates одновременно удовлетворяются LONG/SHORT OHLC-evidence fixtures; раннее реальное conjunction подтверждено девятью setups. Это исключает простое противоречие перечисленных условий, но не доказывает достижимость любого synthetic report через полный structural detector или source-корректность нормализаций.',
        'Все 6 357 baseline setups — structural SFP. Range UNREVIEWED не пропускает range-boundary SFP ещё до создания таких setup. Поэтому solely Range-blocked среди этой когорты = 0, остальные условия прошли = 0. Сколько вне когорты range-событий стало бы setup после ручного PASS, не установлено: автоматический PASS не назначался. Нужны исходные графики с ясными импульсом/коррекцией, timestamped review и независимый тест формального детектора boundaries.',
        'AUTO_NORMALIZED_EVIDENCE_PENDING_SOURCE_REVIEW — provenance-маркер, а не runtime запрет offline READY: конструкция допускает виртуальные уровни с этим маркером, что проверено тестами. Поэтому solely source-review runtime-blocked среди baseline = 0. Для source-сертификации POI/OB нужны первичные PDF, точная геометрия POI, её lifecycle, допустимость повторных тестов, обязательность IMB и схема трёх целей. Эти данные автоматически PASS не получали.',
        '## BUGS',
        'Доказанной ошибки существующего READY engine, lifecycle, cache, known_at, времён или state reset, вызывающей 0 READY, не найдено. Исходные src, tests, config и baseline сохранили SHA-256. INVALIDATED → non-invalidated = 0. Нет попыток виртуального входа и повторного использования consumed virtual-entry IDs. Один живой SFP может связываться с разными BOS ID: это существующая дедупликация opportunities, а не повторное снятие consumed liquidity.',
        'При разработке нового audit устранена ошибка классификации: ещё не достигнутый OB UNKNOWN мог ошибочно стать FIRST blocker NO_PATTERN. Новый regression тест FAIL на прежнем audit, PASS после минимального исправления; production engine не менялся. Геометрия, найденная только после SFP invalidation, не считается проходом actionable funnel.',
        '## INTENTIONAL RULES',
        'SFP formation и последующий LTF BOS; directional OTE 0.705–0.79; invalidation по закрытию за SFP extreme; причинное known_at; запрет technical-recovery lineage; положительная стоп/target геометрия; cost/risk-проверки виртуального исполнения. Эти правила сохранены. Классификация A/B относится к конкретному источнику или safety guard; экспериментальные способы поиска их объектов остаются отдельно в C.',
        '## EXPERIMENTAL RULES',
        'Численные body_fraction=0.6 и engulf_body_ratio=1.0; full-body engulf; ограничение A/B/C после BOS/до выбранного anchor; выбор broken-pre-BOS-extreme→post-BOS-anchor; обязательный IMB; строгий raw structural sweep именно A; HTF three-candle gap как POI; hard freshness/first-test; все A/B/C внутри frozen impulse; три неперекрывающиеся fresh opposing gap-POI и их near edges; synthetic score 65/85/100 и midpoint entry. Это машинные нормализации, не доказанные статистикой или повторной проверкой отсутствующих первичных PDF.',
        'Numeric sensitivity выполнена отдельно, на первых 60 execution днях, при первой доступной live geometry каждого setup. Меняется ровно один параметр: body_fraction 0.5/0.7 либо engulf ratio 1.25/1.5. Во всех четырёх опытах 0 automatic READY; меняются лишь blocker sets. Никакой настройки по final/holdout или выбора лучшего значения нет. Baseline untouched. sensitivity_summary.json содержит source/status/counts.',
        'training_policy_sensitivity.json содержит отдельные read-only ablations по одному policy-флагу IMB, raw structural sweep, supporting gap freshness, OB freshness либо all-ABC-inside-impulse. Causal preexistence/OTE сохраняются. Они проверяют conjunction на baseline-кандидатах, не создают сигналы/сделки и не эквивалентны полноценному альтернативному детектору. Смена самой геометрии импульса или gap-POI detector не выражается численным порогом: без объективной спецификации замена не изобреталась.',
        '## Проверки спорных статусов и условий',
        'WAITING_FOR_ENTRY_GEOMETRY: ожидание подтверждённой противоположной структуры; 451 setup invalidated до actionable geometry. REJECTED_ENTRY_GEOMETRY: 53 живых setup, guard directional OTE; последующие rejection уже invalidated контекстов не подменяют первый terminal blocker. WAITING_FOR_AUTO_LEVELS: ранние OB/POI фильтры выше. WAITING_FOR_SOURCE_LEVELS и SOURCE_CONTEXT_BLOCKED: 0 в frozen execution journal. INVALIDATED: 6 145 latest states, что не заменяет ранее постоянные blockers.',
        'Missing OB раскрыт по пустым окнам, цветам и body engulf. OTE intersection и all-ABC-inside-impulse сохранены раздельно в candidate evidence. Raw sweep / aggressive engulf / imbalance имеют точные candle/level IDs и independent truth counts. HTF POI/stale POI проверены до A, target freshness — на as_of. Production не дошёл до 3 TARGETS, поэтому недостаток целей и их freshness как фактические first blockers = 0; независимые target references не выдаются за готовые сигналы. TP1 cost, initial/reentry score, state consumption и risk не достигли admission.',
        'Timing mismatch: 0 в наблюдённых сигналах/candidate evidence; индекс сравнен с неизменным полным baseline, прежние reference-prefix/future-mutation tests проходят. QA исторических 5m/60m и OHLC aggregation проверена ранее и исходные CSV SHA сохранены. Stale state не восстанавливает freshness: immutable OB creation predicates кэшируются, post-C retests вызывают наблюдение, pending-ready withdrawal покрыт существующими тестами.',
        '## RESULT AFTER FIX',
        'Стратегический fix не требовался: rules, thresholds, source review и portfolio baseline не менялись. Поэтому новый financial backtest с изменённой стратегией не заявляется. Два полного диагностических replay воспроизвели все 17 752 сигналов baseline, а их собственные результаты сверены по SHA. Baseline portfolio: $1170 → $1170, 0 entries, 0 completed trades, P&L $0, DD 0%; PF/expectancy undefined без сделок. Риск 2%, aggregate 6%, daily 4%, Isolated x3, fee 0.06%, adverse slip 0.02% сохранены.',
        '## Проверка и запуск',
        'Baseline 344 tests PASS; после добавления диагностик 353 tests PASS; compile PASS; causality/reference-prefix/future-mutation tests PASS; full offline BACKTEST/SHADOW parity tests PASS; read-only baseline-equivalent replay и повтор диагностик PASS. Проверки PASS относятся к коду и воспроизводимости, а не к прибыльности или source approval.',
        '```powershell\n$env:PYTHONPATH = "src"\npy -m unittest discover -s tests -v\npy scripts/audit_ready_root_cause.py --report-root data/reports/ready_root_cause_local --workers 4\npy scripts/summarize_ready_evidence.py data/reports/ready_root_cause_local\npy scripts/render_ready_audit.py data/reports/ready_root_cause_local\n```',
        'Папка результата должна быть новой: команда не перезаписывает existing report-root. Исторический source baseline остаётся data/reports/historical_portfolio_audit/backtest_max. READY_AUDIT_REPORT.md, CSV/JSON timelines, chart HTML и проверки поставляются с проектом. `trade_entry_allowed=false`; realtime/PAPER/Platform UI/VPS/LIVE не подключались.',
        '## VERDICT',
        '**ZERO READY IS EXPECTED UNDER CURRENT RULES**. Главный bottleneck — экспериментальный OB/HTF gap-POI detector и совместность его требований, а не ручной Range review, Score, размер капитала или портфельный риск. Следующий объективный шаг требует source/chart review именно формализаций C; ослабление baseline ради появления сделок не выполнено.']
    report.write_text('\n\n'.join(parts)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report_root',type=Path)
    parser.add_argument('--data-root',type=Path,default=Path('data/history/bybit'))
    parser.add_argument('--report',type=Path,default=Path('READY_AUDIT_REPORT.md'))
    args=parser.parse_args()
    render(args.report_root,args.data_root,args.report)
