# Next Task — MACHINE_STRATEGY_v3 Prospective Capture Activation + Control Plane v2 Freeze

The prospective-readiness gate is frozen at `fdf5b95e34c724ab73e8f3e64d36aed562ad965b` with `V3_PROSPECTIVE_READINESS_FROZEN_STOP`. Preserve that STOP and every prior freeze. Do NOT run historical v3 financial outcomes, do NOT generate OOS signals/trades, and do NOT change strategy rules.

## Objective
Remove the currently removable infrastructure blockers and start a real append-only prospective evidence clock for the frozen v3 strategy.

This gate has four goals:
1. activate a lawful public prospective BTCUSDT/ETHUSDT Bybit data + instrument-metadata collector from an environment where official public endpoints are normally reachable, without VPN/proxy/geolocation spoofing or credentials;
2. establish append-only provenance/continuity storage that can accumulate a future 365-day warmup;
3. create a phase-stable Control Plane v2 so active QA no longer depends on old `NEXT_TASK` text while all historical frozen tests remain immutable and auditable;
4. create a new fail-closed execution authorization gateway with an OS/process isolation boundary, without modifying the frozen v3 adapter/runner.

No PASS in this gate authorizes financial evaluation, PAPER, LIVE, or OOS registration.

## Immutable inputs
Read-only/frozen:
- baseline `ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`
- failure audit `8ca75ed35876d8f5d4d363e9e8808d7bd4417e87`
- v3 design `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation `43e57ee5c7867dd9421961629746555c8a2e9556`
- v3 metadata recovery `7e89543ef9b443ac65b64f125c919e885dccf37b`
- v3 prospective readiness `fdf5b95e34c724ab73e8f3e64d36aed562ad965b`
- all corresponding frozen namespaces/manifests and the frozen adapter/runner hashes recorded in `STATUS.md`.

Historical verified tick coverage remains 0%. Do not reinterpret or backfill it.

## Required specialist workflow
Required functions:
1. `historical_data_engineer` — prospective M15 collector, continuity, dedupe, receipts and append-only storage.
2. `tick_metadata_researcher` — current/future official instrument metadata and dated tick/filter notices.
3. `oos_forward_validator` — prospective clock, embargo, contamination and future-registration semantics.
4. `no_lookahead_auditor` — prove collector/control tooling cannot read strategy state or outcomes.
5. `market_microstructure_auditor` — verify captured metadata proves executable price-grid semantics from its defensible known-at boundary.
6. `backtest_engineer` — Control Plane v2 / authorization gateway implementation only; no financial backtest.
7. `final_independent_reviewer` — independent final PASS/STOP seal.

Use `execution_auditor`, `backtest_reviewer`, `overfit_red_team` when useful. Record actual identities/functions; do not claim unused agents.

## A. Activate prospective public capture
Implement a production-like, append-only collector for:
- BTCUSDT and ETHUSDT;
- Bybit USDT linear perpetual;
- official public instrument metadata including exact `tickSize` / price-filter fields when available;
- completed native M15 OHLCV bars only;
- dated official notices that change tick/price filters where technically available.

### Access policy
- no private API keys, cookies, account session, VPN, proxy, residential routing or geolocation spoofing;
- do not evade a 403 from the current cloud environment;
- an ordinary GitHub-hosted Actions runner or other normal project CI runner MAY be used as the collector environment if it reaches the same official public endpoint without any evasion mechanism;
- if the official endpoint is also unavailable there, retain immutable failure receipts and STOP that source;
- official alternative endpoints may be used only if documented/normal for public market data, not as a disguised geo-bypass.

### Collector behavior
- capture raw response bytes, request URL/params, response status/headers needed for provenance, retrieval UTC timestamp and SHA-256;
- normalize separately; never overwrite raw bytes;
- capture exact instrument identity and category;
- fetch enough recent closed M15 bars with overlap to tolerate delayed CI runs, then exact-dedupe by symbol/open-time;
- never store an unfinished bar as completed;
- detect missing/duplicate/conflicting bars and never interpolate;
- use exact decimal representation for prices/filters;
- collector must not import strategy/adapter/runner modules;
- collector must not generate signals, states, setups, orders, labels or financial metrics.

Prefer a bounded schedule with overlap and deterministic backfill after transient outages rather than assuming exact cron timing. Keep storage/commit growth reasonable; design a reproducible daily/periodic packing scheme if needed while preserving raw hashes and retrieval chronology.

## B. Append-only capture channel
Create a separate prospective evidence surface so collector writes cannot conflict with active research work. A dedicated branch such as `machine-v3-prospective-capture` is allowed and preferred.

Requirements:
- append-only evidence files/receipts;
- no rewriting prior captures;
- deterministic index/manifest chain with previous-manifest hash;
- capture sequence number + retrieval time;
- provenance for the workflow/code commit that produced each capture;
- workflow has only the minimum repository permission needed;
- no secrets other than the normal GitHub workflow token if repository write is necessary;
- concurrency control prevents races/double writers;
- failed fetches are evidence too and must not be converted into synthetic success.

Before enabling recurring collection, execute at least one bounded manual/CI capture and independently verify the exact bytes, hashes, identity and no-strategy isolation. If verified, enable the schedule in the final reviewed workflow bytes and record the first defensible prospective capture time `T0`.

`T0` is NOT OOS registration and does not retroactively verify any earlier period.

## C. Warmup accumulation and historical gap policy
Do not force-fill prior gaps. Continue attempting only independently verifiable public Bybit-specific sources where allowed, but the durable path is prospective accumulation.

Create a machine-readable clock showing:
- `T0` for each symbol/data surface;
- current verified contiguous completed-M15 span after T0;
- exact missing/conflicting intervals;
- earliest possible date at which a 365-day contiguous warmup could become eligible if collection remains complete;
- conditions that reset/invalidate the continuity clock.

The frozen OOS registration rule remains unchanged. Do not register OOS in this gate.

## D. Control Plane v2 governance
Resolve `FROZEN_ACTIVE_TEST_HEADERS_CONFLICT_WITH_CURRENT_TASK` by explicitly versioning active control tests, not by editing frozen test bytes or injecting old task text.

Requirements:
- preserve old phase-specific tests byte-for-byte as historical evidence;
- define an append-only active-test registry/manifest with version and hashes;
- migrate each brittle test to a phase-stable semantic equivalent that checks immutable capabilities/state rather than a prose `NEXT_TASK` header;
- document one-to-one semantic mapping from legacy assertions to active replacements;
- active current-phase suite must run honestly without monkeypatching task bytes, skips, xfail, filtered failures or weakened guard semantics;
- legacy suite remains separately reproducible/auditable and is not falsely called current-phase PASS.

## E. Execution Authorization Gateway v2
Do not modify the frozen adapter/runner. Add a new outer gateway/version that is the only supported active path for any future historical/OOS execution.

It must:
- default DENY;
- reject absent/invalid/forged/stale/wrong-phase authorization before strategy history reads;
- bind authorization to exact strategy spec, implementation, runner, data/evidence manifest and allowed phase hashes;
- distinguish `INTEGRITY_ONLY`, `OOS_REGISTERED_EMBARGOED`, `FINANCIAL_EVALUATION_AUTHORIZED`, `PAPER`, and `LIVE` capabilities; only `INTEGRITY_ONLY` is permitted in this gate;
- ensure `trade_entry_allowed=false` regardless of malformed input;
- make financial authorization impossible to mint from collector/runtime data alone.

### Isolation
Add the strongest available OS/process boundary for integrity-only tooling:
- separate subprocess/process identity/workdir with explicit allowlisted files and environment;
- no strategy-state path visibility where the host permits it;
- no network except exact allowlisted public collection endpoints during collection;
- no shell/subprocess spawning from integrity worker unless explicitly required and audited;
- prefer OS namespace/container/sandbox primitives if available;
- if true OS-level isolation is unavailable, prove the strongest enforceable boundary and preserve an explicit STOP for that item rather than claiming equivalent security.

## F. Required namespace
Create immutable namespace:
`docs/machine_strategy_v3_capture_control_v2/`

Required artifacts:
- `CAPTURE_CONTROL_REPORT.md`
- `COLLECTOR_SPEC.json`
- `COLLECTOR_ACCESS_RECEIPTS.json`
- `CAPTURE_BRANCH_PROTOCOL.json`
- `PROSPECTIVE_CLOCK.json`
- `ACTIVE_TEST_GOVERNANCE.json`
- `LEGACY_TO_ACTIVE_TEST_MAPPING.json`
- `AUTHORIZATION_GATEWAY_SPEC.json`
- `ISOLATION_QA.json`
- `OUTCOME_ISOLATION_QA.json`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- `freeze_manifest.json`

If recurring capture is successfully activated, also retain the exact collector workflow SHA/content hash and first capture manifest/hash/T0. Do not copy prospective raw data into this frozen report namespace if the separate append-only capture branch is the canonical evidence surface; reference its immutable commit/hash instead.

## Mandatory QA
At minimum:
- bounded real public capture attempt in the intended collector environment;
- raw byte/hash replay and normalized-output determinism;
- exact BTC/ETH contract/category/tick identity checks;
- closed-M15 cutoff/continuity/dedupe/conflict tests;
- collector future-mutation/prefix tests;
- static import graph proving collector/integrity worker does not import strategy/outcome modules;
- dynamic file-access/read audit proving no strategy-state/outcome reads in integrity mode;
- active-test-registry hash verification;
- unmodified new active current-phase suite PASS;
- separate reproducibility record for legacy frozen tests without mislabeling them current PASS;
- missing/forged/wrong-hash/wrong-phase auth tests DENY before history read;
- OS/process isolation escape-negative tests appropriate to the selected mechanism;
- capture branch race/idempotence tests;
- frozen namespace/hash invariance;
- Ruff/format, mypy, compile;
- independent reviewer PASS required for any ACTIVE decision.

## Decision gate
Publish exactly one state:

### `V3_CAPTURE_CONTROL_FROZEN_ACTIVE`
Only if:
- at least one defensible official prospective metadata + M15 capture path is operational for BOTH symbols from a non-evasive public environment;
- append-only capture storage/manifest chain is verified and recurring collection is activated;
- a defensible T0 is frozen;
- Control Plane v2 active suite passes honestly;
- authorization gateway fails closed;
- required isolation is implemented and reviewer accepts its exact guarantees/limitations;
- no strategy outcome was generated/viewed.

### `V3_CAPTURE_CONTROL_FROZEN_STOP`
If any critical requirement remains unresolved. List exact blockers and distinguish time-dependent accumulation from engineering failures.

Even ACTIVE does NOT authorize OOS registration yet. OOS registration can open only after the frozen 365-day warmup prerequisites are objectively satisfied and independently reviewed.

Update `agent_control/STATUS.md` and `CURRENT_STATE.md` with:
- freeze commit/manifest hash;
- exact collector environment and access verdict;
- capture branch/workflow commit and T0 if activated;
- current prospective contiguous duration;
- active-test/control-plane verdict;
- isolation/auth-gateway verdict;
- actual agents used;
- exact remaining blockers and next eligible gate.

Historical financial backtest remains unauthorized.
Do NOT enable PAPER or LIVE.
`trade_entry_allowed=false` remains invariant.
