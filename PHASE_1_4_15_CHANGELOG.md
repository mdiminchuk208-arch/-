# Phase 1.4.15 v0.4.15 — Cross-Asset Freeze + Range Lifecycle Scope

## Goal

Freeze the successfully completed Phase 1.4.14 ten-symbol cross-asset QA evidence without changing trading logic, and narrow the remaining Range lifecycle blocker to the part that is actually unresolved by source material.

## Cross-asset gate

The project-level `CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED` blocker is closed from retained real-data evidence on the required ten-symbol basket:

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

Frozen validation configuration:

- production mode: `SOURCE_CONSERVATIVE`;
- evaluation days: `240`;
- suffix days: `60`;
- stabilization days: `30`;
- analysis warm-up days: `0`;
- required 5m/15m/60m/240m input QA;
- exact suffix BOS reproducibility;
- recovery-free production ancestry;
- MTF runtime safety;
- `trade_entry_allowed=false` for every generated candidate/opportunity.

No BOS/SFP/opportunity count or profitability metric was used to close the gate.

## Cross-asset harness defaults

`analyze_cross_asset_robustness.py` now defaults to the validation-frozen `240 / 60 / 30 / 0` configuration and writes to a Phase 1.4.15 report root by default.

## Range lifecycle clarification

Phase 1.4.15 does **not** invent a permanent range retirement rule.

The already implemented conservative boundary-liquidity lifecycle is frozen and regression-tested:

- established boundary starts `ACTIVE`;
- first strict raid changes the original boundary liquidity to `CONSUMED`;
- a later return inside the prior range does not restore that same boundary to `ACTIVE`;
- later raids cannot reuse the consumed original boundary for another range-boundary SFP;
- an already formed SFP keeps its independent invalidation lifecycle.

This resolves the reactivation/re-use ambiguity only.

The previous broad blocker:

`RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED`

is narrowed to:

`RANGE_RETIREMENT_REDRAW_LIFECYCLE_NOT_FORMALIZED`

because source material still does not provide a complete objective machine rule for permanent range retirement/redraw after exits. Entry Engine remains blocked on that unresolved part.

## Remaining Entry Engine blockers

- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`
- `RANGE_RETIREMENT_REDRAW_LIFECYCLE_NOT_FORMALIZED`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

## Safety

- `trade_entry_allowed=false` remains unchanged.
- No order placement, paper execution or live execution was added.
- No symbol-specific exception was introduced.
- No numeric boundary-clarity threshold was invented.
- No range retirement rule was invented.

## Version

- Package: `0.4.15`
- Source Rule Registry: `phase1.4.15-0.4.15`
