# Retained validation evidence

`BACKTEST_SHADOW_VALIDATION.md` в корне проекта содержит выводы, ограничения и команды.

- `baseline/`: реальные исходные прогоны шести пар таймфреймов; summaries, fingerprints, hashes. `executed_code_manifest.json` отдельно идентифицирует исходное дерево Git.
- `baseline_stages.json`: полный анализ structure/Range исходного 60m/5m периода, включая warmup, 20 series.
- `real_backtest/`, `real_repeat/`, `real_shadow/`: финальные Bybit summaries, hashes всех артефактов, индивидуальные outcomes всех 6 358 сетапов и логи запуска. Большие signals/decisions/equity файлы воспроизводятся историческим CLI из сохранённых исходных CSV; их SHA-256 записаны в `artifact_hashes.json`.
- `real_history_verification.json`: совпадение repeat fingerprint, BACKTEST/SHADOW, исходных inputs, замороженного кода и прежних 17 752 состояний сигналов.
- `constructed/`: **специально построенные согласованные тестовые OHLC**, а не историческая торговля Bybit. Содержит исходные CSV, все outputs LONG/SHORT BACKTEST/SHADOW, частичный checkpoint после TP1 и resume, fingerprints и verification. Поле BYBIT в тестовом CSV служит совместимости с существующим storage loader; provenance — test fixture. Воспроизведение: `PYTHONPATH=src python tests/validate_constructed.py`.
- `checks/`: FAIL/ERROR до исправлений, PASS после них, полный suite, lint/typecheck, Range golden SHA до/после на шести реальных отрезках.

Исторический acceptance остаётся `NOT_READY`: 0 READY, 0 entries. Тестовые положительные сделки подтверждают работу автоматической технической цепочки; они не заменяют этот исторический результат. Во всех execution outputs `trade_entry_allowed=false`.
