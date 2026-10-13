# Exchange Selection Audit v1 — Serial Runbook

This runbook controls execution of the already-open `EXCHANGE_SELECTION_AUDIT_v1` gate. It does not change the frozen scoring model, candidate universe, strategy, or final evidence requirements in `NEXT_TASK.md`.

## Goal
Complete the exchange-selection gate with the lowest practical Work/Codex allowance consumption while preserving independent verification and final review quality.

## Concurrency and reasoning
- Default: exactly **1 active specialist**.
- Hard ceiling: **2 active specialists** only when the second is an independent verifier/reviewer.
- Never run two collection workers on the same evidence.
- Routine evidence collection: medium reasoning.
- High reasoning: only critical synthesis, risk/security/execution audit, statistics/robustness, red-team, final independent review.
- Use narrow context. Venue collectors should read only this runbook, `NEXT_TASK.md` sections relevant to exchange selection, the preregistration/protocol/worker contract, and their own durable checkpoints. Do not load frozen strategy/backtest namespaces unless necessary for a specific compatibility question.

## Durable staged workflow

### Stage 0 — already complete
Preregister scoring, missing-data penalties, hard gates, sensitivity, evidence protocol and worker contract before venue outcomes are collected.

### Stage 1 — low-cost hard-gate triage
Use one `venue_researcher` sequentially to screen every required candidate:
OKX, Binance Futures, Hyperliquid, Gate, Bitget, Bybit, KuCoin Futures, BloFin, MEXC, Kraken derivatives/futures, Coinbase International/perpetual where applicable, Deribit where applicable.

For each venue collect only enough official/current evidence to determine:
1. required BTC + ETH perpetual product exists and identity is deterministic;
2. public API is reachable from current cloud environment;
3. current tick/price/lot metadata is publicly defensible;
4. public BTC/ETH candle history appears technically capable of required M15 research path or is clearly insufficient;
5. bot order API exists;
6. safe API permissions / custody model are technically compatible;
7. base/API fee schedule is deterministically identifiable.

Persist each venue immediately to `docs/exchange_selection_audit_v1/checkpoints/<venue>.json` before moving on. Include URLs, retrieval timestamps, response/hash evidence where possible, PASS/FAIL/UNKNOWN per triage criterion, and exact reason. Do not calculate final ranking yet.

A venue with decisive `PRODUCT_MISMATCH` or decisive hard-gate failure may be marked excluded/deferred and does not receive expensive deep evidence collection unless final reviewer later identifies a factual gap.

### Stage 2 — deep evidence for survivors only
For venues that survive Stage 1, collect the full evidence required by `NEXT_TASK.md`, one evidence family at a time and checkpoint after each family:
1. fees + funding;
2. historical/public data + metadata provenance;
3. API reliability + execution capability + security;
4. liquidity/spread/depth/slippage snapshots.

Use specialist roles sequentially. Reuse checkpointed venue evidence instead of recollecting it.

### Stage 3 — deterministic matrices and scores
After evidence collection is complete, use `statistics_robustness_analyst` to build the required normalized matrices, scores and sensitivity outputs strictly from preregistered rules. No venue evidence collection should be repeated here.

### Stage 4 — independent challenge
Run `overfit_red_team` once against the frozen evidence + deterministic rankings. Repair only factual/evidence defects; do not alter scoring weights after seeing winners.

### Stage 5 — final independent review
Run `final_independent_reviewer` once. Publish exactly `EXCHANGE_SELECTION_AUDIT_FROZEN_PASS` or `EXCHANGE_SELECTION_AUDIT_FROZEN_STOP`, final required artifacts and manifest.

## Resume rule
Every cloud run must begin by checking existing checkpoint files and continue from the first incomplete checkpoint. Never redo a completed venue/evidence family unless its source is invalid, stale for the gate, or independent review explicitly requires re-checking it.

## Launch invariants
- Do not change `MACHINE_STRATEGY_v3` rules.
- Do not run/read historical v3 financial outcomes.
- Do not generate OOS signals/trades.
- PAPER/LIVE remain OFF.
- `trade_entry_allowed=false`.
