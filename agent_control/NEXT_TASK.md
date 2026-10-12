# Next Task — MACHINE_STRATEGY_v3 Historical Market-Metadata Recovery Freeze

The v3 design and complete implementation are frozen. The implementation gate ended in an objective financial STOP because historical exchange price-grid/tick epochs are not verified. Do NOT change strategy rules and do NOT run any historical v3 financial outcomes in this task.

## Objective
Recover, verify, and independently freeze the strongest available historical exchange-metadata evidence for BTCUSDT and ETHUSDT Bybit USDT linear perpetual covering the frozen development path and warmup.

Primary blockers to resolve if evidence permits:
1. `NO_VERIFIED_HISTORICAL_TICK_EPOCHS`
2. `HISTORICAL_EXCHANGE_PRICE_GRID_UNVERIFIED`

This is an EVIDENCE + PROVENANCE gate only. If complete proof cannot be established, narrow the unresolved intervals precisely and preserve STOP. Never infer historical tick settings from candle decimal precision, current API settings, later notices, or desired backtest readiness.

## Immutable inputs
Read-only/frozen:
- `docs/machine_strategy_v3_design/`
- `docs/machine_strategy_v3_implementation_readiness/`
- `docs/machine_strategy_failure_audit_v1/`
- all Original/source/baseline/v2/v2.1/v2.2 frozen namespaces
- v3 design freeze `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation freeze `43e57ee5c7867dd9421961629746555c8a2e9556`
- frozen strategy/spec/adapter/runner hashes recorded in `agent_control/STATUS.md`

No strategy parameter, family, direction, entry, stop, target, state, cost, or validation threshold may be changed in this task.

## Required specialist workflow
Use the smallest competent team, but the following roles are required:
1. `tick_metadata_researcher` — lead historical tick/price-grid evidence discovery and source chronology.
2. `historical_data_engineer` — map evidence intervals against exact frozen BTC/ETH M15 data coverage and identify gaps/overlaps.
3. `market_microstructure_auditor` — assess whether each source actually proves executable price-grid semantics rather than merely display precision.
4. `no_lookahead_auditor` — verify publication/capture/effective/known-at chronology and reject retroactive assumptions.
5. `execution_auditor` — independently validate tick rounding implications and exact adapter compatibility.
6. `final_independent_reviewer` — final PASS/STOP decision; must be independent of evidence collection.

Optional roles when useful: `strategy_explorer`, `oos_forward_validator`, `backtest_reviewer`.

Do not claim that every configured role was used unless it actually ran.

## A. Evidence search scope
Search exhaustively but reproducibly for BTCUSDT and ETHUSDT USDT perpetual historical price-grid/tick metadata over:
- warmup: `2022-01-01T00:00:00Z <= t < 2023-01-01T00:00:00Z`
- development: `2023-01-01T00:00:00Z <= t < 2025-12-05T23:30:00Z`

Prioritize evidence classes in this order:
1. Official Bybit dated tick-size/rule-change announcements with immutable or independently archived copies.
2. Official historical/static instrument metadata snapshots, downloadable exchange-maintained files, status pages, API examples or release artifacts with trustworthy capture/publication time.
3. Independent web archives of official Bybit pages/API responses where capture timestamps and bytes are verifiable.
4. Reputable third-party archival datasets only when they contain explicit instrument metadata, exact contract identity, capture time, provenance and immutable hashes.

Search official announcement pages/API/indexes by symbol, contract class, tick-size wording, price-filter terminology and date. Search archive indexes and snapshots around suspected change windows, not just exact current URLs. Search both pre-change and post-change evidence so continuity is not assumed from one notice.

A failed search or archive miss is NOT evidence that no change occurred.

## B. Evidence standards
For every candidate source retain separately:
- symbol and contract identity;
- source class;
- original URL or archive identifier;
- title/page date;
- publication time if available;
- stated effective time;
- archive capture time;
- retrieval time;
- raw byte/content hash;
- normalized relevant-text hash when applicable;
- literal before/after tick values if stated;
- what the source proves;
- what it does NOT prove;
- verification status.

Never collapse publication time, effective time, archive time and retrieval time into one timestamp.

Do NOT promote a historical epoch solely because:
- current `/v5/market/instruments-info` reports a tick size;
- historical candles contain a certain number of decimal places;
- all observed trades happen to align to a grid;
- a later article says a previous tick changed but pre-effective publication cannot be established;
- no additional change notice was found.

Observed price alignment may be retained only as non-authoritative consistency QA, never as epoch proof.

## C. Epoch construction
Construct non-overlapping candidate and verified interval maps per symbol.

A `VERIFIED` epoch requires enough evidence to support all material fields required by the frozen runner:
- `valid_from`
- `valid_to` or an independently justified open interval boundary
- `tick_size`
- `effective_at`
- `known_at`
- exact instrument identity
- evidence receipts/hashes

If continuity across a boundary is not proven, split the map and mark the unknown interval `UNVERIFIED` rather than bridging it.

Report coverage separately for warmup and development, in timestamps and duration percentage. The final financial-readiness decision requires 100% verified executable coverage for the exact declared evaluation interval; partial coverage does not authorize silently dropping periods.

## D. Price-grid authenticity
Independently assess whether the frozen historical OHLC inputs are compatible with each verified tick epoch.

This check is secondary and cannot create an epoch. It may:
- detect contradiction between evidence and data;
- verify every OHLC price is representable on the claimed grid within exact decimal arithmetic;
- identify source rows that violate an otherwise documented exchange grid;
- force STOP if contradictions remain unresolved.

Use exact decimal/integer scaling; no float-tolerance handwaving.
Do not modify candle prices or round source history to make it fit.

## E. Alternative evidence path if full historical proof is impossible
If exhaustive evidence still cannot establish 100% historical coverage:
- preserve `V3_FINANCIAL_STOP`;
- identify the minimal exact unresolved intervals per symbol;
- state whether a shorter historical interval is fully proven, but DO NOT authorize truncating development or selecting that interval based on performance;
- assess whether a prospective-only metadata collection path can establish future executable epochs from a clean registration point;
- do not change the frozen validation protocol in this task.

The purpose is to learn whether the blocker is removable, not to force a PASS.

## Required namespace
Create a new immutable namespace:
`docs/machine_strategy_v3_market_metadata_recovery/`

Required artifacts:
- `MARKET_METADATA_RECOVERY_REPORT.md`
- `EVIDENCE_SEARCH_LOG.json`
- `SOURCE_INVENTORY.json`
- `BTCUSDT_TICK_EPOCHS.json`
- `ETHUSDT_TICK_EPOCHS.json`
- `EPOCH_COVERAGE_MAP.json`
- `PRICE_GRID_COMPATIBILITY.json`
- `PROVENANCE_TIMELINE.json`
- `UNRESOLVED_INTERVALS.json`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- `freeze_manifest.json`

Retain immutable evidence receipts/raw pages or reproducible archive metadata where legally and technically possible. Do not commit credentials, cookies, private account data or secrets.

## Mandatory QA
At minimum:
- exact hash verification for retained evidence;
- deterministic rebuild/replay of epoch maps;
- non-overlap and monotonic interval checks;
- publication/effective/capture/retrieval timestamp separation checks;
- exact BTC/ETH symbol/contract identity checks;
- full frozen-data-period coverage calculation;
- exact-decimal OHLC/grid compatibility check for any VERIFIED epoch;
- contradiction detection across sources;
- static proof that no strategy outcome/P&L data was read for evidence decisions;
- frozen v3 design/implementation namespace invariance;
- full tests, Ruff/format, mypy and compile for new code;
- final independent reviewer PASS required for any readiness promotion.

## Decision gate
Publish exactly one primary state:

### `V3_MARKET_METADATA_FROZEN_READY_FOR_FINANCIAL_AUTH_GATE`
Only if BOTH symbols have 100% VERIFIED historical tick/price-grid coverage for the exact intended warmup/development interval, data compatibility passes, evidence chronology is defensible, all QA passes, and no v3 financial result was generated/viewed.

### `V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP`
If any required interval remains unverified or contradictory. List exact unresolved intervals and strongest remaining evidence gap.

Even a PASS here does NOT itself run or authorize the financial backtest. A separate NEXT_TASK must explicitly open the first financial evaluation gate.

Update `agent_control/STATUS.md` and `CURRENT_STATE.md` with:
- metadata freeze commit SHA;
- namespace/manifest hash;
- verified coverage by symbol and interval;
- unresolved intervals;
- exact agents actually used;
- QA/review result;
- whether a separate first-financial-auth gate may now be opened.

Do NOT run historical v3 financial outcomes.
Do NOT enable PAPER or LIVE.
`trade_entry_allowed=false` remains invariant.
