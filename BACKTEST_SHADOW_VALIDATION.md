# BACKTEST / SHADOW validation — 2026-10-08

Техническая автоматическая цепочка от OHLC до закрытия виртуальной позиции проверена для LONG и SHORT, включая восстановление после TP1. Полную торговую готовность на предоставленной истории Bybit **не подтверждаю**: фактический прогон по-прежнему не содержит READY или входов. Тестовые OHLC ниже явно отделены от исторических наблюдений; это не результат торговли на Bybit и не доказательство доходности.

| CHECK | STATUS | EVIDENCE |
|---|---|---|
| Полный suite | PASS | 373 tests, [лог](data/reports/continuation_validation/checks/final_full_tests_v2.log) |
| Lint | PASS | `ruff check src scripts tests --select E9,F` |
| Typecheck | PASS | `mypy src scripts`: 49 файлов |
| Полная автоматическая цепочка LONG/SHORT | PASS на тестовых OHLC | [CLI verification](data/reports/continuation_validation/constructed/verification.json), исходные CSV, signals, decisions, trades, equity curve в соседних каталогах |
| Restart с открытой позицией после TP1 | PASS | Fingerprint SHADOW == resumed; восстановление pending, TP1/TP2, дневного лимита и consumed IDs проверено отдельно |
| Risk, стоп, breakeven, повторный вход | PASS | `test_virtual_portfolio`, `test_portfolio_accounting`, `test_portfolio_checkpoint` |
| Causality / determinism | PASS в проверенных сценариях | Каждый prefix сравнен с независимым snapshot; будущие OHLC изменены; повторный CLI имеет тот же fingerprint |
| Реальная история Bybit: торговые условия | NOT READY | 6 358 сетапов, 0 READY, 0 входов; [полные причины](data/reports/continuation_validation/real_backtest/setup_outcomes.jsonl) |
| Реальные ордера / private API | DISABLED | `trade_entry_allowed=false`; BACKTEST/SHADOW enum отвергает LIVE |

## BEFORE

Исходный полный suite: **353 PASS**. Однако отсутствовали checkpoint и resume, а дополнительные регрессии воспроизвели нарушения проверки данных и сигналов.

60m/5m, 10 монет, warmup 576 LTF-свечей, капитал $1 170:

| Метрика | Исходный прогон | После исправлений |
|---|---:|---:|
| Execution candles | 685 320 | 685 350 |
| Setups / signal candidates | 6 357 | 6 358 |
| Signal state changes | 17 752 | 17 753 |
| READY / virtual entries / closed trades | 0 / 0 / 0 | 0 / 0 / 0 |
| Equity / PnL | $1 170 / $0 | $1 170 / $0 |

Начало execution: `2026-01-27T12:00:00Z`. Старый конец: `2026-09-22T11:00:00Z`; исправленный конец: `2026-09-22T11:15:00Z`. Последние 15 минут были ошибочно отсечены из-за отсутствия будущего HTF-close. Старые 17 752 состояния сигналов совпадают после исключения номера версии и новых полей R:R.

Все шесть доступных пар также проверены с прежним `AutoLevelPolicy()` и полной общей историей:

| HTF / LTF | Setups | Signal changes | READY / entries |
|---|---:|---:|---:|
| 15m / 5m | 12 641 | 38 081 | 0 / 0 |
| 60m / 5m | 6 357 | 17 752 | 0 / 0 |
| 60m / 15m | 4 090 | 12 217 | 0 / 0 |
| 240m / 5m | 2 182 | 4 755 | 0 / 0 |
| 240m / 15m | 1 665 | 4 435 | 0 / 0 |
| 240m / 60m | 1 001 | 2 863 | 0 / 0 |

Точный суммарный результат по парам — **27 936 сетапов**. Эти строки имеют разные периоды warmup/execution при смене LTF; суммирование свечей между строками не является числом уникальных рыночных наблюдений. Baseline JSON и hashes сохранены в [baseline](data/reports/continuation_validation/baseline). Hashes кода в старых baseline-файлах сняты при записи отчёта во время разработки; для версии, фактически исполняемой baseline, следует использовать исходный Git commit `38fe78e`. Финальные прогоны выполнены с неизменяемыми исходниками и проверены против текущих hashes.

Полный анализ исходного 60m/5m периода вместе с warmup, 20 series: **748 670 candles, 304 482 structural levels, 27 428 BOS transitions, 103 417 structural SFP formations, 26 452 Range candidates, 7 667 Range sweep episodes**. Из них 4 260 `CONSUMED_NO_SFP`, 3 393 `CLARITY_REVIEW_BLOCKED`, 14 ambiguous; Range SFP events=0 при сохранённом UNREVIEWED. Range outcomes: 8 583 rejected internal structure, 4 601 invalidated internal structure, 12 236 retired, 128 validated, 904 waiting. [Разбивка по монетам/TF](data/reports/continuation_validation/baseline_stages.json). Эти числа включают оба таймфрейма и не равны execution candles из таблицы выше. Воспроизведение: `PYTHONPATH=src python tests/validate_stages.py`.

## ROOT CAUSES

1. `VirtualPortfolio` не сохранял позиции, ожидающие сигналы, частичные выходы, journal, марки, баланс, clock, дневной latch и consumed/terminal IDs. Перезапуск терял состояние.
2. Пропущенная свеча могла трактоваться как соседняя при анализе структуры или диапазона. Объявленный HTF мог отличаться от физической длительности свечи. Исполнение принимало дробную минуту.
3. Неизвестное состояние сигнала превращалось в WAITING; повторные consumed/terminal identities игнорировались без объяснения. Два противоречащих состояния одного ID зависели от порядка в batch.
4. READY принимался с отсутствующим, нечисловым или выходящим из зоны Optimal Entry.
5. Оба replay CLI обрезали LTF-history по последнему закрытому HTF. На согласованном OHLC-сценарии это давало 0 entries вместо корректного виртуального входа и закрытия.
6. Не было исчерпывающего отдельного исхода каждого setup в итоговом историческом отчёте. R:R рассчитывался внутри trade-plan, но не попадал в signal.
7. Range prevalidation строил timeline до конца всей истории после уже известного первого terminal event. Регрессия воспроизвела 2 011 обращений к свечам вместо ограниченного участка; большие прогоны расходовали время на данные, не влияющие на решение.

`SOURCE_SL_TARGET_SELECTION_NOT_IMPLEMENTED` **не является текущим блокером**: SL/TP архитектура и wiring уже реализованы. Реальные остановки — условия существующей экспериментальной OB/POI-нормализации, а не real-trading guard.

Отдельная причина отсутствия исторических READY: 5 842 сетапа дошли до автоматического подбора уровней в execution-срезе; 4 659 встретили `NO_POST_BOS_OB_PATTERN`. Девять достигли проверки подходящего поддерживающего POI, и каждый получил `FRESH_PREEXISTING_HTF_POI_NOT_FOUND`. Причины могут пересекаться; это не независимые категории для суммирования. [Сохранённый подробный аудит](READY_AUDIT_REPORT.md) проверяет исходные касания POI, девять близких случаев и правила freshness.

Это проверено как поведение текущей нормализации: все обязательные условия совместимы и достигаются одновременно на согласованных тестовых OHLC, а отвергнутые исторические POI действительно были ранее затронуты. Основания автоматически ослаблять эти правила ради сделок не найдены.

## FIXES

- Atomic versioned JSON checkpoint с digest, whitelist типов, проверкой accounting/clock/state; предыдущий файл сохраняется при сбое замены. LIVE и true execution flag отвергаются даже при пересчитанном digest.
- CLI `--checkpoint`, `--checkpoint-every`, `--resume`, `--stop-after-bars`. Возобновление требует тех же входных файлов, кода, параметров, режима и капитала. Уже обработанные batches повторно не исполняются.
- Проверка целостности временного ряда и входных сигналов до любых изменений портфеля; точные duplicate updates дедуплицируются, конфликтующие отвергаются.
- Явные причины для consumed/terminal identities и `setup_outcomes.jsonl`. `total_setups = passed + rejected`; ожидающие объекты в конце данных отмечены как right-censored. Это завершение отчёта, а не выдуманный timeout стратегии.
- Causal LTF tail сохранён; отсутствие действительно требуемой закрытой HTF-свечи отвергается как stale history.
- R:R min/max/Optimal Entry включены в signal; версия `0.4.20-replay.4`.
- Range timeline ограничен первым terminal event. Приоритет одновременных событий сохранён: internal BOS → boundary raids → midpoint. Golden SHA всего Range-report совпал до/после на шести реальных отрезках ADA/BTC/ETH, 5m/60m.
- Исправлены аннотации и lint; два старых теста с минутными свечами, ошибочно названными часовыми, получили настоящие H1 timestamps.

## TESTS

В Cloud Environment выполнены:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
ruff check src scripts tests --select E9,F
mypy src scripts
PYTHONPATH=src python tests/validate_constructed.py
PYTHONPATH=src python scripts/run_historical_portfolio.py --days max --workers 4 --mode BACKTEST --report-root /workspace/continuation_runs/final_backtest_v2
PYTHONPATH=src python scripts/run_historical_portfolio.py --days max --workers 4 --mode BACKTEST --report-root /workspace/continuation_runs/final_repeat_v2
PYTHONPATH=src python scripts/run_historical_portfolio.py --days max --workers 4 --mode SHADOW --report-root /workspace/continuation_runs/final_shadow_v2
```

373 tests PASS; 20 дополнительных тестов относительно baseline. До исправлений сохранены FAIL/ERROR для clock integrity, отсутствующего checkpoint, signal integrity, LTF tail и Range work horizon. После исправлений соответствующие suites PASS. Dev tools воспроизводимо устанавливаются через `pip install -r requirements-dev.txt`.

## BACKTEST AFTER

Реальная история: **6 358 setups, 17 753 signal changes, READY=0, entries=0, closed=0, TP1=TP2=TP3=SL=0, PnL=$0**. Для всех 6 358 записан результат: 0 passed + 6 358 rejected/censored. Индивидуальные причины сохранены; ожидание в конце данных не превращено в фиктивный торговый сигнал.

Автоматический CLI на специально построенном тестовом рынке, без `QualifiedLevels`, готовых signals или подставленных structural reports:

| Direction | Setups | Signal changes | READY | Entries | Closed | TP1/TP2/TP3 | SL | Net PnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 1 | 3 | 1 | 1 | 1 | 1 / 1 / 1 | 0 | +$139.77 |
| SHORT | 1 | 3 | 1 | 1 | 1 | 1 / 1 / 1 | 0 | +$139.50 |

Каждая H1-свеча точно равна агрегации своих двенадцати 5m-свечей. SFP, структура, OB, freshness, targets и entry определены штатными анализаторами. Рыночные тестовые цены специально описывают необходимые условия; они **не являются историческим результатом Bybit**. Stop/BE/gap/ambiguous-bar выходы дополнительно проверены независимыми accounting/risk tests.

## SHADOW AFTER

Исторический SHADOW: те же 6 358 setups, 0 READY, 0 entries, equity $1 170. Decisions, trades, setup outcomes и equity curve совпали с BACKTEST побайтно; signals совпали после нормализации только mode.

Тестовый SHADOW: LONG/SHORT прошли тот же полный lifecycle. После остановки с 60% открытой позиции после TP1 resume дал тот же полный fingerprint, что непрерывный SHADOW. Данные или mode, изменённые после checkpoint, отвергаются без перезаписи сохранённого состояния.

SHADOW здесь — закрытые свечи и виртуальный execution. Подключённого realtime feed нет.

## LOOKAHEAD

`test_historical_replay` сравнивает каждый close с независимым анализом prefix; проверяет реальный ADA prefix и изменённый future suffix. Новый автоматический lifecycle сравнивает все 190 closes, включая положительный READY. Будущие цены изменены без изменения прошлых сигналов. Геометрия, SL, POI/targets, evidence timestamps и Score доступны только в момент принятия решения; fill происходит на следующем open.

SFP не возникает до подтверждения; BOS использует подтверждённый protected point и close. В source-консервативной номенклатуре проекта смена существующей структуры называется `*_STRUCTURE_BROKEN_BOS` — отдельное новое правило CHOCH не добавлялось. Range episodes `SFP_FORMED`, `CONSUMED_NO_SFP`, ambiguous, invalidation и retirement проверены существующими suites; consumed boundary не переиспользуется.

## DETERMINISM

Повторный полный исторический BACKTEST имеет тот же fingerprint. BACKTEST/SHADOW сравниваются по содержанию после исключения только mode; их полные fingerprints различаются из-за mode в summary/signals.

На тестовом рынке совпали fingerprints backtest/repeat и shadow/resumed для обоих направлений. [Verification](data/reports/continuation_validation/constructed/verification.json) содержит значения; [real-history verification](data/reports/continuation_validation/real_history_verification.json) содержит проверку исторических артефактов и hashes финального кода.

## RISK

Сохранены: risk/trade 2–5% (default 2%), aggregate cap ≤6%, daily loss limit 4%, default leverage x3, max x5, Isolated; повторный вход только новым ID после закрытия прежней позиции и Score≥75. Fees 0.0006 и slippage 0.0002 применяются к каждому соответствующему fill. После TP1 stop покрывает costs на оставшейся позиции.

Пройденные проверки включают одинаковый OPEN нескольких монет без использования чужого будущего CLOSE, margin/risk caps, daily latch после убытка и его сохранение при перезапуске, разрывы цены, приоритет stop при TP/SL в одной OHLC-свече, частичные выходы, duplicate settlement, NaN/Infinity, malformed/unclosed/out-of-order/duplicate/missing candles, пустой dataset и слишком узкий stop. Zero volume допускается и присутствует в CLI test-market evidence.

Модель сохраняет прежние ограничения: fractional linear quantity без исторических exchange lot filters; funding/liquidation не моделируются; порядок внутри OHLC трактуется консервативно. MFE/MAE — полный bar envelope, drawdown/equity sampling — на close. Эти ограничения явно присутствуют в отчётах и не выдаются за точный exchange execution.

## GIT

Репозиторий: [mdiminchuk208-arch/Zsfhjl-](https://github.com/mdiminchuk208-arch/Zsfhjl-), ветка `main`.

- `f3fcb67`: integrity, outcomes, checkpoint/resume.
- `4c1cc24`: causal LTF tail, R:R, полный автоматический lifecycle, typecheck.
- `a849177`: Range horizon, restart integrity, воспроизводимый CLI validator.
- Финальный commit с отчётом и evidence указан в ответе; hash нельзя включить в содержимое самого commit без изменения hash.

Stable commits отправлены обычным push. Force push, reset и переписывание истории не использовались. Исходные рабочие файлы и старые отчёты сохранены. `.gitignore` исключает venv, caches, build outputs и secret files; новые временные большие прогоны находятся вне репозитория. В Git сохранены summaries, индивидуальные setup outcomes, тестовые полные артефакты и проверочные логи; hashes всех крупных исторических файлов позволяют воспроизвести их штатным CLI.

## REMAINING

В предоставленной истории нет ни одного одновременно удовлетворяющего текущим правилам автоматического сетапа. Это **не подтверждает историческую торговую готовность**. Подменять этот результат тестовыми сделками нельзя.

Внешние зависимости для подтверждения стратегии на рынке: оригинальные материалы и предметная квалификация экспериментальных OB/POI-нормализаций; source-clarity review фактических Range boundaries; более длинная/иная историческая выборка. Имеется около 240 дней, а не полный год, и нет 1D CSV. Realtime public market feed также не предоставлен и не входит в выполненный offline SHADOW.

Найденные внутренние ошибки исправлены и покрыты регрессиями; известных падающих проверок текущего этапа не оставлено. При этом исходный критерий «положительные валидные сделки на предоставленной истории Bybit» остаётся неподтверждённым, и этот отчёт не объявляет его выполненным.
