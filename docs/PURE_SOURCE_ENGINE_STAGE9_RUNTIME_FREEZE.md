# PURE SOURCE Engine — Stage 9: Runtime Freeze

Status: IMPLEMENTED FOR REVIEW

## Goal
Stage 9 freezes the canonical PURE_SOURCE runtime after Stages 1–8. The runtime no longer derives setup/admission truth through the historical strategy engine. It only accepts causal SOURCE evidence produced by the new Stage-2..8 modules.

## Canonical path

`closed candles / causal clock`
→ `Stage 2–6.5 market objects`
→ `Stage 7 setup assembly`
→ `Stage 8 execution semantics`
→ `PureSourceRuntime`

The runtime persists evidence, validates causal parentage, records unresolved SOURCE blockers, and exposes SOURCE-ready state separately from order permission.

## Hard invariants
- `trade_entry_allowed=false` always.
- no private exchange API and no live order path.
- no PROJECT_POLICY in the canonical PURE_SOURCE evidence path.
- no ranking, score, PnL, MFE/MAE, cost filter or portfolio overlay may resolve SOURCE ambiguity.
- object existence/validity is independent from setup validity.
- setup validity is independent from Stage-8 execution completeness.
- SOURCE-ready is independent from live trading permission.
- all consumed evidence must already be known at the runtime observation time.
- a future confirmation, invalidation or lifecycle mutation cannot be imported into an earlier prefix.
- the decision watermark is monotonic.
- Stage-7 causal parents must be registered before the setup.
- Stage-8 unresolved items become explicit runtime blockers.

## Removed from canonical runtime
The previous runtime instantiated the historical strategy engine by default, adapted its zones/events/setups and promoted legacy `ready_id` into trade eligibility. That behavior is no longer canonical and has been removed from `PureSourceRuntime`.

The canonical class does not import the historical strategy engine, virtual/project portfolio implementation or exchange adapter.

Calling the old adapter-style `advance(timeframe, index)` interface now fails loudly. The runtime clock is advanced with `observe_candles(...)`, while market-object detection remains in the dedicated Stage-2..8 causal modules.

## Runtime API

### `observe_candles(candles, decision_at=...)`
Validates closed-candle/no-future semantics and advances only the causal runtime watermark.

### `register_object(obj, observed_at=...)`
Persists a causal market object. Trade admission never controls whether the object exists.

### `register_setup(SourceSetupEvidence, observed_at=...)`
Accepts Stage-7 output only after its context/entry parents are registered. The setup cannot arrive pre-admitted.

### `register_execution_plan(SourceExecutionPlan, observed_at=...)`
Accepts Stage-8 output. Any unresolved SOURCE semantics are copied into runtime blockers. A mechanically complete SOURCE plan may mark the setup `trade_eligible`, but the global runtime still keeps `trade_entry_allowed=false`.

### `register_execution_assessment(...)`
Preserves `PASS / UNKNOWN / FAIL` from Stage 8. UNKNOWN/FAIL becomes a blocker instead of a guessed execution rule.

### `finish()`
Returns a deterministic runtime summary including:
- strategy profile/version;
- global trade permission (`false`);
- object/setup/execution-plan counts;
- SOURCE-ready setup IDs;
- decision watermark;
- unresolved blockers.

## What Stage 9 does not do
Stage 9 does not invent a universal automatic detector/orchestrator for every qualitative SOURCE term. Those terms remain inside their dedicated Stage-2..8 evidence modules and retain explicit UNKNOWN states where the source is not machine-identifiable.

Stage 9 also does not run a money/PnL backtest. Objective historical replay belongs to the Market Data + Backtest + QA branch after the clean SOURCE runtime is frozen.

## Next gate
Before declaring PURE SOURCE baseline executable for backtest:
1. full repository CI must pass;
2. no forbidden import may exist in the canonical runtime;
3. prefix/no-look-ahead tests must pass;
4. unresolved Stage-8 geometry must remain visible rather than silently normalized;
5. a deterministic adapter from reproducible market-data replay into Stage-2..8 evidence must be validated separately.
