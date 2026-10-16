# QUALITATIVE EVIDENCE ANNOTATION PROTOCOL v1

Purpose: resolve SOURCE concepts that are explicitly qualitative without inventing hidden numeric thresholds.

Current Stage-2 scope:

- EQH/EQL `reasonable tilt`;
- whether two candidate extrema are substructure swings belonging to the same relevant local structure.

This protocol is SOURCE evidence infrastructure, not a PROJECT optimization layer.

## 1. Hard prohibitions

The annotator must not see or use:

- future candles after `decision_at`;
- whether a setup later became READY;
- fill status;
- target/stop outcome;
- WIN/LOSS;
- PnL;
- MFE/MAE;
- later project score/rank;
- later branch selection;
- later optimization results.

No annotation may introduce an undocumented numerical tolerance such as:

- percent distance;
- ATR multiple;
- basis points;
- tick count;
- fixed candle distance;
- fitted volatility threshold.

If such a threshold is later researched, it is `PROJECT_POLICY` or research parameter unless directly sourced.

## 2. Required annotation record

Every annotation must contain:

- `annotation_id`;
- `concept`;
- `symbol`;
- `timeframe`;
- `left_object_id` / relevant parent object IDs;
- `right_object_id` / relevant parent object IDs;
- `decision_at`;
- `known_at`;
- `visible_window_start`;
- `visible_window_end`;
- `source_rule_ids`;
- `verdict`: `PASS | FAIL | UNKNOWN`;
- `reason_code`;
- `annotator_provenance`;
- `forbidden_future_confirmed=true`.

`visible_window_end` must never exceed `decision_at`.

## 3. EQH/EQL reasonable tilt

SOURCE evidence: SW6 p10.

Known SOURCE facts:

- exact equality is not mandatory;
- EQH permitted tilt direction: left maximum above right maximum;
- EQL permitted tilt direction: left minimum below right minimum;
- deviation must be "within reason";
- points must be substructure swings.

The SOURCE does not supply a numeric definition of "within reason".

### PASS

All must hold:

1. candidate points are causally known substructure swings;
2. they belong to the same relevant local/substructure context visible by `decision_at`;
3. tilt direction obeys SOURCE;
4. visual geometry is consistent with the SOURCE examples and clearly functions as one liquidity pool;
5. no future/outcome information is required to reach the judgment.

### FAIL

Any of:

- wrong tilt direction;
- candidate points are arbitrary candles rather than substructure swings;
- points clearly belong to different unrelated structural contexts;
- geometry is clearly too separated to represent one pool when compared with the SOURCE examples;
- judgment would require future information.

### UNKNOWN

Use when:

- geometry is borderline;
- substructure ownership is ambiguous;
- available window is insufficient;
- source examples do not uniquely resolve the case;
- two competent blinded annotators disagree and adjudication cannot resolve from SOURCE alone.

UNKNOWN must remain UNKNOWN. It must not be forced to PASS to increase sample size.

## 4. Substructure pair evidence

### PASS

Both candidate points are already-confirmed swings and can be placed in one causally visible local structural sequence without using bars after `decision_at`.

### FAIL

At least one point is not a confirmed swing, or the points are visibly from unrelated structural sequences.

### UNKNOWN

The SOURCE/context does not permit a unique assignment by `decision_at`.

## 5. Blinding

For research annotation batches:

- hide all trade outcomes;
- randomize case order;
- do not expose whether the engine currently accepts/rejects the case;
- do not expose historical strategy PnL;
- preferably use at least two independent annotations for a validation sample before freezing a deterministic proxy.

## 6. Disagreement policy

If annotators disagree:

1. preserve both original annotations;
2. perform source-only adjudication;
3. if SOURCE cannot resolve the disagreement, final status is `UNKNOWN`;
4. never select the verdict that produces better backtest performance.

## 7. Deterministic automation rule

A future machine proxy may replace manual annotation only after:

- a frozen labeled sample exists;
- proxy features are defined before outcome inspection;
- the proxy is tested for agreement with source-only annotations;
- the proxy is classified explicitly as `TECHNICAL_NORMALIZATION` or `PROJECT_POLICY`;
- it does not use future/outcome information.

Until then, non-exact tilted EQH/EQL stays `UNKNOWN` unless explicit qualitative evidence is supplied.
