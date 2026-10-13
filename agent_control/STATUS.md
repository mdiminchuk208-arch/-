# Agent Status

State: MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_REPAIR_OPEN
Branch: `machine-v3-research`.

User priority remains strategy-first and autonomous. Do not require routine user steering. Platform/site/integration work stays paused until strategy qualification reaches the platform-reconnection milestone.

## Hard target
A promoted strategy must satisfy the frozen qualification policy including:
- Win Rate >= 70%;
- positive net expectancy and net P&L after modeled costs and signed funding;
- base Profit Factor >=1.20;
- doubled-total-fees-and-slippage net positive and PF >=1.00;
- CLOSED >=200;
- max case-ledger drawdown <=20R;
- max consecutive net losses <=10;
- each coin+direction >=30 CLOSED and net positive;
- Wilson 95% lower bound >=0.60;
- concentration limits and no critical leakage/integrity failure.

## Selected venue
OKX: BTC-USDT-SWAP and ETH-USDT-SWAP.

## Frozen Stage-A v1
Decision: MACHINE_STRATEGY_V3_QUALIFICATION_STOP at Stage A only.
Freeze commit: `5a63716e0a042d8b1778581ae0d513d6314fb188`.
Manifest: `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`.

Completed evidence is reusable and must not be recollected:
- 105,120 continuous official OKX M15 candles/product;
- deterministic H1/H4/D1 derivation;
- full scoped historical signed funding series from official monthly archives/API overlap;
- 24 targeted QA tests and independent STOP review PASS.

## Why Stage A stopped
This was not a financial strategy failure. Exact historical OKX tick/lot/filter epochs and historical account-applicable API SWAP fees could not be source-verified. Current metadata cannot be backdated and blocked announcement routes are not to be evaded.

## Active repair
`agent_control/NEXT_TASK.md` opens `MACHINE_STRATEGY_v3_OKX_COMPATIBILITY_v1`.

The repair creates a separately versioned, pre-outcome compatibility execution model:
- frozen v3 signal/decision rules remain unchanged;
- synthetic quantization stress scenarios are explicitly modeled, not claimed as historical OKX truth;
- every candidate is evaluated under all preregistered stress scenarios with worst-case/adverse aggregation;
- base cost uses the already frozen 6bp fee + 2bp slippage per leg model;
- actual signed historical OKX funding is included;
- doubled-total-cost sensitivity remains mandatory;
- a new OKX runner/binding must be versioned separately from the frozen Bybit-bound runner.

No financial outcomes may be generated until compatibility policy/preregistration is frozen and independently accepted. If compatibility READY, the autonomous campaign may proceed to the one-shot historical financial run without routine user approval.

## Allowance policy
Serial-first: one specialist normally, hard ceiling two threads with the second only for independent review. Reuse frozen evidence and checkpoint every stage.

Historical financial v3 outcome access: still unauthorized until compatibility READY.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
