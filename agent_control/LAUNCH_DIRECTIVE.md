# Crypto Bot — Strategy-First Launch Directive

This directive is authoritative for future work unless explicitly superseded by the user.

## Primary objective
Finish and qualify the trading strategy first. Platform/site/product-integration work is deferred until the strategy has a defensible validation result.

`MACHINE_STRATEGY_v3` is NOT considered launch-ready merely because its design and implementation are frozen. The current objective is to determine whether the frozen v3 logic is an actually viable trading candidate under realistic OKX data, metadata, fees, funding and execution assumptions.

Do not redesign/tune v3 from observed financial outcomes. First validate the frozen version honestly. If it fails the preregistered qualification gate, open a new explicit strategy-version design gate (for example v3.1/v4) using the frozen failure evidence; never patch rules post hoc inside the same evaluation.

## Selected venue for strategy work
The project selection for the current strategy path is **OKX**, chosen from the compared OKX / Kraken / Deribit / Hyperliquid direction.

Primary validation products:
- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`

Strategy research/backtesting is executed by our own deterministic Python runner in the repository, not on an exchange website. Official/public OKX data and retained OKX evidence are the primary market-data source. Additional venues are references only unless a later explicit reselection gate is opened.

## Usage-efficiency policy — serial first
- default one active specialist at a time;
- hard concurrency ceiling 2 threads;
- second thread only for independent verification/review;
- medium reasoning for routine engineering/data work;
- high reasoning only for critical statistical/robustness/final review;
- narrow context, reuse frozen artifacts/evidence, checkpoint every batch;
- do not mechanically launch all configured roles.

## Strategy-first qualification sequence
1. **V3 validation readiness on OKX** — verify the frozen v3 runner/spec, exact BTC/ETH products, causal data path, fee/funding model, tick/lot metadata treatment and preregister qualification metrics before reading new v3 financial outcomes.
2. **One-shot historical financial validation** — only after readiness PASS, run the frozen v3 on the preregistered OKX development sample with realistic costs and no tuning during the run.
3. **Robustness / failure audit** — LONG/SHORT, setup family, coin, regime, cost sensitivity, concentration, drawdown, loss streak, expectancy, PF and no-lookahead checks.
4. If v3 FAILS: freeze the failure evidence, then open a new strategy design version using causal changes only and repeat validation.
5. If v3 PASSES: proceed to pristine OOS/forward validation under preregistration.
6. After OOS qualification: Paper Trading, minimum 200 CLOSED virtual trades + 30 calendar days and required metrics.
7. Only after strategy qualification should platform/integration become the main workstream.
8. LIVE activation still requires explicit user authorization.

## Current safety invariants
- No platform/site work is active while the strategy-first gate is open unless it is strictly necessary to validate the strategy.
- No private exchange credentials or live orders are required for historical strategy qualification.
- PAPER remains OFF until qualification.
- LIVE remains OFF until qualification + explicit user authorization.
- `trade_entry_allowed=false` remains invariant until then.
- No VPN/proxy/geolocation evasion for data evidence.

## Reporting
At each strategy gate record exact PASS/STOP, frozen inputs, hashes, actual agents used, metrics, blockers and next action. The question to answer is simple: **is v3 a defensible OKX trading candidate or does it need a new strategy version?**
