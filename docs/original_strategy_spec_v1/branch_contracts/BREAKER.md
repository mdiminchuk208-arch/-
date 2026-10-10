# BREAKER

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

Structural direction/new HH/LL; может reversal или continuation; актуальное context flow.

Source support: S_FLOW, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

Prior qualifying OB цельно impulsively пробит без chopping; новая structure.

Source support: S_BREAKER_FORMATION, S_BREAKER_IMB_CHOCH

## CONFIRMATION

BOS в primary; supplemental DOC19 требует IMB затем CHOCH — конфликт scope открыт.

Source support: S_BREAKER_FORMATION, S_BREAKER_IMB_CHOCH, S_BOS

## POI

Broken OB zone как BR POI, body boundaries vs full candle stop distinct.

Source support: S_BREAKER_FORMATION, S_POI

## TRIGGER

Реакция/тест BR; exact timing method source examples not exhaustive.

Source support: S_POI, S_ADVERSE_BLOCK

## ENTRY ZONE

BR POI test, точная order/quote selection unresolved.

Source support: S_PLAN

## OPTIMAL ENTRY

Optional FVG/OTE confluence не fitted gate.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## INVALIDATION

Adverse structural change/BR failure; exact retired object lifecycle OPEN.

Source support: S_BOS, S_FLOW, S_PLAN

## SL

Body aggressive или raid impulse extreme conservative (SW9p9–10), fixed thereafter.

Source support: S_BREAKER_STOPS, S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Nearest contextual FTA; full/partial unresolved.

Source support: S_FLOW, S_LIQUIDITY_CONTEXT, S_PLAN, S_FTA, S_FTA_EXIT_OPTIONS

## RE-ENTRY

Typed BR repeat algorithm отсутствует, нельзя inherit lifetime policy как source.

Source support: S_FLOW

## Source rule citations

- S_BREAKER_FORMATION: SW9 p7–8
- S_BREAKER_IMB_CHOCH: 19 word/document.xml:P0113–P0116
- S_BREAKER_STOPS: SW9 p9–10
- S_POI: SW9 p10–11
- S_BOS: SW5 p4–5; 19 word/document.xml:P0088–P0100
- S_FLOW: SW22 p5–6
- S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073
- S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121
- S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066
- S_PLAN: SW11 p2–4
- S_STOP_FIXED: SW11 p8–8; SW12 p13–13
- S_SL_OFF_POOL: SW11 p8–8
- S_FTA: SW9 p11–13; SW9 p16–16
- S_FTA_EXIT_OPTIONS: SW9 p11–11; SW9 p16–16

Known_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.
