# Current State

Branch: `machine-v3-research`. Strategy first; platform/site work remains paused. Production candidate: NONE. OOS not registered; PAPER=false; LIVE=false; `trade_entry_allowed=false`.

## Frozen predecessors

- OKX Stage A freeze: `5a63716e0a042d8b1778581ae0d513d6314fb188`, manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`; reuse sealed 210,240 M15 bars and 4,380 funding rows.
- v3 compatibility READY: `e57b15091bda7e994133e586d7ab851d32011c5d`, manifest `5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1`.
- v3 financial qualification STOP: checkpoint `2d7770680867f93948d4d26b91633cbb8cdbc9136bd54a988436a687accc6dd0`, audit manifest `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`.
- v3 causal failure audit complete: publication `54419daa29e7e68d6f692daee9cf2132203393ef`, manifest `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`.

Known v3 diagnostic result remains unchanged: 99 candidates, 20 all-nine CLOSED, base WR50%, PF_R0.278459, expectancy -0.309356R, net -6.187114R; doubled-cost WR45%, PF_R0.162663, net -9.243979R. This is failed v3 evidence, not a v4/v4.1 result.

## Frozen v4 design

MACHINE_STRATEGY_V4_DESIGN_PASS published `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f`. External design freeze manifest: `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`.

Frozen v4 design preserves LONG/SHORT and all five families and introduces only preregistered causal changes: CLEAN/CORRECTIVE/INVALID approach, completed-close FTA lifecycle, structural resting lifetime, structural-vs-executable zone separation, doubled-cost 1R planned payoff gate and outcome-blind gate telemetry. Qualification thresholds remain unchanged, including WR>=70%.

## Completed gate — v4 implementation readiness STOP

Decision: `MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP`. External STOP-checkpoint manifest: `6e325d6e5b3cffc4f143bfd4d390712b39ea940bccd4504c85148ed904bbcd7e`. Complete implementation freeze=false; implementation_ready=false; historical_financial_authorized=false.

Independent execution, no-lookahead and final reviews confirmed a frozen selected-POI first-test gap: STB body/full parent consumption; generated BREAKER/RANGE origin-CONF/context/eligibility; required RANGE reaction exemption. Planned Decimal50 versus inherited ledger80 scope also required a separate design declaration. No historical v4 financial result was generated.

Component QA remains evidence only: 54 tests and nine commands PASS, bounded BTC/ETH source prefix/future-mutation and full sealed data integrity/continuity PASS. Historical tick/lot/account/mark/fill/API latency assumptions remain explicit model limitations.

## Completed gate — v4.1 design PASS

MACHINE_STRATEGY_V4_1_DESIGN_PASS independently accepted and externally frozen. Manifest SHA256 `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`; verified --resume-existing PASS. Design manifest is final authority over retained candidate/opening labels. Implementation_ready=false; complete_implementation_freeze=false; historical_financial_authorized=false.

Continued remotely authored draft from `964b3834b2f893497c2ae39849854ef9e06165c1`. Review clarified M15 execution versus native contact clocks, latched physical POI lifecycle before viable H1 proposal, immutable origin versus later proposal CONF, context-late FIRST M15 eligibility cutoff, native-context-at-OPEN, equal-cutoff contact before emission and nullable provenance. These close the selected-POI scope without changing unrelated frozen v4 geometry/exits/costs/scenarios/qualification. STB body/fullparent separation, BREAKER generated identity, RANGE reaction exemption and planned50/ledger80 are explicit machine definitions; source ambiguities are preserved.

Actual QA PASS: 52 tests (24 new hand-fixture design/guard tests plus28 frozen v4 design regressions), nine commands; prefix/future-mutation/deterministic replay in abstract design oracle, source/pin/qualification consistency, static/type/compile and both frozen parent resumes. All18 registered witness IDs have corresponding executed tests. Context/M4/fill facts are hand witnesses, not production signals or execution. Full-period historical causality/execution/funding parity remains future implementation work.

Actual serial independent roles: execution_auditor (/root/v41_execution_review), no_lookahead_auditor (/root/v41_no_lookahead_review), final_independent_reviewer (/root/v41_final_independent_review). Separate final reviewer re-ran24 tests/design check/parent resumes and verified all QA hashes/logs. Root sole writer; ECC2.2.3 enabled, hooks inactive. Prior interrupted execution review's clock finding retained; its failed final turn was not treated as acceptance.

Next after publication: separately named v4.1 Implementation Readiness v1. Preserve frozen v4.1/v4 and all predecessors; build new version paths and complete adapter/lifecycle/runner causality/conformance before any complete implementation freeze. This design PASS opens no financial/OOS/PAPER/LIVE/private API/orders/platform gate. Production candidate NONE; trade_entry_allowed=false.
