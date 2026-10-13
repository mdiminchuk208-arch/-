# Current State

Branch: `machine-v3-research`.

## Completed exchange-selection gate

`EXCHANGE_SELECTION_AUDIT_v1` is accepted as the authoritative completed nonfinancial architecture-selection gate.

Decision: `EXCHANGE_SELECTION_AUDIT_FROZEN_PASS`.
Freeze commit: `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`.
Namespace: `docs/exchange_selection_audit_v1/`.
Manifest SHA-256: `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`.
Final independent marker: `FINAL_REVIEW_PASS_FOR_EXCHANGE_SELECTION`.
Reconciliation record: `agent_control/EXCHANGE_AUDIT_RECONCILIATION.md`.

Frozen venue roles:
- PRIMARY_RESEARCH_VALIDATION_VENUE=Bitget (research score 82; tied with OKX, preregistered lexicographic tie-break).
- PRIMARY_EXECUTION_VENUE=BloFin (execution score 69, highest eligible).
- SECONDARY_EXECUTION_VENUE=Kraken Futures (29; tied with KuCoin and sensitive in 1/76 leave-one-snapshot cases).
- REFERENCE_BENCHMARK_VENUE=OKX (research score 82).

Audit QA: 30 targeted tests PASS; 18 derived JSON outputs replay byte-identically; 503 response receipts and 606 predecessor hashes verified; targeted math/synthesis coverage ~84.79%; final independent reviewer PASS. The inherited full suite was not rerun or claimed PASS.

The later OKX-only checkpoint is additive evidence at `docs/exchange_selection_checkpoints_v1/okx.json`, commit `0509a0d4a72a41ca9b741f5bc7dabde3f7449465`: six Stage-1 criteria PASS; ordinary API SWAP fee remains UNKNOWN. It does not alter the frozen venue roles.

## Preserved limitations

- Architecture selection is not trading readiness.
- No venue has verified historical tick/filter epochs.
- Full continuous 2–3-year executable history remains unproved.
- Current metadata must never be backdated into historical execution.
- Actual account/jurisdiction eligibility, account fee tier, collateral/mode, idempotency and protective-order behavior remain unverified.
- Bitget/Kraken book-unit caveats remain preserved.
- BloFin future execution requires one-way/reduce-only compatibility verification.
- Historical v3 financial execution remains unauthorized.
- OOS clock has not started.

## Active gate

`UNIFIED_EXCHANGE_LAYER_v1` is now open as a nonfinancial infrastructure gate.

Goal: preserve the frozen strategy core and website/product surfaces while adding venue-neutral market-data/metadata/account/order/position contracts and selected-venue adapters behind a fail-closed authorization boundary.

Execution is serial-first. `agent_control/CURRENT_BATCH.md` opens only Stage 1A: typed contract core plus deterministic disabled private/order boundary. One `exchange_adapter_architect`, medium reasoning, narrow context, STOP after commit/push. Later batches will add public Bitget/BloFin bindings, benchmark/secondary bindings, backend migration, independent review and final freeze.

## Safety state

Production candidate: NONE.
Historical financial v3 backtest ready=false and authorized=false.
OOS registration: none.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

Protected freezes remain immutable, including v3 design/implementation, metadata recovery, prospective readiness, exchange-selection audit and all earlier historical gates.
