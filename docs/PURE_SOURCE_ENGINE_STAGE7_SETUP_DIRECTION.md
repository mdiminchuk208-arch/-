# PURE SOURCE Engine — Stage 7: Setup Assembly + Direction

Status: IMPLEMENTED FOR REVIEW

## Scope
Stage 7 assembles SOURCE-valid market objects from Stages 2–6.5 into causal setup objects and derives setup direction from SOURCE evidence. It does **not** choose entry price, stop, FTA/target, exit, remainder, re-entry, risk, ranking, or portfolio policy.

## Baseline
- Upstream strategy baseline: `main` after Stage 6.5 Demand/Supply.
- Strategy profile: `PURE_SOURCE`.
- `trade_entry_allowed=false` remains invariant.
- No private exchange API or live orders.
- Exchange-independent; OKX remains the project primary data source but is not part of setup semantics.

## Source-permitted setup branches represented
- OB direct first-test plan.
- OB repeated-test plan only after causal lower-timeframe reaction.
- Conservative OB refinement: HTF OB reaction -> 1–15m LTF BOS -> one newly formed source-valid POI.
- General conservative after-CONF OB variant, preserved with no precedence over other source-permitted branches.
- SFP -> strictly lower-TF BOS -> one newly formed source-valid POI.
- Breaker direct plan.
- Demand/Supply direct plan with causal Premium/Discount context and freshness kept separate from object existence.
- STB/BTS direct plan.
- Range aggressive external-POI/deviation branch.
- Range conservative deviation -> return/acceptance -> boundary-retest branch.

## Direction contract
Directional objects (OB, SFP, Breaker, D/S, STB/BTS) pass their SOURCE direction into the setup and cannot be overridden by project macro/HTF logic.

Range is different: the Range object stores the impulse that formed it, while a setup direction is derived from the later deviation side (`LOW -> LONG`, `HIGH -> SHORT`). The forming impulse therefore cannot silently override the causal deviation direction.

## Timeframe contract
No universal H1->M5, H4->M15, H4/D1 or other project mapping is SOURCE.

When a branch requires a lower timeframe:
1. the declared context timeframe must match the parent object's timeframe;
2. refinement must be strictly lower;
3. conservative OB refinement also preserves the explicit SOURCE 1–15m scope;
4. an unparseable context timeframe becomes `UNKNOWN`, not an invented mapping.

## Branch ambiguity
No score, ranking, PnL selection or hardcoded branch precedence is used.

For branches requiring a newly formed entry POI:
- zero causal candidates -> `WAIT_NEW_SOURCE_VALID_ENTRY_POI`;
- exactly one causal candidate -> setup may assemble;
- more than one already-known candidate -> `WAIT_NONUNIQUE_ENTRY_POI`;
- future candidates are invisible and cannot retroactively change an earlier unique decision.

Multiple source-valid branches may coexist. Their setup IDs remain distinct while the branch-independent physical idea ID remains stable for the same context/direction.

## Object/setup separation
A valid market object is not invalidated when its setup cannot be assembled. Stage-7 setup objects are created with `trade_eligible=false`; actual entry eligibility belongs to Stage 8/Stage 9 integration after unresolved execution semantics are handled.

## Explicitly unresolved
- precedence among simultaneously source-valid branches;
- generic HTF/LTF mapping outside source-explicit scopes;
- selection among multiple simultaneously valid newly formed POIs;
- generic timeframe/context hierarchy beyond SOURCE wording;
- entry quote and stop anchor;
- FTA/target and exit/remainder;
- re-entry identity/eligibility.

These remain unresolved rather than being filled with PROJECT_POLICY.

## Legacy isolation
`src/crypto_bot/strategy/source_engine.py` and legacy `PureSourceRuntime._capture_setups()` remain historical/adaptation infrastructure and are **not** promoted to Stage-7 SOURCE truth. Stage 7's canonical setup semantics live in `source_setup_v2.py` + `source_setup_rules_v2.json`. Final clean-runtime wiring is deferred to the SOURCE Engine freeze stage so the legacy engine cannot silently define setup precedence.

## Tests
`tests/test_source_setup_v2.py` covers:
- branch-independent physical idea identity;
- distinct branch setup IDs;
- `trade_eligible=false` at assembly;
- parent/refinement timeframe causality;
- unresolved timeframe normalization;
- one causal newly formed POI;
- future-POI mutation safety;
- non-unique POI remains unresolved rather than ranked;
- SFP lower-timeframe relation;
- Range direction derived from deviation rather than forming impulse.

## Deferred to Stage 8
Stage 8 will address only SOURCE-supported execution semantics: Entry + Stop + FTA/Target + Exit/Remainder. Any unresolved rule remains explicit; project TP 40/30/30, cost BE, edge/cost admission, ranking and portfolio overlays remain forbidden from the clean baseline.
