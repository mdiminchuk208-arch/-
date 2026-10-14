# Current Campaign — MACHINE_STRATEGY_v4.1 independent design review

The v4 implementation-readiness gate completed STOP and was published `766271619c7e03d8cc5dda08a2b3ec626d99c1e8`. Component QA PASS did not establish full implementation readiness.

A narrow pre-outcome v4.1 selected-POI/arithmetic-scope amendment has now been authored in `docs/machine_strategy_v4_1_design_v1/`. Do not redesign unrelated v4 rules and do not inspect historical financial outcomes or catalog-count effects.

Active gate: independently review the exact v4.1 draft for:
- causal selected-POI identity/provenance for SFP/OB/STB/BREAKER/RANGE;
- no self-cancel of required formation/reaction events;
- pre-emission first-test and active-order same-bar ordering;
- LONG/SHORT symmetry and native-TF/context clocks;
- parent deadline interaction and no retroactive state use;
- Decimal50 design/execution versus Decimal80 ledger boundary;
- preregistration/outcome isolation and unchanged qualification thresholds.

Run synthetic witnesses only; no historical fill/exit/P&L. Use serial `execution_auditor` → `no_lookahead_auditor` → separate `final_independent_reviewer`, root sole writer. Freeze exactly `MACHINE_STRATEGY_V4_1_DESIGN_PASS` or `MACHINE_STRATEGY_V4_1_DESIGN_STOP` with an externally pinned manifest. PASS opens only a new implementation-readiness gate.

No OOS/PAPER/LIVE/private API/orders/platform work. `trade_entry_allowed=false`; ECC hooks inactive.
