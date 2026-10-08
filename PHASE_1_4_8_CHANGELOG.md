# Phase 1.4.8 v0.4.8 changelog

## Why this phase exists
The 240-day validation run exposed a structural lifecycle defect: LTF BOS inventory collapsed from dozens of BOS events on the shorter history to almost none on the longer history. The cause was not data coverage. Phase 1.4.7 could remain in `BROKEN` until a later CONF-specific close occurred, and while `BROKEN` it refused to establish the opposite live structure. That could suppress all later BOS cycles.

A synthetic regression reproduces the defect in v0.4.7: after bullish BOS, a valid post-BOS bearish LL+LH forms, but without bearish CONF the old engine remains `BROKEN`; therefore a later close above the new LH cannot emit the next bearish-structure BOS. The same sequence in v0.4.8 emits both BOS events.

## Source basis
SOURCE_RULE:
- Advanced Market Structure: BOS breaks the original structure; once the original structure is interrupted the market priority/trend changes to the opposite side; CONF is the later confirmation/update of the new structure.
- General methodology: after bullish BOS a bearish LL + LH structure should form; after bearish BOS a bullish HL + HH structure should form.

## Implementation correction
1. Structure existence and CONF are now separate lifecycle concepts.
2. `BROKEN` is only a causal transition state after BOS while the first opposite structure is still forming.
3. At BOS the engine freezes the structure that was actually broken:
   - protected HL/LH price;
   - current key HH/LL price.
4. Opposite structure can then form from strictly post-BOS swings:
   - bullish BOS -> post-BOS LL below broken HL, then later LH below broken key HH -> bearish structure is live;
   - bearish BOS -> post-BOS HH above broken LH, then later HL above broken key LL -> bullish structure is live.
5. The new correction LH/HL becomes the protected level immediately when that LL+LH / HH+HL structure is complete.
6. CONF remains separate and later: a body close through the first post-BOS key LL/HH is recorded as `BEARISH_CONF_CONFIRMED` / `BULLISH_CONF_CONFIRMED`.
7. A new live structure may itself BOS even if CONF never occurred. This removes the long-history `BROKEN` lock.

The exact comparison of post-BOS swings to the frozen broken protected/key-extreme prices is **TECHNICAL_NORMALIZATION**, not a numeric source rule.

## New QA / diagnostics
- compressed `UNKNOWN / BULLISH / BEARISH / BROKEN` state segments;
- per-state candle counts;
- longest `BROKEN` run;
- `structure_audit/htf_trend_state_segments.csv`;
- `structure_audit/ltf_trend_state_segments.csv`;
- summary JSON contains state counts and longest BROKEN run;
- regression test that prepending older valid history does not suppress the recent second BOS cycle;
- regression test that a post-BOS opposite structure can break before CONF;
- multi-reversal lifecycle regression.

## What did not change
- 3-candle swing source rule;
- BOS body-close rule;
- SFP formation/invalidation;
- range-boundary SFP logic;
- wait-window experiments;
- global opportunity clustering;
- Range Validation blockers;
- Trade Entry remains intentionally blocked.

## Versions
- Package: `0.4.8`
- Source Rule Registry: `phase1.4.8-0.4.8`
