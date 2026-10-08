# Phase 1.4.13 v0.4.13 — Validation Freeze / Pre-Entry Gate

## Goal
Freeze the source-aligned production policies that are already supported by the Phase 1.4.12 evidence, without pretending the remaining Range and Entry gaps are solved.

## Frozen decisions
1. **Production analysis mode:** `SOURCE_CONSERVATIVE`.
   - Same-direction post-BOS recovery remains available only as `TECHNICAL_RECOVERY` diagnostic/counterfactual QA.
   - The default `analyze_market(...)` mode is now `SOURCE_CONSERVATIVE`.
   - Recovery ancestry never grants source entry-search eligibility.
2. **Production global cross-pair clustering:** exact timestamp only (`0` minutes).
   - Positive near-time windows (`15`, `60`, etc.) remain `BACKTEST_PARAMETER` experiments.
   - Opposite directions never merge and distinct opportunities from the same HTF/LTF pair never collapse.
3. The v0.4.12 recovery-ablation and global-clustering freeze blockers are removed from runtime Entry Engine blockers.

## New explicit pre-entry QA gate
`CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED` is added because the packaged real-data validation currently covers BTCUSDT and ETHUSDT only. This is a project QA gate, not a source trading rule.

Recommended robustness basket before Entry Engine freeze:
`BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT, DOGEUSDT, ADAUSDT, LINKUSDT, AVAXUSDT, LTCUSDT`.

## Blockers intentionally still open
- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`
- `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED`
- `CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

## Why Range blockers remain open
The uploaded source registry preserves two simultaneous source statements: materially smeared/ambiguous boundaries should be skipped, while perfectly crisp boundaries are not required if price still trades in a defined area. No objective numeric clarity threshold is supplied. The source also does not fully formalize permanent Range retirement/redraw or liquidity renewal after exit/re-entry. Phase 1.4.13 does not invent either rule.

## Safety
`trade_entry_allowed=false` remains unchanged. No Entry Engine, order execution, private exchange endpoint or profitability claim is introduced.

## Version
- Package: `0.4.13`
- Source Rule Registry: `phase1.4.13-0.4.13`
