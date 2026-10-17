# PURE SOURCE — authoritative current status

**Status date:** 2026-10-17  
**Current rebuild stage:** Stage 17 — Non-ranked SOURCE Branch Registry  
**Base:** Stage 16 merge `f206e6938fe78adb7290ba3264c6d19c2ababf9b`

> This file is the current continuation entrypoint for PURE SOURCE strategy work.
> Historical `README.md`, `CONTINUATION_STATUS.md`, old Bybit replays, source-permitted physical cases and earlier PnL reports remain preserved evidence, but they are **not SOURCE truth** and must not be used to resolve current SOURCE ambiguity.

## Current verdict

The PURE SOURCE baseline is **`NOT_IDENTIFIABLE`** as one unique executable financial strategy.

This is intentional and fail-closed:

- `trade_entry_allowed=false`;
- no financial PURE SOURCE backtest is authorized yet;
- no PAPER/LIVE/private exchange API/orders;
- no PROJECT overlays in SOURCE baseline;
- historical PnL must not choose among SOURCE-permitted alternatives.

Stage 15 established deterministic diagnostic end-to-end replay and exact repeated-artifact verification. Stage 16 froze the identifiability frontier and priority-1 Methodichka evidence. Stage 17 gives finite, explicit SOURCE alternatives stable branch identities **without selecting or ranking them**.

## What is already causally implemented

The rebuild has a deterministic closed-candle causal core for market structure and typed evidence transport, including structural SFP and IMB/FVG evidence, setup transport, execution-semantics transport, prefix/future-mutation QA and diagnostic replay fingerprints.

`OBJECT VALIDITY != TRADE ELIGIBILITY` remains a hard invariant.

Stage 17 adds another explicit boundary:

`EXACT SOURCE ALTERNATIVE != TRADE ELIGIBILITY`.

An exact branch such as STB/BTS midpoint 0.5, full FTA fixation, or ATR 14 is only exact **conditional on its required causal parent evidence**. Exactness does not make that branch preferred, profitable, or executable.

## Source details confirmed from the priority-1 Methodichka

The extracted `19.clean.txt` is tied by the frozen archive manifest to `Криптология/Методичка.docx`, so it outranks SW modules when reconstructing the rules.

It confirms several pieces that are more specific than the previous generic frontier:

- OB: last candle before imbalance; the movement must update structure; the OB swept a low/high or wick; body should be large and wicks small. The exact numeric meaning of “large/small” is still not supplied.
- Breaker: an impulsively pierced OB that swept a high/low, is pierced by imbalance and is followed by CHOCH.
- Range: no structure inside; first high after the impulse and first low define the range; reaction from 0.5 validates it; the described setup trades after deviation, return, zone test and CHOCH. The remaining machine problem is source-qualified impulse/reaction provenance, not inventing a new range midpoint.
- OTE: source levels include 0.5 / 0.62 / 0.705 / 0.79, and OTE is explicitly 0.705–0.79. The remaining problem is causal selection of the correct source-qualified impulse/anchors.
- SFP: original pattern is three candles, may have a fourth confirmation candle, applies on all timeframes and requires liquidity context to be swept.

These findings narrow the frontier but do **not** yet make a unique executable financial baseline.

## Stage 17 branch registry

Finite explicit alternatives are now represented separately instead of being collapsed into one generic unresolved choice. Current registered families are:

- `OB_DIRECT_ENTRY`: exact boundary vs under-specified inside-zone quote;
- `OB_EXECUTION_PATH`: direct path vs LTF BOS + new-POI path;
- `OB_STOP_ANCHOR`: beyond OB extreme vs beyond engulfing-candle wick;
- `BREAKER_STOP_ANCHOR`: aggressive vs conservative anchor;
- `STB_BTS_ENTRY`: directional zone part vs exact 0.5 midpoint;
- `FTA_FIXATION`: full 100% fixation vs under-specified partial fixation;
- `SFP_ATR_PERIOD`: standard 14 vs strategy-adjusted period family.

The registry rejects ranking/outcome fields such as `rank`, `score`, `preferred`, `win_rate`, `profit_factor`, `expectancy`, `pnl`, and `backtest_result`. It also rejects PROJECT policies, financial-backtest permission and `trade_entry_allowed=true`.

Machine-readable branch registry: `config/pure_source_branch_registry_v2.json`.
Typed contract: `src/crypto_bot/strategy/pure_source_branch_registry_v2.py`.
Detailed Stage 17 record: `docs/PURE_SOURCE_ENGINE_STAGE17_BRANCH_REGISTRY.md`.

## Current blocking frontier

### 1. Qualitative SOURCE provenance still missing for automatic detection

The machine must not invent numeric proxies for source concepts whose original definition remains qualitative. Current examples include:

- EQH/EQL source-qualified substructure / reasonable tilt;
- OB large-body/small-wick, liquidity-sweep, imbalance and context provenance;
- Breaker provenance from a source-valid OB, imbalance pierce and CHOCH;
- Range source-qualified preceding impulse segmentation and midpoint-reaction provenance;
- STB/BTS manipulation segmentation and full-engulf provenance;
- Demand/Supply last-movement segmentation;
- OTE / Premium-Discount source-qualified impulse/dealing-range anchors, while OTE ratios themselves are source-defined;
- meaningful / adverse liquidity context.

Until these have source-backed causal provenance, they stay `UNKNOWN`, not `FAIL` and not guessed `PASS`.

### 2. Exact geometry / lifecycle remains unspecified in places

Examples include exact quote inside an OB/new POI, exact buffer for a stop described only as “behind/beyond”, some protective stops, partial-FTA fraction, destination of the remaining position and re-entry identity/eligibility.

Stage 17 now preserves these as properties of specific alternatives instead of forcing one common selection. They remain `UNRESOLVED` unless an original source defines them or a bounded source-supported branch can be represented without adding a new trading rule.

### 3. Context selection remains unresolved

Where several source-valid timeframes, liquidity pools or identities coexist, no PROJECT ranking/filter may choose among them. Re-entry identity/eligibility also remains unresolved where SOURCE does not define it precisely.

## Source authority

Use this order only:

1. Методичка
2. SW5
3. SW9
4. SW11
5. SW12
6. SW22
7. other confirmed ORIGINAL SOURCE materials
8. SOURCE Rule Registry

Repository code is infrastructure / historical evidence, not SOURCE truth.

The frozen manifest confirms verified provenance for the original source set. Raw SW5/SW9/SW11/SW12/SW22 PDFs and extracted text are retained under `data/source_materials/primary_pdf_2026_10_09/`; the archive-extracted Methodichka text is retained as `data/source_materials/cryptology_2026_10_09/19.clean.txt` with manifest linkage to the verified DOCX hash.

## Next permitted work

The next safe step is to build **causal qualitative evidence / annotation contracts** for source concepts that are genuinely qualitative, rather than replacing them with arbitrary numeric thresholds. The Stage 17 branch registry can then consume only source-valid parent evidence and keep alternatives non-ranked.

A financial PURE SOURCE backtest remains blocked until required object provenance, execution geometry and exit lifecycle are sufficiently identified.

Machine-readable frontier: `config/pure_source_identifiability_frontier_v2.json`.
Stage 16 record: `docs/PURE_SOURCE_ENGINE_STAGE16_IDENTIFIABILITY_FRONTIER.md`.
Stage 17 record: `docs/PURE_SOURCE_ENGINE_STAGE17_BRANCH_REGISTRY.md`.
