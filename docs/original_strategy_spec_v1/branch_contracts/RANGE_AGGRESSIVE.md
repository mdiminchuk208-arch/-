# RANGE_AGGRESSIVE

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

После impulse/correction clear range с midpoint reaction, внешний POI.

Source support: S_RANGE_FORMATION, S_STRUCTURE, S_LIQUIDITY_CONTEXT, S_ADVERSE_BLOCK

## SETUP FORMATION

Первый конец impulse и законченная correction задают edges; liquidity inside/outside.

Source support: S_RANGE_FORMATION, S_RANGE_DEVIATION

## CONFIRMATION

Known deviation снимает external liquidity; weakness/divergence optional.

Source support: S_RANGE_FORMATION, S_RANGE_DEVIATION

## POI

Outside POI below LONG deviation/above SHORT, не arbitrary LTF standalone signal.

Source support: S_RANGE_AGGRESSIVE

## TRIGGER

На deviation с outside POI; не ждать будущий возврат для заднего entry.

Source support: S_RANGE_AGGRESSIVE, S_ADVERSE_BLOCK

## ENTRY ZONE

Цена в outside POI; exact quote/order unresolved.

Source support: S_RANGE_AGGRESSIVE, S_PLAN

## OPTIMAL ENTRY

Range midpoint/P-D/context; OTE не universal range gate.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## INVALIDATION

Range/POI/context failure; acceptance breakout qualitative OPEN.

Source support: S_PLAN

## SL

General technical stop beyond invalidator; branch-specific exact anchor/buffer OPEN.

Source support: S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

80% внутри у opposite boundary;20% optional breakout; offset/remainder OPEN.

Source support: S_RANGE_EXIT, S_LIQUIDITY_CONTEXT, S_PLAN, S_RANGE_EXIT

## RE-ENTRY

Новая deviation/evidence требует recheck range; unlimited recycling не source.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## Source rule citations

- S_RANGE_FORMATION: 06 word/document.xml:P0037–P0072; 19 word/document.xml:P0122–P0128
- S_RANGE_DEVIATION: 06 word/document.xml:P0074–P0094; 19 word/document.xml:P0125–P0130
- S_RANGE_AGGRESSIVE: 06 word/document.xml:P0111–P0118
- S_RANGE_EXIT: 06 word/document.xml:P0119–P0121
- S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073
- S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121
- S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066
- S_PLAN: SW11 p2–4
- S_STOP_FIXED: SW11 p8–8; SW12 p13–13
- S_SL_OFF_POOL: SW11 p8–8
- S_RANGE_EXIT: 06 word/document.xml:P0119–P0121

Known_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.
