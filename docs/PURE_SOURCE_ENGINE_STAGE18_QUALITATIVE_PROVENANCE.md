# PURE SOURCE Engine — Stage 18: Causal Qualitative Provenance

Stage 18 follows the Stage 17 non-ranked branch registry. It formalizes how genuinely qualitative SOURCE facts may be supplied to the engine without inventing numeric thresholds.

It does **not** decide whether a qualitative claim is true. It defines the audit contract required before a PASS/FAIL qualitative judgment may be consumed by later object providers.

## Problem

The frozen SOURCE contains terms such as:

- aggressive / strong / fast impulse;
- large body / small wicks;
- continuous movement without trading inside an OB;
- no internal Range structure;
- reaction from the Range midpoint;
- full engulf of STB/BTS manipulation;
- last rising/falling movement for Demand/Supply;
- EQH/EQL substructure and reasonable tilt;
- source-qualified impulse segmentation;
- SFP liquidity context.

Some exact geometry around these concepts is known, but SOURCE does not provide a universal numeric threshold for the qualitative part. Converting them into ATR multiples, candle-body percentages, arbitrary tolerances, scores or ML probabilities would create a new strategy rule.

## Stage 18 contract

`SourceQualitativeClaim` records:

- one frozen semantic ID;
- scope: `OBJECT_FORMATION` or `TRADE_CONTEXT`;
- PASS / FAIL / UNKNOWN;
- symbol and timeframe;
- exact observation window;
- `known_at`;
- subject/parent object IDs;
- frozen source references and rule IDs from the semantic catalog;
- annotation method;
- immutable provenance reference;
- rationale code;
- canonical evidence ID.

For PASS or FAIL, provenance is mandatory. The evidence ID is a SHA-256-derived canonical identity over the causal claim payload.

UNKNOWN is deliberately different: it has no annotation method, provenance reference, rationale or evidence ID. This prevents an unknown fact from being passed downstream as if it were audited evidence.

## Causality

A claim cannot be known before the end of its observed closed-data window:

`known_at >= observation_end_at`

Consumers can call `available_at(decision_at)`; a claim with a future `known_at` is unavailable to the earlier decision.

The contract does not contain future outcome fields and the catalog rejects ranking/proxy metadata.

## Frozen annotation methods

Stage 18 permits only:

- `HUMAN_SOURCE_ANNOTATION`
- `CURATED_SOURCE_DATASET_ANNOTATION`

This is intentionally conservative. A model score, probability or auto-generated threshold is not source evidence merely because it predicts the historical label well.

Future automation would require a separately audited deterministic/source-supported derivation contract; it is not silently admitted here.

## Semantic catalog

The Stage 18 catalog currently freezes qualitative semantics for:

- OB aggressive impulse;
- OB large body / small wicks;
- Breaker fast/whole impulse;
- Breaker continuous no-OB trading;
- source-qualified impulse segmentation for Range/OTE;
- Range strong directional impulse;
- Range midpoint reaction;
- Range no internal structure;
- STB/BTS full manipulation engulf;
- Demand/Supply last-movement segmentation;
- EQH/EQL substructure pair;
- EQH/EQL reasonable tilt;
- SFP liquidity context.

The catalog is source-referenced and does not itself assert PASS/FAIL on any market instance.

## Object vs trade-context boundary

Stage 18 explicitly types claim scope.

Most geometry claims are `OBJECT_FORMATION`. `SFP_LIQUIDITY_CONTEXT` is `TRADE_CONTEXT`, because the source allows structural SFP formation broadly but requires liquidity context for trading use.

A claim cannot be moved between scopes without failing catalog validation.

This protects the existing invariant:

`OBJECT VALIDITY != TRADE ELIGIBILITY`.

## Compatibility boundary

`project_legacy_qualitative()` can project an audited Stage 18 claim into the old status/evidence-id/known-at shape used by existing Stage 4/6 consumers.

The projection is only a compatibility transport. The full `SourceQualitativeClaim` must remain the authoritative audit record. Stage 18 does not yet replace every legacy `QualitativeEvidence` construction site; consumer migration is a separate next step so that the contract can be audited before changing object behavior.

## Explicitly forbidden

The catalog rejects fields such as:

- rank / score / weight / preferred;
- confidence / probability;
- win rate / profit factor / expectancy / PnL / backtest result.

It also enforces:

- `trade_entry_allowed=false`;
- financial backtest permission = false;
- numeric proxy inference = false;
- `project_policy_applied=[]`.

Therefore Stage 18 cannot be used to select a branch because it performs better and cannot make a qualitative SOURCE term numeric by optimization.

## Files

- `config/pure_source_qualitative_semantics_v2.json`
- `src/crypto_bot/strategy/source_qualitative_provenance_v2.py`
- `tests/test_source_qualitative_provenance_v2.py`

## Next safe step

After this contract passes repository validation, migrate qualitative consumers incrementally so that OB/Breaker, Range/STB, Demand/Supply and EQH/EQL consume audited claims or stay UNKNOWN. Each migration must preserve closed-candle causality and must not change SOURCE definitions.

The PURE SOURCE financial baseline remains `NOT_IDENTIFIABLE`; PAPER/LIVE/private exchange execution stays forbidden.
