# Work order — MACHINE_STRATEGY_v4.1 failure audit review with source-fidelity check

State: `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_REVIEW_PENDING`.

## Frozen inputs

- Financial result: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP`.
- External result manifest SHA256: `d0a05dcd49545ae963a89840aa09388419b5213f963ba0bd266686e622812d74`.
- RUN_CHECKPOINT SHA256: `7dfaa6fb20c07febdbdb4a98278ce6c92ea4d1a026499656b3c9c5ed0280d6f8`.
- Audit namespace: `docs/machine_strategy_v4_1_failure_audit_v1/`.
- Mandatory source-fidelity evidence: `SOURCE_FIDELITY_FINDING.md`, supplied `Методичка.docx`, and the prior source-evidence plan containing the 176365 raw-proposal universe and the no-hidden-threshold/visual-annotation requirement.

## Required review sequence

No historical financial replay or changed-trade simulation.

1. `strategy_explorer`: reconcile the frozen funnel and independently compare candidate-generation coverage to the supplied methodology. Determine whether the 54-candidate/two-year stream is a strategy-translation artifact rather than natural method frequency.
2. `execution_auditor`: verify 396 retired +18 expired =44 all-nine retired +2 all-nine expired cases and review whether H1-only proposal timing, selected-POI/first-test admission and pending retirement can structurally starve otherwise source-valid visual setups.
3. `source-fidelity review` within the competent strategy/execution review: verify the methodology claims that market structure/SFP apply across timeframes and that OB/Breaker/Range/liquidity are visual/contextual chart constructions. Verify that qualitative concepts were not source-defined as the hard numeric gates introduced later.
4. `cost_funding_auditor`: verify that costs amplify but do not create the negative aggregate sign; preserve exchange-model limitations.
5. `backtest_reviewer` or equivalent independent causal reviewer: verify every numeric claim and the distinction between financial failure and source-fidelity failure.
6. Separate `final_independent_reviewer`: issue exact `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_PASS` or `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_STOP` and freeze an exact manifest.

## Audit acceptance requirements

- No financial replay, alternative PnL, robustness/OOS/forward run, parameter sweep or outcome-driven tuning.
- No SHORT ban, H4-only/SFP-only promotion or profitable-slice selection.
- Exact frozen reconciliation:54 candidates /486 states /46 no-fill /8 filled /7 CLOSED /1 filled unresolved.
- Explicitly classify whether v4/v4.1 over-constrained the source strategy. If accepted, source-fidelity mismatch becomes a primary causal finding.
- Do not infer that the supplied method naturally trades only tens of times per year from the v4.1 output.
- Do not force an arbitrary trade count either. The next design must first prove opportunity coverage and rejection telemetry before PnL.
- A future source-faithful candidate layer must keep exact objective predicates deterministic but route genuinely qualitative visual concepts through blinded chart annotation rather than invented hidden thresholds.
- Preserve one unresolved all-nine `WAIT_INTRABAR_ORDER` case with no assigned exit.
- Preserve gross-negative finding separately from modeled-cost amplification.
- Produce review receipts, QA/source-causality/source-fidelity consistency record and `FAILURE_AUDIT_FREEZE_MANIFEST.json` only after all reviews pass.

## After review

If PASS, the next possible phase is a separately named **pre-outcome source-fidelity strategy design gate**. Its first deliverable is candidate discovery/visual annotation coverage, not financial optimization. No v4.2 historical PnL run is authorized by audit PASS alone.

If STOP, repair only the audit/evidence mismatch; do not alter strategy rules or run financial history.

Safety remains: `trade_entry_allowed=false`; no PAPER/LIVE/private API/orders/platform.
