# Phase 1.3.2 — Liquidity/SFP cleanup

## Source recheck correction

A previous interpretation risked filtering three-candle swings as if only some of them could be structural liquidity. The source recheck does **not** support that shortcut:

- Advanced Market Structure defines a Swing as a structural point.
- Liquidity material places external liquidity at structural highs/lows of the relevant timeframe.
- SFP material says SFP can form at structural highs/lows on any timeframe, while H1+ is the preferred search timeframe.

Therefore v0.3.2 does **not** invent a "significant swing" filter.

## Implemented

- Structural-liquidity lifecycle: `ACTIVE -> SWEPT -> CONSUMED`.
- Same candle + same side raw liquidity takes are grouped into one `LiquiditySweepEpisode`.
- Raw per-level `HIGH_LIQUIDITY_TAKEN` / `LOW_LIQUIDITY_TAKEN` events remain intact for auditability.
- At most one SFP **formation** event is emitted per sweep episode.
- If several member levels satisfy SFP, the outermost valid level is the deterministic representative:
  - highest valid level for a high-side sweep;
  - lowest valid level for a low-side sweep.
- SFP event names now explicitly say `FORMATION` to avoid treating the pattern itself as an entry signal.
- The analyzer records whether the analyzed timeframe is source-preferred for SFP search:
  - `SOURCE_PREFERRED_H1_PLUS` for H1+;
  - `SOURCE_VALID_BELOW_PREFERRED_H1` below H1.
- M1 SFP formation remains source-valid, but the CLI warns that H1+ is preferred and LTF BOS is still required after SFP formation.
- Added `sweep_episodes.csv` alongside `events.csv` and `summary.json`.
- Source Rule Registry bumped to `phase1.3-0.3.2`.
- Package and Bybit User-Agent bumped to `0.3.2`.

## Not implemented / deliberately not invented

- No arbitrary ATR/percentage price-distance clustering threshold.
- No arbitrary "important swing" filter.
- No SFP trade entry: LTF BOS confirmation is still not implemented in the SFP pipeline.
- OB autovalidation remains `BLOCKED_PENDING_CONTEXT`.

## QA

- 69/69 unit tests pass.
- `compileall` passes.
- Source Rule Registry JSON validates and has unique IDs.
