# PURE SOURCE Stage21 — provenance-retaining EQH/EQL consumer

Base: Stage20 merge `a37fd2233321af0cc77643af0c88d7df2e8eb8f0` (PR23). Stage20 exact head `6ef4ef3dd020b3759a9fbf309ea4703362ddaff0` passed Actions39050968731 and local831tests. This stage connects bound claims to one actual diagnostic consumer. All new binding/transport checks are TECHNICAL_NORMALIZATION; SOURCE geometry is preserved, not redefined.

## SOURCE basis

Stage19 `SECONDARY_SOURCE_COMPARISON.json` records exact citations SEC_SW6_SUBSTRUCTURE and SEC_SW6_EQ_TILT: pools form between substructure swings; perfect equality is allowed; a tilted EQH has left high above right, and tilted EQL left low below right. Reasonable tilt has no numeric threshold. Priority1 Methodichka figure19 corroborates a tilted EQL without supplying a bound. Source priority is unchanged. No relevance, adverse-liquidity or trade-admission rule is inferred from pair validity.

## Consumer contract

`assess_bound_equal_liquidity` accepts a journal, actual closed replay frame, explicit pair of swing IDs, kind and exact annotation window. It reconstructs both swings with the canonical closed-three-candle producer. Callers cannot supply fabricated swing prices, generic qualitative IDs or booleans. The window must include both full three-candle footprints. The selected annotation window is an explicit observation boundary, not a new source lookback or expiry parameter.

The consumer resolves EQH_EQL_SUBSTRUCTURE_PAIR internally with OBJECT_FORMATION scope and exact subjects/timeframe/window. Non-flat pairs additionally require EQH_EQL_REASONABLE_TILT. Exact equality requires no separate tilt judgment. Invalid side/order/directional geometry can fail without qualitative inference; no tolerance, ratio, ATR or scoring filter is added.

Every supporting receipt is rebound to the actual consumer prefix and canonical swing objects. A mutation within the witnessed window is rejected even when it preserves swing IDs. Complete semantic/scope/window metadata, assessments, claim IDs, original witness bytes, context hashes and first-observation timestamps survive in the result. The legacy inner result is compatibility data; the returned qualified envelope is the authoritative diagnostic record.

Missing or conflicting evidence stays UNKNOWN, without a fabricated resolution timestamp. A resolved result cannot be known before its swing geometry or required available annotations; late delivery never backfills the pair. Multiple source-valid candidate pairs remain separately addressable, with no automatic selection or ranking.

The adapter does not mutate the journal. Historical read queries may use an earlier prefix after later annotation arrivals; only annotations available by that decision participate. Stage20's caller-clock/authorship/truth/blindness limits still apply. This is not proof that any synthetic annotation is true on market history.

## Integration and blockers

Frozen Stage1–20 code, configs and artifacts remain unchanged. The explicit qualified consumer calls the existing deterministic equal-pair geometry only after its stronger binding checks. Default object/replay providers are not silently switched. There is no formed trade, READY or order from this adapter; `trade_entry_allowed` is an immutable false field on the result.

A separate source comparison rejected direct OB/Breaker legacy wrapping: universal adjacent body engulf, HTF POI and pre-existing same-direction structure would incorrectly harden one intersection; generic BOS does not encode Methodichka's CHOCH-or-continuation alternatives. Boolean IMB and loose sweep references do not prove the qualifying movement ancestry. New priority1 OB/Breaker transport still needs explicit movement/event/IMB/sweep relation contracts; no Range/OTE annotation is repurposed as an OB oracle. These findings are preserved in `MIGRATION_FRONTIER.json` rather than changing frozen consumers.

Next independent safe target: a provenance-retaining SFP liquidity-context assessment that remains separate from structural SFP validity and from trade admission. Actual market annotation sets, unresolved anchor/segment geometry, adverse-liquidity direction and execution/remainder/re-entry semantics remain source blockers. Baseline is NOT_IDENTIFIABLE and all financial/trading/private-API permissions remain false.

## Validation

Targeted cases cover exact and tilted pairs, negative/conflicting/missing annotations, late delivery, wrong semantics/subjects, actual swing membership, complete windows, context tampering, gaps/unfinished/future data, mirrored EQH/EQL dependencies, repeat/prefix/future-mutation and two-receipt input-order invariance. Fixtures are synthetic QA, not market-valid trading cases. Independent review and final full-suite logs/manifest are under `docs/pure_source_stage21_qa_v1/`.
