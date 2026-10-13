# Next Task — MACHINE_STRATEGY_v3 OKX Compatibility Repair v1

The autonomous strategy campaign remains active. Stage A v1 is frozen STOP at commit `5a63716e0a042d8b1778581ae0d513d6314fb188`, manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`.

Do not rebuild or recollect the sealed Stage-A candles/funding namespace. Reuse it exactly.

## Why this repair exists
Stage A proved the OKX BTC/ETH M15 and funding path, but exact historical OKX tick/lot/filter epochs and ordinary historical account-applicable API SWAP fees are not publicly verified. This is a source-evidence barrier, not a strategy P&L result.

The independent Stage-A review explicitly permits a separately versioned compatibility policy before outcomes. This repair must create that policy without pretending synthetic assumptions are historical OKX facts.

## Objective
Create a defensible, explicitly modeled **MACHINE_STRATEGY_v3_OKX_COMPATIBILITY_v1** execution/financial binding that preserves the frozen v3 signal logic but removes the impossible requirement to claim unknown historical exchange filters as verified epochs.

Only after this compatibility policy is fully preregistered, independently reviewed and frozen may Stage-B financial outcomes be generated.

## Non-negotiable strategy boundary
Protected v3 signal/decision logic remains immutable. Do not change setup definitions, trend/range classification, entry signal rules, stop/target intent, score logic or trade selection because no financial outcome has yet been seen.

The compatibility version may change only venue/execution modeling needed to evaluate frozen signals on OKX:
- price/quantity quantization treatment;
- venue identity binding;
- fee/slippage/funding cash accounting;
- fill/rounding ambiguity handling;
- timestamp/known-at plumbing.

All changes must be frozen before financial output access.

## Historical tick/filter compatibility policy
Do NOT backdate current OKX filters and do NOT fabricate `verified=true` epochs.

Instead implement a modeled stress family whose values are explicitly labeled synthetic compatibility assumptions, not historical exchange truth.

Required principles:
1. Use the documented current OKX tick/lot/contract fields only as a scale/reference, never as a historical claim.
2. Predefine multiple adverse quantization scenarios before outcomes, including intentionally coarser price/size grids than the current grid.
3. Evaluate each candidate trade under all preregistered quantization scenarios and use the **worst financial result / most adverse valid execution state** for qualification. Never choose the scenario that improves the trade.
4. If scenario disagreement makes a trade outcome or eligibility unresolved, retain it as unresolved/adverse according to a preregistered deterministic rule; do not silently discard losing/ambiguous cases.
5. Preserve all original candidate cases so the modeled compatibility layer cannot improve Win Rate by selectively removing adverse groups.
6. Record clearly that this historical run is a conservative compatibility model, not an exact historical OKX microstructure reconstruction.

The compatibility designer must freeze the exact scenario ladder and ambiguity rule before outcome generation. No parameter sweep after P&L access.

## Cost model
Reuse the existing preregistered project policy rather than inventing post-outcome thresholds:
- frozen core fee model: 0.0006 per leg;
- frozen core slippage model: 0.0002 per leg;
- actual signed OKX funding from the sealed Stage-A historical funding series;
- mandatory doubled-total-fees-and-slippage sensitivity already preregistered in Stage A;
- promotion requires doubled-cost net P&L positive and doubled-cost Profit Factor >= 1.00, in addition to the base qualification requirements.

The 6bp/2bp model must be labeled a model, not a proven historical OKX account rate. The doubled-cost stress is the mandatory robustness envelope while exact historical account fees remain unavailable. If later verified applicable costs exceed the frozen envelope, requalification is required before Paper/LIVE.

## OKX financial binding
Create a new versioned runner/adapter/binding. Do not mutate frozen v3 runner/adapter bytes.

The new binding must:
- consume the sealed official OKX BTC-USDT-SWAP / ETH-USDT-SWAP M15 inputs;
- preserve deterministic H1/H4/D1 derivation and completed-bar causality;
- bind venue identity as OKX, never BYBIT;
- account for actual signed funding settlements while positions are open using the frozen historical funding series;
- apply base and doubled-cost scenarios deterministically;
- implement the preregistered quantization stress family/worst-case rule;
- preserve intrabar ambiguity policy and no-lookahead rules;
- generate no output until preregistration integrity checks pass.

## Existing qualification thresholds remain frozen
Use the previously preregistered Stage-A thresholds without relaxation:
- Win Rate >= 70%;
- CLOSED trades >= 200;
- Profit Factor >= 1.20 base;
- net expectancy R > 0;
- net P&L > 0;
- doubled-cost PF >= 1.00 and doubled-cost net positive;
- max case-ledger drawdown <= 20R;
- max consecutive net losses <= 10;
- each coin+direction >=30 CLOSED and net positive;
- Wilson 95% lower bound >=0.60;
- largest quarter profit share <=0.50;
- largest coin profit share <=0.80;
- zero filled unknown exits;
- no critical causality/integrity failure.

Do not weaken criteria after outcomes.

## Compatibility repair workflow
Use one specialist at a time.
1. `execution_auditor` or `backtest_engineer`: design the exact synthetic quantization stress policy and venue/funding binding without P&L access.
2. Root implements new versioned compatibility code/tests only after policy text/JSON is frozen in a pre-outcome commit.
3. `no_lookahead_auditor` independently checks causality and that no financial outputs were accessed during design.
4. `final_independent_reviewer` verifies policy, code hashes, deterministic replay and authorization boundary.
5. If PASS, freeze `MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY` and immediately open the one-shot Stage-B financial validation under the autonomous campaign if allowance remains.
6. If STOP, solve the narrow technical issue autonomously; do not ask the user unless credentials/legal/capital are inherently required.

## Required namespace
Create a new immutable namespace:
`docs/machine_strategy_v3_okx_compatibility_v1/`

At minimum:
- `COMPATIBILITY_POLICY.md`
- `COMPATIBILITY_PREREGISTRATION.json`
- `QUANTIZATION_STRESS_POLICY.json`
- `COST_FUNDING_BINDING.json`
- `CAUSALITY_REPORT.md`
- `QA_REPORT.md`
- `INDEPENDENT_REVIEW.md`
- `freeze_manifest.json`

## Decision
Publish exactly one:
- `MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY`
- `MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_STOP`

READY authorizes only the preregistered one-shot historical financial validation. It does not authorize OOS, PAPER or LIVE.

PAPER=false. LIVE=false. `trade_entry_allowed=false`.
