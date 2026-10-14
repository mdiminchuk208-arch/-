# Current Campaign — MACHINE_STRATEGY_v4 Pre-outcome Design

The v3 OKX failure audit is independently complete, frozen and published: `54419daa29e7e68d6f692daee9cf2132203393ef`, manifest `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`. v3 remains QUALIFICATION_STOP.

## Active batch
Execute `agent_control/V4_DESIGN_WORK_ORDER.md` completely together with `docs/machine_strategy_v4_design_v1/DESIGN_GATE_PROTOCOL.md` and pinned `DESIGN_INPUTS.json`.

The design must directly address the two verified failure classes without selecting rules from exposed historical P&L:
- scarcity/over-filtering: only 99 candidates in two development years; 10,511/11,947 raw formations terminated at the early non-smooth/opposing-BOS veto;
- construction/payoff weakness: known CLOSED gross edge already negative, target/stop geometry poor, wins much smaller than losses.

Mandatory decision families: H00 telemetry, H01 structural-approach semantics, H02 completed-mark/FTA lifecycle, H03 resting-entry validity/lifetime, H04 structural-vs-executable zone, H05 pre-entry structural payoff/anti-scalp feasibility. Each must be ADOPTED/DEFERRED/REJECTED with causal reasoning, source/policy classification, deterministic machine semantics and LONG/SHORT mirror.

## Workflow
Serial only: `strategy_designer` → `execution_auditor` → `backtest_reviewer`/`no_lookahead_auditor` → `final_independent_reviewer`. Root is sole writer; hard ceiling root + one specialist.

Produce the complete v4 design namespace and synthetic QA. Freeze exactly one decision:
- `MACHINE_STRATEGY_V4_DESIGN_PASS`
- `MACHINE_STRATEGY_V4_DESIGN_STOP`

On DESIGN_PASS, open a separately named v4 implementation/readiness gate. Do not run v4 historical financial outcomes in this batch.

Qualification remains unchanged: WR>=70% plus all prior net-edge, PF, sample, drawdown, doubled-cost, concentration, causality and robustness requirements.

No v3 rerun/edit, no historical optimization, no OOS execution, PAPER/LIVE/private API/orders/platform work. `trade_entry_allowed=false`; hooks inactive.
