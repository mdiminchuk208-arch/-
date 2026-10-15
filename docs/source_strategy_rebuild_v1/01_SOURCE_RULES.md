# Source Strategy Rebuild v1 — literal source rules

This document records only rules directly supported by `Методичка.docx`. Ambiguities are preserved instead of silently resolved.

## 1. Market structure

Source pages 3–9.

- Market structure is a sequence of highs and lows and applies on all timeframes.
- Bullish structure: higher highs (HH) and higher lows (HL).
- Bearish structure: lower lows (LL) and lower highs (LH).
- In bullish structure, only highs that update prior highs are structurally relevant.
- In bearish structure, only lows that update prior lows are structurally relevant.
- Range/sideways movement is a third market phase.
- For a bullish-structure break, price breaking the last HL means structure is broken; after BOS a bearish structure with LL/LH is expected; when LH forms the source says to look for a short.
- For a bearish-structure break, the relevant LH that formed the last LL is the break level; after BOS a bullish structure with HL/HH is expected; when HL forms the source says to look for a long.
- Before forming a setup, market structure must be considered.

Unresolved by source alone:
- exact swing-point algorithm;
- exact body-close versus wick-cross requirement for BOS;
- minimum distance/strength for a new HH/HL/LH/LL;
- tie handling and equal highs/lows inside structure.

## 2. Range / sideways market

Source pages 6–7 and 14–15.

- When price is in a range, consider the preceding trend, the general trend on higher timeframes, and whether price is at support/resistance.
- A range can form at highs or lows.
- The range may not have perfectly clear boundaries; the instrument must trade in a defined area.
- The source describes the range boundaries as the first high after the impulse and the first low.
- Inside a range there should be no normal trending structure.
- The source trades a range only after deviation outside the range boundary.
- Validation includes reactions from the range midpoint/equilibrium 0.5.
- One explicit range setup: price returns after deviation, then tests the zone that sent price back into the range, with CHOCH.

Unresolved by source alone:
- exact tolerance for a range boundary;
- what numerical condition defines `no structure`;
- how many midpoint reactions are required;
- exact support/resistance construction.

## 3. Order Block (OB)

Source pages 9–10.

- OB is the last candle before an imbalance / sharp impulsive move.
- The move must update a structural point, by CHOCH or by updating a high in a long trend / a low in a short trend.
- The OB must have taken some low/high or wick.
- The OB body should be large while its wicks should be small.

Unresolved by source alone:
- numerical definition of `large body` and `small wicks`;
- whether the OB zone is body-only, full candle, or another sub-zone;
- exact mitigation/entry rule;
- exact invalidation and re-entry rule.

## 4. Imbalance

Source page 11.

- Imbalance is a sharp impulsive move/candle that leaves price inefficiency.
- The inefficiency/gap is marked using the shadows of neighboring candles.
- The source treats imbalance as a magnet to which price can later return.

Unresolved by source alone:
- minimum gap size;
- minimum impulse size;
- whether every such gap is tradable or only contextual.

## 5. Breaker

Source page 12.

- A breaker is an Order Block that is impulsively broken through.
- The breaker must first take a high/low and then be broken.
- It must be broken through with imbalance.
- After that the source requires CHOCH.

Unresolved by source alone:
- exact breaker zone geometry;
- exact entry trigger on return;
- exact stop/invalidation.

## 6. Liquidity

Source pages 13–14.

- Liquidity is described as traders' stops and as a target of a trade.
- Equal highs and equal lows are liquidity.
- Trendline liquidity is also shown as a liquidity concept.
- The strategy uses liquidity as something price may manipulate/sweep.

Unresolved by source alone:
- tolerance for EQH/EQL;
- how many touches create a valid liquidity pool;
- priority among multiple liquidity targets;
- exact definition of `meaningful` liquidity.

## 7. OTE / Fibonacci

Source pages 16–19.

- Relevant levels include 0.5, 0.62/0.618, 0.705 and 0.79.
- 0.5 is equilibrium/fair price.
- For entry, behavior beyond 0.5 is relevant.
- The OTE zone is 0.705–0.79 and is described as an optimal entry zone.
- OTE is intended as a complement to the strategy, not a standalone signal.
- The source says OTE works especially well together with an Order Block.

Ambiguity preserved:
- the text gives high-to-low Fibonacci wording for short and then repeats high-to-low wording for long; the long anchoring direction must not be silently corrected without an explicit technical/source resolution.

## 8. SFP

Source page 19.

- SFP is a reversal pattern.
- The original form consists of 3 candles; a 4th candle may confirm direction.
- Its purpose is to take/activate stops above highs or below lows, including swing highs/lows and range boundaries.
- Price makes a false move and reverses in the opposite direction without body acceptance/confirmation beyond the swept area; the source describes this as no CHOCH/BOS continuation through the level.
- SFP is applicable on all timeframes.
- Context is mandatory: there must be points or zones whose liquidity is being taken.

Unresolved by source alone:
- exact 3-candle geometry in OHLC equations;
- exact optional fourth-candle confirmation rule;
- exact body-acceptance/invalidation threshold;
- exact entry and stop rule after SFP.

## 9. AMD

Source pages 20–21.

- AMD consists of accumulation, manipulation and distribution.
- Two position-building approaches are described: working with local POIs around the transition from manipulation to distribution, and a riskier entry during manipulation.
- For the risky manipulation entry the source tells the trader to consider speed of return into range, liquidity above plus removal of lows during manipulation, and increasing buying volume versus selling volume.

This section is contextual/descriptive and does not provide a complete deterministic trade-entry contract by itself.

## 10. What the source does NOT fully specify

The 22-page methodichka does not provide a complete machine contract for:
- exact swing algorithm;
- exact BOS/CHOCH close semantics;
- exact stop placement for every setup;
- exact take-profit/partial-exit policy;
- exact re-entry policy;
- exact setup lifetime/expiry;
- exact numerical definitions for qualitative words such as large/small/clear/fast;
- exact timeframe ladder for a bot;
- exact risk sizing;
- exact volume-profile rule.

These gaps must be resolved separately and explicitly. They may not be filled by copying old v2/v3/v4/v4.1 heuristics as if those were source rules.
