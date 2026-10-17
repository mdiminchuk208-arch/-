# PURE SOURCE Engine — Stage 16: Identifiability Frontier

Base merge: `b570018371eff6fac34088038091f6b8aff41ea1` (Stage 15).

Stage 16 does not add a trading rule. It freezes the current **identifiability frontier** so later work cannot silently convert source ambiguity into a backtest parameter or PROJECT policy.

## Why this stage exists

Stages 1–15 established a causal, deterministic transport from closed candles through structure/evidence/setup/execution diagnostics. Stage 15 can fingerprint an exact replay and repeat it deterministically, but reproducibility alone does not make an under-specified discretionary source into one unique executable strategy.

The current source material contains two fundamentally different kinds of gaps:

1. **qualitative concepts whose machine provenance is not yet source-defined**; and
2. **explicitly source-permitted alternatives for which the source gives no unique precedence**.

Those categories must not be collapsed. A qualitative missing definition cannot be replaced by a guessed threshold. A finite source-permitted alternative can be enumerated as a branch, but it cannot be ranked or selected using outcome data.

## Primary frozen evidence reviewed for this frontier

The frozen source manifest records verified provenance for the original material. It retains raw SW5/SW9/SW11/SW12/SW22 PDFs under `data/source_materials/primary_pdf_2026_10_09/` together with extracted text. The archive manifest also ties `Криптология/Методичка.docx` to verified SHA-256 `032a314046cc5dba220f698da567387e9f0dd30b35e4ff1add6328ea41e4e9d1`; its extracted text is `data/source_materials/cryptology_2026_10_09/19.clean.txt`.

Because Методичка is source priority #1, its rule-level evidence is evaluated before SW modules.

### Методичка — priority-1 clarifications

Paragraphs P0102-P0108 define OB more specifically than the previous generic gap label:

- OB is the last candle before imbalance / sharp impulse;
- the movement must update a structural point (CHOCH or trend continuation high/low);
- the OB swept a low/high or wick;
- the OB body should be large while the wicks are small.

The first three conditions are structurally meaningful. “Large body / small wicks” remains qualitative because no numeric ratio is supplied. Stage 16 therefore narrows the missing provenance instead of inventing a candle threshold.

Paragraphs P0113-P0116 define Breaker as an impulsively pierced OB that swept a high/low, is pierced by imbalance and is followed by CHOCH. The remaining machine task is causal provenance from a source-valid OB and the relevant imbalance/CHOCH, not an arbitrary “breaker score”.

Paragraphs P0122-P0130 substantially narrow Range semantics:

- there should be no structure inside the range;
- the range is built from the first high after the impulse and the first low;
- reaction from 0.5 is required to validate the figure;
- the described trade setup follows deviation, return into the range, test of the zone that sent price back, and CHOCH.

Therefore range endpoints and midpoint are not free parameters. The remaining ambiguity is causal/source-qualified impulse segmentation, reaction provenance and any execution geometry not specified by the source.

Paragraphs P0139-P0156 define Fibonacci levels 0.5, 0.62, 0.705 and 0.79 and explicitly define OTE as the 0.705-0.79 price zone. The unresolved part is not the OTE ratio: it is selecting the correct source-qualified impulse/dealing-range anchors causally.

Paragraphs P0157-P0162 define SFP as originally a three-candle reversal pattern, optionally followed by a fourth candle confirming direction; it is applicable on all timeframes and requires context in the form of points/zones whose liquidity is being swept. This reinforces the distinction between structural SFP validity and trade eligibility/context.

### SW5 — structure

SW5 defines swing structure, HH/HL/LH/LL, BOS and CONF. A swing is a three-candle structural point; BOS requires break plus candle-body acceptance/close beyond the relevant structural level; CONF is renewal/confirmation of the new structure. This belongs to the already implemented causal core.

### SW9 — OB / Breaker / POI / FTA

The source states, among other things:

- an OB must satisfy formation/context conditions, including liquidity work, an aggressive engulfing impulse, structural confirmation and HTF POI context;
- direct OB work permits a limit on the zone boundary and also permits a limit inside the OB;
- a second, more conservative OB variant waits for lower-timeframe structure break and formation of a new POI before placing a limit on that new POI;
- OB stops have more than one source-permitted anchor;
- Breaker work permits aggressive and conservative stops;
- FTA is the first trouble area and may be used for full or partial profit fixation.

The text therefore supports branch enumeration for some execution alternatives, but it does not define one unique precedence or all exact numeric geometry.

### SW11 — risk material

SW11 is retained as SOURCE material, including risk-management guidance. Stage 16 does not inject PROJECT portfolio rules into PURE SOURCE and does not use risk guidance to manufacture missing market-object or execution semantics.

### SW12 — ATR

SW12 describes ATR, states that the standard value is 14 and explicitly says the setting can be changed depending on the strategy. It also explains ATR use around SFP stops and pattern invalidation.

Therefore `14` is a source-supported standard/default reference, but the source does not establish that every valid strategy instance must use 14. Historical performance must not be used inside PURE SOURCE reconstruction to decide the winning ATR period.

### SW22 — STB/BTS

SW22 requires trend alignment, liquidity sweep/manipulation, full engulf and BOS/CONF context for STB/BTS use. It permits entry using the directional part of the STB/BTS zone or exact 0.5. Again, this is an explicit source family, not a unique precedence rule.

## Blocker classes

### A. `MISSING_SOURCE_QUALITATIVE_PROVENANCE`

These are objects/context whose source definition still contains qualitative semantics that are not safely reducible to deterministic OHLC rules without additional source evidence or explicit causal annotation:

- EQH/EQL qualified substructure / reasonable tilt;
- OB large-body/small-wick, liquidity-sweep, imbalance and context provenance;
- Breaker provenance from a source-valid OB, imbalance pierce and CHOCH;
- Range source-qualified preceding-impulse segmentation and midpoint-reaction provenance;
- STB/BTS segmentation and full-engulf provenance;
- Demand/Supply last-movement segmentation;
- OTE / Premium-Discount qualified impulse/dealing-range anchors, while the OTE ratios themselves are source-defined;
- meaningful / adverse liquidity context.

**Allowed resolution:** extract more rule-level source evidence, or define a strictly causal human/source annotation contract with provenance and timestamps.

**Forbidden resolution:** arbitrary candle fractions, ATR thresholds, percentages, ticks, scores, ML labels or profitability filters masquerading as SOURCE.

### B. `SOURCE_PERMITTED_VARIANTS_NO_PRECEDENCE`

The source itself permits multiple choices without selecting one universal winner.

Current examples:

- OB boundary vs inside-zone direct entry;
- OB direct vs LTF-confirmed new-POI entry path;
- alternate OB stop anchors;
- aggressive vs conservative Breaker stop;
- STB/BTS directional-zone-part vs exact 0.5 entry;
- full vs partial FTA fixation;
- ATR standard 14 vs strategy-adjusted setting.

**Allowed resolution:** enumerate distinct SOURCE branches with stable IDs and identical causal evidence inputs.

**Forbidden resolution:** select a branch because it has the best WR/PF/PnL/expectancy or because a PROJECT score prefers it.

### C. `SOURCE_GEOMETRY_UNSPECIFIED`

The source sometimes names a zone or relative placement without supplying one exact numeric coordinate needed by a deterministic fill engine.

Examples include exact quote inside an OB/new POI, exact “behind/beyond” stop buffer and protective-stop geometry for patterns where the current frozen material does not define it.

These remain `UNRESOLVED` unless an exact source anchor or an honestly bounded source-supported branch is found. Source-defined coordinates such as Range 0.5 or OTE 0.705-0.79 must not be relabelled as arbitrary technical choices.

### D. `SOURCE_EXIT_ALLOCATION_UNSPECIFIED`

Examples:

- fraction when FTA fixation is partial;
- destination/termination of the remainder after partial FTA;
- destination/termination of the remaining 20% after the source Range 80% fixation case.

PROJECT TP 40/30/30 and project breakeven are not valid gap-fillers.

### E. `SOURCE_CONTEXT_OR_IDENTITY_UNSPECIFIED`

Examples include timeframe/context selection where multiple source-valid choices exist, selection among multiple meaningful liquidity pools and precise re-entry identity/eligibility.

Methodichka explicitly says SFP is applicable on all timeframes; this establishes validity scope, but it still does not supply one mandatory trading-timeframe precedence for every setup.

## Consequence for backtesting

A **single unique financial PURE SOURCE baseline is not yet identifiable**. That statement is stronger and more precise than saying the implementation is merely unfinished.

What is allowed now:

1. continue causal object/provider reconstruction from original evidence;
2. implement source-defined geometry such as Range 0.5 and OTE 0.705-0.79 only when their source-qualified anchors/objects are causally known;
3. enumerate finite explicit source branches without ranking them;
4. build annotation/provenance contracts for genuinely qualitative concepts;
5. run non-financial diagnostic replay and causality QA;
6. when branch geometry becomes executable, test branches independently without using the results to rewrite SOURCE.

What is not allowed now:

- claim PURE SOURCE edge from historical PnL;
- promote an old Bybit/source-permitted research run to current baseline;
- optimize unresolved SOURCE choices on historical outcomes;
- invent numeric body/wick, impulse, liquidity or geometry thresholds because the source is qualitative;
- apply Anti-Scalp, edge/cost filters, project HTF filters, scoring/ranking, portfolio risk, TP 40/30/30 or project breakeven inside PURE SOURCE;
- permit PAPER/LIVE/private exchange execution.

## Historical-results boundary

`README.md`, `CONTINUATION_STATUS.md`, old source-permitted Bybit reports and prior research engines contain valuable historical evidence. They are preserved, but their performance numbers and machine interpretations predate or sit outside the current PURE SOURCE rebuild. They must not be treated as authority for resolving Stage 16 blockers.

The current continuation entrypoint is `PURE_SOURCE_CURRENT_STATUS.md`.

## Machine-readable contract

See `config/pure_source_identifiability_frontier_v2.json`.

Required safety flags remain:

- `baseline_identifiability = NOT_IDENTIFIABLE`
- `trade_entry_allowed = false`
- `financial_backtest_allowed = false`
- `paper_allowed = false`
- `live_allowed = false`
- `private_api_allowed = false`

No SOURCE rule is added by Stage 16. Stage 16 only records source evidence and the current implementation/identifiability boundary.
