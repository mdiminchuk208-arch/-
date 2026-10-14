# Agent Status

State: MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_IMPLEMENTATION_OPEN
Branch: `machine-v3-research`.

User priority remains strategy-first and autonomous. Platform/site/integration work stays paused until strategy qualification reaches the platform-reconnection milestone.

## Hard target
A promoted strategy must satisfy the frozen qualification policy including Win Rate >=70%, positive net expectancy and P&L after modeled costs and signed funding, PF>=1.20, doubled-cost net positive/PF>=1.00, CLOSED>=200, drawdown<=20R, max loss streak<=10, required coin+direction sample/net positivity, Wilson lower bound>=0.60, concentration limits and no critical leakage/integrity failure.

## Selected venue
OKX: BTC-USDT-SWAP and ETH-USDT-SWAP.

## Frozen Stage-A v1
Decision: MACHINE_STRATEGY_V3_QUALIFICATION_STOP at Stage A only.
Freeze commit: `5a63716e0a042d8b1778581ae0d513d6314fb188`.
Manifest: `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`.

Reusable evidence:
- 105,120 continuous official OKX M15 candles/product;
- deterministic H1/H4/D1 derivation;
- full scoped historical signed funding series;
- independent Stage-A STOP review PASS.

## Frozen compatibility preregistration
Policy commit: `23f275cae85d1cab4d91cc07351ffdef2560d75d`.
Namespace: `docs/machine_strategy_v3_okx_compatibility_v1/`.
Policy receipt confirms no historical financial outcomes generated and implementation not yet started at the freeze point.

Nine frozen scenarios: price grid multipliers 1/5/20 × lot/minimum multipliers 1/100/700. Fixed reference candidate catalog/risk denominator, all states retained, worst CLOSED value and preregistered adverse STOP handling for disagreement/unresolved fills. Base modeled cost 6bp fee +2bp slippage per leg; actual signed funding included; doubled-total-cost sensitivity mandatory.

## Active batch
`agent_control/CURRENT_BATCH.md` now authorizes implementation of the versioned OKX compatibility runner/binding and focused deterministic QA. Frozen v3 signal logic, Stage-A bytes and compatibility policy bytes must remain unchanged.

After implementation, run independent no-lookahead review then final independent READY review. Only `MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY` may authorize the one-shot Stage-B historical financial run. Until then no new strategy P&L may be generated/read.

## Allowance policy
Serial-first: normally one specialist; hard ceiling two threads with second only for independent review. Checkpoint/push each stage and resume rather than repeat.

Historical financial v3 outcome access: unauthorized until compatibility READY.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
