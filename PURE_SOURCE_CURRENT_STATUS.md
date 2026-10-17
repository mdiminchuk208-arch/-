# PURE SOURCE — authoritative current status

**Status date:** 2026-10-17  
**Current rebuild stage:** Stage 16 — Identifiability Frontier  
**Base:** Stage 15 merge `b570018371eff6fac34088038091f6b8aff41ea1`

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

Stage 15 established deterministic diagnostic end-to-end replay and exact repeated-artifact verification. It did **not** manufacture missing entry quotes, stops, ATR choices, FTA allocation, qualitative market objects, exits or re-entry rules.

## What is already causally implemented

The rebuild has a deterministic closed-candle causal core for market structure and typed evidence transport, including structural SFP and IMB/FVG evidence, setup transport, execution-semantics transport, prefix/future-mutation QA and diagnostic replay fingerprints.

`OBJECT VALIDITY != TRADE ELIGIBILITY` remains a hard invariant.

## Source details newly confirmed from the priority-1 Methodichka

The extracted `19.clean.txt` is tied by the frozen archive manifest to `Криптология/Методичка.docx`, so it outranks SW modules when reconstructing the rules.

It confirms several pieces that are more specific than the previous generic frontier:

- OB: last candle before imbalance; the movement must update structure; the OB swept a low/high or wick; body should be large and wicks small. The exact numeric meaning of “large/small” is still not supplied.
- Breaker: an impulsively pierced OB that swept a high/low, is pierced by imbalance and is followed by CHOCH.
- Range: no structure inside; first high after the impulse and first low define the range; reaction from 0.5 validates it; the described setup trades after deviation, return, zone test and CHOCH. The remaining machine problem is source-qualified impulse/reaction provenance, not inventing a new range midpoint.
- OTE: source levels include 0.5 / 0.62 / 0.705 / 0.79, and OTE is explicitly 0.705–0.79. The remaining problem is causal selection of the correct source-qualified impulse/anchors.
- SFP: original pattern is three candles, may have a fourth confirmation candle, applies on all timeframes and requires liquidity context to be swept.

These findings narrow the frontier but do **not** yet make a unique executable financial baseline.

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

### 2. SOURCE explicitly permits multiple execution variants

Frozen originals confirm that some rules are a **family of permitted branches**, not a single precedence rule:

- SW9: OB boundary limit vs inside-zone entry; direct vs LTF-confirmed new-POI variant;
- SW9: multiple OB/Breaker stop variants;
- SW9: FTA may be full or partial fixation;
- SW12: ATR 14 is the standard setting, while the source explicitly permits strategy-specific adjustment;
- SW22: STB/BTS entry may use the directional zone part or exact 0.5.

These alternatives may be **enumerated as separate SOURCE branches**, but no branch may be selected because it backtests better.

### 3. Exact geometry / lifecycle remains unspecified in places

Examples include exact quote inside an OB/new POI, exact buffer for a stop described only as “behind/beyond”, some protective stops, partial-FTA fraction, destination of the remaining position and re-entry identity/eligibility.

These remain `UNRESOLVED` unless an original source defines them or a bounded source-supported branch can be represented without adding a new trading rule.

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

Continue rule-level extraction from the frozen originals. Where the source has finite explicit alternatives, represent them as separate non-ranked branches. Where a concept is qualitative, create a causal provenance/annotation contract rather than an arbitrary threshold. Only after required object, execution and exit semantics become sufficiently identified may a financial PURE SOURCE backtest be proposed.

Machine-readable frontier: `config/pure_source_identifiability_frontier_v2.json`.

Detailed Stage 16 record: `docs/PURE_SOURCE_ENGINE_STAGE16_IDENTIFIABILITY_FRONTIER.md`.
