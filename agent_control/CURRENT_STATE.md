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

## Active gate — v4.1 independent design review

A separate narrow pre-outcome MACHINE_STRATEGY_v4.1 amendment has now been authored. It does not change any unrelated frozen v4 strategy rule and uses no historical v4/v4.1 outcomes or catalog-count ranking.

Authored namespace `docs/machine_strategy_v4_1_design_v1/` now contains:
- `MACHINE_STRATEGY_v4_1_SPEC.md`;
- `SELECTED_POI_CONTRACT.json`;
- `ARITHMETIC_SCOPE_CONTRACT.json`;
- `PREREGISTRATION.json`;
- `FIELD_PROVENANCE.json`;
- `FIRST_TEST_DECISION_TREE.json`;
- `RULE_REGISTRY.json`;
- `SYNTHETIC_WITNESS_REGISTRY.json`.

The amendment makes the selected entry POI a distinct causal object with family-specific identity and first-test clock. SFP/OB keep their refined M15 POIs. STB gets a generated body handle separate from the full manipulation parent. BREAKER gets a generated body handle created only after its completed breaker event. RANGE gets a generated zero-width boundary handle; its mandatory boundary reaction is explicitly exempt from consumption, while the first later eligible contact consumes it. Eligibility begins prospectively only after family prerequisites, origin CONF and required completed context are known. An already-active order is evaluated from the bar OPEN snapshot before current-bar contact becomes known at CLOSE; CLOSE cannot retroactively cancel an earlier valid fill.

Arithmetic is now explicitly separated: design/execution geometry and admission use Decimal precision50 ROUND_HALF_EVEN; realized ledger accumulation/R division uses precision80 ROUND_HALF_EVEN over canonical serialized design values and may not recompute or change admission geometry.

Current decision is NOT yet PASS. Active task is independent synthetic causality/execution/no-lookahead/final review of the exact authored bytes. On accepted `MACHINE_STRATEGY_V4_1_DESIGN_PASS`, publish an external design manifest and reopen a separately named v4.1 implementation-readiness gate. On STOP, preserve the exact blocker. No implementation may silently bypass review.

No historical v4/v4.1 fill/exit/financial output, no OOS/PAPER/LIVE/private API/orders/platform work. Production candidate NONE; `trade_entry_allowed=false`. ECC enabled; hooks inactive.
