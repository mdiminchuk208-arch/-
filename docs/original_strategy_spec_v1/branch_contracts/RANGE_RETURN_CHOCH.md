# RANGE_RETURN_CHOCH

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

DOC19 Range context + возврат после deviation; не universal trend-only.

Source support: S_RANGE_FORMATION, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

Range edges и midpoint reaction known; deviation outside old boundary.

Source support: S_RANGE_FORMATION, S_RANGE_DEVIATION

## CONFIRMATION

Return-driving zone сделала CHOCH; после return новый тест зоны.

Source support: S_RANGE_FORMATION, S_RANGE_DEVIATION, S_RANGE_CONSERVATIVE

## POI

Именно zone, отправившая обратно в range; не обязательно сама граница.

Source support: S_RANGE_CONSERVATIVE

## TRIGGER

Retest return-zone after known CHOCH.

Source support: S_RANGE_CONSERVATIVE, S_ADVERSE_BLOCK

## ENTRY ZONE

Zone entry exact quote selection OPEN.

Source support: S_RANGE_CONSERVATIVE, S_PLAN

## OPTIMAL ENTRY

Range0.5 confirmation, FVG/OTE optional при доказанном confluence.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## INVALIDATION

Return premise/zone failure; source lifecycle incomplete.

Source support: S_PLAN

## SL

Fixed primary protective SL, exact anchor OPEN.

Source support: S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Range80/20 branch-specific applies; nearest FTA mapping explicit plan needed.

Source support: S_RANGE_EXIT, S_LIQUIDITY_CONTEXT, S_PLAN, S_RANGE_EXIT

## RE-ENTRY

Fresh return evidence required; no universal lifetime ban.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## Source rule citations

- S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072; 19 word/document.xml:P0122–P0128
- S_RANGE_DEVIATION: 06 word/document.xml:P0074–P0094; 19 word/document.xml:P0125–P0130
- S_RANGE_CONSERVATIVE: 06 word/document.xml:P0124–P0129; 19 word/document.xml:P0129–P0130
- S_RANGE_EXIT: 06 word/document.xml:P0119–P0121
- S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073
- S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121
- S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066
- S_PLAN: SW11 p2–4
- S_STOP_FIXED: SW11 p8–8; SW12 p13–13
- S_SL_OFF_POOL: SW11 p8–8
- S_RANGE_EXIT: 06 word/document.xml:P0119–P0121

Known_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.
