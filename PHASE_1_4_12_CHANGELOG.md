# Phase 1.4.12 v0.4.12 changelog

## Why this phase exists

The v0.4.11 lifecycle work established stable causal structure output, but the same-direction post-BOS fallback was still mixed into one analysis path. Phase 1.4.12 makes that fallback an explicit ablation dimension and carries its provenance through the diagnostic Range and MTF layers.

## Changes

- Added `StructureAnalysisMode.SOURCE_CONSERVATIVE` and `StructureAnalysisMode.TECHNICAL_RECOVERY`.
- Kept the source-expected opposite post-BOS path in both modes; only same-direction recovery is switched by the mode.
- Added causal recovery transition IDs to structural events, Range instances, Range SFP events, MTF candidates/opportunities and global opportunity context references.
- Recovery ancestry is diagnostic and blocks source entry search for an affected context. `trade_entry_allowed` remains false everywhere.
- Replaced the obsolete `STRUCTURE_LIFECYCLE_REAL_DATA_NOT_REVALIDATED` blocker with the explicit `STRUCTURE_RECOVERY_ABLATION_NOT_VALIDATED` gate. Range, global-clustering and Entry Zone/SL/FTA/TP/RR blockers remain.
- Added semantic ablation accounting for BOS, structural/Range SFP, Range candidates, validated ranges, SFP→BOS links, pair opportunities and global opportunities. Keys use causal timestamps/prices and provenance instead of ordinal IDs; `entry_search_changed_count` is reported separately from semantic object changes.
- Added explicit `analysis_mode` to global opportunity records and comparison rows so SOURCE_CONSERVATIVE versus TECHNICAL_RECOVERY remains visible through the full diagnostic chain; the label is metadata and does not inflate semantic diff counts.
- Kept Range boundary handling causal: first strict raid consumes boundary liquidity, a boundary deviation does not by itself invalidate the range, and no numeric clarity threshold was invented.
- Added the independent runner `scripts/analyze_recovery_ablation.py` with input QA, SHA-256 manifest, 240-day evaluation, suffix-stability checks, mode comparison and complete tolerance/wait/cluster grids.
- The runner's input-span guard now follows the requested `--evaluation-days` window rather than an implicit 240-day constant.
- Added tests for both recovery directions, mode isolation, ancestry propagation, prefix immutability, range/MTF/global gates, positional compatibility, serialization and registry classification.
- Optimized internal level/episode lookups and active-liquidity scans without changing the public helper signatures or causal output ordering.
- Synchronized package, user-agent and report-root version strings to `0.4.12` / `phase1_4_12`.

## Scope boundary

Same-direction recovery remains `TECHNICAL_NORMALIZATION`, never a `SOURCE_RULE`. The recovery run is a counterfactual audit. No trade entries, exchange credentials or live execution were enabled.

## Validation

- Full unittest suite: **189 tests OK**.
- `compileall` for `src`, `scripts` and `tests`: OK.
- CLI help for the Phase 1.4.12 analysis scripts: OK.
- BTCUSDT and ETHUSDT public Bybit history: 5m/15m/60m/240m, approximately 240 days, QA clean.
- Two-mode ablation: completed for both symbols with tolerances `0.04, 0.06, 0.08, 0.10, 0.12`, waits `60, 120, 240` minutes and global cluster windows `0, 15, 60` minutes; both symbol summaries report `checks_passed=true`. The manifests identify inputs and code by SHA-256.
- Full-history versus trailing 60-day suffix BOS stability: exact `Jaccard=1.000` for every symbol, timeframe and mode.
- Technical fingerprint comparison against the unmodified v0.4.11 analyzer: exact for BTCUSDT and ETHUSDT on 15m, 60m and 240m; the reproducible spot-check is saved in [`data/reports/phase1_4_12/v0_4_11_fingerprint_comparison.json`](data/reports/phase1_4_12/v0_4_11_fingerprint_comparison.json). The full 5m v0.4.11 baseline is not repeated because its unoptimized O(n²) scan is prohibitively slow; the current 5m runs are included in the two-mode grid.

Detailed metrics and links to both complete symbol summaries are in [`data/reports/phase1_4_12/final_240d/ABLATION_SUMMARY.md`](data/reports/phase1_4_12/final_240d/ABLATION_SUMMARY.md).
