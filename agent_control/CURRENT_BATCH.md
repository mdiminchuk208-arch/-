# Current Campaign — OKX Compatibility Implementation + READY Review

The autonomous strategy campaign remains active. Do not ask the user routine questions. Platform/site/integration work remains paused.

## Fixed target
Promoted strategy target remains Win Rate >=70% plus positive net expectancy/P&L after modeled costs and signed funding, CLOSED>=200, PF>=1.20, doubled-cost PF>=1.00 and net positive, drawdown<=20R, loss streak<=10, slice/sample/concentration rules, and no critical leakage/integrity failure.

## Venue/products
OKX:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

## Frozen inputs to reuse
Stage-A v1 freeze:
- commit `5a63716e0a042d8b1778581ae0d513d6314fb188`
- manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`
- 105,120 continuous completed M15 bars/product
- deterministic H1/H4/D1 derivation
- 2,190 signed funding settlements/product

Compatibility policy preregistration is already frozen before outcomes at commit:
- `23f275cae85d1cab4d91cc07351ffdef2560d75d`

Policy namespace:
- `docs/machine_strategy_v3_okx_compatibility_v1/`

Policy receipt states historical financial outputs generated=false and implementation_started=false. Preserve policy bytes unchanged.

## Execute now
Use one implementation specialist at a time, normally `backtest_engineer`; a second thread is allowed only later for independent no-lookahead/final review.

1. Implement a NEW versioned OKX compatibility runner/binding. Do not mutate frozen v3 strategy core, frozen Bybit runner/adapter, Stage-A freeze, or frozen compatibility policy bytes.
2. Consume only the sealed OKX M15/derived/funding inputs.
3. Preserve frozen v3 signal/setup/trend/range/entry/stop/target rules.
4. Implement all nine preregistered compatibility scenarios exactly: price-grid multipliers 1/5/20 × lot/minimum multipliers 1/100/700.
5. Preserve one fixed reference candidate catalog/reservation and reference risk denominator across scenarios. Do not regenerate/select different candidates per scenario to improve results.
6. Retain all cases. For CLOSED cases use the preregistered worst financial result across scenarios. Any preregistered eligibility/fill/closure disagreement or unresolved fill must follow the frozen adverse/STOP rule rather than disappearing from the denominator.
7. Include actual signed historical OKX funding according to the frozen settlement proxy/timing policy. Funding is never a signal input.
8. Apply base modeled costs 6bp fee +2bp slippage per leg and the mandatory doubled-total-fees-and-slippage scenario. Do not replace them with favorable unverified OKX fee assumptions.
9. Add deterministic tests for scenario enumeration, candidate identity preservation, adverse aggregation, funding sign/timing, base+doubled costs, no-leakage, prefix/future mutation, venue identity, protected-hash invariance and output authorization.
10. Before any P&L output can be generated, run an independent `no_lookahead_auditor` review and then a fresh `final_independent_reviewer` READY review. Reviewers must not author the implementation.
11. Publish either `MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY` or `_STOP` with QA/replay/freeze manifest.
12. If READY, immediately open the one-shot Stage-B historical financial run under the same frozen policy if allowance remains. If allowance stops, checkpoint exact READY state and next command; do not repeat the compatibility work next run.

## Forbidden before READY
- reading/generating new strategy financial outcomes;
- parameter tuning or strategy redesign;
- changing the nine-scenario policy after implementation results;
- website/platform work;
- private OKX API/orders;
- OOS/PAPER/LIVE.

`trade_entry_allowed=false`.
