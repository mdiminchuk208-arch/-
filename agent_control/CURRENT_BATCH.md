# Current Campaign — STRATEGY_AUTONOMY_TO_PLATFORM_RECONNECT

This replaces manual stage-by-stage user steering. The project lead owns the strategy loop end-to-end. Do not stop to ask the user routine questions. The next user-facing milestone is a strategy that has completed historical qualification, robustness, pristine OOS/forward validation and Paper qualification strongly enough to reopen platform reconnection planning.

## Non-negotiable target
A promoted strategy version must achieve **Win Rate >= 70%** on the applicable qualification sample and must also have positive net expectancy and positive net P&L after realistic fees/slippage/funding. Win Rate alone is insufficient. The 70% target must survive OOS/forward and Paper; do not waive it because in-sample results were strong.

## Venue and products
Use OKX as the strategy venue.
- BTC-USDT-SWAP
- ETH-USDT-SWAP

Use official/public OKX data and retained OKX evidence. Backtesting runs in the repository's deterministic Python runner. Do not substitute another venue without a separately frozen evidence-based reselection gate.

## Autonomous serial workflow
Operate SERIAL-FIRST to protect allowance: normally exactly one active specialist; hard ceiling two threads, with the second only for genuine independent review. Checkpoint and push after every stage/version so an interrupted run can resume without repeating work.

1. Complete v3 Stage-A readiness: exact frozen inputs/hashes, continuous M15/timestamps, historical tick/filter treatment, cost/funding/slippage preregistration, no-lookahead readiness, qualification rules including WR>=70%.
2. If readiness has a technical/data blocker that can be solved without user credentials/capital/legal choice, solve it autonomously and re-run readiness. Do not ask the user.
3. When readiness passes, execute the one-shot frozen-v3 historical validation.
4. Run failure/robustness analysis with the appropriate specialist roles sequentially.
5. If v3 fails any hard criterion — including WR<70%, non-positive net expectancy/P&L, unacceptable preregistered drawdown/loss-streak, leakage or robustness failure — freeze the complete failure evidence.
6. Open a NEW explicit strategy version (v3.1/v4/etc.) before evaluating its financial outcomes. Use strategy_explorer/strategy_designer only after the prior failure is frozen. Make causal, evidence-backed changes; do not post-hoc patch the failed version.
7. Preregister the new version, validate deterministically, backtest once, audit robustness, and repeat the version loop until a candidate passes or a genuine hard evidence blocker requires user action.
8. After historical/robust qualification, independently register and run pristine OOS/forward validation. WR>=70% and positive net edge remain required.
9. After OOS qualification, proceed to Paper qualification using the existing minimum of 200 CLOSED trades + 30 calendar days plus required risk/performance metrics. WR>=70% and positive net edge remain required.
10. Only after Paper qualification reopen platform reconnection planning and prepare the user-facing final strategy result.

## Specialist routing
Use the configured specialist catalog by function, not all at once:
- historical_data_engineer / backtest_engineer — data and deterministic runs;
- cost_funding_auditor / market_microstructure_auditor / execution_auditor — realism and costs;
- no_lookahead_auditor — causal integrity;
- statistics_robustness_analyst / market_regime_researcher — robustness/failure localization;
- strategy_explorer / strategy_designer — only for a new version after failure freeze;
- overfit_red_team / final_independent_reviewer — promotion challenge and seal.

## User escalation
Do not ask the user about routine parameters, strategy versions, tests, sequencing, repairs or whether to continue after a failed version. Escalate only if blocked by something that inherently requires the user: credentials/secrets, legal/account/jurisdiction decision, real capital, irreversible external action, or explicit LIVE authorization.

## Safety
No platform/site work until the strategy reaches the platform-reconnection milestone except code strictly necessary to validate the strategy. No private exchange trading API or live orders during historical/OOS validation. PAPER and LIVE remain controlled by their qualification gates. `trade_entry_allowed=false` until explicitly advanced.

If allowance forces the cloud run to stop, persist the exact checkpoint, next action and version state, push it, and exit cleanly. On the next run resume from that checkpoint rather than restarting research.

## Resume checkpoint

Stage A v1 is frozen STOP at `5a63716e0a042d8b1778581ae0d513d6314fb188`, manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`. Completed candles/funding must be reused. Exact restart action and source barriers are recorded in CURRENT_STATE.md and STAGE_A_REPORT.md. No Stage-B financial authorization follows from data acquisition alone. Preserve this freeze and use a new readiness-repair namespace for later source proof or a defensible separately versioned compatibility treatment. The WR>=70% autonomous campaign remains the objective; no platform work, strategy redesign to bypass missing evidence, OOS clock or PAPER/LIVE activation.
