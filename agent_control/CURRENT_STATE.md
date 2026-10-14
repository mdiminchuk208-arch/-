# Current State

Branch: `machine-v3-research`. Strategy first; platform/site work remains paused. Production candidate: NONE. OOS not registered; PAPER=false; LIVE=false; `trade_entry_allowed=false`.

## Frozen predecessors

- OKX Stage A freeze: `5a63716e0a042d8b1778581ae0d513d6314fb188`, manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`; reuse sealed 210,240 M15 bars and 4,380 funding rows.
- v3 compatibility READY: `e57b15091bda7e994133e586d7ab851d32011c5d`, manifest `5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1`.
- v3 financial qualification STOP: checkpoint `2d7770680867f93948d4d26b91633cbb8cdbc9136bd54a988436a687accc6dd0`, audit manifest `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`.
- v3 causal failure audit complete: publication `54419daa29e7e68d6f692daee9cf2132203393ef`, manifest `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`.

Known v3 diagnostic result remains unchanged: 99 candidates, 20 all-nine CLOSED, base WR50%, PF_R0.278459, expectancy -0.309356R, net -6.187114R; doubled-cost WR45%, PF_R0.162663, net -9.243979R. This is failed v3 evidence, not a v4 result.

## Frozen v4 design

MACHINE_STRATEGY_V4_DESIGN_PASS published `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f`. External design freeze manifest: `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`.

Frozen v4 design preserves LONG/SHORT and all five families and introduces only preregistered causal changes: CLEAN/CORRECTIVE/INVALID approach, completed-close FTA lifecycle, structural resting lifetime, structural-vs-executable zone separation, doubled-cost 1R planned payoff gate and outcome-blind gate telemetry. Qualification thresholds remain unchanged, including WR>=70%.

## Completed gate — v4 implementation readiness STOP

Decision: `MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP`. External STOP-checkpoint manifest: `6e325d6e5b3cffc4f143bfd4d390712b39ea940bccd4504c85148ed904bbcd7e`. Complete implementation freeze=false; implementation_ready=false; historical_financial_authorized=false.

Independent execution, no-lookahead and final reviews confirmed the frozen selected-POI first-test gap: STB body/full parent consumption; generated BREAKER/RANGE origin-CONF/context/eligibility; required RANGE reaction exemption. H04 preserves eligibility, so implementation cannot invent the missing policy. The unsupported M15 clock is removed for these three families; lifecycle explicitly WAITs. Planned Decimal50 versus inherited ledger80 scope requires a new design declaration.

Preserved prototype work: separate completed-M15 source loop/H1 signal clock, causal anchors/U/FTA, per-scenario geometry checks, event telemetry, lifecycle and nine-scenario synthetic driver/funding. Historical entry unconditionally blocked; only registered exact synthetic fixtures execute. Full five-family historical lifecycle and rule conformance is NOT complete.

Actual component QA: 54 tests (28 frozen design +26 prototype/synthetic), nine commands PASS; static/type/compile, bounded seven-day BTC/ETH source prefix and future-mutation with position engine trap, exact frozen design/failure/Stage-A resumes. Full official capture data review PASS: 210240 native M15 bars, 4380 funding rows, complete H1/H4/D1, zero gaps/duplicates/interpolation. Historical tick/lot/account/mark/fill/API latency assumptions remain unverified.

Actual serial roles: backtest_engineer; historical_data_engineer; execution_auditor; no_lookahead_auditor; final_independent_reviewer. Root sole writer; ECC ecc@ecc 2.2.3 enabled; hooks inactive. Review receipts and exact hash pins are in docs/machine_strategy_v4_implementation_readiness_v1/.

Next action after publication: open a separate narrow pre-outcome MACHINE_STRATEGY_v4.1 selected-POI first-test/arithmetic-scope design gate. No outcome-based policy selection. Preserve all frozen v4/predecessor artifacts; implementation resumes only after new design review/freeze. This checkpoint cannot open a financial gate.

No historical v4 fill/exit/financial output generated or viewed. No OOS/PAPER/LIVE/private API/orders/platform work. Production candidate NONE; trade_entry_allowed=false.
