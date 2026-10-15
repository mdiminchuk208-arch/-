# Source Strategy Rebuild v1 — semantic policy and overlays

## Rule classes

Every executable rule must carry exactly one class:

1. `SOURCE_RULE` — directly supported by the user's strategy material.
2. `TECHNICAL_NORMALIZATION` — a machine definition needed to make an underspecified source phrase computable.
3. `PROJECT_OVERLAY` — bot/exchange/risk/qualification policy that is not part of the source strategy.

A `TECHNICAL_NORMALIZATION` or `PROJECT_OVERLAY` must never be reported as a source rule.

## Unknown semantics policy

If a source concept exists but its exact numeric meaning is missing, the engine must not silently convert it to a hard rejection.

During source-fidelity/detector stages:
- preserve the formation/candidate;
- attach `UNKNOWN_<CONCEPT>`;
- record the exact missing semantic;
- do not delete the opportunity from coverage telemetry;
- do not create P&L from that unresolved candidate.

Only after the normalization is separately frozen may that concept become PASS/FAIL in the executable detector.

## No visual-AI dependency

The target implementation is rule-following code, not discretionary chart-image judgment. Images from the source are evidence/examples used to understand the written rule; production detection must be based on causal market data and explicit predicates.

## Timeframe policy

Source truth: market structure and SFP are stated to apply on all timeframes.

Initial executable bot universe is a PROJECT scope, not a source restriction. The rebuild must first support the already available native/derived set:
- M15
- H1
- H4
- D1

The architecture must not encode H1/H4 as the only legitimate setup timeframes. Lower-timeframe expansion (including M5 when source-quality data is available) must be possible without rewriting source rules.

## User frequency requirement — PROJECT_OVERLAY

The user requires a practical strategy with frequent opportunities and has set a sanity expectation of at least roughly one trade opportunity per day per coin.

For this rebuild, before any P&L is opened, run an outcome-blind **coverage gate**:
- report raw source formations per coin/year/TF/family;
- report fully machine-resolved actionable setups per coin/year/TF/family;
- report the funnel reason for every drop;
- target sanity threshold: `>=365 actionable setup opportunities / coin-year` across the active timeframe universe.

This threshold is a product/coverage requirement, not a claim that the source guarantees exactly one profitable trade each day. The engine must never fabricate trades to hit the count. If the detector remains at tens of opportunities per year, the result is `SOURCE_FIDELITY_STOP`, not a profitability backtest.

## Existing project overlays retained only after source detection

The following remain outside source detection and may be applied only after a setup exists:
- OKX execution compatibility model;
- fee/slippage/funding assumptions;
- anti-scalp/cost viability rules where explicitly retained by project policy;
- risk sizing and portfolio limits;
- qualification target WR >= 70% and other robustness thresholds;
- PAPER/LIVE safety gates.

## Prohibited shortcuts

- no outcome-derived tuning before source detector freeze;
- no family deletion because an old version lost money;
- no LONG/SHORT deletion because an old sample was weak;
- no arbitrary cooldown/expiry copied from old engines;
- no hidden threshold for `large body`, `small wick`, `clear range`, `context`, `fast`, `meaningful liquidity`;
- no financial test until coverage/source-fidelity passes.
