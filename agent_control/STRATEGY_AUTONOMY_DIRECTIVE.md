# Strategy Autonomy Directive

User intent: the project lead owns strategy iteration end-to-end and should not stop for routine user decisions. The next user-facing milestone is strategy qualification sufficient to begin platform reconnection planning.

## Objective
Produce a defensible positive-edge OKX trading strategy candidate. Do not optimize merely for an in-sample positive curve. A candidate must survive realistic costs, robustness checks, pristine OOS/forward validation and paper qualification before platform reconnection becomes the main workstream.

User hard target: **Win Rate >= 70%** for a strategy version to be considered qualified for the intended launch path. This target is not satisfied by a single cherry-picked in-sample slice. It must coexist with positive net expectancy and positive net P&L after realistic fees/slippage/funding and must survive robustness, OOS/forward validation and Paper Trading.

No profitability guarantee is implied. If evidence shows no robust positive edge or the 70% target is not sustained, continue with a new explicitly versioned strategy design rather than hiding or post-hoc tuning failed results.

## Autonomous loop
1. Finish current v3 readiness gate.
2. Run one-shot frozen v3 historical validation when readiness authorizes it.
3. Run failure/robustness audit using specialist roles appropriate to the failure mode.
4. If v3 fails any hard qualification criterion, including Win Rate < 70%, freeze the failure evidence and open a new strategy version (v3.1, v4, etc.) BEFORE seeing that new version's financial outcomes.
5. Strategy redesign may change signal filters, direction logic, entry/exit geometry, target/stop construction, cost feasibility, regime logic, setup selection and other strategy rules only when the change is justified by frozen failure evidence and is preregistered before evaluation.
6. Run deterministic validation of the new version under the same anti-leakage discipline.
7. Repeat until a version qualifies historically and robustly or a hard evidence/data blocker makes further fair testing impossible.
8. On historical qualification, proceed to independently registered pristine OOS/forward validation. Win Rate >= 70% remains a required target there; do not waive it because historical results were stronger.
9. On OOS qualification, proceed to Paper Trading under the existing minimum 200 CLOSED trades + 30 calendar days and required metrics. Win Rate >= 70% remains required on the paper qualification sample together with positive net expectancy/P&L after modeled and realized costs.
10. Platform reconnection planning becomes active only after the strategy reaches the qualification threshold required by the launch plan.

## Success standard
Do not call a version successful solely because Net P&L > 0 or because Win Rate alone is high. Require all of the following as hard principles:
- Win Rate >= 70% on the applicable qualification sample;
- positive net expectancy after realistic fees/slippage/funding;
- positive net P&L;
- Profit Factor above break-even and above the exact preregistered threshold for that gate;
- acceptable drawdown and loss streak under preregistered limits;
- sufficient CLOSED-trade sample;
- no critical no-lookahead violations;
- no single-direction/setup/coin/time-slice dependence that invalidates robustness;
- survival of preregistered cost/execution sensitivity.

Exact numeric thresholds other than the user-fixed 70% Win Rate target must be preregistered before the corresponding financial evaluation and may reuse prior frozen project requirements. Never choose thresholds after seeing outcomes.

## Agent orchestration
The configured 22-role catalog is available. Use only the roles needed for the current failure/question. Typical sequence:
- backtest_engineer / historical_data_engineer for deterministic data and runs;
- execution_auditor / cost_funding_auditor / market_microstructure_auditor for realism;
- strategy_explorer / strategy_designer only after a failed version is frozen and a new version gate is open;
- market_regime_researcher for regime-conditioned failure analysis;
- statistics_robustness_analyst / no_lookahead_auditor / overfit_red_team for challenge;
- final_independent_reviewer for promotion.

Allowance policy remains serial-first: normally one active specialist, hard ceiling two threads, second only for genuine independent verification/review. Do not run 22 agents concurrently.

## User escalation
Do not ask the user to choose routine strategy parameters, versions, tests, sequencing, or repair actions. Escalate only when an action inherently requires the user: credentials/secrets, legal/account/jurisdiction decisions, real capital, irreversible external actions, or explicit authorization for LIVE trading.

## Platform boundary
Website/backend/UI work remains paused except for changes strictly necessary to run or validate the strategy. When the strategy reaches the platform-reconnection milestone, report the qualified version, frozen evidence, key metrics, residual risks and the exact integration target.

PAPER/LIVE remain governed by their separate gates. `trade_entry_allowed=false` until explicitly advanced by those gates.
