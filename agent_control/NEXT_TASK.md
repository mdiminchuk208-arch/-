# Next Task — MACHINE_STRATEGY_v4.1 Independent Design Review + Freeze

State: MACHINE_STRATEGY_V4_1_DESIGN_REVIEW_OPEN. Do not repeat the v4 implementation diagnosis or author a different strategy version.

Pinned parents:
- v4 implementation STOP publication: `766271619c7e03d8cc5dda08a2b3ec626d99c1e8`;
- v4 implementation STOP manifest: `6e325d6e5b3cffc4f143bfd4d390712b39ea940bccd4504c85148ed904bbcd7e`;
- frozen v4 design publication: `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f`;
- frozen v4 design manifest: `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`.

Review the exact authored v4.1 draft under `docs/machine_strategy_v4_1_design_v1/`, especially:
- `MACHINE_STRATEGY_v4_1_SPEC.md`;
- `SELECTED_POI_CONTRACT.json`;
- `ARITHMETIC_SCOPE_CONTRACT.json`;
- `PREREGISTRATION.json`;
- `FIELD_PROVENANCE.json`;
- `FIRST_TEST_DECISION_TREE.json`;
- `RULE_REGISTRY.json`;
- `SYNTHETIC_WITNESS_REGISTRY.json`.

Required work:
1. Verify all pinned input hashes/parent resumes before review.
2. Run synthetic witnesses for mirrored five-family identity/eligibility, required-reaction exemptions, pre-emission consumption, active-order same-bar contact/fill ordering, context-late eligibility, deadline boundaries, and Decimal50→Decimal80 boundary serialization.
3. Execution auditor checks that STB body/full-parent separation, BREAKER generated body, RANGE boundary reaction exemption and SFP/OB refined-POI inheritance are deterministic and do not silently alter unrelated v4 rules.
4. No-lookahead auditor checks known_at, native-TF clocks, same-time TF advancement, prospective context eligibility and no retroactive CLOSE cancellation.
5. Final independent reviewer must be separate from the design author. Freeze exactly one decision: `MACHINE_STRATEGY_V4_1_DESIGN_PASS` or `MACHINE_STRATEGY_V4_1_DESIGN_STOP`.
6. On PASS, create externally pinned `DESIGN_FREEZE_MANIFEST.json`, exact verifier/QA receipts, update controls and open a separate v4.1 implementation-readiness gate. On STOP, freeze exact blocker and do not implement around it.

No historical v4/v4.1 fill/exit simulation, financial metrics, catalog-count selection, threshold tuning, OOS, PAPER/LIVE/private API/orders or platform work. All qualification thresholds remain unchanged, including WR>=70%. `trade_entry_allowed=false`.
