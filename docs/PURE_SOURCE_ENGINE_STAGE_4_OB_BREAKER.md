# PURE SOURCE ENGINE — STAGE 4: ORDER BLOCK + BREAKER

Status: IMPLEMENTING

Base merge commit: `55898b3b68fc43404802a8a4331cd7b8e75a97e1`

Branch: `pure-source-engine-stage-4-ob-breaker`

Scope: SOURCE Order Block and Breaker **object formation only**. Entry, stop, first/repeat test admission, FTA, target, RR, ranking, PnL and portfolio logic are deferred.

`trade_entry_allowed=false` remains invariant.

## Object validity remains separate from trade eligibility

A valid OB may exist even if:

- price never retests it;
- no entry setup is later assembled;
- a later retest is rejected;
- the object is later broken and becomes the parent of a Breaker;
- a future trade would lose.

A Breaker is a new descendant object. It never retroactively turns the historical parent OB into a non-object.

## Order Block SOURCE contract

### Unambiguous requirements

From Методичка p9-10 and SW9 p2-3:

1. the candidate OB candle itself works with / sweeps liquidity;
2. the following candle is an aggressive impulsive candle that overlaps/engulfs the candidate;
3. the movement receives BOS / structural-change confirmation;
4. the formation is located in an HTF POI;
5. the OB is inside a structural impulse and worked with the structural trend;
6. the OB zone is the whole candidate candle including its wicks.

The clean object remains `trade_eligible=false`. SW9 first-test/repeated-test behavior belongs to later setup/admission logic.

### Qualitative geometry

SOURCE does **not** give numeric definitions for:

- aggressive impulse;
- large OB body / small wicks;
- sufficiently strong displacement.

Stage 4 therefore does not invent ATR multiples, body ratios or percentage thresholds. These facts use `QualitativeEvidence` with:

- PASS / FAIL / UNKNOWN;
- evidence id;
- causal `known_at`.

PASS without provenance is not accepted.

### Engulf geometry

SW9 says the aggressive impulse overlaps/engulfs the prior candle. The deterministic machine representation uses directional **body coverage** of the candidate body.

This is explicitly:

`TECHNICAL_NORMALIZATION: TN_OB_BODY_ENGULF_GEOMETRY`

It is not claimed as a verbatim numeric SOURCE rule.

### Causality of context

The liquidity parent, HTF POI and structure context cannot be discovered in the future and retroactively manufacture an OB.

For Stage 4:

- liquidity parent must be known by candidate-candle open;
- HTF POI must be source-valid and known by candidate-candle open;
- source structure must be known by candidate-candle open and aligned with OB direction;
- BOS may be known later and acts as source-required formation confirmation;
- `formation_at` records completion of the candidate + immediate impulse geometry;
- `known_at` records the first time all required evidence used by the assessment is causally available.

## OB IMB conflict

The source set is not perfectly uniform:

- Методичка p9 describes OB as the last candle before imbalance / sharp impulsive movement;
- SW9 p2 says the signal is most accurate when IMB follows the engulfed candle;
- SW9 p6 warns beginners not to ignore IMB.

Stage 4 does not silently choose a threshold or rewrite this conflict.

Current rule:

- `imbalance_present=true` is compatible with all cited SOURCE material and can proceed;
- `imbalance_present=false/null` returns `UNKNOWN: SOURCE_CONFLICT_OB_IMB_HARD_VS_QUALITY_UNRESOLVED`;
- absence of IMB is neither silently accepted nor used to erase an otherwise observed candidate.

Stage 5 will implement clean IMB/FVG geometry, but it must not retroactively use future fills/outcomes.

## First and repeated OB tests

SW9 p3 says approximately 90% of work is from the first OB test and allows some repeated entries after LTF reaction.

This is **not OB object formation**.

Therefore Stage 4 does not include:

- `test_number` in object identity;
- future retest in formation validity;
- LTF reaction as a prerequisite for historical OB existence.

These belong to setup/admission stages.

## Breaker SOURCE contract

### Parent identity

SW9 and Методичка define Breaker from a previously existing OB. A Breaker therefore requires a valid parent `ORDER_BLOCK` object and stores `parent_ob_id`.

### SW9 requirements

SW9 p7:

- the OB is broken by a fast impulsive movement;
- the movement is whole/continuous, without trading inside the OB area;
- Breaker is tied to structure break/update and may be reversal or continuation;
- new HH/LL / trend structure remains relevant.

Again, `fast` and `whole/continuous` are qualitative. No numeric displacement/speed threshold is introduced.

### Higher-priority Методичка requirement

Методичка p12 explicitly states:

- Breaker is an impulsively penetrated OB;
- it should take high/low and then be penetrated;
- the Breaker **must** be penetrated with imbalance;
- after that CHOCH / structure shift should be obtained.

Given project SOURCE priority, Stage 4 requires:

- imbalance present;
- a causal structure-shift/BOS-style reference in Breaker direction.

Exact CHOCH formalization is not invented as a new numeric rule; Stage 4 consumes an auditable structure-shift reference.

### Machine break geometry

Stage 4 represents an OB as broken only after a completed candle body closes beyond the opposite edge of the parent OB zone.

This is:

`TECHNICAL_NORMALIZATION: TN_BREAKER_CLOSE_BEYOND_OB_ZONE`

A wick-only penetration is not automatically promoted to Breaker.

## Deferred

The following are explicitly not part of Stage 4 object semantics:

- first-test entry;
- repeated-test entry;
- OB boundary/inside limit order selection;
- OB stop behind OB extreme or engulfing wick;
- Breaker aggressive/conservative stops;
- FTA/targets;
- RR;
- FVG/IMB detector details (Stage 5);
- OTE/Premium/Discount (Stage 5);
- STB/BTS (Stage 6);
- ranking/scoring;
- cost admission;
- portfolio/risk overlays.

## Acceptance criteria

Stage 4 is complete only if:

1. OB object can be formed only from a raid performed by the candidate candle itself;
2. candidate + immediate impulse geometry is causal and closed-candle based;
3. qualitative terms require provenance rather than numeric invention;
4. BOS, HTF POI and structure context are explicit evidence;
5. IMB absence remains explicit SOURCE conflict/UNKNOWN;
6. OB zone is full candidate candle including wicks;
7. valid OB remains `trade_eligible=false`;
8. later retest/outcome is absent from OB stable identity;
9. Breaker requires a valid parent OB and preserves its parent ID;
10. Breaker formation never mutates parent OB history;
11. fast/continuous Breaker geometry is provenance-based;
12. higher-priority Методичка IMB + structure-shift requirement is enforced;
13. wick-only OB penetration is not auto-promoted under the machine break normalization;
14. full unit suite and safety invariant are green;
15. no PROJECT_POLICY or PnL optimization enters the path.
