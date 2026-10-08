# Phase 1.4.14 v0.4.14 — Cross-Asset Robustness Harness

## Goal

Turn the Phase 1.4.13 `CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED` blocker into a reproducible, explicit validation procedure without inventing any trading-quality or profitability threshold.

Phase 1.4.14 does **not** close the cross-asset gate by code alone. The gate closes only after the required real-data basket is actually present and passes the causal/safety invariants.

## Added

- `src/crypto_bot/strategy/cross_asset_validation.py`
  - canonical ten-symbol project QA basket;
  - required 5m/15m/60m/240m timeframe set;
  - per-symbol causal/safety checks;
  - deterministic gate decision that is independent of BOS/SFP/opportunity counts.
- `scripts/analyze_cross_asset_robustness.py`
  - validates Bybit CSV identity and Data QA;
  - aligns all runnable symbols to one common UTC evaluation end;
  - runs production `SOURCE_CONSERVATIVE` structure analysis;
  - checks that no recovery ancestry can appear in production mode;
  - performs stabilized full-vs-suffix BOS reproducibility checks;
  - runs structural SFP -> LTF BOS linkage on `60->5` and `240->15` with source-unbounded wait (no invented expiry);
  - verifies every MTF candidate/opportunity keeps `trade_entry_allowed=false`;
  - emits per-symbol JSON, overall JSON, input/code SHA-256 provenance and a cross-asset matrix CSV;
  - optional `--diagnostic-recovery` is counterfactual only and never affects the gate decision.

## Default project QA basket

- BTCUSDT
- ETHUSDT
- SOLUSDT
- XRPUSDT
- BNBUSDT
- DOGEUSDT
- ADAUSDT
- LINKUSDT
- AVAXUSDT
- LTCUSDT

This basket is a **TECHNICAL_NORMALIZATION / project QA policy**, not a source trading rule and not evidence of profitability.

## Pass/fail policy

The cross-asset gate uses only invariants:

1. required real-data files exist for 5m/15m/60m/240m;
2. Data QA and series identity pass;
3. requested evaluation span is covered;
4. production `SOURCE_CONSERVATIVE` contains no technical-recovery ancestry;
5. stabilized suffix BOS inventory is exactly reproducible;
6. structural SFP -> LTF BOS linkage completes without runtime errors;
7. no MTF candidate/opportunity permits a trade entry.

BOS/SFP/opportunity counts, longest `BROKEN` runs and other event inventories are written for diagnostics only. They are deliberately **not** pass/fail thresholds.

## Smoke verification in this build

The packaged archive still contains real Bybit data only for BTCUSDT and ETHUSDT. A short common-window smoke run was completed on those two symbols with:

- evaluation: 30 days;
- suffix: 20 days;
- stabilization guard: 7 days;
- analysis warm-up: 20 days.

Both BTCUSDT and ETHUSDT pass all per-symbol invariants. The overall cross-asset gate correctly remains OPEN because eight required symbols are absent.

This smoke run is infrastructure QA only and does not replace the required ten-symbol 240-day validation.

## What did not change

- Swing/BOS/CONF definitions;
- structural liquidity/SFP rules;
- Range detection/Range SFP logic;
- production mode freeze (`SOURCE_CONSERVATIVE`);
- production global cluster window (`0` minutes);
- Entry Engine status;
- real-order status.

## Remaining Entry Engine blockers

- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`
- `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED`
- `CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

## Version

- Package: `0.4.14`
- Source Rule Registry: `phase1.4.14-0.4.14`
