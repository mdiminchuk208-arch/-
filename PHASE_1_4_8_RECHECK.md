# Phase 1.4.8 v0.4.8 recheck

## Source recheck
Rechecked the uploaded Market Structure sources before changing the lifecycle.

Preserved as SOURCE_RULE:
- bullish structure = HH + HL;
- bearish structure = LL + LH;
- bullish BOS breaks the protected/key HL by candle-body acceptance;
- bearish BOS breaks the protected/key LH by candle-body acceptance;
- after bullish BOS the methodology expects bearish LL + LH;
- after bearish BOS it expects bullish HL + HH;
- Advanced source defines CONF as the later confirmation/update of the new structure, not as the definition of the first new structure itself.

TECHNICAL_NORMALIZATION:
- `BROKEN` remains a temporary causal software state between BOS and completion of the first opposite LL+LH / HH+HL;
- post-BOS LL/HH is checked against the broken protected level, and the later LH/HL against the broken structure's key HH/LL;
- only strictly post-BOS swings can build the new structure;
- CONF remains a later body close through the first post-BOS key extreme.

No future swing or same-candle newly-confirmed swing is used by an earlier event.

## Bug regression
Synthetic sequence:
`bullish structure -> bullish BOS -> post-BOS LL -> post-BOS LH -> close above new LH before bearish CONF`.

- v0.4.7: emitted only the first BOS and ended `BROKEN`.
- v0.4.8: establishes bearish structure at LL+LH, then emits the second BOS when the new LH is broken.

A second regression prepends older valid market history and requires the recent two-BOS cycle to remain observable.

## State audit
Every analyzed candle contributes to a compressed state trace. Reports expose:
- state candle counts;
- longest BROKEN run;
- segment start/end indices and UTC timestamps.

This is diagnostic QA, not a trading signal.

## Current Bybit public API recheck (2026-09-13)
Official V5 documentation remains compatible with the unchanged data adapter:
- `/v5/market/kline`: intervals include 5/15/60/240, `start`/`end`, limit up to 1000, reverse sorted by startTime, unclosed closePrice is last traded price;
- `/v5/market/time`: `timeSecond`, `timeNano`;
- `/v5/market/instruments-info`: current instrument metadata endpoint.

No adapter change is required by Phase 1.4.8.

## Remaining blockers before Entry Engine
- `RANGE_DETECTION_NORMALIZATION_NOT_VALIDATED`
- `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`
- `RANGE_EXIT_REENTRY_LIFECYCLE_NOT_FORMALIZED`
- `GLOBAL_CROSS_PAIR_CLUSTER_PARAMETER_NOT_FROZEN`
- `ENTRY_ZONE_SL_TARGET_RR_NOT_IMPLEMENTED`

Actual trade entries remain zero.
