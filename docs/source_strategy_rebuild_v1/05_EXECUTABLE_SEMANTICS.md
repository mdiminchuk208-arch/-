# Source Strategy Rebuild v1 — executable semantics

State: `STAGE_2_IN_PROGRESS`. No financial outcomes are authorized.

## Global causal clock

- Only completed candles may publish source objects.
- A candle becomes knowable at its `end` timestamp.
- A three-bar pivot centered on candle `i` becomes knowable only after candle `i+1` completes.
- A setup may reference only objects whose `known_at <= decision_at`.
- Stable object IDs are hashes of immutable source identity fields; future candles may not change an already-published ID.

## Structure

`TN_SWING_001` is the initial explicit technical normalization:
- swing high: center high strictly greater than both adjacent highs;
- swing low: center low strictly lower than both adjacent lows.

The detector retains ordered swing objects. Consecutive same-side structural extrema are classified by price relation:
- high > previous high => HH;
- high < previous high => LH;
- low > previous low => HL;
- low < previous low => LL;
- equality remains `UNKNOWN_EQUAL_STRUCTURE` rather than being forced into a trend label.

Trend state is evidence, not a trade by itself. A bullish structure requires source-consistent HH/HL evidence; bearish requires LL/LH evidence. Ambiguous/incomplete sequences remain UNKNOWN.

## BOS / CHOCH

The source says a protected structural point is broken and the opposite structure is then expected. Because a universal exact body/wick equation is not fully stated, Stage 2 uses explicit normalization `TN_BOS_001`:
- bullish BOS publication: completed close above the relevant protected high/LH;
- bearish BOS publication: completed close below the relevant protected low/HL;
- wick-only excursion does not publish BOS.

`CHOCH` is not silently equated with every BOS. Until a complete source distinction is resolved, the engine publishes a structural break event plus prior-trend context, and exposes `UNKNOWN_CHOCH_EXACT_SEMANTICS` where a family explicitly requires CHOCH.

## Imbalance

`TN_IMBALANCE_001` creates wick-gap geometry without an arbitrary minimum-size threshold:
- bullish: bar3.low > bar1.high; zone `[bar1.high, bar3.low]`;
- bearish: bar3.high < bar1.low; zone `[bar3.high, bar1.low]`.

This detects geometric inefficiency only. The source word `sharp/impulsive` is separately `UNKNOWN_IMPULSE_STRENGTH`; it may not delete the geometric object during coverage telemetry.

## Order Block

A raw OB candidate can be anchored to the last candle preceding a source-compatible imbalance/impulse sequence and must retain evidence links for:
- structural update/BOS relationship;
- whether that candle swept/took an already-known high/low/wick;
- body/wick geometry.

Stage 2 must not invent thresholds for `large body` / `small wicks`. Therefore raw OB evidence is emitted with:
- `UNKNOWN_OB_BODY_LARGE`;
- `UNKNOWN_OB_WICKS_SMALL`;
- `UNKNOWN_OB_ZONE_GEOMETRY` where executable zone choice is required.

These UNKNOWN states block a final actionable order later, but **do not erase the raw source formation from detector coverage**.

## Breaker

A raw Breaker requires a prior OB identity, subsequent high/low sweep relationship, a break through that OB with imbalance evidence, and a structural-break/CHOCH requirement. Because CHOCH and exact return/entry geometry remain incomplete, the breaker can exist as a causal formation while final actionability remains UNKNOWN.

## Liquidity

The engine may publish exact known liquidity objects without inventing tolerances:
- exact-equality highs/lows can be tagged `EXACT_EQH/EQL`;
- structural swing highs/lows remain potential stop/liquidity locations;
- trendline-liquidity candidates require a separate normalization before deterministic validation.

Near-equal highs/lows are not silently rejected. They are retained as unresolved potential objects under `UNKNOWN_EQH_EQL_TOLERANCE` until the normalization is frozen.

## Range / Deviation

The source gives a boundary construction example (first high after impulse, first low) and requires sideways behavior, deviation, return and midpoint/0.5 reaction. Stage 2 may publish raw range-boundary candidates and deviation events, but final range validity remains UNKNOWN where `range clarity`, `absence of structure`, or required reaction count is not numerically specified.

A deviation event is causal when a completed candle trades beyond a known range boundary. Return/reclaim evidence is separately published when a later completed candle returns inside. No future bar may retroactively make an earlier range candidate valid.

## OTE

Given frozen impulse endpoints `(low, high)`, OTE geometry itself is exact:
- equilibrium 0.5;
- source levels 0.62, 0.705, 0.79;
- OTE interval 0.705–0.79 of the selected retracement.

However the source wording for long Fibonacci anchoring is ambiguous. Stage 2 therefore supports deterministic level calculation once direction/anchor order is supplied, while emitting `UNKNOWN_OTE_LONG_ANCHOR_DIRECTION` when source identity does not resolve that order. OTE is evidence, never a standalone trade trigger.

## SFP

The source facts that are directly usable are:
- sweep of stops above/below an already-known swing/range level;
- reversal/no body acceptance beyond the swept area;
- mandatory context;
- original pattern described as three candles with optional fourth confirmation;
- applies on all timeframes.

`TN_SFP_001` therefore emits a **raw candidate**, not a final trade:
- bearish: completed candle high > known level and close <= level;
- bullish: completed candle low < known level and close >= level.

Candidate retains the surrounding completed candles and context IDs. Exact three-candle role assignment, optional fourth confirmation and context priority remain explicit UNKNOWN fields until frozen. This prevents the old failure mode where ambiguity became a hard rejection and erased opportunities.

## AMD

AMD remains context telemetry in Stage 2. Accumulation/manipulation/distribution labels may be emitted only when their machine semantics are separately normalized. No AMD label by itself may create or reject a financial trade.

## Opportunity states

Detector records use these nonfinancial stages:
- `FORMATION` — source geometry exists;
- `CANDIDATE` — enough source conditions exist to evaluate the family;
- `ACTIONABLE_SOURCE_SETUP` — all required SOURCE rules and frozen technical normalizations for that family are resolved;
- `UNKNOWN_SOURCE_SEMANTICS` — source formation exists but at least one necessary semantic is unresolved;
- `SOURCE_REJECT` — a directly applicable source rule is definitively false.

`UNKNOWN_SOURCE_SEMANTICS` is not equivalent to `SOURCE_REJECT`.

## No financial fields

Stage 2/3 records must not contain WIN/LOSS, P&L, MFE/MAE, future TP/SL outcome, fee/funding result or outcome-derived labels. `trade_entry_allowed=false` throughout.
