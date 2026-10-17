# PURE SOURCE Engine — Stage 17: Non-ranked SOURCE Branch Registry

Base merge: `f206e6938fe78adb7290ba3264c6d19c2ababf9b` (Stage 16).

Stage 17 turns finite, explicitly SOURCE-permitted alternatives into stable typed branch identities. It does **not** choose a preferred branch, does not calculate outcomes, and does not authorize financial backtesting or execution.

## Why a branch registry is needed

Stage 8 already preserves multiple execution options inside one `SourceExecutionPlan`, while Stage 16 establishes that several ambiguities are not missing knowledge but explicit SOURCE alternatives with no universal precedence.

Keeping every alternative as a generic `unresolved` list is safe but insufficient for later causal research because it can blur three different situations:

1. SOURCE gives an exact alternative once its parent object is known;
2. SOURCE gives a bounded or relative alternative but not one exact price/fraction;
3. SOURCE gives an explicit family of parameters but no universal choice.

Stage 17 represents those situations without ranking them.

## Registered families

### `OB_DIRECT_ENTRY` — SW9 p3

- `OB_DIRECT_BOUNDARY_LIMIT`: exact once source-valid OB geometry is known; LONG upper boundary / SHORT lower boundary.
- `OB_DIRECT_INSIDE_ZONE`: bounded inside OB, but exact quote is unspecified.

No precedence is assigned.

### `OB_EXECUTION_PATH` — SW9 p3-6

- `OB_DIRECT_PATH`.
- `OB_LTF_CONFIRMATION_NEW_POI_PATH`: waits for HTF OB reaction, causal LTF BOS and new source-valid POI; exact quote and refined stop remain unresolved.

This family records path identity only; it does not make the final quote executable.

### `OB_STOP_ANCHOR` — SW9 p3

- beyond OB extreme;
- beyond engulfing-candle wick/extreme.

Both anchors remain relative because SOURCE does not supply one exact beyond-anchor buffer.

### `BREAKER_STOP_ANCHOR` — SW9 p9-10

- aggressive beyond Breaker;
- conservative beyond liquidity-sweeping impulse extreme.

Again, exact beyond-anchor buffer is unresolved.

### `STB_BTS_ENTRY` — SW22 p3-4

- directional part of zone: bounded, no exact quote;
- exact 0.5 midpoint: exact once parent STB/BTS geometry is source-valid.

The fact that one branch is geometrically exact does **not** make it preferred or trade-eligible.

### `FTA_FIXATION` — SW9 p11-16

- full fixation: exact allocation `1.0` once causal FTA is known;
- partial fixation: SOURCE-permitted but exact partial fraction and remainder lifecycle remain unresolved.

Full fixation is preserved as an exact SOURCE branch, not promoted as the default.

### `SFP_ATR_PERIOD` — SW12 p12-14

- standard ATR period `14`;
- strategy-adjusted period family, with no universal alternate period supplied by SOURCE.

ATR 14 is a precise source-supported branch. Stage 17 does not infer that it must be used for every SFP strategy instance.

## Schema safety

The typed loader rejects:

- `trade_entry_allowed=true`;
- financial-backtest permission;
- any PROJECT policy;
- ranking/outcome metadata such as `rank`, `score`, `weight`, `priority`, `preferred`, `win_rate`, `profit_factor`, `expectancy`, `pnl`, or `backtest_result`;
- duplicate family or alternative IDs;
- unresolved geometry classes that omit their blocker;
- malformed exact parameter/allocation contracts.

The registry is canonically sorted and can be SHA-256 fingerprinted independently of JSON family/alternative declaration order.

## Critical semantic boundary

`is_exact_choice` means only that SOURCE supplies the branch's coordinate/parameter once required parent evidence is causally known.

It does **not** mean:

- the parent object is valid;
- the setup is eligible;
- the branch has precedence;
- the branch is profitable;
- the strategy may enter a trade.

Therefore:

`EXACT SOURCE ALTERNATIVE != TRADE ELIGIBILITY`

and the project-wide invariant remains:

`OBJECT VALIDITY != TRADE ELIGIBILITY`.

## Files

- machine-readable registry: `config/pure_source_branch_registry_v2.json`
- typed contract: `src/crypto_bot/strategy/pure_source_branch_registry_v2.py`
- tests: `tests/test_pure_source_branch_registry_v2.py`

## What Stage 17 does not solve

It does not resolve:

- qualitative object provenance (OB body/wick quality, source-qualified impulse, Range reaction quality, meaningful liquidity, STB/BTS segmentation, etc.);
- exact inside-zone/new-POI quotes where SOURCE gives only a zone;
- exact beyond-anchor buffers;
- partial FTA fraction/remainder lifecycle;
- adjusted ATR period precedence;
- re-entry identity;
- timeframe/liquidity selection where multiple source-valid contexts coexist.

Those remain explicit blockers. No financial PURE SOURCE baseline is authorized by this stage.

Required state remains:

- `baseline_identifiability = NOT_IDENTIFIABLE`
- `trade_entry_allowed = false`
- financial backtest = false
- PAPER/LIVE/private API = false
- PROJECT overlays = forbidden inside PURE SOURCE.
