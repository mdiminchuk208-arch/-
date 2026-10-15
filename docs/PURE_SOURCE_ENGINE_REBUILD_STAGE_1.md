# PURE_SOURCE_ENGINE_REBUILD_STAGE_1

Status: IMPLEMENTED_AWAITING_REPOSITORY_CI

## Baseline
- Base branch: `main`
- Base commit: `dab8d254aaf4babc07659e3d03d14b269445767b`
- Base Engine version: `0.4.20`
- Stage-1 Engine version: `0.4.21`
- SOURCE spec version: `ORIGINAL_STRATEGY_SPEC_v1.1`
- Stage: `CAUSAL OBJECT CORE + CONTAMINATION ISOLATION`
- Exchange dependency: none. OKX is primary for the project, but Stage 1 is exchange-agnostic.
- `trade_entry_allowed=false` is invariant. Private API and real orders are out of scope.

The remote GitHub commit is the baseline. A remote commit has no uncommitted working-tree state; no local/dirty experiment tree is used by this branch.

## Objective
Create a causal, replay-safe object layer in which a SOURCE market object exists independently from trade admission, later cancellation, or financial outcome. Stage 1 does not rewrite trading semantics of Structure, Liquidity, SFP, OB, Breaker, STB/BTS, Range, Entry, Stop, FTA or Exit.

## PURE_SOURCE contamination boundary
The official Stage-1 runtime profile is `strategy_profile=PURE_SOURCE`. The following PROJECT_POLICY families are forbidden: Anti-Scalp; `edge_cost_ratio`; cost viability; fee/slippage admission; project HTF filters; project medium-term filter; scoring; ranking; portfolio admission; correlation limits; daily-loss limits; leverage policy; TP 40/30/30; cost-adjusted breakeven; project re-entry filters.

Historical/research code is not deleted. It is outside `PureSourceRuntime` and cannot be applied through the PURE_SOURCE policy gate.

## Causal contract
Every object persisted through the Stage-1 causal registry carries `object_id, object_type, symbol, timeframe, direction, formation_at, known_at, confirmed_at, invalidated_at, formation_valid, trade_eligible, status, source_rule_ids, technical_normalization_ids, rejection_reasons, parent_object_ids, provenance` plus append-only lifecycle events.

`formation_valid` and `trade_eligible` are independent. A later invalidation/cancellation never rewrites the fact that an object existed and was valid at an earlier causal time.

- `formation_at`: physical time at which required SOURCE geometry formed.
- `known_at`: first time closed, available data made the object knowable.
- `confirmed_at`: later SOURCE confirmation only when such confirmation exists.
- `invalidated_at`: first causally known SOURCE invalidation event.

No fake confirmation timestamp is created for implementation convenience.

## Stable identity
Stable IDs are SHA-256 based on causal formation identity only. The ID builder rejects PnL, WIN/LOSS, MFE/MAE, future touch, cancellation, ranking and score fields. Covered types: swing, structure, liquidity_pool, POI, OB, breaker, SFP, STB/BTS, range, FVG, setup and physical idea.

## Rejection taxonomy
`OBJECT_INVALID_SOURCE`, `WAIT_CONFIRMATION`, `WAIT_ENTRY_CHAIN`, `WAIT_UNRESOLVED_SOURCE_RULE`, `SETUP_REJECTED_SOURCE`, `PROJECT_POLICY_DISABLED`, `CANCELLED_AFTER_READY`. A rejection is not automatically object invalidity.

## Closed-candle / no-look-ahead invariants
Unfinished candles and closes after decision time are rejected; prefix replay preserves known identity/state; future mutation cannot change past identity/formation/known history; outcomes cannot enter identity; later cancellation is appended, not deletion.

## SOURCE freeze
See `docs/source_freeze_v1/source_manifest.json`. Primary PDF bytes stored in repo are frozen from the existing SHA256 manifest. DOCX items available only through archive-manifest evidence are explicitly `FREEZE_BLOCKED_RAW_SOURCE_UNAVAILABLE`; recorded archive hashes remain provenance, not newly verified Stage-1 hashes.

## Files changed by Stage 1
`src/crypto_bot/strategy/profile.py`, `src/crypto_bot/strategy/causal_objects.py`, `src/crypto_bot/strategy/pure_source_runtime.py`, `tests/test_causal_object_core.py`, `tests/test_pure_source_profile.py`, `tests/test_pure_source_runtime.py`, `docs/source_freeze_v1/source_manifest.json`, `docs/PURE_SOURCE_ENGINE_REBUILD_STAGE_1.md`, `src/crypto_bot/__init__.py`, `pyproject.toml`.

## Explicit non-goals
No profitability calculation, PnL comparison, optimization, outcome-selected branch, private API, real order or LIVE enablement is introduced.
