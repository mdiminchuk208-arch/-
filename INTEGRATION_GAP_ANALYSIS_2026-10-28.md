# Crypto Bot — Integration Gap Analysis, 2026-10-28

## Purpose

This document compares the current Crypto Bot architecture against three external acceleration references:

1. `tradesdontlie/tradingview-mcp`
2. `Jakeschincariol/day-trader-skill`
3. `Jakeschincariol/trader-skill`

The goal is **not** to replace or modify PURE SOURCE semantics. The goal is to reuse architectural patterns that can accelerate market-data tooling, replay/QA, entry/exit orchestration, risk, paper execution, alerts, diagnostics, and platform integration.

## Hard boundary

PURE SOURCE remains authoritative under `AGENTS.md` and `PURE_SOURCE_CURRENT_STATUS.md`.

Current authoritative verdict:

- rebuild stage: Stage 23 — Qualified Diagnostic Replay;
- baseline verdict: `NOT_IDENTIFIABLE` as one unique executable financial strategy;
- `trade_entry_allowed=false`;
- no financial PURE SOURCE backtest is authorized yet;
- no PAPER/LIVE/private exchange execution from PURE SOURCE;
- no PROJECT overlay may resolve SOURCE ambiguity;
- historical PnL/WR/PF/expectancy cannot choose among SOURCE-permitted branches;
- missing SOURCE semantics remain `UNRESOLVED` / `UNKNOWN`.

Therefore every external component in this report is classified as **INFRASTRUCTURE / QA / PROJECT**, never SOURCE truth.

---

## 1. Current Crypto Bot state

### 1.1 PURE SOURCE / Strategy Engine

Current repo `main` is at Stage 23.

Already present:

- closed-candle causality;
- `formation_at`, `known_at`, `confirmed_at`, `invalidated_at` semantics;
- deterministic diagnostic replay;
- stable SOURCE alternatives without ranking;
- typed qualitative provenance;
- causal claim journal bound to closed candle windows;
- qualified EQH/EQL consumer;
- qualified SFP trade-context consumer;
- explicit annotation-delivery schedules;
- future schedules excluded from prior evidence fingerprints;
- fail-closed execution (`trade_entry_allowed=false`).

Still blocked by SOURCE identifiability:

- missing source-qualified market annotations for several qualitative concepts;
- incomplete migration of OB/Breaker, Range/OTE, STB/BTS and Demand/Supply consumers;
- unresolved exact quote inside POI variants;
- unresolved beyond-anchor stop buffer / some protective-stop geometry;
- unresolved partial FTA / remainder lifecycle;
- unresolved re-entry identity/eligibility details;
- unresolved context selection when multiple valid timeframes/liquidity pools coexist.

**Decision:** do not use external skills or PnL to fill any of these gaps.

### 1.2 Historical data / replay

The repository has a substantial native historical research and QA layer, including Bybit historical datasets, source-permitted physical case replay, prefix/future-mutation checks, identity preservation, cost/risk ledgers and historical execution audits.

However, the production target exchange is **OKX**, while the repository still contains a large Bybit-centric historical layer. The current GitHub codebase has no confirmed complete OKX market-data adapter in main.

**Gap:** OKX-native reproducible data layer remains a production blocker.

Required production data contract:

- primary exchange: OKX;
- canonical timeframes: 5m / 15m / H1 / H4 / D1;
- D1 normalized consistently (target design previously used UTC daily bars);
- closed candles only;
- pagination, gaps, duplicates, continuity and MTF alignment checks;
- immutable dataset manifest and hashes;
- dataset version attached to every run;
- prefix replay and future-mutation QA;
- deterministic stable IDs.

### 1.3 Platform / backend

Existing validated Platform v1 work already covers much of the shell:

- RU/EN UI;
- 17 workspace sections;
- auth;
- Cloudflare Worker/D1 local runtime;
- PAPER open/close lifecycle;
- SHADOW lifecycle;
- TP/SL lifecycle in the historical platform branch;
- persistence, idempotency, journal/audit and capital semantics;
- daily loss/stale guards in the platform layer;
- 24 routes and local browser/API validation;
- production bundle dry-run.

Known platform gaps:

- Strategy Engine is not integrated into production Platform signals;
- UI still has PRE_STRATEGY / NOT_CONNECTED paths in the validated build;
- platform source is not yet the same GitHub source-of-truth as Strategy Engine;
- production deploy remains unverified / older production 503 remained unresolved in the last recorded validation;
- PostgreSQL runtime and autonomous 24x7 bot runtime are not established;
- OKX replaces legacy Bybit transport;
- staging and production system-health validation are still required.

---

## 2. External reference A — TradingView MCP

Repository: `tradesdontlie/tradingview-mcp`

Useful capabilities:

- local TradingView Desktop control through CDP;
- symbol/timeframe navigation;
- OHLCV reading;
- Pine values/lines/labels/tables/boxes;
- screenshots;
- multi-pane layouts;
- Replay start/step/autoplay/trade/status;
- alert and drawing control;
- JSON CLI / streaming;
- health checks.

### What to adopt

Create a **TradingView / AI QA Bridge** as an optional sidecar:

`Strategy Engine / Backtest -> QA Bridge -> TradingView MCP`

Use it for:

- visual replay of selected historical cases;
- forensic review of losses / disputed cases;
- chart rendering for a setup ID;
- automatic D1/H4/H1/M15 navigation;
- screenshots for human review;
- comparison of engine objects against chart state;
- visual regression / research support.

### What NOT to do

- do not use TradingView as production market-data source;
- do not make MCP a dependency of Strategy Engine;
- do not use LLM visual judgment as SOURCE truth;
- do not place real orders through TradingView MCP;
- do not let MCP failure block OKX production runtime.

Reason: TradingView MCP relies on undocumented internal Desktop interfaces and can break after TradingView updates.

Classification: **INFRASTRUCTURE / QA TOOLING**.

---

## 3. External reference B — day-trader-skill

Repository: `Jakeschincariol/day-trader-skill`

Relevant orchestration pattern:

`scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker -> alerts`

### 3.1 Scanner pattern

Adopt the orchestration concept, not ORB/flag/oversold rules.

Crypto Bot equivalent:

`OKX universe -> SOURCE object pipeline -> setup candidates -> setup events`

Required output per candidate:

- object/setup ID;
- symbol;
- timeframe(s);
- formation/known/confirmed timestamps;
- source rule refs;
- state;
- rejection reason;
- engine/dataset version.

Classification: **INFRASTRUCTURE**.

### 3.2 Entry watcher pattern

Strongly useful pattern:

- bar-by-bar state machine;
- closed bars only;
- immutable trigger moment;
- waiting / triggered / expired states;
- replay clock support;
- no retroactive level movement.

Crypto Bot equivalent:

`Setup -> EntryWatch -> CONFIRMED / INVALIDATED / EXPIRED`

Do not copy its long-only ORB logic.

Classification: **INFRASTRUCTURE / TECHNICAL NORMALIZATION**, only where it does not redefine SOURCE.

### 3.3 Exit planner pattern

Useful pattern:

- freeze entry/stop/target plan before execution;
- reject malformed geometry;
- hand immutable plan downstream;
- never widen a stop after activation unless a separate explicit policy says so.

Do not copy OR midpoint / ATR / fixed 1R/2R exits into PURE SOURCE.

Crypto Bot equivalent should preserve SOURCE branch identity and unresolved exit geometry.

Classification: **INFRASTRUCTURE**, with exit selection remaining SOURCE or PROJECT depending on origin.

### 3.4 Time Machine pattern

Useful as research only:

- deterministic seed;
- reproducible simulation;
- historical replay of the same rule;
- target-first / stop-first / neither statistics;
- average R;
- explicit separation of simulation from prediction.

Crypto Bot adaptation:

- use real SOURCE setup identity / PROJECT experiment identity;
- retain dataset/version/seed;
- never use Monte Carlo to resolve SOURCE ambiguity;
- never promote its verdict to PURE SOURCE trade admission.

Classification: **PROJECT RESEARCH / QA**.

### 3.5 Budget / Risk / Broker / Alerts

Reuse architecture pattern:

`physical trade idea -> sizing -> risk gate -> paper executor -> position -> alerts/journal`

Do not reuse US-stock assumptions.

Classification: **PROJECT RISK / PLATFORM**.

---

## 4. External reference C — trader-skill

Repository: `Jakeschincariol/trader-skill`

Most useful concepts for Crypto Bot:

### 4.1 Risk gate

Good patterns:

- proposal separated from approval;
- deterministic PASS/BLOCK;
- exact rejection reason;
- batch-aware risk state;
- duplicate protection;
- changed order requires re-validation;
- risk rules cannot silently modify the order;
- fingerprint binds verdict to the exact proposal.

Crypto Bot adaptation:

- `trade_idea_fingerprint`;
- `risk_verdict_fingerprint`;
- risk verdict bound to engine version, dataset version and plan identity;
- modified entry/SL/TP/size -> new fingerprint -> new risk pass;
- no silent limit loosening.

Project-only checks can include:

- risk per trade;
- total portfolio risk;
- concurrent exposure;
- correlation;
- daily loss;
- leverage/margin;
- stale data;
- duplicate intent;
- position size;
- liquidation distance.

These remain **PROJECT_POLICY**, outside PURE SOURCE baseline.

### 4.2 Broker/executor gate

Good architecture:

- analysis does not execute;
- risk does not execute;
- executor consumes only an approved exact ticket;
- execution state is logged independently.

Current Crypto Bot target:

- SHADOW executor;
- PAPER executor;
- no LIVE/private API while current safety boundary remains.

Classification: **PLATFORM / EXECUTION INFRASTRUCTURE**.

### 4.3 Alerts / portfolio state

Useful pattern:

- stateful alerts derived from an immutable plan;
- one-shot event handling;
- journal of fired alerts;
- explicit portfolio state.

Adapt to 24/7 crypto, not NYSE sessions.

Classification: **PLATFORM**.

---

## 5. Target full architecture

```text
                         +-----------------------------+
                         | TradingView / AI QA Bridge  |
                         | optional, local/research    |
                         +--------------+--------------+
                                        |
                                        v
OKX PUBLIC DATA -> Market Data / Dataset Layer -> PURE SOURCE Strategy Engine
                         |                         |
                         |                         +-> diagnostic objects
                         |                         +-> setup candidates
                         |                         +-> rejection reasons
                         |                         +-> provenance
                         |
                         +-> Backtest / Prefix Replay / Future Mutation QA
                                                  |
                                                  v
                                         Entry Watch State Machine
                                                  |
                                   +--------------+--------------+
                                   |                             |
                              INVALIDATED                    CONFIRMED
                                                                 |
                                                                 v
                                                      Physical Trade Idea
                                                                 |
                                            +--------------------+--------------------+
                                            |                                         |
                                      PURE SOURCE branch                      PROJECT overlays
                                      identity/provenance                     (separate namespace)
                                            |                                         |
                                            +--------------------+--------------------+
                                                                 |
                                                                 v
                                                           Risk Engine
                                                                 |
                                                    PASS / BLOCK + reason
                                                                 |
                                                                 v
                                                     SHADOW / PAPER Executor
                                                                 |
                                                                 v
                                                     Positions / Journal / PnL
                                                                 |
                                                                 v
                                                         Backend / Database
                                                                 |
                                                                 v
                                                           Platform UI
```

### Rule

The AI/TradingView layer may **observe, explain and QA**. It must never become the source of a PURE SOURCE rule or override deterministic engine state.

---

## 6. Gap matrix

| Area | Current state | External accelerator | Required action | Priority |
|---|---|---|---|---|
| PURE SOURCE | Stage23, NOT_IDENTIFIABLE, fail-closed | none | continue source-qualified provenance work only | P0 |
| OKX data | target architecture defined, complete adapter not confirmed in main | none | build OKX adapter + immutable dataset manifests | P0 |
| Closed-bar entry watcher | causality primitives exist | day-trader-skill entry pattern | create generic engine-owned watcher | P0 |
| Immutable trade plan | partially represented in historical runtimes | day-trader-skill exit pattern | formal plan schema + fingerprint | P0 |
| Backtest/replay QA | strong historical diagnostic layer | Time Machine + TradingView MCP | add selected visual replay sidecar; keep deterministic backtest primary | P1 |
| Risk engine | historical/project risk concepts exist; platform guards exist separately | trader-skill risk pattern | unify into explicit PROJECT risk service | P1 |
| Paper executor | platform lifecycle exists separately | trader-skill broker pattern | connect engine event contract to SHADOW/PAPER only | P1 |
| Alerts | platform notifications incomplete/external delivery absent | trader-skill alerts | event-driven alert subsystem | P2 |
| Backend/DB | platform Worker/D1 + FastAPI validation exists separately | state/fingerprint patterns | define canonical event schema + PostgreSQL production persistence | P1 |
| Platform integration | UI shell strong; engine NOT_CONNECTED | all three | ingest engine events and expose provenance/QA | P1 |
| TradingView QA | absent from core | TradingView MCP | optional local QA bridge | P2 |
| 24x7 runtime | not established | none | VPS/container/runtime + restart/reconnect health | P1 |
| Production deploy | prior Worker 503 unresolved in last validation | none | staging -> production smoke -> monitoring | P1 |
| LIVE trading | intentionally disabled | broker reference only | keep disabled | BLOCKED |

---

## 7. Implementation order

### Phase A — preserve SOURCE and close data/runtime foundations

1. Do not change SOURCE rules from external projects.
2. Implement OKX public market-data adapter.
3. Normalize 5m/15m/H1/H4/D1 closed candles.
4. Add immutable dataset manifest/hash/version.
5. Run data QA: gaps, duplicates, continuity, alignment, timezone, prefix, future mutation.
6. Keep Bybit datasets as historical/legacy comparison only.

### Phase B — formal event pipeline

7. Freeze canonical Strategy Engine -> Platform event contract.
8. Add setup lifecycle state machine:
   - FORMING
   - KNOWN
   - CONFIRMED
   - INVALIDATED
   - EXPIRED
   - BLOCKED_SOURCE_UNKNOWN
9. Add immutable Physical Trade Idea schema where SOURCE actually permits one.
10. Add trade-idea fingerprint and causal provenance references.

### Phase C — replay / QA acceleration

11. Build generic closed-bar EntryWatch pattern inspired by day-trader-skill.
12. Keep deterministic prefix replay as primary QA.
13. Add conditional research simulator only in PROJECT namespace.
14. Add TradingView MCP sidecar for selected case visual replay and forensic review.
15. Never feed TradingView/LLM judgments back into SOURCE truth automatically.

### Phase D — risk / paper execution

16. Build explicit PROJECT Risk Engine with deterministic PASS/BLOCK and reason codes.
17. Bind risk verdict to exact trade-idea fingerprint.
18. Any edit -> new fingerprint -> revalidation.
19. Connect only SHADOW/PAPER executor.
20. Keep private exchange API and LIVE disabled.

### Phase E — backend / platform / 24x7

21. Make GitHub the source-of-truth for platform/backend code.
22. Connect Strategy Engine events to Backend ingestion.
23. Persist engine version, dataset version, source branch ID, provenance, rejection reason and risk verdict.
24. Run PostgreSQL production runtime.
25. Deploy autonomous 24x7 runtime on VPS/container infrastructure.
26. Add restart/reconnect/stale-data/safe-mode health tests.
27. Deploy staging.
28. Run full browser/API/engine integration smoke.
29. Deploy production only after staging receipts pass.

---

## 8. Immediate concrete work packages

### WP-01 OKX adapter

Deliverables:

- REST/public WS adapters;
- canonical candle model;
- 5m/15m/H1/H4/D1 mapping;
- closed-bar enforcement;
- pagination/retry/rate-limit handling;
- gap/duplicate audit;
- dataset manifest/hash;
- deterministic fixtures/tests.

### WP-02 Engine event contract

Minimum payload:

- market object;
- object_id;
- setup_id;
- symbol;
- timeframe;
- side;
- state;
- formation_at;
- known_at;
- confirmed_at;
- invalidated_at;
- entry only when source-permitted;
- stop only when source-permitted;
- FTA/target only when source-permitted;
- rejection reason;
- SOURCE rule references;
- SOURCE branch identity;
- provenance/evidence IDs;
- engine version;
- git commit;
- dataset version.

### WP-03 EntryWatch

- closed candles only;
- deterministic waiting/confirmed/invalidated/expired transitions;
- replay clock;
- prefix determinism;
- no retroactive mutation;
- immutable event log.

### WP-04 Risk service

- PROJECT namespace only;
- exact input fingerprint;
- PASS/BLOCK + machine reason code;
- no order mutation;
- stale-data guard;
- duplicate guard;
- risk-per-trade / total risk / daily loss / leverage / margin / exposure checks;
- new fingerprint after any plan change.

### WP-05 TradingView QA bridge

- optional process, not production dependency;
- health check;
- load symbol/timeframes;
- Replay to timestamp;
- draw engine objects;
- screenshot/export QA bundle;
- compare engine IDs/timestamps with displayed chart;
- no execution authority.

### WP-06 Platform integration

- ingest engine events;
- replace PRE_STRATEGY / NOT_CONNECTED for connected environments;
- display source provenance and rejection reason;
- display engine/dataset versions;
- setup timeline;
- QA conflict panel;
- SHADOW/PAPER lifecycle only.

---

## 9. Acceptance gates

### Data gate

- OKX historical and live-public closed candles reproduce deterministically;
- zero silent gaps/duplicates;
- manifests/hashes stable;
- MTF alignment pass;
- future mutation test pass.

### Strategy gate

- no PROJECT policy inside PURE SOURCE;
- unresolved source facts remain UNKNOWN;
- no financial execution artifact while `NOT_IDENTIFIABLE` blocks it;
- all SOURCE timing/provenance tests pass.

### Platform gate

- engine event ingestion idempotent;
- restart persistence pass;
- stale-data fail-closed;
- SHADOW/PAPER state survives restart;
- platform cannot invent a signal not emitted by engine;
- browser/API smoke pass.

### Production gate

- autonomous runtime with local PC off;
- restart/reconnect recovery pass;
- monitoring/health endpoints active;
- staging receipts stored;
- production smoke pass;
- LIVE remains disabled until a separate explicit project decision changes the boundary.

---

## 10. Final decision

The three external projects **do not change the Crypto Bot architecture we already chose**. They validate and accelerate it.

Use them as follows:

- **TradingView MCP:** visual QA / Replay / chart-control sidecar.
- **day-trader-skill:** orchestration patterns for scanner/entry/exit/replay pipeline.
- **trader-skill:** risk fingerprints, sizing, executor gates, alerts/state patterns.

Keep the real core unchanged:

`OKX -> canonical data -> PURE SOURCE Strategy Engine -> deterministic QA -> explicit PROJECT risk -> SHADOW/PAPER -> Backend/DB -> Platform`.

The current critical path is therefore:

**OKX data foundation -> event contract -> EntryWatch -> risk service -> SHADOW/PAPER integration -> PostgreSQL/24x7 runtime -> Platform ingestion -> optional TradingView QA bridge.**

PURE SOURCE identifiability work continues independently and must not be accelerated by guessing, PnL optimization, LLM visual judgment or external strategy rules.
