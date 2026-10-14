# MACHINE_STRATEGY_v4.1 — implementation checkpoint

State: IMPLEMENTATION_IN_PROGRESS. This checkpoint is not READY and authorizes no historical financial evaluation.

## New distinct v4.1 paths

- `scripts/machine_strategy_v4_1_contracts.py`
  - canonical selected-POI identities for STB/BREAKER/RANGE;
  - Decimal50 HALF_EVEN design parsing/serialization;
  - monotonic first-admissible M15 eligibility latch;
  - native OPEN eligibility / native CLOSE contact publication;
  - RANGE required-reaction self-consumption exemption;
  - pre-emission consumed/retired rejection;
  - Decimal50 canonical-string -> Decimal80 ledger transport;
  - unconditional historical financial execution blocker.
- `scripts/machine_strategy_v4_1_selected_poi_inventory.py`
  - preproposal physical selected-POI registration;
  - M15 eligibility latch independent of viable H1 proposal;
  - native first-test event publication and permanent consumption/retirement;
  - H1 proposal origin-CONF vs proposal-CONF separation;
  - no position/outcome/financial imports or outputs.
- `tests/test_machine_strategy_v4_1_contracts.py`
  - synthetic witnesses for identities, monotonic CONF latch, partial native interval, native CLOSE publication, RANGE reaction exemption, equal-cutoff preconsumption, CONF A/B separation and Decimal50->80 transport.

## Required next executed QA

The cloud/workspace must execute, not infer, at minimum:

1. compile/import of both new modules;
2. `tests/test_machine_strategy_v4_1_contracts.py` plus frozen v4/v4.1 design tests;
3. lint/type/static safety checks, including no `trade_entry_allowed=True`;
4. exact v4.1 design `--resume-existing` against manifest `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`;
5. exact v4 STOP checkpoint resume against `6e325d6e5b3cffc4f143bfd4d390712b39ea940bccd4504c85148ed904bbcd7e`;
6. bind the inventory into a distinct full `v4_1` historical source adapter and run source-only prefix/future-mutation/replay with finance-engine trap;
7. verify all five H1/H4 family clocks, same-time TF advancement, H4 midbar M15 execution independence, contact-at-emission rejection, post-exit ownership, deadline/gap/EOF boundaries;
8. complete nine-scenario synthetic execution/funding/fixed-U/Decimal transport guards;
9. independent execution/no-lookahead/final review before any READY freeze.

No historical v4/v4.1 case fill/exit, P&L, WR, PF, expectancy, drawdown, MFE/MAE or equity is permitted in this checkpoint.

`trade_entry_allowed=false`; PAPER=false; LIVE=false; production candidate NONE.
