# MACHINE_STRATEGY_v4 — Implementation Readiness v1

State: IMPLEMENTATION_IN_PROGRESS. This namespace begins after independent design PASS and does not authorize historical financial evaluation.

## Frozen authority

- Design publication: `f88bff4a79a1e5c1aa64c0f16204a1f8b546fa1f`.
- External design manifest SHA-256: `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`.
- Design decision: `MACHINE_STRATEGY_V4_DESIGN_PASS`.
- v3 remains frozen `QUALIFICATION_STOP`; no v3 code or outcome artifact may be edited or rerun as strategy qualification.

## Implementation boundary

The readiness gate may implement and test only frozen v4 semantics. It may load/verify sealed OKX source bytes and causal prefixes, but it may not run historical v4 fill/exit simulation or expose case-level financial outcomes before an independently reviewed implementation freeze.

Separate v4 code paths are mandatory. Reuse of v3 is limited to pinned raw discovery/state/data primitives whose semantics were explicitly inherited. The following v4 rules are implemented separately and must never silently fall back to v3:

- M4 approach CLEAN/CORRECTIVE/INVALID state;
- raw and inward FTA-completion checks;
- one-grid executable envelope;
- doubled-cost 1R structural-payoff gate;
- half-open 57,600-second structural parent lifetime;
- outcome-blind gate telemetry.

## Current checkpoint

Created:

- `scripts/machine_strategy_v4_readiness_core.py` — pure nonfinancial contracts only;
- `tests/test_machine_strategy_v4_readiness_core.py` — synthetic mirrored/lifecycle/payoff/telemetry tests;
- `RULE_TO_CODE_CONFORMANCE.json` — frozen-rule mapping;
- `RUNNER_OUTCOME_ISOLATION.json` — explicit pre-freeze financial barrier.

No QA PASS is claimed yet. The repository CI workflow runs automatically only on `main` pushes or pull requests, not direct pushes to `machine-v3-research`. Therefore these new files require an actual cloud/local readiness run before any implementation PASS/freeze claim.

## Next implementation work

1. Build `machine_strategy_v4_historical_adapter.py` as a separate causal pre-entry adapter over sealed OKX M15/H1/H4/D1 data.
2. Bind all five families and H1/H4/D1 context without importing historical outcome code.
3. Implement selected-POI ownership, scenario plans, current completed-close FTA retirement and structural pending lifecycle.
4. Add append-only telemetry and prove it cannot feed strategy state.
5. Add nine-scenario execution/funding conformance on registered synthetic fixtures only.
6. Run prefix/future-mutation, mirrored LONG/SHORT, five-family, gap/EOF/unknown, deterministic replay and negative guard tests.
7. Independently review and externally pin `IMPLEMENTATION_FREEZE_MANIFEST.json` before opening any one-shot v4 financial gate.

PAPER=false. LIVE=false. `trade_entry_allowed=false`.
