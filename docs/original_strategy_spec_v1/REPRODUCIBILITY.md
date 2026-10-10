# Воспроизведение и freeze

Рабочий каталог `/workspace/-`, Python `/workspace/crypto-bot-venv/bin/python`.
Builder и interpreter используют только standard library; production package,
historical trades, fitted tree и exchange client не импортируются.

До freeze:

```bash
/workspace/crypto-bot-venv/bin/python scripts/build_original_strategy_spec_v1.py
/workspace/crypto-bot-venv/bin/python scripts/verify_original_strategy_spec_v1.py --validate
/workspace/crypto-bot-venv/bin/python -m unittest discover -s tests -p test_original_strategy_spec_v1.py -v
/workspace/crypto-bot-venv/bin/ruff check scripts/build_original_strategy_spec_v1.py scripts/original_strategy_spec_contract.py scripts/verify_original_strategy_spec_v1.py tests/test_original_strategy_spec_v1.py
/workspace/crypto-bot-venv/bin/python scripts/verify_original_strategy_spec_v1.py --freeze
```

После freeze использовать проверяемый resume:

```bash
/workspace/crypto-bot-venv/bin/python scripts/verify_original_strategy_spec_v1.py --resume-existing
```

Builder отказывается перегенерировать frozen v1. SHA256 manifest включает spec,
registry, tree, six resolvers, branch contracts, policies/normalizations, examples,
tests/producers и QA; manifest сам себя не хеширует. Commit содержит manifest;
его hash определяется после записи Git commit, поэтому не встроен внутрь самого
manifest. Нет циклического «commit должен содержать собственный hash».

Дополнительные файлы нового этапа меняют Git-visible membership относительно
19404. Старый `seal_source_fidelity_delivery.py --resume-existing` предназначен
для последнего состояния того этапа и теперь ожидаемо не принимает новые
additions. Новый verifier проверяет **тот же неизменный** старый manifest с
membership на архивном commit `c2d1e8c`, а все17851старых Git blobs — по текущим
bytes. Это не ослабление checksums и не переписывание прежнего lock.

Freeze spec ограничен собственным namespace и явно перечисленными code/test
files. Следующие этапы могут добавлять свои namespaces; менять sealed v1 нельзя.
Ответы пользователя требуют version2/freeze, а не new financial run старого v1.

Interpreter принимает integer UTC epoch seconds, relative TF длительности в
минутах (SFP допускает и1/60мин). Qualitative facts содержат bool, known_at,
completed_at, provenance evidence и optional dependencies. Это synthetic causal
annotations, а не скрытые OHLC thresholds. Next OPEN schema не содержит будущие
high/low/close. По неизвестному/future annotation возвращается UNKNOWN.

`SOURCE_CONDITIONS_PASS` означает только, что предъявленные literal evidence
условия согласованы. Для trade setup итог всё равно CONTRACT_UNRESOLVED;
для POI/OTE/AMD components — COMPONENT_ONLY. SOURCE ALLOW отключён, никакой
project admission или order не появляется. SFP body exit helper использует
переданный pattern-chart TF как явную diagnostic normalization `N_BODY_EXIT_TF`;
не доказывает уникальный resolver всех возможных candle TF.

Тесты проверяют semantic distinction, causal envelope и границу admission.
Synthetic prefix/future QA не заменяет real-history проверки будущего полного
детектора. Сохранённые real-history audit causal receipts остаются неизменны;
новый profitability backtest не запускался. `trade_entry_allowed=false`.
