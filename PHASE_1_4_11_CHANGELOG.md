# Phase 1.4.11 v0.4.11 changelog

## Why this phase exists
A source/code recheck of v0.4.10 found that generic HH/HL and LL/LH detection could pair same-side swings whose chronology was not interleaved. Example: `low -> low -> high -> high` could satisfy the old price comparisons and be mislabeled bullish even though it is not an alternating high/low market-structure sequence. The same issue existed in the post-BOS local recovery fallback.

A second issue was that updates of an already-live trend compared a new high/low to the latest same-side swing rather than the current key HH/LL. An internal lower high could therefore become the accidental reference for a later high and create a false key-HH update.

## Changes
- Added chronological interleaving for machine structure sequences:
  - bullish: previous low -> previous high -> protected HL -> key HH;
  - bearish: previous high -> previous low -> protected LH -> key LL.
- Added live-key update guards:
  - bullish update must exceed the current key HH and use an intervening HL above the current protected HL;
  - bearish update must break the current key LL and use an intervening LH below the current protected LH.
- Applied the same interleaving requirement to the strictly post-BOS local-structure fallback.
- `post_bos_*_level_ids` transition-audit fields now contain only swing centers on/after BOS that were confirmed after BOS.
- If the local fallback resolves in the source-expected opposite direction, later CONF semantics are preserved. Same-direction technical recovery does not silently create a source-labeled CONF.
- Updated runtime report roots to `data/reports/phase1_4_11` and synchronized package/User-Agent version to `0.4.11`.
- Added regression tests for non-interleaved false positives and live-key-reference false updates.

## Scope boundary
Same-direction post-BOS recovery remains a `TECHNICAL_NORMALIZATION`, not a source rule. Real-data lifecycle audit remains mandatory before removing the structure-lifecycle blocker. Trade Entry remains disabled.
