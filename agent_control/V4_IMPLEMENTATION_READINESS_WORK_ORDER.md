# MACHINE_STRATEGY_v4 Implementation Readiness v1

State: IMPLEMENTATION_READINESS_OPEN. This is a new gate after independently accepted design publication `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f`, external design manifest `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`. Design bytes are now immutable. No financial result is authorized in this gate.

## Verify and reuse

Run `scripts/verify_machine_strategy_v4_design_v1.py --resume-existing --expected-manifest-sha256 b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b` and the pinned v3 failure-audit verifier (manifest 9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3). On a fresh checkout restore exact raw audits with scripts/pack_okx_v3_catalog_audits_v1.py --restore first. Verify sealed Stage-A dataset/funding and all parent manifests, not just that files exist. No recollection or v3 rerun.

Read the frozen spec, normative ENTRY_EXIT_CONTRACT.json and EXECUTION_CONTRACT.json, registries, preregistration, current QA/review receipts and historical limitations. The design manifest, not opening/draft status labels, is current authority. Preserve Original/v2/v3 outcomes and code byte hashes; use separate v4 code paths.

## Scope

1. Implement the complete historical source-event/state/POI/FTA adapter for all five native H1/H4 families, H4/D1/H1 context and M15 refinement. Reuse only pinned raw discovery/aggregation components; explicit v4 overrides must not leak back into v3. Trace every mandatory decision field to completed causal data and keep exact formation/physical IDs.
2. Implement the exact frozen approach selector, native structural anchors, raw/reference inward target validity, selected-POI executable envelope, planned doubled-cost K_s parity, original formation+57600 half-open pending lifecycle, exclusive reservation and prospective event order. No threshold, entry/stop/target/exit choice or family/direction change.
3. Build guarded runner infrastructure with all nine scenario plans, one immutable reference catalog, base/doubled same path, fixed U accounting and inherited coherent minimum funding witnesses/valuation. Funding realization is post-event only. No production financial kernel may run on historical v4 cases before readiness freeze; test accounting/execution only with explicitly registered synthetic fixtures.
4. Implement append-only write-only telemetry and Anti-Scalp statistics classifications. FILL/EXIT decision_cutoff is the event observation cutoff; store emission_decision_at separately. NO_HTF_CONTEXT remains nonterminal WAIT, excluded rejected denominator; counts distinguish unique origins, physical ideas, gate exposure and retries. Telemetry cannot become strategy state.
5. Verify real public data authenticity/continuity/completed aggregation on all sealed 210240 native M15 bars and4380 signed funding rows, completed H1/H4/D1 prefixes and source byte hashes. Keep the frozen synthetic tick/lot/current-metadata/account-cost/mark/fill assumptions explicitly unverified as historical truth. New evidence may be documented separately but cannot silently change this frozen design/model.
6. Perform meaningful production conformance tests: prefix and future mutation, same-time TF advancement, structural-retirement and parent-deadline boundaries, first-test ownership/current-bar ordering, mirrored LONG/SHORT/five families, immutable FTA across scenarios, fixed-U/Q accounting and interval funding ambiguity, gap/EOF/unknown preservation, telemetry readback isolation, deterministic replay and guard negative tests. Synthetic design reference fixtures alone are insufficient.
7. Prepare data-exposure/OOS readiness: old history is exposed development. Define separate future untouched validation prerequisites, without registering false-pristine history or running OOS. Production qualification remains NONE.
8. Independent reviews and full QA, then externally pinned complete implementation freeze. Only a later separately named one-shot development-financial gate may authorize a historical financial run.

Allowed historical work here is source/data verification and causal feature/adapter readiness. Do not execute historical v4 trade fill/exit simulation or inspect case-level financial outcomes before complete implementation freeze. No historical P&L, PF, WR, expectancy, drawdown, MFE/MAE, equity or case-level finance output in readiness.

## Required artifacts

New namespace docs/machine_strategy_v4_implementation_readiness_v1/:
- IMPLEMENTATION_PROTOCOL.md and RULE_TO_CODE_CONFORMANCE.json;
- HISTORICAL_ADAPTER_COVERAGE.json and CAUSAL_FIELD_PROVENANCE.json;
- DATA_GRID_AUTHENTICITY_AND_CONTINUITY.json, DATA_EXPOSURE_AND_OOS_READINESS.json;
- RUNNER_OUTCOME_ISOLATION.json, EXECUTION_AND_FUNDING_CONFORMANCE.json;
- TELEMETRY_CONFORMANCE.json, QA_REPORT.md/QA_RECEIPT.json and logs;
- actual AGENT_REGISTER.json and independent reviews;
- IMPLEMENTATION_FREEZE_MANIFEST.json with all design/data/code/config/QA/review pins and external manifest SHA.

PASS: MACHINE_STRATEGY_V4_IMPLEMENTATION_READY only with full reviewed implementation and no historical financial access. STOP: exact causality/coverage/execution/guard blocker with checkpoint; no silent substitution or weakened qualification.

## Roles and safety

Root is sole writer. Serial root plus one specialist: backtest_engineer for scoped implementation design/conformance; historical_data_engineer for adapter/data review; execution_auditor for five-family/mirror/scenario/funding semantics; no_lookahead_auditor or backtest_reviewer for prefix/isolation; final_independent_reviewer for freeze. Do not launch all mechanically; collect each non-overlapping evidence needed. Any implementation change to a frozen rule requires an explicit new design version, not a patch hidden in readiness.

All qualification thresholds unchanged, including WR>=70%. No OOS execution, PAPER/LIVE/private exchange API/orders/platform work; trade_entry_allowed=false. ECC runtime /workspace/ecc-setup/codex-ecc, hooks inactive.
