# OB_DIRECT

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

OB внутри structural impulse своего направления и mandatory higher-TF POI.

Source support: S_OB_FORMATION, S_OB_TREND, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

Raid candle + aggressive engulf + BOS; весь native candle with wicks — zone.

Source support: S_OB_FORMATION

## CONFIRMATION

BOS; CONF более поздний optional style, не universal direct prerequisite.

Source support: S_OB_FORMATION

## POI

Untested/first-test OB; repeat requires new LTF reaction и unresolved eligibility.

Source support: S_OB_ZONE, S_OB_IMB, S_OB_FIRST_TEST

## TRIGGER

Последующий приход в OB; first test причинно после формирования.

Source support: S_OB_DIRECT_ENTRY, S_ADVERSE_BLOCK

## ENTRY ZONE

LONG upper boundary, SHORT lower boundary либо внутри zone (SW9p3).

Source support: S_OB_DIRECT_ENTRY, S_PLAN

## OPTIMAL ENTRY

OB+OTE0.705–0.79 source confluence; IMB quality/stacked priority, не universal all-branch gate.

Source support: S_OB_IMB, S_OTE

## INVALIDATION

Слом required structure/POI логики; exact body/wick retirement threshold OPEN.

Source support: S_PLAN

## SL

За OB extreme либо engulf wick; selector и buffer unresolved; fixed primary stop.

Source support: S_OB_DIRECT_STOP, S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Первый contextual opposing POI/FTA; full/partial plan unresolved.

Source support: S_LIQUIDITY_CONTEXT, S_PLAN, S_FTA, S_FTA_EXIT_OPTIONS

## RE-ENTRY

First primarily; repeat only fresh LTF reaction; no proven lifetime physical ban.

Source support: S_OB_FIRST_TEST

## Source rule citations

- S_OB_FORMATION: SW9 p2–2
- S_OB_ZONE: SW9 p2–3
- S_OB_TREND: SW9 p3–3; SW9 p16–16
- S_OB_IMB: SW9 p2–2; SW9 p6–7
- S_OB_FIRST_TEST: SW9 p3–3
- S_OB_DIRECT_ENTRY: SW9 p3–3
- S_OB_DIRECT_STOP: SW9 p3–3
- S_OTE: 19 word/document.xml:P0138–P0156
- S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073
- S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121
- S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066
- S_PLAN: SW11 p2–4
- S_STOP_FIXED: SW11 p8–8; SW12 p13–13
- S_SL_OFF_POOL: SW11 p8–8
- S_FTA: SW9 p11–13; SW9 p16–16
- S_FTA_EXIT_OPTIONS: SW9 p11–11; SW9 p16–16

Known_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.
