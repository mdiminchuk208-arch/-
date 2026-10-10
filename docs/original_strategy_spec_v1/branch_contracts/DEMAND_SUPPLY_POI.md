# DEMAND_SUPPLY_POI

Role: `POI_COMPONENT`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

Native HTF one candle/LTF multi-candle context; range P/D.

Source support: S_SND_FORMATION, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

Последний opposite move through old liquidity raid; untested Demand/Supply.

Source support: S_SND_FORMATION

## CONFIRMATION

POI definition не самостоятельный trade confirmation.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## POI

Demand/Supply eligible только при untapped/P-D.

Source support: S_SND_FORMATION

## TRIGGER

Trigger должен поступить из доказанной trade branch; independent trigger OPEN.

Source support: S_SND_ROLE, S_ADVERSE_BLOCK

## ENTRY ZONE

Exact independent entry price не source-defined.

Source support: S_SND_ROLE, S_PLAN

## OPTIMAL ENTRY

Demand discount / Supply premium обязательны для зоны.

Source support: S_SND_FORMATION, S_PD

## INVALIDATION

After test исходное untapped определение больше не выполнено.

Source support: S_PLAN

## SL

Independent SnD SL отсутствует; используйте parent branch contract после его closure.

Source support: S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Independent SnD exit отсутствует; zone может opposing FTA в другой ветви.

Source support: S_LIQUIDITY_CONTEXT, S_PLAN, S_FTA, S_FTA_EXIT_OPTIONS

## RE-ENTRY

Нельзя считать touched old zone новой untapped; новая causal formation отдельна.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## Source rule citations

- S_SND_FORMATION: 18 word/document.xml:P0005–P0012
- S_SND_ROLE: 18 word/document.xml:P0013–P0013
- S_PD: SW22 p4–4; 19 word/document.xml:P0140–P0155
- S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073
- S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121
- S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066
- S_PLAN: SW11 p2–4
- S_STOP_FIXED: SW11 p8–8; SW12 p13–13
- S_SL_OFF_POOL: SW11 p8–8
- S_FTA: SW9 p11–13; SW9 p16–16
- S_FTA_EXIT_OPTIONS: SW9 p11–11; SW9 p16–16

Known_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.
