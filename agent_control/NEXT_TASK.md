# Next Task — MACHINE_STRATEGY_v4.1 Executed Implementation QA

State: MACHINE_STRATEGY_V4_1_IMPLEMENTATION_QA_PENDING. Frozen design publication `96e76edf0e526c588cf87a665da681f577cca77a`; external design manifest `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`.

Do **not** restart design and do not author a new strategy version. The distinct v4.1 source/lifecycle implementation is now present through the historical source-adapter boundary.

Execute on the exact current branch bytes, in order:

1. `python scripts/verify_machine_strategy_v4_1_source_adapter.py --full` — BTC/ETH deterministic full source/lifecycle replay, bounded prefix replay, future-M15-tail mutation invariance, zero position-engine calls, financial-runner import trap.
2. Run targeted v4.1 tests for contracts, selected-POI inventory, execution binding and funding guard.
3. Run compile/static/lint/type and runtime safety checks; `trade_entry_allowed` must remain false.
4. Verify exact frozen v4.1 design, prior v4 STOP checkpoint and Stage-A parent resumes/hashes; frozen predecessor bytes must be unchanged.
5. Inspect all-five-family source/lifecycle conformance: preproposal M15 latch, late reaction latch, native context known at OPEN, contact learned at CLOSE, equal-cutoff contact before H1 proposal, half-open deadline/retirement, no CONF rebasing, no hidden parent-consumption substitution.
6. Run serial `execution_auditor`, then `no_lookahead_auditor`, then separate `final_independent_reviewer` on the exact QA/code bytes.
7. Finish exactly `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY` with externally pinned `IMPLEMENTATION_FREEZE_MANIFEST.json`, or exact `MACHINE_STRATEGY_V4_1_IMPLEMENTATION_STOP` with specific blockers.

READY may open only a separately named one-shot development financial gate. Do not run historical v4.1 fills/exits/WR/PF/P&L inside this QA gate. No catalog-count selection/tuning, OOS/PAPER/LIVE/private API/orders/platform. Qualification remains unchanged including WR>=70%; `trade_entry_allowed=false`.
