# Current State

Branch: `machine-v3-research`.

## Priority
Strategy first. Platform/site/integration work remains paused.

## MACHINE_STRATEGY_v3 status
v3 is coded/frozen but not yet financially qualified. No accepted v3 P&L result exists yet, so there is still no evidence-based reason to redesign its signal rules.

## Selected venue
OKX remains the strategy/data/trading target:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

Backtesting uses the repository's deterministic Python tooling and official/public OKX evidence.

## Frozen Stage-A readiness result
Stage A v1 is sealed at:
- decision: `MACHINE_STRATEGY_V3_QUALIFICATION_STOP`
- commit: `5a63716e0a042d8b1778581ae0d513d6314fb188`
- namespace: `docs/machine_strategy_v3_okx_qualification_v1/`
- manifest: `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`

Stage A successfully established:
- 105,120 continuous native completed OKX M15 bars per product (210,240 total);
- 365-day warmup plus two complete UTC development years;
- deterministic H1/H4/D1 derivation;
- 2,190 signed historical funding settlements per product from official OKX archives/API, all source-verified;
- deterministic replay and targeted QA;
- no new strategy financial outcomes were read.

Stage A stopped only because exact historical OKX tick/lot/filter epochs and historical account-applicable API SWAP fees could not be source-verified. This is an execution-model evidence barrier, not a strategy performance result.

## Active repair gate
`MACHINE_STRATEGY_v3 OKX Compatibility Repair v1` is now open via `agent_control/NEXT_TASK.md`.

The repair will create a separately versioned historical compatibility execution model before P&L access:
- preserve v3 signal/decision logic byte-for-byte;
- never backdate current OKX metadata or fabricate historical epochs;
- preregister multiple synthetic adverse quantization scenarios using current documented filters only as reference scale, not historical truth;
- evaluate all candidate cases under all scenarios and qualify on deterministic worst-case/adverse treatment;
- do not discard ambiguous/adverse trades to improve Win Rate;
- use the existing 6bp fee + 2bp slippage per-leg modeled cost policy plus actual signed funding;
- require the already preregistered doubled-total-cost robustness condition;
- implement a new versioned OKX financial binding/runner rather than mutating the frozen Bybit-bound runner.

Only after compatibility policy, code, causality and replay are independently frozen READY may financial outputs be generated.

## Qualification policy remains unchanged
Hard targets include Win Rate >=70%, CLOSED >=200, PF>=1.20, positive net expectancy/P&L, doubled-cost net positive and PF>=1.00, drawdown<=20R, loss streak<=10, required coin+direction sample/net positivity, Wilson lower bound>=0.60, concentration limits and zero critical causality/integrity failures.

If v3 later fails those financial/robustness criteria, freeze the failure evidence and open a new explicit strategy version; continue autonomously. If it passes, proceed to OOS/forward then Paper. Only after Paper qualification reopen platform reconnection work.

## Safety
Historical financial outcome access is currently unauthorized until compatibility READY.
OOS not registered.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.

## Compatibility policy checkpoint

One execution_auditor identity /root/okx_compatibility_policy_execution_auditor designed the pre-outcome model in docs/machine_strategy_v3_okx_compatibility_v1/. Nine scenarios: price grid multipliers1/5/20 × lot/minimum multipliers1/100/700; one fixed reference candidate catalog/reservation, fixed reference risk denominator, all states retained, worst CLOSED value and STOP for eligibility/fill/closure disagreement or unresolved fills. Actual signed funding uses a declared M15 settlement-close proxy and coherent adverse timing, never a signal input. All Stage-A numeric thresholds unchanged. Policy bytes are frozen before implementation; no historical financial outputs or READY authorization. Next: implement versioned guarded binding, independent causality/QA/final READY review. PAPER/LIVE=false; trade_entry_allowed=false.
