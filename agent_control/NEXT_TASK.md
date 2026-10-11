# Next Task — Failure Audit Before v3

Do not design or implement v3 yet.

Perform a reproducible failure audit of frozen v2/v2.1/v2.2 using only already-frozen artifacts and causal pre-entry fields.

Required outputs:
1. Decompose negative expectancy into signal quality, entry geometry, stop geometry, target/FTA geometry, modeled costs, and regime/direction effects.
2. Investigate LONG/SHORT asymmetry across year, symbol, branch, TF, cost burden, target distance, stop distance, fill behavior, and exit reason.
3. Determine whether SHORT underperformance is consistent across multiple independent slices or concentrated in one regime/subgroup.
4. Measure whether apparently good directional setups are being destroyed by poor reward/risk or costs.
5. Compare gross edge vs net edge to identify cost sensitivity.
6. Identify implementation asymmetries between LONG and SHORT, including sign/price/rounding/stop/target logic, before attributing differences to market structure.
7. Audit extreme-R trades and leverage-like normalization artifacts for bugs or unstable denominators.
8. Do not introduce filters, remove directions, or change strategy rules in this task.
9. Do not use v2.1/v2.2 changes as evidence that a threshold is optimal.

Create a new immutable diagnostic namespace, e.g. `docs/machine_strategy_failure_audit_v1/`, with:
- FAILURE_AUDIT_REPORT.md
- FAILURE_AUDIT.json
- LONG_SHORT_ASYMMETRY.json
- GROSS_VS_NET_COST_ATTRIBUTION.json
- EXIT_REASON_BREAKDOWN.json
- IMPLEMENTATION_SYMMETRY_QA.json
- EXTREME_R_AUDIT.json
- QA_REPORT.md
- freeze_manifest.json

Update `agent_control/STATUS.md` with the commit, principal findings, unresolved questions, and whether evidence justifies designing v3.

Do not create a v3 production rule until this audit is frozen.