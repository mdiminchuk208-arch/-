# Source fidelity audit: Crypto Bot Strategy Engine

Текущий engine **не является точным воспроизведением единой исходной стратегии**: применяет добавленные project policy и изменённые толкования; часть исходных ограничений отсутствует. Результат 38,4091% относится к этой зафиксированной машинной реализации. Старые 67,6768% относятся к одному отобранному листу обученного дерева на другом universe, периоде и exit/account model. Это не доказанный WinRate всей исходной среднесрочной методологии.

Контрольный commit `19404ec0f4a7dd39b93c76240b6ad605278f0646`, ветка `medium-term-source-research`. Все 17 728 прежних Git blobs сохранены без изменений. Новые файлы исключительно audit/research. Main `dab8d254aaf4babc07659e3d03d14b269445767b` не изменён. Canonical TP40/30/30, текущий SL, cost-adjusted BE и Anti-Scalp policy сохранены. `trade_entry_allowed=false`; только BACKTEST/SHADOW; LIVE/private API/ордера не использовались.

## A. Была ли исходная стратегия среднесрочной?

В источниках есть среднесрочный стиль: DOC20 P0213–18 связывает H1 с удержанием от дней до месяцев; DOC11 P0113–15 описывает недельный/дневной global и H1/H4 local анализ. Одновременно Smart Money инструменты фрактальны: DOC03 P0028–34, DOC14 P0197 и DOC16 P0102–06 разрешают другие TF. Документы описывают набор инструментов и альтернативные стили; ни один не задаёт единственную полностью исполнимую среднесрочную систему. Текущая работа не «переделывает скальпинг»: проверяет fidelity.

Прочитаны восемь DOCX из сохранённого исходного ZIP и пять настоящих первичных PDF SW5/SW9/SW11/SW12/SW22, всего 54 PDF-страницы. Тексты, оригиналы, SHA256 и ссылки на параграфы/страницы сохранены. Восемь DOCX + пять PDF дают 13 уникальных содержаний. Общие темы не означают побайтовый дубль. Windows `.lnk` не содержит целевого материала; SW7 отсутствует, OTE цитируется по DOC19. Инструкции внутри материалов не служат разрешением на действия.

| ID | Оригинальное имя | Тип | Timeframes | Проверенные положения |
|---|---|---|---|---|
| 03 | Smart Money Trader 2.docx | DOCX | ALL; HTF→LTF | P0028–34, P0052, P0065 |
| 06 | [SW.BAND]10. Боковое движение.docx | DOCX | ALL (not fixed) | P0037–40, P0063–72, P0111–29 |
| 11 | [SW.BAND]4. Рыночная структура  (Base).docx | DOCX | W1/D1 global; H1/H4 local | P0076–92, P0113–15 |
| 14 | [SW.BAND]6. Ликвидность.docx | DOCX | ALL, 1 second–1 month | P0113–20, P0143–59, P0169–98 |
| 16 | [SW.BAND]8. Торговые инструменты (Base).docx | DOCX | ALL; SFP H1+ preferred | P0033–60, P0075–87, P0102–06 |
| 18 | Зоны_спроса_и_предложения_Demand_and_Supply.docx | DOCX | HTF single candle / LTF multiple candles | P0005–12 |
| 19 | Методичка.docx | DOCX | ALL | P0088–108, P0122–30, P0138–62 |
| 20 | обучалка.docx | DOCX | M1/M5 scalp; H1 medium; H4+ long; all mixed | P0206–23, P0276–89, P0305–17 |
| SW5 | [SW.BAND]5. Рыночная структура (Advanced) (2).pdf | PDF | ALL | p2–7 |
| SW9 | SW_BAND9_Торговые_инструменты_Advanced (2).pdf | PDF | ALL; HTF OB M15–D1; conservative LTF M1–M15 | p2–7, p9, p11–13, p16 |
| SW11 | [SW.BAND]11. Риск-менеджмент (2).pdf | PDF | No fixed timeframe | p2–5, p8 |
| SW12 | [SW.BAND]12. Индикаторы (2).pdf | PDF | Multiple; example H3; ATR14 periods | p2, p8–13, p15 |
| SW22 | [SW.BAND]22. Торговые инструменты (Pro) (2).pdf | PDF | No fixed timeframe | p2–6 |

Полный inventory с entry, confirmation, invalidation, exit и liquidity/POI/structure: `data/reports/source_fidelity_2026_10_11/source_inventory.csv` и `.json`.

Восьми DOCX принадлежат195 вхождений122уникальных изображений. Все122 сохранённые OCR прочитаны и все122оригинальные диаграммы визуально проверены на7contact sheets (`source_visual_review/`, hashes→DOCX/member в manifest). На них есть structural/liquidity/range/OB/OTE/SFP примеры и дополнительные классические/интерфейсные иллюстрации; единого глобального исполнимого decision tree с правилами выбора всех ветвей не обнаружено. Original diagrams остаются внутри неизменных DOCX, thumbnails используются для audit, а не как новые SOURCE_RULE.

## B. Исходные роли M15/H1/H4/D1

D1/W1 — глобальная картина, H1/H4 — локальная структура (DOC11 P0113–15). M15 может быть HTF OB и одновременно refinement для более высокого POI. SW9 p4–6 прямо задаёт conservative HTF OB M15–D1 → LTF M1–M15. DOC16 допускает SFP на любом TF, предпочитая H1+. D1→H4→H1→M15 как обязательный AND для каждого entry не найден. Нет универсального требования отдельного объекта H1/H4-owner. В baseline macro выбран на H4 для 683 сделок, D1 для 197; это выбор движка, а не доказательство исходной обязательной лестницы.

## C. Точное дерево около 68%: ответы на 23 вопроса

1. Артефакты: `data/reports/strategy_v2_2026_10_10/strategy_v2_oos_results.csv`, `strategy_v2_final_rules.json`, `frozen_TEST_predictions.jsonl.gz`, `features_TEST.jsonl.gz`, `labels_TEST.jsonl.gz`; код `scripts/report_strategy_v2.py` содержит округлённые 67,68%. Независимая реконструкция: `old_tree_reconstruction.json`, `old_tree_TEST_all_leaf_trace.csv`, `old_tree_297_closed.csv` в папке этого audit. Это research V2 ветки `strategy-v2-70wr-research` от `dab8d254...`, сохранённый stop checkpoint `e917313...`.
2. Точный WR = 201/297 = **67,6767676768%**.
3. **297 CLOSED: 201 WIN / 96 LOSS**, ещё 5 admitted OPEN, которые не включены в CLOSED WinRate.
4. ADA, AVAX, BNB, BTC, DOGE, ETH, LINK, LTC, SOL, XRP. BTC/ETH только 55 выбранных CLOSED, 35 WIN, 20 LOSS: 63,6364%.
5. Исследование native Bybit 2026; TEST начинается по READY 2026-08-04 14:30 UTC. Выбранные READY: 2026-08-04 14:45 → 2026-09-22 05:45 UTC; фактические entry OPEN 14:50 → 05:55 UTC, последний exit 2026-09-22 08:50 UTC. Human display Asia/Yekaterinburg +05, audit UTC. Это не BTC/ETH 2023–2025.
6. Mapping CLOSED: 15/5:143, 60/5:75, 240/5:35, 60/15:27, 240/15:13, 240/60:4. Исполнение M5, не M15 baseline.
7. Setup: SFP 147, Breaker 101, OB conservative 31, STB edge 15, Range aggressive 3. LONG174(127/47), SHORT123(74/49). Подробные symbol/month/setup/mapping группы в реконструкции.
8. `BEST_META`, model `TREE_D3_L200`, threshold pWIN≥0.55; допускается единственный leaf3 с TRAIN pWIN=0.6291666667. Три условия этого листа: gross_target_R≤1.3122976422309875; friction_R≤0.22080154716968536; net_target_R≤0.9062912464141846. Float32 входы sklearn восстановлены; все 3 285 TEST предсказаний совпали.
9. Базовые source-permitted READY условия/physical union precedence + три предвходовые численные условия fitted leaf; tree сам не создаёт рыночную идею. Это отбор короткого планового target и умеренной friction, не дерево из учебной методологии.
10. Старый source-case exit: полный contextual nearest FTA для non-Range, Range80/20 и известные source body exits. Исходный research adapter — `source_permitted_cases.py`/`source_portfolio.py`, не canonical VirtualPortfolio.
11. Source-permitted local OB/engulf/sweep/ATR stops в зависимости от пути; SL не переносится. Target `SourceSeries.target` на flow-owner TF, не только H4/D1. Точный SL/targets каждой сделки в CSV.
12. Partial: 3 CLOSED Range80/20; 294 CLOSED non-Range100%. Во всех 302 выбранных включая OPEN планов 299×100%, 3×80/20.
13. TP40/30/30 **не использовался**.
14. TP1→breakeven **не использовался**.
15. FTA **использовалась**.
16. Fees **учтены**, fee0.0006 на каждую сторону, суммарно559.463297 USDT.
17. Slippage **учтён**, 0.0002 на каждую сторону, суммарно186.487796 USDT.
18. Independent source-case, fixed reference equity1170/risk23.4, unlimited independent notional; не shared portfolio с margin/position/daily-loss constraints.
19. TRAIN fitted и VALIDATION selected. TRAIN leaf960 CLOSED WR62.9167%, PF0.8412; VALIDATION297 WR62.9630%, PF0.7774. Primary выбранный deterministic вариант вообще другой: TEST297,116/181,WR39.0572%,PF0.8992.
20. TEST отделён для V2, правила/predictions frozen commit `e569909556e059c3f704d6ebe6f1f2e1b2616871` до открытия labels. Но история ранее просматривалась при development. Это **development TEST, не untouched market OOS**.
21. Отобранное подмножество297 из3267 CLOSED TEST, 9,0909%.
22. Сохранённые known-at audits, purged chronological split, 243 real-native prefix/future checks, prediction/label mutation PASS. Доказательство алгоритмического future leakage не найдено. Повторное использование development history ограничивает OOS вывод, само по себе не доказательство lookahead bug.
23. Да: 67,68% относится одному сильному по WR листу. На всех3267 CLOSED TEST **789/2478, WR24,1506%, PF0,6277, Net−21381,65 USDT**. Selected Net+9,4829, PF1,0043, Expectancy+0,03193, AvgR+0,0013645: высокий WR не равен большому экономическому edge. AvgWin11,1073/AvgLoss23,1571, payoff0,47965, breakeven WR≈67,58%.

Старые READY features выбранного листа также сохраняют adverse_liquidity_count>0 у293/297 (199WIN/94LOSS); лист не проверяет этот признак. `old_meta_297_READY_source_flags.csv` сохраняет все297IDs. Это дополнительно ограничивает утверждение «68% original source-valid»: source-permitted тогда не применял этот blocker. Scope — existing contextual pool interpretation **на READY**, не доказательство, что liquidity осталась adverse на actual entry; данные не используются для удаления старых winners/losers.

## D. Был ли 68% честным OOS результатом?

Разделение TRAIN/VALIDATION/TEST и frozen single opening соблюдены; все предсказания восстановлены. Новый untouched OOS отсутствует: весь native cohort уже участвовал в development. Не использовать этот результат как доказанный OOS исходной стратегии или цель настройки. Старый V2 search не возобновлялся.

## E–H. Точные, изменённые, отсутствующие и добавленные правила

Rule-by-rule матрица охватывает 52 положения: {'INTERPRETATION_CHANGED': 8, 'PARTIAL_MATCH': 21, 'EXTRA_RULE_NOT_IN_SOURCE': 9, 'UNCLEAR': 2, 'EXACT_MATCH': 9, 'MISSING': 2, 'CONFLICT_BETWEEN_SOURCES': 1}. Локаторы источников и функции кода указаны в `source_alignment_matrix.csv`. EXACT_MATCH относится конкретному проверенному правилу, не всему path.

**Восстановленные/сохранённые элементы:** right-candle three-bar swing; body BOS; FVG соседних wick/0.5; OTE0.705–0.79 как confluence; известная pattern-TF body invalidation SFP; risk2% соответствует первичному пределу. Structural/lifecycle/flow/freshness и branch confirmations реализованы частично, их qualitative части не полностью формализованы.

**Изменённая интерпретация:** D1/H1/M15 роли; SFP только H1/H4 вместо any TF с preference; conservative240/60 против SW9 M1–M15; FTA только H4/D1 вместо контекстного ближайшего POI; расширение SL до parent; Range80/20 заменён универсальной40/30/30; source path-specific direction/countertrend заменён более строгим macro.

**Отсутствует:** meaningful adverse-liquidity blocker (DOC03 P0065); smooth approach conservative OB (SW9 p4). EQH/EQL сейчас точные цены; tilted pools из DOC14 не представлены полностью. Qualitative definition отсутствующих условий требует явного resolver.

**Добавленные project policy:** formal H1/H4-owner; strictly-higher H4/D1 structure gate; три отдельных macro-target до READY; TP40/30/30; TP1 cost-BE; одно сохранённое physical idea на lifetime; range tolerance0.08; Anti-Scalp ratio3 и four-cost policy; portfolio6%/daily4%/3x. Часть добавлений ранее прямо разрешена пользователем, включая canonical TP/BE/Anti-Scalp. Они не стали SOURCE_RULE из-за такого разрешения и сейчас не изменяются.

Первичные SW11 p8 и SW12 p13 запрещают перенос stop; дополнительный DOC20 P0277 предлагает BE после10–15%. Это конфликт источников, а не первичный TP1→BE. В source_pdf_native.py:799–802 старый adverse blocker существует, но текущий MediumTermEngine наследует source_permitted emitter, который лишь записывает roles, а medium emitter их не применяет. Это доказанный пропуск executable gate относительно указанного source prohibition.

## I. Правильно ли реализован universal H1/H4-owner?

Как project policy он реализован и проверен, но как универсальное исходное правило — **EXTRA_RULE_NOT_IN_SOURCE**. Нижний TF не обязан создавать независимую безконтекстную идею; это не доказывает необходимости формального owner объекта. Источники допускают HTF POI/context с младшим trigger. `_macro_context` выбирает первый подходящий строго старший H4/D1 объект; это не одновременная проверка всех четырёх TF.

Gate требует дополнительный формальный context object, но не всегда directional structure: для parent SFP/Range допускается active range вместо structure и не требуется совпадение macro direction. Среди880:337same-direction,281opposite-direction,262без directional structure с range context. Countertrend allowance flag у719 сделок не означает719фактических countertrend trades. Слова «macro structure gate» в начальном checkpoint надо читать с этим уточнением; финальный NO_HTF trace называет его CONTEXT_OBJECT_GATE. Это описание сохранённого кода, без изменения policy.

## J. Все 3 680 NO_HTF_CONTEXT

Воспроизведён точный baseline renderer: concatenate BTC/ETH → sort(known_at,signal_id) → last per physical idea never READY. Доля3680/3817=96,4108%; все case IDs и состояния сохранены в `no_htf_3680_rule_trace.csv` и causal snapshots. Engine causes: {'FORMAL_HIGHER_MACRO_CONTEXT_OBJECT_GATE_POSSIBLY_PLUS_MAIN_GATE': 1496, 'FORMAL_MAIN_SETUP_OR_SETUP_TF_GATE': 2184}.

Для самого этого reason **ENGINE_EXTRA_REJECTION=3680; TRUE_SOURCE_REJECTION доказанных этим reason=0**. Это не утверждение, что все3680 source-valid: остальные исходные условия и последующие machine gates ещё не пройдены; исходный полный resolver неизвестен. Сохранённый refusal не содержит main_valid/context_valid и фактический actual_setup_tf; поле setup_tf — flow-owner htf, поэтому нельзя надёжно восстановить каждый boolean отказа из лога. Где context_tf сохранён, macro существовал; где None, отсутствовал требуемый machine object, что не доказывает отсутствие всей исходной context. Before gate `_active_flow` прошёл. FIRST_DISCOVERY parent может отличаться от последнего physical alias/path; этот предел явно записан. Число доказанно пропущенных прибыльных/source-valid сделок из одного reason **не определено**.

## K–L. Все880 входов и542 losses

`rule_trace_880.csv`, `rule_trace_542_losses.csv` и `trade_rule_evidence.jsonl.gz` включают D1/H4/H1/M15 completed states, applicable machine roles, liquidity, structure, POI, OB, FVG/IMB, OTE, BOS, P/D, FTA READY/PRE_ENTRY, invalidation, trigger, branch и source decision. Состояние TF доступно — это PASS completion, но не автоматический PASS неописанного source AND. Все snapshots frozen до продвижения future mutable BOS/flow.

Прямое нарушение conservative LTF диапазона SW9: **7 сделок, 4 losses**. Adverse liquidity по явно указанной старой contextual pool интерпретации: **751 сделок, 446 losses**. Пересечения учитываются по уникальным trade IDs; окончательные interpreted решения: {'ORIGINAL_TREE_REJECT_UNDER_STATED_INTERPRETATION': 751, 'UNCLEAR_ORIGINAL_TREE': 129}; среди losses: {'ORIGINAL_TREE_REJECT_UNDER_STATED_INTERPRETATION': 446, 'UNCLEAR_ORIGINAL_TREE': 96}.

Эти source-alignment flags не зависят от исхода. Их нельзя все объявить экспертно подтверждёнными false positives исходной стратегии: «значимая» liquidity и полный original branch contract неоднозначны. **Точное число ORIGINAL_TREE_ALLOW и точное число исходно запрещённых542 losers неидентифицируемы**. Нет корректного способа заменить UNCLEAR на ALLOW/REJECT без нового толкования, которое пользователь запретил. CSV сохраняет неопределённость.

Отдельно старый fitted numerical leaf на текущем weighted quote-плане допустил171:101 baseline WIN/70 LOSS, отверг709:237WIN/472LOSS. При full current first target признаках допустил308:176WIN/132LOSS. `frozen_meta_tree_on_880.csv` показывает каждый путь. Это применение неизменного fitted selector с разными определениями target feature, не original source decision, не backtest новой стратегии и не рекомендация удалить losers.

## M. Математическое разложение67,68→38,41

| Переход | Разница WR, п.п. | Что доказано |
|---|---:|---|
| OLD_META_TEST_SELECTED → OLD_TEST_UNFILTERED_INDEPENDENT | 43.5262 | EXACT_SAME_TEST_FROZEN_LEAF_SELECTION |
| OLD_TEST_UNFILTERED_INDEPENDENT → CURRENT_NATIVE_FULL_INDEPENDENT | -10.6512 | DESCRIPTIVE_COMBINED_SCOPE_CHANGE_NOT_SINGLE_CAUSAL_EFFECT |
| CURRENT_NATIVE_FULL_INDEPENDENT → CURRENT_PRIMARY_INDEPENDENT | 0.0229 | DESCRIPTIVE_COMBINED_SCOPE_CHANGE_NOT_SINGLE_CAUSAL_EFFECT |
| CURRENT_PRIMARY_INDEPENDENT → CURRENT_PRIMARY_SHARED | -3.6302 | EXACT_SAME_COHORT_SHARED_ADMISSION_SUBSET_NO_COMMON_RESULT_FLIPS |

Сумма=**29.2677 п.п.**. Старый frozen leaf на том же TEST исключил2970=588WIN+2382LOSS: точный selection lift43,5262п.п. Shared admission baseline исключил1472=480WIN+992LOSS из2352, сохранив880 с тем же знаком результата: точный WR lift3,6302п.п. Case ledgers: `old_tree_TEST_all_leaf_trace.csv`, `capital_admission_2352_to_880.csv`. Различие TEST2026/полногоnative2026/primary2023–2025 смешивает период, инструменты, entries и exits; приписывать его одному условию нельзя. Разный состав нельзя устранить арифметическим сравнением агрегатов.

`entry_universe_comparison.csv` даёт accepted/rejected universe counts по symbol, direction, mapping, branch, month и causal context proxy, отдельно OLD_TEST_ALL/ADMITTED/REJECTED и C_INDEPENDENT/SHARED. Old flow classification и current strictly-higher macro admission — разные определения context; proxy не выдаётся за единую ретроспективную market regime сегментацию. Сохраняются разные ready/execution periods и executionM5vsM15; exact matching всех traded IDs между2026 и2023–2025 невозможно из-за непересекающихся периодов.

Новый source-owner/SL/FTA/exit/account policy действительно меняет проверяемую систему, но один причинный компонент всего падения не установлен. Same-entry exits ниже изолируют только сопровождение. Изменение entry надо проверять после определения source resolver, без P&L-подбора.

## N. Exit edge на тех же880 фактических входах

Модели зарегистрированы до новых exit результатов в `SOURCE_FIDELITY_AUDIT_PROTOCOL.md`. Заморожены actual entry OPEN, цена/quantity/entry fees и текущий initial SL. Stop-first OHLC, adverse gap fill, entry-bar favourable only CLOSE, известные source body exits, fee/slip без изменения. Future duration не используется. Новые exits не перераспределяют будущий capital: это независимые matched cases, не новый shared NAV; MaxDD этих моделей не вычисляется как portfolio.

A diagnostic: сохранённая source-permitted альтернатива fullFTA для non-Range/80–20Range. Exact original MODEL A остаётся UNKNOWN. B1 full current TP1 изолирует allocation/BE; B2 full nearest contextual flow-owner FTA на pre-entry OPEN изолирует другую target selection. C canonical40/30/30+BE; D same40/30/30 без BE. Все5 результатов опубликованы, лучший не выбран.

| Exit model | CLOSED | OPEN | WR% | Gross USDT | Fees | Slippage | Net | PF | Expectancy | AvgR | AvgWin | AvgLoss | MFE R | MAE R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_SOURCE_PERMITTED_EXIT_DIAGNOSTIC | 876 | 0 | 37.79 | -165.26 | 635.46 | 211.82 | -1012.53 | 0.7578 | -1.1559 | -0.1492 | 9.5688 | 7.6694 | 0.9622 | 0.8982 |
| B1_FULL_BASELINE_FIRST_TARGET | 880 | 0 | 38.41 | -85.29 | 636.69 | 212.23 | -934.21 | 0.7772 | -1.0616 | -0.1153 | 9.6411 | 7.7360 | 0.9381 | 0.8751 |
| B2_FULL_OLD_SOURCE_FTA | 876 | 0 | 37.79 | -169.67 | 635.45 | 211.82 | -1016.93 | 0.7567 | -1.1609 | -0.1500 | 9.5555 | 7.6694 | 0.9144 | 0.8854 |
| C_CANONICAL | 880 | 0 | 38.41 | -231.84 | 636.80 | 212.27 | -1080.91 | 0.7422 | -1.2283 | -0.1299 | 9.2070 | 7.7360 | 1.1791 | 0.8835 |
| D_NO_BE | 880 | 0 | 31.93 | -28.44 | 636.83 | 212.28 | -877.56 | 0.7970 | -0.9972 | -0.1184 | 12.2609 | 7.2168 | 1.2857 | 1.0082 |

Gross=reference-price P&L до costs; identity Gross−Fees−Slippage=Net. Историческое поле gross_pnl baseline уже содержит slippage: не вычитать его повторно. MFE/MAE mean в единицах первоначального риска и зависят от длительности наблюдения модели; это outcome diagnostics. UndefinedFTA cases: {'A_SOURCE_PERMITTED_EXIT_DIAGNOSTIC': 4, 'B2_FULL_OLD_SOURCE_FTA': 4}; они сохранены, не подменены дальней целью. Common defined+CLOSED entry sample=876; same-sample результаты отдельно в `matched_exits/summary.json`. OPEN остатки остаются OPEN, EOF не закрываются; не смешивать WR разных censored sets. Все fills и сделки по моделям в matched_exits/*.csv и *.jsonl.gz; `exit_outcome_transitions.csv` связывает каждый flip и P&L delta с неизменным entry.

Точные переходы: B1 сохранил338WIN/542LOSS, изменил271exit time, Net delta+146,7001USDT. D без BE перевёл57WIN→LOSS,0LOSS→WIN;183exit time изменились; Net delta+203,3495USDT при WR−6,4773п.п. B2 nearestFTA на876common закрытых:70WIN→LOSS и64LOSS→WIN,361exit time изменён, matched Net delta+56.5153USDT. Четыре undefined включают1baselineWIN/3LOSS. A partialRange отличие отB2 меняетNet на+4,3984USDT при том же WR. Ни одна из проверенных exit моделей на этих фиксированных входах не восстанавливает68%. Эти outcomes не использованы для выбора production exit.

## O. Стратегические вариантыA/B/C и Anti-Scalp

| Variant | Статус | READY | FILLED | CLOSED | WR | Net | PF | AvgR | DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A точная ORIGINAL | NOT_IDENTIFIABLE | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| B точная ORIGINAL+non-method Anti | DEPENDENT_ON_A | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| C19404ec | VERIFIED_RESUME |6760|880|880|38,4091%|−1080,9067|0,7422|−0,12993|93,2981%|

Нулевых сделок A/B не утверждается: они **не запущены как EXACT**, потому что отсутствует unique executable original contract. Конкретные шесть недостающих resolver с цитатами: `original_contract_gaps.csv`, `exact_variants_identifiability.json`. Выбор full/partial, stop/BE, branch priority, TF ladder, qualitative liquidity и re-entry произвольно создал бы новую стратегию. Это противоречило бы главной задаче. Поэтому точный новый original max/WinRate не заявляется. C complete artifacts проверены через `--resume-existing`, все880 per-trade C diagnostic fills/costs/exits совпали.

C Gross-231.84,Fees636.80,Slip212.27,Net-1080.91,Expectancy-1.2283; holding median9,5h/mean≈25h. Полные LONG/SHORT/setup/branch/year/mapping/holding bin breakdown в `baseline_C_breakdowns.csv`, `strategy_variant_A_B_C.csv` и original summaries. Сигналы baseline — READY output; pre-READY attempts/refusals не названы FILLED.

Anti-Scalp policy не менялась. ON880:338/542,WR38,4091%,Net−1080,91; OFF880:343/537,WR38,9773%,Net−1083,53. Всего845 общих trade IDs, по35 arm-specific. ON-only19WIN/16LOSS; OFF-only24WIN/11LOSS; sign flips общих=0. READY6760vs6796, различие36; вмешательство меняет chronology/capital admission, одинаковое число не означает identical entries. Сам ratio gate не объясняет происхождение всей машинной HTF policy. Target too close соответствует наличию положительной structural target лишь частично; требование именно H4/D1 plus3targets добавлено. Four costs/ratio3 ранее разрешены пользователем, первичные документы не дают этот numerical threshold.

## P–Q. Проверял ли engine изменённую стратегию и есть ли leakage?

Да: extra universal-owner/macro gates, target scope/count, SL expansion, allocation/BE и missing adverse blocker — конкретные доказательства, что baseline не exact original. Это не доказательство, что исходная стратегия прибыльна или что правильное восстановление даст68%.

Old tree: алгоритмический future leakage не доказан; development TEST не untouched OOS. Новые проверки: real-history state prefix/future mutation на9000M15, триcuts,93полных UTC D1; all5440known-time snapshots; same-entry real-history exit prefix/future mutation; BACKTEST/SHADOW parity для всех defined моделей; all880baseline C equality; strict manifests/resume; immutable17 728blobs;582unittests; mypy53sourcefiles; compileall; additive ruff. Detailed scopes и результаты в qa/*.json/log, включая сохранённые первые диагностические ошибки путей/единиц, исправленные до complete результатов. Нет LIVE/private API calls. Prefix probes не являются исчерпывающим доказательством всех возможных рынков, подтверждают проверенные data/code paths.

Дополнительно prefix/future tests проверяют12 обоих направлений H1/H4 contextual target/liquidity probes на заранее известных128барных границах (non-trading QA context); real matched exit tests22chronologically decimated entries×5models=110PASS. Full mode parity4392defined pairs. Known-time audit проверил556824known_at,21760completed_at и остальные formation/test/body times, future evidence не найдено. Full Ruff baseline555=current555, exact diagnostic identity PASS, новых замечаний0. Повторяемые команды и архивный producer hash описаны в `SOURCE_FIDELITY_AUDIT_REPRODUCIBILITY.md`.

## R. Следующий шаг без оптимизации

Установить versioned SOURCE_EXECUTION_CONTRACT: зафиксировать original branch precedence/TF roles, критерии meaningful liquidity/smooth approach, применимые stop alternatives, FTA allocation/remainder, конфликт BE, re-entry/lifecycle. Решения должны происходить по материалам и исходной авторской методологии, до открытия новых outcome результатов; не выбирать их по PF/WR. Затем можно реализовать exact contract в отдельном research adapter и выполнить запрошенные одинаковые BTC/ETH A/B/C с causality/known_at/parity. До этого сохранять baseline и не выдавать одну выбранную альтернативу за исходную стратегию.

В этой поставке добавлены source originals/inventory/matrix, causal snapshots,880/542/3680traces, reconstructed frozen tree, matched exit artifacts, comparison ledgers, QA/scripts/tests/protocol/report. `changed_files.csv` содержит точный additive list относительно19404ec; baseline не затронут. `delivery_manifest.json` фиксирует SHA256/членство новой поставки, вложенные COMPLETE manifests и baseline proof. Stable commits опубликованы только в `medium-term-source-research`; final delivery commit указан в ответе и Git history.
