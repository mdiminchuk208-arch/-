# PURE SOURCE ENGINE — STAGE 5: IMB/FVG + OTE + PREMIUM/DISCOUNT

Status: IMPLEMENTING

Base merge commit: `5648713afeb71cbc1260535698830212df100453`

Branch: `pure-source-engine-stage-5-imb-ote-pd`

Scope: deterministic SOURCE geometry for Imbalance/FVG, Equilibrium/Full Fill, OTE and Premium/Discount context. No entry execution, stop, FTA, RR threshold, scoring, PnL or portfolio policy.

`trade_entry_allowed=false` remains invariant.

## 1. Imbalance / FVG

### SOURCE geometry

SW8 defines Imbalance as price inefficiency caused by an impulsive movement and gives explicit outer-candle zone boundaries:

- bullish IMB: previous-candle **high** to post-impulse-candle **low**;
- bearish IMB: post-impulse-candle **high** to previous-candle **low**.

Методичка p11 likewise says IMB is an impulsive movement leaving price inefficiency and that the zone is marked by the neighboring candle shadows/wicks.

Stage 5 therefore uses a three-candle wick-gap representation.

### Strict positive gap

If the outer wicks only touch, zone width is zero. Stage 5 does not emit an IMB object.

This is explicit:

`TECHNICAL_NORMALIZATION: TN_IMB_STRICT_POSITIVE_GAP`

No minimum ATR, percent, ticks or displacement-size filter is added.

### Causality

The third candle's high/low is part of the final zone boundary. Therefore a stable IMB object is emitted only after the third candle closes.

`formation_at == known_at == third_candle.close_time`

This prevents an intrabar low/high mutation from rewriting a previously emitted object.

### Equilibrium

SW8 explicitly defines Equilibrium as `0.5` of the IMB zone.

Stage 5 uses the exact arithmetic midpoint:

`equilibrium = (zone_low + zone_high) / 2`

No tolerance is used.

### Full Fill

SW8 defines Full Fill as complete coverage of the price inefficiency.

Stage 5 records later interaction facts separately:

- equilibrium touched;
- full fill reached.

These later facts do not alter IMB object identity or erase its historical formation.

### No future-guarantee filter

SOURCE describes IMB as a magnet and says price tends toward equilibrium/full fill. Stage 5 preserves that as descriptive SOURCE context only.

It is **not** converted into:

- guaranteed target;
- trade admission condition;
- PnL expectation;
- future-fill requirement for historical IMB validity.

## 2. OTE

Методичка p16-18 gives explicit OTE geometry:

- important Fibonacci levels include 0.5, 0.62, 0.705 and 0.79;
- OTE is the range `0.705–0.79`;
- the tool complements the strategy rather than replacing context;
- OTE is especially used with Order Block.

### Critical Stage-5 boundary

OTE ratios are exact, but **anchor selection is not automatically solved by those ratios**.

The old engine must not take arbitrary latest high/low points and call them an OTE impulse.

Stage 5 accepts only `SourceImpulseReference` containing:

- direction;
- chronological start/end prices;
- causal `known_at`;
- parent SOURCE object ids;
- evidence id;
- provenance.

Only then is the 0.705–0.79 geometry computed.

The produced OTE zone is represented as a SOURCE POI-style object but remains:

`trade_eligible=false`

OTE alone never creates a trade.

## 3. Premium / Discount

SOURCE materials repeatedly use 0.5 as fair price/equilibrium and refer to Premium/Discount context around that midpoint. SW9 warns against OB outside OTE / Premium-Discount context, and SW22 mitigation material also centers the 0.5 zone.

Stage 5 therefore implements only deterministic midpoint classification:

- below 0.5 of an already-qualified dealing range -> `DISCOUNT`;
- exactly 0.5 -> `EQUILIBRIUM`;
- above 0.5 -> `PREMIUM`.

### No invented dealing range

This stage **does not** detect a dealing range from arbitrary extrema.

`SourceDealingRangeReference` requires:

- already-known low/high endpoints;
- causal `known_at`;
- parent SOURCE object ids;
- evidence id;
- provenance.

If the range is not source-qualified, Premium/Discount is not calculated.

Clean Range construction itself remains Stage 6 / later evidence work.

## 4. Relationship to Stage 4 OB

Stage 4 deliberately leaves OB-without-IMB as explicit SOURCE conflict/UNKNOWN.

Stage 5 now supplies a clean causal IMB/FVG object contract that later integration may use as evidence for OB formation.

Stage 5 does **not** retroactively re-run historical OB candidates or silently change Stage-4 objects. Integration must happen explicitly in a later assembly step with causal timestamps.

## 5. Legacy code boundary

Existing `trade_plan.py` contains OTE geometry and older structural-anchor helpers. The numeric 0.705–0.79 calculation is compatible with SOURCE, but old anchor-selection logic is not automatically promoted to canonical PURE_SOURCE.

The canonical Stage-5 path is `source_imb_ote_pd_v2.py`.

Legacy FVG creation inside older `SourceSeries` is diagnostic/history only until explicitly migrated to this clean contract.

## Deferred

- automatic impulse anchor selection where SOURCE geometry is ambiguous;
- clean dealing-range construction;
- OB/IMB integration and setup assembly;
- OTE/PD as entry admission rules;
- stop;
- FTA/target;
- RR threshold;
- STB/BTS and Range;
- scoring/ranking;
- transaction-cost filters;
- portfolio/risk overlays.

## Acceptance criteria

Stage 5 is complete only if:

1. bullish and bearish IMB/FVG use exact SOURCE wick-gap boundaries;
2. all three candles are closed and contiguous;
3. equality/touch does not invent a zero-width IMB;
4. stable IMB object is known only after third-candle close;
5. equilibrium is exact 0.5;
6. later equilibrium/full-fill facts never change object ID/history;
7. no minimum FVG size threshold is invented;
8. OTE is exactly 0.705–0.79;
9. OTE cannot be built without a source-qualified impulse reference;
10. OTE remains trade-ineligible;
11. Premium/Discount is calculated only from a source-qualified dealing range;
12. no arbitrary extrema are promoted to dealing range/OTE anchors;
13. no future fill, PnL, scoring or PROJECT policy enters identity or validity;
14. full unit suite and safety invariant are green.
