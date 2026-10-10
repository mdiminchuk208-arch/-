# STB_BTS

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

Основной относящийся trend/active flow, global delivery destination; TF fixed list не задан.

Source support: S_STB_FORMATION, S_FLOW, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

STB LONG/BTS SHORT raid ликвидности и full absorption всей manipulation.

Source support: S_STB_FORMATION

## CONFIRMATION

BOS либо CONF, не оба универсально AND.

Source support: S_STB_FORMATION

## POI

Whole STB/BTS zone и0.5; source описывает mitigation.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## TRIGGER

Retest entry edge или0.5; source разрешает обе точки.

Source support: S_STB_ENTRY, S_ADVERSE_BLOCK

## ENTRY ZONE

LONG upper/SHORT lower zone edge либо midpoint0.5.

Source support: S_STB_ENTRY, S_PLAN

## OPTIMAL ENTRY

P/D0.5 manipulation/dealing range; exact range owner selection unresolved.

Source support: S_STB_ENTRY, S_PD

## INVALIDATION

Нарушение manipulation/structure/flow target test; exact technical zone failure OPEN.

Source support: S_FLOW, S_PLAN

## SL

Source не задаёт unique STB stop price; general technical primary stop fixed.

Source support: S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Flow destination/global POI + first contextual FTA; allocation unresolved.

Source support: S_FLOW, S_LIQUIDITY_CONTEXT, S_PLAN, S_FTA, S_FTA_EXIT_OPTIONS

## RE-ENTRY

Mitigation объясняет retest, но не max entries; repeat identity OPEN.

Source support: S_FLOW

## Source rule citations

- S_STB_FORMATION: SW22 p2–3
- S_STB_ENTRY: SW22 p3–4
- S_FLOW: SW22 p5–6
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
