# Next Task — MACHINE_STRATEGY_v4.1 one-shot development financial gate

State: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_OPEN`.

Do not restart design or implementation readiness. Reuse frozen implementation commit `bf9bb4c7ed9e82df42b4fc2eec5df28695edf155` and external manifest SHA256 `e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61`.

Read and execute `agent_control/V4_1_DEVELOPMENT_FINANCIAL_WORK_ORDER.md` completely. The financial rules were preregistered before outcomes in `docs/machine_strategy_v4_1_development_financial_v1/PREREGISTRATION.json`; one-shot authorization is in `AUTHORIZATION.json`.

First execute pre-run QA on `scripts/run_machine_strategy_v4_1_development_financial_v1.py` and its synthetic guards. Then run `--verify-authorization`. If and only if those PASS and no result checkpoint exists, execute exactly one historical `--run`. Immediately checkpoint and commit/push exact outputs before any analysis or repair based on results.

After the one-shot output exists, never silently rerun or retune. Independently audit all-nine coverage, realized accounting and frozen qualification thresholds; then serially review and freeze exact PASS or STOP. If STOP, open causal failure audit/new explicit strategy version. If PASS, open robustness / separately registered untouched OOS prerequisites. No OOS relabeling, PAPER, LIVE, private API/orders or platform reconnect here. `trade_entry_allowed=false`.
