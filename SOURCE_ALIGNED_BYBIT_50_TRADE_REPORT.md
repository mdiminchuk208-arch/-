# Bybit SOURCE_TRADE_CASE_VALIDATION — первичные PDF

Полный replay завершён: **9 READY → 0 FILLED → 0 CLOSED**. Уникальных opportunities: 9; дубликатов: 0. Основная выборка: 0 первых уникальных закрытых сделок по хронологии entry.

Прочитаны все 54 страницы SW5 (9), SW9 (16), SW11 (8), SW12 (15), SW22 (6): весь текст и все схемы. [Оригиналы, полный текст и SHA256](data/source_materials/primary_pdf_2026_10_09/manifest.json); [постраничная source reconstruction](SOURCE_PDF_PROTOCOL.md) и [native timing correction](SOURCE_PDF_NATIVE_PROTOCOL.md). Первичные SOURCE_RULE отделены от численной машинной интерпретации и выбранных допустимых вариантов. Source protocol опубликован в `18eb8bb`, первоначальная PDF реализация — в `63ab3ae`. Первый PDF replay (9 READY /0FILLED/0CLOSED) сохранён; native timing correction и 504 tests опубликованы в `cbcd30a` до текущих outcomes. Этот этап уже знает результат первоначального PDF прогона, поэтому не выдаётся за полностью слепое исследование.

Все 40 сохранённых native Bybit серий / 993575 свечей проверены по SHA, count, identity и alignment; 10 символов, 5m/15m/60m/240m. Это ранее просмотренная история 2026 DEVELOPMENT, не OOS. Нет интерполяции, синтетических свечей, LIVE/private API. `trade_entry_allowed=false`.

Основные mappings: 15/5,60/5,60/15,240/5,240/15. Каждый уникальный READY получает отдельный reference account 1170 USDT, риск 23.4 USDT (2%) с учётом базовых затрат. Общая занятость и portfolio budget не подавляют trade cases. Dedup выполняется до fills/outcomes: первый READY, затем higher HTF/lower LTF/fixed symbol priority/ID. Разные визиты OB различаются. Все CLOSED сверх первых 50 и все OPEN сохранены; endpoint не закрывает сделку принудительно.

## Новый funnel

| Этап — строго пять mappings | Количество |
|---|---:|
| setups | 55734 |
| qualified_structure | 8566 |
| liquidity_passed | 179 |
| poi_passed | 179 |
| order_flow_passed | 9 |
| pd_passed | 9 |
| READY | 9 |
| unique_opportunities | 9 |
| duplicates | 0 |
| FILLED | 0 |
| CLOSED | 0 |
| OPEN_CENSORED | 0 |
| PENDING_CENSORED | 0 |

Source_contexts считаются на TF до разветвления по mappings и могут включать 240/60; таблица выше вычислена непосредственно по строгим setup artifacts. Стадии являются accumulated ever-passed counters; отменённые setups остаются в funnel.

## WIN/LOSS и результаты

| Метрика | fc61f35: старый последовательный portfolio | 74a6f8d: cases без PDF | Первоначальный PDF / HTF close | Исправленный native PDF cases |
|---|---:|---:|---:|---:|
| READY | 647 | 3 | 9 | 9 |
| FILLED | 14 | 0 | 0 | 0 |
| CLOSED | 13 | 0 | 0 | 0 |
| Wins | 2 | 0 | 0 | 0 |
| Losses | 11 | 0 | 0 | 0 |
| BE | 0 | 0 | 0 | 0 |
| WinRate (%) | 15.384615 | N/A | N/A | N/A |
| ProfitFactor | 0.14037608 | N/A | N/A | N/A |
| Expectancy | -15.416649 | N/A | N/A | N/A |
| AvgR | -0.71226448 | N/A | N/A | N/A |
| MedianR | -1 | N/A | N/A | N/A |
| NetPnL | -200.41643 | 0 | 0 | 0 |
| Fees | 39.332695 | 0 | 0 | 0 |
| Slippage | 13.110893 | 0 | 0 | 0 |

PF = сумма положительных net PnL / абсолютная сумма отрицательных net PnL. Expectancy = средний net PnL на CLOSED, Avg R = средний net PnL / первоначальный planned risk. WIN/LOSS определяется net PnL после затрат. N/A означает неопределённую метрику. Сумма независимых case PnL не является NAV общего торгового счёта; portfolio DD к ней не применяется. fc61f35 и новый результат имеют разные admission/entry/exit contracts, поэтому разницу нельзя приписывать только качеству стратегии. 0 CLOSED в 74a6f8d не было окончательной оценкой метода.

## Все FILLED trade cases

| # | ID | Symbol | L/S | HTF/LTF | HTF/local POI | READY | Fill interval start | Entry | SL | Targets/fractions | Exit | Status/result | Net PnL | R | Fees | Slippage |
|---:|---|---|---|---|---|---|---|---:|---:|---|---|---|---:|---:|---:|---:|

FILLED trade cases отсутствуют; WIN/LOSS выборки нет.

[Полные сделки со всеми fills и source snapshots](data/reports/source_pdf_native_bybit_2026_10_09/cases.jsonl.gz); [первые 50 или фактическое меньшее число](data/reports/source_pdf_native_bybit_2026_10_09/primary_cases.jsonl.gz); [все решения/отмены](data/reports/source_pdf_native_bybit_2026_10_09/case_decisions.jsonl.gz).

Комиссия 0.06% и slippage 0.02% на каждую сторону — фиксированные project assumptions. Funding, spread, tick sizes и market impact недоступны и не моделируются. Время fill — интервал реальной 5m свечи, известный на CLOSE. Stop-first при неоднозначном OHLC, favorable entry-bar TP требует CLOSE proof; adverse gap исполняется по OPEN. Истинный intrabar MAE неизвестен: сохранён только OHLC upper bound после entry bar; для закрытия в entry bar MAE — N/A.

## Все READY и исполнение лимитов

| ID | Symbol | Mapping | Visit | HTF/local POI | READY | Quote | SL | Targets | Execution decisions |
|---|---|---|---:|---|---|---:|---:|---|---|
| 6c344f059a7c60a550543e0f | ETHUSDT | 15/5 | 1 | STB/ORDER_BLOCK | 2026-04-04T17:25:00+00:00 | 2048.82 | 2043 | [2103.1] | 2026-04-04T17:25:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-04-05T04:50:00+00:00: CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN |
| 03f04beb4424d34ddc690938 | AVAXUSDT | 15/5 | 1 | DEMAND/STB | 2026-05-20T15:30:00+00:00 | 9.185 | 9.157 | [9.423] | 2026-05-20T15:30:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-05-20T16:25:00+00:00: CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN |
| 26ebd579151eabf9cc29764e | XRPUSDT | 15/5 | 1 | SUPPLY/ORDER_BLOCK | 2026-05-26T21:50:00+00:00 | 1.3614 | 1.3651 | [1.2883] | 2026-05-26T21:50:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-05-27T04:50:00+00:00: CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN |
| 18400ffd6f66057d5f2900c7 | AVAXUSDT | 60/15 | 1 | BTS/BTS | 2026-05-29T19:00:00+00:00 | 8.9145 | 8.979 | [8.356] | 2026-05-29T19:00:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-05-30T00:15:00+00:00: CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN |
| a2ce1597eb140da12d811ab2 | SOLUSDT | 15/5 | 1 | STB/STB | 2026-07-07T16:35:00+00:00 | 80.895 | 80.46 | [82.55] | 2026-07-07T16:35:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-07-07T17:30:00+00:00: CANCEL_FLOW_DESTINATION_TESTED |
| 0429a4616fcdc8c1715dc056 | DOGEUSDT | 15/5 | 1 | STB/DEMAND | 2026-07-07T17:20:00+00:00 | 0.074005 | 0.07366 | [0.07644] | 2026-07-07T17:20:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-07-07T17:30:00+00:00: CANCEL_GLOBAL_ORDER_FLOW_INACTIVE |
| 3031446d683902755d235932 | DOGEUSDT | 15/5 | 1 | STB/ORDER_BLOCK | 2026-08-17T16:15:00+00:00 | 0.07012 | 0.07005 | [0.07102] | 2026-08-17T16:15:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-08-17T16:45:00+00:00: CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN |
| 18435abb9bf479f85cb2d2f7 | SOLUSDT | 15/5 | 1 | STB/STB | 2026-09-03T01:35:00+00:00 | 99.48 | 99.13 | [101.31] | 2026-09-03T01:35:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-09-03T01:50:00+00:00: CANCEL_CONFIRMED_LTF_STRUCTURE_BROKEN |
| 04fb0127b7b01c6e66209bb7 | BTCUSDT | 15/5 | 1 | STB/DEMAND | 2026-09-14T14:00:00+00:00 | 77560.75 | 77429.5 | [78855.4] | 2026-09-14T14:00:00+00:00: VIRTUAL_LIMIT_PENDING; 2026-09-14T16:20:00+00:00: CANCEL_FLOW_DESTINATION_TESTED |

Все 9 active limits независимо прослежены по фактическим native 5m свечам. Quote не достигнут до причинной отмены: 6 сломов подтверждённой LTF структуры, 2 теста глобальной цели и 1 прекращение Order Flow. [Все проверенные интервалы и source cancellations](data/reports/source_pdf_native_qa_2026_10_09/execution_audit.json).

## Что изменилось относительно fc61f35 и 74a6f8d

- Уже известная HTF POI теперь наблюдается на CLOSED native 5m, без ожидания HTF close (SW9 p4–6), без формирования/чтения незакрытой HTF свечи. Один визит не пересчитывается на HTF close. FTA уже позади текущего LTF close блокирует READY; first test FTA наблюдается по native 5m.
- STB/BTS: полный key-to-sweep диапазон и его полное поглощение по SW22 p2–4; quote .5 и SL вне всей манипуляции заменяют single sweep candle proxy.
- OB: реальное снятие ликвидности исходной свечой и немедленное поглощение по SW9 p2; IMB — confluence, численное body dominance не выдается за PDF. LTF OB должен пересекать HTF POI.
- SW9 p3: повторный OB теперь возможен только отдельным визитом с новой LTF цепочкой; D/S остаётся свежим первым тестом. Dedup использует фактический визит.
- Order Flow: ключевые structural pairs вместо последних произвольных внутренних swings; подтверждённое continuation может создать flow. Цель заморожена до её теста, без переназначения на следующем CONF (SW22 p5–6).
- FTA: первая противоположная HTF POI по SW9 p16; случайный близкий LTF FVG больше не определяет обязательный выход. Технический SL находится вне wick boundary.
- Дальние исторические equal pools вне текущего structural leg не считаются универсальным блокером; meaningful liquidity внутри leg, в том числе ниже SL, учитывается.
- SW11 подтверждает planned risk/SL/TP и .25–2%; SW12 не добавляет обязательных RSI/volume/ATR сигналов. Численные альтернативы не выбирались по новому PnL.
- Из fc61f35 уже ранее исправлены Range external POI/reclaim/retest, независимый D/S без failed-OB fallback и полный causal LTF chain; они сохранены. Новый код изолирован от canonical.

Три прежних READY 74a6f8d ниже сопоставлены с новыми READY того же symbol/mapping и UTC-дня. Это сопоставление эпизодов, без объявления их одинаковыми opportunities.

| 74a6f8d ID / symbol / mapping | Old READY / quote / SL / targets | Native PDF READY того же дня / quote / SL / targets |
|---|---|---|
| afd834d7916213bcbe1e44e9 / DOGEUSDT / 15/5 | 2026-08-17T16:15:00+00:00 / 0.070085 / 0.07005 / [0.0706] | 2026-08-17T16:15:00+00:00 / 0.07012 / 0.07005 / [0.07102] |
| ea27f65b73e584faa2bfc806 / BTCUSDT / 60/5 | 2026-09-06T23:00:00+00:00 / 79672.9 / 79604.6 / [80188.09999999999, 80787.0] | NONE |
| 54fdfab3931bf4e19debb560 / BTCUSDT / 15/5 | 2026-09-14T13:50:00+00:00 / 77524.75 / 77429.5 / [78542.2] | 2026-09-14T14:00:00+00:00 / 77560.75 / 77429.5 / [78855.4] |

Native timing correction сохранила 9 READY и их времена, но исправила clock HTF взаимодействий и свежесть FTA. Например, у ETH 2026-04-04 первая цель изменена с 2055.41 (уже протестирована native 5m) на свежую 2103.1. Новые fills/CLOSED не появились. Этап зарегистрирован после исходных PDF outcomes и потому имеет явно указанную contamination.

## Старые losses: source audit без отбора по PnL

Проверены все 13 fc61f35 CLOSED, включая WIN, на точных old READY и entry cutoffs. FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION означает непрохождение данной зарегистрированной source реконструкции; это не доказательство невозможности всех discretionary вариантов. Отличающиеся допустимые quote/SL и исключённый 240/60 сами по себе не доказывают source false positive. Из 11 прежних LOSS: **10 false positives данной source реализации**, DOGE 240/15 `c1bc1cb68a185d4492c8b9e6` — UNCERTAIN_OR_DIFFERENT_PERMITTED_VARIANT. Из 2 WIN: один также false positive, один остаётся uncertain; положительный PnL не заменяет source proof.

| Old ID | Symbol/mapping | Old result/PnL | Audit | Hard reasons | Other contract differences |
|---|---|---|---|---|---|
| c0eb9c4daf48e1f3e98d72f8 | ETHUSDT 60/15 | LOSS -23.4 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| 9c181eee25ee9e39d8b5a523 | LINKUSDT 60/5 | LOSS -22.932 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY |  |
| c8d326347c6830f75b573f88 | DOGEUSDT 15/5 | LOSS -22.47336 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| ca98f11190187b5877332b3a | BTCUSDT 15/5 | LOSS -22.023893 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| c1bc1cb68a185d4492c8b9e6 | DOGEUSDT 240/15 | LOSS -21.583415 | UNCERTAIN_OR_DIFFERENT_PERMITTED_VARIANT |  | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| 235e7ba6c224826bf8e64cd2 | XRPUSDT 240/15 | LOSS -21.151747 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| 25faa78ab0a2eea4d4c48c20 | DOGEUSDT 240/60 | LOSS -20.728712 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY | 240_60_OUTSIDE_STRICT_CONSERVATIVE_SCOPE; OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| d5cd448d6c02f037d76c9d35 | LTCUSDT 60/15 | LOSS -20.314137 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| b58c6bbb565b806e85fa6798 | LINKUSDT 240/15 | LOSS -19.907855 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | RANGE_WITHOUT_REQUIRED_CAUSAL_EXTERNAL_POI; NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| d6b7416116c201f0a70c378c | LINKUSDT 240/15 | LOSS -19.509698 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| fd05901bf55ee3c53409bed9 | LINKUSDT 240/15 | LOSS -19.119504 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | NO_CAUSALLY_ACTIVE_GLOBAL_ORDER_FLOW_AT_OLD_READY; OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| 3fa88b97bdbbf06988a7684b | XRPUSDT 240/5 | WIN 3.7220675 | UNCERTAIN_OR_DIFFERENT_PERMITTED_VARIANT |  | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |
| 07b320b636a8d15d4ed8af6d | XRPUSDT 15/5 | WIN 29.005818 | FALSE_POSITIVE_REGISTERED_SOURCE_IMPLEMENTATION | OLD_DS_WAS_FVG_DEPENDENT_FAILED_OB_FALLBACK | OLD_UNIVERSAL_ENTRY_DIFFERS_FROM_REGISTERED_POI_POLICY |

Наиболее конкретный source defect прежних Range losses: необходимо доказать существовавшую до deviation внешнюю typed POI и её фактическое взаимодействие, а SFP-only не разрешает вход (сохранённый SW10). Ниже приведены фактические кандидаты новой реконструкции.

| Old Range loss ID | External POI candidates at old cutoff |
|---|---|
| ca98f11190187b5877332b3a | NONE |
| 25faa78ab0a2eea4d4c48c20 | NONE |
| 9c181eee25ee9e39d8b5a523 | NONE |
| b58c6bbb565b806e85fa6798 | NONE |
| d5cd448d6c02f037d76c9d35 | NONE |

Отсутствие flow/POI в машинной реконструкции ограничено её объявленным способом выбора ключей и зон. Нельзя считать каждый старый LOSS автоматически ошибкой. Исходные пять losses OLD7 также сохранены и независимо проверены на READY/entry; verdict WAIT не превращается в подтверждённый false positive.

| Original OLD7 loss | Mapping | PnL | READY verdict/reasons | Entry verdict/reasons |
|---|---|---:|---|---|
| XRPUSDT | 60/5 | -23.4 | REJECT: HTF_ORDER_FLOW_DIRECTION_BROKEN; LTF_CURRENT_STRUCTURE_BULLISH; MEANINGFUL_UNSWEPT_LIQUIDITY_BETWEEN_ENTRY_AND_SL | REJECT: HTF_ORDER_FLOW_DIRECTION_BROKEN; LTF_CURRENT_STRUCTURE_BULLISH; MEANINGFUL_UNSWEPT_LIQUIDITY_BETWEEN_ENTRY_AND_SL |
| BNBUSDT | 240/5 | -23.4 | WAIT: HTF_ORDER_FLOW_DIRECTION_BROKEN; NO_ACTIVE_CONF_AFTER_OLD_BOS | REJECT: HTF_ORDER_FLOW_DIRECTION_BROKEN; LTF_CURRENT_STRUCTURE_BEARISH |
| BNBUSDT | 240/15 | -23.4 | WAIT: HTF_ORDER_FLOW_DIRECTION_BROKEN; LTF_CURRENT_STRUCTURE_BROKEN; OLD_LOCAL_POI_ALREADY_TESTED_OR_INVALIDATED | WAIT: HTF_ORDER_FLOW_DIRECTION_BROKEN; LTF_CURRENT_STRUCTURE_BROKEN; OLD_LOCAL_POI_ALREADY_TESTED_OR_INVALIDATED |
| AVAXUSDT | 60/15 | -23.4 | REJECT: HTF_ORDER_FLOW_DIRECTION_BEARISH; LTF_CURRENT_STRUCTURE_BEARISH; OUTSIDE_REQUIRED_DISCOUNT_PREMIUM | REJECT: HTF_ORDER_FLOW_DIRECTION_BEARISH; LTF_CURRENT_STRUCTURE_BROKEN; OLD_LOCAL_POI_ALREADY_TESTED_OR_INVALIDATED; OUTSIDE_REQUIRED_DISCOUNT_PREMIUM |
| AVAXUSDT | 240/60 | -23.623317 | REJECT: HTF_ORDER_FLOW_DIRECTION_BULLISH; NO_TYPED_QUALIFIED_HTF_POI_SUPPORTING_OLD_GAP; NO_ACTIVE_CONF_AFTER_OLD_BOS | REJECT: HTF_ORDER_FLOW_DIRECTION_BULLISH; NO_TYPED_QUALIFIED_HTF_POI_SUPPORTING_OLD_GAP; NO_ACTIVE_CONF_AFTER_OLD_BOS |

## Отдельные diagnostics и незавершённые setups

ANY_TF 240/60: 0 READY / 0 FILLED / 0 CLOSED. Не включён в primary.

Однопозиционный portfolio: 0 entries / 0 CLOSED, realized net 0, final NAV 1170; это отдельный результат с budget/occupancy.

| Последний blocker/setup outcome, strict mappings | Количество |
|---|---:|
| HTF_FLOW_DIRECTION_CHANGED | 26273 |
| OB_NEW_VISIT_REQUIRES_NEW_LTF_REACTION | 16621 |
| HTF_POI_BODY_INVALIDATION | 9969 |
| DEMAND_SUPPLY_SECOND_VISIT_NOT_FRESH | 2646 |
| HTF_RAID_EXTREME_BODY_INVALIDATION | 157 |
| WAIT_LTF_RAID_BOS_NEW_STRUCTURE_CONF | 38 |
| WAIT_CAUSAL_RAID_BOS_NEW_STRUCTURE_CONF_ORDER | 11 |
| WAIT_NEW_FRESH_LTF_POI | 8 |
| CONFIRMED_LTF_STRUCTURE_BROKEN | 6 |
| FLOW_DESTINATION_TESTED | 2 |
| WAIT_MEANINGFUL_LIQUIDITY_AGAINST_SETUP | 2 |
| GLOBAL_ORDER_FLOW_INACTIVE | 1 |

## QA, сохранность и границы вывода

До текущих outcomes: 504 tests PASS, compileall PASS, Ruff E9/F PASS, mypy PASS; [pre-outcome registration](data/reports/source_pdf_native_qa_2026_10_09/pre_outcome_registration.json). Для итогового причинного/ledger/hash/resume QA см. [QA receipt](data/reports/source_pdf_native_qa_2026_10_09/delivery_receipt.json). Итоговые 504 tests / compileall / Ruff E9F / mypy PASS. Nonempty prefix SOL: 67570 реальных native свечей, 1 READY, 1799 flows, 102 Range audits — exact full/prefix match и future mutation всех 4 TF PASS. Все 9 READY имеют причинные timestamps и свежие FTA/global targets по независимому native OHLC check. 93 core artifact hashes, 27 implementation files и все 40 inputs проверены. Verified COMPLETE resume не изменил ни одного файла. Прежние scripts/tests/исторические артефакты сохранены; отчёт 74a6f8d [сохранён дословно](data/reports/source_cases_74a6f8d_intermediate/report.md). Canonical TP40/30/30, текущий SL и cost-adjusted BE после TP1 не изменены.

Полный replay исчерпывает всю доступную проверенную Bybit историю для зафиксированной реализации. Получено 0 уникальных CLOSED; цель 50 не достигнута. Это фактический максимум данной policy на этих данных, а не доказанный максимум всех допустимых source вариантов. PDF задают качественные POI, варианты SL/входа, но не полный единственный вычислимый алгоритм. Все такие решения объявлены заранее. Разреженная DEVELOPMENT выборка не подтверждает edge или LIVE readiness.
