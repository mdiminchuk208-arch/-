# MACHINE_STRATEGY_v4.1 — third implementation checkpoint

State: IMPLEMENTATION_IN_PROGRESS. This checkpoint does **not** claim `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY` and does not authorize historical financial evaluation.

Frozen design authority remains publication `96e76edf0e526c588cf87a665da681f577cca77a`, external manifest `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`.

## Added in this checkpoint

- `scripts/machine_strategy_v4_1_selected_poi_inventory.py`
  - monotonic `reaction_required_at` latch for SFP/OB/RANGE physical POIs registered before reaction completion;
  - reaction timestamp cannot reset after first latch or after eligibility.
- `scripts/machine_strategy_v4_1_historical_adapter.py`
  - distinct v4.1 source/lifecycle path over sealed OKX public history;
  - H1/H4 formation discovery with every-M15 selected-POI eligibility checks;
  - native-TF context snapshot before current bar close, first-test publication only at native CLOSE;
  - equal-cutoff contact is applied before H1 proposal emission;
  - generated STB/BREAKER/RANGE physical handles remain separate from inherited parent consumption;
  - SFP/OB refined M15 POIs use origin-bound geometry without using historical financial outcomes;
  - half-open `formation_known_at+57600` deadline and structural retirement retained;
  - no historical position/fill/exit/P&L evaluation path.
- `scripts/verify_machine_strategy_v4_1_source_adapter.py`
  - BTC/ETH bounded deterministic replay;
  - future M15 tail mutation must not alter prefix bytes/digest;
  - `--full` requires two byte-identical full development-period source/lifecycle replays;
  - runtime asserts zero position-engine calls, zero financial outputs, `trade_entry_allowed=false`;
  - historical financial runner import trap.
- `tests/test_machine_strategy_v4_1_selected_poi_inventory.py`
  - late reaction latch and reset rejection witnesses added.
- `RULE_TO_CODE_CONFORMANCE.json` updated to bind the full source adapter and verifier.

## Required executed gate before READY

The code above is authored but connector-only authoring is not execution evidence. A workspace/cloud run must execute on the exact committed bytes:

1. `python scripts/verify_machine_strategy_v4_1_source_adapter.py --full`.
2. All targeted v4.1 tests including contracts, inventory, execution binding and funding guard.
3. Compile/static/lint/type and safety invariant checks.
4. Exact frozen design/v4 STOP/Stage-A parent resume and frozen-byte invariance checks.
5. Full sealed-history source/rule/lifecycle conformance for BTC-USDT-SWAP and ETH-USDT-SWAP with finance-engine trap.
6. Serial independent `execution_auditor`, `no_lookahead_auditor`, and separate `final_independent_reviewer`.
7. Publish exact `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY` or exact STOP plus `IMPLEMENTATION_FREEZE_MANIFEST.json` only on full affirmative evidence.

No historical v4.1 fill/exit/finance, catalog-count selection, WR, PF, expectancy, P&L, DD, MFE/MAE or OOS/PAPER/LIVE/private API/platform work is authorized by this checkpoint. Qualification remains unchanged including WR>=70%.
