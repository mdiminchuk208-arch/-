# Phase 1.4.13 v0.4.13 — Recheck

## Baseline evidence reviewed
Phase 1.4.12 packaged public Bybit evidence for BTCUSDT and ETHUSDT, 5m/15m/60m/240m, approximately 240 days.

The packaged ablation reports state:
- input QA clean for both symbols and all four intervals;
- `checks_passed=true` for both symbol summaries;
- full-history vs trailing 60-day BOS suffix stability `Jaccard=1.000` for every symbol/timeframe/mode;
- structural SFP occurrence keys identical between `SOURCE_CONSERVATIVE` and `TECHNICAL_RECOVERY`;
- BOS/Range/MTF objects differ materially when same-direction recovery is enabled;
- every MTF/global record keeps `trade_entry_allowed=false`.

## Gate decisions

| Gate | Phase 1.4.13 status | Reason |
|---|---|---|
| `STRUCTURE_RECOVERY_ABLATION_NOT_VALIDATED` | CLOSED | v0.4.12 contains independent two-mode causal runs, recovery lineage, exact suffix stability and clean QA. Production is frozen to `SOURCE_CONSERVATIVE`; recovery is diagnostic-only. |
| `GLOBAL_CROSS_PAIR_CLUSTER_PARAMETER_NOT_FROZEN` | CLOSED | Production window frozen to `0` minutes (exact timestamp only), which does not invent a near-time tolerance. Positive windows remain experiments. |
| `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED` | OPEN | Current real-data evidence is limited to BTC/ETH and the Range engine still relies on qualitative-to-machine normalizations. |
| `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED` | OPEN | Source gives qualitative nuance but no numeric threshold. |
| `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED` | OPEN | Source does not fully define permanent retirement/redraw/liquidity renewal. |
| `CROSS_ASSET_ROBUSTNESS_NOT_VALIDATED` | OPEN | Packaged real-data evidence covers only BTCUSDT and ETHUSDT. |
| `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED` | OPEN | Entry Engine belongs to the next phase after validation freeze. |

## Rule classification
- `SOURCE_CONSERVATIVE` production selection: `TECHNICAL_NORMALIZATION` / project policy, not a source trading rule.
- `TECHNICAL_RECOVERY`: diagnostic `TECHNICAL_NORMALIZATION`, never production source logic.
- exact-time global clustering (`0m`): production `TECHNICAL_NORMALIZATION`.
- positive clustering windows: `BACKTEST_PARAMETER`.
- cross-asset robustness requirement: project QA `TECHNICAL_NORMALIZATION`, not a source trading rule.

## Automated QA
- v0.4.12 baseline suite re-run before patch: **189/189 OK**.
- v0.4.13 clean-archive recheck: **192/192 OK**.
- `python -B -m compileall -q src scripts tests`: **PASS**.
- Source Rule Registry: `phase1.4.13-0.4.13`, **80 rules / 80 unique rule IDs** (`25 SOURCE_RULE`, `48 TECHNICAL_NORMALIZATION`, `7 BACKTEST_PARAMETER`); all SOURCE_RULE entries retain provenance.
- CLI `--help`: **7/7 scripts PASS**.
- Packaged v0.4.12 real-data evidence was re-read: both BTCUSDT/ETHUSDT summaries keep `checks_passed=true`; all 16 stored suffix BOS comparisons have `exact_jaccard=1.0`.
- Safety audit across packaged JSON reports scanned 267,750 `trade_entry_allowed` fields and found **0 true values**.
- ZIP integrity: **PASS** after clean repack; cache bytecode is excluded from the release archive.

### Reproducibility boundary
The expensive 240-day BTC/ETH ablation was **not fully re-run under v0.4.13 during this recheck**. Phase 1.4.13 changes production defaults/policy gates and version/report metadata; it does not alter the underlying Swing/BOS/SFP/Range/MTF detector algorithms. The 240-day causal evidence therefore remains the packaged Phase 1.4.12 baseline until a future full rerun is explicitly completed. Cross-asset validation is still open.

## Phase conclusion
Phase 1.4.13 is a **partial validation freeze**, not Entry Engine approval. Two policy blockers are closed, but Range robustness/lifecycle/clarity plus cross-asset validation remain. `trade_entry_allowed=false` remains mandatory.

Current readiness: **NOT_READY_FOR_PHASE_1_5** until the remaining pre-entry validation gates are either closed from evidence or explicitly redesigned without inventing source rules.
