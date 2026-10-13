# Next Task — UNIFIED_EXCHANGE_LAYER_v1 Nonfinancial Freeze

Continue from accepted `EXCHANGE_SELECTION_AUDIT_v1`:
- freeze commit `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`
- manifest SHA-256 `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`
- decision `EXCHANGE_SELECTION_AUDIT_FROZEN_PASS`
- reconciliation `agent_control/EXCHANGE_AUDIT_RECONCILIATION.md`

Selected architecture:
- research/validation: Bitget
- future execution: BloFin
- secondary execution: Kraken Futures
- benchmark: OKX

Preserve every frozen strategy and audit artifact. Do NOT redesign/tune `MACHINE_STRATEGY_v3`. Do NOT run historical strategy financial outcomes, generate OOS signals/trades, start an OOS clock, use private exchange credentials, place orders, or enable PAPER/LIVE.

## Objective
Build the narrowest venue-neutral exchange/data layer needed to move Crypto Bot toward launch without rewriting the strategy core or website/product surfaces.

The layer must provide explicit typed contracts for public market data/metadata and inert account/order/position boundaries, then bind selected venues in later staged batches. Unknown units/epochs/permissions must fail closed rather than be guessed.

## Required architecture

1. Venue-neutral exact-decimal contracts for:
   - venue/product identity;
   - candle/bar with completed/open semantics;
   - instrument metadata with tick/lot/minimum/current-known-at provenance;
   - mark/index/funding observations;
   - orderbook snapshots with explicit price/size units;
   - timestamp provenance separating exchange event/server time, receipt time, retrieved_at and known_at.

2. Inert typed contracts for:
   - account/balance;
   - order intent/state;
   - fill;
   - position;
   - margin/leverage/protective-order capabilities.

3. Authorization boundary:
   - private authentication and actual order transport are forbidden in this gate;
   - any direct private/order execution entrypoint must fail deterministically before network I/O;
   - `trade_entry_allowed=false`, PAPER=false, LIVE=false enforced at API boundaries, not only UI/CLI wrappers.

4. Selected-venue compatibility facts must remain explicit:
   - Bitget primary research;
   - BloFin future execution with one-way/reduce-only caveat;
   - Kraken Futures conditional secondary with USD multi-collateral/product differences;
   - OKX benchmark with ordinary API SWAP fee still unresolved;
   - no historical tick/filter epochs are to be invented or backdated.

5. Public adapters in later batches must use pinned exchange-audit receipts first and bounded new public probes only when a concrete contract gap requires them. No alternate routing to evade 403/451 restrictions.

6. Existing website/product surfaces should remain exchange-agnostic behind this layer: Dashboard, Scanner, Portfolio, Journal, Stats, Backtest UI, Settings, alerts, Audit Log, Safe Mode, STOP AUTO TRADING and CLOSE ALL.

## Required namespace
Create `docs/unified_exchange_layer_v1/` and progressively populate:
- `UNIFIED_EXCHANGE_LAYER_SPEC.md`
- contract/schema registry
- `VENUE_BINDINGS.json`
- `COMPATIBILITY_GAPS.json`
- `PUBLIC_ADAPTER_EVIDENCE.json`
- `AUTHORIZATION_BOUNDARY.md`
- `BACKEND_MIGRATION_MAP.md`
- `CONTROL_PLANE_MIGRATION_PLAN.md`
- `CAUSALITY_AND_REPLAY_REPORT.md`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- machine-readable QA receipt
- `freeze_manifest.json`

## QA requirements
By final freeze, cover at minimum:
- exact decimal/tick/lot handling;
- product/unit mismatch rejection;
- unknown-unit/unknown-epoch fail-closed;
- completed-bar and known_at causality;
- timestamp-domain separation;
- deterministic fixture replay;
- source/hash consistency;
- HTTP/application error handling for public adapters;
- direct private/order calls fail before network side effects;
- no strategy runner/OOS/PAPER/LIVE invocation;
- protected frozen artifacts invariant;
- Ruff/format, mypy and compile for new code;
- independent reviewer PASS.

Do not claim inherited full-suite PASS unless actually run and safe; preserve prior documented phase-pinned failures.

## Workflow / allowance policy
Execution is SERIAL-FIRST:
- normally one active specialist;
- hard ceiling two threads, second only for independent verification/review;
- medium reasoning for routine implementation/collection;
- high reasoning only for critical final review if needed;
- narrow context and checkpoint every batch;
- never launch the full configured agent catalog mechanically.

`agent_control/CURRENT_BATCH.md` is authoritative for the currently allowed subset. Do not execute later stages automatically.

## Decision
Final gate may publish only:
- `UNIFIED_EXCHANGE_LAYER_FROZEN_PASS`, or
- `UNIFIED_EXCHANGE_LAYER_FROZEN_STOP` with exact blockers.

PASS opens a separate venue-specific v3 compatibility freeze. It does NOT authorize financial evaluation, OOS, PAPER or LIVE.

`trade_entry_allowed=false` remains invariant.
