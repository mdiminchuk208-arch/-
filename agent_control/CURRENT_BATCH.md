# Current Campaign — v3 OKX Failure Audit → New Version Design

The first preregistered OKX financial development run is frozen STOP. v3 is financially failed for the current qualification policy; do not rerun it or tune it in place.

Use `agent_control/NEXT_TASK.md` and `agent_control/V3_OKX_FAILURE_AUDIT_PLAN.md` as the active instructions.

## Frozen result
- 99 unique candidates total;
- 20 all-nine CLOSED;
- 70 all-scenario no fill;
- 9 eligibility disagreements;
- known CLOSED base WR 50%, PF_R 0.278459, net -6.187114R;
- doubled-cost WR 45%, PF_R 0.162663, net -9.243979R;
- gross edge already negative;
- fixed catalog cannot satisfy CLOSED>=200.

## Active work
Perform diagnosis-only causal failure audit from existing frozen outputs. No second v3 financial run.

Priority order:
1. unique-origin admission scarcity, especially refinement/BOS/origin-bound/non-smooth-approach gates;
2. exact mechanics of 70 no-fill candidates;
3. gross-edge decomposition of CLOSED cases;
4. exact causes of nine compatibility eligibility disagreements;
5. ranked causal redesign hypotheses for the next version.

Use specialists serially and only as needed: strategy_explorer → execution_auditor → backtest_reviewer/statistics_robustness_analyst → final_independent_reviewer. Root is sole writer. Hard ceiling two threads, second only for independent review.

Create and freeze `docs/machine_strategy_v3_okx_failure_audit_v1/` per the audit plan.

## Autonomous transition
Once failure audit is independently frozen, if actionable causal hypotheses exist, immediately open a separately named new strategy version design gate (v3.1 or v4) without asking the user. Freeze the new design before any financial outcome. The new version must still target WR>=70% plus all existing net-edge/sample/cost/robustness criteria.

Do not relax thresholds, cherry-pick small positive slices, ban SHORT based on the failed sample, remove adverse cases, or optimize numeric thresholds against observed P&L.

No OOS/PAPER/LIVE/private exchange API/orders/platform work. `trade_entry_allowed=false`.
