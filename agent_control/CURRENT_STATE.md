# Current State

Branch: `machine-v3-research`.

## Priority
Strategy first. Platform/site/integration work remains paused.

## Strategy status
`MACHINE_STRATEGY_v3` is coded/frozen but not yet financially qualified. No accepted v3 P&L result exists yet.

## Venue
OKX remains the strategy/data/trading target:
- BTC-USDT-SWAP
- ETH-USDT-SWAP

## Frozen Stage-A readiness
Stage A v1 is sealed:
- decision `MACHINE_STRATEGY_V3_QUALIFICATION_STOP`
- commit `5a63716e0a042d8b1778581ae0d513d6314fb188`
- manifest `e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0`

Reusable evidence is complete for the selected period:
- 105,120 continuous completed native OKX M15 bars per product;
- deterministic H1/H4/D1 derivation;
- 2,190 signed OKX funding settlements per product;
- deterministic QA/replay and independent Stage-A STOP review.

Stage A stopped because exact historical OKX tick/lot/filter epochs and ordinary historical account-applicable API SWAP fees were not publicly source-verifiable. This was an execution-model evidence STOP, not a strategy performance failure.

## Frozen compatibility policy
A separately versioned pre-outcome execution policy is now frozen at commit:
`23f275cae85d1cab4d91cc07351ffdef2560d75d`.

Namespace:
`docs/machine_strategy_v3_okx_compatibility_v1/`.

At the freeze point `POLICY_FREEZE_RECEIPT.json` records:
- historical_financial_outcomes_generated=false;
- historical_financial_authorized=false;
- implementation_started=false.

Frozen compatibility model:
- nine scenarios = price-grid multipliers 1/5/20 × lot/minimum multipliers 1/100/700;
- current OKX metadata is reference scale only, not claimed historical truth;
- one fixed reference candidate catalog/reservation and fixed reference risk denominator across scenarios;
- all cases retained;
- worst CLOSED financial value across scenarios used;
- eligibility/fill/closure disagreement or unresolved fills follow the preregistered adverse/STOP rule;
- actual signed historical funding included with the frozen settlement proxy/timing convention;
- base modeled cost 6bp fee +2bp slippage per leg;
- doubled-total-fees-and-slippage sensitivity mandatory;
- v3 signal/decision rules remain unchanged.

## Active work
`agent_control/CURRENT_BATCH.md` authorizes implementation of the NEW versioned OKX compatibility runner/binding and focused deterministic tests.

Required sequence:
1. implementation without touching frozen strategy/policy bytes;
2. independent no-lookahead/causality review;
3. independent final READY review;
4. freeze `MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY` or STOP;
5. only READY opens the one-shot historical financial validation.

No financial outcome may be read/generated before READY.

## Qualification target
Win Rate >=70% remains mandatory together with CLOSED>=200, PF>=1.20, positive net expectancy/P&L, doubled-cost net positive and PF>=1.00, DD<=20R, loss streak<=10, required slice/sample rules, Wilson lower bound>=0.60, concentration limits and no critical leakage/integrity failure.

If v3 later fails financially, freeze the failure evidence and open a new explicit strategy version, then continue autonomously. If it passes, proceed to OOS/forward then Paper. Platform reconnection only after strategy qualification milestones.

## Safety
Historical financial outcome access unauthorized until compatibility READY.
OOS not registered.
PAPER=false.
LIVE=false.
trade_entry_allowed=false.

## Preserved implementation checkpoint (2026-10-14 UTC)

The versioned OKX compatibility binding, guarded one-shot runner and freeze builder are implemented. The four policy files at 23f275ca remain unchanged; protected strategy and all Stage-A/transitive hashes match. QA: 30 compatibility +24 source/bridge/Stage-A tests PASS, Ruff/format/mypy/compile PASS, nine registered toy replays identical. Independent no_lookahead_auditor PASS on exact current code, including emitted-candidate prefix/future mutation, conflicts, ETH/LONG/SHORT and new campaign guard.

Actual roles: /root/okx_compatibility_policy_execution_auditor; /root/okx_compatibility_no_lookahead_auditor; /root/okx_compatibility_final_independent_reviewer. Serial root+one specialist. Final READY review was interrupted by usage on Oct13 and resumed Oct14; no final verdict/READY freeze yet. No actual historical financial namespace, evaluations or outputs. Current action: finish independent review; if PASS seal/commit/push READY, then execute only the frozen one-shot development run. Reuse all existing code and QA; do not restart collection or policy design.

ECC ecc@ecc2.2.3 enabled via /workspace/ecc-setup/codex-ecc; hooks remain inactive. OOS/PAPER/LIVE=false; trade_entry_allowed=false.

## Compatibility implementation freeze

Decision: MACHINE_STRATEGY_V3_OKX_COMPATIBILITY_V1_READY. Manifest: 5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1. Both independent causality and final non-author reviews PASS. QA54tests PASS plus static/compile/replay. Implementation checkpoint0f741938df2c1e1e15a4faaf0990b5b49ce2b8a4 is published. No actualfinancialoutcomes existed at READY freeze.

Next action immediately after publishing this READY: scripts/okx_v3_compatibility_runner_v1.py --run-historical-once --expected-ready-manifest-sha2565faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1 --ready-freeze-commit READY_COMMIT_SHA (insert published commit). All financial outputs go to docs/machine_strategy_v3_okx_financial_validation_v1. Preserve READY namespace and current CURRENT_BATCH/NEXT_TASK controlpins until run ends. This authorizes development only, not OOS/PAPER/LIVE. trade_entry_allowed=false.
