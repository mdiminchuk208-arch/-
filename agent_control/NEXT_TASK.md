# Next Task — MACHINE_STRATEGY_v3 Prospective Data/Metadata Capture + OOS Registration Readiness Freeze

The historical metadata-recovery gate is frozen at `7e89543ef9b443ac65b64f125c919e885dccf37b` with `V3_MARKET_METADATA_FROZEN_FINANCIAL_STOP`. Historical v3 execution must remain STOP: do not weaken that decision, do not infer old tick epochs, and do not run any historical v3 financial outcomes.

## Objective
Create and independently freeze the prospective-only data/metadata infrastructure required to establish a genuinely clean future validation path for the already-frozen `MACHINE_STRATEGY_v3`.

This gate must answer two questions without observing strategy outcomes:
1. Can BTCUSDT/ETHUSDT Bybit USDT-linear current/future tick/price-grid metadata be captured prospectively with causally known timestamps and immutable receipts from a clean start?
2. Can the frozen 365-day pre-start warmup/data-integrity prerequisites be assembled and verified well enough to permit a separate exact OOS registration commit?

This is DATA + METADATA + CONTROL-PLANE infrastructure only. Strategy rules remain immutable. No signals, orders, positions, trade labels, case outcomes, P&L, PF, WR, expectancy, drawdown, MFE/MAE or equity may be generated or inspected.

## Immutable inputs
Treat as read-only:
- `docs/machine_strategy_v3_design/`
- `docs/machine_strategy_v3_implementation_readiness/`
- `docs/machine_strategy_v3_market_metadata_recovery/`
- all failure-audit/source/baseline/v2/v2.1/v2.2 frozen namespaces
- v3 design freeze `62590f1e09e2fa7516038ba1b3d813b0411d93ab`
- v3 implementation freeze `43e57ee5c7867dd9421961629746555c8a2e9556`
- metadata-recovery freeze `7e89543ef9b443ac65b64f125c919e885dccf37b`

Historical financial STOP remains authoritative. Do not relabel historical data as verified/OOS.

## Required specialist workflow
Use the smallest competent team, with these required functions:
1. `oos_forward_validator` — lead contamination/embargo/registration protocol review.
2. `tick_metadata_researcher` — prospective tick/instrument metadata capture and announcement provenance.
3. `historical_data_engineer` — warmup gap acquisition, continuity, hashes and source identity.
4. `market_microstructure_auditor` — confirm captured fields prove executable price-grid semantics from capture time forward.
5. `no_lookahead_auditor` — verify raw-access isolation, known-at chronology and zero strategy-state leakage.
6. `final_independent_reviewer` — independent PASS/STOP seal.

Use `execution_auditor`, `backtest_reviewer`, or `overfit_red_team` if a specific issue requires them. Do not claim agents that did not actually run.

## A. Prospective tick/price-grid capture
Build an append-only prospective metadata capture path for BTCUSDT and ETHUSDT Bybit USDT linear perpetual.

At minimum:
- capture current public instrument metadata from an official Bybit source when technically available;
- retain raw bytes/response, retrieval timestamp, request parameters, HTTP status, content hash and normalized selected fields;
- record `tickSize`, price-filter semantics and exact instrument identity;
- separately monitor/capture dated official notices that may change tick/price filters;
- never backdate current metadata before its actual capture time;
- define deterministic epoch-opening/closing semantics for future changes;
- if official endpoint access is blocked, retain immutable failure receipts and use only evidence classes permitted by the frozen protocol;
- no credentials/private API.

A prospective epoch may begin no earlier than the first defensible causally known capture/effective boundary. Historical unknown periods remain unknown.

## B. Warmup data readiness
The frozen protocol requires 365 days of completed pre-start bars for state warmup with no pre-start orders/outcomes.

Resolve the exact missing warmup intervals previously recorded for BTCUSDT and ETHUSDT using independently verifiable public data if possible.

Requirements:
- exact BTCUSDT/ETHUSDT Bybit USDT-linear identity;
- completed native M15 bars only;
- UTC timestamp continuity and duplicate detection;
- raw-source receipts/hashes and retrieval timestamps;
- deterministic normalization;
- no interpolation, synthetic bars or silent alias substitution;
- compare overlap against already pinned local data and report any OHLCV conflicts explicitly;
- derived H1/H4/D1 only from verified contiguous M15 after capture/merge QA.

If multiple public mirrors disagree, preserve the disagreement and STOP registration until independently resolved. Do not choose the source that makes strategy behavior preferable.

## C. OOS embargo and exact registration readiness
Preserve the frozen validation protocol exactly unless an explicitly non-outcome operational clarification is required and independently reviewed.

The intended prospective OOS remains:
- BTCUSDT + ETHUSDT Bybit USDT linear perpetual;
- completed M15, derived UTC H1/H4/D1;
- 365 UTC days locked evaluation;
- 365 days contiguous pre-start warmup;
- no pre-start orders/carried positions;
- no candidate signals, positions, trade labels, P&L or equity observation before locked end;
- raw access before end limited to logged integrity/continuity/metadata checks by tooling that cannot access strategy state.

Create a registration-readiness artifact that computes the earliest legally valid start boundary under the frozen rule, but DO NOT register/start OOS unless every prerequisite is objectively satisfied in this gate.

If all prerequisites are satisfied, create a separate append-only exact registration artifact/commit that freezes:
- implementation/spec/manifest hashes;
- exact start UTC D1 open;
- exact end exclusive timestamp;
- exact 365-day warmup interval;
- symbols/contract/timeframes;
- data acquisition procedures;
- prospective tick metadata start evidence;
- embargo policy;
- integrity-only access policy;
- invalidation conditions.

If any prerequisite is unresolved, publish STOP and list exact blockers. Do not shift dates to force readiness.

## D. Control-plane / QA hardening
The completed metadata gate disclosed two brittle current-phase tests coupled to an old `NEXT_TASK` header and a forged-auth-file guard limitation.

Without touching frozen strategy behavior:
- remove task-header brittleness from active non-frozen test/control infrastructure so the unmodified current-phase suite can run honestly;
- preserve the semantic guard itself: unauthorized historical outcome execution must still fail closed;
- replace fixture-only phase assumptions with explicit immutable capability/authorization inputs where needed;
- no auth artifact may authorize a financial run in this gate;
- add tests proving missing/invalid/forged authorization still blocks before historical outcomes.

Do not modify frozen namespaces to make tests green.

## Required namespace
Create an immutable namespace:
`docs/machine_strategy_v3_prospective_readiness/`

Required artifacts:
- `PROSPECTIVE_READINESS_REPORT.md`
- `CURRENT_METADATA_CAPTURE.json`
- `PROSPECTIVE_TICK_EPOCH_PROTOCOL.json`
- `WARMUP_SOURCE_INVENTORY.json`
- `WARMUP_CONTINUITY.json`
- `WARMUP_CONFLICTS.json`
- `RAW_ACCESS_EMBARGO_SPEC.json`
- `OOS_REGISTRATION_READINESS.json`
- `CONTROL_PLANE_GUARD_QA.json`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- `freeze_manifest.json`

If and only if registration prerequisites are all met, additionally create a separate append-only namespace such as:
`docs/machine_strategy_v3_oos_registration/`
with exact immutable registration artifacts. Do not create a fake registration on STOP.

## Mandatory QA
At minimum:
- deterministic replay of metadata/warmup readiness outputs;
- raw-response/hash verification;
- exact timestamp/known-at/capture chronology checks;
- exact symbol/contract identity checks;
- M15 continuity/duplicate/gap checks;
- overlap conflict checks using exact decimals;
- future mutation/prefix isolation for integrity tooling;
- static/dynamic proof integrity-only tooling cannot import/read strategy-state or financial outcome surfaces;
- unauthorized/forged/missing auth capability tests must fail closed;
- unmodified current-phase full test suite PASS (no old NEXT_TASK byte injection workaround);
- Ruff/format, mypy, compile;
- frozen namespace invariance;
- independent reviewer PASS required for readiness promotion.

## Decision gate
Publish exactly one primary state:

### `V3_PROSPECTIVE_READINESS_FROZEN_READY_FOR_OOS_REGISTRATION`
Only if prospective metadata capture is defensible, 365-day warmup is contiguous/verified, control-plane QA passes, and the exact registration prerequisites are all met without strategy/outcome observation.

### `V3_PROSPECTIVE_READINESS_FROZEN_STOP`
If metadata capture, warmup continuity/authenticity, embargo isolation, or control-plane QA remains unresolved. List exact blockers.

If the READY state is reached, registration itself may be created only according to Section C and must still generate zero strategy outcomes in this gate.

Update `agent_control/STATUS.md` and `CURRENT_STATE.md` with:
- prospective-readiness freeze commit SHA;
- manifest hash;
- metadata capture verdict;
- warmup continuity verdict;
- control-plane QA verdict;
- exact agents actually used;
- whether OOS registration was objectively allowed/created;
- exact remaining blockers.

Historical financial backtest remains unauthorized regardless of this gate result.
Do NOT enable PAPER or LIVE.
`trade_entry_allowed=false` remains invariant.
