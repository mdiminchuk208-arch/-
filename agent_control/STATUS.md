# Agent Status

State: UNIFIED_EXCHANGE_LAYER_V1_STAGE_1A_OPEN
Branch: `machine-v3-research`.

Latest completed gate: `EXCHANGE_SELECTION_AUDIT_v1`.
Decision: `EXCHANGE_SELECTION_AUDIT_FROZEN_PASS` — conditional nonfinancial architecture selection only.
Freeze commit: `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`.
Manifest SHA-256: `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`.
Final independent marker: `FINAL_REVIEW_PASS_FOR_EXCHANGE_SELECTION`.
Reconciliation: `agent_control/EXCHANGE_AUDIT_RECONCILIATION.md`.

Frozen venue roles:
- PRIMARY_RESEARCH_VALIDATION_VENUE=Bitget
- PRIMARY_EXECUTION_VENUE=BloFin
- SECONDARY_EXECUTION_VENUE=Kraken Futures
- REFERENCE_BENCHMARK_VENUE=OKX

The later OKX-only Stage-1 checkpoint is preserved at `docs/exchange_selection_checkpoints_v1/okx.json`, commit `0509a0d4a72a41ca9b741f5bc7dabde3f7449465`. Six criteria PASS; ordinary API SWAP fee remains UNKNOWN. It is additive evidence and does not alter the frozen role selection.

Allowance policy is SERIAL-FIRST:
- default one active specialist;
- hard ceiling two threads, second only for independent verification/review;
- routine collection/implementation uses medium reasoning unless a critical review needs high;
- narrow context, reuse frozen evidence, checkpoint every batch;
- do not launch all configured roles.

## Active gate
`UNIFIED_EXCHANGE_LAYER_v1` — nonfinancial infrastructure only.

Current batch is `agent_control/CURRENT_BATCH.md` Stage 1A: venue-neutral contract core and fail-closed authorization boundary only. One `exchange_adapter_architect`, no venue research, no private exchange calls, no strategy financial execution. Stop after the Stage-1A commit/push.

Frozen `MACHINE_STRATEGY_v3` rules and prior gate namespaces remain immutable. No strategy tuning or redesign.

Historical financial v3 backtest ready=false and authorized=false.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
