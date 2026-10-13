# Current Batch — MACHINE_STRATEGY_v3 Qualification Stage A1

Execute only this batch, commit/push, then STOP. Do not continue automatically into financial outcome execution.

## Goal
Make frozen `MACHINE_STRATEGY_v3` honestly testable. This is strategy work, not platform work.

Use exactly one specialist: `backtest_engineer` (or the closest configured deterministic backtest/data specialist if role routing requires). No parallel subagents. Medium reasoning. Narrow context only.

## Required work
1. Verify and record the exact frozen v3 design/implementation/runner hashes currently intended for qualification.
2. Inspect only the strategy inputs and execution assumptions needed for a fair BTC/ETH historical run: candles, timestamps, completed bars, tick/lot/filter rounding, fees, slippage, funding and fill ambiguity.
3. Bind the qualification plan to Bitget BTC/ETH USDT perpetual public data as the preferred research source, without changing the user's live exchange set and without building a general platform adapter.
4. Determine whether reproducible continuous M15 history for the intended development period is available and whether historical tick/filter treatment is defensible.
5. If historical tick/filter epochs are unavailable, DO NOT backdate current metadata. Produce the narrowest preregistered compatibility proposal needed for a fair future financial run, before reading any new v3 financial outcomes.
6. Freeze the exact qualification date range, cost assumptions, metrics and deterministic pass/fail rules by reusing existing frozen requirements where available. Do not choose thresholds after seeing outcomes.
7. Add focused no-lookahead/data-causality checks needed for the later financial run.

## Required Stage-A1 artifacts
Create `docs/machine_strategy_v3_qualification_v1/` with at least:
- `READINESS_REPORT.md`
- `FROZEN_INPUTS.json`
- `DATA_METADATA_READINESS.json`
- `COST_MODEL_PREREGISTRATION.json`
- `QUALIFICATION_RULES.json`
- `STAGE_A1_QA_REPORT.md`

## Decision for this batch
Publish exactly one:
- `V3_QUALIFICATION_STAGE_A1_PASS` — all prerequisites are explicit enough to open one-shot financial validation next;
- `V3_QUALIFICATION_STAGE_A1_STOP` — list exact missing data/metadata/causality blockers.

Do NOT run/read new v3 financial outcomes in Stage A1. Do NOT tune strategy rules. Do NOT build website/backend/unified exchange layer. Do NOT place orders or use private APIs. PAPER=false, LIVE=false, `trade_entry_allowed=false`.

STOP after commit/push.
