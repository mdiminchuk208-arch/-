# Next Task — MACHINE_STRATEGY_v3 Qualification v1

Platform/site/unified-exchange-layer work is paused by user direction. The active goal is to finish the strategy first.

## Current truth
`MACHINE_STRATEGY_v3` has a frozen design and implementation, but it is NOT yet a qualified trading strategy. Historical financial v3 execution was previously blocked because executable historical metadata/tick provenance and venue/data compatibility were not defensible enough. Therefore frozen/coded != validated/profitable/launch-ready.

Preserve all frozen v3 strategy rules during this qualification gate. Do not tune rules from newly observed financial outcomes. If the frozen version fails, freeze the failure evidence and open a new explicit strategy-version design gate afterward.

## Objective
Answer whether frozen `MACHINE_STRATEGY_v3` is a defensible trading candidate using realistic BTC/ETH perpetual data and execution assumptions, before doing platform work.

## Venue/data scope
The original project exchange set remains Bybit, Bitget, BloFin and MEXC. Do not expand the strategy/product venue set merely because the broader architecture audit examined more venues.

For validation evidence, prefer Bitget public BTC/ETH USDT perpetual data where it is reproducible and sufficiently documented. Other retained sources may be used only as independent references, not to change the user's intended live venue set.

## Qualification sequence

### Stage A — pre-outcome readiness
Before any new v3 financial outcome is read:
1. verify exact frozen v3 spec/runner/code hashes and identify all inputs that affect fills, stops, targets, fees, funding, tick/lot rounding and causality;
2. define exact BTC/ETH perpetual product identities and validation date range;
3. verify continuous M15 data path and timestamp/completed-bar semantics;
4. resolve historical tick/lot/filter treatment. Never backdate current metadata. If historical epochs cannot be recovered, preregister a conservative compatibility rule/version BEFORE financial outcomes or STOP;
5. freeze fee/slippage/funding assumptions from evidence, not later P&L;
6. freeze qualification metrics and pass/fail rules before financial execution, reusing already-frozen criteria where they exist instead of inventing post-outcome thresholds;
7. verify no-lookahead/prefix causality and deterministic replay readiness.

### Stage B — one-shot historical financial validation
Only after Stage A PASS, explicitly authorize and execute one deterministic frozen-v3 historical validation on the preregistered development period. No parameter search or tuning during/after the run inside this version.

Report at minimum:
- CLOSED trades;
- Winrate;
- gross/net P&L in R and cash-normalized form where supported;
- Profit Factor;
- Expectancy;
- Avg R:R / payoff;
- Max Drawdown;
- max loss streak;
- fees, slippage and funding contribution;
- LONG vs SHORT;
- BTC vs ETH;
- setup family;
- market regime where available.

### Stage C — robustness and decision
Run deterministic robustness checks and independent review. Explicitly test whether apparent edge survives realistic cost and execution sensitivity and whether performance is concentrated in one direction/setup/coin/time slice.

Publish exactly one:
- `MACHINE_STRATEGY_V3_QUALIFIED_PASS` — only if the frozen v3 demonstrates a defensible positive edge and robustness under the preregistered rules;
- `MACHINE_STRATEGY_V3_QUALIFIED_FAIL` — freeze exact failure evidence and open a new strategy-version design gate;
- `MACHINE_STRATEGY_V3_QUALIFICATION_STOP` — if evidence/data/metadata is still insufficient for a fair financial test.

PASS does not mean LIVE-ready. It opens pristine OOS/forward validation next.

## Safety
- No platform/site work unless strictly required for strategy validation.
- No private trading API/order placement.
- No OOS clock until qualification and separate registration.
- PAPER=false.
- LIVE=false.
- `trade_entry_allowed=false`.

`agent_control/CURRENT_BATCH.md` defines the currently allowed atomic subset. Do not skip ahead automatically.
