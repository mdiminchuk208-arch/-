# PURE SOURCE ENGINE — STAGE 2: STRUCTURE + LIQUIDITY

Status: IMPLEMENTING

Base merge commit: `f6eca678a24cbedd3a60f2f30c7a3ce3f6c24bcc`

Branch: `pure-source-engine-stage-2-structure-liquidity`

Scope: SOURCE market-structure and liquidity evidence only. No trade PnL, setup optimization, project scoring, risk overlay, private exchange API, or live orders.

`trade_entry_allowed=false` remains invariant.

## 1. SOURCE evidence used

### Market structure

- SW4 p3: bullish trend has highs and lows above the previous ones; bearish trend has lows and highs below the previous ones.
- SW5 p2: Swing High/Low is a strict three-consecutive-candle construction.
- SW5 p4-5: BOS breaks the protected structural minimum/maximum and requires candle-body acceptance beyond it.
- SW5 p6-7: CONF is a later update of the key minimum/maximum of the new structure after BOS; conservative entry is discussed after CONF.

### Liquidity

- SW6 p7-10: EQH/EQL are liquidity pools; they do not have to be ruler-flat.
- SW6 p10: allowed tilt direction is explicit: EQH left maximum above right, EQL left minimum below right.
- SW6 p10: EQH/EQL form between substructure swings, not arbitrary candles.
- SW6 p12: internal liquidity lies inside a range/formed impulse between structural endpoints; external liquidity lies beyond range boundaries and at structural highs/lows of the corresponding timeframe.

## 2. Stage-2 executable rules

### Strict three-candle swings

Executable and causal.

A swing becomes `known_at` only after the right-hand candle has closed. This is `TECHNICAL_NORMALIZATION: SWING_CONFIRM_001` and prevents look-ahead.

### Bullish/bearish structure

Executable when an interleaved swing sequence is causally available:

- bullish: previous low -> previous high -> higher low -> higher high;
- bearish: previous high -> previous low -> lower high -> lower low.

The chronological pairing rule is technical normalization. It prevents unrelated same-side swings from being paired into an artificial structure.

### BOS

Executable using the active protected point:

- bullish structure breaks only on a closed candle body below its protected HL;
- bearish structure breaks only on a closed candle body above its protected LH.

A wick-only penetration is not BOS under this representation.

### CONF

SOURCE meaning is preserved: later update of the key extreme of the new structure after BOS.

The exact machine anchor-selection procedure remains a technical normalization and must remain traceable. Stage 2 does not use CONF as a profitability filter.

### Structural liquidity

Every confirmed structural swing can produce causal liquidity evidence. When a known parent structural leg exists:

- a swing strictly inside its structural endpoints is represented as internal liquidity;
- an endpoint/outside swing is represented as external liquidity.

This is a deterministic representation of SW6 p12 and must retain the parent swing/structure provenance.

## 3. EQH/EQL — important correction

Legacy `SourceSeries` labels a pool EQH/EQL when a later swing has exactly the same numeric price as an existing pool. That rule is **not SOURCE-complete** and cannot define PURE_SOURCE EQH/EQL.

SOURCE requires:

1. the points are substructure swings;
2. exact equality is allowed but not required;
3. tilted EQH: left maximum > right maximum;
4. tilted EQL: left minimum < right minimum;
5. the tilt is "within reason" / reasonable.

The source does **not** provide a numerical tolerance for "reasonable".

Therefore Stage 2 uses three evidence states:

- `PASS`
- `FAIL`
- `UNKNOWN`

Rules:

- exact-price pair + causally confirmed substructure relation -> `PASS`;
- correct tilt direction + confirmed substructure + explicit qualitative reasonable-tilt evidence -> `PASS`;
- correct tilt but missing qualitative evidence -> `UNKNOWN`;
- wrong tilt direction -> `FAIL`;
- arbitrary candles instead of substructure swings -> `FAIL`;
- missing evidence that the pair belongs to substructure -> `UNKNOWN`.

No ATR, percentage, tick-distance, basis-point, or candle-count tolerance may be silently introduced.

## 4. Liquidity take / sweep

The current deterministic representation uses strict wick penetration:

- high-side: `candle.high > pool.price`;
- low-side: `candle.low < pool.price`.

This remains explicitly `TECHNICAL_NORMALIZATION`, not a verbatim SOURCE numeric rule. It is not allowed to mutate into a hidden threshold.

Touching the exact price without penetration is not considered a sweep under this normalization.

## 5. Object validity and trade eligibility

Stage 1 contract remains authoritative:

`formation_valid != trade_eligible`

A valid swing/structure/liquidity pool exists independently from whether a later SFP, OB, entry chain, target, or profitable trade appears.

Later cancellation/invalidation does not erase historical existence.

## 6. Legacy boundary

The following legacy behavior is not allowed to be treated as PURE_SOURCE truth:

- exact-price-only automatic EQH/EQL classification;
- hidden significance filters;
- old adverse-liquidity labels;
- PnL-selected liquidity gates;
- project HTF ownership rules;
- outcome-dependent object identity.

Legacy modules remain available for regression/comparison only until migrated behind the clean contract.

## 7. Files introduced in Stage 2

- `src/crypto_bot/strategy/source_structure_liquidity_v2.py`
- `tests/test_source_structure_liquidity_v2.py`
- `docs/PURE_SOURCE_ENGINE_STAGE_2_STRUCTURE_LIQUIDITY.md`

## 8. Acceptance criteria

Stage 2 is complete only when:

1. strict swings are prefix-safe;
2. bullish/bearish structure is reproducible from causally confirmed swings;
3. BOS uses body-close acceptance beyond the protected point;
4. internal/external structural liquidity is traceable to known structure endpoints;
5. EQH/EQL no longer depends on exact-price-only legacy labeling in the clean PURE_SOURCE evidence path;
6. qualitative `reasonable tilt` remains `UNKNOWN` unless explicit evidence exists;
7. future candle mutation does not change prior object IDs/timestamps;
8. existing Stage-1 safety invariants remain green;
9. no PROJECT_POLICY enters the path;
10. full CI is green before merge.

## 9. Deferred to later stages

Not solved here:

- SFP trade chain (Stage 3);
- OB / Breaker (Stage 4);
- FVG/IMB/OTE/Premium-Discount (Stage 5);
- STB/BTS/Range (Stage 6);
- Setup/Direction (Stage 7);
- Entry/Stop/FTA/Exit/Remainder/Re-entry (Stage 8+).
