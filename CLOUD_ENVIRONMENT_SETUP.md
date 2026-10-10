# Проверенная настройка cloud environment

Применены skills cloud-environment-onboarding:setup и
cloud-environment:cloud-environment-runtime. Python 3.12, isolated venv
`/workspace/crypto-bot-venv`, editable crypto-bot-core 0.4.20.

Повторяемый installer: `scripts/cloud_environment_install.sh`. Он выполнен
дважды; pip check и imports numpy/scipy/sklearn/matplotlib/pyarrow прошли.
Логи: `data/reports/medium_term_2026_10_10/qa/setup_install*.log`.
Кэши находятся в writable /workspace/.cache; HOME не переназначается.

Сохранён конфигурационный draft revision 3:
`e2a8b1eb-ac42-439a-8412-7e6e877c0ea5~cecfgdraft_6ac9104296888191b68a218368e1dc29`.
Setup script и start instructions сохранены, PIP_CACHE_DIR и MPLCONFIGDIR
указаны как environment requirements. Draft требует публикации в настройках
cloud environment для использования при следующем запуске; сохранение draft
само по себе не публикует конфигурацию. Repository membership, ref main,
network policy и secret requirements сохранены. Новые secrets не нужны.

Workflow: library development и offline BACKTEST/SHADOW. Сервис запускать
не требуется. Читайте RESEARCH_PROTOCOL.md, EXIT_RESEARCH_PROTOCOL.md и
MEDIUM_TERM_CONTINUATION_STATUS.md. Всегда trade_entry_allowed=false.
Для completed medium segments используйте проверяемый --resume-existing;
незавершённые или ошибочные segments сохраняйте. Jobs не предполагаются
сохранившимися после нового запуска среды.

QA: unittest discover -s tests, compileall -q src scripts tests, mypy src,
ruff по изменённым файлам и полный lint с explicit baseline delta.
