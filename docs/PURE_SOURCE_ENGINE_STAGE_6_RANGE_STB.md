# PURE SOURCE ENGINE — STAGE 6: RANGE + DEVIATION + STB/BTS

Status: IMPLEMENTING

Base merge commit: `ee16a2e98fbded85c4a3b3813535127d1e5c1710`

Branch: `pure-source-engine-stage-6-range-stb`

Scope: causal SOURCE object semantics for Range and STB/BTS, plus raw Range deviation events. No entry execution, stop, FTA, RR, ranking, PnL or portfolio logic.

`trade_entry_allowed=false` remains invariant.

## Range formation

SW10 defines the construction:

1. Range follows a **strong directional impulse**.
2. Impulse end is boundary one.
3. Later correction end is boundary two.
4. For an up impulse: first boundary = high, second boundary = later low.
5. For a down impulse: first boundary = low, second boundary = later high.
6. 0.5 midpoint reaction is an important confirmation of correct boundaries.

Higher-priority Методичка additionally says internal structure should be absent inside the range.

### Qualitative evidence boundary

SOURCE does not numerically define:

- strong impulse;
- good/correct 0.5 reaction;
- clear/no-internal-structure range quality.

Stage 6 therefore uses auditable `QualitativeEvidence` with PASS/FAIL/UNKNOWN + evidence id + causal timestamp. It does **not** reuse historical fixed midpoint tolerance `0.08`, ATR displacement or a range clarity score.

The strength of the impulse may naturally be known before the correction endpoint. Midpoint reaction and no-internal-structure confirmation cannot causally predate the second boundary.

### Range object timing

- `formation_at`: second/correction boundary becomes causally known;
- `known_at`: all required SOURCE evidence is available;
- `confirmed_at`: same time as final Stage-6 Range confirmation.

The Range object remains `trade_eligible=false`.

## Deviation

SW10 defines deviation as movement beyond a Range boundary to remove external liquidity.

Stage 6 records a raw deviation event after strict boundary penetration:

- high-side deviation: high > upper boundary;
- low-side deviation: low < lower boundary.

Strict wick penetration is an explicit deterministic normalization.

A candle that sweeps both sides preserves **both** events; no direction is silently selected.

Return/reclaim/acceptance inside the Range is **not** required for the raw deviation event. That belongs to later setup/entry assembly.

SOURCE language that a deviation on one side tends to lead toward the other side is retained as context, not converted into a guaranteed target.

## Range trading rules deferred

SW10 has at least two trade variants:

- aggressive: deviation + POI beyond the Range;
- conservative: external POI interaction, return/acceptance inside the Range, boundary retest.

SW10 also gives an 80/20 exit concept.

These are not part of Range object validity and are deferred to setup/entry/exit stages. Future failure or success of these branches cannot rewrite the historical Range.

## STB / BTS

SW22 defines STB/BTS around smart-money manipulation:

- liquidity pool is swept;
- a manipulation zone/movement exists;
- the manipulation is fully engulfed on reversal;
- BOS or CONF occurs;
- the potential position agrees with the main trend.

STB is the long-side form after low-side manipulation; BTS is its short-side mirror after high-side manipulation.

### Qualitative full engulf

SOURCE does not specify a numeric candle count, ATR multiple or displacement percentage for `full engulf of the manipulation`.

Stage 6 therefore requires qualitative provenance instead of inventing a number.

### Object timing

The manipulation may physically exist first. The STB/BTS object is only known/confirmed when full-engulf evidence plus BOS/CONF are causally available.

The object remains `trade_eligible=false`.

## 0.5 mitigation is later chain logic

SW22 describes test/mitigation at the relevant side or 0.5 of the STB/BTS zone. This belongs to entry logic and is not required for historical STB/BTS object existence.

## Acceptance criteria

Stage 6 is complete only if:

1. Range cannot exist without a source-qualified impulse and correction endpoint;
2. boundary ordering mirrors source direction;
3. strong impulse, midpoint reaction and no-internal-structure facts never receive hidden numeric thresholds;
4. midpoint/no-structure confirmation cannot precede the second boundary;
5. Range object identity excludes future deviation/outcome;
6. raw deviations use known Range boundaries only;
7. dual-side same-candle deviation is preserved as ambiguous/raw evidence;
8. reclaim/entry is not folded into deviation existence;
9. STB/BTS requires causal liquidity manipulation, main-trend alignment, full engulf and BOS/CONF;
10. full-engulf remains qualitative/provenance-based;
11. 0.5 mitigation does not define STB/BTS object existence;
12. all objects remain trade-ineligible;
13. no PROJECT policy or PnL appears in identity/validity;
14. full unit suite and safety invariant are green.
