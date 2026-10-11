# Machine v2.2

Frozen base v2 engine, five branches, TF roles, structure/liquidity/FTA, FIRST_TEST_ONLY, fixed stop, no BE and theoretical accounting remain unchanged. Inherited geometry/case IDs identify the same market opportunities across strategy versions; version-specific admission is frozen separately. Exact Original stays the source reference.

Retain v2.1 cost budget. Structural target distance must additionally cover at least one initial planned stop distance: abs(FTA-entry)/abs(entry-fixed stop)>=1. No farther substitute target; reject before order when nearest causal FTA fails.

A new risk-budget hypothesis: a full nearest-target win must offer at least the gross price risk of one planned stop. Unity is risk symmetry, not a searched optimum. It does not guarantee positive expectancy or solve sample/OOS/execution gaps.

This design is created only after the previous version result and robustness commits. One new pre-entry hypothesis, no parameter sweep, no removal based on realized WIN/LOSS, hold duration, coin, branch or period. No target percentage substitution, no farther target chosen for R. Version P&L will be calculated only after its own pre-outcome commit. Reusing fully viewed 2023-2025 data is development diagnosis, not independent validation. Production requires real execution evidence and forward paper; trade_entry_allowed=false.
