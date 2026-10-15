# Agent Status

State: `SOURCE_STRATEGY_REBUILD_STAGE_2_EXECUTABLE_SEMANTICS`.

The project has been reset to a source-first strategy rebuild. The authoritative strategy input is the user-supplied `Методичка.docx`. Historical machine versions v2/v2.1/v2.2/v3/v4/v4.1 and their financial/audit results remain frozen evidence, but they are **not authoritative interpretations of the source strategy** and must not supply rules silently.

Stage 1 source freeze is present in `docs/source_strategy_rebuild_v1/`:
- `00_SOURCE_AUTHORITY.md`
- `01_SOURCE_RULES.md`
- `02_SEMANTIC_POLICY_AND_OVERLAYS.md`
- `03_STAGE_PLAN.md`

Current work is Stage 2 only: translate the literal source into causal executable semantics and explicitly separate every predicate into `SOURCE_RULE`, `TECHNICAL_NORMALIZATION`, or `PROJECT_OVERLAY`.

Critical rebuild policy:
- no visual/discretionary AI dependency for production detection;
- no hidden numeric thresholds for qualitative source language;
- unresolved source semantics remain visible as `UNKNOWN_*` and may not silently delete formations from coverage telemetry;
- market structure and SFP are not restricted to H1/H4; the initial active data universe is M15/H1/H4/D1 as a project scope, with architecture open to lower TF expansion;
- old v4/v4.1 WAIT/REJECT gates, lifetimes, admission rules, family preferences and outcome-derived slices are forbidden carry-over unless separately justified and reclassified;
- no historical financial execution until source-fidelity/coverage and entry/stop/target contracts are frozen.

Before any new P&L, the detector must pass an outcome-blind source-fidelity/coverage gate. User project sanity target: `>=365 actionable setup opportunities / coin-year` across the active timeframe universe. This is a coverage requirement, not permission to fabricate trades; tens of opportunities per year means `SOURCE_FIDELITY_STOP` and detector repair.

Safety remains `trade_entry_allowed=false`; no PAPER/LIVE/private exchange API/orders/platform. Production candidate NONE.
