# Next Task — MACHINE_STRATEGY_v4 Independent Design Review / Freeze

State: DESIGN_DRAFT_COMPLETE_REVIEW_PENDING. Do not repeat v3 diagnosis and do not generate v4 financial outcomes.

## Pinned predecessors
- v3 causal failure audit publication: `54419daa29e7e68d6f692daee9cf2132203393ef`.
- failure audit manifest: `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`.
- v3 financial audit manifest: `129bde6fe60600449c6740d5cca4e093a20549f1a678390931836d081b50f4c2`.

## Review scope
Read all files in `docs/machine_strategy_v4_design_v1/`, especially:
- `MACHINE_STRATEGY_V4_SPEC.md`
- `DECISION_TREE.json`
- `V3_TO_V4_CHANGELOG.md`
- `V4_PREREGISTRATION.json`
- `RULE_PROVENANCE_REGISTRY.json`
- `TELEMETRY_SCHEMA.json`
- `AMBIGUITY_AND_STOP_REGISTRY.json`
- `DESIGN_DRAFT_RECEIPT.json`

Use serial `execution_auditor` -> `backtest_reviewer` / `no_lookahead_auditor` -> `final_independent_reviewer`. Root remains sole writer; hard ceiling root + one specialist.

Review must independently verify:
1. every v4 change is causally linked to frozen H00-H05 evidence rather than selected by exposed P&L;
2. LONG/SHORT symmetry and all five setup families are preserved;
3. the three-state approach contract is deterministic and cannot use future evidence;
4. completed-close FTA lifecycle uses only known data and never falls back to farther targets;
5. event-driven order lifetime has deterministic retirement semantics and no hidden duration search;
6. structural-vs-executable one-grid envelope is labeled technical normalization and evaluated across all compatibility scenarios, never as historical OKX truth;
7. the +1R doubled-cost nearest-FTA gate is fixed risk-unit parity, not a fitted historical optimum;
8. telemetry is observer-only and cannot feed outcomes back into admission;
9. frozen qualification thresholds, cost policy and compatibility adverse handling are unchanged;
10. no v4 historical financial output existed before design freeze.

Add synthetic design-consistency/causality/symmetry tests or review artifacts as needed without evaluating historical P&L.

## Decision
Publish exactly one:
- `MACHINE_STRATEGY_V4_DESIGN_PASS`
- `MACHINE_STRATEGY_V4_DESIGN_STOP`

On PASS: create an externally pinned `DESIGN_FREEZE_MANIFEST.json`, update control files, and open a separately named `MACHINE_STRATEGY_v4 Implementation Readiness` gate. Do NOT run financial outcomes in the design-review batch.

On STOP: list the exact deterministic/source/causality defect and repair only that defect before repeating review. Do not relax qualification targets.

PAPER=false. LIVE=false. `trade_entry_allowed=false`. No platform work.
