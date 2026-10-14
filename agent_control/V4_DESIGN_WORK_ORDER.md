# MACHINE_STRATEGY_v4 — Active Design Work Order

State: PRE_OUTCOME_DESIGN_ACTIVE. This work order turns the frozen v3 failure audit into one deterministic v4 design. It does not authorize implementation or financial testing.

## Pinned evidence
- v3 financial result is frozen failed qualification.
- causal failure audit publication: `54419daa29e7e68d6f692daee9cf2132203393ef`.
- failure audit manifest: `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`.
- v4 design inputs: `docs/machine_strategy_v4_design_v1/DESIGN_INPUTS.json`.

## Design objective
Create one causally justified v4 that attacks both verified v3 failure classes without selecting rules from historical P&L:
1. **candidate scarcity / over-filtering** — v3 produced only 99 candidates in two development years and 88% of raw formations terminated at the pre-context non-smooth/opposing-BOS gate;
2. **negative payoff construction** — the known CLOSED sample had negative gross edge, median target/stop distance ratio about 0.4426 and average net win far smaller than average loss.

The design goal is not to maximize the exposed development WR. The frozen promotion standard remains WR>=70% together with positive net expectancy/P&L, PF/sample/drawdown/cost/robustness requirements and later OOS/Paper survival.

## Mandatory design decisions
The design must explicitly ADOPT / DEFER / REJECT each item below, with source/policy classification, decision-time fields, LONG/SHORT mirror and deterministic machine semantics.

### H00 — observer telemetry prerequisite
ADOPT unless a source conflict is proven. Add unique formation/physical IDs, first-pass/repeated-wait/terminal gate events, known_at timestamps and gate-level denominators. Observer telemetry must never become an outcome-dependent filter.

### H01 — causal structural approach semantics
Re-justify the v3 early opposing-BOS/non-smooth veto from first principles. Do not inherit the v3 "zero opposing BOS before context" convention merely because it existed. The design must define which completed structural events invalidate an idea and in what order context, confirmation and structural invalidation are evaluated. No historical threshold sweep and no direction-specific relaxation.

### H02 — decision mark / nearest FTA lifecycle
A new order must not be reserved when completed information already shows the selected nearest structural FTA has been reached/invalidated. Define completed-mark, target validity and cancellation known_at semantics. Never jump to a farther target merely to improve economics.

### H03 — structural resting-entry validity and lifetime
The fixed one-hour v3 order lifetime is project policy, not a source-mandated fact. v4 must define entry lifetime from structural validity / setup lifecycle, or explicitly justify any time expiry before outcomes. No retrospective choice of the duration and no moving an entry toward missed price after observing future path.

### H04 — structural versus executable zone
Define separately the structural idea region and the executable price region under the preregistered synthetic OKX compatibility grids. Zero-width/narrow boundaries must have deterministic adverse handling without inventing historical exchange epochs, widening a zone after the fact or deleting unresolved cases.

### H05 — pre-entry structural payoff / anti-scalp feasibility
Before order reservation, require an explicit structural/economic feasibility contract using only decision-time entry, stop, nearest valid FTA and preregistered round-trip cost assumptions. It may reject structurally poor payoff constructions, but must not use realized outcome, holding time, MFE/MAE or a cutoff selected from the 20 exposed CLOSED cases. Keep structural FTA targets; no fixed-percent TP replacement and no farther-FTA fallback.

## Design constraints
- BTC-USDT-SWAP and ETH-USDT-SWAP on OKX remain the research venue/products.
- Preserve LONG/SHORT symmetry; no SHORT ban from historical performance.
- Preserve SMC/source concepts only where provenance supports them; machine conventions must be labeled PROJECT_POLICY or TECHNICAL_NORMALIZATION.
- Preserve actual signed historical funding binding and the compatibility cost framework for future implementation.
- Preserve adverse same-bar/OHLC ambiguity handling.
- No source claim may be invented for historical tick/filter epochs or ordinary account fee history.
- Development history is exposed. It can support diagnosis but cannot become pristine OOS.

## Required outputs before design PASS
Within `docs/machine_strategy_v4_design_v1/` create/finalize at minimum:
- `MACHINE_STRATEGY_V4_SPEC.md`
- `DECISION_TREE.json`
- `RULE_REGISTRY.json`
- `V3_TO_V4_CHANGELOG.md`
- `OBSERVER_TELEMETRY_SCHEMA.json`
- `EXECUTION_CONTRACT.json`
- `ENTRY_EXIT_CONTRACT.json`
- `QUALIFICATION_PREREGISTRATION.json`
- `CAUSALITY_AND_SYMMETRY_QA.md`
- `INDEPENDENT_REVIEW.md`
- `DESIGN_FREEZE_MANIFEST.json`

Add narrow synthetic tests for every adopted rule and LONG/SHORT mirror. No financial output fields may be imported, generated or used to rank alternatives during design.

## Specialist sequence
Serial only:
1. `strategy_designer` — one design based on the frozen causal hypotheses and source corpus;
2. `execution_auditor` — challenge H02/H03/H04/H05 execution semantics and symmetry;
3. `backtest_reviewer` or `no_lookahead_auditor` — challenge causality, decision-time fields and outcome isolation;
4. `final_independent_reviewer` — accept/STOP design freeze.

Root is sole writer. Hard ceiling root + one specialist at a time.

## Exit decision
Publish exactly one:
- `MACHINE_STRATEGY_V4_DESIGN_PASS` — complete deterministic design frozen before implementation/outcomes;
- `MACHINE_STRATEGY_V4_DESIGN_STOP` — exact material blocker identified.

DESIGN_PASS opens a separately named v4 implementation/readiness gate. It does not authorize historical financial execution, OOS, PAPER, LIVE or platform work.

PAPER=false. LIVE=false. `trade_entry_allowed=false`.
