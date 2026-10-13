# Agent Status

State: EXCHANGE_SELECTION_AUDIT_V1_STAGE_1A_OPEN
Branch: `machine-v3-research`.

Latest completed gate: MACHINE_STRATEGY_v3 Prospective Data/Metadata Capture + OOS Registration Readiness Freeze.
Completed decision: `V3_PROSPECTIVE_READINESS_FROZEN_STOP`.
Prospective freeze commit: `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`.
Namespace: `docs/machine_strategy_v3_prospective_readiness/`.
Manifest SHA-256: `b96797ec01575303b6d4c0170f0683554386f53569ef41ad38ed3f91cf7fe45d`.

Primary project directive remains launch-first: earliest safe evidence-backed Crypto Bot launch, with frozen `MACHINE_STRATEGY_v3` rules preserved and no speculative strategy redesign during the launch path.

## Allowance policy
The orchestration catalog still contains 22 specialist roles, but execution is SERIAL-FIRST:
- default one active specialist at a time;
- hard concurrency ceiling two agent threads;
- second thread only for genuinely independent verification/review;
- at most one `venue_researcher` at a time;
- routine collection medium reasoning with narrow context;
- high reasoning reserved for critical synthesis/audit/red-team/final-review work;
- durable checkpoints prevent repeated evidence collection.

This supersedes all earlier 4/8/16-thread policies after observed disproportionate Work/Codex allowance consumption.

## Active exchange-selection gate
The full frozen requirements remain in `agent_control/NEXT_TASK.md` and the preregistered scoring/probe protocol remains unchanged:
`docs/exchange_selection_audit_v1/SCORING_PREREGISTRATION.json`, SHA-256 `ab7add22e1ab5efd543499729c431e03fda1fd6f213063c94bbbf6614e9ce699`.

Execution is now staged by `agent_control/EXCHANGE_AUDIT_RUNBOOK.md` to reduce allowance without weakening final independent verification.

### Current batch
`agent_control/CURRENT_BATCH.md` opens Stage 1A only:
1. OKX hard-gate triage;
2. Binance Futures hard-gate triage;
3. one `venue_researcher`, sequentially, medium reasoning;
4. checkpoint each venue under `docs/exchange_selection_audit_v1/checkpoints/`;
5. stop after Stage 1A and do not automatically continue into more venues.

If allowance pressure or a blocker appears after OKX, persist the OKX checkpoint and stop rather than repeating work.

No interrupted cloud result is treated as frozen evidence. No strategy financial outcome may be run/read. No prospective OOS clock may start until exchange selection is frozen and a later capture-registration gate explicitly opens it.

Protected freezes remain immutable:
- baseline `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation `43e57ee5c7867dd9421961629746555c8a2e9556`
- v3 metadata recovery `7e89543ef9b443ac65b64f125c919e885dccf37b`
- v3 prospective readiness `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`

Historical financial backtest ready=false and authorized=false.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
