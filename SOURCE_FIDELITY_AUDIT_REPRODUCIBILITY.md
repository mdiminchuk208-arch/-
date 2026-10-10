# Воспроизводимость source fidelity audit

Контроль: `19404ec0f4a7dd39b93c76240b6ad605278f0646`, текущая ветка
`medium-term-source-research`. Audit не изменяет production, canonical exits,
Anti-Scalp policy, исходные reports или main. `trade_entry_allowed=false`.
Используются только сохранённые public candles и offline BACKTEST/SHADOW.

Среда настроена по cloud-environment-onboarding:setup и runtime skill;
проверенная инструкция остаётся в `CLOUD_ENVIRONMENT_SETUP.md`, installer —
`scripts/cloud_environment_install.sh`. Новые зависимости и secrets не нужны.
Текущий интерпретатор: `/workspace/crypto-bot-venv/bin/python`.
Полные tests/mypy/compile прошли; полный Ruff содержит те же 555 прежних
диагностик, новых 0. Эта поставка сохраняет исходные файлы с этими замечаниями.

Все команды выполняются из корня repository. Для сохранённых completed
сегментов использовать проверяемый `--resume-existing`:

```bash
python scripts/replay_medium_role_correction.py --cohort primary --resume-existing
python scripts/evaluate_strategy_v2.py --resume-existing
python scripts/verify_source_fidelity_audit.py --resume-existing
python scripts/audit_source_fidelity_exits.py --resume-existing
python scripts/seal_source_fidelity_delivery.py --resume-existing
```

Первый source-state replay произведён точной committed версией `6eaf3d6`.
После завершения исправлены только три Ruff замечания в новом audit worker
(imports и dict literal). Его checksum изменился, поэтому прямой повторный
worker `--resume-existing` закономерно не принимает прежний fingerprint.
`verify_source_fidelity_audit.py --resume-existing` проверяет producer bytes
через `git show 6eaf3d6:scripts/audit_source_fidelity_state.py`, все остальные
dependencies по текущим байтам, затем строгие SHA256/членство COMPLETE artifacts.
Lock не переписывается. Изменение любого исходного data/code файла отклоняется.
Matched exits произведены уже с оформленным worker и проверяются напрямую.

Source inventory/matrix и fitted tree reconstruction воспроизводятся без
обучения и новых outcome решений:

```bash
python scripts/build_source_fidelity_audit.py sources
python scripts/build_source_fidelity_audit.py tree
python scripts/build_source_fidelity_audit.py traces
python scripts/build_source_fidelity_comparisons.py
python scripts/compare_source_fidelity_exits.py
python scripts/report_source_fidelity_audit.py
```

Проверки causality и baseline имеют отдельные сохранённые receipts:

```bash
python scripts/verify_source_fidelity_audit.py prefix
python scripts/verify_source_fidelity_audit.py exits
python scripts/verify_source_fidelity_audit.py baseline
```

Первый baseline verifier ошибочно воспринимал пять C-quoted кириллических путей
из Git как буквальные имена. Исправленная проверка сопоставляет frozen mapping
с NUL-separated исходным tree и проверяет каждый из 17 728 действительных blob.
Исходный baseline lock и первоначальный failure log сохранены.
Два первых comparison probes использовали неверное имя independent artifact и
ожидали отсутствующие MFE_R поля; сохранены логи, итоговый builder читает
`independent_cases.jsonl.gz` и выводит R из первоначального risk, без изменения
исходных artifacts. Новых завершённых результатов из ошибочных probes не было.

Не добавлять файлы внутрь sealed state/matched_exits: это нарушит membership.
Четыре undefined contextual FTA сохранены для каждой из двух соответствующих
моделей; нет fallback target или принудительного EOF exit. Exact strategy A/B
не заявлены: шесть contract gaps в `original_contract_gaps.csv` запрещают назвать
произвольно выбранный adapter точной ORIGINAL strategy. Model A source-permitted
exit diagnostic — одна зарегистрированная альтернатива, отличная от exact
strategy variant A.

`delivery_manifest.json` проверяет итоговую additive поставку и вложенные
manifests; итоговый commit указан в Git history и ответе пользователю.
