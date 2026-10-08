# Phase 1.4.9 v0.4.9 changelog

## Recheck finding
A source/code recheck of v0.4.8 found one remaining lifecycle over-restriction. v0.4.8 required the first post-BOS opposite anchor to have `swing_index > BOS_index`. That rejects a common causal case where the BOS candle/leg itself becomes the new LL/HH and is confirmed as a three-candle swing only by the next candle.

## Correction
- Pre-BOS swings remain forbidden.
- The first opposite LL/HH anchor may have `swing_index == BOS_index` only when `confirmed_index > BOS_index`.
- The later LH/HL correction must still be strictly later than the anchor.
- This is TECHNICAL_NORMALIZATION, not a new source rule.
- CONF remains separate from structure existence.

## Regressions
Added symmetric tests for:
- bullish BOS candle becoming the first bearish LL after later swing confirmation;
- bearish BOS candle becoming the first bullish HH after later swing confirmation.

No data-adapter, SFP, range, wait-window, clustering, risk, or entry logic changed. Trade Entry remains blocked.
