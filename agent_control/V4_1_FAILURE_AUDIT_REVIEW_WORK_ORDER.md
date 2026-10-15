# Work order — MACHINE_STRATEGY_v4.1 cached-evidence failure audit review

State: `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_REVIEW_PENDING`.

## Frozen inputs

- Financial result: `MACHINE_STRATEGY_V4_1_DEVELOPMENT_FINANCIAL_STOP`.
- External result manifest SHA256: `d0a05dcd49545ae963a89840aa09388419b5213f963ba0bd266686e622812d74`.
- RUN_CHECKPOINT SHA256: `7dfaa6fb20c07febdbdb4a98278ce6c92ea4d1a026499656b3c9c5ed0280d6f8`.
- Audit namespace: `docs/machine_strategy_v4_1_failure_audit_v1/`.

## Required review sequence

Use cached/frozen evidence only; zero historical engine calls.

1. `strategy_explorer`: independently reconcile funnel and family/direction/timeframe coverage; verify no profitability slice is promoted to a rule.
2. `execution_auditor`: independently verify the inference 396 retired + 18 expired = 44 all-nine retired + 2 all-nine expired cases, and review lifecycle/reachability causal language. Reject any claim not supported by frozen state records.
3. `cost_funding_auditor`: verify the statement that costs amplify but do not create the negative aggregate sign; preserve all exchange-model limitations.
4. `backtest_reviewer` or equivalent independent causal reviewer: verify every numeric claim against frozen result artifacts and check that unresolved evidence is explicit rather than imputed.
5. Separate `final_independent_reviewer`: issue exact `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_PASS` or `MACHINE_STRATEGY_V4_1_FAILURE_AUDIT_STOP` and freeze an exact manifest.

## Audit acceptance requirements

- No financial replay, changed-trade simulation, new PnL calculation from alternative rules, robustness/OOS/forward run, parameter sweep or tuning.
- No SHORT ban, H4-only/SFP-only promotion, family deletion, lifetime extension, or cost change derived from exposed outcomes.
- Exact reconciliation: 54 candidates / 486 states / 46 no-fill / 8 filled / 7 CLOSED / 1 filled unresolved.
- Preserve one unresolved all-nine `WAIT_INTRABAR_ORDER` case with no assigned exit.
- Preserve gross-negative finding separately from modeled-cost amplification.
- Preserve tiny-sample and exposed-development limitations.
- If cached artifacts cannot support an exact retirement-reason census, retain that as unresolved; do not invent it.
- Produce review receipts, QA/source-causality consistency record and `FAILURE_AUDIT_FREEZE_MANIFEST.json` only after all reviews pass.

## After review

If PASS, the next possible phase is a separately named **pre-outcome strategy design gate** using only audit-supported hypotheses. No v4.2 implementation or financial test is authorized by audit PASS alone.

If STOP, repair only the audit claim/evidence mismatch; do not alter strategy rules or run financial history.

Safety remains: `trade_entry_allowed=false`; no PAPER/LIVE/private API/orders/platform.
