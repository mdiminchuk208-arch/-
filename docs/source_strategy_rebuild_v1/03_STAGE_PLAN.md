# Source Strategy Rebuild v1 — staged execution plan

## Stage 1 — SOURCE FREEZE

Goal: freeze the user's strategy rules exactly as supplied and separate SOURCE / TECHNICAL_NORMALIZATION / PROJECT_OVERLAY.

Outputs:
- `00_SOURCE_AUTHORITY.md`
- `01_SOURCE_RULES.md`
- `02_SEMANTIC_POLICY_AND_OVERLAYS.md`

No P&L. No historical trade simulation.

## Stage 2 — EXECUTABLE SEMANTICS

Translate each source concept into causal machine predicates without changing its meaning.

Required contracts:
- swing/HH/HL/LH/LL identity;
- BOS and CHOCH semantics;
- range construction and deviation;
- OB construction;
- imbalance geometry;
- breaker construction;
- liquidity/EQH/EQL/trendline-liquidity objects;
- OTE anchors and 0.5/0.62/0.705/0.79 levels;
- SFP 3-candle + optional 4th-confirmation semantics;
- AMD context telemetry;
- causal IDs and `known_at` timestamps.

Every non-source numeric choice must be labeled `TECHNICAL_NORMALIZATION` and independently reviewable.

## Stage 3 — DETECTOR ONLY

Run the detector on BTC and ETH without money/exits.

For each bar/timeframe:
1. update completed market structure;
2. detect source formations;
3. update liquidity/POI/range/OTE objects;
4. emit every source setup candidate;
5. record exact PASS/FAIL/UNKNOWN reason for every source rule;
6. keep LONG and SHORT symmetric;
7. keep all setup families represented.

No fees, no P&L, no win/loss labels.

## Stage 4 — SOURCE-FIDELITY / COVERAGE GATE

Before any financial backtest, produce per coin/year/TF/family:
- number of source formations;
- number of candidate setups;
- number fully actionable after resolved source semantics;
- every drop reason and its count;
- duplicate/identity statistics;
- future-mutation/no-lookahead checks.

Project sanity target from the user:
`>=365 actionable setup opportunities per coin-year` across the active timeframe universe.

If the count remains at tens per year, STOP and fix source detection. Do not proceed to P&L.

## Stage 5 — ENTRY / STOP / TARGET CONTRACT

Only after source-fidelity passes, freeze how an emitted valid setup becomes an order.

Use source-backed rules where the user's supplied materials define them. Any missing stop/target/partial/re-entry semantics must be resolved explicitly from other user-supplied source material or clearly labeled project policy/technical normalization. Never borrow old v2-v4.1 behavior silently.

Then apply exchange/cost/risk overlays after the source setup exists.

## Stage 6 — ONE-SHOT DEVELOPMENT BACKTEST

Only after Stages 1–5 are independently frozen:
- preregister exact window and products;
- run one deterministic financial evaluation;
- freeze result before analysis;
- independent audit;
- report CLOSED, WR, PF, expectancy, gross/net P&L, costs, DD, loss streak, coin/direction/family/TF breakdowns.

Qualification target remains WR >=70% plus the existing robustness thresholds.

## Stage 7 — ROBUSTNESS / OOS / PAPER

Only after a development PASS:
- robustness;
- pristine OOS/forward;
- PAPER with real elapsed time;
- platform reconnection only after strategy qualification.

## Current authorized next action

Proceed only to Stage 2. Do not run financial history.
