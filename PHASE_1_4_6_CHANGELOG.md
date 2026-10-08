# Phase 1.4.6 v0.4.6 changelog

## Goal
Validate the Phase 1.4.5 machine normalization for range detection before building Entry Engine. No trade entry is created in this phase.

## Source-aligned facts kept unchanged
- Range follows a strong directional impulse.
- The impulse end is boundary #1; the correction end is boundary #2.
- A good reaction around 0.5 supports/validates the chosen boundaries.
- Structure should be absent inside the range.
- Range boundaries are external liquidity and can be the swept level for SFP.
- The source explicitly warns that smeared/unclear range boundaries should be skipped.

## Phase 1.4.6 additions
- Separate audit funnels for `STRUCTURAL_SWING` and `RANGE_BOUNDARY` SFP contexts.
- Range-stage accounting: candidate ranges -> ever validated -> unique ranges with boundary sweeps -> unique ranges with SFP.
- MTF outcome accounting per origin: invalidated / expired / right-censored / no-BOS / BOS confirmed / opportunities-with-origin-context.
- Explicit warning that origin opportunity counts are not additive if a single opportunity contains mixed-origin contexts.
- Midpoint-tolerance validation grid. Default experiment values: `0.04 0.06 0.08 0.10 0.12`.
- `range_validation_audit.csv` with boundaries, midpoint reaction distance, lifecycle status, sweep/SFP counts and chart-review windows.
- `midpoint_tolerance_validation_matrix.csv` crossing each midpoint tolerance with each requested SFP->BOS wait scenario.
- Per-wait `funnel_wait_*.json` reports.

## Recheck findings / blockers made explicit
The source warns to skip ranges whose boundaries are smeared/unclear but does not define an objective numeric clarity test. Phase 1.4.6 therefore does **not** invent one. `RANGE_BOUNDARY_CLARITY_NOT_FORMALIZED` remains an Entry Engine blocker.

The source also describes deviations and return/acceptance logic, but does not fully define a machine lifecycle for permanent range retirement/redraw or boundary-liquidity renewal after exits/re-entry. `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED` is now explicit rather than silently assumed away.

## Parameter status
- Structural BOS as a strong-impulse proxy: `TECHNICAL_NORMALIZATION`.
- In-range BOS as internal-structure proxy: `TECHNICAL_NORMALIZATION`.
- Midpoint numeric tolerance: `BACKTEST_PARAMETER`.
- Tolerance grid itself: `BACKTEST_PARAMETER`.
- SFP wait windows and global cross-pair clustering windows remain `BACKTEST_PARAMETER`.

## Version / registry
- Package: `0.4.6`
- Source Rule Registry: `phase1.4.6-0.4.6`
- Registry rules: 60 unique IDs.
