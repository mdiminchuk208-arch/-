# ORIGINAL_STRATEGY_DECISION_TREE_v1

**NOT_IDENTIFIABLE**. Исполнимо как проверка переданных source evidence. Автоматическое распознавание качественных source concepts из OHLC не реализовано.

START → выбранная source branch → контекст → formation/confirmation → POI/entry → invalidation/SL/target plan → lifecycle. Source priority между branches неизвестен.

Каждый SOURCE node: PASS → следующий; FAIL → SOURCE_REJECT; UNKNOWN → SOURCE_UNRESOLVED. Завершение пути означает только SOURCE_CONDITIONS_PASS. Глобальный verdict блокирует ALLOW и PROJECT_ADMISSION до закрытия material gaps и следующего freeze.

После source path: global contract gap gate entry/invalidation/lifecycle → CONTRACT_UNRESOLVED. Он не маскируется под дополнительный SOURCE_RULE node. Engineering envelope отдельно проверяет timestamps/completed-only. Даже semantic PASS не создаёт fills, portfolio или financial results.

## SFP (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| SFP:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | SFP:1 | REJECT / UNRESOLVED |
| SFP:1 | context | S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121 | dependencies ≤ decision; OPEN только open | SFP:2 | REJECT / UNRESOLVED |
| SFP:2 | formation | S_SFP_FORMATION: 16 word/document.xml:P0068–P0083; 19 word/document.xml:P0157–P0162 | dependencies ≤ decision; OPEN только open | SFP:3 | REJECT / UNRESOLVED |
| SFP:3 | next_open | S_SFP_FORMATION: 16 word/document.xml:P0068–P0083; 19 word/document.xml:P0157–P0162 | dependencies ≤ decision; OPEN только open | SFP:4 | REJECT / UNRESOLVED |
| SFP:4 | tf | S_SFP_TF: 16 word/document.xml:P0102–P0106; 19 word/document.xml:P0161–P0162 | dependencies ≤ decision; OPEN только open | SFP:5 | REJECT / UNRESOLVED |
| SFP:5 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | SFP:6 | REJECT / UNRESOLVED |
| SFP:6 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | SFP:7 | REJECT / UNRESOLVED |
| SFP:7 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | SFP:8 | REJECT / UNRESOLVED |
| SFP:8 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | SFP:9 | REJECT / UNRESOLVED |
| SFP:9 | target | S_FTA: SW9 p11–13; SW9 p16–16 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## OB_DIRECT (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| OB_DIRECT:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | OB_DIRECT:1 | REJECT / UNRESOLVED |
| OB_DIRECT:1 | formation | S_OB_FORMATION: SW9 p2–2 | dependencies ≤ decision; OPEN только open | OB_DIRECT:2 | REJECT / UNRESOLVED |
| OB_DIRECT:2 | higher_poi | S_OB_FORMATION: SW9 p2–2 | dependencies ≤ decision; OPEN только open | OB_DIRECT:3 | REJECT / UNRESOLVED |
| OB_DIRECT:3 | trend | S_OB_TREND: SW9 p3–3; SW9 p16–16 | dependencies ≤ decision; OPEN только open | OB_DIRECT:4 | REJECT / UNRESOLVED |
| OB_DIRECT:4 | test | S_OB_FIRST_TEST: SW9 p3–3 | dependencies ≤ decision; OPEN только open | OB_DIRECT:5 | REJECT / UNRESOLVED |
| OB_DIRECT:5 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | OB_DIRECT:6 | REJECT / UNRESOLVED |
| OB_DIRECT:6 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | OB_DIRECT:7 | REJECT / UNRESOLVED |
| OB_DIRECT:7 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | OB_DIRECT:8 | REJECT / UNRESOLVED |
| OB_DIRECT:8 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | OB_DIRECT:9 | REJECT / UNRESOLVED |
| OB_DIRECT:9 | target | S_FTA: SW9 p11–13; SW9 p16–16 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## OB_CONSERVATIVE (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| OB_CONSERVATIVE:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:1 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:1 | formation | S_OB_FORMATION: SW9 p2–2 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:2 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:2 | higher_poi | S_OB_FORMATION: SW9 p2–2 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:3 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:3 | trend | S_OB_TREND: SW9 p3–3; SW9 p16–16 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:4 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:4 | tf | S_OB_CONS_TF: SW9 p4–6 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:5 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:5 | approach | S_OB_APPROACH: SW9 p4–4 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:6 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:6 | trigger | S_OB_CONS_TRIGGER: SW9 p4–6 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:7 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:7 | test | S_OB_FIRST_TEST: SW9 p3–3 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:8 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:8 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:9 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:9 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:10 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:10 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:11 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:11 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | OB_CONSERVATIVE:12 | REJECT / UNRESOLVED |
| OB_CONSERVATIVE:12 | target | S_FTA: SW9 p11–13; SW9 p16–16 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## BREAKER (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| BREAKER:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | BREAKER:1 | REJECT / UNRESOLVED |
| BREAKER:1 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | BREAKER:2 | REJECT / UNRESOLVED |
| BREAKER:2 | formation | S_BREAKER_FORMATION: SW9 p7–8 | dependencies ≤ decision; OPEN только open | BREAKER:3 | REJECT / UNRESOLVED |
| BREAKER:3 | flow | S_FLOW: SW22 p5–6 | dependencies ≤ decision; OPEN только open | BREAKER:4 | REJECT / UNRESOLVED |
| BREAKER:4 | poi | S_POI: SW9 p10–11 | dependencies ≤ decision; OPEN только open | BREAKER:5 | REJECT / UNRESOLVED |
| BREAKER:5 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | BREAKER:6 | REJECT / UNRESOLVED |
| BREAKER:6 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | BREAKER:7 | REJECT / UNRESOLVED |
| BREAKER:7 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | BREAKER:8 | REJECT / UNRESOLVED |
| BREAKER:8 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | BREAKER:9 | REJECT / UNRESOLVED |
| BREAKER:9 | target | S_FTA: SW9 p11–13; SW9 p16–16 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## STB_BTS (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| STB_BTS:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | STB_BTS:1 | REJECT / UNRESOLVED |
| STB_BTS:1 | trend | S_STB_FORMATION: SW22 p2–3 | dependencies ≤ decision; OPEN только open | STB_BTS:2 | REJECT / UNRESOLVED |
| STB_BTS:2 | formation | S_STB_FORMATION: SW22 p2–3 | dependencies ≤ decision; OPEN только open | STB_BTS:3 | REJECT / UNRESOLVED |
| STB_BTS:3 | flow | S_FLOW: SW22 p5–6 | dependencies ≤ decision; OPEN только open | STB_BTS:4 | REJECT / UNRESOLVED |
| STB_BTS:4 | pd | S_PD: SW22 p4–4; 19 word/document.xml:P0140–P0155 | dependencies ≤ decision; OPEN только open | STB_BTS:5 | REJECT / UNRESOLVED |
| STB_BTS:5 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | STB_BTS:6 | REJECT / UNRESOLVED |
| STB_BTS:6 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | STB_BTS:7 | REJECT / UNRESOLVED |
| STB_BTS:7 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | STB_BTS:8 | REJECT / UNRESOLVED |
| STB_BTS:8 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | STB_BTS:9 | REJECT / UNRESOLVED |
| STB_BTS:9 | target | S_FTA: SW9 p11–13; SW9 p16–16 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## RANGE_AGGRESSIVE (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| RANGE_AGGRESSIVE:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:1 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:1 | range | S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072; 19 word/document.xml:P0122–P0128 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:2 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:2 | deviation | S_RANGE_DEVIATION: 06 word/document.xml:P0074–P0094; 19 word/document.xml:P0125–P0130 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:3 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:3 | poi | S_RANGE_AGGRESSIVE: 06 word/document.xml:P0111–P0118 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:4 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:4 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:5 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:5 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:6 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:6 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:7 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:7 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | RANGE_AGGRESSIVE:8 | REJECT / UNRESOLVED |
| RANGE_AGGRESSIVE:8 | target | S_RANGE_EXIT: 06 word/document.xml:P0119–P0121 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## RANGE_CONSERVATIVE (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| RANGE_CONSERVATIVE:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:1 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:1 | range | S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072; 19 word/document.xml:P0122–P0128 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:2 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:2 | deviation | S_RANGE_DEVIATION: 06 word/document.xml:P0074–P0094; 19 word/document.xml:P0125–P0130 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:3 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:3 | poi | S_RANGE_AGGRESSIVE: 06 word/document.xml:P0111–P0118 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:4 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:4 | retest | S_RANGE_CONSERVATIVE: 06 word/document.xml:P0124–P0129; 19 word/document.xml:P0129–P0130 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:5 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:5 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:6 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:6 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:7 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:7 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:8 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:8 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | RANGE_CONSERVATIVE:9 | REJECT / UNRESOLVED |
| RANGE_CONSERVATIVE:9 | target | S_RANGE_EXIT: 06 word/document.xml:P0119–P0121 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## RANGE_RETURN_CHOCH (TRADE_SETUP)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| RANGE_RETURN_CHOCH:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:1 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:1 | range | S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072; 19 word/document.xml:P0122–P0128 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:2 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:2 | deviation | S_RANGE_DEVIATION: 06 word/document.xml:P0074–P0094; 19 word/document.xml:P0125–P0130 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:3 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:3 | return | S_RANGE_CONSERVATIVE: 06 word/document.xml:P0124–P0129; 19 word/document.xml:P0129–P0130 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:4 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:4 | adverse | S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:5 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:5 | plan | S_PLAN: SW11 p2–4 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:6 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:6 | stop | S_STOP_FIXED: SW11 p8–8; SW12 p13–13 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:7 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:7 | sl_liquidity | S_SL_OFF_POOL: SW11 p8–8 | dependencies ≤ decision; OPEN только open | RANGE_RETURN_CHOCH:8 | REJECT / UNRESOLVED |
| RANGE_RETURN_CHOCH:8 | target | S_RANGE_EXIT: 06 word/document.xml:P0119–P0121 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## DEMAND_SUPPLY_POI (POI_COMPONENT)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| DEMAND_SUPPLY_POI:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | DEMAND_SUPPLY_POI:1 | REJECT / UNRESOLVED |
| DEMAND_SUPPLY_POI:1 | formation | S_SND_FORMATION: 18 word/document.xml:P0005–P0012 | dependencies ≤ decision; OPEN только open | DEMAND_SUPPLY_POI:2 | REJECT / UNRESOLVED |
| DEMAND_SUPPLY_POI:2 | pd | S_SND_FORMATION: 18 word/document.xml:P0005–P0012 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## FVG_POI (POI_COMPONENT)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| FVG_POI:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | FVG_POI:1 | REJECT / UNRESOLVED |
| FVG_POI:1 | formation | S_FVG: 16 word/document.xml:P0051–P0060; 19 word/document.xml:P0109–P0112 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## OTE_CONFLUENCE (CONFLUENCE_COMPONENT)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| OTE_CONFLUENCE:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | OTE_CONFLUENCE:1 | REJECT / UNRESOLVED |
| OTE_CONFLUENCE:1 | formation | S_OTE: 19 word/document.xml:P0138–P0156 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |

## AMD_CONTEXT (CONTEXT_COMPONENT)

| Node | Stage | Rule / citation | Known_at | PASS → | FAIL / UNKNOWN |
|---|---|---|---|---|---|
| AMD_CONTEXT:0 | context | S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073 | dependencies ≤ decision; OPEN только open | AMD_CONTEXT:1 | REJECT / UNRESOLVED |
| AMD_CONTEXT:1 | context | S_AMD: 19 word/document.xml:P0163–P0170 | dependencies ≤ decision; OPEN только open | SOURCE_CONDITIONS_PASS | REJECT / UNRESOLVED |
