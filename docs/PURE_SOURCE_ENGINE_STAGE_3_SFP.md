# PURE SOURCE ENGINE — STAGE 3: SFP

Status: IMPLEMENTING

Base merge commit: `c9005f4ced9356805d8cb4cb7c2e3c4e52f152c8`

Branch: `pure-source-engine-stage-3-sfp`

Scope: SOURCE SFP object formation and invalidation lifecycle only. No entry optimization, no project score/rank, no finite wait timeout, no portfolio overlay, no live orders.

`trade_entry_allowed=false` remains invariant.

## SOURCE contract

### Formation

From SW8 p5:

1. external liquidity already exists at a structural swing or range boundary;
2. price sweeps/false-breaks that external liquidity;
3. the sweep candle body closes back inside the level;
4. the immediate next candle opens back inside the level;
5. only after the pattern is complete may the strategy move to LTF and wait for BOS.

This means **SFP object validity is independent from later LTF BOS**.

The clean engine records SFP `formation_at == known_at == immediate next candle open time`. The next candle does not need to be closed because future H/L/C values are not part of formation.

### Direction

- high-side external-liquidity sweep -> bearish/SHORT SFP;
- low-side external-liquidity sweep -> bullish/LONG SFP.

The lower-side representation is the deterministic mirror already preserved by prior source rechecks.

### Invalidation

SW12 p13: SFP becomes irrelevant after a later candle **body close** beyond pattern min/max.

Machine representation of pattern min/max:

- LONG SFP -> sweep-candle low;
- SHORT SFP -> sweep-candle high.

This mapping is `TECHNICAL_NORMALIZATION: TN_SFP_PATTERN_EXTREME_SWEEP_CANDLE`.

A later wick beyond the extreme without body close does not invalidate.

Invalidation is append-only. It changes current lifecycle status but cannot erase the fact that the SFP was source-valid before invalidation.

## External-liquidity parents

Stage 3 accepts two SOURCE origins:

- structural external liquidity from Stage 2;
- a source-valid Range boundary object.

Internal liquidity is not accepted as the external-liquidity anchor for this SFP path.

Range detection itself remains deferred to Stage 6. The Stage-3 Range adapter is only the typed contract by which a future clean Range object may become an SFP parent.

## Causality

External liquidity must be causally known no later than sweep-candle open. A level discovered after the sweep begins cannot be used retroactively.

This is an explicit causality normalization, not a profitability filter.

The sweep candle must be closed before its reclaim condition is accepted.

Only the immediate next candle's `open_time` and `open` are read. Its still-forming/future high, low and close are forbidden from influencing SFP identity or validity.

## Timeframes

Prior source recheck confirms:

- SFP may form on any timeframe;
- H1+ is preferred for search;
- H1+ is not a mandatory validity gate.

Therefore no H1/H4 project admission filter is allowed in the clean SFP detector.

## No finite expiry

SOURCE does not define a fixed number of bars/minutes in which LTF BOS must arrive.

Any historical `max_wait_ltf_bars`, minutes window or similar expiry is `BACKTEST_PARAMETER` and is disabled for PURE_SOURCE baseline.

Right-censoring at dataset end is not the same thing as expiry.

## Dual-sided formations

If one causal episode produces source-valid opposite-direction SFP objects at the same formation time, preserve both historical objects.

The source does not define a deterministic trade-direction selection for that edge case. Therefore later setup admission must remain ambiguous/WAIT rather than deleting one SFP or choosing by score/PnL.

## Object vs trade chain

A clean SFP object:

- `formation_valid=true` once the SOURCE pattern completes;
- `trade_eligible=false` at formation;
- exposes `requires_ltf_bos=true` as a later chain requirement;
- may later become invalidated by body close beyond pattern extreme;
- is never retrospectively erased by invalidation, missing BOS, dataset end or bad PnL.

## Stage 3 files

- `src/crypto_bot/strategy/source_sfp_v2.py`
- `tests/test_source_sfp_v2.py`
- `config/source_sfp_rules_v2.json`
- `docs/PURE_SOURCE_ENGINE_STAGE_3_SFP.md`

## Acceptance criteria

Stage 3 is complete only when:

1. structural external liquidity can form SFP causally;
2. range-boundary parent contract exists without importing legacy range thresholds;
3. sweep candle must be closed;
4. immediate next open completes formation without reading future next-candle H/L/C;
5. object ID is stable under future H/L/C mutation;
6. SFP remains trade-ineligible until later chain logic;
7. body-close invalidation is append-only and wick-only invalidation is rejected;
8. no finite expiry is introduced;
9. SFP below H1 remains source-valid;
10. dual-side same-time formations preserve both objects and flag chain ambiguity;
11. full unit suite and safety invariant are green;
12. no PROJECT_POLICY enters the path.

## Deferred

- LTF BOS -> entry POI/setup assembly: later setup stages;
- OB/Breaker: Stage 4;
- FVG/IMB/OTE/PD: Stage 5;
- clean Range construction: Stage 6;
- entry/stop/FTA/exit/re-entry: later stages.
