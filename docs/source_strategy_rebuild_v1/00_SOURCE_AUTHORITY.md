# Source Strategy Rebuild v1 — authority

State: `SOURCE_STRATEGY_REBUILD_STAGE_2_EXECUTABLE_SEMANTICS`.

## Purpose

Rebuild the user's trading strategy faithfully before any new profitability work. Previous machine implementations v2/v2.1/v2.2/v3/v4/v4.1 remain frozen historical implementations and are **not** authoritative interpretations merely because they produced results.

## Authoritative source corpus

The strategy authority is the complete previously frozen user-supplied source corpus represented by:
- `docs/original_strategy_spec_v1_1/original_strategy_rule_registry_v1_1.json` and its immutable source citations/hashes;
- `docs/original_strategy_spec_v1_1/branch_contracts.json` and branch source citations;
- the supplied `Методичка.docx`;
- the cited Smart Money / SW source materials preserved by the v1.1 source-fidelity freeze.

`Методичка.docx` is a primary source but **not the only source**. A rule supported by another frozen source document must not be lost just because it is not fully described in Methodichka.

The frozen v1.1 verdict that the exact historical-original strategy was not uniquely identifiable remains true. That does not erase source rules; it means choices needed for one executable bot profile must stay visibly separated from literal source statements.

## User-resolved executable profile

The user's pre-backtest decisions U1–U6 in `docs/original_strategy_spec_v1_1/ORIGINAL_STRATEGY_SPEC_v1_1.md` are authoritative user choices for the executable bot profile, but they are **not SOURCE_RULE**. Preserve them under `USER_RESOLUTION_PRE_BACKTEST`:
- U1 exit;
- U2 stop;
- U3 entry branch;
- U4 timeframe profile;
- U5 liquidity handling;
- U6 re-entry / first-test-only.

Registered N11 conventions remain explicit `TECHNICAL_NORMALIZATION`, never source truth.

## Rule classes

Every executable predicate must belong to exactly one class:
1. `SOURCE_RULE` — directly supported by frozen user-supplied source material.
2. `USER_RESOLUTION_PRE_BACKTEST` — an explicit user decision selecting among source-permitted variants or closing a source ambiguity before outcomes.
3. `TECHNICAL_NORMALIZATION` — deterministic machine semantics required to make an underspecified rule computable.
4. `PROJECT_OVERLAY` — exchange, costs, risk, frequency sanity, qualification, safety and platform policy outside the source strategy.

No class may be silently promoted to SOURCE_RULE.

## Forbidden carry-over

Do not import as strategy truth:
- v2/v3/v4/v4.1 admission filters merely because they existed;
- v4.1 candidate starvation/lifecycle behavior;
- old outcome-derived family/direction preferences;
- old profitability labels, WIN/LOSS, MFE/MAE or P&L;
- old arbitrary lifetimes/cooldowns;
- hidden numerical thresholds for qualitative source terms;
- old machine labels that are not backed by the frozen source registry or explicit U/N records.

## Reuse that IS allowed

Reuse is required when it is provenance-safe:
- frozen SOURCE_RULE text/citations from original_strategy_rule_registry_v1_1;
- U1–U6 exactly as user resolutions;
- N11 conventions exactly as technical normalizations, subject to Stage 2 source-fidelity review;
- stable causal identity/no-lookahead infrastructure that does not change strategy semantics.

## Safety

This rebuild remains pre-financial. `trade_entry_allowed=false`. No PAPER/LIVE/private exchange API/orders/platform reconnection is authorized by this stage.
