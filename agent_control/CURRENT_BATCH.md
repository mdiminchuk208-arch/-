# Current Campaign — MACHINE_STRATEGY_v4 Implementation Readiness

Pre-outcome design independently PASS and published `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f`, external freeze `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`. Do not restart design or diagnosis.

## Current implementation checkpoint

Separate v4 code paths now exist:
- `scripts/machine_strategy_v4_readiness_core.py` — M4 approach, FTA lifecycle, H04 executable envelope, H05 doubled-cost 1R payoff gate, parent deadline, telemetry guard;
- `scripts/machine_strategy_v4_historical_adapter.py` — OKX causal pre-entry adapter over pinned raw/state/data primitives; no position/outcome simulation;
- `scripts/machine_strategy_v4_execution_binding.py` — all nine compatibility scenarios retained through pre-fill eligibility, no financial outcome generation;
- synthetic tests for readiness core and nine-scenario binding;
- readiness namespace with implementation protocol, rule-to-code conformance and explicit outcome isolation.

No test/QA PASS is claimed merely from commits. GitHub workflow on this repository does not run for direct `machine-v3-research` pushes, so the cloud executor must actually execute QA.

## Execute next

Continue `NEXT_TASK.md` and `V4_IMPLEMENTATION_READINESS_WORK_ORDER.md` from the committed checkpoint. Do not rewrite existing v4 design.

1. Run compile/static/unit checks for new v4 files and repair implementation defects without changing frozen rules.
2. Exercise sealed OKX adapter prefix and future-mutation causality for BTC-USDT-SWAP and ETH-USDT-SWAP; no historical fill/exit or finance output.
3. Complete active-order event loop: structural lifetime, context/POI/FTA retirement, current-bar event ordering, gap/EOF/unknown preservation.
4. Complete guarded nine-scenario execution/funding binding using registered synthetic fixtures only until implementation freeze.
5. Add full append-only gate telemetry with readback isolation.
6. Run mirrored LONG/SHORT and all-five-family production conformance, deterministic replay and negative financial-guard tests.
7. Independent no-lookahead, execution/funding and final implementation review.
8. Freeze exactly one decision: `MACHINE_STRATEGY_V4_IMPLEMENTATION_READY` or `MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP`, externally pinning `IMPLEMENTATION_FREEZE_MANIFEST.json`.

Only IMPLEMENTATION_READY may open a later one-shot historical v4 financial gate. Historical P&L/WR/PF/expectancy/DD/case outcomes remain forbidden now.

Serial root plus one specialist, root sole writer. No OOS/PAPER/LIVE/private API/orders/platform work. `trade_entry_allowed=false`; ECC hooks inactive.
