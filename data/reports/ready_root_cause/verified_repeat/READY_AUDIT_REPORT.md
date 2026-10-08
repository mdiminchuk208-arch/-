# READY ROOT CAUSE

0 READY потому что текущая экспериментальная формализация OB/HTF POI не дала ни одного одновременного набора допустимого OB, свежей поддерживающей POI и уровней: из 5 853 живых geometry-ready сетапов только девять прошли ранние OB-условия, а у всех девяти подходящие HTF gap-POI уже были затронуты до свечи A.

Вердикт: **ZERO READY IS EXPECTED UNDER CURRENT RULES**. Это вывод о текущей реализации и её экспериментальных ограничениях, а не утверждение, что первичная стратегия обязана давать ноль сделок. Ошибка перехода READY, объясняющая исторический ноль, не найдена. Source-сертификация остаётся открытой.

## Зафиксированная выборка и проверка

10 symbols; 60m/5m; 237.95833333 дня; execution 2026-01-27T12:00:00+00:00 → 2026-09-22T11:00:00+00:00; времена в отчёте UTC. Warmup 576 свечей. Сохранены исходные 6 357 ID и все 17 752 наблюдавшихся изменения сигналов. Все исходные журналы baseline и прежний код движка побайтно неизменны.

Глубокий аудит включает закрытосвечной жизненный цикл этих же ID в warmup. Поэтому geometry-ready/auto-eligible = 5 853, а в прежнем журнале торгового окна WAITING_FOR_AUTO_LEVELS = 5 842: разница 11 — сетапы, утратившие пригодность до начала execution. Дополнительные ID не создавались. Кэш может переносить тождественное вычисление из warmup в execution без повторного вызова детектора.

## FUNNEL

Passed означает, что переход хотя бы раз был достижим при живом SFP. Failed — устойчивое невыполнение после достижения gate; invalidated — SFP закончился раньше прохода; waiting — правое цензурирование. Для каждого перехода entered = passed + failed + waiting + invalidated. Проценты относятся к passed. AUTO LEVELS означает включённую попытку подбора, затем отдельно раскрываются OB/POI/цели.

| Gate | Entered | Passed | Failed | Waiting | Invalidated | % all | % previous |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SETUP | 6357 | 6357 | 0 | 0 | 0 | 100.000 | 100.000 |
| SFP | 6357 | 6357 | 0 | 0 | 0 | 100.000 | 100.000 |
| POST-SFP BOS | 6357 | 6357 | 0 | 0 | 0 | 100.000 | 100.000 |
| ENTRY GEOMETRY | 6357 | 5853 | 53 | 0 | 451 | 92.072 | 92.072 |
| OTE | 5853 | 5853 | 0 | 0 | 0 | 92.072 | 100.000 |
| SOURCE CONTEXT | 5853 | 5853 | 0 | 0 | 0 | 92.072 | 100.000 |
| AUTO LEVELS | 5853 | 5853 | 0 | 0 | 0 | 92.072 | 100.000 |
| OB | 5853 | 9 | 5844 | 0 | 0 | 0.142 | 0.154 |
| POI | 9 | 0 | 9 | 0 | 0 | 0.000 | 0.000 |
| 3 TARGETS | 0 | 0 | 0 | 0 | 0 | 0.000 | N/A |
| RANGE REVIEW | 0 | 0 | 0 | 0 | 0 | 0.000 | N/A |
| SCORE | 0 | 0 | 0 | 0 | 0 | 0.000 | N/A |
| READY | 0 | 0 | 0 | 0 | 0 | 0.000 | N/A |

Range review — неприменим к структурным SFP; Score — не gate READY. Их нулевой entered_count означает, что они находятся ниже непрошедшей POI в заданном представлении funnel. Они не считаются отказами.

## Внутренний OB funnel

| Условие, совместно на одном кандидате | Setups passed |
| --- | --- |
| Attempt auto levels | 5853 |
| Full-body engulf A/B | 1188 |
| Numeric aggression | 909 |
| Mandatory imbalance | 458 |
| OB overlaps OTE and all ABC inside impulse | 71 |
| Exact raw structural sweep by A | 9 |
| Fresh preexisting overlapping HTF gap-POI | 0 |

Первый фильтр содержит три разных причины: 3346 пустых окон после BOS/до anchor, 846 окон без нужных цветов A/B и 473 без полного body-engulf. Это объясняет 4 665 NO_POST_BOS_OB_PATTERN, а не отсутствие любых OB на рынке.

## TOP BLOCKERS

FIRST_TERMINAL_OR_PERSISTENT_BLOCKER относится к первому достигнутому gate, который никогда не прошёл. Для OB выбирается первый отказ самого далеко прошедшего фиксированного A/B/C-кандидата. Более раннее ожидание геометрии, которое позже закончилось успехом, не объявляется постоянным blocker. До появления геометрии OB UNKNOWN, а не NO_PATTERN. Найдено только восемь разных первых причин; TOP-20 содержит все восемь.

| Reason | Setups | % | Category |
| --- | --- | --- | --- |
| NO_POST_BOS_OB_PATTERN | 4665 | 73.384 | C. EXPERIMENTAL BACKTEST PARAMETER |
| ALL_HTF_SFP_CONTEXTS_INVALIDATED | 451 | 7.095 | A. REAL STRATEGY RULE |
| DIRECTIONAL_IMBALANCE_NOT_CONFIRMED | 451 | 7.095 | C. EXPERIMENTAL BACKTEST PARAMETER |
| OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE | 387 | 6.088 | C. EXPERIMENTAL BACKTEST PARAMETER |
| AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET | 279 | 4.389 | C. EXPERIMENTAL BACKTEST PARAMETER |
| RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | 62 | 0.975 | C. EXPERIMENTAL BACKTEST PARAMETER |
| REJECTED_ENTRY_GEOMETRY | 53 | 0.834 | B. SAFETY / CAUSALITY RULE |
| FRESH_PREEXISTING_HTF_POI_NOT_FOUND | 9 | 0.142 | C. EXPERIMENTAL BACKTEST PARAMETER |

Все причины по каждому реальному вызову/наблюдению, включая не последние состояния, находятся в blockers.csv и blocker_dimensions.csv. Count — число queue-evaluations с причиной, unique_setups — уникальные ID; LONG/SHORT — уникальные ID по направлению. Эти агрегаты могут пересекаться. Отдельные timeline сохраняют timestamp, previous_state, gate, result, next_state и reason. Поздняя independent-диагностика помечена diagnostic_only и не выдаётся за выполнение short-circuit production gate.

## CODE PATH

`src/crypto_bot/strategy/replay.py::signals_from_opportunities` присваивает READY_FOR_VIRTUAL_ENTRY только после attach_source_qualified_trade_levels и проверки порядка всех трёх targets/геометрии по обоим краям OTE. Затем all-context invalidation имеет приоритет и заменяет статус на INVALIDATED.

```text
READY = ENTRY_SEARCH_ALLOWED
     && GEOMETRY_KNOWN_AT <= AS_OF
     && AT_LEAST_ONE_LINKED_HTF_SFP_ALIVE
     && QUALIFIED_LEVELS_EXIST
     && LEVELS_KNOWN_AT <= AS_OF
     && VALID_STOP_FOR_ENTIRE_OTE
     && THREE_PROFIT_SIDE_STRICTLY_ORDERED_TARGETS

AUTO_QUALIFIED_LEVELS = EXACT_SOURCE_BOS_AND_OPPOSITE_STRUCTURE
     && EXISTS_SAME_ABC_CANDIDATE(POST_BOS_PRE_ANCHOR
        && COLORS_AND_FULL_BODY_ENGULF && NUMERIC_AGGRESSION
        && IMBALANCE && OTE_OVERLAP && ABC_INSIDE_IMPULSE
        && EXACT_CAUSAL_RAW_STRUCTURAL_SWEEP
        && PREEXISTING_OVERLAPPING_FRESH_HTF_GAP_POI
        && TREND_ALIGNMENT && OB_FIRST_TEST_NOT_CONSUMED
        && STOP_PROTECTS_ENTIRE_OTE)
     && THREE_DISTINCT_NONOVERLAPPING_FRESH_OPPOSING_GAP_POIS
```

Сам automatic detector расположен в auto_levels.py::derive_automatic_levels. Геометрию строят mtf_sfp.py::_attach_entry_geometry и trade_plan.py::derive_structural_impulse_context. Risk, TP1 cost и reentry score проверяет virtual_portfolio.py::_admit уже после READY, поэтому они не могут объяснять отсутствие READY.

## TRUE / FALSE / UNKNOWN и пересечения

Найдено 1755 уникальных A/B/C-кандидатов (ключ setup ID + A.open), в 6270 автоматических вычислениях. Ниже независимые результаты на уникальном кандидате при первой доступной геометрии, а не сложение проходов разных кандидатов.

| Condition | TRUE | FALSE | UNKNOWN |
| --- | --- | --- | --- |
| AGGRESSION | 1218 | 537 | 0 |
| IMBALANCE | 580 | 1175 | 0 |
| OB_FRESH | 434 | 1321 | 0 |
| OB_OTE_AND_IMPULSE | 220 | 1535 | 0 |
| RAW_SWEEP | 145 | 1610 | 0 |
| STOP_GEOMETRY | 550 | 1205 | 0 |
| SUPPORTING_POI | 3 | 1752 | 0 |
| TREND_ALIGNMENT | 1755 | 0 | 0 |

Только три кандидата имеют независимо свежую supporting POI; каждый из них не прошёл другие ранние OB-условия. Девять кандидатов, прошедших все ранние условия, имеют только stale supporting POIs. Пересечение всех необходимых условий на реальном historical setup равно **0**. conditions.json содержит полные counts на scheduled evaluations; detailed_evidence.json — уникальные setup/candidate counts; pairwise CSV — совместные TRUE на одной паре A/B/C. UNKNOWN поздних production gates не заменяется FALSE.

## NEAR-READY

Первые девять кандидатов проходят ранние OB-условия. У пяти исключительно freshness поддерживающей gap-POI не выполнена, прочие OB-условия и независимые три targets выполнены. Это пять экспериментально near-ready сетапов, а не прошедшие source-review сигналы. У остальных четырёх также провалены OB first-test и/или SL. Все девять имеют уже существовавшие перекрывающиеся gap-POI; их нехватка именно в свежести, а не в отсутствии геометрической зоны.

| Rank | Symbol / side | Timestamp UTC | Score | First candidate blocker | Other failed gates |
| --- | --- | --- | --- | --- | --- |
| 1 | ETHUSDT LONG | 2026-05-05T07:55:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | SUPPORTING_POI |
| 2 | LINKUSDT LONG | 2026-06-02T10:30:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | SUPPORTING_POI |
| 3 | LINKUSDT LONG | 2026-08-08T04:15:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | SUPPORTING_POI |
| 4 | ETHUSDT SHORT | 2026-08-16T20:50:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | SUPPORTING_POI |
| 5 | XRPUSDT SHORT | 2026-09-06T06:55:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | SUPPORTING_POI |
| 6 | SOLUSDT LONG | 2026-02-21T13:45:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | OB_FRESH, SUPPORTING_POI |
| 7 | ADAUSDT LONG | 2026-07-21T15:10:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | OB_FRESH, SUPPORTING_POI |
| 8 | LTCUSDT SHORT | 2026-04-20T21:45:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | OB_FRESH, STOP_GEOMETRY, SUPPORTING_POI |
| 9 | XRPUSDT LONG | 2026-07-08T14:00:00+00:00 | 85 | FRESH_PREEXISTING_HTF_POI_NOT_FOUND | OB_FRESH, STOP_GEOMETRY, SUPPORTING_POI |
| 10 | BNBUSDT LONG | 2026-02-08T09:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 11 | BNBUSDT SHORT | 2026-02-20T14:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 12 | LTCUSDT SHORT | 2026-02-21T02:20:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 13 | ADAUSDT SHORT | 2026-04-06T23:30:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 14 | SOLUSDT LONG | 2026-04-07T17:55:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 15 | ADAUSDT LONG | 2026-04-23T20:15:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 16 | ADAUSDT LONG | 2026-05-04T13:35:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 17 | LTCUSDT SHORT | 2026-05-20T01:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 18 | BNBUSDT LONG | 2026-05-20T02:30:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 19 | BNBUSDT LONG | 2026-06-17T05:30:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 20 | XRPUSDT LONG | 2026-06-28T21:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 21 | AVAXUSDT SHORT | 2026-08-18T21:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 22 | DOGEUSDT LONG | 2026-09-02T12:15:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 23 | SOLUSDT SHORT | 2026-09-11T18:25:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, SUPPORTING_POI |
| 24 | DOGEUSDT LONG | 2026-01-29T07:25:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 25 | ADAUSDT LONG | 2026-02-02T07:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 26 | DOGEUSDT LONG | 2026-02-02T07:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 27 | XRPUSDT LONG | 2026-02-02T07:25:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 28 | XRPUSDT LONG | 2026-02-09T00:10:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 29 | DOGEUSDT LONG | 2026-02-26T23:15:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 30 | LINKUSDT SHORT | 2026-02-27T00:55:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 31 | LINKUSDT SHORT | 2026-03-08T03:25:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 32 | LTCUSDT LONG | 2026-03-29T08:10:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 33 | AVAXUSDT LONG | 2026-04-06T05:35:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 34 | DOGEUSDT SHORT | 2026-04-08T15:10:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 35 | SOLUSDT LONG | 2026-04-14T14:15:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 36 | XRPUSDT LONG | 2026-04-14T14:15:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 37 | LINKUSDT LONG | 2026-04-20T07:05:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 38 | AVAXUSDT LONG | 2026-04-26T11:55:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 39 | SOLUSDT LONG | 2026-04-28T14:10:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 40 | XRPUSDT LONG | 2026-05-03T22:30:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 41 | LINKUSDT LONG | 2026-05-03T23:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 42 | AVAXUSDT LONG | 2026-05-12T12:50:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | OB_FRESH, RAW_SWEEP, SUPPORTING_POI |
| 43 | DOGEUSDT LONG | 2026-05-21T08:25:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 44 | BNBUSDT LONG | 2026-05-22T12:30:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 45 | SOLUSDT SHORT | 2026-06-07T20:00:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 46 | XRPUSDT LONG | 2026-06-21T10:25:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 47 | LINKUSDT SHORT | 2026-06-28T11:10:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 48 | SOLUSDT LONG | 2026-06-29T07:10:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 49 | AVAXUSDT LONG | 2026-06-29T09:35:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |
| 50 | LTCUSDT SHORT | 2026-07-16T23:35:00+00:00 | 85 | RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | RAW_SWEEP, STOP_GEOMETRY, SUPPORTING_POI |

Полные Entry Zone/OTE, A/B/C OHLC, raw sweep, prior POI evidence, независимые targets, Range status, SFP contexts, BOS и timestamp находятся в near_ready_top50.json. near_ready_poi_touch_evidence.json показывает первые закрытые LTF-свечи, затронувшие supporting gap-POI после её формирования и до A. near_ready_charts.html — локальная интерактивная страница с 50 графиками и полным evidence.

## Невозможные комбинации и ручные gates

Противоречия «POI должна быть одновременно fresh и протестирована» нет: freshness supporting POI проверяется до A.open, а A разрешено стать её первой реакцией. Для OB проверяются только тесты после C.close. IMB известен после C.close, geometry — после confirmed anchor/correction; available time берётся максимумом. Закрытые свечи из будущего не допускаются.

Все predicates одновременно удовлетворяются LONG/SHORT OHLC-evidence fixtures; раннее реальное conjunction подтверждено девятью setups. Это исключает простое противоречие перечисленных условий, но не доказывает достижимость любого synthetic report через полный structural detector или source-корректность нормализаций.

Все 6 357 baseline setups — structural SFP. Range UNREVIEWED не пропускает range-boundary SFP ещё до создания таких setup. Поэтому solely Range-blocked среди этой когорты = 0, остальные условия прошли = 0. Сколько вне когорты range-событий стало бы setup после ручного PASS, не установлено: автоматический PASS не назначался. Нужны исходные графики с ясными импульсом/коррекцией, timestamped review и независимый тест формального детектора boundaries.

AUTO_NORMALIZED_EVIDENCE_PENDING_SOURCE_REVIEW — provenance-маркер, а не runtime запрет offline READY: конструкция допускает виртуальные уровни с этим маркером, что проверено тестами. Поэтому solely source-review runtime-blocked среди baseline = 0. Для source-сертификации POI/OB нужны первичные PDF, точная геометрия POI, её lifecycle, допустимость повторных тестов, обязательность IMB и схема трёх целей. Эти данные автоматически PASS не получали.

## BUGS

Доказанной ошибки существующего READY engine, lifecycle, cache, known_at, времён или state reset, вызывающей 0 READY, не найдено. Исходные src, tests, config и baseline сохранили SHA-256. INVALIDATED → non-invalidated = 0. Нет попыток виртуального входа и повторного использования consumed virtual-entry IDs. Один живой SFP может связываться с разными BOS ID: это существующая дедупликация opportunities, а не повторное снятие consumed liquidity.

При разработке нового audit устранена ошибка классификации: ещё не достигнутый OB UNKNOWN мог ошибочно стать FIRST blocker NO_PATTERN. Новый regression тест FAIL на прежнем audit, PASS после минимального исправления; production engine не менялся. Геометрия, найденная только после SFP invalidation, не считается проходом actionable funnel.

## INTENTIONAL RULES

SFP formation и последующий LTF BOS; directional OTE 0.705–0.79; invalidation по закрытию за SFP extreme; причинное known_at; запрет technical-recovery lineage; положительная стоп/target геометрия; cost/risk-проверки виртуального исполнения. Эти правила сохранены. Классификация A/B относится к конкретному источнику или safety guard; экспериментальные способы поиска их объектов остаются отдельно в C.

## EXPERIMENTAL RULES

Численные body_fraction=0.6 и engulf_body_ratio=1.0; full-body engulf; ограничение A/B/C после BOS/до выбранного anchor; выбор broken-pre-BOS-extreme→post-BOS-anchor; обязательный IMB; строгий raw structural sweep именно A; HTF three-candle gap как POI; hard freshness/first-test; все A/B/C внутри frozen impulse; три неперекрывающиеся fresh opposing gap-POI и их near edges; synthetic score 65/85/100 и midpoint entry. Это машинные нормализации, не доказанные статистикой или повторной проверкой отсутствующих первичных PDF.

Numeric sensitivity выполнена отдельно, на первых 60 execution днях, при первой доступной live geometry каждого setup. Меняется ровно один параметр: body_fraction 0.5/0.7 либо engulf ratio 1.25/1.5. Во всех четырёх опытах 0 automatic READY; меняются лишь blocker sets. Никакой настройки по final/holdout или выбора лучшего значения нет. Baseline untouched. sensitivity_summary.json содержит source/status/counts.

training_policy_sensitivity.json содержит отдельные read-only ablations по одному policy-флагу IMB, raw structural sweep, supporting gap freshness, OB freshness либо all-ABC-inside-impulse. Causal preexistence/OTE сохраняются. Они проверяют conjunction на baseline-кандидатах, не создают сигналы/сделки и не эквивалентны полноценному альтернативному детектору. Смена самой геометрии импульса или gap-POI detector не выражается численным порогом: без объективной спецификации замена не изобреталась.

## Проверки спорных статусов и условий

WAITING_FOR_ENTRY_GEOMETRY: ожидание подтверждённой противоположной структуры; 451 setup invalidated до actionable geometry. REJECTED_ENTRY_GEOMETRY: 53 живых setup, guard directional OTE; последующие rejection уже invalidated контекстов не подменяют первый terminal blocker. WAITING_FOR_AUTO_LEVELS: ранние OB/POI фильтры выше. WAITING_FOR_SOURCE_LEVELS и SOURCE_CONTEXT_BLOCKED: 0 в frozen execution journal. INVALIDATED: 6 145 latest states, что не заменяет ранее постоянные blockers.

Missing OB раскрыт по пустым окнам, цветам и body engulf. OTE intersection и all-ABC-inside-impulse сохранены раздельно в candidate evidence. Raw sweep / aggressive engulf / imbalance имеют точные candle/level IDs и independent truth counts. HTF POI/stale POI проверены до A, target freshness — на as_of. Production не дошёл до 3 TARGETS, поэтому недостаток целей и их freshness как фактические first blockers = 0; независимые target references не выдаются за готовые сигналы. TP1 cost, initial/reentry score, state consumption и risk не достигли admission.

Timing mismatch: 0 в наблюдённых сигналах/candidate evidence; индекс сравнен с неизменным полным baseline, прежние reference-prefix/future-mutation tests проходят. QA исторических 5m/60m и OHLC aggregation проверена ранее и исходные CSV SHA сохранены. Stale state не восстанавливает freshness: immutable OB creation predicates кэшируются, post-C retests вызывают наблюдение, pending-ready withdrawal покрыт существующими тестами.

## RESULT AFTER FIX

Стратегический fix не требовался: rules, thresholds, source review и portfolio baseline не менялись. Поэтому новый financial backtest с изменённой стратегией не заявляется. Два полного диагностических replay воспроизвели все 17 752 сигналов baseline, а их собственные результаты сверены по SHA. Baseline portfolio: $1170 → $1170, 0 entries, 0 completed trades, P&L $0, DD 0%; PF/expectancy undefined без сделок. Риск 2%, aggregate 6%, daily 4%, Isolated x3, fee 0.06%, adverse slip 0.02% сохранены.

## Проверка и запуск

Baseline 344 tests PASS; после добавления диагностик 353 tests PASS; compile PASS; causality/reference-prefix/future-mutation tests PASS; full offline BACKTEST/SHADOW parity tests PASS; read-only baseline-equivalent replay и повтор диагностик PASS. Проверки PASS относятся к коду и воспроизводимости, а не к прибыльности или source approval.

```powershell
$env:PYTHONPATH = "src"
py -m unittest discover -s tests -v
py scripts/audit_ready_root_cause.py --report-root data/reports/ready_root_cause_local --workers 4
py scripts/summarize_ready_evidence.py data/reports/ready_root_cause_local
py scripts/render_ready_audit.py data/reports/ready_root_cause_local
```

Папка результата должна быть новой: команда не перезаписывает existing report-root. Исторический source baseline остаётся data/reports/historical_portfolio_audit/backtest_max. READY_AUDIT_REPORT.md, CSV/JSON timelines, chart HTML и проверки поставляются с проектом. `trade_entry_allowed=false`; realtime/PAPER/Platform UI/VPS/LIVE не подключались.

## VERDICT

**ZERO READY IS EXPECTED UNDER CURRENT RULES**. Главный bottleneck — экспериментальный OB/HTF gap-POI detector и совместность его требований, а не ручной Range review, Score, размер капитала или портфельный риск. Следующий объективный шаг требует source/chart review именно формализаций C; ослабление baseline ради появления сделок не выполнено.
