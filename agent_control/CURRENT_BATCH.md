# Current Batch — UNIFIED_EXCHANGE_LAYER_v1 Stage 1A

Execute only this batch, commit/push, then STOP. Do not continue automatically into venue adapters or later stages.

## Scope
Build the venue-neutral contract core and deterministic fail-closed authorization boundary only.

Use exactly one `exchange_adapter_architect` specialist. No parallel subagents. Medium reasoning. Narrow context: `agent_control/NEXT_TASK.md`, accepted exchange-selection role decisions, timestamp follow-up, existing relevant exchange/v3 contract interfaces, and this batch. Do not load or inspect historical strategy financial outputs.

## Required work

1. Inspect the existing code structure and add the narrowest new versioned module/package for unified exchange contracts without modifying frozen `MACHINE_STRATEGY_v3` modules.

2. Implement typed exact-decimal contracts for at least:
   - Venue/Product identity;
   - Candle/bar with completed flag and open/event/known-at provenance;
   - Instrument metadata with tick size, lot size, minimums, unit semantics and current-known-at provenance;
   - Mark/index/funding observation;
   - Orderbook snapshot with explicit price and size units;
   - Timestamp provenance separating exchange event/server time, retrieved/receipt time and known_at.

3. Implement inert typed private-domain contracts for:
   - account/balance;
   - order intent/state;
   - fill;
   - position;
   - margin/leverage/protective-order capability descriptors.

4. Implement a deterministic authorization boundary so any private/order execution entrypoint fails before network I/O while:
   - `trade_entry_allowed=false`;
   - PAPER=false;
   - LIVE=false.

Do not create usable signing/auth clients and do not call any private exchange API.

5. Add focused tests for:
   - exact Decimal preservation;
   - product/unit mismatch rejection;
   - unknown unit/epoch fail-closed;
   - timestamp-domain separation and known_at ordering;
   - incomplete-bar handling;
   - direct private/order invocation denied with zero network side effects.

6. Create/update only Stage-1A documentation under `docs/unified_exchange_layer_v1/`:
   - `STAGE1A_CONTRACT_CORE.md`
   - `AUTHORIZATION_BOUNDARY.md`
   - `STAGE1A_QA_RECEIPT.json`

Record files changed, tests run and exact PASS/STOP. Reuse frozen exchange audit facts; no new venue research or HTTP probes in this batch.

## Mandatory stop conditions

STOP after Stage 1A commit/push. Do not implement Bitget/BloFin/OKX/Kraken adapters yet. Do not touch strategy rules. Do not run historical v3 financial execution, OOS, PAPER or LIVE.

If implementation exposes a blocker, publish an honest Stage-1A STOP with the narrowest blocker and completed safe artifacts rather than widening scope.

`trade_entry_allowed=false` remains invariant.
