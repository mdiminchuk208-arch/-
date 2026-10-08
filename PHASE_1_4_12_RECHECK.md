# Phase 1.4.12 v0.4.12 recheck

## Source and rule classification

The Source Rule Registry was read before implementation. The source rules remain the definitions of HH/HL, LL/LH, BOS, SFP and the qualitative range sequence. Same-direction post-BOS recovery, chronological machine ordering, causal pattern-extreme storage, range midpoint tolerance and wait/cluster grids are explicitly marked `TECHNICAL_NORMALIZATION` or `BACKTEST_PARAMETER`; none is promoted to a trading rule.

The registry is valid JSON with unique rule IDs. New entries cover mode isolation, recovery lineage and ablation accounting.

## Recovery ablation

Each input series was independently analyzed in both modes:

- `SOURCE_CONSERVATIVE`: same-direction post-BOS recovery is rejected and recorded as a diagnostic reason.
- `TECHNICAL_RECOVERY`: the v0.4.11 local recovery fallback is retained for counterfactual comparison.

The runner compares BOS source-only versus recovery, Range candidates, validated ranges, Range SFP, SFP→BOS, pair opportunities and global opportunities. Semantic keys avoid false differences caused by per-run ordinal IDs. Recovery transition IDs are carried into descendants and shown in CSV/JSON output. Affected contexts cannot unlock source entry search; all trade flags remain false.

## Causality checks

- Only closed, strictly chronological candles are accepted.
- BOS is evaluated before a swing confirmed by the same right-hand candle can be used.
- SFP invalidation uses a later body close beyond the already-known sweep-candle extreme.
- Range validation and boundary sweeps use only events after the second boundary or midpoint confirmation as appropriate; pre-validation raids consume boundary liquidity without retroactive SFP formation.
- No recovery timeout, numeric impulse-strength rule, numeric boundary-clarity rule or profitability threshold was added.
- Full-history versus trailing 60-day suffix BOS checks are exact (`Jaccard=1.000`) for BTCUSDT and ETHUSDT on 5m, 15m, 60m and 240m in both modes.

## Real-data run

The final run used public Bybit CSV data under `data/history/bybit`:

| Symbol | 5m rows | 15m rows | 60m rows | 240m rows | Span | QA |
|---|---:|---:|---:|---:|---|---|
| BTCUSDT | 69,119 | 23,039 | 5,759 | 1,439 | ≈240 days | clean |
| ETHUSDT | 69,119 | 23,039 | 5,760 | 1,439 | ≈240 days | clean |

The evaluation window was 240 days. Tolerance, wait and clustering grids were all completed; both symbol summaries report `checks_passed=true`. The selected metric slice and the complete report location are documented in [`data/reports/phase1_4_12/final_240d/ABLATION_SUMMARY.md`](data/reports/phase1_4_12/final_240d/ABLATION_SUMMARY.md).

The runner validates that loaded history covers the requested evaluation window; the 240-day run therefore uses the same explicit value for both the guard and the evaluation slice.

## Regression and correction log

The first post-optimization test run exposed stale `episode_indices`/level indexes (`KeyError`) in an intermediate patch. The index synchronization was corrected before the final run. The final full suite passed with 189 tests, and the 5m/15m/60m/240m real-data run completed without analysis errors.

The final review also corrected global JSON mode provenance and excluded the mode label from semantic behavior comparisons, preventing metadata alone from inflating changed-object counts. The input-span guard now follows `--evaluation-days`; an end-to-end CLI regression accepts a fully covered one-day fixture and rejects that same history for two-day and 240-day requests. All production changes were included in the final BTC/ETH grid. The later test-only addition leaves all 30 recorded code hashes unchanged.

The optimized analyzer preserves the v0.4.11 semantic fingerprint on direct BTCUSDT and ETHUSDT 15m, 60m and 240m comparisons (and on the existing deterministic fixtures); the reproducible evidence is [`data/reports/phase1_4_12/v0_4_11_fingerprint_comparison.json`](data/reports/phase1_4_12/v0_4_11_fingerprint_comparison.json). Only explicit recovery ancestry and mode metadata are new output fields in those semantic comparisons. The full 5m v0.4.11 baseline is not repeated because its unoptimized O(n²) scan is prohibitively slow.

## Gate status

The obsolete `STRUCTURE_LIFECYCLE_REAL_DATA_NOT_REVALIDATED` blocker is absent from runtime blockers. `STRUCTURE_RECOVERY_ABLATION_NOT_VALIDATED` remains an explicit Entry Engine gate together with the still-unimplemented Range clarity/lifecycle, global clustering and Entry Zone/SL/FTA/TP/RR gates. Entry Engine and real trade execution remain disabled pending a later phase.

## QA checklist

- Full unittest: **189 tests OK**.
- Global opportunity CSV and summary now carry the explicit `analysis_mode`; mixed modes remain rejected before clustering.
- `python -B -m compileall -q src scripts tests`: OK.
- Phase 1.4.12 CLI help: OK.
- Public-data input identity and QA: OK for both symbols and all four intervals.
- Two-mode ablation and complete grid: OK.
- No live API keys or real entries used.
