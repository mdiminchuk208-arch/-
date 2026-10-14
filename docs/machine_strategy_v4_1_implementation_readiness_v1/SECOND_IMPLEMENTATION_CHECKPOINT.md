# MACHINE_STRATEGY_v4.1 — second implementation checkpoint

State: IMPLEMENTATION_IN_PROGRESS. This checkpoint does **not** claim READY and does not authorize historical financial evaluation.

Frozen design authority remains publication `96e76edf0e526c588cf87a665da681f577cca77a`, external design manifest `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`.

## Added since the initial checkpoint

- `tests/test_machine_strategy_v4_1_selected_poi_inventory.py`
  - RANGE mandatory-reaction exemption then subsequent consumption;
  - origin CONF A/B monotonic latch;
  - native bar opened before eligibility cannot consume;
  - equal-cutoff pre-emission consumption rejects;
  - context WAIT cannot create false eligibility;
  - half-open parent deadline.
- `scripts/machine_strategy_v4_1_execution_binding.py`
  - distinct v4.1 nine-scenario non-financial path;
  - H04/H05 and nearest-FTA lifecycle retained;
  - Decimal50 HALF_EVEN execution scope;
  - entry/stop/target/quantity persisted as canonical strings;
  - every adverse/ineligible scenario retained; no historical fill/exit engine.
- `tests/test_machine_strategy_v4_1_execution_binding.py`
  - mirrored LONG/SHORT scenario retention;
  - completed FTA remains an ineligible state instead of disappearing;
  - canonical-string transport and version guard.
- `scripts/machine_strategy_v4_1_funding_guard.py`
  - registered-synthetic-only Decimal80 funding witness;
  - coherent -1/+1 same-timestamp fill/exit slots;
  - adverse minimum signed funding cash;
  - historical OKX funding evaluation unconditionally blocked in readiness.
- `tests/test_machine_strategy_v4_1_funding_guard.py` synthetic funding/guard witnesses.
- Required readiness artifacts added:
  - `HISTORICAL_ADAPTER_COVERAGE.json`;
  - `CAUSAL_FIELD_PROVENANCE.json`;
  - `DATA_EXPOSURE_AND_OOS_READINESS.json`;
  - `EXECUTION_AND_FUNDING_CONFORMANCE.json`;
  - expanded `RULE_TO_CODE_CONFORMANCE.json`.

These tests are **authored but not claimed executed** in this connector-only checkpoint. No CI PASS, implementation PASS, catalog size, fill/exit result, WR, PF, P&L or trade outcome is inferred.

## Exact remaining production-readiness barrier

The remaining material implementation task is the distinct full historical v4.1 source/lifecycle adapter and its executed QA:

1. Bind preproposal selected-POI registration/latch for all five families to the sealed OKX source stream.
2. At every completed M15 cutoff, evaluate first admissible M4/context eligibility without creating an extra signal clock.
3. Snapshot native-TF context as known at native bar OPEN; publish eligible contact only at that native bar CLOSE. A bar opened before eligibility is wholly ineligible.
4. Keep every-M15 pending-order execution/rechecks independent from native first-test publication; current-bar OPEN/wick execution precedes contact learned at CLOSE.
5. Apply equal-cutoff completed contact before H1 emission; preserve H4 midbar emission/fill and no retroactive CLOSE cancellation.
6. Bind the distinct v4.1 nine-scenario path, common reference catalog/U, synthetic execution/funding guards and Decimal50→canonical-string→Decimal80 transport.
7. Run source-only full-period/prefix/future-mutation/deterministic replay on the sealed BTC/ETH history with a hard finance-engine trap.
8. Run static/type/compile plus targeted and relevant inherited tests on the exact bytes.
9. Perform serial execution/no-lookahead/final independent review and publish external `IMPLEMENTATION_FREEZE_MANIFEST.json`.

Only exact `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY` may open a separately named one-shot development-financial gate. Until then: financial validation=false, OOS=false, PAPER=false, LIVE=false, `trade_entry_allowed=false`.
