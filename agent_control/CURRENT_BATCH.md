# Current Campaign — MACHINE_STRATEGY_v4 Pre-outcome Design

The v3 OKX failure audit is independently complete, frozen and published: `54419daa29e7e68d6f692daee9cf2132203393ef`, manifest `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`. Its new-version hypotheses are conditional; v3 remains QUALIFICATION_STOP.

Current gate: DESIGN_GATE_OPEN. Follow NEXT_TASK.md and docs/machine_strategy_v4_design_v1/DESIGN_GATE_PROTOCOL.md. Design has not been completed, implemented, frozen or financially tested.

Serial strategy_designer → execution_auditor → backtest_reviewer → final_independent_reviewer; root is sole writer, hard ceiling two threads. Preserve all frozen predecessors. Register causal choices before outcomes and do not fit to historical P&L. Qualification remains WR>=70% plus all prior cost/sample/net-edge/robustness requirements.

No new historical strategy/financial run, OOS execution, PAPER/LIVE/private API/orders/platform work. trade_entry_allowed=false; hooks inactive.
