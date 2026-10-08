# Phase 1.4.6 v0.4.6 recheck

## Source consistency
Rechecked against:
- `[SW.BAND]10. Боковое движение` pages 1-6.
- `[SW.BAND]8. Торговые инструменты (Base)` SFP section.
- `Методичка` RANGE section.

The implementation continues to distinguish source rules from technical normalizations and backtest parameters. No numeric definition was invented for a visually "clear" range.

## Causality / lookahead
- Midpoint validation only uses already-confirmed swing events.
- Pre-validation boundary raids are not retroactively converted into SFP after later midpoint validation.
- Range SFP formation still resolves at the next candle open using only that open for the source next-open condition.
- MTF BOS remains strictly post-SFP and respects invalidation/expiry/right-censoring.
- Parameter sweeps rerun the causal range augmentation for each tolerance; they do not reuse future labels to change past detections.

## Accounting safeguards
- Range candidate/episode/SFP counts are not called trade counts.
- Origin-level opportunity counts are explicitly labelled `opportunities_with_origin_context` because mixed-origin contexts may share one opportunity.
- Actual trade entries remain exactly zero.

## Integration QA
- Unit tests: 141/141 OK.
- `compileall`: OK.
- CLI `--help`: OK.
- Synthetic end-to-end CLI run: exit 0; produced range audit, per-wait funnel JSON, midpoint-tolerance matrix, MTF reports and global reports.
- Registry: 60 rules / 60 unique IDs / valid kinds.

## Entry Engine remains blocked by
- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_NOT_FORMALIZED`
- `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED`
- `GLOBAL_CROSS_PAIR_CLUSTER_PARAMETER_NOT_FROZEN`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

Phase 1.4.6 is a validation/audit phase, not permission to enter trades.
