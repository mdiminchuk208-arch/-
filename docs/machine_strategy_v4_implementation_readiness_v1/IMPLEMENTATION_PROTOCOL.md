# MACHINE_STRATEGY_v4 — Implementation Readiness v1

State: MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP. This namespace follows independent design PASS and does not authorize historical financial evaluation.

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

Component QA was actually executed: 54 tests and nine commands PASS, with exact tested/log hashes in QA_RECEIPT.json. This is prototype/synthetic and bounded source-only evidence, not complete model conformance. No repository CI PASS is claimed; its workflow runs on `main`/PR, not direct research-branch pushes.

## Checkpoint scope and deferred work

Separate source-only adapter, scenario binding, telemetry, lifecycle prototype and registered synthetic execution/funding runner are retained. Seven-day BTC/ETH prefix/future-mutation checks passed with position engines trapped. Complete five-family selected-POI ownership and full-period lifecycle conformance remain blocked by the frozen contract gap.

The next gate is a separate pre-outcome v4.1 selected-POI design amendment. It must define origin/context/eligibility and reaction semantics, and make planned50/inherited-ledger80 arithmetic scope explicit before implementation resumes. The planned IMPLEMENTATION_FREEZE_MANIFEST.json will seal only a STOP checkpoint; complete_implementation_freeze=false and implementation_ready=false. It cannot open a financial gate.

PAPER=false. LIVE=false. `trade_entry_allowed=false`.

## Current independently identified blocker

MACHINE_STRATEGY_V4_IMPLEMENTATION_STOP pending a separately frozen selected-POI first-test contract. Source/data and registered synthetic infrastructure are checkpointed, not complete implementation readiness. No historical v4 execution or financial output has been generated. See BLOCKER_REGISTER.json. Implementation_STOP checkpoint cannot open a financial gate.
