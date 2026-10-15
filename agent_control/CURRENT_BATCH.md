# Current Campaign — v4.1 Executed Implementation QA

Frozen DESIGN_PASS published `96e76edf0e526c588cf87a665da681f577cca77a`, manifest `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`.

Active gate: `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_QA_PENDING`. Do not restart design and do not open financial validation yet.

Distinct v4.1 implementation paths are now authored through the full source/lifecycle adapter boundary:
- `machine_strategy_v4_1_contracts.py`;
- `machine_strategy_v4_1_selected_poi_inventory.py` with monotonic late-reaction latch;
- `machine_strategy_v4_1_historical_adapter.py` with every-M15 source/lifecycle ordering, OPEN context snapshot, CLOSE contact publication and H1-only proposal clock;
- `machine_strategy_v4_1_execution_binding.py` all-nine non-financial scenario planning;
- `machine_strategy_v4_1_funding_guard.py` registered synthetic-only funding guard;
- `verify_machine_strategy_v4_1_source_adapter.py` deterministic replay/future-tail/full-period finance-trap verifier;
- targeted v4.1 unit/synthetic witnesses and readiness conformance artifacts;
- `THIRD_IMPLEMENTATION_CHECKPOINT.md`.

## Execute now

1. `python scripts/verify_machine_strategy_v4_1_source_adapter.py --full`.
2. Run all targeted v4.1 tests plus compile/static/lint/type/safety checks.
3. Verify frozen parent resumes/hashes and predecessor invariance.
4. Review all-five-family source/lifecycle ordering and no-lookahead on exact executed bytes.
5. Serial execution auditor → no-lookahead auditor → separate final independent reviewer.
6. Freeze exactly `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY` or exact STOP with `IMPLEMENTATION_FREEZE_MANIFEST.json`/checkpoint evidence.

Only READY may open the separately named one-shot development financial gate. No historical fill/exit/WR/PF/P&L/catalog-count selection in this batch. Qualification remains unchanged including WR>=70%. No OOS/PAPER/LIVE/private API/orders/platform; `trade_entry_allowed=false`; ECC hooks inactive.
