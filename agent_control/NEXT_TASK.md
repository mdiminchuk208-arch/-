# Next Task — MACHINE_STRATEGY_v3 Implementation Readiness Freeze

The v3 design is frozen at `62590f1e09e2fa7516038ba1b3d813b0411d93ab`. Do NOT change strategy rules and do NOT run any historical financial outcome evaluation in this task.

## Objective
Complete and independently freeze the full causal implementation infrastructure required to execute the already-frozen `MACHINE_STRATEGY_v3` exactly as specified.

This gate exists to remove the two current first-backtest STOP reasons:
1. `HISTORICAL_EVENT_ADAPTER_NOT_IMPLEMENTED`
2. `NO_VERIFIED_HISTORICAL_TICK_EPOCHS`

If either blocker cannot be removed with evidence, keep the STOP explicitly. Never fabricate metadata, interpolate rules, or weaken the frozen design to force a backtest.

## Immutable inputs
Treat these as frozen and read-only:
- `docs/machine_strategy_v3_design/`
- `docs/machine_strategy_failure_audit_v1/`
- all Original/source/baseline/v2/v2.1/v2.2 frozen namespaces
- v3 spec hash `c3876fa2239268f251454304d66a5828f6928e379c27398d4ded3b9c99786ed8`
- v3 design manifest hash `f612b806292844e5d17bee783c9e04879e4a3d32530570a900a467e4ca2e5cc0`

No rule may be changed because of case counts, outcomes, historical P&L, PF, WR, expectancy, drawdown, MFE/MAE, or subgroup performance.

## Required multi-agent workflow
Use all relevant project roles:
1. `strategy_explorer` — map frozen v3 contract requirements to existing historical data/event primitives and identify missing adapter surfaces.
2. `execution_auditor` — own tick-epoch provenance, price-grid validity, rounding, cost/execution identities, and LONG/SHORT symmetry.
3. `strategy_designer` — implementation-conformance role only: verify the adapter/runner implements the frozen spec exactly; no strategy redesign.
4. `backtest_reviewer` — independently review no-lookahead, provenance, hidden tuning, metadata claims, data completeness, and freeze readiness.

Record role outputs under the new readiness namespace.

## A. Full historical event adapter
Implement the complete deterministic adapter needed to transform verified historical market data into the frozen v3 causal event/state/setup representation.

Required coverage:
- BTCUSDT and ETHUSDT Bybit USDT linear perpetual;
- M15 native input with deterministic contiguous UTC H1/H4/D1 derivation where allowed by the frozen spec;
- causal market-state generation;
- all five setup families: SFP, OB, Breaker, STB, Range;
- POI/FTA/liquidity inventories required by the frozen design;
- first-test and physical-idea reservation semantics;
- entry-order representation, gap invalidation, unfilled state, intrabar ambiguity state;
- structural stop and risk-normalization inputs;
- target selection and modeled-cost feasibility inputs;
- exact known-at / source-bar / formation timestamps;
- deterministic identity/hash generation;
- explicit WAIT/REJECT reasons for missing, ambiguous, discontinuous, or unverifiable data.

The adapter must not read realized outcome, exit, future path, P&L or performance columns while deciding admission or constructing an order.

## B. Full runner implementation — outcome engine may exist but must not be financially executed
Implement any remaining runner/execution code required for the later frozen-spec financial backtest, including exit/state transitions, but test it only on synthetic fixtures or deliberately non-financial contract fixtures in this gate.

Do NOT run the completed runner over historical development cases in a way that reveals aggregate or case-level financial outcomes.
Do NOT print or inspect historical v3 wins/losses, R, PF, P&L, expectancy, drawdown, MFE/MAE, or equity.

A static/behavioral guard must make accidental historical outcome evaluation in this gate detectable.

## C. Historical tick-epoch provenance
Establish price tick-size epochs for BTCUSDT and ETHUSDT over every historical development interval that would be eligible for the first v3 financial run.

Evidence hierarchy:
1. official Bybit dated announcements / rule-change notices;
2. official archived/static instrument metadata or exchange-maintained historical material with immutable capture/hash and known publication time;
3. independently archived evidence only when provenance, capture time, and content integrity are explicit.

Rules:
- current `instruments-info` is NOT proof of historical values by itself;
- publication date, effective date, title date, retrieval date and archive capture date must remain separate fields;
- do not infer an epoch boundary merely from observed candle decimals;
- do not backfill unknown periods from later settings;
- if exact coverage is not provable for a period, mark it `UNVERIFIED` and preserve STOP for that period.

For each symbol produce machine-readable intervals with:
- `valid_from`
- `valid_to`
- `tick_size`
- `effective_at`
- `known_at`
- `source_url_or_archive_id`
- `source_hash`
- `evidence_class`
- `verification_status`
- notes on publication/effective-date discrepancies.

## D. Data-grid authenticity and completeness
Verify every historical input series used by the adapter:
- source identity and content hash;
- symbol/contract type;
- UTC timestamps;
- expected M15 continuity;
- duplicate/missing bars;
- H1/H4/D1 derivation rules;
- source aliases/overlap so duplicate representations are not treated as independent evidence;
- exact data period eligible for development evaluation.

Never interpolate missing OHLCV bars.
If continuity cannot be established, produce explicit WAIT/STOP coverage maps.

## E. OOS readiness preparation — no OOS outcome observation
Preserve the frozen validation principle: all currently inventoried history is exposed development, and old 2026 TEST data is not untouched OOS.

In this gate:
- determine whether a contiguous 365-day pre-start warmup can be assembled from independently verified public data for a future prospective OOS registration;
- verify acquisition procedure, hashes, continuity checks, and metadata coverage;
- do not generate candidate signals, positions, trade labels or P&L for the prospective OOS period;
- do not claim a pristine OOS window exists until a separate append-only registration freezes exact future start/end timestamps after the complete implementation freeze;
- if warmup/data/metadata cannot be made ready, preserve `STOP_NO_PRISTINE_OOS`.

Do NOT silently change the frozen validation protocol. Any necessary non-outcome operational clarification must be explicitly documented, independently reviewed, and re-frozen before observation.

## Required readiness namespace
Create an immutable namespace such as:
`docs/machine_strategy_v3_implementation_readiness/`

Required artifacts:
- `IMPLEMENTATION_READINESS_REPORT.md`
- `HISTORICAL_ADAPTER_SPEC.json`
- `HISTORICAL_ADAPTER_COVERAGE.json`
- `TICK_EPOCH_EVIDENCE.md`
- `TICK_EPOCHS.json`
- `DATA_GRID_AUTHENTICITY.json`
- `DATA_CONTINUITY_REPORT.json`
- `OUTCOME_GUARD_QA.json`
- `OOS_READINESS.json`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- `freeze_manifest.json`

Store immutable evidence receipts/hashes or reproducible retrieval metadata where legally/technically possible. Do not commit secrets or private API credentials.

## Mandatory QA before freeze
At minimum:
- deterministic adapter replay;
- historical input prefix/future-mutation no-lookahead test;
- known-at timestamp validation;
- M15→H1/H4/D1 aggregation fixtures;
- LONG/SHORT reflection/symmetry fixtures;
- all-five-family synthetic fixtures;
- tick rounding/epoch boundary fixtures;
- gap/missing-bar/duplicate-bar tests;
- intrabar ambiguity tests;
- first-test/reservation/re-entry tests;
- cost identity and risk-floor invariants;
- static scan proving admission/order construction does not read outcome columns;
- guard proving historical financial evaluation was not executed in this gate;
- frozen namespace hash invariance;
- full test suite, Ruff/format, mypy, compile;
- independent reviewer PASS required for readiness.

## Decision gate
At completion, publish one of the following exact states:

### `V3_IMPLEMENTATION_FROZEN_READY_FOR_FIRST_FINANCIAL_BACKTEST`
Only if ALL are true:
- full adapter and runner implement frozen v3 deterministically;
- development data grid is verified for the declared evaluation period;
- historical tick epochs fully cover that declared period;
- all QA/review passes;
- no historical v3 financial outcomes were viewed before freeze.

### `V3_IMPLEMENTATION_FROZEN_FINANCIAL_STOP`
If any required implementation/data/tick evidence remains unresolved. List exact blockers and affected periods/symbols.

Separately report OOS state. OOS readiness does not need to be complete to freeze implementation, but no production qualification can occur without later pristine OOS/forward validation.

Update `agent_control/STATUS.md` and `CURRENT_STATE.md` with:
- complete implementation freeze commit SHA;
- manifest and code/spec hashes;
- exact tick-epoch coverage verdict;
- historical adapter/data coverage verdict;
- actual agents used;
- QA/review result;
- whether first development financial backtest is now authorized;
- whether a separate prospective OOS-registration gate can be opened.

Do NOT run the first financial backtest in this task even if readiness becomes PASS.
Do NOT enable PAPER or LIVE.
`trade_entry_allowed=false` remains invariant.
