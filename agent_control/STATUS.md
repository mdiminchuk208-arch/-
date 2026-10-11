# Agent Status

State: V3_PRE_OUTCOME_DESIGN_TASK_OPEN

Branch: `machine-v3-research`.

Failure audit is frozen and immutable.
- Audit commit: `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- Published audit head: `d143bb9d8aee44e0a40cef653fec07e7d1df7243`
- Audit namespace: `docs/machine_strategy_failure_audit_v1/`
- Audit QA: PASS (963 tests + independent review)

The next authorized task is now `agent_control/NEXT_TASK.md`: design and freeze a separate `MACHINE_STRATEGY_v3` specification before any new financial backtest.

Required design principles:
- do not disable SHORT merely because v2 SHORT lost money;
- do not mine profitable subgroups;
- redesign direction/context symmetrically;
- address structurally tiny risk denominators and cost/R instability;
- address entry/nearest-FTA economics without moving targets to manufacture R:R;
- preserve causal timestamps and explicit intrabar uncertainty;
- preregister dataset exposure and genuinely untouched OOS before the first v3 outcome;
- freeze every v3 rule before viewing aggregate v3 P&L.

Required roles for this phase: strategy_explorer, execution_auditor, strategy_designer, backtest_reviewer.

No v3 financial result is authorized in this phase.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
