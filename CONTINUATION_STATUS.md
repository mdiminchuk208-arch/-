# Strategy Engine: восстановление исследования

Это промежуточная точка продолжения, а не итоговый robustness verdict.
Исходный GitHub HEAD проверен: `b86fd7de0bccaae1e48fdc5ff74c6b9ceb59b074`.
Рабочее дерево до настройки было чистым. Cloud checkout использует ветку `work`,
публикация результатов направляется в `main` без переписывания истории.

## Проверено в новой среде

- Python 3.12.14; изолированное окружение `/workspace/venvs/crypto-bot`.
- Установлены точные версии из `requirements-dev.txt` и `requirements-research.txt`.
- Full tests: **437 PASS**; lint E9/F и mypy проходят.
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
Девять `binance_15_5/REFERENCE_SEGMENT_00..08` восстановлены с точным совпадением.
На `binance_60_5/REFERENCE_SEGMENT_00` проверка обнаружила расхождение и остановила
восстановление: expected `2795678d54357bfbfafa042407581dcda42f7d184512337af6fc49a333593b51`,
actual `2c26c63f7945a5fda37426b878f15aca278889cdd0af1c72ca2bd8266751747a`.
Этот случай не засчитывается восстановленным. Выполняется диагностический повтор
с исходным research adapter из `b86fd7de`; исходный checkpoint не изменён.
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
canonical Binance 15/5, 60/5, 240/5, 240/15; соответствующие execution/exit studies;
оставшиеся OTE/midpoint variants. OTE 0.710 уже запущен отдельно.
Выполнить зарегистрированные VALIDATION/HOLDOUT/walk windows, costs/risk,
TP allocation, BE timing и POI sensitivity, не отбирать лучший параметр.

Итоговый renderer допускается только при полном inventory. Затем full tests,
baseline/hash validation, commit/push в `main`, архив точного commit и final hash.
Малая выборка должна завершаться честным `INSUFFICIENT SAMPLE`, а не изменением
canonical ради положительного результата.
