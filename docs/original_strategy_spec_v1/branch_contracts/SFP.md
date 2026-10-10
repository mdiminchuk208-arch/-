# SFP

Role: `TRADE_SETUP`. Status: `PARTIAL_SOURCE_CONTRACT_NOT_IDENTIFIABLE`.

## CONTEXT

Causal structural/range external liquidity; source-valid любой TF, H1+ preference.

Source support: S_SFP_TF, S_LIQUIDITY_CONTEXT, S_STRUCTURE, S_ADVERSE_BLOCK

## SETUP FORMATION

Wick raid old external level + body reclaim; не foreknowledge pattern.

Source support: S_SFP_FORMATION

## CONFIRMATION

Следующая native OPEN на reclaimed стороне; optional LTF BOS refinement отдельно.

Source support: S_SFP_FORMATION

## POI

Pattern raid zone и последующая contextual POI при refinement; точная POI price не задана.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## TRIGGER

Formation сама не равна приказу market entry; LTF BOS optional разрешён.

Source support: S_SFP_REFINE, S_ADVERSE_BLOCK

## ENTRY ZONE

На source-confirmed POI/паттерне; exact quote/order type unresolved.

Source support: S_SFP_REFINE, S_PLAN

## OPTIMAL ENTRY

OTE не обязательна; применима только если выбранный impulse/POI confluence доказан.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## INVALIDATION

Native pattern-TF body close за raid extreme делает pattern неактуальным.

Source support: S_SFP_BODY_EXIT, S_PLAN

## SL

SFP ATR beyond extreme, fixed protective SL; estimator/buffer unresolved.

Source support: S_SFP_STOP, S_PLAN, S_STOP_FIXED, S_SL_OFF_POOL

## TARGET/FTA

Nearest contextual FTA/liquidity; full/partial unresolved; body failure — separate exit.

Source support: S_LIQUIDITY_CONTEXT, S_PLAN, S_FTA, S_FTA_EXIT_OPTIONS

## RE-ENTRY

После failure нельзя reuse старый SFP; новый formation — новая evidence, retry selector unresolved.

Source support: OPEN: unique source algorithm absent; no fabricated rule.

## Source rule citations

- S_SFP_FORMATION: 16 word/document.xml:P0068–P0083; 19 word/document.xml:P0157–P0162
- S_SFP_TF: 16 word/document.xml:P0102–P0106; 19 word/document.xml:P0161–P0162
- S_SFP_REFINE: 16 word/document.xml:P0084–P0087
- S_SFP_STOP: SW12 p12–13
- S_SFP_BODY_EXIT: SW12 p13–13
- S_LIQUIDITY_CONTEXT: 14 word/document.xml:P0113–P0120; 19 word/document.xml:P0117–P0121
- S_STRUCTURE: SW5 p2–3; 19 word/document.xml:P0053–P0073
- S_ADVERSE_BLOCK: 03 word/document.xml:P0061–P0066
- S_PLAN: SW11 p2–4
- S_STOP_FIXED: SW11 p8–8; SW12 p13–13
- S_SL_OFF_POOL: SW11 p8–8
- S_FTA: SW9 p11–13; SW9 p16–16
- S_FTA_EXIT_OPTIONS: SW9 p11–11; SW9 p16–16

Known_at: все formation/confirmation/POI dependencies после native CLOSE; entry не раньше causal trigger. POI-component и confluence-component не получают самостоятельный ALLOW. Все материальные questions в UNRESOLVED_QUESTIONS.md; отсутствие цены/SL/target не заполняется current engine.
