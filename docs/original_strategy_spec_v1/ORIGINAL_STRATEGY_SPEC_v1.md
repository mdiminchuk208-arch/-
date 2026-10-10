# ORIGINAL_STRATEGY_SPEC_v1

**Verdict: NOT_IDENTIFIABLE.** Из13 уникальных source documents восстановлен
максимально faithful частичный контракт; единственная полностью определённая
исполняемая original trading strategy из этих материалов не идентифицируется.
Нельзя утверждать готовность Original A/B или запускать её financial backtest.
Offline evidence checker исполним, но не распознаёт все qualitative concepts
из OHLC и не создаёт торговых приказов. Spec v1 замораживает также его holes.

Основание: пользовательский запрос, `ORIGINAL_STRATEGY_SPEC_PROTOCOL.md`,
audit `c2d1e8cfb94637caaf150bb9c508cb011c3e85ba`. Baseline `19404ec0f4a7dd39b93c76240b6ad605278f0646` и все результаты audit неизменны.
Текущий MediumTermEngine используется только как ранее сохранённое comparison;
не импортируется builder/interpreter. Новые trades, P&L и financial comparisons
не создавались. Старые67.6768% не являются целевым результатом или source tree.

## Evidence и source hierarchy

8 DOCX +5 настоящих PDF; literal passages, SHA256 и page/paragraph locators
сохранены в registry. Изображения122unique/195media occurrences и54PDFpages
сохраняются в source originals и прежних visual review receipts; новый anchor
index привязывает inline diagrams к textual context. Все13text были полностью
прочитаны в предыдущем audit; этот этап повторно сверяет relevant passages и
diagrams, не выдаёт OCR за отдельный original source. SW7 доступен только как
.lnk; OTE цитируется по DOC19, не по непрочитанному SW7.

Resolver order задан пользователем: explicit primary rule → более конкретное
→ setup-specific → text/diagram consistency → доказанная chronology.
Capture dates и March посты DOC20 не доказывают, что он отменяет primary SMC.
В DOC03P0004/P0007 автор описывает toolbox/менторство для развития личного
стиля; complete branch-priority/price/lifecycle таблицы в наборе нет.
Все шесть resolver-документов сохраняют варианты, conflicts и предел знания.

## Три слоя

SOURCE_RULE имеет original document, literal excerpt, page/diagram, applicability,
known_at. PROJECT_POLICY имеет authority User/project; TECHNICAL_NORMALIZATION
имеет явную числовую/алгоритмическую трактовку или статус OPEN. B/C не SOURCE.
Confidence HIGH_LITERAL не утверждает уникальность executable normalization.
Фиксированные технические правила времени/immutability обеспечивают correctness,
а не создают alpha. Качественный source факт требует provenance annotation;
отсутствие annotation даёт UNKNOWN, не PASS.

## TF_ROLE_MATRIX

[CSV](TF_ROLE_MATRIX.csv): W1/D1 global, H1/H4 local; M15 relative HTF POI/OB и
relative LTF refinement. SFP allTF; H1+ preference. Conservative OB LTF1–15M,
строго ниже HTF; M15–D1 явно перечислены как HTF, «и т.д.» оставляет allowance
выше D1 не исчерпывающе определённым. Нельзя считать D1 абсолютным source ceiling.
Нет universal H1/H4 owner, обязательной четырёхTF conjunction или universal D1
directional gate. Source context/relative higher POI там, где его требует setup,
не исчезает при удалении лишнего owner gate. Unavailable dataset TF — не source prohibition.

## Контракты branches и место концептов

| Branch | Role | Contract status |
|---|---|---|
| [SFP](branch_contracts/SFP.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [OB_DIRECT](branch_contracts/OB_DIRECT.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [OB_CONSERVATIVE](branch_contracts/OB_CONSERVATIVE.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [BREAKER](branch_contracts/BREAKER.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [STB_BTS](branch_contracts/STB_BTS.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [RANGE_AGGRESSIVE](branch_contracts/RANGE_AGGRESSIVE.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [RANGE_CONSERVATIVE](branch_contracts/RANGE_CONSERVATIVE.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [RANGE_RETURN_CHOCH](branch_contracts/RANGE_RETURN_CHOCH.md) | TRADE_SETUP | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [DEMAND_SUPPLY_POI](branch_contracts/DEMAND_SUPPLY_POI.md) | POI_COMPONENT | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [FVG_POI](branch_contracts/FVG_POI.md) | POI_COMPONENT | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [OTE_CONFLUENCE](branch_contracts/OTE_CONFLUENCE.md) | CONFLUENCE_COMPONENT | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |
| [AMD_CONTEXT](branch_contracts/AMD_CONTEXT.md) | CONTEXT_COMPONENT | PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE |

Каждый contract задаёт CONTEXT→FORMATION→CONFIRMATION→POI→TRIGGER→ENTRY ZONE
→OPTIMAL ENTRY→INVALIDATION→SL→TARGET/FTA→RE-ENTRY с citations и holes.
Market Structure определяет structural context/BOS/CONF; Order Flow добавляет
raid/liquidity и destination. Liquidity даёт setup cause/target/adverse role.
SFP external raid/reclaim — formation, а не обещание future reversal.
BOS/CHOCH меняет structure; CONF — update новой structure, не синоним BOS.
OB/FVG/SnD/Breaker/STB дают typed POI; FVG и OTE не отдельный trade сигнал.
OTE0.705–0.79 — optional confluence selected causal impulse; P/D — midpoint
относящегося range, обязательный для SnD definition. Range имеет собственные
deviation/reclaim/80–20 styles. FTA ограничивает ближайшее препятствие.

## Conservative OB: точные source границы

SW9p2–6: raid, engulf, BOS, higher POI, structural impulse direction;
zone вся свеча с wicks, первый тест преимущественно. IMB strongest-quality
и stacked-OB priority конкретны; universal no-IMB prohibition не доказан.
HTF15M–1D examples → LTF1–15M → smooth structural approach → reaction → BOS
→new POI →limit. Smooth не заменяется fitted ATR/candle-count filter.
SW5 послеCONF — отдельный более поздний conservative style, не extra AND
в каждой SW9 entry. OTE/P-D confluence учитывается с явными impulse anchors;
universal OTE для всех branches source не требует. SL choices SW9p3 относятся
к OB; p9 aggressive/conservative stops относятся к Breaker и не доказывают
универсальный HTF raid stop для conservative OB. Entry quote, approach metric,
local-vs-parent stop и invalidation lifecycle остаются OPEN.

## Adverse liquidity

[Полный resolver](ADVERSE_LIQUIDITY_SOURCE_RESOLVER.md) отвечает на meaningful,
TF, setup relation, distance, flow, target vs blocker, sweep и tilted EQ.
Source conditional запрет установлен; uniquely correct автоматический classifier
не установлен. Proven ADVERSE→WAIT_SWEEP, TARGET/FTA не automatic blocker,
UNKNOWN→UNRESOLVED. После sweep переоценить актуальный setup, не выдать
автоматический entry. Старые751flags/446LOSS не удалены; точные audit conclusions
и3680ENGINE_EXTRA_REJECTION сохранены без нового исхода или reinterpretation.

## STOP и EXIT

ORIGINAL_SOURCE_STOP_POLICY=FIXED_INITIAL_PROTECTIVE_STOP в primary scope.
SW11p8 + SFP-specific SW12p13 выше mixed DOC20BE10–15%; conflict не скрыт.
Source manual SFP body-invalid exit отделён от protective stop move.
CRYPTO_BOT_PROJECT_BE_POLICY=costBE after TP1 только отдельный project overlay.
Его применение меняет source stop management, поэтому требует маркировки
project-managed variant; оно не доказывает Original fidelity.
SL anchors: OB extreme/engulf; Breaker body/raid; SFP ATR-from-extreme.
Buffer/ATR-estimator/branch-specific отсутствующие stops нельзя брать молча
из current engine. Source0.25–2% account risk не stop-distance процент.

Non-Range FTA допускает full/partial; эти две alternatives записаны как
SOURCE_PERMITTED_VARIANT_A/B. Они **компоненты**, не две готовые стратегии:
partial fraction/remainder и contextual target owner/quote не определены.
Range80/20 отдельно;20% optional, остаточный выход OPEN. Canonical40/30/30
не original. Ни одно source-permitted сочетание не выбиралось по outcomes.

## Decision tree и causal semantics

[JSON](ORIGINAL_STRATEGY_DECISION_TREE_v1.json) и [human tree](ORIGINAL_STRATEGY_DECISION_TREE_v1.md).
Каждый node имеет source rule/citation/known_at/PASS/FAIL/UNKNOWN/next.
No fitted ML thresholds. PASS по evidence не равен executable ALLOW.
Unresolved material contract блокирует admission глобально. Synthetic LONG/SHORT
показывают удовлетворение/нарушение literal constraints; они не закрывают
source-normalization gaps и не создают trades.
Engineering envelope: completed candles, OPEN-only открытие, known_at не позже
decision time; swings только после right CLOSE; prefix/future mutation/replay
и BACKTEST/SHADOW parity на offline checker. Future holding-time/P&L поля не
используются. Source detection causality из предыдущего audit остаётся отдельным
сохранённым evidence; synthetic QA не выдаётся за новый real-history detector QA.

## Project overlays и composition

SOURCE STRATEGY → PROJECT ADMISSION → RISK ENGINE → POSITION MANAGEMENT → EXECUTION.
Anti-Scalp, edge_cost_ratio3, cost viability, total risk6%, daily/correlation,
leverage,40/30/30,costBE,exchange safety находятся в project_policy_registry.
Они сохранены и не интегрированы в source decision. PROJECT_ADMISSION может
получить только source ALLOW; сейчас ALLOW disabled. Production baseline сохраняется
целиком; новый project wiring не реализуется до identifiable/frozen version.
trade_entry_allowed=false; BACKTEST/SHADOW only; LIVE/private API forbidden.

## Material unresolved и freeze

[Шесть конкретных групп вопросов](UNRESOLVED_QUESTIONS.md): exit/remainder,
stop anchor/normalization, branch/entry selection, TF/context selection,
meaningful liquidity и qualitative geometry, re-entry identity/eligibility.
Source разрешённые варианты сохраняются; решения пользователя будут
PROJECT_POLICY/TECHNICAL_NORMALIZATION, если не предоставлена новая source evidence.
После ответа нужен новый version/freeze; старый spec с holes не переписывается.

Freeze SHA256 включает spec, citations, resolver decisions, builder/checker/tests
и source dependencies. Audit c2d1 tree проверяется побайтно. Profitability
backtest на этом этапе не запускался и при verdict NOT_IDENTIFIABLE заблокирован.

## SOURCE_RULE summary

| Rule | Applicability | Literal meaning |
|---|---|---|
| S_FRACTAL | context-dependent | Top-down анализ фрактальной структуры; W1/D1 глобально, H1/H4 локально. |
| S_STRUCTURE | mandatory | HH/HL вверх, LH/LL вниз; структура — фундамент анализа. |
| S_SWING | context-dependent | Три последовательные свечи; экстремум центральной строго выше/ниже двух крайних. |
| S_BOS | context-dependent | BOS пробивает ключевой HL/LH с закреплением тела; новая структура развивается после слома. |
| S_CONF | context-dependent | CONF — обновление ключевого экстремума новой структуры; консервативно искать вход после CONF. |
| S_FLOW | context-dependent | Актуальный Order Flow сочетает структуру, работу с ликвидностью и доставку в global POI. |
| S_POI | context-dependent | POI — диапазон ожидаемой реакции: OB, Breaker, манипуляции и другие элементы. |
| S_LIQUIDITY_CONTEXT | mandatory | Ликвидность — контекст и цель, не самостоятельный базовый сигнал; направление снятия заранее не гарантировано. |
| S_ADVERSE_BLOCK | mandatory | При ликвидности против сетапа вход категорически запрещён. |
| S_EQ_STRUCTURE | context-dependent | EQH/EQL между свингами субструктуры; разумный наклон: EQH левый выше правого, EQL левый ниже правого. |
| S_ADVERSE_WAIT | context-dependent | EQH/EQL под входом: вход после снятия; текст не задаёт зеркальный short алгоритм. |
| S_POOL_SCOPE | context-dependent | Internal между границами импульса/range своего TF; external за границами/на structural extremes; любые TF. |
| S_PREVIOUS_LEVELS | optional | PDH/PDL/PWH/PWL/PMH/PML — дополнительные liquidity ориентиры. |
| S_OB_FORMATION | mandatory | Свеча снимает ликвидность, затем агрессивная импульсная свеча поглощает её; BOS и HTF POI обязательны. |
| S_OB_ZONE | mandatory | Вся поглощённая свеча вместе с тенями — OB zone. |
| S_OB_TREND | mandatory | OB внутри структурного импульса; работать по его тренду. |
| S_OB_IMB | context-dependent | IMB повышает точность; начинающие игнорируют IMB/структуру/OTE; пример нижнего OB имеет приоритет из-за IMB. |
| S_OB_FIRST_TEST | context-dependent | Обычно первый тест; иногда повторный вход после реакции на LTF. |
| S_OB_DIRECT_ENTRY | context-dependent | Лимит на верхней LONG/нижней SHORT границе OB или внутри зоны. |
| S_OB_DIRECT_STOP | context-dependent | SL за экстремумом OB либо за тенью поглотившей свечи. |
| S_OB_CONS_TF | mandatory | HTF OB 15M–1D «и т.д.»; переключение на меньший TF 1–15M. |
| S_OB_APPROACH | mandatory | Ожидать плавный структурный подход в HTF OB. |
| S_OB_CONS_TRIGGER | mandatory | После реакции — LTF BOS и новая POI; лимит на новую POI. |
| S_BREAKER_FORMATION | mandatory | OB импульсно пробит цельным движением без проторговки; новый HH/LL, слом структуры. |
| S_BREAKER_IMB_CHOCH | context-dependent | В Методичке breaker обязательно прошит IMB, затем CHOCH. |
| S_BREAKER_STOPS | context-dependent | Aggressive SL за body broken OB; conservative за raid impulse extreme. |
| S_FVG | context-dependent | IMB — gap по теням соседних свечей, equilibrium 0.5; full fill тоже возможен. |
| S_SFP_FORMATION | mandatory | External structural/range liquidity raid, reclaim body CLOSE, следующая OPEN на reclaimed стороне. |
| S_SFP_TF | mandatory | SFP на любом TF, H1+ предпочтительно; нужен liquidity context. |
| S_SFP_REFINE | optional | После formation можно перейти на LTF, дождаться BOS и искать entry. |
| S_SFP_STOP | context-dependent | ATR расстояние отсчитывается от extreme SFP; защитный ордер не переставляется. |
| S_SFP_BODY_EXIT | mandatory | Закрыть, если свеча закрылась за SFP minimum/maximum; паттерн неактуален. |
| S_STB_FORMATION | mandatory | STB/BTS: основной тренд, raid, полное поглощение манипуляции, BOS либо CONF. |
| S_STB_ENTRY | context-dependent | Entry upper LONG/lower SHORT edge либо 0.5 STB/BTS; mitigation/Premium Discount. |
| S_PD | context-dependent | 0.5 — справедливая цена; покупки discount, продажи premium в соответствующем dealing range. |
| S_OTE | optional | OTE 0.705–0.79 — оптимальная зона; Fibonacci дополняет стратегию, особенно OB. |
| S_RANGE_FORMATION | mandatory | Impulse конец и correction конец задают границы; реакция на 0.5; неясный range пропустить. |
| S_RANGE_DEVIATION | mandatory | Deviation снимает внешнюю ликвидность; range trade после выхода за границы. |
| S_RANGE_AGGRESSIVE | context-dependent | Aggressive entry на deviation только с POI за range; divergence доп. фактор. |
| S_RANGE_CONSERVATIVE | context-dependent | Ждать external POI; если нет реакции — возврат/закрепление в range и тест границы/возвратной зоны. |
| S_RANGE_EXIT | mandatory | 80% всегда внутри у границы, 20% можно оставить на true breakout. |
| S_SND_FORMATION | mandatory | Последнее opposite move, old liquidity raid; Demand/Supply не тестированы; Demand discount, Supply premium. |
| S_SND_ROLE | context-dependent | Материал задаёт определение зон для совершенствования стратегии. |
| S_FTA | mandatory | Первая opposing POI/проблемная зона; тренд и контртренд; старший contextual TF. |
| S_FTA_EXIT_OPTIONS | context-dependent | FTA допускает full либо partial close, в том числе countertrend. |
| S_PLAN | mandatory | Entry, exit и TP точно определены до открытия; SL ограничивает убыток. |
| S_STOP_FIXED | mandatory | Первичный запрет переносить стоп, SFP явно fixed stop. |
| S_RISK_GUIDANCE | context-dependent | Account risk 0.25–2%, position size зависит от расстояния SL; fee отдельно. |
| S_INDICATORS_SUPPORT | mandatory | Индикаторы только подтверждают идею; не дают standalone buy/sell сигнал. |
| S_SUPPLEMENT_BE | context-dependent | В дополнительной обучалке BE после +10–15% на цену entry. |
| S_AMD | context-dependent | AMD: локальная transition POI либо рискованная покупка manipulation; liquidity/volume context. |
| S_MEDIUM_PREFERENCE | optional | H1 основной анализ medium, H4+ long в смешанном supplemental материале. |
| S_SL_OFF_POOL | mandatory | Не размещать стоп на уровне скопления ликвидности. |
