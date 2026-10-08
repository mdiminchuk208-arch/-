# Phase 1.4.9 v0.4.9 recheck

## Source basis
- Advanced Market Structure: once the original structure is interrupted it is no longer current; CONF is the later update/confirmation of the new structure.
- General methodology: after bullish BOS a bearish LL+LH should form; after bearish BOS a bullish HL+HH should form. The diagrams place the new opposite extreme on the breaking leg, so software must not require the swing center to be strictly after the BOS candle.

## Causality
The BOS-leg extreme is not used at BOS time. It becomes eligible only if the following candle later confirms it as a valid three-candle swing (`confirmed_index > BOS_index`). Thus no future information leaks into the BOS event.

## QA target
The previous v0.4.8 regression where the BOS candle itself is the new opposite extreme ended BROKEN. v0.4.9 must establish the opposite structure in both bullish->bearish and bearish->bullish mirror cases.

Current public Bybit V5 Kline/Time/Instruments assumptions were rechecked on 2026-09-13 and remain compatible; no adapter change is required.

## Final QA
- unit tests: 149/149 OK;
- compileall: OK;
- CLI help: OK;
- Source Rule Registry: phase1.4.9-0.4.9, 67 unique rules;
- package version: 0.4.9;
- regression comparison: v0.4.8 stays BROKEN when the BOS candle itself is the first opposite extreme; v0.4.9 recovers to BEARISH/BULLISH in the mirrored cases.
