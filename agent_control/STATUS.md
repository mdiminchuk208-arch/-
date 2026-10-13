# Agent Status

State: MACHINE_STRATEGY_V3_QUALIFICATION_STAGE_A1_OPEN
Branch: `machine-v3-research`.

User priority is now explicit: finish/qualify the strategy first; platform/site/unified-exchange-layer work is deferred.

## Strategy truth
`MACHINE_STRATEGY_v3` has frozen design and implementation artifacts, but it is NOT yet a qualified trading strategy and is NOT launch-ready. Historical financial v3 execution has not yet been accepted as a fair evidence-based validation because data/metadata/tick provenance and venue compatibility blockers remained.

Frozen/coded means the rules and implementation are available for testing. It does not mean profitability, robustness, OOS qualification, paper readiness or live readiness has been established.

The reason v3 rules are not being casually changed now is anti-overfit discipline: first test the frozen version honestly. If it fails, freeze the failure evidence and then open a new explicit strategy-version design gate rather than tuning v3 after seeing results.

## Venue scope
Original project live/execution set remains Bybit, Bitget, BloFin and MEXC. The broader exchange-selection audit is preserved as research evidence only; additional venues are not automatically added to the product plan.

For strategy validation, Bitget is the preferred public research source where its BTC/ETH USDT perpetual data/metadata can be defended. This does not by itself change future live venue choices.

## Active gate
`MACHINE_STRATEGY_v3 Qualification v1`.

Current batch `agent_control/CURRENT_BATCH.md` is Stage A1 readiness only: verify frozen inputs, build the narrowest strategy-only Bitget validation binding/data plan, resolve or formally STOP on historical tick/filter treatment, freeze cost model and pass/fail rules, and STOP before new financial outcomes.

Platform/site/unified-exchange-layer implementation is paused.

## Preserved exchange audit
`EXCHANGE_SELECTION_AUDIT_v1` remains a completed conditional architecture research artifact:
- freeze commit `ff20ac4bee75d605c0a7f4234fe74bb89a337fbf`
- manifest `06556298d9f8041c493af5225740425cdfc51807566a322e2dd86f944b9c24d5`
- final marker `FINAL_REVIEW_PASS_FOR_EXCHANGE_SELECTION`
It is not a mandate to add Kraken/OKX/other audited venues to the user's live venue set.

## Allowance policy
SERIAL-FIRST: one active specialist by default, hard ceiling two threads, second only for independent verification/review, medium reasoning for routine work, narrow context, checkpoint every batch.

Historical financial v3 backtest ready=false and authorized=false until Stage A readiness PASS opens the one-shot validation gate.
OOS registration: none.
Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.
