# Phase 1.4.7 v0.4.7 changelog

## Why this recheck exists
A source-completeness review found that Phase 1.4.6 preserved the dedicated range-module warning about smeared boundaries, but omitted a second uploaded statement from `Методичка.docx` saying that a range may lack perfectly crisp boundaries as long as price still trades within a defined area.

Treating only the first statement as if the source universally required crisp boundaries was incomplete.

## Corrections
1. Added `RANGE_BOUNDARIES_MAY_BE_NONCRISP_001` as a SOURCE_RULE.
2. Narrowed `RANGE_UNCLEAR_BOUNDARIES_SKIP_001` to the actual dedicated-module wording: skip when boundaries are smeared enough that future movement becomes difficult to determine.
3. Reframed the machine gate as a source nuance with no objective numeric threshold.
4. Renamed the runtime blocker to `RANGE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`.
5. Added `boundary_clarity_policy` to range summary JSON.
6. Updated manual audit marker to `REQUIRED_SOURCE_NUANCE_BOUNDARY_CLARITY_THRESHOLD_NOT_FORMALIZED`.
7. Added a registry regression test ensuring both source statements remain present.

## What did NOT change
- Range candidate construction.
- Midpoint tolerance experiments.
- Range-boundary SFP formation.
- SFP invalidation.
- MTF SFP -> LTF BOS linkage.
- Wait-window experiments.
- Global opportunity clustering.
- Trade-entry safety boundary: actual trade entries remain zero.

## Versions
- Package: `0.4.7`
- Source Rule Registry: `phase1.4.7-0.4.7`
