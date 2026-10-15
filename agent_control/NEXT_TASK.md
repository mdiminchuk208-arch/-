# Next task — Source Strategy Rebuild v1 Stage 2

State: `SOURCE_STRATEGY_REBUILD_STAGE_2_EXECUTABLE_SEMANTICS`.

Authority:
- `docs/source_strategy_rebuild_v1/00_SOURCE_AUTHORITY.md`
- `docs/source_strategy_rebuild_v1/01_SOURCE_RULES.md`
- `docs/source_strategy_rebuild_v1/02_SEMANTIC_POLICY_AND_OVERLAYS.md`
- `docs/source_strategy_rebuild_v1/03_STAGE_PLAN.md`

Do not resume v4.1 strategy design or financial execution. Its artifacts remain frozen historical evidence only.

## Stage 2 required work

1. Build a complete versioned rule registry for structure, BOS/CHOCH, Range/Deviation, OB, Imbalance, Breaker, liquidity, OTE, SFP and AMD context.
2. For every rule record:
   - exact source statement / source section;
   - rule class (`SOURCE_RULE`, `TECHNICAL_NORMALIZATION`, `PROJECT_OVERLAY`);
   - causal inputs and `known_at` semantics;
   - deterministic output/object identity;
   - executable predicate where source is sufficiently exact;
   - explicit `UNKNOWN_*` when the source is qualitative or incomplete.
3. Implement a new detector core under new source-strategy module names. Do not subclass/import v4.1 strategy/admission logic.
4. Initial active TF universe: M15/H1/H4/D1. Never encode H1/H4 as the only setup TF. Structure/SFP must be reusable on every active TF.
5. Add synthetic source-semantics tests for bullish/bearish structure, BOS/CHOCH, Range+Deviation, OB+Imbalance, Breaker chain, liquidity, OTE and SFP; test unresolved qualitative semantics are preserved instead of hard-rejected.
6. Enforce completed-bar/no-lookahead semantics and stable causal IDs.
7. No P&L, fees, funding, TP/SL simulation or profitability labels in Stage 2.
8. After implementation QA, open Stage 3 detector-only historical coverage. Before P&L, report formations/candidates/actionable/drop reasons by coin/year/TF/family and enforce source-fidelity sanity (`>=365 actionable setup opportunities / coin-year` project target; no fabricated trades).

Safety: `trade_entry_allowed=false`; production NONE; no PAPER/LIVE/private API/orders/platform.
