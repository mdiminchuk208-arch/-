# Next Task — UNIFIED_EXCHANGE_LAYER_v1 Nonfinancial Freeze

Continue from the completed EXCHANGE_SELECTION_AUDIT_v1 freeze recorded with exact commit/manifest in STATUS.md and CURRENT_STATE.md. Verify that manifest with the audit builder's externally pinned --resume-existing before consuming its evidence. Do not restart the exchange audit or alter any frozen artifacts.

## Objective and limits

Implement the next launch-directive step: a venue-neutral public market-data/metadata layer plus explicit account/order/position contracts, preserving the website and frozen strategy core. This gate is infrastructure only. It must not interpret historical strategy financial outcomes, execute the v3 runner, produce signals/trades, start an OOS clock, or qualify a venue/account for trading.

Selected architecture: Bitget primary research, BloFin future execution, Kraken Futures conditional secondary, OKX benchmark. Research Bitget/OKX ties at 82; secondary Kraken/KuCoin ties at 29 and flips under one shallow-book removal. Those caveats stay explicit. Bitget/Kraken book denomination is unproven; unknown book units must fail closed for executable depth. Kraken PF USD multi-collateral differs from USDT-linear venues. No venue has complete historical tick epochs or audited continuous 2–3-year candles. Architecture PASS does not resolve predecessor readiness STOP.

## Scope

1. Inspect existing interfaces/services and retain all frozen adapter/runner bytes. Add the narrowest new namespace/module version needed; do not rewrite frozen v3 modules or strategy rules.
2. Specify typed venue-neutral product identity, candle, mark/index, funding, instrument metadata and orderbook contracts using exact decimal values. Represent venue/product/margin/settlement, price/quantity units, tick/lot/minimum rules, source URL/hash, event/effective/known_at/retrieved_at times and completed-bar semantics explicitly. Unknown historical epochs remain unknown, never replaced by current filters. Version schema and normalization assumptions.
The audit timestamp follow-up at docs/exchange_selection_audit_v1_followup/TIMESTAMP_SEMANTICS_NOTE.md is mandatory input: Kraken CI normalized time_utc uses receipt completion despite retained ISO serverTime. The new contracts must distinguish exchange/server time from request/receipt/known_at and test that distinction; preserve the frozen audit parser.

3. Implement bounded public-only adapters for Bitget and BloFin BTC/ETH linear perpetual metadata and native M15 data. Add OKX benchmark public metadata/candle binding and Kraken PF conditional identity binding where supported. Reuse pinned fixtures from exchange selection; bounded new public probes only if a concrete contract gap requires them. Preserve HTTP/API errors and application codes. Do not retry blocked routes through alternate routing.
4. Define venue-neutral account, balance, order intent/state, fill and position interfaces as inert typed contracts. Private authentication, credentials and actual account/order transport are forbidden in this gate. All private or order execution entrypoints must raise a deterministic disabled/unauthorized error before any network operation. Do not construct usable secret/signing clients. Enforce trade_entry_allowed=false, PAPER=false and LIVE=false at API boundaries; test direct invocation, not only CLI wrappers.
5. Distinguish venue observations from strategy assumptions. Keep compatibility placeholders explicit: BloFin one-way reduce-only requirement; account-tier fees and jurisdiction unverified; durable client-ID idempotency and exchange-side protective behavior not validated; Bitget/Kraken book denomination unresolved. No guessed unit multipliers in executable books. Exact lot/price-grid arithmetic must use documented current rules and carry provenance/known_at.
6. Define retry/rate-limit/timeouts, response identity checks, monotonic timestamp validation, fail-closed stale/incomplete metadata handling and append-only evidence output. No daemon, cron, 365-day registration, retrospective-to-OOS relabeling, or financial data scan. A short bounded contract smoke probe is not prospective OOS.
7. Define exchange-agnostic backend boundaries for existing product surfaces without changing website behavior or generating simulated financial values. Include migration map and safety/authorization boundary. Avoid broad UI work in this gate.
8. Record a control-plane migration plan for prior phase-pinned header tests. Preserve archived pinned tests and prior STOP; create new active version tests only where required by the new interface. Do not claim the inherited full suite PASS if its documented failures remain. A full repair/registration gate is separate if needed.

## Required artifacts

Create docs/unified_exchange_layer_v1/ with:
- UNIFIED_EXCHANGE_LAYER_SPEC.md and typed schema/contract registry;
- VENUE_BINDINGS.json and COMPATIBILITY_GAPS.json;
- PUBLIC_ADAPTER_EVIDENCE.json with source receipts or references into the pinned audit;
- AUTHORIZATION_BOUNDARY.md and BACKEND_MIGRATION_MAP.md;
- CONTROL_PLANE_MIGRATION_PLAN.md;
- CAUSALITY_AND_REPLAY_REPORT.md;
- INDEPENDENT_REVIEW.md;
- QA_REPORT.md, machine-readable QA receipt and freeze_manifest.json.

Keep all implementation/tests/scripts. Add a deterministic builder/resume validator that requires a supplied manifest hash, checks exact namespace membership and hashes, and refuses mutation of an existing freeze. Include protected predecessor hashes and new code/config/test hashes; no self-referential commit SHA inside a commit. STATUS/CURRENT_STATE carry the resulting exact freeze commit and manifest.

## Workflow and QA

Use ECC role instructions and the current allowance-saving policy in LAUNCH_DIRECTIVE.md: normal 2–3 active agents, hard ceiling four total threads, at most two venue collectors. Reuse existing receipts; use narrow context and sequential reviewer batches. Root is sole implementation writer. Involve exchange_adapter_architect/platform_backend_architect for scoped interface analysis, and an independent execution/risk or final reviewer who did not author implementation. Merge functions under one identity when competent; record actual identities and scope. No mechanical launch of all roles.

Required checks: exact decimal/tick/lot contract tests; product and unit mismatch rejection; unknown-unit/epoch fail-closed; completed-bar and known_at causality; prefix/future-input mutation for the new nonfinancial transformations; deterministic fixture replay byte-identical; source/hash consistency; HTTP/application error handling; denied private/order direct calls with zero network side effects; no OOS/strategy runner invocation; protected frozen artifacts invariant; Ruff/format, mypy and compile for new code. Run existing relevant interface tests where safe, distinguish targeted/new PASS from inherited unrun/failing suite. Never run legacy tests that print strategy financial outputs to satisfy a blanket suite claim.

Obtain independent review, freeze exact bytes, update STATUS/CURRENT_STATE and next narrowest gate under the launch directive, commit and push machine-v3-research without force. On external evidence blockers, publish honest STOP with exact gaps and useful completed artifacts; do not fabricate proof.

## Decision

Publish UNIFIED_EXCHANGE_LAYER_FROZEN_PASS only for a reproducible nonfinancial layer whose private/order boundary fails closed and whose bindings retain all uncertainties. Otherwise UNIFIED_EXCHANGE_LAYER_FROZEN_STOP. PASS opens venue-specific v3 compatibility specification/freeze, not financial evaluation, actual orders or OOS registration.

PAPER/LIVE and private exchange APIs are forbidden. Historical financial v3 execution remains unauthorized. trade_entry_allowed=false. No strategy tuning or changes to frozen namespaces.
