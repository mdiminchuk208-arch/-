# Phase 1.4.10 v0.4.10 recheck

## Source recheck
- Advanced market structure defines bullish `HH/HL`, bearish `LL/LH`, BOS as interruption of the original structure, and CONF as later continuation/update of the new structure.
- General methodology says after bullish BOS bearish `LL+LH` should follow; after bearish BOS bullish `HL+HH` should follow.
- No source rule defines an unlimited `BROKEN` state, a time-based transition timeout, or a dedicated same-direction-recovery algorithm.

Therefore:
- expected opposite transition remains SOURCE-aligned priority;
- post-BOS local recovery is kept as TECHNICAL_NORMALIZATION;
- no timeout is invented;
- all fallback points must be causally confirmed and on/after BOS, never pre-BOS.

## Regression reproduced
A synthetic case where bullish BOS is rapidly reclaimed and strictly post-BOS swings later form a fresh bullish `HH+HL` gives:
- v0.4.9: final state `BROKEN`, longest BROKEN 8 candles;
- v0.4.10: final state `BULLISH`, resolution mode `SAME_DIRECTION_POST_BOS_RECOVERY`, longest BROKEN 7 candles.

The diagnostic records why the expected bearish fast path failed before local recovery.

## QA checklist
- Unit tests: see packaged test run.
- compileall: required.
- main CLI help: required.
- structure-audit CLI help: required.
- registry JSON unique/valid: required.
- ZIP re-extract + full unit tests: required before release.

## Real-data gate
This build is not considered validated until BTCUSDT/ETHUSDT are rerun on the existing 240-day data. First run the dedicated lifecycle audit; only then rerun the expensive 180-day Range Validation.
