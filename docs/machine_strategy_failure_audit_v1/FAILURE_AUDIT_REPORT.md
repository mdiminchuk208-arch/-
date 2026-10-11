# Frozen machine failure audit v1

Retrospective development diagnosis; no new strategy, cohort, historical execution or admission rule. All frozen outputs remain intact. trade_entry_allowed=false; PAPER/LIVE off.

| Version | CLOSED | Gross R | Fees R | Slippage R | Net R ex funding | PF |
|---|---:|---:|---:|---:|---:|---:|
| v2 | 223 | 50.992034 | 74.236361 | 24.745454 | -47.989781 | 0.682938 |
| v2.1 | 83 | 27.610450 | 29.214199 | 9.738066 | -11.341815 | 0.837552 |
| v2.2 | 39 | 30.007827 | 26.603316 | 8.867772 | -5.463261 | 0.896249 |

## Direction and attribution

| Version/direction | CLOSED | Gross R | Costs R | Net R | Planned target/stop median |
|---|---:|---:|---:|---:|---:|
| v2/LONG | 118 | 73.709148 | 46.636065 | 27.073083 | 0.496659 |
| v2/SHORT | 105 | -22.717114 | 52.345749 | -75.062863 | 0.481206 |
| v2.1/LONG | 45 | 37.681849 | 13.221854 | 24.459996 | 0.922776 |
| v2.1/SHORT | 38 | -10.071399 | 25.730412 | -35.801811 | 0.821558 |
| v2.2/LONG | 22 | 37.959577 | 11.401028 | 26.558549 | 2.043835 |
| v2.2/SHORT | 17 | -7.951751 | 24.070060 | -32.021810 | 3.002782 |

SHORT gross weakness precedes costs in v2 across each year and both symbols. RANGE and 2024 concentrate much of its net deficit, but neither accounts for all losses. H4 and BREAKER can differ from the aggregate. The all-case, year/symbol/branch/TF/month/context/FTA/status tables are in LONG_SHORT_ASYMMETRY.json; these overlapping slices are not independent experiments.

Low nearest-FTA reward relative to planned stop is common among CLOSED v2 trades: planned target/stop <1R in 89/118 LONG and 78/105 SHORT. Geometry for unfilled and gap-invalidated cases differs from closed cases, indicating selection by execution. No counterfactual outcome is invented for unfilled orders. Gross realized performance cannot uniquely separate signal quality from target/stop policy or market regime; no causal market explanation is asserted.

Aggregate positive gross is erased by modeled price-proportional costs in all three versions. Gross/(fees+slippage) describes arithmetic cost tolerance, not a proposed or proven execution budget. Funding remains unavailable/excluded; amounts are R units, not account-currency P&L. The frozen 0.5x/1x/2x cost scenarios are preserved sensitivity evidence, never optimized fee assumptions.

## Extreme denominators and execution symmetry

All 345 CLOSED version records independently match signed gross, actual fill-to-stop denominator, 6 bp fee per leg, 2 bp slippage per leg and net identities. No direction-sign defect was identified in those records or inspected planning/execution predicates. Paired reflection and price-scaling tests strengthen bounded synthetic evidence, while bps costs and relative epsilon require explicit transformation-aware expectations.

ETH SHORT RANGE case ede81fd2453984e72a532c1e1b4f0a3385d426073829b6d222ecbe518e16a5d3 has fill 3121.5, stop 3121.8300312183, risk 0.3300312183 (1.057 bp), gross -1R, modeled costs 15.133914R and net -16.133914R. Relative epsilon adds only 0.0000312183; the entry-anchor gap produces the tight risk. Small-risk LONG winners and losers also occur. EXTREME_R_AUDIT.json records IDs/prices, risk ratios, cost tails and leave-one-extreme-out sensitivity. Official cohorts, labels and totals are unchanged.

v2.2 is particularly unstable: omitting the worst SHORT diagnostically reverses total net sign; omitting its top two LONG gains reverses LONG net sign. These omissions are diagnostics, never permitted strategy exclusions. v2.1/v2.2 are exact nested subsets with unchanged shared outcomes and only 83/39 CLOSED; their contrast is not independent replication or proof of an optimal threshold.

## Timing and unresolved evidence

Same-bar wick-fill/stop timing-bound overprecision affects v2: 6, v2.1: 4, v2.2: 4 version records; later versions repeat inherited cases. True intrabar elapsed times are unknown. Recorded zero hold and point exit bounds are observation conventions that overstate timing certainty. P&L arithmetic is unchanged, and the frozen engine is not fixed here.

All WAIT_INTRABAR_ORDER cases are LONG (5/2/1). Resolved-only direction metrics retain asymmetric censoring; OHLC does not establish their outcomes. Historical tick/rounding, actual spread, funding and shared portfolio/margin behavior remain unverified.

## Causality, independent review and next gate

Features use only frozen pre-outcome cases and recursively validated known_at/end_swing_at timestamps. Both ALL_TRADES (filled) and CLOSED_TRADES partitions, counts/statuses, preregistered IDs/ordering, commit ancestry, stored accounting and nested outcomes are verified. Saved execution fill/observation/consumption/exit chronology passes; it cannot resolve intrabar order. Deterministic audit replay is separate from financial backtesting. The local saved-case projection check is determinism only, not independent future-mutation proof. Original/evidence/baseline/source-audit/dataset and all 14 machine namespaces are hash-verified. The inherited actual midpoint prefix proof covers 426 cases (BTC 210, ETH 216) with a 10x future suffix mutation; this audit does not claim a fresh historical rerun or every-instant proof.

Independent roles strategy_explorer, execution_auditor and backtest_reviewer ran through cloud collaboration with the configured gpt-6-sol/high role instructions. Native ECC config/read verified named roles and skills separately; this does not claim the cloud subagents were launched as native CLI agent_type processes. Their recorded conclusions and review scope are retained under independent_review/. strategy_designer was not launched.

Designing a separate MACHINE_STRATEGY_v3 is justified only after this diagnostic freeze: investigate executable structural risk/cost capacity, stable sizing/normalization and causal signal-versus-fill attribution. This is permission to investigate causally justified definitions, not evidence of a profitable rule. No direction/branch/year/symbol is removed, no threshold is selected from performance, and the audit creates no v3 rule. A new pre-outcome specification and untouched OOS/forward evaluation are prerequisites to any production claim.

Current production candidate: NONE. PAPER_TRADING_READY=false; REAL_TRADING_READY=false; trade_entry_allowed=false.

Evidence files: FAILURE_AUDIT.json; LONG_SHORT_ASYMMETRY.json; GROSS_VS_NET_COST_ATTRIBUTION.json; EXIT_REASON_BREAKDOWN.json; IMPLEMENTATION_SYMMETRY_QA.json; EXTREME_R_AUDIT.json; CASE_DIAGNOSTICS.csv; CAUSALITY_QA.json; FROZEN_INPUT_VERIFICATION.json. QA_REPORT.md and freeze_manifest.json close the audit after checks.
