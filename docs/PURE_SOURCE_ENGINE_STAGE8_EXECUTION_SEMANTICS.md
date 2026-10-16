# PURE SOURCE Engine — Stage 8: Entry + Stop + FTA/Target + Exit/Remainder

Status: IMPLEMENTED FOR REVIEW

## Scope
Stage 8 records only SOURCE-supported execution semantics for setups already assembled by Stage 7. It does not send orders, enable trade admission, optimize variants, rank branches, choose by PnL, or apply PROJECT risk/portfolio/economic overlays.

`trade_entry_allowed=false` remains invariant.

## Direct SOURCE findings

### Order Block — SW9 p3-6
Direct variant:
- in roughly 90% of examples/work, use the first OB test;
- LONG limit may be placed at the upper OB boundary;
- SHORT limit may be placed at the lower OB boundary;
- source also permits limits inside the OB zone;
- stop may be beyond the OB minimum/maximum;
- alternatively stop may be beyond the wick/extreme of the candle that engulfed the OB.

SOURCE does not define which entry/stop variant must win when more than one is available, nor the exact buffer beyond a stop anchor. Stage 8 therefore preserves variants and marks selection unresolved.

Conservative variant:
- HTF OB -> lower TF 1–15m -> reaction -> BOS -> new POI -> limit order on the new POI.
- SOURCE does not give a universal exact quote inside that new POI or a unique stop rule for the refined POI.

### Breaker — SW9 p7-10
Breaker is a tradable POI. Two stop variants are explicitly described:
- aggressive immediately beyond the Breaker;
- conservative beyond the liquidity-sweeping impulse candle minimum/maximum.

Exact quote inside the Breaker and exact beyond-anchor stop buffer are not uniquely specified.

### FTA — SW9 p11-16
FTA is the first trouble area after the character/trend shift and may be an opposing higher-timeframe POI. Both trend and countertrend sections place TP at FTA; source permits full or partial fixation.

Technical normalization used only to make `first` causal/deterministic:
- consider only already-known, active, unconsumed opposing higher-TF POIs;
- the first contact with a price zone is its near edge (low edge for LONG, high edge for SHORT);
- future POIs and future consumption cannot change an earlier FTA decision.

The full-vs-partial fraction remains unresolved.

### SFP — SW8 p5 + SW12 p12-14
After a completed SFP, move to lower TF, wait for BOS, then seek an entry. Exact quote is not defined by SW8.

SW12 supports ATR-based protective stops:
- ATR distance is measured from the relevant SFP lower/upper pattern point;
- standard ATR setting is 14;
- source also says the period may be changed depending on strategy;
- protective stop is not moved merely to survive repeated tests;
- a candle body close beyond the SFP pattern minimum/maximum makes the pattern irrelevant.

Stage 8 can calculate an ATR stop from supplied causal ATR evidence. Period 14 is the standard source reference; another period remains explicit as a strategy-parameter ambiguity, not silently promoted to baseline truth.

### STB/BTS — SW22 p2-4
For a valid STB/BTS:
- entry may use the upper part for LONG / lower part for SHORT;
- source also permits the exact 0.5 midpoint of the whole STB/BTS zone;
- Premium/Discount mitigation also focuses on 0.5 or beyond it.

SOURCE does not define a unique protective stop in these pages. No stop is invented.

### Range — SW10 p5-7
Aggressive:
- on deviation;
- only when an external POI exists below/above the Range.

Conservative:
- wait for price to return and accept back inside the Range;
- enter on a boundary retest.

Exit:
- 80% is fixed inside the Range at the directional opposite boundary;
- 20% may remain for a true breakout.

The exact destination/termination rule for the remaining 20% is not stated and remains unresolved. SW10 does not state a unique protective stop anchor for these branches.

### Demand/Supply — verified secondary source SRC_DS_001
Demand/Supply zones may act as profit-taking areas or points for opening positions. Zones must be untested, formed through a raid of old liquidity, and used in Discount/Premium according to direction.

The source does not state an exact quote inside the zone or a unique protective stop. Both remain unresolved.

## Stage-8 architecture
Canonical module:
- `src/crypto_bot/strategy/source_execution_v2.py`

Rule matrix:
- `config/source_execution_rules_v2.json`

Tests:
- `tests/test_source_execution_v2.py`

The module separates:
- source-permitted entry options;
- source-permitted stop options;
- causal FTA selection;
- source-specific exit policies;
- unresolved selection/geometry.

A Stage-8 plan may be `PASS` as a faithful representation of SOURCE while still having `execution_ready=false`. This is intentional: representation of source semantics is not the same as permission to trade.

## Explicitly unresolved after Stage 8
- OB boundary-vs-inside entry selection;
- OB stop variant and exact beyond-anchor buffer;
- conservative new-POI exact quote and stop geometry;
- Breaker exact entry quote, stop variant and buffer;
- SFP exact quote inside post-BOS POI;
- strategy-specific ATR period beyond standard 14;
- STB/BTS edge-vs-midpoint precedence and protective stop;
- Range aggressive exact quote and protective stop;
- Demand/Supply exact entry quote and protective stop;
- generic FTA full-vs-partial fraction;
- Range 20% remainder destination/termination;
- generic remainder/re-entry semantics.

## Forbidden contamination
Stage 8 does not use:
- Anti-Scalp;
- `edge_cost_ratio`;
- fee/slippage admission;
- project HTF admission;
- score/ranking;
- TP 40/30/30;
- cost-adjusted breakeven;
- portfolio/correlation/daily-loss/leverage gates;
- future outcome, PnL, MFE/MAE or post-hoc winner selection.

## No-look-ahead requirements
Tests require that:
- future POIs cannot alter current FTA;
- later POI consumption does not rewrite prior FTA history;
- future ATR/anchor evidence is rejected;
- multiple SOURCE variants remain variants rather than outcome-selected winners;
- every Stage-8 plan keeps `trade_entry_allowed=false`.

## Next stage
Stage 9 is SOURCE Engine Freeze / clean runtime wiring. It must connect Stages 1–8 without allowing legacy `source_engine.py` or old virtual/project portfolio behavior to silently define SOURCE semantics.
