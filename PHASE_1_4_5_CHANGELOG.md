# Phase 1.4.5 v0.4.5 changelog

## Goal
Close the previously explicit `RANGE_BOUNDARY_SFP_NOT_IMPLEMENTED` gap without pretending that the source's qualitative range language has numeric definitions it does not provide.

## Source-aligned range rules implemented
- A range follows a strong directional impulse.
- End of impulse = boundary #1; end of correction = boundary #2.
- Up impulse: first boundary high, later second boundary low. Down impulse: first boundary low, later second boundary high.
- A good reaction around 0.5 confirms that the range boundaries are drawn correctly.
- Structure should be absent inside a range.
- Range boundaries are external liquidity and are valid SFP liquidity sources.
- Deviation is source-defined as price moving beyond a range boundary to take external liquidity; v0.4.5 therefore does not silently equate every outside close with automatic destruction of the whole range.
- A completed range-boundary SFP still requires the same return-inside formation semantics and later LTF BOS before entry-search eligibility.

## Explicit technical normalizations / backtest parameters
- `strong impulse` has no numeric threshold in the source. v0.4.5 uses a causally confirmed structural BOS as a conservative impulse proxy. This can under-detect ranges and is not presented as a source rule.
- `good reaction at 0.5` has no numeric tolerance in the source. v0.4.5 requires a confirmed three-candle swing within `midpoint_tolerance_fraction * range_width` of 0.5. Default `0.08` is a BACKTEST_PARAMETER.
- An in-range BOS is the machine proxy for the source requirement that structure should be absent inside the range.
- The first strict raid of an established range boundary consumes that original boundary liquidity for SFP purposes. If the sweep candle does not close back inside, no SFP forms, but the whole range is not hard-invalidated solely by that outside close because the source explicitly allows deviations beyond range boundaries.
- Boundary raids observed after boundary #2 is causally known but before midpoint validation are not retroactively turned into SFPs; they still consume the original boundary liquidity.
- A same-candle sweep of both range boundaries is preserved as ambiguous and does not auto-create two opposite SFPs.

## New implementation
- `src/crypto_bot/strategy/range_engine.py`
- `src/crypto_bot/range_report.py`
- Range-boundary SFPs are merged with structural-swing SFPs before MTF BOS linkage.
- SFP provenance is explicit: `STRUCTURAL_SWING` or `RANGE_BOUNDARY`, with `range_id` for range contexts.
- Range IDs use collision-free negative level/episode IDs when represented in the common SFP event pipeline.

## New reports
For every HTF/LTF pair:
- `range/ranges.csv`
- `range/range_sweep_episodes.csv`
- `range/range_sfp_events.csv`
- `range/summary.json`

MTF candidate/audit outputs now also include SFP liquidity origin and range ID.

## Entry status
Trade Entry remains blocked. Range-boundary SFP is now implemented, but range machine normalizations still require chart/backtest validation. Remaining blockers include range normalization validation, cross-pair cluster parameter freeze, and Entry Zone/SL/FTA/TP/RR.
