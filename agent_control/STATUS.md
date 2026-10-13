# Agent Status

State: EXCHANGE_SELECTION_AUDIT_V1_STAGE_1A_OKX_OPEN
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

## Active exchange-selection gate
The full frozen requirements remain in `agent_control/NEXT_TASK.md`; the preregistered scoring/probe protocol remains unchanged at `docs/exchange_selection_audit_v1/SCORING_PREREGISTRATION.json` (SHA-256 `ab7add22e1ab5efd543499729c431e03fda1fd6f213063c94bbbf6614e9ce699`).

The active scope is the latest OKX-only Stage 1A batch. Prior unsynchronized work is preserved, not rerun or used to bypass this batch stop.

### Current batch — OKX only
`agent_control/CURRENT_BATCH.md` requires exactly:
1. one `venue_researcher`;
2. OKX hard-gate triage only;
3. medium reasoning, narrow context, no parallel subagents;
4. durable `docs/exchange_selection_checkpoints_v1/okx.json` (preservation-safe physical location; see CURRENT_BATCH);
5. push checkpoint + status and STOP before Binance or any other venue.

If access/environment prevents completion, record evidence/blocker, push the partial checkpoint, and stop rather than broad retry/research.

No strategy financial outcome may be run/read. No prospective OOS clock may start. No PAPER/LIVE. Protected freezes remain immutable.

Historical financial backtest ready=false and authorized=false.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

## Preserved earlier attempt — not the active next gate

Before receipt of remote scope change `4435687`, the resumed older task produced audit freeze commit `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`, manifest `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`, plus additive timestamp note/review. Its internal decision is conditional architecture PASS, with 30 targeted tests and 18-output replay. These bytes and all prior evidence are preserved. No new ranking/review is run by the current OKX batch, and the prior proposed Unified Exchange Layer gate is NOT open under the newly received batch directive. The full audit result awaits reconciliation with the current serial runbook; no trading or financial authorization follows from it.

The requested checkpoint directory was inside this already-sealed exact-membership namespace. To preserve the immutable freeze, the same OKX checkpoint is stored at `docs/exchange_selection_checkpoints_v1/okx.json`; CURRENT_BATCH records this mechanical location adjustment. No source/scoring rule is changed.
