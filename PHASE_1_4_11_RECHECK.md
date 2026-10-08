# Phase 1.4.11 v0.4.11 recheck

## Source recheck
The source describes market structure as a sequence of highs and lows. Advanced defines bullish structure as key HH/HL above prior points and bearish structure as key LL/LH below prior points. The general methodology says only highs/lows that update prior structure are structurally relevant. After BOS the methodology expects the opposite LL+LH / HL+HH sequence, while Advanced defines CONF as the later update of the new structure's key minimum/maximum.

The sources do not provide software indexing rules for swing chronology, so explicit chronological interleaving is labeled `TECHNICAL_NORMALIZATION` rather than `SOURCE_RULE`.

## Defects reproduced from v0.4.10
1. Non-interleaved synthetic structural levels `low -> low -> high -> high` were accepted by `_post_bos_bullish_structure` because the old implementation compared same-side prices without requiring the correction low to occur after the prior high. Mirror issue existed bearish.
2. A live bullish structure with key HH=15 could incorrectly accept new high=13 if an internal later swing high=12 became the comparison reference. Mirror issue existed bearish.

Both cases are rejected in v0.4.11.

## Causality checks
- Post-BOS structure still excludes pre-BOS swing centers.
- A BOS-leg extreme can still seed the new opposite structure only after later three-candle confirmation.
- BOS is evaluated before same-close swing confirmation.
- CONF remains a later close through the new structure's key extreme.
- No time-based structure-recovery timeout is invented.

## QA checklist
- full unittest suite required;
- compileall required;
- main CLI help required;
- lifecycle-audit CLI help required;
- registry JSON unique/valid required;
- ZIP re-extract + full test rerun required.

## Real-data gate
Run the dedicated 240d-vs-60d lifecycle audit before the expensive Range Validation. v0.4.11 is not considered real-market validated merely because unit tests pass.

## Direct regression comparison
Using the same synthetic structural levels `low(10) -> low(11) -> high(12) -> high(13)`:
- v0.4.10 `_post_bos_bullish_structure(...)` returned a bullish structure (false positive);
- v0.4.11 returns `None` because the sequence is not chronologically interleaved.

Mirror bearish coverage is included in the unit suite.

## Bybit V5 adapter assumptions rechecked 2026-09-13
Official Bybit V5 documentation still supports Kline intervals `5/15/60/240` with page limit up to 1000; Server Time still exposes `timeSecond/timeNano`; Instruments Info remains `/v5/market/instruments-info`. No adapter change was required by Phase 1.4.11.
