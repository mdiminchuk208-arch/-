# Source-permitted physical cases — current continuation checkpoint

Полный replay завершён:40 native Bybit серий /993575 свечей /10 символов.
**19448 physical READY → 16351 FILLED → 16333 CLOSED**,
OPEN=18, PENDING=118; endpoint не force-close.
Цель достигнута: первые50 уникальных source-valid FILLED+CLOSED физически различных cases,
хронологически по реальным native fill-интервалам и фиксированному tie order.
**WIN=12,LOSS=38,BE=0; WR=24.00%;
PF=0.31411766; Expectancy=-11.88246634 USDT;
AvgR=-0.50779771; NetPnL=-594.12331714 USDT.**
Полные метрики50/all-CLOSED, all38cohorts, разбивки, все сделки и source evidence сохранены.
Расширение истории для цели50 не требуется; утверждение максимума Bybit universe не делается.

Первичные5PDF/54страницы и ZIP/DOCX прочитаны и сохранены.
Протокол7c47621, движок7f9782f, physical424d663, SFP bodyd87edb1,
bounded execution096e225 опубликованы до финальных outcomes; полный replay artifacts0fc7246 опубликован.
Все15 paths самостоятельны; primary union выбирается по earliest valid READY/registered precedence
до исполнения, global physical aliases ставятся до cohort filtering; later winner не заменяет выбор.
SourceFTA/Range80/20/SFPATR exits исследуются отдельно от frozen canonical.
CanonicalTP40/30/30, текущийSL и cost-adjusted BE послеTP1 неизменны.
Независимый case:reference1170 USDT, planned risk2%=23.4 с costs; shared occupancy/NAV не применяется.
Development2026 уже просмотрена; OOS/прибыльность стратегии не объявляются. Даты отчёта Asia/Yekaterinburg(+05).

QA:548tests, compileall, Ruff zero new /555 inherited, mypy46files PASS.
Full source/native/identity96,954variants/46,589nativeSFPbodyevents/23,812ATRstops PASS;
реальный14293bars prefix/all15paths +future mutation4TF PASS.
Ledger76,524caseinstances, costs/risk/no-lookahead/cancellation/selection/physicaldedup PASS.
Все40inputSHA/gap audit PASS; baseline15385d466 blobs и более ранние artifacts неизменны.
Exact resumes:152native detector artifacts +1118physical execution artifacts, все SHA unchanged, replay=false.
Detector corpus COMPLETE с явным scopeCORPUS_ONLY после OOM provisional aggregation32GiB;
primary execution COMPLETE в отдельном physical root. Исходные попытки/logs не удалены.
Verifier extra-CLOSE assertion исправлен по DOC16P0082–87 и ранее зарегистрированному inclusiveBOS timing;
шесть same-CLOSE cases допустимы, источник/quotes/stops/targets/selection/PnL не менялись.

Старые13fc61f35 cases проверены на точных old READY/entry cutoffs и всех новых source paths.
10старыхLOSS остаются false positives strict projection, без автоматического переноса на весь source universe.
DOGE240/15:точная старая FTA уже тестировалась native5m CLOSE2026-04-12T20:45UTC
доREADY21:00UTC; старый план false positive зарегистрированного fresh-FTA contract.
Другая formation/quote/target остаётся отдельным вариантом; старый UNCERTAIN и все snapshots сохранены.
Все179старыхOF контекстов,9quotes и18controlled cancel replays доступны в новом отчёте.
Frozen robustness45studies и exit88cases/301variants/264Aparity сохранены без повторного дорогого replay.

[Итоговый отчёт](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md).
[Все50 CSV](data/reports/source_permitted_analysis_2026_10_10/first50.csv).
[Полный union CSV.gz](data/reports/source_permitted_analysis_2026_10_10/all_physical_union_cases.csv.gz).
[Source protocol](SOURCE_PERMITTED_PROTOCOL.md).
[QA receipts](data/reports/source_permitted_qa_2026_10_10).
Только BACKTEST/SHADOW; **trade_entry_allowed=false**; без LIVE/private exchange API/orders.

---

## Historical checkpoint through d46646f — superseded by the source-permitted result above

# Primary-PDF source cases — current continuation checkpoint

Все настоящие SW5/SW9/SW11/SW12/SW22 PDF сохранены и полностью прочитаны:
54 страницы, весь текст и все схемы. `SOURCE_PDF_PROTOCOL.md` содержит
постраничные SOURCE_RULE и отдельно обозначенные машинные решения.
Source protocol опубликован в `18eb8bb`, первоначальный PDF движок в `63ab3ae`,
native timing correction в `cbcd30a` до результатов повторного replay.
Последняя policy: `source-primary-pdf-native-2`; исходный PDF replay сохранён.
Timing correction знает первый результат и не объявляется слепым исследованием.

**Полный Bybit SOURCE_TRADE_CASE_VALIDATION завершён: 9 READY → 0 FILLED → 0 CLOSED.**
40 native серий / 993575 свечей / 10 символов, без интерполяции и новых загрузок.
Strict mappings:15/5,60/5,60/15,240/5,240/15; ANY_TF240/60 отдельно:0 READY.
Funnel:55734 setups → 8566 qualified_structure → 179 liquidity/POI →
9 order_flow/PD → 9 unique READY; duplicates=0, OPEN/PENDING=0.
Все девять quotes независимо проверены по фактическим активным native 5m барам:
до fill они отменены — 6 LTF structure breaks, 2 destination tests, 1 inactive flow.
WIN=0,LOSS=0,NetPnL=0; WinRate/PF/Expectancy/AvgR=N/A, поскольку CLOSED нет.
Риск каждого независимого случая1170×2%=23.4, budget/occupancy не блокируют cases.
Отдельный однопозиционный portfolio также0entries, cash/NAV1170.

Цель 50 CLOSED не достигнута. Исчерпана вся доступная история для зафиксированной
машинной source реализации: её максимум CLOSED=0. Это не доказательство
максимума всех качественных discretionary вариантов PDF и не оценка edge.
2026 история DEVELOPMENT, уже просмотренная; не OOS. Правила не подгонялись под PnL.
Все 13 старых fc61f35 CLOSED проверены на точных READY/entry cutoffs:
10 из11LOSS — false positives данной реконструкции; DOGE240/15
`c1bc1cb68a185d4492c8b9e6` — uncertain/другой разрешённый вариант.
Один прежний WIN также false positive; причины и snapshots сохранены в отчёте.
74a6f8d и исходный PDF replay сохранены со всеми scripts/tests/artifacts.

```bash
python scripts/run_source_pdf_native_bybit.py --output data/reports/source_pdf_native_bybit_2026_10_09 --resume-existing --workers 4
python scripts/verify_primary_pdfs.py
python scripts/verify_source_pdf_native_evidence.py --input data/reports/source_pdf_native_bybit_2026_10_09 --symbol SOLUSDT --cutoff 2026-07-07T16:35:00+00:00 --output /tmp/source_pdf_native_evidence.json
python scripts/audit_source_pdf_native_execution.py --input data/reports/source_pdf_native_bybit_2026_10_09 --output /tmp/source_pdf_native_execution.json
python scripts/verify_source_pdf_preservation.py
```

QA:504 tests PASS, compileall/RuffE9F/mypy PASS. Nonempty SOL prefix67570
native свечей:1READY/1799flows/102Range audits совпадают с full replay;
future mutation всех4TF PASS. Все9READY проверены по causal timestamps,
ключевой структуре и независимой реальной свежести FTA/global target.
93core artifacts/27implementation files/40input hashes PASS.
Verified COMPLETE `--resume-existing`:10сегментов, все105файлов неизменны.
Byte-exact сохранены все15069 старых Git blobs74a6f8d и15258 blobs
pre-outcome этапаcbcd30a; новый ledger QA helper намеренно дополнен.
57baseline registered Git hashes PASS. Frozen robustness/exit исследования
уже завершены; exit parity recheck88cases/301variants/264Achecks сохранён,
без повторного дорогого перерасчёта и без изменения canonical.
TP40/30/30, текущий SL, cost-adjusted BE послеTP1 неизменны.
Только BACKTEST/SHADOW, `trade_entry_allowed=false`, без LIVE/private API/orders.

[Все результаты, сравнение, READY и старые losses](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md).
[Итоговый QA receipt](data/reports/source_pdf_native_qa_2026_10_09/delivery_receipt.json).

## Historical 74a6f8d checkpoint — superseded below

# Corrected source cases — historical continuation checkpoint

Published implementation before corrected outcomes: `742fda0`; initial correction
protocol `363fa01`. Full40 native Bybit series /993575 candles /10symbols completed.
**SOURCE_TRADE_CASE_VALIDATION:3 unique READY,0 FILLED,0 CLOSED,0 OPEN/PENDING.**
Maximum observed closures under this registered machine interpretation =0. This
is not an exhaustive source/discretionary maximum and cannot assess strategy edge.
All3 entry quotes were never touched during their active real5m intervals; limits
cancelled on LTF break, FTA/destination test or OPEN beyond the SL–FTA interval.
Shared occupancy and budget did not reject any independent case.

Strict mappings15/5,60/5,60/15,240/5,240/15;240/60 is separate ANY_TF research(0READY).
Separate PORTFOLIO_SIMULATION also0entries, cash/NAV1170; not primary cases.
Old13 closures are a flawed intermediate policy result, preserved verbatim in
`data/reports/source_bybit_fc61f35_intermediate/report.md` and original artifacts.
All13 fail the declared corrected executable contract; all5 oldRange losses lack
reconstructed causal qualifying external POI, and240/60 is out of strict scope.
Alternative source-allowed quotes/stops alone are not a literal methodology defect.

Five latest purported PDF uploads remain identical Windows shortcuts. Actual
SW5/9/11/12/22 PDF contents are still absent; summaries were not promoted to
SOURCE_RULE. Missing originals block complete methodology certification, not the
completed available-data machine replay. See attachment receipt and report.

```bash
python scripts/run_source_cases_bybit.py --output data/reports/source_cases_bybit_2026_10_09 --resume-existing --workers 4
python scripts/verify_source_case_evidence.py --input data/reports/source_cases_bybit_2026_10_09 --output /tmp/source_case_evidence.json
python scripts/audit_source_pending_limits.py --input data/reports/source_cases_bybit_2026_10_09 --output /tmp/pending_order_audit.json
```

Use the current locked source context; changed code/inputs/artifacts fail resume.
Do not update expected hashes. New policies require a fresh output; preserve all
existing results. The interrupted pre-outcome QA pass has exact code snapshots.
Old `run_source_bybit.py` resume requires its originalfc61f35 registered context,
including the old source registry; the new registry correctly changes that hash.
Current old-run manifest/input/committed-code checks passed without rerunning it.

QA:489full tests/18targeted PASS; compileall/RuffE9F/mypy PASS; real14,293-bar prefix,
172flow generations/20Range audits and4TF future mutation PASS. Additional96,088-bar
BTC prefix at the last emitted READY:2signals/1cancellation/1131flows/159Range audits
match exactly;4TF future mutation PASS. Cutoff selected from source metadata, notPnL. All3 READY source
proofs and93manifest artifact hashes verified. Actual trade risk/cost ledger has
0rows; nonempty execution/cost/occupancy checks use labelled constructed unit tests.
QA and independent every-active-bar no-fill proof: `data/reports/source_case_qa_2026_10_09`.
No frozen research rerun, baselineTP40/30/30/SL/cost-adjustedTP1BE unchanged.
Only BACKTEST/SHADOW,trade_entry_allowed=false,noLIVE/private API/orders.

[Full comparison and evidence](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md).
[Registered correction choices](SOURCE_CORRECTION_PROTOCOL.md).

## Historical checkpoints below — superseded machine-policy descriptions

# Strategy Engine: завершённое зарегистрированное исследование

## Итог нового source replay после получения ZIP — 2026-10-09

Полный цикл завершён на сохранённых native Bybit data: **40 series / 993,575
candles / 10 symbols / 6 mappings**. По заранее зафиксированной машинной
интерпретации доступных оригиналов **MAX CLOSED = 13**, ещё **1 OPEN** на правой
границе истории. Всего 647 READY и 14 виртуальных входов одного последовательного
счёта. Закрытые: 2 WIN / 11 LOSS, net PnL **−200.41643367 USDT**, PF
**0.14037608**, expectancy **−15.41664874 USDT**, mean R **−0.71226448**.
Никакие параметры по PnL не выбраны; 50 CLOSED не объявляются достигнутыми.

Архив прочитан: 8 реальных DOCX и 122 уникальные схемы; ожидаемые SW5/7/9/11/12/22
содержат только shortcuts. Это ограничивает буквальную source-сертификацию,
но полный historical replay выполнен. Правила и интерпретации:
[SOURCE_RECONSTRUCTION_2026_10_09.md](SOURCE_RECONSTRUCTION_2026_10_09.md).
Все сделки, funnel, старые пять losses и OLD vs NEW:
[SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md).

Отдельные engine / exits / risk: `source_engine.py`, `source_portfolio.py`.
Frozen canonical TP40/30/30, SL и BE после TP1 сохранены в прежнем runtime;
новый source replay использует объявленный FTA / Range80/20, исходный технический
SL без автоматического BE и риск2% с базовыми затратами. Только BACKTEST/SHADOW;
`trade_entry_allowed=false`, LIVE/private API отсутствуют.

Проверяемое продолжение готового нового прогона:

```bash
python scripts/run_source_bybit.py --output data/reports/source_bybit_2026_10_09_final --resume-existing
python scripts/verify_source_bybit_evidence.py --input data/reports/source_bybit_2026_10_09_final --output /tmp/source_evidence_receipt.json
```

Resume проверяет код, policy, input SHA, 10 segments и все core artifacts,
после чего возвращает `VERIFIED_COMPLETE_NO_MUTATION`. Проверьте полный lock;
не обновляйте ожидаемые SHA для обхода несовпадения. При изменении engine нужен
новый output; старые и диагностические прогоны сохранены с точными snapshots.

**471 tests PASS**, compileall, Ruff E9/F, mypy и safety PASS. Реальный BTC prefix
до 2026-03-01 воспроизводит 6 signals / 6 cancellations точно. Аудит всех647
READY подтверждает cutoff; 14 уникальных входов не перекрываются, R и затраты
пересчитаны. QA receipts находятся в `data/reports/source_bybit_qa_final_2026_10_09`.
Дорогие frozen studies не перезапускались. Раздел ниже — сохранённый предыдущий
checkpoint до предоставления оригинального ZIP.

## Проверка продолжения на текущем main — 2026-10-09

Завершённость ниже относится к frozen research baseline, а не к полной
source-сертификации текущего engine. После исследования source-gate изменил
`replay.py` и replay CLI; исходный baseline hash guard правильно отклоняет
прямой запуск старого pipeline на текущем main. Не заменяйте ожидаемые SHA.

Для проверки сохранённых studies с исходным runtime без отката main:

```bash
python scripts/verify_frozen_research_resume.py --workers 4 --output data/reports/fresh_resume_validation
```

Нужен новый output path. Helper проверяет сохранённые артефакты и source context,
восстанавливает 57 frozen файлов из Git в игнорируемом temporary runtime и
использует проверяемый `--resume-existing` для сохранённых exit cases.
Предыдущие historical artifacts остаются неизменными.

Новый per-trade source audit и конкретные blockers полного Bybit source validation:
[SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md).
Оригинальный `Криптология.zip` недоступен в этой задаче; 50 source-valid CLOSED
trades не получены и новый полный source-aligned backtest не объявлен завершённым.

Все зарегистрированные historical, VALIDATION, retrospective HOLDOUT, walk-forward, execution, POI и exit sensitivity studies завершены. Полный inventory и итоговые таблицы имеют `complete=true`.

Все 21 исходных fingerprints восстановлены точно; 57 canonical source/config SHA неизменны. Canonical TP 40/30/30, inclusive wick-touch и `trade_entry_allowed=false` сохранены. Варианты не выбраны для canonical.

Full tests: **439 PASS**, lint E9/F и mypy PASS. Результаты и необходимые для продолжения артефакты сохранены в Git.

Итоговые выводы и ограничения: [robustness report](ROBUSTNESS_RESEARCH_REPORT.md) и [exit management report](EXIT_MANAGEMENT_RESEARCH_REPORT.md). Отдельные chronological holdout portfolios не объединены в один account; это retrospective validation, не prospective OOS.

## Завершённая точка передачи

Для проверки и повторного использования сохранённых результатов:

```bash
PYTHONPATH=src python scripts/restore_research_checkpoint.py --workers 4
PYTHONPATH=src python scripts/continue_robustness_research.py --workers 4
```

Без `--checkpoint-main` команды не публикуют commits. Сохранённые случаи повторно используются после SHA/fingerprint validation. Историческая диагностика восстановления приведена ниже; её промежуточные counts/status не описывают финальный inventory.

<details><summary>История восстановления и промежуточной проверки</summary>

# Strategy Engine: восстановление исследования

Это промежуточная точка продолжения, а не итоговый robustness verdict.
Исходный GitHub HEAD проверен: `b86fd7de0bccaae1e48fdc5ff74c6b9ceb59b074`.
Рабочее дерево до настройки было чистым. Cloud checkout использует ветку `work`,
публикация результатов направляется в `main` без переписывания истории.

## Проверено в новой среде

- Python 3.12.14; изолированное окружение `/workspace/venvs/crypto-bot`.
- Установлены точные версии из `requirements-dev.txt` и `requirements-research.txt`.
- Full tests последнего проверенного этапа: **439 PASS**; lint E9/F и mypy проходят.
  Последующие checkpoints записывают актуальный count и exit status отдельно.
- Все **57** canonical source/config SHA сохранены.
- Все **34** публичные серии проверены по stored SHA и распакованному CSV SHA:
  [receipt](data/reports/robustness_research/continuation_input_validation.json).
- До восстановления проверены **145** artifact fingerprints, **1015** файлов:
  135 canonical, 7 structural sensitivity и 3 reserve cases.
- Сохранённые exit experiments проверены: **38 cases / 266 variants**;
  source signal SHA совпадают; baseline A trades/decisions/equity совпадают точно;
  paired BACKTEST/SHADOW receipts согласованы:
  [receipt](data/reports/robustness_research/continuation_exit_validation.json).

Canonical остаётся TP **40/30/30**, inclusive wick-touch, прежние SL/BE,
`trade_entry_allowed=false`. Исследовательские варианты не выбираются для canonical.

## Восстановление отсутствующих артефактов

В исходном commit сохранены только fingerprints 21 сегмента из
[checkpoint ledger](data/reports/robustness_research/resume_original_case_fingerprints.json).
Сами их артефакты отсутствовали; предыдущая Cloud Environment недоступна.
Пользователь разрешил пересчитать только отсутствующие случаи с теми же inputs,
frozen baseline и параметрами, требуя совпадения прежних fingerprints.

Первый `canonical/binance_15_5/REFERENCE_SEGMENT_00` восстановлен точно:
`2d27f51566bc0a87028052173bc6ba14eb8c068e2947e66ba0c7da646d0286ae`.
Все **21** исходных сегмента восстановлены с точным совпадением fingerprints:
9 `binance_15_5/REFERENCE_SEGMENT_00..08`, 11 `binance_60_5/REFERENCE_SEGMENT_00..10`
и `binance_60_5/VALIDATION_SEGMENT_10`.
Расхождение первого 60/5 случая диагностировано и устранено: исходные workers
предшествовали добавлению `bos_level_price` в diagnostic POI audit (изменение
research tools в `a646301`). Повтор с исходным adapter из `b86fd7de` дал тот же
expanded fingerprint `2c26c63f7945a5fda37426b878f15aca278889cdd0af1c72ca2bd8266751747a`.
Восстановление прежней схемы только audit-файла дало точное исходное значение
`2795678d54357bfbfafa042407581dcda42f7d184512337af6fc49a333593b51`.
Все остальные шесть artifact SHA сохранились; source/config/inputs/исполнение
не изменились. Expanded audit и [schema receipt](data/reports/robustness_research/restoration_diagnostics/canonical/binance_60_5/REFERENCE_SEGMENT_00/schema_restoration.json)
сохранены отдельно. Преобразование разрешено helper только если оно даёт **точный
исходный fingerprint**; любой иной mismatch останавливает восстановление.
Статус последней полностью законченной группы находится в
[restoration receipt](data/reports/robustness_research/checkpoint_restoration_receipt.json).
До статуса `complete=true` весь checkpoint не считается восстановленным.

Повторяемая команда из корня checkout:

```bash
source /workspace/venvs/crypto-bot/bin/activate
PYTHONPATH=src python scripts/restore_research_checkpoint.py --workers 4
```

Команда проверяет frozen source/config, dataset stored SHA, сохраняет исходные
input hashes и проверяет каждый восстановленный fingerprint. При расхождении
останавливается с expected/actual; изменять исходный checkpoint запрещено.
Уже сохранённые случаи проверяются и пропускаются. Targeted recovery сохраняет
ledger других окон/сегментов. Артефакты должны коммититься вместе с receipts,
а не оставаться только во временном окружении.

Research adapter повторно использует вычисленные POI seeds только для точного
неизменного prefix; future seeds исключаются по времени подтверждения.
Изменённые/interior foreign candles идут через исходный расчёт. Regression tests
проверяют prefix equality, изменение history и восстановление runtime patches.
Canonical source не изменён. Совпадение checkpoint fingerprints остаётся
обязательным независимым критерием воспроизводимости реальных сегментов.

## Сохранённые измерения

Предварительные таблицы создаются из имеющихся результатов без повторного replay:

```bash
PYTHONPATH=src python scripts/summarize_robustness_research.py --allow-partial
```

[Generation receipt](data/reports/robustness_research/table_generation_receipt.json)
имеет `complete=false`; таблицы не являются итоговым отчётом.
Отсутствующий study означает `UNAVAILABLE_INCOMPLETE_STUDY`, а не нулевой sample.
Walk windows и независимые портфели не объединяются ради размера выборки.

В завершённых сохранённых primary HOLDOUT: Bybit 60/15 и Binance 60/15 имеют
по одной CLOSED сделке; каждый PF=0, win rate=0%, expectancy≈−23.40 USDT.
NAV drawdown соответственно ≈6.78% и ≈3.45%. Это описания отдельных n=1
samples, не оценка надёжного рыночного edge и не pooled account.
В Binance 60/5 VALIDATION POI BODY даёт две сделки против одной у wick baseline;
обе BODY сделки убыточны. Оснований выбирать BODY или менять wick policy нет.

TP allocation, timing и censored paired outcomes доступны в
[exit metrics](data/reports/robustness_research/exit_management_metrics.csv),
[paired entries](data/reports/robustness_research/paired_exit_actual_entries.csv),
[post-BE observations](data/reports/robustness_research/post_be_follow.csv).
Неизвестные ratios остаются undefined; будущие price touches не приравниваются
к прибыли. External history является retrospective holdout, не prospective OOS.

## Дальнейшая работа

После точного восстановления 21 сегмента продолжить только незавершённые studies
из [inventory](data/reports/robustness_research/research_completion_inventory.json):
canonical Binance 15/5, 60/5, 240/5, 240/15 и соответствующие execution/exit studies.
Все 11 зарегистрированных structural variants
уже рассчитаны и проверяются на completeness; midpoint даёт 0 entries в VALIDATION
против 1 у BASE. Альтернативы не выбираются по этому sample.
Выполнить зарегистрированные VALIDATION/HOLDOUT/walk windows, costs/risk,
TP allocation, BE timing и POI sensitivity, не отбирать лучший параметр.

Итоговый renderer допускается только при полном inventory. Затем full tests,
baseline/hash validation, commit/push в `main`, архив точного commit и final hash.
Малая выборка должна завершаться честным `INSUFFICIENT SAMPLE`, а не изменением
canonical ради положительного результата.

Для автоматического продолжения зарегистрированных studies:

```bash
PYTHONPATH=src python scripts/continue_robustness_research.py --workers 4
```

При явно разрешённой пользователем публикации `--checkpoint-main` включает full
tests, lint/mypy, staged content scan, commit и non-force push каждого стабильного
этапа в `main`. Уже завершённые canonical/structural studies пропускаются по
complete inventory и fingerprints. Execution/exit cases повторно используются
только после проверки source/input SHA и artifact hashes. Новые per-case manifests
и source context сохраняются для последующего возобновления.

После завершения pipeline финальная доставка выполняется командой
`PYTHONPATH=src python scripts/finalize_research_delivery.py`. Она требует полного
inventory и итогового проверенного этапа, повторно сверяет все 21 исходных
fingerprints, публикует актуальную точку передачи и создаёт ZIP точного commit
в `/workspace/artifacts` с CRC-проверкой, SHA256 и `latest_final.json`.
Незавершённый inventory блокирует финальную доставку.

</details>
