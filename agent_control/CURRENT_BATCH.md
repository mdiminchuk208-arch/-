# Current Campaign — v4.1 one-shot development financial gate

State: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_OPEN`.

Frozen implementation READY authority: commit `bf9bb4c7ed9e82df42b4fc2eec5df28695edf155`, manifest SHA256 `e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61`.

Pre-outcome financial preregistration: `docs/machine_strategy_v4_1_development_financial_v1/PREREGISTRATION.json`, commit `f5e60538a2c6ea4194177971ac1d433143ddf3a2`.
One-shot authorization: `docs/machine_strategy_v4_1_development_financial_v1/AUTHORIZATION.json`, commit `4a0a1471c040522058cb0520b0dc25a8dd20d4b5`.
Work order: `agent_control/V4_1_DEVELOPMENT_FINANCIAL_WORK_ORDER.md`.

## Execute in this order

1. Verify exact implementation resume:
   `PYTHONPATH=scripts python scripts/verify_machine_strategy_v4_1_implementation_v1.py --resume-existing --expected-manifest-sha256 e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61`
2. Run targeted financial-runner synthetic/negative tests plus relevant frozen execution/funding tests, compile/static/type checks. Repair implementation-only defects **before** historical outputs; do not change strategy rules.
3. Verify authorization:
   `PYTHONPATH=scripts python scripts/run_machine_strategy_v4_1_development_financial_v1.py --verify-authorization`
4. Confirm no final one-shot output/checkpoint exists and record exact pre-run runner/test/auditor hashes in the gate QA receipt.
5. Execute exactly once:
   `PYTHONPATH=scripts python scripts/run_machine_strategy_v4_1_development_financial_v1.py --run`
6. Immediately record `RUN_CHECKPOINT.json` SHA256 and commit/push all exact catalog/case/result bytes. Do not rerun after any financial outputs exist.
7. Run the independent post-result auditor on the frozen bytes:
   `PYTHONPATH=scripts python scripts/audit_machine_strategy_v4_1_development_financial_v1.py --write`
   The auditor independently checks catalog/case coverage, all-nine scenario ordering, reference U, realized gross/fee/slippage/net arithmetic, base+doubled metrics, net cash, coin-direction requirements, Wilson/concentration/disagreement/unknown-exit gates. If runner and auditor decisions differ, final gate is STOP; never rerun to reconcile them.
8. Serial result reviews: backtest_reviewer → cost_funding_auditor → statistics_robustness_analyst → overfit_red_team → final_independent_reviewer. Cost/funding review must independently verify signed funding witnesses against sealed rows.
9. Freeze exactly `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_PASS` or `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP` with an external result manifest.

The runner's internal decision is provisional until the independent audit and reviews accept the exact frozen output. No parameter sweep, no threshold tuning, no post-result family/direction removal, no profitable-slice or catalog-count selection. Existing history is exposed development, not OOS. PASS may open robustness / separately registered untouched OOS prerequisites only. STOP opens causal failure audit/new explicit strategy version. No PAPER/LIVE/private API/orders/platform; `trade_entry_allowed=false`.
