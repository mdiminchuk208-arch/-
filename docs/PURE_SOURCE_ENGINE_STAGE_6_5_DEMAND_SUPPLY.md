# PURE SOURCE ENGINE — STAGE 6.5: DEMAND / SUPPLY

Status: IMPLEMENTING

Parent Stage-6 head: `dcee2f23df3a90da005e54cb22a3ff25991879e2`

Branch: `pure-source-engine-stage-6-5-demand-supply`

Verified source material:

`Криптология/Зоны_спроса_и_предложения_Demand_and_Supply.docx`

SHA256:

`824a8a97902d84f85099aa10db6c13c8c008c6f818b188453af8ede6ccdbb020`

Classification: confirmed secondary ORIGINAL SOURCE material. It may extend the clean object inventory but cannot override contradictory higher-priority Методичка/SW material.

`trade_entry_allowed=false` remains invariant.

## SOURCE rules

The material states:

- Supply = the last rising movement, which may be one candle on a higher timeframe or several consecutive candles on a lower timeframe.
- Demand = the last falling movement, likewise one or several consecutive candles.
- The movement forming the zone **must** raid old liquidity.
- Supply and Demand zones are untested/fresh.
- Supply is valid for sales in Premium.
- Demand is valid for buys in Discount.

## Object vs contextual eligibility

Stage 6.5 deliberately separates two layers.

### Historical market object

Movement + old-liquidity raid may form a Demand/Supply POI object.

The object records:

- zone bounds;
- direction;
- movement evidence id;
- raid evidence id;
- causal timestamps;
- parent object ids;
- SOURCE rule ids.

It remains `trade_eligible=false`.

### Contextual eligibility

Freshness and Premium/Discount are evaluated separately at a decision time.

This means:

- a future first test can make the zone no longer fresh for a later setup;
- a future test does **not** erase the fact that the zone existed historically;
- missing Premium/Discount evidence yields `UNKNOWN`, not a fabricated PASS/FAIL;
- a Premium/Discount fact that becomes known later cannot be projected backward.

## Qualitative last-movement geometry

The SOURCE explicitly allows one candle or several consecutive candles but gives no deterministic algorithm for segmenting the exact `last movement` from raw OHLC.

Therefore Stage 6.5 does not invent:

- a fixed candle count;
- ATR/displacement thresholds;
- body-size thresholds;
- a fitted lookback window.

`SourceMovementReference` carries PASS / FAIL / UNKNOWN qualitative evidence with provenance and `known_at`.

- PASS with provenance may form a D/S object.
- FAIL rejects the candidate.
- UNKNOWN remains `WAIT_LAST_MOVEMENT_QUALITATIVE_PROVENANCE`.

## Direction mapping

- falling last movement + low-side old-liquidity raid -> `DEMAND`, LONG context;
- rising last movement + high-side old-liquidity raid -> `SUPPLY`, SHORT context.

A raid occurring only after the forming movement is complete cannot retroactively create the zone.

## Premium / Discount

Stage 6.5 consumes the Stage-5 `PremiumDiscountEvidence` contract.

It does not create a dealing range itself.

- Demand -> Discount required for context eligibility.
- Supply -> Premium required for context eligibility.
- Equilibrium is neither Demand-Discount nor Supply-Premium for this rule.

## Freshness

`first_test_at` is a later lifecycle/context fact and is excluded from stable object identity.

At a decision time:

- no known first test -> fresh;
- first test already occurred -> contextual FAIL: `ZONE_ALREADY_TESTED_NOT_FRESH`.

The historical object remains `formation_valid=true`.

## Deferred

- exact entry quote within D/S zone;
- stop behind movement extreme;
- FTA/target;
- RR;
- selection among D/S, OB, Breaker, SFP, STB/BTS, Range branches;
- automatic raw-OHLC movement segmentation until source-supported or qualitatively annotated.

## Acceptance criteria

Stage 6.5 is complete only if:

1. Demand/Supply object formation requires a causal old-liquidity raid;
2. Demand/Supply direction mirrors falling/rising movement semantics;
3. last-movement ambiguity is PASS/FAIL/UNKNOWN, not a hidden numeric algorithm;
4. a later raid cannot retroactively create the zone;
5. object identity excludes future first test and future PnL;
6. Premium/Discount is causal context, not backfilled from the future;
7. later first test removes freshness without deleting the historical object;
8. Demand requires Discount, Supply requires Premium for context eligibility;
9. all D/S objects remain trade-ineligible;
10. no PROJECT policy, ranking, cost filter or PnL optimization enters the path;
11. full unit suite and safety invariant are green.
