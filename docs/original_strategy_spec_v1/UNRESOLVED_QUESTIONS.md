# Минимальный пакет решений пользователя

Шесть групп материальных решений. Это вопросы о логике, не запрос approval backtest. A/B ниже — source scopes/варианты, а не обещание двух готовых стратегий. Где source не даёт алгоритма, требуются annotations или явно маркированная normalization.

## Q_EXIT

Для non-Range выбрать full FTA или partial FTA? Для partial и optional Range20% задайте fraction, остаточную target/exit rule и точный смысл «у границы».

- Source option A: FULL_FTA: весь объём у первой contextual FTA (SW9 p11/16).
- Source option B: PARTIAL_FTA: часть у FTA (SW9 p11/16); Range80% внутри, optional20% breakout (DOC06 P0119–21).
- Логические последствия: A завершает non-Range trade на FTA; B оставляет остаток и требует отдельного complete plan. Range остаётся отдельным.
- Рекомендация: Нет source-приоритета между разрешёнными стилями.
- Gap: Source разрешает оба, не задаёт fraction/остаточный lifecycle/near offset.

## Q_STOP

Как выбирать source SL anchor по ветвям: OB extreme или engulf wick; Breaker body или raid extreme? Для SFP подтвердите ATR construction, период и beyond-level buffer; для STB/Range отдельный structural stop.

- Source option A: OB extreme (SW9 p3), Breaker aggressive body (p9), technical SL (SW11 p4).
- Source option B: OB engulf wick (SW9 p3), Breaker conservative raid extreme (p9); SFP ATR beyond pattern extreme (SW12 p12–13).
- Логические последствия: Меняется initial invalidation price и sizing; initial protective stop primary profile остаётся фиксированным.
- Рекомендация: Primary fixed initial stop лучше подтверждён SW11p8 и SFP-specific SW12p13; между разрешёнными anchors приоритета нет.
- Gap: Нет общего selector и buffers; source risk account percent не выбирает price anchor.

## Q_BRANCH_ENTRY

Какой стиль entry выбрать для OB direct vs LTF-confirmed, STB edge vs0.5, Range aggressive vs return/retest? Если несколько setups описывают один эпизод — какая ветвь владеет entry и какой causal physical-id/selection rule?

- Source option A: Direct OB border/intrazone (SW9 p3), STB edge (SW22p3), Range deviation with outside POI (DOC06 P0111–18).
- Source option B: OB reaction→LTF BOS→new POI (SW9 p4–6), STB0.5 (SW22p3), Range reclaim/retest (DOC06 P0124–29 / DOC19P0130).
- Логические последствия: Разные trigger timing и planned entry price; confluence не доказывает несколько независимых trades.
- Рекомендация: Нет source-приоритета между разрешёнными стилями.
- Gap: Source перечисляет styles, но не total ordering/ownership. SFP formation nextOPEN сама не задаёт market-fill contract.

## Q_TF

Как выбирать обследуемые TF и contextual TF/FTA owner среди нескольких валидных контекстов? Нужен explicit mapping по setup, без universal owner gate.

- Source option A: SFP/structure all TF (DOC16P0102–06, DOC19P0060/P0161); относительный HTF→LTF (DOC03P0028–30).
- Source option B: Конкретный conservative OB HTF M15–D1 и LTF M1–M15 (SW9p4–6); SFP H1+ preferred, не запрет ниже.
- Логические последствия: Определяется пространство поиска и выбор context; эти source scopes совместимы, A/B не глобально взаимоисключающие ladders.
- Рекомендация: Сохранить доказанные conservative LTF bounds и allTF SFP permission. Source не рекомендует единый selector остальных TF.
- Gap: Роли известны, deterministic TF selection нет; W1 conservative allowance за «и т.д.» не исчерпывающе задан.

## Q_LIQUIDITY_NORMALIZATION

Нужны causal LONG/SHORT размеченные примеры или явное правило для meaningful liquidity относительно setup, её TF/scope, reasonable EQ tilt и снятия. Также задайте smooth approach/whole impulse/range clarity/ключевые structural endpoints; source числовых thresholds не даёт.

- Source option A: Liquidity против setup → запрет до sweep; EQ example под entry (DOC03P0065, DOC14P0155–59).
- Source option B: Liquidity в направлении source delivery → target/fuel; opposing POI впереди → FTA (DOC14P0113–20, SW9p11–16).
- Логические последствия: A и B — разные роли, не две конкурирующие стратегии. Требуется правило классификации, а не blanket запрет всех unswept pools.
- Рекомендация: Категорический запрет только после доказанной contextual adverse classification; unknown scope оставлять UNRESOLVED.
- Gap: Источник не определяет единственный classifier. Ни один numeric cutoff или old751 removal не авторизован. Числовые решения будут TECHNICAL_NORMALIZATION, не SOURCE_RULE.

## Q_REENTRY

Использовать только первый OB test или разрешать некоторые повторные входы после новой LTF reaction? Для repeat нужны eligibility, new-evidence identity, simultaneous ownership и max retries/cooldown, если они нужны проекту.

- Source option A: Работа исключительно от первого OB test как основной стиль (SW9p3, «в90% случаев»).
- Source option B: Некоторые повторные OB entries после LTF reaction (SW9p3).
- Логические последствия: A исключает repeat style; B требует новую reaction и полную повторную валидацию. Tested SnD не превращается в новую untapped zone.
- Рекомендация: Нет source-приоритета между разрешёнными стилями.
- Gap: 90% не квота/random gate; «некоторые» не формальный resolver. Lifetime dedup не источник.
