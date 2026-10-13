# Next Task — MACHINE_STRATEGY_v3 Qualification v1

Platform/site/unified-exchange-layer work is paused by user direction. The active goal is to finish the strategy first.

## Current truth
`MACHINE_STRATEGY_v3` has a frozen design and implementation, but it is NOT yet a qualified trading strategy. Historical financial v3 execution was previously blocked because executable historical metadata/tick provenance and venue/data compatibility were not defensible enough. Therefore frozen/coded != validated/profitable/launch-ready.

Preserve all frozen v3 strategy rules during this qualification gate. Do not tune rules from newly observed financial outcomes. If the frozen version fails, freeze the failure evidence and open a new explicit strategy-version design gate afterward.

## Objective
Answer whether frozen `MACHINE_STRATEGY_v3` is a defensible trading candidate using realistic BTC/ETH perpetual data and execution assumptions, before doing platform work.

## Validation venue and data source
The project has selected **OKX** as the primary venue for v3 strategy qualification.

Primary products:
- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`

Primary data source must be official/public OKX market-data endpoints and retained OKX evidence where reproducible. Use native 15-minute candles for the strategy timeline, official instrument metadata for current tick/lot/product identity, funding history where required, and public order-book observations for execution-cost/slippage calibration. Do not substitute another exchange merely because it is easier unless a later explicit STOP/reselection gate is opened.

The existing OKX checkpoint already establishes current public reachability and product identity, but ordinary API SWAP fee applicability and historical tick/filter epochs remain unresolved. Those are Stage-A readiness items, not permission to invent values.

## Hard user qualification target
Before any new financial outcome is read, preregister **Win Rate >= 70%** as a hard target for strategy qualification. A strategy version below 70% does not pass the user's target and must move to a new explicit version after failure evidence is frozen.

Do not optimize only for Win Rate. PASS also requires positive net expectancy and positive net P&L after realistic costs, acceptable drawdown/loss streak, sufficient sample size, no critical leakage, and robustness across relevant slices. The 70% target must later survive OOS/forward validation and Paper Trading; an in-sample-only 70% is insufficient for platform reconnection.

## Qualification sequence

### Stage A — pre-outcome readiness
Before any new v3 financial outcome is read:
1. verify exact frozen v3 spec/runner/code hashes and identify all inputs that affect fills, stops, targets, fees, funding, tick/lot rounding and causality;
2. bind exact OKX BTC-USDT-SWAP / ETH-USDT-SWAP product identities and freeze the validation date range;
3. verify reproducible continuous native OKX M15 history and timestamp/completed-bar semantics;
4. resolve historical tick/lot/filter treatment. Never backdate current OKX metadata. If historical epochs cannot be recovered, preregister a conservative compatibility rule/version BEFORE financial outcomes or STOP;
5. freeze fee/slippage/funding assumptions from defensible OKX evidence before seeing P&L. Unknown ordinary API fee must remain unknown until resolved or handled by a preregistered conservative rule;
6. freeze qualification metrics and pass/fail rules before financial execution. `Win Rate >= 70%` is mandatory; all other numeric thresholds must also be preregistered before outcomes;
7. verify no-lookahead/prefix causality and deterministic replay readiness.

### Stage B — one-shot historical financial validation
Only after Stage A PASS, explicitly authorize and execute one deterministic frozen-v3 historical validation on the preregistered OKX development period. No parameter search or tuning during/after the run inside this version.

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
- `MACHINE_STRATEGY_V3_QUALIFIED_PASS` — only if the frozen v3 reaches Win Rate >=70% AND demonstrates positive net edge and robustness under all preregistered rules;
- `MACHINE_STRATEGY_V3_QUALIFIED_FAIL` — freeze exact failure evidence and open a new strategy-version design gate;
- `MACHINE_STRATEGY_V3_QUALIFICATION_STOP` — if OKX evidence/data/metadata is still insufficient for a fair financial test.

PASS does not mean LIVE-ready. It opens pristine OOS/forward validation next, where the 70% target remains active.

## Safety
- No platform/site work unless strictly required for strategy validation.
- No private trading API/order placement.
- No OOS clock until qualification and separate registration.
- PAPER=false.
- LIVE=false.
- `trade_entry_allowed=false`.

`agent_control/CURRENT_BATCH.md` defines the currently allowed atomic subset. Do not skip ahead automatically.
