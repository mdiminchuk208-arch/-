# Crypto Bot — Strategy-First Launch Directive

This directive is authoritative for future work unless explicitly superseded by the user.

## Primary objective
Finish and qualify the trading strategy first. Platform/site/exchange-abstraction product work is deferred until the strategy has a defensible validation result.

`MACHINE_STRATEGY_v3` is NOT considered launch-ready merely because its design and implementation are frozen. The current objective is to determine whether the frozen v3 logic is an actually viable trading candidate under realistic data, metadata, fees, funding and execution assumptions.

Do not redesign/tune v3 from observed financial outcomes. First validate the frozen version honestly. If it fails the preregistered qualification gate, open a new explicit strategy-version design gate (for example v3.1/v4) using the frozen failure evidence; never patch rules post hoc inside the same evaluation.

## Venue scope
The original project execution set remains the project's primary venue scope: Bybit, Bitget, BloFin and MEXC. The broader exchange-selection audit is preserved as useful research evidence, but additional venues discovered there are not automatically added to the strategy/product plan.

For strategy validation, one accessible research venue may be used as an evidence source when needed. Bitget is currently the preferred public research source because the retained audit found accessible BTC/ETH perpetual data/metadata. That does not change the user's intended live exchange set by itself.

## Usage-efficiency policy — serial first
- default one active specialist at a time;
- hard concurrency ceiling 2 threads;
- second thread only for independent verification/review;
- medium reasoning for routine engineering/data work;
- high reasoning only for critical statistical/robustness/final review;
- narrow context, reuse frozen artifacts/evidence, checkpoint every batch;
- do not mechanically launch all configured roles.

## Strategy-first qualification sequence
1. **V3 validation readiness** — verify the frozen v3 runner/spec, exact BTC/ETH products, causal data path, fee/funding model, tick/lot metadata treatment and preregister qualification metrics before reading new v3 financial outcomes.
2. **One-shot historical financial validation** — only after readiness PASS, run the frozen v3 on the preregistered development sample with realistic costs and no tuning during the run.
3. **Robustness / failure audit** — LONG/SHORT, setup family, coin, regime, cost sensitivity, concentration, drawdown, loss streak, expectancy, PF and no-lookahead checks.
4. If v3 FAILS: freeze the failure evidence, then open a new strategy design version using causal changes only and repeat validation.
5. If v3 PASSES: proceed to pristine OOS/forward validation under preregistration.
6. After OOS qualification: Paper Trading, minimum 200 CLOSED virtual trades + 30 calendar days and required metrics.
7. Only after strategy qualification should platform/exchange-layer integration become the main workstream.
8. LIVE activation still requires explicit user authorization.

## Current safety invariants
- No platform/site work is active while the strategy-first gate is open unless it is strictly necessary to validate the strategy.
- No private exchange credentials or live orders are required for historical strategy qualification.
- PAPER remains OFF until qualification.
- LIVE remains OFF until qualification + explicit user authorization.
- `trade_entry_allowed=false` remains invariant until then.
- No VPN/proxy/geolocation evasion for data evidence.

## Reporting
At each strategy gate record exact PASS/STOP, frozen inputs, hashes, actual agents used, metrics, blockers and next action. The question to answer is simple: **is v3 a defensible trading candidate or does it need a new strategy version?**
