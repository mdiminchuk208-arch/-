# Machine strategy workflow report

| Stage | Version | Status | Commit | Manifest | Next gate |
|---|---|---|---|---|---|
| — | Original/reference | HASH_VERIFIED_PRESERVED | 29da54ed9476b3281c0d7aab225ffa6c39d31c6a | docs/machine_strategy_preservation/freeze_manifest.json | INITIAL_PROOF_PRECEDES_MACHINE_DESIGN |
| 1 | v2 | DETERMINISTIC | 3861d9e8ce661066cf46ade123be846f943aec19 | docs/machine_strategy_v2_design/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 2 | v2 | PRE_OUTCOME_COMMITTED | c6bf08761800750146dfb99f0c33f4a3c9b29a76 | docs/machine_strategy_v2_pre_outcome/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 3 | v2 | FINANCIAL_RESULT_FROZEN | 4c18005a633390d1d6f4105462af44a9fcefc373 | docs/machine_strategy_v2_result/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 4 | v2 | FAIL | 72852d307fc016eaba882245477231c62f2cbaa7 | docs/machine_strategy_v2_robustness/freeze_manifest.json | QUALITY_AND_EXECUTION_READINESS |
| 5 | v2.1 | DETERMINISTIC | 39e263542b0f94677a8665e0d1e7931617296778 | docs/machine_strategy_v2_1_design/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 5 | v2.1 | PRE_OUTCOME_COMMITTED | 8d9dbf777af433788825ad0a4ab2cf3b7881ffe6 | docs/machine_strategy_v2_1_pre_outcome/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 5 | v2.1 | FINANCIAL_RESULT_FROZEN | a6da596765b8a2c003fed1a4b0b92ec755a6566a | docs/machine_strategy_v2_1_result/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 5 | v2.1 | FAIL | db4b7c7f632288c107b213264209d26752da096c | docs/machine_strategy_v2_1_robustness/freeze_manifest.json | QUALITY_AND_EXECUTION_READINESS |
| 6 | v2.2 | DETERMINISTIC | fe16012f944f73d22a23acee653408beab85d923 | docs/machine_strategy_v2_2_design/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 6 | v2.2 | PRE_OUTCOME_COMMITTED | 84253b63a3ad6f6d72bfb0a8dca5c87a665d577d | docs/machine_strategy_v2_2_pre_outcome/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 6 | v2.2 | FINANCIAL_RESULT_FROZEN | e1b6b00c3534541e6cfa862e4319181cc8c42722 | docs/machine_strategy_v2_2_result/freeze_manifest.json | NEXT_SEQUENTIAL_STAGE |
| 6 | v2.2 | FAIL | 0c3cd926d3038de6d1b85a950880b26a2c089ea3 | docs/machine_strategy_v2_2_robustness/freeze_manifest.json | QUALITY_AND_EXECUTION_READINESS |
| 7 | — | BLOCKED_NOT_RUN | — | — | QUALIFIED_BASE_PRODUCTION_CANDIDATE |
| 8 | — | BLOCKED_NOT_RUN | — | — | SATISFACTORY_BACKTEST_ROBUSTNESS_AND_TESTED_OVERLAYS |
| 9 | — | BLOCKED_NOT_RUN | — | — | SUCCESSFUL_200_CLOSED_30_DAY_FORWARD_PAPER_GATE |

| Version | CLOSED | WR % | PF | Expectancy/AvgR | Net ex-funding R | MaxDD R | Robustness |
|---|---:|---:|---:|---:|---:|---:|---|
| v2 | 223 | 52.91479820627802 | 0.6829382381754818 | -0.2152008095806765 | -47.98978053649086 | 78.95457438204309 | WEAK |
| v2.1 | 83 | 45.78313253012048 | 0.8375520967969219 | -0.1366483795039568 | -11.341815498828415 | 29.063266435212768 | INSUFFICIENT_SAMPLE |
| v2.2 | 39 | 33.33333333333333 | 0.8962485230465018 | -0.1400836204861817 | -5.463261198961086 | 23.64980637851785 | INSUFFICIENT_SAMPLE |

CURRENT_PRODUCTION_CANDIDATE=null. PAPER_TRADING_READY=false. REAL_TRADING_READY=false. trade_entry_allowed=false.

STOP:
- No production candidate selected: completed development versions do not establish qualified backtest/robustness and exchange execution evidence.
- Theoretical unrounded tick/epsilon execution and unavailable funding cannot establish realistic exchange performance.
- No independent forward/OOS validation; same-history v2.1/v2.2 results are development diagnostics.
- No paper session started; 0 CLOSED virtual paper trades and 0 calendar days. Historical CLOSED is not forward paper evidence.

v2.1: edge/cost>=5. v2.2: retain cost budget and add structural target>=1 initial R. Stops/targets/branches/periods remain unchanged; rejected wins and losses are reported. No threshold sweep or best subgroup selection. No prior frozen version rewritten.

QA: exact matched execution identity, inherited source/data/archive hashes, deterministic outputs and mode/prefix/future-mutation checks. All trades/metrics/breakdowns/holding/cost sensitivity in version result and robustness namespaces. Funding excluded; unrounded theoretical prices. Values are independent-case normalized risk units and diagnostic closed-return drawdown, not account currency or a live portfolio. Backtest results do not guarantee future profits.
