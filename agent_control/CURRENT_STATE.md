# Current State

State: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_OPEN`.

Strategy-first campaign remains active; platform/site work is paused. Production candidate NONE. `trade_entry_allowed=false`; PAPER=false; LIVE=false.

## Frozen implementation authority

`MACHINE_STRATEGY_V4_1_IMPLEMENTATION_READY` is complete and frozen at commit `bf9bb4c7ed9e82df42b4fc2eec5df28695edf155`, external implementation manifest SHA256 `e18fa81383bac27af8524ad62703a894018c6b761241faa5015109efebcf0e61`. Exact resume PASS. Implementation QA: 89 targeted/registered-synthetic tests plus static/type/compile, complete sealed-data verification, deterministic full BTC/ETH source replay, field conformance and independent execution/no-lookahead/final reviews PASS. Historical position evaluations at implementation freeze: 0.

Frozen v4.1 design manifest: `4074c337be4800e54682a5ad1ddfd9015e35ce16f4fe2742fc4d12b4bb415790`. Frozen v4 design manifest: `b9452dea092c0d186d2ac164c044f2fad0d865becf9904791caebbf7b477273b`. All strategy rules and qualification thresholds including WR>=70% remain unchanged.

## Active gate — one-shot development financial v1

Financial preregistration was committed **before any v4.1 historical financial outcome**:
- preregistration: `docs/machine_strategy_v4_1_development_financial_v1/PREREGISTRATION.json`
- preregistration commit: `f5e60538a2c6ea4194177971ac1d433143ddf3a2`
- authorization: `docs/machine_strategy_v4_1_development_financial_v1/AUTHORIZATION.json`
- authorization commit: `4a0a1471c040522058cb0520b0dc25a8dd20d4b5`
- work order: `agent_control/V4_1_DEVELOPMENT_FINANCIAL_WORK_ORDER.md`

Frozen scope: OKX `BTC-USDT-SWAP` + `ETH-USDT-SWAP`, exposed development `[2024-10-13T00:00:00Z,2026-10-13T00:00:00Z)`, LONG+SHORT, SFP/OB/BREAKER/STB/RANGE, H1 signal clock, every-M15 execution/lifecycle, all nine synthetic compatibility scenarios, base and doubled fee/slippage columns, actual signed funding with coherent adverse timing witness, immutable reference U and all existing qualification thresholds.

One-shot runner: `scripts/run_machine_strategy_v4_1_development_financial_v1.py`.
Synthetic runner guards: `tests/test_machine_strategy_v4_1_development_financial_runner.py`.
Independent post-result auditor: `scripts/audit_machine_strategy_v4_1_development_financial_v1.py`.

The runner is guarded by committed implementation/preregistration/authorization bytes and refuses execution if final output/checkpoint files already exist. It builds the frozen source catalog first, replays v4.1 pending lifecycle before every M15 OPEN, executes current-bar events before contact published at CLOSE, inherits frozen conservative filled-position exits, retains all nine scenario states, and uses Decimal80 realized accounting without rebuilding Decimal50 design geometry.

**No v4.1 historical financial result exists yet.** Candidate count, CLOSED, WR, PF, expectancy, net P&L, DD and case outcomes have not yet been generated/viewed in this gate. Existing v3 failed numbers remain historical evidence only and are not v4.1 results.

## Exact next execution

Follow `CURRENT_BATCH.md` and `NEXT_TASK.md`:
1. verify frozen implementation resume;
2. execute new runner synthetic/negative QA + relevant inherited execution/funding/static checks;
3. run `--verify-authorization`;
4. if no result checkpoint exists, execute exactly one `--run`;
5. immediately checkpoint/commit/push exact catalog/case/result bytes;
6. execute independent financial audit and serial backtest/cost/statistics/overfit/final reviews;
7. freeze exact `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_PASS` or `..._STOP`.

After any financial output is emitted, no silent rerun, parameter sweep, threshold tuning, family/direction removal, profitable-slice selection or catalog-count selection is allowed. Any rule change requires a new explicit strategy version. PASS may open robustness and separately registered untouched OOS prerequisites only. STOP opens causal failure audit/new explicit version. No OOS relabeling, PAPER/LIVE/private exchange API/orders/platform in this gate.

## Frozen predecessor evidence retained

- OKX Stage A sealed data: 210,240 M15 bars + 4,380 signed funding rows + 774 receipts.
- v3 compatibility READY manifest `5faeb02bd244777aa416d57f50f9809d9e59abe1eb2ec2fc8c062de721619fd1`.
- v3 financial STOP checkpoint `2d7770680867f93948d4d26b91633cbb8cdbc9136bd54a988436a687accc6dd0`.
- v3 failure audit manifest `9b0353dbfeabfa2768f4a1f62af820c128f98c48faad09544acee4c0547867a3`.
- v3 known diagnostic: 99 candidates, 20 all-nine CLOSED, base WR50%, PF_R0.278459, expectancy -0.309356R, net -6.187114R; doubled WR45%, PF_R0.162663, net -9.243979R. These are not v4.1 outcomes.

Pre-run checkpoint:110tests/sevencommands and real authorization PASS; independent execution reviewer21tests/current hashes PASS. New wrapper-only defects repaired before any historical outcome, frozen implementation bytes unchanged. No historical result/RUN_STARTED exists yet; next action exactly one authorized run, immediate checkpoint/commit/push before analysis. See PRE_RUN_QA_RECEIPT and EXECUTION_PRE_RUN_REVIEW in the development financial namespace.
