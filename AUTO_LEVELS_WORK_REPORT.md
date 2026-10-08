# Strategy Engine — автоматические уровни, 0.4.20-replay.2

Исторический отчёт предыдущего этапа. Текущая версия `0.4.20-replay.3` и
исследование портфеля $1170 описаны в HISTORICAL_PORTFOLIO_REPORT.md.
Приведённые ниже fingerprint относятся к сохранённой версии `.2`.

Перед изменениями подтверждён baseline предыдущего рабочего этапа: 288 тестов
PASS и пользовательский Windows-прогон 10 монет / 48 свечей, 44 сетапа,
0 виртуальных входов с fingerprint
`a4f47cf8b459514a8229bdfa3b5fcf1190ad7e0cc79de2fb9d8ba8cada27ea16`.
Создан backup `data/reports/auto_levels_audit/before_auto_levels_code.zip`.
Git-метаданных в загруженном проекте нет.

| CHECK | STATUS | EVIDENCE |
| --- | --- | --- |
| Структура движка | СОХРАНЕНА | Существующие data → structure/Range/SFP → MTF → OTE → replay → virtual_portfolio; отдельный модуль auto_levels |
| Проверенные модули | PASS тестов | Полный unittest discovery: данные/QA/хранилище, structure, Range/lifecycle, SFP, MTF/provenance, OB/geometry, risk, replay, CLI и виртуальный портфель |
| Baseline → итог | PASS | 288 → 327 тестов; добавлено 39, итоговых FAIL/ERROR = 0; final_tests.log, 6.823 с |
| Детектор автоматических уровней | PASS технических тестов | 28 тестов: LONG/SHORT, BOS/структура, сырые liquidity events, OB/IMB, HTF seeds, свежесть, геометрия, дубликаты и неверные данные |
| Полный виртуальный lifecycle | PASS синтетических сценариев | Реальный детектор → сигнал → next-open вход → TP1/TP2/TP3 для LONG/SHORT и BACKTEST/SHADOW; структурные отчёты в fixture заданы явно и сверяются с OHLC |
| Причинность/lookahead | PASS тестов | Prefix/full-history/future-mutation равенство; будущие HTF/геометрия не открывают вход; подтверждения имеют known_at и идентичность свечей; данные фильтруются по close_time ≤ as_of |
| Range/SFP/MTF lifecycle | PASS регрессий | Старые lifecycle, invalidation, resolved_index, post-SFP BOS и source/recovery тесты включены в полный набор; ядро этих модулей в новом этапе не переписано |
| Детерминированность BACKTEST | PASS | Два запуска на 10 реальных CSV-сериях дали побайтово одинаковые summary.json и decisions.jsonl |
| BACKTEST ↔ офлайн SHADOW | PASS | Все поля summary равны после удаления mode только на верхнем уровне и в signal_updates; журналы побайтово равны |
| Реальный исторический ввод | ПРОВЕРЕНО | 10 символов, HTF60/LTF5, 48 execution bars и warmup576 на символ: 480 snapshots, 44 уникальных сетапа |
| Виртуальные входы на этой истории | 0 | Последние состояния: 22 INVALIDATED, 22 WAITING_FOR_AUTO_LEVELS; подтверждённых OB/IMB не хватило, правила не ослаблялись для получения сделок |
| История Bybit | PASS сохранности | SHA-256 всех 40 CSV совпадают с исходным загруженным ZIP |
| Код ↔ отчёт | PASS | input_code_hashes сверены с текущими исходниками, CLI, source_rules.json и pyproject.toml |
| Compileall | PASS | src/scripts/tests, exit code 0 |
| Lint/typecheck | НЕ НАСТРОЕНЫ | В проекте отсутствует соответствующая конфигурация; PASS не заявляется |
| Реальная торговля | ЗАБЛОКИРОВАНА | trade_entry_allowed=false у сигналов/журнала/портфеля; LIVE/PAPER отвергаются; private API/Execution Engine/production интеграция не добавлены |
| Source-соответствие автоматического POI | НЕ ПОДТВЕРЖДЕНО | Исходные PDF отсутствуют; HTF gap-seeds, численные пороги и выбор трёх целей помечены BACKTEST_PARAMETER, source-review gate сохранён |
| Текущий рынок / live SHADOW | НЕ ПОДКЛЮЧЁН | SHADOW этого этапа воспроизводит исторические CSV, не является запущенным сервисом наблюдения текущего рынка |
| До интеграции с сайтом | ОСТАЛОСЬ | Проверка POI по первичным материалам/графикам, оценка параметров и торговой статистики, public-feed SHADOW adapter, Range clarity, производительность/низкая задержка |

## Реализация

`--auto-levels` явно включает эксперимент. Без него сохраняются прежние
ожидание source-qualified уровней и caller-assertion API. CLI запрещает смешивать
автоматический и внешний источник уровней.

Подбор требует причинно готовую противоположную структуру после точного BOS,
новый LTF OB после BOS внутри структурного импульса с пересечением OTE,
настоящий raw structural sweep, агрессивное поглощение A/B, третью свечу IMB,
первую реакцию в существовавшей HTF gap-POI и отсутствие последующего теста OB.
SL — экстремум A; targets — ближние края трёх различных непересекающихся
свежих противоположных HTF gap-seeds. TP1 всегда ближайшая; перекрывающиеся
с уже выбранной зоны пропускаются как отдельные цели. Искусственные RR-цели
и деление одной зоны на три не применяются.

Пороги `min_body_fraction=0.6`, `min_engulf_body_ratio=1.0` сохранены в manifest.
Сигнал содержит `level_policy`, структурированные `level_evidence`,
`level_blocking_reasons`, `levels_known_at`. Статистика blockers учитывает
последнее состояние каждого уникального сигнала; один сетап может иметь
несколько причин. Исторические значения новых policy-параметров не считаются
оптимизированными или проверенными на доходность.

## Исправленные ошибки сопровождения

1. Если готовые уровни теряют подтверждение, старый pending вход удаляется на
   текущем закрытии. Его нельзя выполнить на более поздней свече с устаревшими
   доказательствами. Решение уже принятого открытия не пересчитывается;
   открытые позиции продолжают сопровождаться своими уровнями.
2. Слишком близкая TP1 раньше давала BE вне диапазона свечи: в воспроизведении
   LONG свеча имела high100.06, а новый stop считался равным100.160128; SHORT
   имел low99.94 и stop99.840128. До допуска проверяется положительный net TP1
   после моделируемых комиссий и slippage. Негодный вход блокируется с причиной
   TP1_NOT_POSITIVE_AFTER_COSTS. Исходная ошибка сохранена в tp1_cost_bug_before.json.

TP 40/30/30, BE с комиссиями/slippage, риск 2–5%, совокупный stop-risk cap6%,
суточная защёлка потерь, Isolated x3/max5, повторный вход после завершения и
score≥75 сохранены и проверены существующими тестами.

## Изменённые файлы

- Новые: src/crypto_bot/strategy/auto_levels.py, tests/test_auto_levels.py,
  tests/test_auto_replay.py, AUTO_LEVELS.md, AUTO_LEVELS_WORK_REPORT.md.
- Изменённые: src/crypto_bot/strategy/replay.py,
  src/crypto_bot/strategy/virtual_portfolio.py, scripts/run_strategy_replay.py,
  tests/test_replay_cli.py, tests/test_virtual_portfolio.py, README.md,
  STRATEGY_REPLAY.md, STRATEGY_ENGINE_WORK_REPORT.md (пометка предыдущего этапа).

Новые тесты: 28 detector + 8 integration + 2 CLI + 1 cost-regression =39.
Актуальные логи/JSON/evidence находятся в data/reports/auto_levels_audit/.
Предыдущий 240-дневный structural audit сохраняется как свидетельство прошлого
этапа; его полный code hash больше не равен новой реализации и он не представлен
как новый тест auto-levels.

Проверенный BACKTEST fingerprint:
`86a199c3e2c6d6fb32fbfdcb54176955a69df537da5c5e3d3adb51c37447e9a2`.
Офлайн SHADOW fingerprint:
`5a055cc566d685baffc7b2b11a6566a7b29e65c50c382219edebc40e517c0156`.
Различие объясняется mode в отчёте; смысловой результат и journal одинаковы.

Модель не включает funding, liquidation, price/quantity rounding, contract
minimums и биржевое исполнение. Полученные PASS относятся к программным
инвариантам и сценариям, а не к гарантии прибыли или полной source-сертификации.
