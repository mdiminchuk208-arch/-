# Agent Status

State: STRATEGY_AUTONOMY_TO_PLATFORM_RECONNECT_ACTIVE
Branch: `machine-v3-research`.

User priority is explicit: the project lead owns the strategy loop end-to-end. Do not require routine user steering. The next user-facing milestone is strategy qualification sufficient to reopen platform reconnection planning.

## Strategy truth
`MACHINE_STRATEGY_v3` is coded/frozen but not yet qualified. The project must determine whether v3 can meet the hard launch target and, if not, autonomously freeze its failure evidence and move to a new explicit version.

## Hard user target
A promoted strategy version must achieve:
- Win Rate >= 70% on the applicable qualification sample;
- positive net expectancy after realistic fees/slippage/funding;
- positive net P&L;
- the preregistered Profit Factor/drawdown/loss-streak and robustness requirements;
- no critical leakage/lookahead;
- survival of OOS/forward validation and Paper qualification.

The 70% target is not waived for a strong in-sample result. It remains required on OOS/forward and Paper qualification samples.

## Selected venue
OKX is the active strategy/data/trading target unless a later evidence-based reselection gate explicitly changes it.
Primary products:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

Backtesting uses the repository's deterministic Python runner with official/public OKX data and retained OKX evidence.

## Active campaign
`agent_control/CURRENT_BATCH.md` now defines the autonomous serial strategy campaign:
1. finish v3 readiness;
2. one-shot historical validation;
3. robustness/failure audit;
4. if failed, freeze evidence and create a new explicit strategy version;
5. repeat until a robust candidate qualifies or a genuine user-required blocker appears;
6. pristine OOS/forward validation;
7. Paper qualification (minimum 200 CLOSED + 30 calendar days plus metrics);
8. only then reopen platform reconnection planning.

No routine user confirmation is required between these steps.

## Allowance policy
SERIAL-FIRST: normally one specialist at a time; hard ceiling two threads, second only for independent review. Medium reasoning for routine engineering/data work; High reserved for critical statistical/red-team/final review. Checkpoint/push after each stage/version and resume rather than repeat if allowance ends.

Platform/site/integration implementation is paused until the strategy reaches the platform-reconnection milestone.

Historical financial v3 backtest remains unauthorized until readiness prerequisites are frozen, after which the campaign may open the one-shot validation gate without asking the user for routine approval.
OOS registration: none yet.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
