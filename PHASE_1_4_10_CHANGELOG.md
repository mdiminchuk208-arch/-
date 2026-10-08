# Phase 1.4.10 v0.4.10 changelog

## Why this phase exists
The v0.4.9 real 240-day run restored many M15 BOS events, but M5 still spent ~99% of loaded candles in software state `BROKEN`, including multi-month runs. That showed the expected-opposite transition normalization could still fail permanently after a BOS.

## Changes
- Kept source-expected post-BOS opposite structure as priority fast path.
- Added strictly post-BOS local structure fallback (`HH+HL` / `LL+LH`) with no pre-BOS swing reuse.
- Same-direction recovery is explicitly labeled `TECHNICAL_NORMALIZATION`, not a source rule.
- Added `StructureTransitionDiagnostic` and CSV export with rejection/resolution reasons.
- Added unresolved end-of-data transition reporting.
- Added `scripts/audit_structure_lifecycle.py` for full-history vs recent-suffix BOS diagnostics.
- Added BOS suffix-stability metrics with an explicit stabilization guard and no hard-coded pass threshold.
- Fixed report root from stale `phase1_4_8` to `phase1_4_10`.
- Added explicit Entry blocker `STRUCTURE_LIFECYCLE_REAL_DATA_NOT_REVALIDATED`.
- Version synchronized to 0.4.10; Source Rule Registry version updated to `phase1.4.10-0.4.10`.
