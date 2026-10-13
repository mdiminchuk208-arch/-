# Agent Status

State: MACHINE_STRATEGY_V3_QUALIFICATION_STAGE_A1_OPEN
Branch: `machine-v3-research`.

User priority is explicit: finish/qualify the strategy first; platform/site/integration work is deferred.

## Strategy truth
`MACHINE_STRATEGY_v3` has frozen design and implementation artifacts, but it is NOT yet a qualified trading strategy and is NOT launch-ready. Frozen/coded means the rules and implementation are available for testing. It does not mean profitability, robustness, OOS qualification, paper readiness or live readiness has been established.

The reason v3 rules are not casually changed now is anti-overfit discipline: first test the frozen version honestly. If it fails, freeze the failure evidence and then open a new explicit strategy-version design gate rather than tuning v3 after seeing results.

## Selected venue
The current strategy path uses **OKX** as the selected validation/trading architecture target from the OKX / Kraken / Deribit / Hyperliquid comparison direction.

Primary products:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

Backtesting runs in the repository with our deterministic Python runner. Market inputs come from official/public OKX data and retained OKX evidence. Existing OKX checkpoint confirms current public reachability, product identity, current metadata, funding/book/candle access; ordinary API SWAP fee applicability and historical tick/filter epochs remain readiness items.

## Active gate
`MACHINE_STRATEGY_v3 Qualification v1`.

Current batch `agent_control/CURRENT_BATCH.md` is Stage A1 readiness only: verify frozen inputs, validate continuous OKX M15 data/timestamps, resolve historical tick/filter treatment without backdating current metadata, freeze OKX cost/funding/slippage model and qualification rules, and STOP before new financial outcomes.

Platform/site/unified exchange layer implementation is paused.

## Allowance policy
SERIAL-FIRST: one active specialist by default, hard ceiling two threads, second only for independent verification/review, medium reasoning for routine work, narrow context, checkpoint every batch.

Historical financial v3 backtest ready=false and authorized=false until Stage A readiness PASS opens the one-shot validation gate.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
