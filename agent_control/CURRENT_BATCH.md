# Current Campaign — MACHINE_STRATEGY_v4 Design Review / Freeze

v3 is frozen failed. v4 design draft is complete and no v4 financial result exists.

## Active batch
Independent review and freeze only. Execute `agent_control/NEXT_TASK.md` against `docs/machine_strategy_v4_design_v1/`.

Review the complete v4 draft for deterministic causality, provenance classification, LONG/SHORT symmetry, setup-family preservation, outcome isolation, cost/compatibility consistency and absence of exposed-PnL parameter selection.

Required review sequence is serial: execution audit -> causality/backtest review -> final independent review. Root is the only writer; hard ceiling root + one specialist.

Publish exactly one design decision:
- `MACHINE_STRATEGY_V4_DESIGN_PASS`
- `MACHINE_STRATEGY_V4_DESIGN_STOP`

PASS must create `DESIGN_FREEZE_MANIFEST.json` with pinned design artifacts/hashes and open implementation readiness. STOP must name the narrow defect and preserve all qualification criteria.

No v4 historical financial run in this batch. No v3 rerun. No OOS/PAPER/LIVE/private API/orders/platform work. `trade_entry_allowed=false`.
