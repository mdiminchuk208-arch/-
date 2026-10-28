# Crypto Bot — Implementation Status — 2026-10-28

## Executive state

The repository now contains a complete fail-closed infrastructure path from verified OKX public market data to deterministic PURE SOURCE diagnostics and durable backend handoff contracts.

Current canonical boundary remains unchanged:

- PURE SOURCE baseline: `NOT_IDENTIFIABLE` as one unique executable financial strategy;
- `trade_entry_allowed=false`;
- financial PURE SOURCE backtest/PAPER/LIVE remains unauthorized;
- no private OKX order API exists in this runtime;
- PROJECT policy cannot resolve SOURCE ambiguity;
- TradingView is QA-only and optional.

Latest validated head before this status document: `6f0c382fda27de5fe3d38f00712c79199b0eacb4`.

GitHub Actions result on that head:

- project install: PASS;
- compile all Python: PASS;
- full unit suite: PASS;
- safety invariant: PASS.

---

## 1. Completed — OKX market-data foundation

### Implemented

- public OKX V5 REST adapter;
- Global default REST domain `https://openapi.okx.com`;
- configurable regional REST domain for EEA/US/AU registrations;
- canonical intervals including 5m / 15m / H1 / H4 / D1;
- D1 mapped to `1Dutc`;
- exchange-authoritative closed-candle handling using `confirm`;
- backward historical pagination;
- public instrument metadata;
- deterministic dataset manifests;
- content SHA-256 and dataset identity;
- CSV persistence;
- gap/duplicate/continuity/coverage QA;
- replay-eligibility verification gate;
- verified MTF history downloader/CLI.

### Safety properties

- unfinished candle cannot enter deterministic canonical replay;
- dataset hash mismatch fails closed;
- internal gaps fail closed;
- identity mismatch fails closed;
- Bybit remains legacy/historical, not production transport.

---

## 2. Completed — verified history -> PURE SOURCE diagnostics

Implemented verified dataset loader into the existing causal replay path.

Canonical diagnostic path:

`verified CSV+manifest -> ReplaySeries -> Stage 14 execution replay -> Stage 15 diagnostic artifact`

The diagnostic artifact preserves:

- dataset identity;
- causal receipts;
- provider/version identity;
- unresolved SOURCE reasons;
- deterministic artifact fingerprint;
- `financial_run=false`;
- `trade_entry_allowed=false`.

No PnL optimization is used to resolve SOURCE branches.

---

## 3. Completed — live/restart-safe public-data runtime

### Durable live candle feed

Implemented:

- atomic durable candle cursors;
- first-start historical baseline protection;
- explicit commit after downstream success;
- at-least-once replay after crash;
- paginated catch-up after long outage;
- page ceiling;
- exact continuity verification from durable cursor;
- missing live closed bar -> fail closed.

### Durable MTF state

Implemented SQLite MTF state for configured timeframes:

- closed candles only;
- strict market identity;
- aligned timestamps;
- no silent mutation of an existing closed candle;
- exact duplicate is idempotent;
- out-of-order unknown candle fails;
- continuity gap fails;
- restart-safe;
- no arbitrary rolling history truncation in canonical path.

The no-truncation decision is deliberate: an arbitrary live lookback would become an unclassified strategy parameter.

### Verified bootstrap

Live MTF state can be seeded only from verified historical CSV+manifest pairs.

Repeated bootstrap is idempotent.

---

## 4. Completed — live PURE SOURCE diagnostic service

Implemented a composed service cycle:

`verified MTF state -> reconcile cursor -> OKX catch-up -> durable MTF ingest -> Stage 14/15 diagnostic -> outbox -> health`

Important invariants:

- cursor missing + durable verified MTF exists -> cursor starts at durable MTF head, then catches up every closed candle;
- cursor behind MTF -> exact duplicates replay idempotently;
- cursor ahead of MTF -> fail closed;
- cursor never advances before durable MTF acceptance;
- unchanged cycle does not manufacture a new diagnostic event;
- diagnostic artifact remains non-financial and non-executable.

Executable CLI:

`scripts/run_okx_live_diagnostic_service.py`

---

## 5. Completed — operational health / safe mode

Implemented runtime states:

- `STARTING`;
- `HEALTHY_DIAGNOSTIC`;
- `DEGRADED`;
- `SAFE_MODE`.

Health checks cover:

- MTF readiness;
- per-timeframe stale market data;
- durable outbox backlog;
- diagnostic pipeline availability.

Any stale configured market timeframe enters SAFE_MODE.

Health snapshots always preserve `trade_entry_allowed=false`.

Atomic durable receipt:

`health.json`

Health-check CLI:

`scripts/check_live_diagnostic_health.py`

---

## 6. Completed — 24x7 deployment packaging

### Docker

Added:

- `Dockerfile.live-diagnostic`;
- `compose.live-diagnostic.yml`.

Properties:

- non-root runtime;
- read-only container filesystem;
- verified historical data mounted read-only;
- persistent runtime state volume;
- dropped Linux capabilities;
- `no-new-privileges`;
- tmpfs `/tmp`;
- runtime healthcheck;
- restart policy;
- no private OKX credentials.

### systemd

Added hardened unit:

`deploy/systemd/crypto-bot-live-diagnostic.service`

Properties include:

- dedicated `cryptobot` account;
- strict filesystem protection;
- only `/var/lib/crypto-bot` writable;
- no ambient/capability bounding permissions;
- restart on failure.

### Runbook

`LIVE_DIAGNOSTIC_RUNBOOK.md`

covers verified history preparation, smoke tests, Docker, systemd, restart recovery and incident handling.

---

## 7. Completed — Strategy Engine -> backend transport contract

### Immutable object snapshot

Implemented outward `StrategyObjectSnapshot`:

- causal timestamps;
- SOURCE rule IDs;
- provenance;
- branch/evidence IDs;
- engine/git/dataset identity;
- optional geometry only when actually supplied;
- separate `trade_eligible` vs financial `trade_entry_allowed`;
- financial permission fixed false.

### SOURCE execution snapshot

Implemented `SourceExecutionPlanSnapshot` that preserves all SOURCE-permitted alternatives:

- entry options;
- stop options;
- exit policy;
- unresolved reasons;
- source geometry resolution state.

It does not rank alternatives and does not invent one Entry/SL/TP.

Both outward contracts now emit JSON-native arrays/objects so persisted API payloads have stable semantics.

---

## 8. Completed — durable engine outbox and delivery

### SQLite outbox

Implemented:

- idempotent event insertion;
- event-ID collision rejection;
- ordered pending reads;
- durable retry count/error;
- explicit delivery acknowledgement;
- restart persistence.

### HTTP delivery worker

Implemented optional backend transport:

- backend endpoint must be explicitly configured;
- HTTPS required outside explicit localhost development;
- optional bearer authentication;
- exact event envelope;
- `Idempotency-Key`;
- only 2xx acknowledges an event;
- network/non-2xx leaves event pending;
- ordered delivery stops on first failed event.

CLI:

`scripts/deliver_engine_outbox.py`

No fake production backend URL is embedded in the repository.

---

## 9. Completed — backend receiver / PostgreSQL contract

### Receiver validation

Generic receiver contract rejects:

- missing/unknown envelope fields;
- naive timestamps;
- identity/schema mismatches;
- non-object payloads;
- **any recursive `trade_entry_allowed=true`**.

### Deterministic ingestion decision

Implemented:

- canonical payload JSON;
- canonical SHA-256;
- `FIRST_ACCEPTED`;
- `EXACT_DUPLICATE`;
- `COLLISION`.

Exact duplicate is idempotent success. Immutable mismatch is a collision and must not overwrite history.

### PostgreSQL migration

Added:

`deploy/postgres/001_engine_events.sql`

Includes:

- append-only `engine_events`;
- `event_id` primary key;
- JSONB payload;
- payload SHA-256;
- immutable timestamps;
- UPDATE/DELETE rejection triggers;
- separate mutable `engine_event_receipts` table.

Detailed contract:

`BACKEND_ENGINE_EVENT_CONTRACT.md`

No HTTP route or web framework is invented because the actual Platform/Backend code is not present in this repository.

---

## 10. Completed — explicit PROJECT risk gate

Implemented separately from PURE SOURCE:

- explicit policy object with no hidden defaults;
- exact proposal fingerprint;
- deterministic PASS/BLOCK;
- machine reason codes;
- per-trade risk;
- total portfolio risk;
- daily loss;
- leverage;
- margin budget;
- concurrent positions;
- stale data;
- duplicate proposal;
- extension point for explicit PROJECT guards such as correlation.

Any proposal change creates a new fingerprint and requires revalidation.

A PROJECT risk PASS does **not** grant financial execution permission.

---

## 11. Completed — optional TradingView visual QA sidecar

Reference project: `tradesdontlie/tradingview-mcp`.

Implemented an optional local QA adapter under:

`src/crypto_bot/qa/tradingview.py`

Properties:

- not imported by production live runtime;
- explicit TradingView ticker required; no silent OKX -> TradingView mapping;
- deterministic case/plan fingerprint;
- allowed commands limited to connection status, symbol/timeframe navigation, replay start/status/stop, OHLCV summary and screenshot;
- `replay trade` is forbidden;
- QA receipt always has `trade_entry_allowed=false`.

CLI:

`scripts/run_tradingview_qa.py`

Default mode is `PLAN_ONLY`.

Local TradingView control requires explicit `--execute`.

TradingView Desktop/CDP remains optional QA tooling and is not a production dependency or SOURCE authority.

---

## 12. CI / repository quality state

GitHub Actions workflow now uses concurrency cancellation so obsolete validations are cancelled when a newer main head exists.

Validation runs perform:

1. project install;
2. Python compile;
3. full unit suite;
4. explicit safety grep/invariant against `trade_entry_allowed=True` in runtime code.

Deployment-contract tests also enforce key PostgreSQL/Docker/systemd safety properties.

---

# Remaining work by category

## A. SOURCE work — BLOCKED BY SOURCE EVIDENCE, not engineering convenience

Still unresolved by the authoritative SOURCE material/current provenance state:

- source-qualified annotations for remaining qualitative concepts;
- remaining migration/qualification of OB/Breaker, Range/OTE, STB/BTS and Demand/Supply consumers;
- exact quote inside some POI variants;
- exact beyond-anchor stop buffer/protective geometry where SOURCE does not uniquely determine it;
- partial FTA/remainder lifecycle;
- re-entry identity/eligibility details;
- context selection among multiple valid timeframes/liquidity pools.

These must not be guessed by external strategy skills, TradingView visual judgment, PnL or PROJECT optimization.

## B. Platform/Backend application — EXTERNAL SOURCE CODE REQUIRED

The event schema, delivery worker, receiver validation and PostgreSQL migration are ready.

Still missing from this repository:

- actual Platform/Backend web application source;
- chosen HTTP ingestion route;
- actual PostgreSQL connection/runtime;
- UI read-model integration;
- replacement of PRE_STRATEGY / NOT_CONNECTED UI states with engine event data;
- browser/API end-to-end validation against that application.

Do not implement a fake Platform route in this repository. Bring the real Platform/Backend source under GitHub source-of-truth, then wire the prepared contracts.

## C. VPS / staging / production — EXTERNAL INFRASTRUCTURE REQUIRED

Packaging is ready, but actual deployment requires a reachable host/runtime controlled by the project.

Still external:

- VPS/container host access;
- persistent storage provisioning;
- runtime user/directories;
- staging deployment;
- monitoring hookup;
- production deployment;
- stored staging/production smoke receipts.

The local PC should not be required once this deployment is installed on the external host.

## D. Backend delivery — WAITING FOR REAL ENDPOINT

The sender is complete but intentionally disabled until the real backend ingestion endpoint is defined.

Once available, configure:

- HTTPS endpoint;
- authentication secret via environment/secret manager;
- outbox path;
- delivery worker process/service.

No code change to Strategy Engine semantics is required.

## E. LIVE trading — INTENTIONALLY BLOCKED

Still prohibited:

- private OKX order API;
- real order placement;
- real capital execution;
- automatic conversion of diagnostic setup into financial ticket.

This is not an unfinished implementation bug. It is the current explicit project/source safety boundary.

---

# Current critical path

The engineering path no longer starts with market-data plumbing. That foundation is implemented.

The next legitimate critical path is:

1. continue SOURCE provenance/identifiability work independently;
2. obtain/commit the real Platform/Backend application source;
3. wire the existing event receiver + PostgreSQL migration;
4. deploy the already packaged diagnostic runtime to staging VPS;
5. connect outbox delivery to the real backend endpoint;
6. run restart/gap/stale-data/backend-outage end-to-end drills;
7. expose engine provenance/diagnostics in Platform UI;
8. only after SOURCE and project gates change, design any separate PAPER/LIVE financial execution phase.

The current repository must remain fail-closed throughout these steps.
