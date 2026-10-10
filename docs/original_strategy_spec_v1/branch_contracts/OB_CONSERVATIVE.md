# OB_CONSERVATIVE

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

Qualifying HTF OB M15–D1 явно, «и т.д.» не hard D1 ceiling; LTF1–15M, strictly lower.

Source support: S_OB_FORMATION, S_OB_TREND, S_OB_CONS_TF, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

HTF raid/engulf/BOS inside higher POI and impulse; IMB/P-D/OTE relationships recorded.

Source support: S_OB_FORMATION

## CONFIRMATION

Smooth approach→reaction→LTF body BOS→new POI; SW5 afterCONF alternative separate.

Source support: S_OB_FORMATION, S_OB_CONS_TRIGGER, S_CONF

## POI

Именно новая LTF POI, после known BOS; range/delivery context recorded.

Source support: S_OB_ZONE, S_OB_IMB, S_OB_FIRST_TEST, S_OB_CONS_TRIGGER

## TRIGGER

Retest новой LTF POI после её known_at; нельзя retrospective touch fill.

Source support: S_OB_APPROACH, S_OB_CONS_TRIGGER, S_ADVERSE_BLOCK

## ENTRY ZONE

Limit at new POI; border/internal price selector не определён.

Source support: S_OB_CONS_TRIGGER, S_PLAN

## OPTIMAL ENTRY

OTE confluence, если related impulse anchors causal; не substitute для reaction/BOS.

Source support: S_OB_IMB, S_OTE

## INVALIDATION

HTF setup or LTF trigger invalidation; source exact zone-retirement rule не complete.

Source support: S_PLAN

## SL

SW9p3 anchors применяются к OB; универсальное «conservative OB=SLзаHTFraid» не доказано: p9 относится к Breaker. Local vs parent stop OPEN.

Source support: S_OB_DIRECT_STOP, S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Nearest contextual FTA, не mandatory3 H4/D1 targets; full/partial unresolved.

Source support: S_LIQUIDITY_CONTEXT, S_PLAN, S_FTA, S_FTA_EXIT_OPTIONS

## RE-ENTRY

Повтор HTF OB требует новой valid reaction/LTF evidence; numerical approach/eligibility OPEN.

Source support: S_OB_FIRST_TEST

## Source rule citations

- S_OB_FORMATION: SW9 p2–2
- S_OB_ZONE: SW9 p2–3
- S_OB_TREND: SW9 p3–3; SW9 p16–16
- S_OB_IMB: SW9 p2–2; SW9 p6–7
- S_OB_FIRST_TEST: SW9 p3–3
- S_OB_CONS_TF: SW9 p4–6
- S_OB_APPROACH: SW9 p4–4
- S_OB_CONS_TRIGGER: SW9 p4–6
- S_OB_DIRECT_STOP: SW9 p3–3
- S_CONF: SW5 p6–7
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
