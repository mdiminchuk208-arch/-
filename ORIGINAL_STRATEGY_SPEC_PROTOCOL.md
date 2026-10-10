# ORIGINAL_STRATEGY_SPEC_v1 — этап до финансового результата

Авторизация: полный запрос пользователя сохранён в
`data/source_materials/original_strategy_spec_v1_2026_10_11/user_request.txt`.
Старт: `c2d1e8cfb94637caaf150bb9c508cb011c3e85ba`, ветка
`medium-term-source-research`. Baseline: `19404ec0f4a7dd39b93c76240b6ad605278f0646`.

На этом этапе разрешены только добавления: source specification, evidence,
проверяющий её offline interpreter, synthetic examples, tests и QA. Production
engine, все файлы audit commit, baseline, исторические сделки и финансовые
результаты сохраняются побайтно. Финансовый backtest не запускается.

SOURCE_RULE отделяется от PROJECT_POLICY и TECHNICAL_NORMALIZATION. Из отсутствия
однозначного resolver нельзя получать ALLOW. Исполнимый проверяющий контракт
может вернуть REJECT / UNRESOLVED / CONTRACT_UNRESOLVED; это не готовый детектор
рынка и не новая Original A. Synthetic факты проверяют логические source
условия и причинность, а не доказывают автоматическое извлечение качественных
условий из OHLC. PROJECT_ADMISSION допускается только после SOURCE ALLOW,
которое до закрытия материальных gaps недоступно.

Source-permitted альтернативы регистрируются как компоненты, с областью
применения и незаполненными параметрами. Их сочетание не объявляется новой
source strategy. Нет поиска, fitting, выбора по outcomes или удаления 751 сделок.

При NOT_IDENTIFIABLE сохраняем максимально восстановленный spec v1 с явными
holes, минимальный пакет вопросов и freeze такого состояния; не объявляем
контракт полностью определённым. При последующем решении пользователя нужен
новый version/freeze, а не исправление старого sealed spec.

QA: source citations/слои; branch LONG/SHORT; conservative TF; adverse liquidity;
branch exits и неподвижный стоп; propagation UNKNOWN/conflicts; completed-only,
known_at, prefix/future mutation, replay и BACKTEST/SHADOW; source->admission
boundary; immutable старый Git tree; SHA256 spec и всех его dependencies.

Freeze manifest не включает сам себя. Commit с manifest регистрируется и
публикуется без force push только в текущую research ветку. `main` не меняется.
`trade_entry_allowed=false`; LIVE и private API запрещены.
