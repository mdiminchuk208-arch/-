# Agent Status

State: MACHINE_STRATEGY_V4_DESIGN_DRAFT_COMPLETE_REVIEW_PENDING
Branch: `machine-v3-research`.

v3 remains frozen `MACHINE_STRATEGY_V3_QUALIFICATION_STOP`; do not rerun or tune it in place. The independently frozen failure audit remains the causal input for v4.

## v4 design draft

A complete pre-outcome v4 design draft now exists under `docs/machine_strategy_v4_design_v1/`:
- `MACHINE_STRATEGY_V4_SPEC.md`
- `DECISION_TREE.json`
- `V3_TO_V4_CHANGELOG.md`
- `V4_PREREGISTRATION.json`
- `RULE_PROVENANCE_REGISTRY.json`
- `TELEMETRY_SCHEMA.json`
- `AMBIGUITY_AND_STOP_REGISTRY.json`
- `DESIGN_DRAFT_RECEIPT.json`

The draft directly addresses frozen H00-H05 mechanisms while preserving LONG/SHORT symmetry, all five setup families and all qualification thresholds including WR>=70%.

Key design changes are preregistered before any v4 outcome:
- three-state CLEAN/CORRECTIVE/INVALID structural approach instead of terminally rejecting every intervening opposite M15 BOS before context;
- completed-close FTA lifecycle invalidation before order emission;
- event-driven resting-order lifetime instead of fixed one hour, with inherited 16h parent pending ceiling;
- separate structural zone and one-grid technical executable envelope under all adverse compatibility scenarios;
- nearest FTA must provide at least +1R net under doubled fee+slippage versus the full modeled stop unit;
- outcome-blind per-origin/gate telemetry.

No v4 financial outcome has been generated or viewed. No implementation has started. The design is NOT frozen/approved yet.

## Active gate

Independent v4 design review/freeze. Reviewer must verify causality, provenance, LONG/SHORT symmetry, lack of historical-PnL parameter search, deterministic semantics and consistency with frozen qualification/cost/compatibility policies. Publish exactly `MACHINE_STRATEGY_V4_DESIGN_PASS` or `MACHINE_STRATEGY_V4_DESIGN_STOP`.

Only DESIGN_PASS may open a separately named implementation/readiness gate. No historical financial run, OOS, PAPER/LIVE/private exchange API/orders or platform work. `trade_entry_allowed=false`.
