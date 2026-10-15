# MACHINE_STRATEGY_v4.1 — One-shot Development Financial Gate v1

State: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_OPEN`.

Authority: frozen implementation READY at commit `bf9bb4c7ed9e82df42b4fc2eec5df28695edf155`, external implementation manifest SHA256 `e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61`. Pre-outcome preregistration is `docs/machine_strategy_v4_1_development_financial_v1/PREREGISTRATION.json`, committed before authorization. Authorization is `AUTHORIZATION.json`. No v4.1 historical financial outcome had been generated when these files were committed.

## Objective

Execute exactly one fixed historical development financial evaluation of the frozen v4.1 strategy on the preregistered exposed OKX development window `[2024-10-13T00:00:00Z, 2026-10-13T00:00:00Z)` for `BTC-USDT-SWAP` and `ETH-USDT-SWAP`. This is not OOS and cannot be relabeled OOS.

## Frozen scope

- Keep LONG and SHORT.
- Keep SFP / OB / BREAKER / STB / RANGE.
- Keep all nine compatibility scenarios in frozen order.
- Keep frozen H00-H05, v4.1 selected-POI amendment, parent 16h half-open lifetime, nearest FTA, no farther-target fallback, one-grid executable envelope and H05 doubled-cost planned parity gate.
- Keep base fee `0.0006` per leg, base slippage `0.0002` per leg, doubled fee/slippage stress, and actual signed funding with inherited coherent adverse timing witness.
- Keep immutable reference `U` from P01_Q001 for qualification accounting.
- No parameter sweep, no threshold search, no family/direction removal, no catalog-count selection, no profitable-slice selection.

## Runner requirements before the one shot

1. Verify the exact implementation freeze manifest and commit bytes.
2. Verify preregistration and authorization commits are ancestors of HEAD and unchanged.
3. Build the catalog only with the frozen `machine_strategy_v4_1_historical_adapter.py` source path.
4. For each frozen catalog case, evaluate all nine scenarios. Before fill on every M15 OPEN, apply the frozen v4/v4.1 pending lifecycle using causal completed source state; current-bar execution precedes contact learned at CLOSE. After fill, use the frozen inherited conservative position observer only.
5. Preserve all scenario ineligible/unfilled/unknown/disagreement states. Never erase a case or replace a sibling after outcomes.
6. Use Decimal50 design bytes as serialized by implementation and Decimal80 realized accounting. The ledger must not rebuild entry/stop/target/FTA/quantity.
7. Include actual signed funding only after exposure begins and use the inherited coherent adverse same-timestamp witness.
8. Emit base and doubled-cost columns on the identical event path.
9. Hard-block PAPER/LIVE/private API/orders/platform and keep `trade_entry_allowed=false`.

## Required pre-run QA

Run registered synthetic execution/funding tests and negative authorization tests on the financial runner. Verify a caller cannot authorize history by supplying a boolean/manifest path/context. Verify one-shot output namespace is empty before execution. Verify no result metrics are read or used before the single run.

## Single historical execution

Run exactly once. Persist complete catalog/case/result outputs and a checkpoint hash immediately. If execution errors before a committed outcome checkpoint and no case-level financial output was exposed, repair implementation-only defects without changing frozen strategy semantics; record every failed attempt. If any financial/case outcomes were emitted, freeze them and do not silently rerun with altered logic.

## Result audit

Report/freeze at minimum: candidate count, CLOSED, WR, PF, expectancy, net/gross R, net/gross cash, fees, slippage, funding, max DD, max loss streak, Wilson lower bound, base vs doubled, BTC/ETH, LONG/SHORT, family, setup TF, quarter/coin concentration, compatibility disagreements and unknown exits. Apply all preregistered qualification thresholds unchanged.

Serial independent review after result: backtest_reviewer → cost_funding_auditor → statistics_robustness_analyst → overfit_red_team → final_independent_reviewer. Reviewers may audit; they may not retune the frozen result.

Finish exactly `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_PASS` or `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP`, with an externally pinned result manifest. PASS only opens robustness / separately registered untouched OOS prerequisites. STOP opens a causal failure audit/new explicit strategy version. No PAPER/LIVE/platform from this gate.
