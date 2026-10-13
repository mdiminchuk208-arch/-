# Current Campaign — STRATEGY_AUTONOMY_TO_PLATFORM_RECONNECT

The project lead owns the strategy loop end-to-end. Do not stop for routine user decisions. The next user-facing milestone remains a strategy that has completed historical qualification, robustness, pristine OOS/forward validation and Paper qualification strongly enough to reopen platform reconnection planning.

## Hard target
A promoted strategy version must achieve **Win Rate >= 70%** and positive net expectancy/net P&L after realistic costs, with the already preregistered PF/drawdown/loss-streak/sample/concentration/robustness requirements. The 70% target must survive OOS/forward and Paper.

## Venue
OKX remains the strategy/data/trading target:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

## Frozen Stage-A checkpoint
Stage A v1 is frozen STOP at commit `5a63716e0a042d8b1778581ae0d513d6314fb188`, manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`.

Reuse without rebuilding:
- 105,120 continuous native M15 bars per product;
- 365-day warmup + two full development years;
- deterministic H1/H4/D1 derivations;
- complete scoped historical signed funding series;
- retained receipts/checkpoints/QA.

Do not recollect this sealed namespace.

## Active autonomous resume action
Execute `agent_control/NEXT_TASK.md`: **MACHINE_STRATEGY_v3 OKX Compatibility Repair v1**.

Reason: exact historical OKX tick/lot/filter epochs and ordinary historical account-applicable API SWAP fees are unavailable as source-verified facts. Rather than waiting indefinitely or fabricating evidence, create a separately versioned, pre-outcome compatibility execution model.

### Required sequence
1. One specialist designs and preregisters the synthetic adverse quantization stress family and ambiguity/worst-case rule. No P&L access.
2. Freeze that policy in the new compatibility namespace before implementation can generate financial outputs.
3. Implement a new OKX compatibility runner/binding without mutating frozen v3 signal logic or old runner bytes.
4. Use the sealed OKX M15/funding inputs.
5. Base cost remains the existing modeled 6bp fee + 2bp slippage per leg; actual signed funding is included. Mandatory doubled-total-cost sensitivity from the frozen qualification policy remains required.
6. Independently audit no-lookahead, deterministic replay, protected hashes and the fact that no financial outcomes were accessed before compatibility preregistration.
7. If compatibility READY, checkpoint/freeze and continue autonomously into the one-shot historical financial validation if allowance remains.
8. If historical v3 fails any hard criterion, freeze the failure evidence and open a new explicit strategy version before changing strategy rules.
9. Continue version loop autonomously through robustness, then OOS/forward, then Paper.
10. Only after Paper qualification reopen platform reconnection planning.

## Agent policy
Serial-first: normally one active specialist, hard ceiling two threads; second only for independent verification. Use the configured 22-role catalog by function, never all at once.

## User escalation
Do not ask the user about routine strategy parameters, repairs, versions, tests or sequencing. Escalate only for credentials/secrets, legal/account/jurisdiction decisions, real capital, irreversible external actions or LIVE authorization.

## Safety
No platform/site work. No private trading API/orders. OOS not started yet. PAPER=false. LIVE=false. `trade_entry_allowed=false`.

If allowance ends, commit/push the exact checkpoint and next action, then resume from it on the next cloud run.
