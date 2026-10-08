# Phase 1.4.7 v0.4.7 recheck

## Source recheck
Compared the Range Engine assumptions against both uploaded range sources.

Preserved separately:
- dedicated range module: materially smeared/ambiguous boundaries that make future movement difficult should be skipped;
- general methodology: a range may lack perfectly crisp boundaries if the instrument still trades in a defined area.

Conclusion: there is no source-defined numeric clarity threshold. No automatic score was invented.

## Code/QA recheck
- package/version sync checked;
- Source Rule Registry JSON parsed and unique IDs checked;
- compileall passed;
- CLI help passed;
- unit tests passed;
- ZIP re-extraction and second test pass required before release.

## Remaining blockers before Entry Engine
- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`
- `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED`
- `GLOBAL_CROSS_PAIR_CLUSTER_PARAMETER_NOT_FROZEN`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

Actual trade entries remain intentionally blocked.

## Current Bybit public API recheck (2026-09-13)
Official Bybit V5 docs still support the historical-data assumptions used by this build:
- `/v5/market/kline` supports 5/15/60/240 intervals, `start`/`end`, limit up to 1000, reverse-sorted response, and unclosed-candle closePrice as last traded price;
- `/v5/market/time` still exposes `timeSecond` and `timeNano`;
- `/v5/market/instruments-info` remains the instrument-metadata endpoint.

No adapter change was required for Phase 1.4.7.
