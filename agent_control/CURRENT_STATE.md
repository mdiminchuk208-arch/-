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

## Active gate — v4 implementation readiness

State: `MACHINE_STRATEGY_V4_IMPLEMENTATION_READINESS_IN_PROGRESS`.

Separate v4 implementation paths now committed:
- `scripts/machine_strategy_v4_readiness_core.py` — pure nonfinancial frozen-rule contracts;
- `scripts/machine_strategy_v4_historical_adapter.py` — causal OKX pre-entry adapter over pinned raw/state/data primitives, with no position/outcome simulation;
- `scripts/machine_strategy_v4_execution_binding.py` — all nine compatibility scenarios through pre-fill eligibility only;
- `tests/test_machine_strategy_v4_readiness_core.py`;
- `tests/test_machine_strategy_v4_execution_binding.py`;
- `docs/machine_strategy_v4_implementation_readiness_v1/IMPLEMENTATION_PROTOCOL.md`;
- `docs/machine_strategy_v4_implementation_readiness_v1/RULE_TO_CODE_CONFORMANCE.json`;
- `docs/machine_strategy_v4_implementation_readiness_v1/RUNNER_OUTCOME_ISOLATION.json`.

No QA PASS is claimed for these new implementation files yet. Repository Actions trigger strategy validation on main/PR, not direct pushes to this research branch. Actual execution is required next.

## Exact next work

1. execute compile/static/unit checks for new v4 code and repair implementation-only defects;
2. verify real sealed OKX adapter prefix/future-mutation determinism for BTC/ETH without running historical fill/exit finance;
3. complete active-order structural event loop and full append-only telemetry;
4. complete guarded nine-scenario execution/funding path with registered synthetic fixtures only;
5. run mirrored LONG/SHORT/five-family/gap/EOF/unknown/replay/guard-negative conformance;
6. independent no-lookahead, execution/funding and final review;
7. externally pin `IMPLEMENTATION_FREEZE_MANIFEST.json` and publish exactly `MACHINE_STRATEGY_V4_IMPLEMENTATION_READY` or `MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP`.

Historical v4 P&L, WR, PF, expectancy, drawdown and case-level financial outcomes remain unauthorized until IMPLEMENTATION_READY opens a separately named one-shot financial gate. No OOS/PAPER/LIVE/private exchange API/orders/platform work. `trade_entry_allowed=false`.
