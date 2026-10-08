# Phase 1.4.5 v0.4.5 recheck

## Source consistency
Rechecked against the uploaded Range, Trading Tools Base, general Methodology and Liquidity materials.

Confirmed source-derived statements:
- range after strong directional impulse;
- impulse end / correction end define the two boundaries;
- 0.5 reaction validates boundary selection;
- range should not contain normal internal structure;
- range boundary is external liquidity and may form SFP;
- deviation is movement beyond range boundaries to take external liquidity;
- completed SFP still needs LTF BOS before entry search.

Not silently source-labeled:
- structural BOS as the strong-impulse machine proxy;
- 0.08 midpoint tolerance;
- in-range BOS as the machine proxy for forbidden internal structure;
- first-boundary-raid consumption lifecycle;
- dual-boundary same-candle ambiguity handling.

## Causality checks
- Boundary #1 and #2 use only already-confirmed swing events after an already-confirmed BOS proxy.
- Exact-timestamp swing after BOS is not accepted because intratimestamp ordering cannot be proven from OHLC.
- Midpoint validation uses only a confirmed swing event available at its confirmation timestamp.
- A range-boundary SFP can form only after midpoint validation is known; no earlier sweep is retroactively converted into an SFP. Earlier causally observed raids after boundary establishment still consume that original boundary liquidity.
- SFP completion uses the next candle OPEN only; later H/L/C of that candle are not required to create the formation event.
- A range deviation/outside close alone does not hard-invalidate the whole range in this build; a failed return-inside simply consumes that boundary without forming SFP.
- SFP invalidation remains a later candle-body close beyond the stored sweep-candle extreme.

## Safety/status
- `ENTRY_SEARCH_CANDIDATE` remains context/opportunity only, not a trade.
- Actual trade entries remain zero by design.
- Range normalization is explicitly marked not yet validated/frozen for live trading.
