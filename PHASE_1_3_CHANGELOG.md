# Phase 1.3 — 0.3.0 changelog

## Added

- `crypto_bot.strategy.market_analysis`
  - causal structural swing levels;
  - HH/HL and LL/LH structure recognition;
  - protected HL/LH tracking;
  - BOS by candle close through the protected point;
  - structural liquidity take events;
  - structural-liquidity SFP events;
  - explicit OB auto-validation readiness gate.
- `crypto_bot.analysis_report`
  - deterministic `events.csv`;
  - deterministic `summary.json`.
- `scripts/analyze_bybit_history.py`
  - reads Phase-1.2 CSV history;
  - re-runs Data QA before strategy analysis;
  - prints event counts and last detected events;
  - writes machine-readable reports.
- source rules/normalizations for trend, contextual BOS, structural liquidity, protected-point selection and strict liquidity takes.
- real-market structure tests and source-linked BOS fixture.

## Important correction found during implementation

An early draft of the Phase-1.3 analyzer treated a close above the most recent swing high / below the most recent swing low as a generic BOS. That was rejected before release after re-reading the uploaded structure materials.

The released 0.3.0 instead models BOS in the context of the active structure:

- break of protected HL invalidates bullish structure;
- break of protected LH invalidates bearish structure.

The exact machine rule used to select the protected HL/LH is explicitly stored as `TECHNICAL_NORMALIZATION`, not misrepresented as verbatim source logic.

## QA

- 54 unit/source-conformance tests pass.
- `compileall` passes.
- deterministic synthetic CLI smoke test passes.
- no live/private trading endpoint exists in this phase.


# Phase 1.3 — 0.3.1 recheck

This recheck fixes issues found after comparing the implemented logic again with the uploaded source materials and the current Bybit public API schema.

- Fixed post-BOS CONF causality: pre-BOS swings cannot confirm the new trend.
- Added dedicated bullish/bearish CONF events and post-BOS state.
- Changed OB-without-IMB from trade-eligible to `IMB_UNRESOLVED` because the source wording is not unambiguous enough to hard-code IMB as optional.
- Added Bybit response identity validation and `symbolType` parsing.
- Added non-finite/negative market data guards and non-finite risk guards.
- Synchronized package version and User-Agent to 0.3.1.
- Data QA rejects mixed series metadata; strategy timestamps must be timezone-aware.
- Added causal-prefix no-lookahead regression coverage.
- Final recheck suite: 64/64 tests pass; compileall and source-rules JSON validation pass.
