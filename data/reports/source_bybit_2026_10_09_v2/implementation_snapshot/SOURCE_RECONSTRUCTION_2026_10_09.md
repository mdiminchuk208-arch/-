# Supplied Cryptology archive: rules fixed before new outcomes

Input main: `8b0156346ae523a6d3fd721d6ea343de47f44afa`. Archive SHA256:
`33cee26232d90fe26840bb4fced2e75551a5368d59359ffecc4b72d92c3870b9`.
The archive, extracted full text and diagram OCR are retained under
`data/source_materials/cryptology_2026_10_09`. Re-extract with
`scripts/extract_cryptology_sources.py`; links are never executed or followed.

Eight actual DOCX documents were read in full, including embedded text boxes and
122 distinct raster diagrams (195 embedded references). There are no actual PDFs.
SW.BAND 5, 7, 9, 11, 12 and 22 are Windows shortcuts, not their promised contents.
Their rules cannot be attributed to a fresh reading of this ZIP. Earlier project
summaries remain secondary evidence, explicitly distinguished below. OCR is a
reading aid, not ground truth; diagrams were also inspected visually.

Paragraph identifiers below refer to the retained clean text. DOC03 = Smart Money
Trader 2; DOC06 = SW10 Range; DOC11 = SW4 Structure Base; DOC14 = SW6 Liquidity;
DOC16 = SW8 Tools Base; DOC18 = Demand/Supply; DOC19 = Методичка; DOC20 = обучалка.

| Component | Classification and original evidence | Machine policy before PnL |
|---|---|---|
| Structure | SOURCE_RULE: DOC11 P75–77; DOC19 P62–100; diagrams HH/HL, LL/LH, protected-level BOS | Retain SOURCE_CONSERVATIVE analyzer; confirmed alternating swings, protected-level BOS, opposite new structure; CONF is its later extreme update, separate from BOS. No technical recovery. |
| Liquidity | SOURCE_RULE: DOC03 P47–65; DOC14 P145–185; structural EQH/EQL diagrams | Confirmed swing pools, BSL/SSL, exact equal highs/lows, internal/external and previous completed UTC day. Near-equal clustering has no supplied numerical tolerance: remains unknown, not inferred from two random bars. |
| Liquidity against setup | SOURCE_RULE: DOC03 P65 categorical prohibition; DOC14 P156–159 | SOURCE_INTERPRETATION: unswept adverse-side structural pools between intended entry and sweep/technical SL must be raided first. Unresolved pools at the relevant context are WAIT; do not reject every unrelated distant swing. |
| SFP | SOURCE_RULE: DOC16 P68–87, DOC19 P159–163 and diagram DOC16/image6 | Strict wick raid, body reclaim, following open valid side, then causal LTF BOS/new structure. Later body close beyond raid extreme invalidates. LONG mirrors SHORT wording. |
| OB | SOURCE_RULE: DOC19 P104–109; diagrams image11–13; DOC20 P172–185 | Last opposite candle before engulf/displacement plus three-candle IMB and structural impulse plus raid; full wick zone. Qualitative body dominance is an interpretation, no fitted .6 filter. Formation and structure availability precede first-test clock. |
| OB repeated test | Secondary source summary: SOURCE_OF_TRUTH_TRADING_RULES section4 describes missing SW9 | Explicit separate LTF reaction/new structure after repeat touch required. This exception is labelled SECONDARY_SOURCE_INTERPRETATION, never copied to D/S; primary uses first tests. |
| Demand/Supply | SOURCE_RULE: DOC18 P5–12 and both diagrams | Last opposite move, old liquidity raid, untested zone. Demand LONG Discount, Supply SHORT Premium. Inclusive wick touch is declared freshness interpretation. |
| Breaker | SOURCE_RULE: DOC19 P115–117/image17–18; DOC20 P105–106 | Previously qualified OB broken impulsively with IMB and structural change; sweep provenance, opposite return, stop behind breaking impulse/raid. |
| STB/BTS/manipulation | SOURCE_RULE: DOC03 P70–74, DOC19 glossary and AMD P169 | Raid, full absorption, directional structural confirmation, then mitigation. No entry on manipulation alone. Same zone may have several semantic aliases; never count aliases as independent setups. |
| FVG/IMB | SOURCE_RULE: DOC16 P52–60; DOC19 P113 | Three-candle wick gap; supporting POI, not automatic standalone permission. |
| Order Flow | Secondary summary section7; DOC03 P28–33/P71–72 supplies causal sequence, DOC19 glossary P26 | SOURCE_INTERPRETATION: active directional structure + raid/absorption + untested opposing destination POI; invalid on structure break, destination test or raid-extreme body violation. Store timestamps/prices/IDs, not caller booleans. Missing SW22 limits source certification. |
| P/D and OTE | SOURCE_RULE: DOC19 P139–156/images24–26; DOC18 P12 | EQ=.5; LONG Discount, SHORT Premium for D/S and selected conservative path. OTE .705–.79 is confluence only; not a required entry trigger or outcome-fit filter. |
| Range | SOURCE_RULE: DOC06 P37–75 and P119–129; DOC19 P124–131 | Impulse→ordered boundaries→midpoint reaction→clean interior→external deviation→return→LTF confirmation→retest. Retained BOS impulse proxy and midpoint tolerance .08 are RESEARCH_PARAMETER, not literal source definitions. Ambiguous geometry rejected. |
| FTA | DOC19 glossary; secondary summary section9 | SOURCE_INTERPRETATION: nearest available opposing qualified POI near edge, never mandatory three gaps. Full exit at this FTA for non-Range: chosen machine convention, no claimed source percentage. |
| Exits | SOURCE_RULE: DOC06 P119–121 = 80% inside opposite Range edge, optional20% breakout | SOURCE_EXIT_POLICY: Range80/20 only with a pre-entry external destination for20%; otherwise optional remainder also closes at edge. Earlier opposing FTA prevents forcing through trouble. Original technical SL throughout; no automatic BE. |
| Risk | SOURCE_RULE: DOC20 P39–45 low risk1–2%; primary SW11 unavailable | PROJECT_OVERLAY: fixed2% of current equity maximum including base entry/SL friction. Initial1170 USDT. No 3–5%, risk fitting or live leverage. Gap losses can exceed planned risk. |
| Costs | PROJECT_OVERLAY | Retain existing base fee/slippage assumptions, recorded separately; funding unavailable, not fabricated. |

## Registered sample and implementation scope

Use every retained native BYBIT CSV, all10 symbols and all4 TFs. All6 existing
mappings remain evaluated (15/5,60/5,60/15,240/5,240/15,240/60); 60m execution is
an explicitly labelled any-TF interpretation, outside secondary conservative
1–15m preference. No new periods/symbols selected using outcomes. This is already
inspected DEVELOPMENT history, not OOS. Prefix causality is tested.

One sequential virtual account, at most one open position/pending order across
all symbols/mappings, uses real5m candles for execution. Deterministic ties:
ready timestamp, higher HTF, lower LTF, fixed original symbol priority, signal ID.
First50 actual closures are the primary descriptive sample; continue the full
dataset for coverage and the total funnel. Never pool overlapping historical
portfolios. Open endpoint positions remain censored, not forced to close.

Conservative implemented entry: qualified HTF POI interaction and raid context,
then LTF reaction raid→BOS→new structure/CONF→new fresh POI limit. One setup per
HTF reaction/direction/mapping, no alias duplicates. Evidence absent means WAIT.
Old risk/exit/replay classes and frozen artifacts retain their bytes. This additive
engine is a reproducible interpretation of the supplied sources, not certification
that a numerical detector captures every discretionary qualitative source case.
No assertion of high win rate or exact discretionary maximum is warranted.

The code audit identifies the legacy automatic research subset: gap-only HTF POI,
three opposing gap targets, numeric body/engulf thresholds, missing causal OF and
adverse-liquidity context, global40/30/30 and TP1 BE. The new engine provides typed
zones, event evidence and independent source exits. The legacy frozen model stays
available solely as labelled historical research.
