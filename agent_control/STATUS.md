# Agent Status

State: MACHINE_STRATEGY_V3_OKX_FAILURE_AUDIT_OPEN
Branch: `machine-v3-research`.

The first authorized OKX financial development run is frozen STOP. v3 is financially unqualified under the preregistered policy and must not be rerun or tuned in place.

## Frozen financial result
Compatibility READY: `e57b15091bda7e994133e586d7ab851d32011c5d`, manifest `5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1`.
Financial run checkpoint: `2d7770680867f93948d4d26b91633cbb8cdbc9136bd54a988436a687accc6dd0`.
Financial audit manifest: `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`.

Result:
- 99 unique candidates retained;
- 20 all-nine-scenario CLOSED;
- 70 all-scenario NO_FILL;
- 9 eligibility disagreements;
- known CLOSED base: WR 50%, PF_R 0.278459, expectancy -0.309356R, net -6.187114R / -3420.497559USDT;
- doubled costs: WR 45%, PF_R 0.162663, net -9.243979R / -5196.618486USDT;
- gross edge is already negative before costs;
- even an optimistic 99/99 CLOSED catalog cannot satisfy CLOSED>=200.

Independent accounting/statistics/red-team/final STOP reviews and restore/resume verification PASS. This is a genuine failed qualification result for v3, not merely a technical readiness barrier.

## Active action
Follow:
- `agent_control/NEXT_TASK.md`
- `agent_control/V3_OKX_FAILURE_AUDIT_PLAN.md`
- `agent_control/CURRENT_BATCH.md`

Current work is diagnosis-only causal failure audit using frozen outputs. Priority:
1. admission scarcity through refinement/BOS/origin-bound/non-smooth-approach gates;
2. mechanics of 70 no-fill candidates;
3. negative gross-edge construction on CLOSED cases;
4. nine eligibility disagreements;
5. ranked causal redesign hypotheses.

No second v3 financial run and no in-place tuning.

After an independently frozen failure audit, automatically open a separately named new strategy version design gate if actionable causal hypotheses exist. The hard target remains WR>=70% plus positive net expectancy/P&L and all frozen cost/sample/drawdown/robustness requirements.

Platform work paused. OOS/PAPER/LIVE/private exchange API/orders prohibited. `trade_entry_allowed=false`.

Allowance policy remains serial-first: normally one specialist, hard ceiling two threads with the second only for independent verification/review.
