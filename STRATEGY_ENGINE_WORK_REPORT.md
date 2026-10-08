# Crypto Bot / Strategy Engine — отчёт проверенного рабочего этапа

Этот отчёт фиксирует предыдущий этап `0.4.20-replay.1` и его сохранённые
артефакты. Этап `0.4.20-replay.2` описан в AUTO_LEVELS_WORK_REPORT.md;
старые fingerprint и хеши кода не являются хешами новой реализации.
Текущая версия `0.4.20-replay.3` описана в HISTORICAL_PORTFOLIO_REPORT.md.

Работа выполнена на текущем загруженном архиве `crypto_bot_phase1_4_18.zip`
(22 975 869 байт). Папка сохранена; фактическая исходная версия по коду и
pyproject — 0.4.20. Git-метаданных в архиве нет. Package version сохранена для
совместимости с существующими freeze-тестами; новый контур маркируется
`strategy_version=0.4.20-replay.1` и фиксирует SHA-256 входов/кода/результата.

Перед изменениями выполнен полный baseline и создан backup исходного кода.
Старые README/changelog не использовались как доказательство PASS.

| CHECK | STATUS | EVIDENCE |
|---|---|---|
| Структура Strategy Engine | ИЗУЧЕНА | Public-data/QA → structure/liquidity/SFP → Range → MTF/global opportunities → source geometry → replay → virtual portfolio |
| Модули проверены | ПРОВЕРЕНО | Все существующие тесты data/storage/coverage/QA, structure/ordering/stability, SFP/episodes, Range/validation, MTF/global, OB/trade-plan/risk, recovery/provenance/reporting |
| Git status | НЕ ПРИМЕНИМО | В загруженном проекте нет .git; исходное состояние сохранено в оригинальном архиве и локальном backup |
| Baseline unit/integration/regression | PASS: 242, FAIL: 0 | `data/reports/work_audit/baseline_tests.log` |
| Baseline real-data 240d | FAIL: 10/10 MTF runtime checks | Повтор исходного кода из backup: `original_cross_asset_240d/summary.json`; unit baseline не покрывал ошибку OTE |
| Ошибки найдены/исправлены | 9 регрессионных случаев | Ниже; исходный код не проходит новые проверки: `original_regression_reproduction.log` |
| Unit/integration/regression/CLI после изменений | PASS: 288, FAIL: 0 | `final_tests.log`; включает весь baseline и 46 новых тестов |
| Новые тесты | 46 в 4 файлах | 9 work regressions, 13 replay, 22 virtual portfolio, 2 CLI |
| Lookahead safety | PASS в проверенном scope | Prefix vs full-history as-of equality; mutation будущего OHLC; causal reference timestamps; next-open fills; запрет использовать same-bar close PnL при входах |
| Deterministic replay | PASS | Два прогона реальных данных: побайтное совпадение summary и JSONL; `replay_verification.json` |
| Range lifecycle | PASS тестов | Validation → first raid/consumption → no reuse → retirement after both boundaries; pending/resolved episodes; independent SFP invalidation; ambiguous episodes resolved |
| SFP lifecycle | PASS тестов | Sweep close + immediate next open; через пропущенную свечу SFP не подтверждается; invalidation terminal в виртуальном ledger |
| MTF causal linking | PASS | BOS строго после SFP, invalidation выигрывает равный timestamp; chronological opportunity IDs; 10/10 real-data runtime checks |
| OTE/source references | PASS геометрии | Невозможный directional impulse отклоняется с причиной, не падает весь MTF; закрытые соседние OB-свечи; SL/FTA/RR проверки |
| Позиционное сопровождение | PASS | LONG/SHORT, TP 40/30/30, net breakeven с fee/slippage, conservative SL/TP ties и adverse gap open |
| Risk guards | PASS | 2–5% per-trade policy, cap ≤6%, Isolated ≤x5, margin guard, daily latch, сопровождение старых позиций, re-entry после завершения и Score ≥75 |
| Real-data cross-asset 240d | PASS: 10/10 symbols | `final_cross_asset_240d/summary.json`; 5/15/60/240m; suffix=60d, stabilization=30d, warmup=0; input/code hashes сохранены |
| Реальный короткий replay | PASS | 10 symbols ×48 execution bars =480 snapshots, 576 warmup LTF bars, 44 unique setups; HTF 60m / LTF 5m |
| Виртуальные входы в real-data replay | 0, ожидаемо | Квалифицированные SL и три TP не подавались; автоматические уровни не подменены придуманными |
| Квалифицированный signal → виртуальные TP | PASS integration test | `test_end_to_end_qualified_snapshot_to_virtual_tp_management`, плюс экономические LONG/SHORT tests |
| SHADOW | ПОДГОТОВЛЕН ОФЛАЙН-КОНТУР | Mode parity на тех же реальных данных: analysis одинаков за исключением mode, decision JSONL побайтно одинаков |
| Compile check | PASS | `python -B -m compileall -q src scripts tests`, exit 0 |
| Lint/typecheck | НЕ НАСТРОЕНЫ | В исходном pyproject нет соответствующих конфигураций; отдельный результат PASS не заявляется |
| Безопасность | СОХРАНЕНА | trade_entry_allowed=false; LIVE/PAPER rejected; private API/real orders/Execution Engine/production integration не добавлялись |
| Исторические данные | БЕЗ ИЗМЕНЕНИЙ | Все 40 CSV побайтно идентичны загруженному архиву по SHA-256 |
| До интеграции с сайтом | ОСТАЛОСЬ | Auto OB/POI qualification, Range source-validation gates, public live-feed adapter, latency/performance, статистическая проверка экспериментальных параметров |

## Исправленные дефекты

1. SFP подтверждался следующим доступным баром даже после разрыва истории.
   Теперь требуется непосредственное соседство timestamp sweep.close/next.open.
2. SFP не отклонял NaN/Infinity liquidity levels. Добавлена finite/positive проверка.
3. Market/Range принимали перекрывающиеся свечи при растущем open_time.
   Теперь overlap отклоняется.
4. Range принимал внешний base_report с событиями из будущего относительно
   доступной истории. Теперь такой ввод отклоняется.
5. Ambiguous dual-side range episodes оставались без resolved_index, хотя решение
   блокировать обе стороны было известно. Теперь resolution index = sweep index.
6. ID MTF opportunities сортировались сначала по направлению; поздний LONG мог
   перенумеровать ранний SHORT. Теперь порядок сначала хронологический.
7. Из реально валидной противоположной post-BOS структуры не всегда следовал
   directional impulse между frozen broken-extreme/anchor. OTE exception рушил
   MTF на всех десяти инструментах. Теперь entry geometry получает
   REJECTED_ENTRY_GEOMETRY и причину, raw SFP/BOS audit сохраняется.
8. Неизвестное направление в ряде geometry функций неявно трактовалось как SHORT.
   Теперь неизвестные направления отклоняются.
9. Qualified OB geometry могла брать high/low незакрытых или несоседних свечей.
   Добавлены закрытость и непосредственная хронологическая смежность.

На исходном коде девять regression methods воспроизводят ошибки; unittest
учитывает несколько subtests отдельно, поэтому лог содержит 13 failures и 1
error. В исправленном коде эти проверки проходят.

## Изменённые и добавленные файлы

Изменены:

- `src/crypto_bot/strategy/market_analysis.py`
- `src/crypto_bot/strategy/range_engine.py`
- `src/crypto_bot/strategy/sfp.py`
- `src/crypto_bot/strategy/mtf_sfp.py`
- `src/crypto_bot/strategy/trade_plan.py`
- `src/crypto_bot/strategy/order_block.py`
- `README.md`

Добавлены:

- `src/crypto_bot/strategy/replay.py`
- `src/crypto_bot/strategy/virtual_portfolio.py`
- `scripts/run_strategy_replay.py`
- `tests/test_work_regressions.py` — 9 tests
- `tests/test_replay.py` — 13 tests
- `tests/test_virtual_portfolio.py` — 22 tests
- `tests/test_replay_cli.py` — 2 tests
- `STRATEGY_REPLAY.md`
- `STRATEGY_ENGINE_WORK_REPORT.md`
- Проверочные отчёты и backup в `data/reports/work_audit/`.

## Проверки и воспроизведение

Все команды выполнены здесь из папки проекта; это описание доказательств,
а не просьба к пользователю выполнить работу вручную.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -B -m compileall -q src scripts tests

PYTHONPATH=src python scripts/analyze_cross_asset_robustness.py \
  --evaluation-days 240 --suffix-days 60 --stabilization-days 30 \
  --analysis-warmup-days 0 \
  --report-root data/reports/work_audit/final_cross_asset_240d

PYTHONPATH=src python scripts/run_strategy_replay.py \
  --symbols BTCUSDT ETHUSDT SOLUSDT XRPUSDT BNBUSDT DOGEUSDT ADAUSDT LINKUSDT AVAXUSDT LTCUSDT \
  --bars 48 --warmup-bars 576 \
  --report-root data/reports/work_audit/final_replay
```

Replay повторён в `final_replay_repeat`; SHADOW выполнен с теми же аргументами
и `--mode SHADOW` в `final_shadow`. BACKTEST fingerprint:

`a4f47cf8b459514a8229bdfa3b5fcf1190ad7e0cc79de2fb9d8ba8cada27ea16`.

Базовая коллекция покрывает unit, integration и regression одним unittest
discovery. Новые CLI tests действительно запускают отдельный процесс Python.
Это не утверждение, что все возможные рыночные edge cases доказаны.

## Реальное состояние BACKTEST и SHADOW

BACKTEST имеет проверенный причинный observation/replay контур и условно готовый
виртуальный trade lifecycle при предоставлении source-qualified входных уровней.
Он ещё не является автономной торговой стратегией: без квалификации OB/POI
setup остаётся WAITING/REJECTED/INVALIDATED. Score и midpoint reference явно
маркированы как BACKTEST_PARAMETER; их доходность/оптимальность не утверждается.

SHADOW подготовлен как безопасный интерфейс closed-candle observation и virtual
management, с доказанной offline parity и risk guards. Текущий рынок постоянно
не наблюдается: публичный live-feed adapter не подключён. Closed-HTF snapshots
могут задерживать знание next-open SFP до закрытия HTF свечи.

Не следует закрывать оставшиеся gates одним только 10/10 structural audit:
он не формализует автоматический OB/POI selection, объективную Range clarity,
полную Range chart-conformance или эффективность стратегии. Эти признаки в
текущем коде представлены квалифицированными evidence/assertions, а не готовой
автоматической детекцией. Минимально рискованный следующий этап — отдельная
формализация этих правил с dataset fixtures, затем public-feed replay/performance
проверки. Production integration и PAPER остаются отдельным последующим этапом.

Модель не учитывает funding/liquidation, contract minimums и tick/qty rounding;
gap losses могут превосходить модельный stop-risk budget. Подробные контракты и
параметры — в `STRATEGY_REPLAY.md`.
